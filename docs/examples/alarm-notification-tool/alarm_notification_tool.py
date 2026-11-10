#!/usr/bin/env python3
"""告警与通知工具示例。

通过 ThingsBoard REST API 查询/处理告警，并预览或发送通知请求。

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

LOGGER = logging.getLogger("alarm-notification-tool")

DEFAULT_TB_URL = "http://localhost:8080"


@dataclass
class ToolConfig:
    tb_url: str
    api_key: Optional[str]
    username: str
    password: Optional[str]
    action: str
    alarm_id: Optional[str]
    assignee_id: Optional[str]
    comment: Optional[str]
    payload: Optional[Path]
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


def run_action(client: ThingsBoardClient, token: str, config: ToolConfig) -> Any:
    action = config.action
    if action == "list-alarms":
        return client.request(
            token, "GET",
            f"{client.tb_url}/api/alarms?pageSize={config.page_size}&page={config.page}")
    if action == "list-targets":
        return client.request(
            token, "GET",
            f"{client.tb_url}/api/notification/targets"
            f"?pageSize={config.page_size}&page={config.page}")
    if action == "list-templates":
        return client.request(
            token, "GET",
            f"{client.tb_url}/api/notification/templates"
            f"?pageSize={config.page_size}&page={config.page}")
    if not config.alarm_id and action not in (
            "preview-notification", "send-notification"):
        raise ApiError(f"--action {action} 需要 --alarm-id")
    encoded = quote(config.alarm_id, safe="") if config.alarm_id else ""
    if action == "get-alarm":
        return client.request(token, "GET", f"{client.tb_url}/api/alarm/{encoded}")
    if action == "ack":
        return client.request(
            token, "POST", f"{client.tb_url}/api/alarm/{encoded}/ack")
    if action == "clear":
        return client.request(
            token, "POST", f"{client.tb_url}/api/alarm/{encoded}/clear")
    if action == "assign":
        if not config.assignee_id:
            raise ApiError("--assignee-id 为必填参数")
        url = (f"{client.tb_url}/api/alarm/{encoded}/assign/"
               f"{quote(config.assignee_id, safe='')}")
        client.request(token, "POST", url)
        return {"assigned": {"alarmId": config.alarm_id,
                             "assigneeId": config.assignee_id}}
    if action == "comment":
        if not config.comment:
            raise ApiError("--comment 为必填参数")
        return client.request(
            token, "POST", f"{client.tb_url}/api/alarm/{encoded}/comment",
            {"comment": {"text": config.comment}})
    if action in ("preview-notification", "send-notification"):
        payload = read_json(config.payload)
        if not isinstance(payload, dict):
            raise ApiError("--payload 必须是通知请求 JSON 文件")
        suffix = "/preview" if action == "preview-notification" else ""
        return client.request(
            token, "POST",
            f"{client.tb_url}/api/notification/request{suffix}",
            payload)
    raise ApiError(f"不支持的 action: {action}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="告警与通知工具示例。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    connection = parser.add_argument_group("连接")
    connection.add_argument("--tb-url", default=DEFAULT_TB_URL, help="ThingsBoard 地址")
    connection.add_argument("--timeout", type=float, default=30.0, help="HTTP 超时秒数")
    auth = parser.add_argument_group("认证")
    auth.add_argument("--api-key", default=None, help="ThingsBoard API Key")
    auth.add_argument(
        "--username", default="tenant@thingsboard.org", help="账号登录用户名")
    auth.add_argument("--password", default=None, help="密码；缺省时交互输入")
    action = parser.add_argument_group("操作")
    action.add_argument(
        "--action",
        required=True,
        choices=[
            "list-alarms", "get-alarm", "ack", "clear", "assign", "comment",
            "preview-notification", "send-notification",
            "list-targets", "list-templates",
        ],
        help="要执行的操作",
    )
    action.add_argument("--alarm-id", default=None, help="告警 ID")
    action.add_argument("--assignee-id", default=None, help="告警指派人用户 ID")
    action.add_argument("--comment", default=None, help="告警评论内容")
    action.add_argument("--payload", default=None, help="通知请求 JSON 文件")
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
        alarm_id=args.alarm_id,
        assignee_id=args.assignee_id,
        comment=args.comment,
        payload=Path(args.payload) if args.payload else None,
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
