import json
import logging
from typing import Any
from uuid import uuid4

import httpx

from app.agent.executor import AgentActionExecutor
from app.agent.llm import OpenAiChatClient
from app.agent.models import (
    AgentAction,
    AgentActionResult,
    AgentChatRequest,
    AgentChatResponse,
)
from app.agent.prompts import system_prompt_for_user
from app.agent.tools import READ_TOOLS, TOOL_SPECS, TOOL_SUMMARIES, WRITE_TOOLS
from app.auth.thingsboard import CurrentUser, ThingsBoardAuth
from app.clients.thing_model import ThingModelClient
from app.clients.thingsboard import ThingsBoardClient
from app.common.errors import AgentError, AgentUnavailable
from app.config import Settings

logger = logging.getLogger(__name__)
MAX_TOOL_ROUNDS = 3


class AgentService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._http = httpx.AsyncClient(timeout=settings.timeout_seconds)
        self._auth = ThingsBoardAuth(
            self._http,
            settings.thingsboard_url,
            settings.auth_cache_seconds,
        )
        thingsboard = ThingsBoardClient(self._http, settings.thingsboard_url)
        thing_model = ThingModelClient(self._http, settings.thing_model_url)
        self._executor = AgentActionExecutor(thingsboard, thing_model)
        self._llm = OpenAiChatClient(settings)

    async def close(self) -> None:
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

        messages = [{
            "role": "system",
            "content": system_prompt_for_user(
                user.authority,
                user.tenant_id,
                request.tsl is not None,
            ),
        }]
        messages.extend(
            message.model_dump()
            for message in self._latest(request.messages, self._settings.max_messages)
        )

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._llm.complete(messages, TOOL_SPECS)
            if not response.choices:
                raise AgentUnavailable("AI 模型没有返回结果")
            message = response.choices[0].message
            tool_calls = list(message.tool_calls or [])
            if not tool_calls:
                return AgentChatResponse(reply=message.content or "")

            read_calls = [call for call in tool_calls if call.function.name in READ_TOOLS]
            write_calls = [call for call in tool_calls if call.function.name in WRITE_TOOLS]

            if write_calls:
                actions = [
                    self._tool_call_to_action(call)
                    for call in self._latest(write_calls, self._settings.max_actions)
                ]
                return AgentChatResponse(
                    reply=message.content or "已生成待确认操作，请确认后执行。",
                    actions=actions,
                )

            if read_calls:
                messages.append(message.model_dump(exclude_none=True))
                for call in read_calls:
                    result = await self._execute_read_tool(call, token, user)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result.model_dump_json(),
                    })
                continue

            return AgentChatResponse(reply=message.content or "")

        raise AgentUnavailable("AI 规划步骤过多，请缩小需求范围后重试")

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
