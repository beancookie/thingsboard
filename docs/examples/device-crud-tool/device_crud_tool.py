#!/usr/bin/env python3
"""设备增删改查工具示例。

通过 ThingsBoard REST API 完成设备查询、创建、更新、删除和凭证查询。

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

LOGGER = logging.getLogger("device-crud-tool")

DEFAULT_TB_URL = "http://localhost:8080"


@dataclass
class ToolConfig:
    tb_url: str
    api_key: Optional[str]
    username: str
    password: Optional[str]
    action: str
    device_id: Optional[str]
    device_name: Optional[str]
    name: Optional[str]
    profile_id: Optional[str]
    label: Optional[str]
    gateway: bool
    description: Optional[str]
    config: Optional[Path]
    page_size: int
    page: int
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

    def resolve_device(self, token: str) -> Optional[Dict[str, Any]]:
        if self.config.device_id:
            if self.config.dry_run:
                return {"id": {"id": "<DEVICE_ID>"}, "name": self.config.device_name or "<DEVICE>"}
            return self.request(token, "GET", f"/api/device/{self.config.device_id}")
        name = self.config.device_name
        if not name:
            raise ApiError("请提供 --device-id 或 --device-name")
        if self.config.dry_run:
            return {"id": {"id": "<DEVICE_ID>"}, "name": name}
        device = self.find_device_by_name(token, name)
        if not device:
            raise ApiError(f"设备不存在: {name}")
        return device


def build_create_payload(config: ToolConfig) -> Dict[str, Any]:
    payload = read_json(config.config)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ApiError("--config 必须是 JSON 对象")
    if config.name:
        payload["name"] = config.name
    if config.profile_id:
        payload["deviceProfileId"] = {
            "entityType": "DEVICE_PROFILE",
            "id": config.profile_id,
        }
    if config.label:
        payload["label"] = config.label
    if config.gateway or config.description:
        additional = payload.get("additionalInfo")
        if not isinstance(additional, dict):
            additional = {}
        if config.gateway:
            additional["gateway"] = True
        if config.description:
            additional["description"] = config.description
        payload["additionalInfo"] = additional
    return payload


def run_action(client: ThingsBoardClient, token: str, config: ToolConfig) -> Any:
    action = config.action

    if action == "list":
        return client.request(
            token, "GET", "/api/tenant/devices",
            params={"pageSize": config.page_size, "page": config.page})

    if action == "create":
        payload = build_create_payload(config)
        if not payload.get("name"):
            raise ApiError("创建设备需要 --name 或 --config 中的 name")
        return client.request(token, "POST", "/api/device", payload=payload)

    device = client.resolve_device(token)
    device_id = ((device or {}).get("id") or {}).get("id") if device else None
    if not device_id:
        raise ApiError("未找到设备 ID")
    encoded = quote(device_id, safe="")

    if action == "get":
        return client.request(token, "GET", f"/api/device/{encoded}")
    if action == "update":
        current = device if config.dry_run else client.request(
            token, "GET", f"/api/device/{encoded}")
        overrides = read_json(config.config)
        if overrides is None:
            overrides = {}
        if not isinstance(overrides, dict):
            raise ApiError("--config 必须是 JSON 对象")
        if config.name:
            overrides["name"] = config.name
        if config.label:
            overrides["label"] = config.label
        if config.description:
            additional = overrides.get("additionalInfo")
            if not isinstance(additional, dict):
                additional = current.get("additionalInfo") or {}
            additional["description"] = config.description
            overrides["additionalInfo"] = additional
        payload = {**(current or {}), **overrides}
        return client.request(token, "POST", "/api/device", payload=payload)
    if action == "delete":
        client.request(token, "DELETE", f"/api/device/{encoded}")
        return {"deleted": device_id}
    if action == "credentials":
        return client.request(token, "GET", f"/api/device/{encoded}/credentials")
    raise ApiError(f"不支持的 action: {action}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="设备增删改查示例。",
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
        choices=["list", "get", "create", "update", "delete", "credentials"],
        help="要执行的操作",
    )
    action.add_argument("--device-id", default=None, help="设备 ID")
    action.add_argument("--device-name", default=None, help="设备名称，用于查询/更新/删除")
    action.add_argument("--name", default=None, help="创建设备时使用的名称")
    action.add_argument("--profile-id", default=None, help="设备配置 ID")
    action.add_argument("--label", default=None, help="设备标签")
    action.add_argument("--gateway", action="store_true", help="标记为网关设备")
    action.add_argument("--description", default=None, help="设备描述")
    action.add_argument("--config", default=None, help="创建/更新的 JSON 配置文件")
    action.add_argument("--page-size", type=int, default=100, help="分页大小")
    action.add_argument("--page", type=int, default=0, help="页码，从 0 开始")

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
        device_id=args.device_id,
        device_name=args.device_name,
        name=args.name,
        profile_id=args.profile_id,
        label=args.label,
        gateway=args.gateway,
        description=args.description,
        config=Path(args.config) if args.config else None,
        page_size=args.page_size,
        page=args.page,
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
