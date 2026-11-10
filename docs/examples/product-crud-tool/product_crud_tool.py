#!/usr/bin/env python3
"""产品增删改查工具示例。

通过 thing-model REST API 完成产品的查询、创建、更新、TSL 提交、校验和删除。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import getpass
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

LOGGER = logging.getLogger("product-crud-tool")

DEFAULT_TB_URL = "http://localhost:8080"
DEFAULT_THINGMODEL_URL = "http://localhost:8080/api/thing-model"


@dataclass
class ToolConfig:
    tb_url: str
    thingmodel_url: str
    api_key: Optional[str]
    username: str
    password: Optional[str]
    action: str
    product_id: Optional[str]
    keyword: Optional[str]
    page_size: int
    page: int
    config: Optional[Path]
    tsl: Optional[Path]
    tsl_version: Optional[str]
    name: Optional[str]
    model: Optional[str]
    category_id: Optional[str]
    strict_unknown: bool
    timeout: float
    dry_run: bool
    log_level: str


class ApiError(RuntimeError):
    pass


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


def read_json(path: Optional[Path]) -> Optional[Any]:
    if not path:
        return None
    if not path.is_file():
        raise ApiError(f"文件不存在: {path}")
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


class ThingsBoardClient:
    def __init__(self, config: ToolConfig) -> None:
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

    def request(
            self,
            token: str,
            method: str,
            path: str,
            params: Optional[Dict[str, Any]] = None,
            payload: Any = None) -> Any:
        url = f"{self.product_api_base}{path}"
        if self.config.dry_run:
            print(f"[dry-run] {method} {url}")
            if params:
                print(f"[dry-run] params {json.dumps(params, ensure_ascii=False)}")
            if payload is not None:
                print(f"[dry-run] body {json.dumps(payload, ensure_ascii=False)}")
            return None
        response = self.session.request(
            method,
            url,
            headers=self._auth_headers(token),
            params=params,
            json=payload,
            timeout=self.config.timeout,
        )
        self._check(response)
        if response.content:
            return response.json()
        return None


def build_product_payload(config: ToolConfig) -> Dict[str, Any]:
    payload = read_json(config.config)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ApiError("--config 必须是 JSON 对象")
    if config.product_id:
        payload["productId"] = config.product_id
    if config.name:
        payload["name"] = config.name
    if config.model:
        payload["model"] = config.model
    if config.category_id:
        payload["categoryId"] = config.category_id
    if config.tsl_version:
        payload["tslVersion"] = config.tsl_version
    if config.strict_unknown:
        payload["strictUnknown"] = True
    tsl = read_json(config.tsl)
    if tsl is not None:
        payload["tsl"] = tsl
    return payload


def build_tsl_payload(config: ToolConfig) -> Dict[str, Any]:
    tsl = read_json(config.tsl)
    if tsl is None:
        raise ApiError("--tsl 为必填参数")
    payload: Dict[str, Any] = {"tsl": tsl}
    if config.tsl_version:
        payload["tslVersion"] = config.tsl_version
    if config.strict_unknown:
        payload["strictUnknown"] = True
    return payload


def run_action(client: ThingsBoardClient, token: str, config: ToolConfig) -> Any:
    action = config.action
    product_id = config.product_id

    if action == "list":
        params = {"pageSize": config.page_size, "page": config.page}
        if config.keyword:
            params["keyword"] = config.keyword
        return client.request(token, "GET", "", params=params)

    if not product_id and action in ("get", "update-tsl", "validate", "catalog", "delete"):
        raise ApiError(f"--action {action} 需要 --product-id")

    encoded = quote(product_id, safe="") if product_id else ""

    if action == "get":
        return client.request(token, "GET", f"/{encoded}")
    if action in ("create", "update"):
        return client.request(token, "POST", "", payload=build_product_payload(config))
    if action == "update-tsl":
        return client.request(
            token, "PUT", f"/{encoded}/thing-model", payload=build_tsl_payload(config))
    if action == "validate":
        return client.request(
            token, "POST", f"/{encoded}/thing-model/validate",
            payload=build_tsl_payload(config))
    if action == "catalog":
        return client.request(token, "GET", f"/{encoded}/catalog")
    if action == "delete":
        client.request(token, "DELETE", f"/{encoded}")
        return {"deleted": product_id}
    raise ApiError(f"不支持的 action: {action}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="产品增删改查与 TSL 管理示例。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    connection = parser.add_argument_group("连接")
    connection.add_argument(
        "--tb-url", default=DEFAULT_TB_URL, help="ThingsBoard 地址")
    connection.add_argument(
        "--thingmodel-url", default=DEFAULT_THINGMODEL_URL, help="thing-model 地址")
    connection.add_argument(
        "--timeout", type=float, default=30.0, help="HTTP 超时秒数")

    auth = parser.add_argument_group("认证")
    auth.add_argument("--api-key", default=None, help="ThingsBoard API Key")
    auth.add_argument(
        "--username", default="tenant@thingsboard.org", help="账号登录用户名")
    auth.add_argument("--password", default=None, help="账号登录密码；缺省时交互输入")

    action = parser.add_argument_group("操作")
    action.add_argument(
        "--action",
        required=True,
        choices=[
            "list", "get", "create", "update",
            "update-tsl", "validate", "catalog", "delete",
        ],
        help="要执行的操作",
    )
    action.add_argument("--product-id", default=None, help="产品 ID")
    action.add_argument("--keyword", default=None, help="列表搜索关键字")
    action.add_argument("--page-size", type=int, default=100, help="分页大小")
    action.add_argument("--page", type=int, default=0, help="页码，从 0 开始")
    action.add_argument("--config", default=None, help="创建/更新的 JSON 配置文件")
    action.add_argument("--tsl", default=None, help="TSL JSON 文件")
    action.add_argument("--tsl-version", default=None, help="TSL 版本")
    action.add_argument("--name", default=None, help="产品名称")
    action.add_argument("--model", default=None, help="产品型号")
    action.add_argument("--category-id", default=None, help="产品分类 ID")
    action.add_argument(
        "--strict-unknown", action="store_true", help="开启严格未知字段校验")

    output = parser.add_argument_group("输出")
    output.add_argument("--dry-run", action="store_true", help="只打印请求，不访问平台")
    output.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="日志级别")
    return parser


def config_from_args(args: argparse.Namespace) -> ToolConfig:
    return ToolConfig(
        tb_url=args.tb_url,
        thingmodel_url=args.thingmodel_url,
        api_key=args.api_key,
        username=args.username,
        password=args.password,
        action=args.action,
        product_id=args.product_id,
        keyword=args.keyword,
        page_size=args.page_size,
        page=args.page,
        config=Path(args.config) if args.config else None,
        tsl=Path(args.tsl) if args.tsl else None,
        tsl_version=args.tsl_version,
        name=args.name,
        model=args.model,
        category_id=args.category_id,
        strict_unknown=args.strict_unknown,
        timeout=args.timeout,
        dry_run=args.dry_run,
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
        if config.dry_run:
            token = "DRY_RUN"
        else:
            token = client.authenticate()
        result = run_action(client, token, config)
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        LOGGER.error("操作失败: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
