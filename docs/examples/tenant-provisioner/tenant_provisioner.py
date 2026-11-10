#!/usr/bin/env python3
"""租户初始化工具示例。

通过 ThingsBoard REST API 创建租户、租户管理员，并初始化平台服务账号。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import getpass
import json
import logging
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

LOGGER = logging.getLogger("tenant-provisioner")

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
    tenant_id: Optional[str]
    tenant_name: Optional[str]
    profile_id: Optional[str]
    email: Optional[str]
    first_name: str
    last_name: str
    country: Optional[str]
    city: Optional[str]
    phone: Optional[str]
    description: Optional[str]
    send_activation_mail: bool
    show_activation_link: bool
    force: bool
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


class ThingsBoardClient:
    def __init__(self, config: ToolConfig) -> None:
        self.config = config
        self.tb_url = config.tb_url.rstrip("/")
        self.thingmodel_url = config.thingmodel_url.rstrip("/")
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
            return {"X-Authorization": f"ApiKey {value[len('ApiKey '):].strip()}"}
        if lower.startswith("bearer "):
            return {"X-Authorization": f"Bearer {value[len('Bearer '):].strip()}"}
        if value.startswith("tb_"):
            return {"X-Authorization": f"ApiKey {value}"}
        return {"X-Authorization": f"Bearer {value}"}

    def _check(self, response: requests.Response) -> None:
        if response.status_code >= 400:
            raise ApiError(
                f"HTTP {response.status_code} {response.url}: {response.text[:500]}")

    def request(
            self,
            token: str,
            method: str,
            url: str,
            payload: Any = None) -> Any:
        if self.config.dry_run:
            print(f"[dry-run] {method} {url}")
            if payload is not None:
                print(f"[dry-run] body {json.dumps(payload, ensure_ascii=False)}")
            return None
        response = self.session.request(
            method,
            url,
            headers=self._auth_headers(token),
            json=payload,
            timeout=self.config.timeout,
        )
        self._check(response)
        return response.json() if response.content else None

    def default_profile_id(self, token: str) -> str:
        data = self.request(token, "GET", f"{self.tb_url}/api/tenantProfileInfo/default")
        profile = (data or {}).get("id") or {}
        profile_id = profile.get("id")
        if not profile_id:
            raise ApiError("未获取到默认租户配置 ID")
        return profile_id

    def thingmodel_admin_base(self) -> str:
        base = self.thingmodel_url
        if base.endswith("/api/thing-model"):
            return base
        return f"{base}/api/thing-model"


def tenant_payload(config: ToolConfig, profile_id: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "title": config.tenant_name,
        "tenantProfileId": {
            "entityType": "TENANT_PROFILE",
            "id": profile_id,
        },
    }
    for key in ("email", "country", "city", "phone", "description"):
        value = getattr(config, key)
        if value:
            payload[key] = value
    return payload


def user_payload(config: ToolConfig) -> Dict[str, Any]:
    return {
        "tenantId": {"entityType": "TENANT", "id": config.tenant_id},
        "email": config.email,
        "firstName": config.first_name,
        "lastName": config.last_name,
        "authority": "TENANT_ADMIN",
    }


def run_action(client: ThingsBoardClient, token: str, config: ToolConfig) -> Any:
    action = config.action
    if action == "list":
        return client.request(
            token, "GET",
            f"{client.tb_url}/api/tenants?pageSize=100&page=0")
    if action == "get":
        if not config.tenant_id:
            raise ApiError("--tenant-id 为必填参数")
        return client.request(
            token, "GET",
            f"{client.tb_url}/api/tenant/{quote(config.tenant_id, safe='')}")
    if action == "create":
        if not config.tenant_name:
            raise ApiError("--tenant-name 为必填参数")
        profile_id = config.profile_id
        if not profile_id:
            profile_id = "<TENANT_PROFILE_ID>" if config.dry_run else client.default_profile_id(token)
        payload = tenant_payload(config, profile_id)
        return client.request(token, "POST", f"{client.tb_url}/api/tenant", payload)
    if action == "create-admin":
        if not config.tenant_id or not config.email:
            raise ApiError("--tenant-id 和 --email 为必填参数")
        url = (f"{client.tb_url}/api/user?sendActivationMail="
               f"{str(config.send_activation_mail).lower()}")
        result = client.request(token, "POST", url, user_payload(config))
        if config.show_activation_link and result:
            user_id = ((result.get("id") or {}).get("id"))
            if user_id:
                result["activationLink"] = client.request(
                    token, "GET",
                    f"{client.tb_url}/api/user/{user_id}/activationLink")
        return result
    if action == "provision":
        if not config.tenant_id:
            raise ApiError("--tenant-id 为必填参数")
        url = (f"{client.thingmodel_admin_base()}/admin/tenants/"
               f"{quote(config.tenant_id, safe='')}/provision-auto"
               f"?force={str(config.force).lower()}")
        return client.request(token, "POST", url)
    if action == "delete":
        if not config.tenant_id:
            raise ApiError("--tenant-id 为必填参数")
        client.request(
            token, "DELETE",
            f"{client.tb_url}/api/tenant/{quote(config.tenant_id, safe='')}")
        return {"deleted": config.tenant_id}
    raise ApiError(f"不支持的 action: {action}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="租户初始化示例：创建租户、管理员并初始化平台服务账号。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    connection = parser.add_argument_group("连接")
    connection.add_argument("--tb-url", default=DEFAULT_TB_URL, help="ThingsBoard 地址")
    connection.add_argument(
        "--thingmodel-url", default=DEFAULT_THINGMODEL_URL, help="thing-model 地址")
    connection.add_argument("--timeout", type=float, default=30.0, help="HTTP 超时秒数")
    auth = parser.add_argument_group("认证")
    auth.add_argument("--api-key", default=None, help="ThingsBoard API Key")
    auth.add_argument(
        "--username", default="sysadmin@thingsboard.org", help="系统管理员用户名")
    auth.add_argument("--password", default=None, help="密码；缺省时交互输入")
    action = parser.add_argument_group("操作")
    action.add_argument(
        "--action",
        required=True,
        choices=["list", "get", "create", "create-admin", "provision", "delete"],
        help="要执行的操作",
    )
    action.add_argument("--tenant-id", default=None, help="租户 ID")
    action.add_argument("--tenant-name", default=None, help="租户名称")
    action.add_argument("--profile-id", default=None, help="租户配置 ID")
    action.add_argument("--email", default=None, help="租户管理员邮箱")
    action.add_argument("--first-name", default="Tenant", help="管理员名")
    action.add_argument("--last-name", default="Admin", help="管理员姓")
    action.add_argument("--country", default=None, help="国家")
    action.add_argument("--city", default=None, help="城市")
    action.add_argument("--phone", default=None, help="电话")
    action.add_argument("--description", default=None, help="描述")
    action.add_argument(
        "--send-activation-mail", action="store_true", help="创建管理员时发送激活邮件")
    action.add_argument(
        "--show-activation-link", action="store_true", help="创建管理员后输出激活链接")
    action.add_argument("--force", action="store_true", help="强制重新初始化服务账号")
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
        tenant_id=args.tenant_id,
        tenant_name=args.tenant_name,
        profile_id=args.profile_id,
        email=args.email,
        first_name=args.first_name,
        last_name=args.last_name,
        country=args.country,
        city=args.city,
        phone=args.phone,
        description=args.description,
        send_activation_mail=args.send_activation_mail,
        show_activation_link=args.show_activation_link,
        force=args.force,
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
