import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from app.agent.api_catalog import ApiCatalog
from app.agent.api_executor import ApiExecutor
from app.agent.dsh import DshAgentClient, format_dsh_input
from app.agent.executor import AgentActionExecutor
from app.agent.files import FileStore
from app.agent.llm import OpenAiChatClient
from app.agent.models import (
    AgentAction,
    AgentActionResult,
    AgentChatRequest,
    AgentChatResponse,
    AgentFile,
)
from app.agent.prompts import system_prompt_for_user
from app.agent.sessions import SessionStore
from app.agent.tool_gateway import AgentToolGateway
from app.agent.tools import (
    CATALOG_TOOL_SPECS,
    CATALOG_TOOLS,
    READ_TOOLS,
    TOOL_SPECS,
    TOOL_SUMMARIES,
    WRITE_TOOLS,
)
from app.auth.thingsboard import CurrentUser, ThingsBoardAuth
from app.clients.thing_model import ThingModelClient
from app.clients.thingsboard import ThingsBoardClient
from app.common.errors import AgentError, AgentUnavailable
from app.config import Settings

logger = logging.getLogger(__name__)
_TEXT_MIME_PREFIXES = ("text/",)
_TEXT_MIME_TYPES = {
    "application/json",
    "application/xml",
    "application/javascript",
    "application/yaml",
    "application/x-yaml",
}
_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".log",
    ".tsl",
}


def _is_text_file(mime_type: str, name: str) -> bool:
    mime = (mime_type or "").lower().split(";", 1)[0].strip()
    if mime.startswith(_TEXT_MIME_PREFIXES) or mime in _TEXT_MIME_TYPES:
        return True
    return Path(name).suffix.lower() in _TEXT_EXTENSIONS


class AgentService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._http = httpx.AsyncClient(timeout=settings.timeout_seconds)
        self._auth = ThingsBoardAuth(
            self._http,
            settings.thingsboard_url,
            settings.auth_cache_seconds,
        )
        thingsboard = ThingsBoardClient(
            self._http,
            settings.thingsboard_url,
            settings.api_max_response_bytes,
        )
        thing_model = ThingModelClient(
            self._http,
            settings.thing_model_url,
            settings.api_max_response_bytes,
        )
        self._thingsboard = thingsboard
        self._thing_model = thing_model
        self.api_catalog = ApiCatalog.load(settings.api_catalog_dir)
        self._api_executor = ApiExecutor(thingsboard, thing_model)
        self._executor = AgentActionExecutor(
            thingsboard,
            thing_model,
            self.api_catalog,
            self._api_executor,
        )
        self._llm = OpenAiChatClient(settings)
        self._sessions = SessionStore(settings.max_actions)
        self.file_store = FileStore(
            settings.file_ttl_seconds,
            settings.file_max_bytes,
        )
        self.tool_gateway = AgentToolGateway(
            self.api_catalog,
            self._api_executor,
            self._sessions,
        )
        self._dsh = DshAgentClient(settings) if settings.engine == "dsh" else None

    async def close(self) -> None:
        if self._dsh is not None:
            await self._dsh.close()
        await self._llm.close()
        await self._http.aclose()

    async def verify_token(self, token: str) -> CurrentUser:
        return await self._auth.verify(token)

    async def chat(
        self,
        request: AgentChatRequest,
        token: str,
        user: CurrentUser,
    ) -> AgentChatResponse:
        if not self._settings.enabled:
            raise AgentUnavailable("AI Agent 未启用")
        self._validate_request(request)

        if request.mode == "execute":
            return await self._execute_actions(request, token, user)

        if self._dsh is not None:
            return await self._chat_with_dsh(request, token, user)

        session = self._sessions.create(
            token,
            user,
            tsl=request.tsl,
            ttl_seconds=self._settings.timeout_seconds + 30,
        )
        try:
            messages = [{
                "role": "system",
                "content": system_prompt_for_user(
                    user.authority,
                    user.tenant_id,
                    request.tsl is not None,
                ),
            }]
            attachment_context = self._attachment_context(request.files, user)
            if attachment_context:
                messages.append({
                    "role": "system",
                    "content": attachment_context,
                })
            messages.extend(
                {"role": message.role, "content": message.content}
                for message in self._latest(
                    request.messages, self._settings.max_messages
                )
            )

            for _ in range(self._settings.max_tool_rounds):
                response = await self._llm.complete(
                    messages, TOOL_SPECS + CATALOG_TOOL_SPECS
                )
                if not response.choices:
                    raise AgentUnavailable("AI 模型没有返回结果")
                message = response.choices[0].message
                tool_calls = list(message.tool_calls or [])
                if not tool_calls:
                    actions = self._sessions.drain_proposals(session.session_id)
                    return AgentChatResponse(
                        reply=message.content or "",
                        actions=actions,
                    )

                read_calls = [
                    call for call in tool_calls if call.function.name in READ_TOOLS
                ]
                write_calls = [
                    call for call in tool_calls if call.function.name in WRITE_TOOLS
                ]
                catalog_calls = [
                    call for call in tool_calls if call.function.name in CATALOG_TOOLS
                ]

                if write_calls:
                    actions = [
                        self._tool_call_to_action(call)
                        for call in self._latest(
                            write_calls, self._settings.max_actions
                        )
                    ]
                    return AgentChatResponse(
                        reply=message.content or "已生成待确认操作，请确认后执行。",
                        actions=actions,
                    )

                if read_calls or catalog_calls:
                    messages.append(message.model_dump(exclude_none=True))
                    for call in read_calls:
                        result = await self._execute_read_tool(call, token, user)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": result.model_dump_json(),
                        })
                    for call in catalog_calls:
                        result = await self._execute_catalog_tool(
                            call, session.session_id
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                    actions = self._sessions.drain_proposals(session.session_id)
                    if actions:
                        return AgentChatResponse(
                            reply=message.content or "已生成待确认操作，请确认后执行。",
                            actions=actions,
                        )
                    continue

                return AgentChatResponse(reply=message.content or "")

            raise AgentError(
                "AI 规划步骤过多，请缩小查询范围后重试",
                status_code=502,
                code="AI_PLANNING_LIMIT",
            )
        finally:
            self._sessions.delete(session.session_id)

    async def _chat_with_dsh(
        self,
        request: AgentChatRequest,
        token: str,
        user: CurrentUser,
    ) -> AgentChatResponse:
        if self._dsh is None:
            raise AgentUnavailable("DSH 引擎未启用")

        session = self._sessions.create(
            token,
            user,
            tsl=request.tsl,
            ttl_seconds=self._settings.dsh_timeout_seconds + 30,
        )
        try:
            input_text = format_dsh_input(
                request.messages,
                user,
                tsl_attached=request.tsl is not None,
                max_messages=self._settings.max_messages,
                attachment_context=self._attachment_context(request.files, user),
            )
            result = await self._dsh.run(session.session_id, input_text)
            if result.finish_reason == "error":
                raise AgentUnavailable("AI 模型调用失败，请稍后重试")
            actions = self._sessions.drain_proposals(session.session_id)
            return AgentChatResponse(
                reply=result.final_response or "",
                actions=actions,
            )
        finally:
            self._sessions.delete(session.session_id)

    def _attachment_context(
        self,
        files: list[AgentFile],
        user: CurrentUser,
    ) -> str:
        if not files:
            return ""
        owner = user.user_id or user.email or "unknown"
        parts: list[str] = []
        for file in files:
            stored = self.file_store.get(file.id, owner)
            if stored is None:
                parts.append(f"[附件] {file.name}（文件不存在或已过期）")
                continue
            parts.append(
                f"[附件] name={stored.name}, type={stored.mime_type}, "
                f"size={len(stored.data)} bytes"
            )
            if _is_text_file(stored.mime_type, stored.name):
                text = stored.data.decode("utf-8", errors="replace")
                if len(text) > self._settings.file_text_max_bytes:
                    text = text[: self._settings.file_text_max_bytes] + "\n... [已截断]"
                parts.append(f"```\n{text}\n```")
        return "\n".join(parts)

    async def _execute_actions(
        self,
        request: AgentChatRequest,
        token: str,
        user: CurrentUser,
    ) -> AgentChatResponse:
        results: list[AgentActionResult] = []
        for action in self._latest(request.actions, self._settings.max_actions):
            result = await self._executor.execute(action, user, token, request.tsl)
            results.append(result)
        success_count = sum(1 for result in results if result.success)
        failed_count = len(results) - success_count
        if failed_count:
            reply = f"执行完成：{success_count} 个成功，{failed_count} 个失败。"
        else:
            reply = f"执行完成：{success_count} 个操作成功。"
        return AgentChatResponse(reply=reply, executed=results)

    async def _execute_read_tool(
        self,
        call,
        token: str,
        user: CurrentUser,
    ) -> AgentActionResult:
        action = self._tool_call_to_action(call)
        return await self._executor.execute(action, user, token, None)

    async def _execute_catalog_tool(self, call, session_id: str) -> dict[str, Any]:
        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            raise AgentError(
                f"AI 返回的工具参数不是合法 JSON: {call.function.name}",
                status_code=502,
                code="AI_INVALID_TOOL_CALL",
            ) from exc

        if call.function.name == "search_api_operations":
            return {
                "status": "OK",
                "results": self.tool_gateway.search(
                    str(args.get("query") or ""),
                    service=args.get("service"),
                    limit=int(args.get("limit") or 5),
                ),
            }

        if call.function.name == "call_api_operation":
            return await self.tool_gateway.call(
                session_id,
                str(args.get("operation_id") or ""),
                args.get("params") or {},
            )

        return {
            "status": "ERROR",
            "code": "UNKNOWN_TOOL",
            "message": f"不支持的工具: {call.function.name}",
        }

    def _tool_call_to_action(self, call) -> AgentAction:
        try:
            params = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            raise AgentError(
                f"AI 返回的工具参数不是合法 JSON: {call.function.name}",
                status_code=502,
                code="AI_INVALID_TOOL_CALL",
            ) from exc
        return AgentAction(
            id=call.id or uuid4().hex,
            type=call.function.name,
            summary=TOOL_SUMMARIES.get(call.function.name, call.function.name),
            params=params,
        )

    def _latest(self, items: list[Any], limit: int) -> list[Any]:
        if limit <= 0:
            return []
        return items[-limit:]

    def _validate_request(self, request: AgentChatRequest) -> None:
        if request.tsl is not None:
            try:
                size = len(json.dumps(request.tsl, ensure_ascii=False).encode("utf-8"))
            except TypeError as exc:
                raise AgentError("TSL 不是合法 JSON") from exc
            if size > self._settings.max_tsl_bytes:
                raise AgentError(
                    f"TSL 大小不能超过 {self._settings.max_tsl_bytes} 字节",
                    status_code=413,
                    code="TSL_TOO_LARGE",
                )
