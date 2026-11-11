from types import SimpleNamespace

import pytest

from app.agent.models import (
    AgentAction,
    AgentActionResult,
    AgentChatRequest,
    AgentMessage,
)
from app.agent.orchestrator import AgentService
from app.common.errors import AgentError


class FakeFunction:
    def __init__(self, name: str, arguments: str = "{}"):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, name: str, arguments: str = "{}", call_id: str = "call-1"):
        self.id = call_id
        self.function = FakeFunction(name, arguments)


class FakeMessage:
    def __init__(self, content: str | None = None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none: bool = False):
        data = {
            "role": "assistant",
            "content": self.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls
            ],
        }
        return data


class FakeLlm:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.requests = []

    async def complete(self, messages, tools=None):
        self.calls += 1
        self.requests.append([dict(message) for message in messages])
        message = self.responses.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    async def close(self) -> None:
        pass


class FakeExecutor:
    def __init__(self):
        self.calls = []

    async def execute(self, action, user, token, tsl):
        self.calls.append((action, user, token, tsl))
        return AgentActionResult(
            action_id=action.id,
            type=action.type,
            success=True,
            message="ok",
            data={"ok": True},
        )


@pytest.mark.asyncio
async def test_chat_returns_plain_reply(settings, tenant_admin) -> None:
    service = AgentService(settings)
    service._llm = FakeLlm([FakeMessage("你好")])
    try:
        response = await service.chat(
            AgentChatRequest(messages=[AgentMessage(role="user", content="hi")]),
            "token",
            tenant_admin,
        )
    finally:
        await service.close()

    assert response.reply == "你好"
    assert response.actions == []


@pytest.mark.asyncio
async def test_chat_converts_write_tool_to_proposed_action(
    settings, tenant_admin
) -> None:
    service = AgentService(settings)
    service._llm = FakeLlm([
        FakeMessage(
            tool_calls=[
                FakeToolCall(
                    "create_tenant",
                    '{"title":"Test Tenant"}',
                )
            ]
        )
    ])
    executor = FakeExecutor()
    service._executor = executor
    try:
        response = await service.chat(
            AgentChatRequest(messages=[AgentMessage(role="user", content="创建租户")]),
            "token",
            tenant_admin,
        )
    finally:
        await service.close()

    assert response.reply
    assert len(response.actions) == 1
    assert response.actions[0].type == "create_tenant"
    assert response.actions[0].status == "PROPOSED"
    assert executor.calls == []


@pytest.mark.asyncio
async def test_chat_executes_read_tool_and_asks_model_again(
    settings, tenant_admin
) -> None:
    service = AgentService(settings)
    service._llm = FakeLlm([
        FakeMessage(tool_calls=[FakeToolCall("list_products")]),
        FakeMessage("产品列表如下"),
    ])
    executor = FakeExecutor()
    service._executor = executor
    try:
        response = await service.chat(
            AgentChatRequest(messages=[AgentMessage(role="user", content="列产品")]),
            "token",
            tenant_admin,
        )
    finally:
        await service.close()

    assert response.reply == "产品列表如下"
    assert len(executor.calls) == 1
    assert executor.calls[0][0].type == "list_products"


@pytest.mark.asyncio
async def test_chat_uses_catalog_search_and_call(settings, tenant_admin) -> None:
    service = AgentService(settings)

    class FakeGateway:
        def __init__(self) -> None:
            self.searches = []
            self.calls = []

        def search(self, query, *, service=None, limit=5):
            self.searches.append((query, service, limit))
            return [
                {
                    "id": "thingsboard.get.telemetry",
                    "summary": "查询遥测",
                    "mode": "read",
                    "params": {},
                }
            ]

        async def call(self, session_id, operation_id, params):
            self.calls.append((session_id, operation_id, params))
            return {"status": "OK", "data": {"temperature": 20}}

    gateway = FakeGateway()
    service.tool_gateway = gateway
    service._llm = FakeLlm(
        [
            FakeMessage(
                tool_calls=[
                    FakeToolCall(
                        "search_api_operations",
                        '{"query":"遥测"}',
                        "c1",
                    )
                ]
            ),
            FakeMessage(
                tool_calls=[
                    FakeToolCall(
                        "call_api_operation",
                        '{"operation_id":"thingsboard.get.telemetry","params":{}}',
                        "c2",
                    )
                ]
            ),
            FakeMessage("查询完成"),
        ]
    )
    try:
        response = await service.chat(
            AgentChatRequest(
                messages=[AgentMessage(role="user", content="查询遥测")]
            ),
            "token",
            tenant_admin,
        )
    finally:
        await service.close()

    assert response.reply == "查询完成"
    assert gateway.searches == [("遥测", None, 5)]
    assert gateway.calls[0][1] == "thingsboard.get.telemetry"


@pytest.mark.asyncio
async def test_allows_multiple_tool_rounds(settings, tenant_admin) -> None:
    settings.max_tool_rounds = 4
    service = AgentService(settings)
    service._executor = FakeExecutor()
    service._llm = FakeLlm(
        [
            FakeMessage(tool_calls=[FakeToolCall("list_products", call_id="c1")]),
            FakeMessage(tool_calls=[FakeToolCall("list_products", call_id="c2")]),
            FakeMessage(tool_calls=[FakeToolCall("list_products", call_id="c3")]),
            FakeMessage("查询完成"),
        ]
    )
    try:
        response = await service.chat(
            AgentChatRequest(messages=[AgentMessage(role="user", content="查询")]),
            "token",
            tenant_admin,
        )
    finally:
        await service.close()

    assert response.reply == "查询完成"
    assert len(service._executor.calls) == 3


@pytest.mark.asyncio
async def test_tool_round_limit_returns_planning_error(settings, tenant_admin) -> None:
    settings.max_tool_rounds = 2
    service = AgentService(settings)
    service._executor = FakeExecutor()
    service._llm = FakeLlm(
        [
            FakeMessage(tool_calls=[FakeToolCall("list_products", call_id="c1")]),
            FakeMessage(tool_calls=[FakeToolCall("list_products", call_id="c2")]),
        ]
    )
    try:
        with pytest.raises(AgentError) as error:
            await service.chat(
                AgentChatRequest(
                    messages=[AgentMessage(role="user", content="查询")]
                ),
                "token",
                tenant_admin,
            )
    finally:
        await service.close()

    assert error.value.code == "AI_PLANNING_LIMIT"


@pytest.mark.asyncio
async def test_execute_mode_returns_action_results(settings, tenant_admin) -> None:
    service = AgentService(settings)
    executor = FakeExecutor()
    service._executor = executor
    action = AgentAction(
        id="a1",
        type="create_tenant",
        params={"title": "Test"},
    )
    try:
        response = await service.chat(
            AgentChatRequest(mode="execute", actions=[action]),
            "token",
            tenant_admin,
        )
    finally:
        await service.close()

    assert response.reply == "执行完成：1 个操作成功。"
    assert len(response.executed) == 1
    assert response.executed[0].success is True
    assert executor.calls[0][0] == action


@pytest.mark.asyncio
async def test_keeps_latest_messages_without_error(settings, tenant_admin) -> None:
    settings.max_messages = 3
    service = AgentService(settings)
    service._llm = FakeLlm([FakeMessage("ok")])
    try:
        response = await service.chat(
            AgentChatRequest(
                messages=[
                    AgentMessage(role="user", content=f"m{index}")
                    for index in range(5)
                ]
            ),
            "token",
            tenant_admin,
        )
    finally:
        await service.close()

    assert response.reply == "ok"
    assert [message["content"] for message in service._llm.requests[0][1:]] == [
        "m2",
        "m3",
        "m4",
    ]


@pytest.mark.asyncio
async def test_keeps_latest_generated_actions_without_error(
    settings, tenant_admin
) -> None:
    settings.max_actions = 2
    service = AgentService(settings)
    service._llm = FakeLlm([
        FakeMessage(
            tool_calls=[
                FakeToolCall("create_tenant", '{"title":"A"}', "c1"),
                FakeToolCall("create_tenant", '{"title":"B"}', "c2"),
                FakeToolCall("create_tenant", '{"title":"C"}', "c3"),
            ]
        )
    ])
    try:
        response = await service.chat(
            AgentChatRequest(messages=[AgentMessage(role="user", content="创建租户")]),
            "token",
            tenant_admin,
        )
    finally:
        await service.close()

    assert [action.id for action in response.actions] == ["c2", "c3"]


@pytest.mark.asyncio
async def test_execute_keeps_latest_actions_without_error(
    settings, tenant_admin
) -> None:
    settings.max_actions = 2
    service = AgentService(settings)
    executor = FakeExecutor()
    service._executor = executor
    actions = [
        AgentAction(id=f"a{index}", type="create_tenant", params={"title": str(index)})
        for index in range(3)
    ]
    try:
        response = await service.chat(
            AgentChatRequest(mode="execute", actions=actions),
            "token",
            tenant_admin,
        )
    finally:
        await service.close()

    assert [call[0].id for call in executor.calls] == ["a1", "a2"]
    assert response.reply == "执行完成：2 个操作成功。"


@pytest.mark.asyncio
async def test_rejects_oversized_tsl(settings, tenant_admin) -> None:
    settings.max_tsl_bytes = 10
    service = AgentService(settings)
    try:
        request = AgentChatRequest(tsl={"large": "x" * 100})
        with pytest.raises(AgentError) as error:
            await service.chat(request, "token", tenant_admin)
    finally:
        await service.close()

    assert error.value.code == "TSL_TOO_LARGE"


@pytest.mark.asyncio
async def test_missing_ai_key_returns_configuration_error(settings, tenant_admin) -> None:
    settings.openai_api_key = None
    service = AgentService(settings)
    try:
        with pytest.raises(AgentError) as error:
            await service.chat(
                AgentChatRequest(
                    messages=[AgentMessage(role="user", content="hi")]
                ),
                "token",
                tenant_admin,
            )
    finally:
        await service.close()

    assert error.value.status_code == 503
    assert error.value.code == "AI_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_attachment_context_includes_text_file(settings, tenant_admin) -> None:
    service = AgentService(settings)
    try:
        file = service.file_store.create(
            b"temperature,value\\n1,20",
            "data.csv",
            "text/csv",
            tenant_admin.user_id,
        )
        context = service._attachment_context([file], tenant_admin)
    finally:
        await service.close()

    assert "data.csv" in context
    assert "temperature,value" in context

