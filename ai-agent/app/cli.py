from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import yaml
from pydantic import SecretStr

from app.agent.api_catalog import ApiCatalog, ServiceName
from app.agent.api_executor import ApiExecutor
from app.agent.dsh import DshAgentClient
from app.agent.sessions import SessionStore
from app.agent.tool_gateway import AgentToolGateway
from app.auth.thingsboard import CurrentUser, ThingsBoardAuth
from app.clients.thing_model import ThingModelClient
from app.clients.thingsboard import ThingsBoardClient
from app.common.errors import AgentError
from app.config import Settings
from scripts import import_openapi as openapi_importer

DEFAULT_URL = "http://127.0.0.1:8000"
_SECRET_MARKERS = ("key", "token", "secret", "password", "credential")


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    raw = list(sys.argv[1:] if argv is None else argv)
    known_commands = {"catalog", "chat", "dsh", "openapi", "config", "-h", "--help"}
    if not raw:
        raw = ["chat", "--interactive"]
    elif raw[0] not in known_commands and not raw[0].startswith("-"):
        raw = ["chat", *raw]
    args = build_parser().parse_args(raw)
    try:
        if args.command == "catalog":
            return _handle_catalog(args)
        if args.command == "chat":
            return asyncio.run(_handle_chat(args))
        if args.command == "dsh":
            return asyncio.run(_handle_dsh(args))
        if args.command == "openapi":
            return _handle_openapi(args)
        if args.command == "config":
            return _handle_config(args)
        raise ValueError(f"未知命令: {args.command}")
    except AgentError as exc:
        return _print_error(exc.code, exc.message, getattr(args, "json", False))
    except (httpx.HTTPError, OSError, ValueError, json.JSONDecodeError) as exc:
        return _print_error("CLI_ERROR", str(exc), getattr(args, "json", False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-agent-cli",
        description="ThingsBoard AI Agent 本地测试 CLI",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    catalog = commands.add_parser("catalog", help="API 目录测试")
    catalog_commands = catalog.add_subparsers(dest="catalog_command", required=True)

    validate = catalog_commands.add_parser("validate", help="校验 API 目录")
    _add_catalog_dir(validate)
    _add_json(validate)

    search = catalog_commands.add_parser("search", help="搜索 API")
    search.add_argument("query")
    search.add_argument("--service", choices=["thingsboard", "thing_model"])
    search.add_argument("--limit", type=int, default=5)
    _add_catalog_dir(search)
    _add_json(search)

    show = catalog_commands.add_parser("show", help="查看 API 详情")
    show.add_argument("operation_id")
    _add_catalog_dir(show)
    _add_json(show)

    call = catalog_commands.add_parser("call", help="测试单个 API，写操作只生成 PROPOSED")
    call.add_argument("operation_id")
    call.add_argument("--token", required=True)
    call.add_argument("--params", default="{}", help="JSON 字符串或 @文件")
    call.add_argument("--tsl", help="TSL JSON 文件")
    call.add_argument(
        "--authority",
        choices=["SYS_ADMIN", "TENANT_ADMIN", "CUSTOMER_USER"],
        help="本地测试用，跳过 ThingsBoard token 校验",
    )
    call.add_argument("--tenant-id")
    _add_catalog_dir(call)
    _add_json(call)

    chat = commands.add_parser("chat", help="调用运行中的 ai-agent，支持交互式聊天")
    chat.add_argument("message", nargs="?", help="单次消息；省略时进入交互模式")
    chat.add_argument("--token", help="ThingsBoard JWT；也可设置 AI_AGENT_CLI_TOKEN")
    chat.add_argument("--url", help="ai-agent 地址；也可设置 AI_AGENT_CLI_URL")
    chat.add_argument("--mode", choices=["chat", "execute"], default="chat")
    chat.add_argument("--tsl", help="TSL JSON 文件")
    chat.add_argument("--actions-file", help="execute 模式的动作 JSON 文件")
    chat.add_argument("-i", "--interactive", action="store_true", help="强制进入交互模式")
    chat.add_argument("-y", "--yes", action="store_true", help="自动确认并执行待确认动作")
    _add_json(chat)

    dsh = commands.add_parser("dsh", help="DSH runtime 测试")
    dsh_commands = dsh.add_subparsers(dest="dsh_command", required=True)
    smoke = dsh_commands.add_parser("smoke", help="启动 DSH runtime，验证 patch 和插件")
    smoke.add_argument("--message", help="可选，发送一条真实模型请求")
    smoke.add_argument("--api-key")
    smoke.add_argument("--internal-token")
    smoke.add_argument("--home")
    smoke.add_argument("--workspace")
    smoke.add_argument("--patch-template")
    smoke.add_argument("--plugin")
    smoke.add_argument("--profile")
    smoke.add_argument("--model")
    _add_json(smoke)

    openapi = commands.add_parser("openapi", help="OpenAPI 目录工具")
    openapi_commands = openapi.add_subparsers(dest="openapi_command", required=True)
    openapi_import = openapi_commands.add_parser("import", help="从 OpenAPI 生成目录")
    openapi_import.add_argument("--service", required=True, choices=["thingsboard", "thing_model"])
    openapi_import.add_argument("--spec", required=True)
    openapi_import.add_argument("--out", required=True)
    openapi_import.add_argument("--overrides")
    openapi_import.add_argument("--check", action="store_true")

    config = commands.add_parser("config", help="配置工具")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    show = config_commands.add_parser("show", help="查看脱敏配置")
    _add_json(show)

    return parser


def _handle_catalog(args: argparse.Namespace) -> int:
    settings = Settings()
    catalog = ApiCatalog.load(args.catalog_dir or settings.api_catalog_dir)

    if args.catalog_command == "validate":
        if not catalog.all():
            return _print_error("CATALOG_EMPTY", "API 目录为空", args.json)
        _print_json({"status": "ok", "operations": len(catalog.all())}, args.json)
        return 0

    if args.catalog_command == "search":
        results = [
            catalog.search_result(operation)
            for operation in catalog.search(
                args.query,
                service=args.service,
                limit=args.limit,
            )
        ]
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for item in results:
                print(
                    f"{item['id']}\t{item['mode']}\t{item['risk']}\t{item['summary']}"
                )
        return 0

    if args.catalog_command == "show":
        operation = catalog.get(args.operation_id)
        if operation is None:
            return _print_error("OPERATION_NOT_FOUND", "接口不存在", args.json)
        data = operation.model_dump(by_alias=True, exclude_none=True)
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
        return 0

    if args.catalog_command == "call":
        return asyncio.run(_handle_catalog_call(args, settings, catalog))

    raise ValueError(f"未知 catalog 命令: {args.catalog_command}")


async def _handle_catalog_call(
    args: argparse.Namespace,
    settings: Settings,
    catalog: ApiCatalog,
) -> int:
    params = _load_params(args.params)
    tsl = _load_json_file(args.tsl)
    thingsboard = None
    thing_model = None
    http = httpx.AsyncClient(timeout=settings.timeout_seconds)
    try:
        thingsboard = ThingsBoardClient(
            http,
            settings.thingsboard_url,
            settings.api_max_response_bytes,
        )
        thing_model = ThingModelClient(
            http,
            settings.thing_model_url,
            settings.api_max_response_bytes,
        )
        if args.authority:
            user = CurrentUser(
                user_id="cli-user",
                tenant_id=args.tenant_id,
                authority=args.authority,
            )
        else:
            auth = ThingsBoardAuth(
                http,
                settings.thingsboard_url,
                settings.auth_cache_seconds,
            )
            user = await auth.verify(args.token)

        sessions = SessionStore(settings.max_actions)
        gateway = AgentToolGateway(
            catalog,
            ApiExecutor(thingsboard, thing_model),
            sessions,
        )
        session = sessions.create(
            args.token,
            user,
            tsl=tsl,
            ttl_seconds=settings.timeout_seconds + 30,
        )
        result = await gateway.call(session.session_id, args.operation_id, params)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") in {"OK", "PROPOSED"} else 1
    finally:
        await http.aclose()


async def _handle_chat(args: argparse.Namespace) -> int:
    settings = Settings()
    token = args.token or os.getenv("AI_AGENT_CLI_TOKEN") or os.getenv("TB_TOKEN")
    if not token:
        raise ValueError("缺少 --token，或设置 AI_AGENT_CLI_TOKEN / TB_TOKEN")

    url = (args.url or os.getenv("AI_AGENT_CLI_URL") or DEFAULT_URL).rstrip("/")
    tsl = _load_json_file(args.tsl)

    if args.mode == "execute":
        if not args.actions_file:
            raise ValueError("execute 模式需要 --actions-file")
        actions = _load_json_file(args.actions_file)
        if not isinstance(actions, list):
            raise ValueError("actions 文件必须是 JSON 数组")
        data = await _post_chat(
            url,
            token,
            {"mode": "execute", "messages": [], "actions": actions, "tsl": tsl},
            settings.timeout_seconds,
        )
        _print_chat_response(data, args.json)
        return 0

    if args.message:
        return await _run_one_shot_chat(
            args,
            url,
            token,
            args.message,
            tsl,
            settings.timeout_seconds,
        )

    if args.interactive or sys.stdin.isatty():
        return await _run_interactive_chat(
            args,
            url,
            token,
            tsl,
            settings.timeout_seconds,
        )

    message = sys.stdin.read().strip()
    if not message:
        raise ValueError("标准输入为空")
    return await _run_one_shot_chat(
        args,
        url,
        token,
        message,
        tsl,
        settings.timeout_seconds,
    )


async def _run_one_shot_chat(
    args: argparse.Namespace,
    url: str,
    token: str,
    message: str,
    tsl: Any,
    timeout: float,
) -> int:
    data = await _post_chat(
        url,
        token,
        {
            "mode": "chat",
            "messages": [{"role": "user", "content": message}],
            "actions": [],
            "tsl": tsl,
        },
        timeout,
    )

    actions = data.get("actions") or []
    should_execute = bool(actions) and (
        args.yes or (not args.json and _confirm("检测到待确认动作，是否执行？[y/N] "))
    )
    if not should_execute:
        _print_chat_response(data, args.json)
        return 0

    executed = await _post_chat(
        url,
        token,
        {"mode": "execute", "messages": [], "actions": actions, "tsl": tsl},
        timeout,
    )
    if args.json:
        print(json.dumps({"chat": data, "execute": executed}, ensure_ascii=False, indent=2))
    else:
        _print_chat_response(data, False)
        _print_chat_response(executed, False)
    return 0


async def _run_interactive_chat(
    args: argparse.Namespace,
    url: str,
    token: str,
    tsl: Any,
    timeout: float,
) -> int:
    messages: list[dict[str, str]] = []
    print("AI Agent 命令行聊天。输入 /help 查看命令，/exit 退出。")
    while True:
        try:
            line = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line in {"/exit", "/quit"}:
            break
        if line in {"/clear", "/new"}:
            messages.clear()
            print("已清空当前对话。")
            continue
        if line == "/help":
            print("/clear 清空对话  /tsl <file> 设置 TSL  /exit 退出")
            continue
        if line.startswith("/tsl "):
            path = line.split(maxsplit=1)[1].strip()
            try:
                tsl = _load_json_file(path)
                print(f"已加载 TSL: {path}")
            except Exception as exc:
                print(f"加载 TSL 失败: {exc}")
            continue

        messages.append({"role": "user", "content": line})
        try:
            data = await _post_chat(
                url,
                token,
                {"mode": "chat", "messages": messages, "actions": [], "tsl": tsl},
                timeout,
            )
        except AgentError as exc:
            messages.pop()
            print(f"ERROR [{exc.code}] {exc.message}")
            continue

        reply = data.get("reply", "")
        _print_chat_response(data, args.json)
        actions = data.get("actions") or []
        if actions and (args.yes or _confirm("执行这些动作？[y/N] ")):
            try:
                executed = await _post_chat(
                    url,
                    token,
                    {"mode": "execute", "messages": [], "actions": actions, "tsl": tsl},
                    timeout,
                )
                _print_chat_response(executed, args.json)
            except AgentError as exc:
                print(f"ERROR [{exc.code}] {exc.message}")
        messages.append({"role": "assistant", "content": reply})
    return 0


async def _post_chat(
    url: str,
    token: str,
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{url}/chat",
            headers={"X-Authorization": f"Bearer {token}"},
            json=payload,
        )

    if response.status_code >= 400:
        try:
            body = response.json()
        except ValueError:
            body = {"message": response.text[:500]}
        raise AgentError(
            str(body.get("message") or "请求失败"),
            status_code=response.status_code,
            code=str(body.get("code") or f"HTTP_{response.status_code}"),
        )
    return response.json()


def _print_chat_response(data: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    reply = data.get("reply")
    if reply:
        print(f"AI> {reply}")
    for action in data.get("actions", []):
        print(
            f"[待确认] {action.get('type')} "
            f"risk={action.get('risk', 'low')} {action.get('summary', '')}"
        )
    for result in data.get("executed", []):
        print(
            f"[执行] {result.get('type')} "
            f"success={result.get('success')} {result.get('message', '')}"
        )


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in {"y", "yes"}
    except (EOFError, KeyboardInterrupt):
        print()
        return False


async def _handle_dsh(args: argparse.Namespace) -> int:
    settings = Settings()
    if args.api_key:
        settings.deepseek_api_key = SecretStr(args.api_key)
    if args.internal_token:
        settings.internal_tool_token = SecretStr(args.internal_token)
    if args.home:
        settings.dsh_home = args.home
    if args.workspace:
        settings.dsh_workspace = args.workspace
    if args.patch_template:
        settings.dsh_patch_template = args.patch_template
    if args.plugin:
        settings.dsh_plugin_path = args.plugin
    if args.profile:
        settings.dsh_profile = args.profile
    if args.model:
        settings.dsh_model = args.model

    client = DshAgentClient(settings)
    try:
        await client.start()
        if args.message:
            result = await client.run(f"cli-{uuid4().hex}", args.message)
            data = {
                "status": "ok",
                "profile": settings.dsh_profile,
                "model": settings.dsh_model,
                "reply": result.final_response,
                "finish_reason": result.finish_reason,
            }
        else:
            data = {
                "status": "ok",
                "profile": settings.dsh_profile,
                "model": settings.dsh_model,
                "message": "DSH runtime 启动成功",
            }
        _print_json(data, args.json)
        return 0
    finally:
        await client.close()


def _handle_openapi(args: argparse.Namespace) -> int:
    argv = ["--service", args.service, "--spec", args.spec, "--out", args.out]
    if args.overrides:
        argv.extend(["--overrides", args.overrides])
    if args.check:
        argv.append("--check")
    return openapi_importer.main(argv)


def _handle_config(args: argparse.Namespace) -> int:
    data = Settings().model_dump()
    for key, value in list(data.items()):
        if isinstance(value, SecretStr):
            data[key] = "***" if value.get_secret_value() else None
        elif any(marker in key.lower() for marker in _SECRET_MARKERS):
            data[key] = "***" if value else None
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    return 0


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _add_catalog_dir(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--catalog-dir", help="API 目录路径，默认读取 AI_AGENT_API_CATALOG_DIR")


def _add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="JSON 输出")


def _load_json_file(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_params(value: str) -> dict[str, Any]:
    raw = value
    if value.startswith("@"):
        raw = Path(value[1:]).read_text(encoding="utf-8")
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        raise ValueError("--params 必须是 JSON 对象")
    return data


def _print_json(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _print_error(code: str, message: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"code": code, "message": message}, ensure_ascii=False, indent=2))
    else:
        print(f"ERROR [{code}] {message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
