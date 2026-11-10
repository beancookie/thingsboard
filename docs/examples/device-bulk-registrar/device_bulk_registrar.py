#!/usr/bin/env python3
"""设备批量注册工具示例。

在 ThingsBoard 中为指定产品批量创建设备、获取 Access Token、写入服务端属性，
并可选把设备挂到网关设备下（Contains 关系）。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import csv
import getpass
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

LOGGER = logging.getLogger("device-bulk-registrar")

CSV_FIELDS = [
    "product_id",
    "device_name",
    "device_id",
    "access_token",
    "tsl_version",
    "profile_id",
    "site_code",
    "gateway",
    "status",
    "error",
    "created_at",
]


@dataclass
class RegistrarConfig:
    tb_url: str
    thingmodel_url: str
    api_key: Optional[str]
    username: str
    password: Optional[str]
    product_id: str
    profile_id: Optional[str]
    names: List[str]
    prefix: Optional[str]
    count: int
    start_index: int
    site_code: Optional[str]
    gateway: bool
    gateway_device: Optional[str]
    relation_type: str
    output_dir: Path
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_device_names(config: RegistrarConfig) -> List[str]:
    if config.names:
        if config.prefix or config.count:
            raise ApiError("--name 与 --prefix/--count 不能同时使用")
        names = list(config.names)
    else:
        if not config.prefix or config.count <= 0:
            raise ApiError("请使用 --name，或同时提供 --prefix 与 --count")
        base = config.prefix.rstrip("-")
        if not base:
            raise ApiError("--prefix 必须包含非连字符字符")
        width = max(4, len(str(config.start_index + config.count - 1)))
        names = [
            f"{base}-{config.start_index + index:0{width}d}"
            for index in range(config.count)
        ]
    if not names:
        raise ApiError("没有要注册的设备")
    if len(set(names)) != len(names):
        raise ApiError("设备名称存在重复")
    return names


def resolve_output_path(output_dir: Path) -> Path:
    path = output_dir / "device-credentials.csv"
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        path = output_dir / f"device-credentials-{stamp}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class ThingsBoardClient:
    def __init__(self, config: RegistrarConfig) -> None:
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

    def get_product(self, token: str, product_id: str) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.product_api_base}/{quote(product_id, safe='')}",
            headers=self._auth_headers(token),
            timeout=self.config.timeout,
        )
        self._check(response)
        return response.json() or {}

    def find_device_by_name(
            self, token: str, device_name: str) -> Optional[Dict[str, Any]]:
        response = self.session.get(
            f"{self.tb_url}/api/tenant/devices",
            params={"deviceName": device_name},
            headers=self._auth_headers(token),
            timeout=self.config.timeout,
        )
        if response.status_code == 404:
            return None
        self._check(response)
        return response.json() or None

    def create_device(
            self,
            token: str,
            profile_id: str,
            device_name: str,
            gateway: bool) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "name": device_name,
            "type": "default",
            "deviceProfileId": {
                "entityType": "DEVICE_PROFILE",
                "id": profile_id,
            },
        }
        if gateway:
            payload["additionalInfo"] = {"gateway": True}
        response = self.session.post(
            f"{self.tb_url}/api/device",
            headers=self._auth_headers(token),
            json=payload,
            timeout=self.config.timeout,
        )
        self._check(response)
        return response.json()

    def get_credentials(self, token: str, device_id: str) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.tb_url}/api/device/{device_id}/credentials",
            headers=self._auth_headers(token),
            timeout=self.config.timeout,
        )
        self._check(response)
        return response.json()

    def get_asset_attributes(
            self, token: str, asset_id: str) -> List[Dict[str, Any]]:
        response = self.session.get(
            f"{self.tb_url}/api/plugins/telemetry/"
            f"ASSET/{asset_id}/values/attributes/SERVER_SCOPE",
            headers=self._auth_headers(token),
            timeout=self.config.timeout,
        )
        self._check(response)
        return response.json() or []

    def set_server_attributes(
            self,
            token: str,
            device_id: str,
            attributes: Dict[str, Any]) -> None:
        response = self.session.post(
            f"{self.tb_url}/api/plugins/telemetry/"
            f"DEVICE/{device_id}/attributes/SERVER_SCOPE",
            headers=self._auth_headers(token),
            json=attributes,
            timeout=self.config.timeout,
        )
        self._check(response)

    def create_relation(
            self,
            token: str,
            from_id: str,
            to_id: str,
            relation_type: str) -> None:
        response = self.session.post(
            f"{self.tb_url}/api/relation",
            headers=self._auth_headers(token),
            json={
                "from": {"entityType": "DEVICE", "id": from_id},
                "to": {"entityType": "DEVICE", "id": to_id},
                "type": relation_type,
                "typeGroup": "COMMON",
            },
            timeout=self.config.timeout,
        )
        self._check(response)


def find_attribute(
        attributes: List[Dict[str, Any]], key: str) -> Optional[Any]:
    for item in attributes:
        if item.get("key") == key:
            return item.get("value")
    return None


def build_server_attributes(
        config: RegistrarConfig,
        device_id: str,
        product_id: str,
        tenant_id: Optional[str],
        tsl_version: Optional[str],
        tsl_schema: Optional[str]) -> Dict[str, Any]:
    attributes: Dict[str, Any] = {
        "product_id": product_id,
        "device_uuid": device_id,
    }
    if tenant_id:
        attributes["tenant_id"] = tenant_id
    if tsl_version:
        attributes["tsl_version"] = tsl_version
    if tsl_schema:
        attributes["tsl_schema"] = tsl_schema
    if config.site_code:
        attributes["site_code"] = config.site_code
    return attributes


def write_row(
        writer: csv.DictWriter,
        config: RegistrarConfig,
        device_name: str,
        device_id: str = "",
        access_token: str = "",
        tsl_version: str = "",
        profile_id: str = "",
        status: str = "",
        error: str = "") -> None:
    writer.writerow({
        "product_id": config.product_id,
        "device_name": device_name,
        "device_id": device_id,
        "access_token": access_token,
        "tsl_version": tsl_version,
        "profile_id": profile_id,
        "site_code": config.site_code or "",
        "gateway": "true" if config.gateway else "false",
        "status": status,
        "error": error,
        "created_at": now_iso(),
    })


def dry_run(config: RegistrarConfig, names: List[str]) -> int:
    profile_id = config.profile_id or "<PROFILE_ID>"
    for name in names:
        payload = {
            "name": name,
            "type": "default",
            "deviceProfileId": {
                "entityType": "DEVICE_PROFILE",
                "id": profile_id,
            },
        }
        if config.gateway:
            payload["additionalInfo"] = {"gateway": True}
        print(f"[dry-run] create {json.dumps(payload, ensure_ascii=False)}")
        attributes = build_server_attributes(
            config, "<DEVICE_ID>", config.product_id, None, None, None)
        print(
            "[dry-run] attributes "
            f"{json.dumps(attributes, ensure_ascii=False)}")
        if config.gateway_device:
            print(
                f"[dry-run] relation {config.gateway_device} "
                f"-{config.relation_type}-> {name}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="为指定产品批量注册 ThingsBoard 设备。",
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
        help="thing-model 地址",
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
        help="账号密码登录用户名",
    )
    auth.add_argument(
        "--password",
        default=None,
        help="账号密码登录密码；缺省时交互输入",
    )

    target = parser.add_argument_group("设备")
    target.add_argument(
        "--product-id",
        required=True,
        help="产品 ID",
    )
    target.add_argument(
        "--profile-id",
        default=None,
        help="设备配置 ID；缺省时从产品同步信息中读取",
    )
    target.add_argument(
        "--name",
        action="append",
        default=[],
        metavar="NAME",
        help="设备名称，可重复",
    )
    target.add_argument(
        "--prefix",
        default=None,
        help="批量设备名称前缀",
    )
    target.add_argument(
        "--count",
        type=int,
        default=0,
        help="批量设备数量",
    )
    target.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="批量起始序号",
    )
    target.add_argument(
        "--site-code",
        default=None,
        help="写入 site_code 服务端属性",
    )
    target.add_argument(
        "--gateway",
        action="store_true",
        help="把新设备标记为网关设备",
    )
    target.add_argument(
        "--gateway-device",
        default=None,
        help="将新设备挂到该网关设备下",
    )
    target.add_argument(
        "--relation-type",
        default="Contains",
        help="网关关系类型",
    )

    output = parser.add_argument_group("输出")
    output.add_argument(
        "--output-dir",
        default=".",
        help="CSV 输出目录",
    )
    output.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印计划，不访问平台",
    )
    output.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> RegistrarConfig:
    return RegistrarConfig(
        tb_url=args.tb_url,
        thingmodel_url=args.thingmodel_url,
        api_key=args.api_key,
        username=args.username,
        password=args.password,
        product_id=args.product_id.strip(),
        profile_id=args.profile_id,
        names=[name.strip() for name in args.name if name.strip()],
        prefix=args.prefix,
        count=args.count,
        start_index=args.start_index,
        site_code=args.site_code,
        gateway=args.gateway,
        gateway_device=args.gateway_device,
        relation_type=args.relation_type,
        output_dir=Path(args.output_dir),
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
    try:
        names = build_device_names(config)
    except ApiError as exc:
        parser.error(str(exc))

    if config.dry_run:
        return dry_run(config, names)

    client = ThingsBoardClient(config)
    try:
        token = client.authenticate()
        product_data = client.get_product(token, config.product_id)
    except Exception as exc:
        LOGGER.error("认证或查询产品失败: %s", exc)
        return 1

    product = product_data.get("product") or product_data
    profile_id = config.profile_id or product.get("tbProfileId")
    if not profile_id:
        LOGGER.error(
            "产品未同步或缺少 tbProfileId，请先完成产品同步或显式指定 --profile-id")
        return 1
    tenant_id = product.get("tenantId")
    tsl_version = product.get("tslVersion") or "1.0"
    asset_id = product.get("tbAssetId")
    tsl_schema = None
    if asset_id:
        try:
            attributes = client.get_asset_attributes(token, asset_id)
            tsl_schema = find_attribute(attributes, "tsl_schema")
        except Exception as exc:
            LOGGER.warning("读取产品资产属性失败: %s", exc)

    gateway_id = None
    if config.gateway_device:
        try:
            gateway = client.find_device_by_name(token, config.gateway_device)
            if not gateway:
                raise ApiError(
                    f"网关设备不存在: {config.gateway_device}")
            gateway_id = (gateway.get("id") or {}).get("id")
            if not gateway_id:
                raise ApiError("网关设备缺少 id")
        except Exception as exc:
            LOGGER.error("查询网关设备失败: %s", exc)
            return 1

    output_path = resolve_output_path(config.output_dir)
    created = 0
    skipped = 0
    failed = 0

    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for device_name in names:
            device_id = ""
            access_token = ""
            try:
                existing = client.find_device_by_name(token, device_name)
                if existing:
                    device_id = (existing.get("id") or {}).get("id", "")
                    write_row(
                        writer, config, device_name,
                        device_id=device_id,
                        tsl_version=tsl_version,
                        profile_id=profile_id,
                        status="skipped")
                    skipped += 1
                    LOGGER.info("已存在，跳过 %s (%s)", device_name, device_id)
                    continue

                device = client.create_device(
                    token, profile_id, device_name, config.gateway)
                device_id = (device.get("id") or {}).get("id", "")
                if not device_id:
                    raise ApiError("平台未返回设备 ID")

                credentials = client.get_credentials(token, device_id)
                access_token = credentials.get("credentialsId") or ""
                if not access_token:
                    raise ApiError("平台未返回设备 Access Token")

                attributes = build_server_attributes(
                    config, device_id, config.product_id, tenant_id,
                    tsl_version, tsl_schema)
                client.set_server_attributes(token, device_id, attributes)

                if gateway_id:
                    client.create_relation(
                        token, gateway_id, device_id, config.relation_type)

                write_row(
                    writer, config, device_name,
                    device_id=device_id,
                    access_token=access_token,
                    tsl_version=tsl_version,
                    profile_id=profile_id,
                    status="created")
                created += 1
                LOGGER.info("已创建设备 %s (%s)", device_name, device_id)
            except Exception as exc:
                write_row(
                    writer, config, device_name,
                    device_id=device_id,
                    access_token=access_token,
                    tsl_version=tsl_version,
                    profile_id=profile_id,
                    status="failed",
                    error=str(exc))
                failed += 1
                LOGGER.error("创建设备失败 %s: %s", device_name, exc)

    LOGGER.info(
        "汇总 created=%s skipped=%s failed=%s output=%s",
        created, skipped, failed, output_path)
    print(f"csv: {output_path}")
    print("warning: CSV 包含设备 Access Token，请妥善保管")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
