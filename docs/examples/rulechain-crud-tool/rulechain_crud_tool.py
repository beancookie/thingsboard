#!/usr/bin/env python3
"""规则链增删改查与导入导出示例。

通过 ThingsBoard REST API 管理规则链：查询、创建、更新、删除、设为根规则链、
读写节点元数据，以及导出/导入规则链 JSON。

本示例只使用命令行参数配置，不读取环境变量，不内置任何密钥。
"""
from __future__ import annotations

import argparse
import copy
import getpass
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

LOGGER = logging.getLogger("rulechain-crud-tool")

DEFAULT_TB_URL = "http://localhost:8080"


@dataclass
class ToolConfig:
    tb_url: str
    api_key: Optional[str]
    username: str
    password: Optional[str]
    action: str
    rule_chain_id: Optional[str]
    name: Optional[str]
    description: Optional[str]
    debug_mode: bool
    rule_chain_type: str
    input: Optional[Path]
    output: Optional[Path]
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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


def require_rule_chain_id(config: ToolConfig) -> str:
    if not config.rule_chain_id:
        raise ApiError(f"--action {config.action} 需要 --rule-chain-id")
    return quote(config.rule_chain_id, safe="")


def build_rule_chain_payload(config: ToolConfig) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": config.name,
        "type": config.rule_chain_type,
        "debugMode": config.debug_mode,
    }
    if config.description:
        payload["additionalInfo"] = {"description": config.description}
    return payload


def sanitize_rule_chain(rule_chain: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(rule_chain)
    for key in ("id", "createdTime", "tenantId", "version"):
        result.pop(key, None)
    return result


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(metadata)
    result.pop("ruleChainId", None)
    for node in result.get("nodes") or []:
        if isinstance(node, dict):
            node.pop("id", None)
    return result


def export_rule_chain(
        client: ThingsBoardClient, token: str, config: ToolConfig) -> Dict[str, Any]:
    encoded = require_rule_chain_id(config)
    rule_chain = client.request(token, "GET", f"/api/ruleChain/{encoded}")
    metadata = client.request(token, "GET", f"/api/ruleChain/{encoded}/metadata")
    bundle = {"ruleChain": rule_chain, "metadata": metadata}
    output = config.output or Path(f"{config.rule_chain_id}.rule-chain.json")
    if not config.dry_run:
        write_json(output, bundle)
        LOGGER.info("已导出规则链到 %s", output)
    else:
        print(f"[dry-run] write {output}")
    return bundle


def import_rule_chain(
        client: ThingsBoardClient, token: str, config: ToolConfig) -> Dict[str, Any]:
    bundle = read_json(config.input)
    if not isinstance(bundle, dict) or "ruleChain" not in bundle:
        raise ApiError("--input 必须包含 ruleChain 和 metadata")
    rule_chain = sanitize_rule_chain(bundle["ruleChain"])
    if config.name:
        rule_chain["name"] = config.name
    if config.debug_mode:
        rule_chain["debugMode"] = True

    if config.dry_run:
        print("[dry-run] ruleChain")
        print(json.dumps(rule_chain, ensure_ascii=False))
        print("[dry-run] metadata")
        print(json.dumps(bundle.get("metadata") or {}, ensure_ascii=False))
        return {"imported": False}

    saved = client.request(token, "POST", "/api/ruleChain", payload=rule_chain)
    saved_id = saved.get("id") if isinstance(saved, dict) else None
    if not saved_id:
        raise ApiError("规则链创建后未返回 id")
    metadata = sanitize_metadata(bundle.get("metadata") or {})
    metadata["ruleChainId"] = saved_id
    client.request(token, "POST", "/api/ruleChain/metadata", payload=metadata)
    return {"ruleChainId": saved_id.get("id"), "name": saved.get("name")}


def run_action(client: ThingsBoardClient, token: str, config: ToolConfig) -> Any:
    action = config.action

    if action == "list":
        return client.request(
            token, "GET", "/api/ruleChains",
            params={
                "pageSize": config.page_size,
                "page": config.page,
                "type": config.rule_chain_type,
            })

    if action == "create":
        if not config.name:
            raise ApiError("--name 为必填参数")
        return client.request(
            token, "POST", "/api/ruleChain",
            payload=build_rule_chain_payload(config))

    if action == "export":
        return export_rule_chain(client, token, config)

    if action == "import":
        return import_rule_chain(client, token, config)

    encoded = require_rule_chain_id(config)

    if action == "get":
        return client.request(token, "GET", f"/api/ruleChain/{encoded}")
    if action == "update":
        current = client.request(token, "GET", f"/api/ruleChain/{encoded}")
        if not isinstance(current, dict):
            current = {}
        if config.name:
            current["name"] = config.name
        if config.description:
            additional = current.get("additionalInfo")
            if not isinstance(additional, dict):
                additional = {}
            additional["description"] = config.description
            current["additionalInfo"] = additional
        if config.debug_mode:
            current["debugMode"] = True
        return client.request(token, "POST", "/api/ruleChain", payload=current)
    if action == "delete":
        client.request(token, "DELETE", f"/api/ruleChain/{encoded}")
        return {"deleted": config.rule_chain_id}
    if action == "set-root":
        return client.request(token, "POST", f"/api/ruleChain/{encoded}/root")
    if action == "metadata":
        if config.input:
            metadata = read_json(config.input) or {}
            if "ruleChainId" not in metadata:
                metadata["ruleChainId"] = {
                    "entityType": "RULE_CHAIN",
                    "id": config.rule_chain_id,
                }
            return client.request(
                token, "POST", "/api/ruleChain/metadata", payload=metadata)
        return client.request(token, "GET", f"/api/ruleChain/{encoded}/metadata")
    raise ApiError(f"不支持的 action: {action}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="规则链增删改查与导入导出示例。",
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
            "list", "get", "create", "update", "delete",
            "set-root", "metadata", "export", "import",
        ],
        help="要执行的操作",
    )
    action.add_argument("--rule-chain-id", default=None, help="规则链 ID")
    action.add_argument("--name", default=None, help="规则链名称")
    action.add_argument("--description", default=None, help="规则链描述")
    action.add_argument("--debug-mode", action="store_true", help="开启调试模式")
    action.add_argument(
        "--rule-chain-type", default="CORE",
        choices=["CORE", "EDGE"], help="规则链类型")
    action.add_argument("--input", default=None, help="导入或元数据 JSON 文件")
    action.add_argument("--output", default=None, help="导出 JSON 文件路径")
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
        rule_chain_id=args.rule_chain_id,
        name=args.name,
        description=args.description,
        debug_mode=args.debug_mode,
        rule_chain_type=args.rule_chain_type,
        input=Path(args.input) if args.input else None,
        output=Path(args.output) if args.output else None,
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
