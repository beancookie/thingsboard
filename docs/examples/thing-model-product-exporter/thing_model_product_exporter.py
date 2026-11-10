#!/usr/bin/env python3
"""物模型产品导出工具示例。

从运行中的 ThingsBoard / thing-model 平台导出产品列表和完整 TSL 物模型，
输出 products.csv、products.json 和 tsl/<productId>.tsl.json。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import csv
import getpass
import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

LOGGER = logging.getLogger("thing-model-product-exporter")

CSV_FIELDS = [
    "product_id",
    "name",
    "model",
    "category_id",
    "tsl_version",
    "status",
    "property_count",
    "event_count",
    "action_count",
    "tb_profile_id",
    "tb_asset_id",
    "tb_rule_chain_id",
    "updated_at",
    "tsl_file",
    "error",
]

_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class ExporterConfig:
    tb_url: str
    thingmodel_url: str
    api_key: Optional[str]
    username: str
    password: Optional[str]
    product_ids: List[str]
    output_dir: Path
    include_detail: bool
    timeout: float
    log_level: str


class ApiError(RuntimeError):
    pass


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_filename(value: str, fallback: str = "product") -> str:
    name = _INVALID_FILENAME.sub("_", value.strip()).strip(" .")
    return name or fallback


class ThingsBoardClient:
    def __init__(self, config: ExporterConfig) -> None:
        self.config = config
        self.tb_url = config.tb_url.rstrip("/")
        self.thingmodel_url = config.thingmodel_url.rstrip("/")
        self.session = requests.Session()

    @property
    def product_api_base(self) -> str:
        base = self.thingmodel_url
        if base.endswith("/api/thing-model") or base.endswith("/api"):
            return f"{base}/products"
        return f"{base}/api/products"

    def authenticate(self) -> str:
        if self.config.api_key:
            return self.exchange_api_key_for_token(self.config.api_key)
        password = self.config.password
        if not password:
            password = getpass.getpass(
                f"ThingsBoard password for {self.config.username}: ")
        return self.login(self.config.username, password)

    def login(self, username: str, password: str) -> str:
        response = self.session.post(
            f"{self.tb_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=self.config.timeout,
        )
        self._check(response)
        return response.json()["token"]

    def exchange_api_key_for_token(self, api_key: str) -> str:
        api_key_header = self.api_key_token(api_key)
        user_response = self.session.get(
            f"{self.tb_url}/api/auth/user",
            headers=self._auth_headers(api_key_header),
            timeout=self.config.timeout,
        )
        self._check(user_response)
        user_id = ((user_response.json() or {}).get("id") or {}).get("id")
        if not user_id:
            raise ApiError("API Key 未返回用户 ID")
        token_response = self.session.get(
            f"{self.tb_url}/api/user/{user_id}/token",
            headers=self._auth_headers(api_key_header),
            timeout=self.config.timeout,
        )
        self._check(token_response)
        token = (token_response.json() or {}).get("token")
        if not token:
            raise ApiError("API Key 未返回 JWT")
        return token

    def api_key_token(self, api_key: str) -> str:
        value = api_key.strip()
        if not value:
            raise ApiError("API Key 不能为空")
        if value.lower().startswith("apikey "):
            value = value[len("ApiKey "):].strip()
        return f"ApiKey {value}"

    def _auth_headers(self, token: str) -> Dict[str, str]:
        value = token.strip()
        lower = value.lower()
        if lower.startswith("apikey "):
            return {
                "X-Authorization": f"ApiKey {value[len('ApiKey '):].strip()}"
            }
        if lower.startswith("bearer "):
            return {
                "X-Authorization": f"Bearer {value[len('Bearer '):].strip()}"
            }
        if value.startswith("tb_"):
            return {"X-Authorization": f"ApiKey {value}"}
        return {"X-Authorization": f"Bearer {value}"}

    def _check(self, response: requests.Response) -> None:
        if response.status_code >= 400:
            raise ApiError(
                f"HTTP {response.status_code} {response.url}: "
                f"{response.text[:500]}")

    def list_products(self, token: str) -> List[Dict[str, Any]]:
        response = self.session.get(
            self.product_api_base,
            headers=self._auth_headers(token),
            timeout=self.config.timeout,
        )
        self._check(response)
        return response.json() or []

    def get_product_detail(
            self, token: str, product_id: str) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.product_api_base}/{quote(product_id, safe='')}",
            headers=self._auth_headers(token),
            timeout=self.config.timeout,
        )
        self._check(response)
        return response.json()

    def get_thing_model(
            self, token: str, product_id: str) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.product_api_base}/"
            f"{quote(product_id, safe='')}/thing-model",
            headers=self._auth_headers(token),
            timeout=self.config.timeout,
        )
        self._check(response)
        return response.json()


def base_row(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "product_id": item.get("productId") or "",
        "name": item.get("name") or "",
        "model": item.get("model") or "",
        "category_id": item.get("categoryId") or "",
        "tsl_version": item.get("tslVersion") or "",
        "status": item.get("status") or "",
        "property_count": item.get("propertyCount"),
        "event_count": item.get("eventCount"),
        "action_count": item.get("actionCount"),
        "tb_profile_id": item.get("tbProfileId") or "",
        "tb_asset_id": item.get("tbAssetId") or "",
        "tb_rule_chain_id": item.get("tbRuleChainId") or "",
        "updated_at": item.get("updatedAt") or "",
        "tsl_file": "",
        "error": "",
    }


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def export_product(
        client: ThingsBoardClient,
        token: str,
        item: Dict[str, Any],
        tsl_dir: Path,
        include_detail: bool) -> Dict[str, Any]:
    row = base_row(item)
    product_id = row["product_id"]
    if not product_id:
        row["error"] = "product has no productId"
        return row

    try:
        thing_model = client.get_thing_model(token, product_id)
    except Exception as exc:
        row["error"] = str(exc)
        return row

    tsl = thing_model.get("tsl") if isinstance(thing_model, dict) else None
    if not isinstance(tsl, dict):
        tsl = thing_model
    tsl_name = f"{sanitize_filename(product_id)}.tsl.json"
    write_json(tsl_dir / tsl_name, tsl)
    row["tsl_file"] = f"tsl/{tsl_name}"

    if include_detail:
        try:
            row["_detail"] = client.get_product_detail(token, product_id)
        except Exception as exc:
            row["error"] = f"detail: {exc}"
    return row


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="导出 thing-model 产品列表与完整 TSL 物模型。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    connection = parser.add_argument_group("连接")
    connection.add_argument(
        "--tb-url",
        default="http://localhost:8080",
        help="ThingsBoard 地址",
    )
    connection.add_argument(
        "--thingmodel-url",
        default="http://localhost:8080/api/thing-model",
        help="thing-model 地址；网关代理使用 <host>/api/thing-model",
    )
    connection.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP 超时秒数",
    )

    auth = parser.add_argument_group("认证")
    auth.add_argument(
        "--api-key",
        default=None,
        help="ThingsBoard API Key；与账号密码二选一",
    )
    auth.add_argument(
        "--username",
        default="tenant@thingsboard.org",
        help="使用账号密码登录时的用户名",
    )
    auth.add_argument(
        "--password",
        default=None,
        help="使用账号密码登录时的密码；缺省时交互输入",
    )

    output = parser.add_argument_group("输出")
    output.add_argument(
        "--product-id",
        action="append",
        default=[],
        help="指定产品 ID，可重复；缺省导出全部产品",
    )
    output.add_argument(
        "--output-dir",
        default="product-export",
        help="输出目录",
    )
    output.add_argument(
        "--no-detail",
        action="store_true",
        help="跳过产品详情请求，只导出列表和 TSL",
    )
    output.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> ExporterConfig:
    return ExporterConfig(
        tb_url=args.tb_url,
        thingmodel_url=args.thingmodel_url,
        api_key=args.api_key,
        username=args.username,
        password=args.password,
        product_ids=[pid.strip() for pid in args.product_id if pid.strip()],
        output_dir=Path(args.output_dir),
        include_detail=not args.no_detail,
        timeout=args.timeout,
        log_level=args.log_level,
    )


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)

    if args.api_key and args.password:
        parser.error("--api-key 与 --password 不能同时使用")

    config = config_from_args(args)
    client = ThingsBoardClient(config)

    try:
        token = client.authenticate()
        products = client.list_products(token)
    except Exception as exc:
        LOGGER.error("认证或获取产品列表失败: %s", exc)
        if args.api_key and "HTTP 401" in str(exc):
            LOGGER.error(
                "目标服务拒绝了 API Key，请检查密钥或改用 --username/--password")
        return 1

    wanted = config.product_ids
    if wanted:
        by_id = {item.get("productId"): item for item in products}
        selected = [item for item in products
                    if item.get("productId") in wanted]
        missing = [pid for pid in wanted if pid not in by_id]
    else:
        selected = products
        missing = []

    output_dir = config.output_dir
    tsl_dir = output_dir / "tsl"
    rows: List[Dict[str, Any]] = []
    exported: List[Dict[str, Any]] = []
    failures = 0

    for item in selected:
        row = export_product(
            client, token, item, tsl_dir, config.include_detail)
        detail = row.pop("_detail", None)
        if row["error"]:
            failures += 1
            LOGGER.error("导出失败 %s: %s", row["product_id"], row["error"])
        else:
            LOGGER.info(
                "已导出 %s (%s) -> %s",
                row["product_id"],
                row["name"],
                row["tsl_file"],
            )
        rows.append(row)
        exported.append({
            "meta": item,
            "detail": detail,
            "tslFile": row["tsl_file"],
            "error": row["error"],
        })

    for pid in missing:
        failures += 1
        row = base_row({"productId": pid})
        row["error"] = "product not found"
        rows.append(row)
        exported.append({
            "meta": {},
            "detail": None,
            "tslFile": "",
            "error": row["error"],
        })
        LOGGER.error("导出失败 %s: 产品不存在", pid)

    write_csv(output_dir / "products.csv", rows)
    write_json(output_dir / "products.json", {
        "exportedAt": now_iso(),
        "tbUrl": client.tb_url,
        "thingmodelUrl": client.thingmodel_url,
        "count": len(exported),
        "products": exported,
    })

    LOGGER.info(
        "汇总 products=%s exported=%s failed=%s output=%s",
        len(rows),
        len(rows) - failures,
        failures,
        output_dir,
    )
    print(f"csv: {output_dir / 'products.csv'}")
    print(f"json: {output_dir / 'products.json'}")
    print(f"tsl: {tsl_dir}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
