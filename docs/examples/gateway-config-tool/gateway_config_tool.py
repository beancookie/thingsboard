#!/usr/bin/env python3
"""网关与子设备配置工具示例。

通过 ThingsBoard REST API 创建网关/子设备、建立 Contains 关系、查询在线状态
并写入网关 general_configuration 配置。

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
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

LOGGER = logging.getLogger("gateway-config-tool")

DEFAULT_TB_URL = "http://localhost:8080"
STATUS_KEYS = "active,lastConnectTime,lastDisconnectTime"
CONFIG_KEYS = "general_configuration,active_connectors,inactive_connectors"


@dataclass
class ToolConfig:
    tb_url: str
    api_key: Optional[str]
    username: str
    password: Optional[str]
    action: str
    gateway_name: Optional[str]
    gateway_id: Optional[str]
    sub_device_name: Optional[str]
    profile_id: Optional[str]
    relation_type: str
    config: Optional[Path]
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
        self.session = requests.Session()

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
        url = f"{self.tb_url}{path}"
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

    def find_device_by_name(
            self, token: str, name: str) -> Optional[Dict[str, Any]]:
        response = self.session.get(
            f"{self.tb_url}/api/tenant/devices",
            params={"deviceName": name},
            headers=self._auth_headers(token),
            timeout=self.config.timeout,
        )
        if response.status_code == 404:
            return None
        self._check(response)
        return response.json() or None

    def resolve_gateway(self, token: str) -> Dict[str, Any]:
        if self.config.gateway_id:
            if self.config.dry_run:
                return {"id": {"id": "<GATEWAY_ID>"}, "name": self.config.gateway_name or "<GATEWAY>"}
            return self.request(token, "GET", f"/api/device/{self.config.gateway_id}")
        name = self.config.gateway_name
        if not name:
            raise ApiError("请提供 --gateway-name 或 --gateway-id")
        if self.config.dry_run:
            return {"id": {"id": "<GATEWAY_ID>"}, "name": name}
        gateway = self.find_device_by_name(token, name)
        if not gateway:
            raise ApiError(f"网关设备不存在: {name}")
        return gateway


def build_device_payload(
        config: ToolConfig, name: str, gateway: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"name": name, "type": "default"}
    if config.profile_id:
        payload["deviceProfileId"] = {
            "entityType": "DEVICE_PROFILE",
            "id": config.profile_id,
        }
    if gateway:
        payload["additionalInfo"] = {"gateway": True}
    return payload


def run_action(client: ThingsBoardClient, token: str, config: ToolConfig) -> Any:
    action = config.action

    if action == "list":
        if config.dry_run:
            return client.request(
                token, "GET", "/api/tenant/devices",
                params={"pageSize": 100, "page": 0})
        devices = client.request(
            token, "GET", "/api/tenant/devices",
            params={"pageSize": 100, "page": 0}) or {}
        rows: List[Dict[str, Any]] = []
        for device in devices.get("data", []):
            additional = device.get("additionalInfo") or {}
            if additional.get("gateway"):
                rows.append({
                    "id": (device.get("id") or {}).get("id"),
                    "name": device.get("name"),
                    "createdTime": device.get("createdTime"),
                })
        return rows

    if action == "create-gateway":
        if not config.gateway_name:
            raise ApiError("--gateway-name 为必填参数")
        payload = build_device_payload(config, config.gateway_name, True)
        return client.request(token, "POST", "/api/device", payload=payload)

    if action == "create-sub-device":
        if not config.sub_device_name:
            raise ApiError("--sub-device-name 为必填参数")
        payload = build_device_payload(config, config.sub_device_name, False)
        return client.request(token, "POST", "/api/device", payload=payload)

    gateway = client.resolve_gateway(token)
    gateway_id = ((gateway or {}).get("id") or {}).get("id")
    if not gateway_id:
        raise ApiError("未找到网关设备 ID")
    encoded_gateway = quote(gateway_id, safe="")

    if action == "status":
        return client.request(
            token, "GET",
            f"/api/plugins/telemetry/DEVICE/{encoded_gateway}/values/attributes",
            params={"keys": STATUS_KEYS})

    if action == "get-config":
        return client.request(
            token, "GET",
            f"/api/plugins/telemetry/DEVICE/{encoded_gateway}/values/attributes",
            params={"keys": CONFIG_KEYS})

    if action == "set-config":
        config_payload = read_json(config.config)
        if config_payload is None:
            raise ApiError("--config 为必填参数")
        if isinstance(config_payload, dict) and "general_configuration" in config_payload:
            body = {"general_configuration": config_payload["general_configuration"]}
        else:
            body = {"general_configuration": config_payload}
        return client.request(
            token, "POST",
            f"/api/plugins/telemetry/DEVICE/{encoded_gateway}/attributes/SHARED_SCOPE",
            payload=body)

    if action == "bind":
        if not config.sub_device_name:
            raise ApiError("--sub-device-name 为必填参数")
        if config.dry_run:
            sub_device_id = "<SUB_DEVICE_ID>"
        else:
            sub_device = client.find_device_by_name(token, config.sub_device_name)
            if not sub_device:
                raise ApiError(f"子设备不存在: {config.sub_device_name}")
            sub_device_id = ((sub_device.get("id") or {}).get("id"))
            if not sub_device_id:
                raise ApiError("未找到子设备 ID")
        return client.request(
            token, "POST", "/api/relation",
            payload={
                "from": {"entityType": "DEVICE", "id": gateway_id},
                "to": {"entityType": "DEVICE", "id": sub_device_id},
                "type": config.relation_type,
                "typeGroup": "COMMON",
            })

    raise ApiError(f"不支持的 action: {action}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="网关与子设备配置示例。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    connection = parser.add_argument_group("连接")
    connection.add_argument(
        "--tb-url", default=DEFAULT_TB_URL, help="ThingsBoard 地址")
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
            "create-gateway", "create-sub-device", "bind",
            "list", "status", "set-config", "get-config",
        ],
        help="要执行的操作",
    )
    action.add_argument("--gateway-name", default=None, help="网关设备名称")
    action.add_argument("--gateway-id", default=None, help="网关设备 ID")
    action.add_argument("--sub-device-name", default=None, help="子设备名称")
    action.add_argument("--profile-id", default=None, help="设备配置 ID")
    action.add_argument(
        "--relation-type", default="Contains", help="网关到子设备的关系类型")
    action.add_argument("--config", default=None, help="general_configuration JSON 文件")

    output = parser.add_argument_group("输出")
    output.add_argument("--dry-run", action="store_true", help="只打印请求，不访问平台")
    output.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="日志级别")
    return parser


def config_from_args(args: argparse.Namespace) -> ToolConfig:
    return ToolConfig(
        tb_url=args.tb_url,
        api_key=args.api_key,
        username=args.username,
        password=args.password,
        action=args.action,
        gateway_name=args.gateway_name,
        gateway_id=args.gateway_id,
        sub_device_name=args.sub_device_name,
        profile_id=args.profile_id,
        relation_type=args.relation_type,
        config=Path(args.config) if args.config else None,
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
        token = "DRY_RUN" if config.dry_run else client.authenticate()
        result = run_action(client, token, config)
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        LOGGER.error("操作失败: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
