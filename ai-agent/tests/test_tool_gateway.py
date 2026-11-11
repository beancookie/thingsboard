from typing import Any

import pytest

from app.agent.api_catalog import ApiCatalog, ApiOperation
from app.agent.api_executor import ApiExecutor
from app.agent.sessions import SessionStore
from app.agent.tool_gateway import AgentToolGateway


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request(
        self,
        method: str,
        path: str,
        token: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "token": token,
                "params": params,
                "json": json,
            }
        )
        return {"data": [{"id": "tenant-1"}]}


def _catalog() -> ApiCatalog:
    return ApiCatalog(
        [
            ApiOperation.model_validate(
                {
                    "id": "thingsboard.listTenants",
                    "service": "thingsboard",
                    "method": "GET",
                    "path": "/api/tenants",
                    "summary": "查询租户列表",
                    "aliases": ["租户"],
                    "mode": "read",
                    "code_access": "read",
                    "permission": "SYS_ADMIN",
                    "risk": "low",
                    "params": {},
                }
            ),
            ApiOperation.model_validate(
                {
                    "id": "thingsboard.createTenant",
                    "service": "thingsboard",
                    "method": "POST",
                    "path": "/api/tenant",
                    "summary": "创建租户",
                    "aliases": ["创建租户"],
                    "mode": "write",
                    "code_access": "write",
                    "permission": "SYS_ADMIN",
                    "risk": "medium",
                    "handler": "create_tenant",
                    "params": {
                        "title": {
                            "in": "body",
                            "type": "string",
                            "required": True,
                        }
                    },
                }
            ),
            ApiOperation.model_validate(
                {
                    "id": "thing_model.updateThingModel",
                    "service": "thing_model",
                    "method": "PUT",
                    "path": "/api/products/{productId}/thing-model",
                    "summary": "更新产品物模型",
                    "aliases": ["更新物模型"],
                    "mode": "write",
                    "code_access": "write",
                    "permission": "TENANT_ADMIN",
                    "risk": "medium",
                    "handler": "update_thing_model",
                    "params": {
                        "productId": {
                            "in": "path",
                            "type": "string",
                            "required": True,
                        },
                        "tsl": {
                            "in": "body",
                            "type": "object",
                            "required": True,
                        },
                    },
                }
            ),
        ]
    )


@pytest.fixture
def gateway() -> tuple[AgentToolGateway, FakeClient, SessionStore]:
    thingsboard = FakeClient()
    sessions = SessionStore()
    catalog = _catalog()
    gateway = AgentToolGateway(
        catalog,
        ApiExecutor(thingsboard, FakeClient()),
        sessions,
    )
    return gateway, thingsboard, sessions


def test_search_returns_compact_results(gateway) -> None:
    tool_gateway, _, _ = gateway

    result = tool_gateway.search("租户")

    assert result[0]["id"] == "thingsboard.listTenants"
    assert result[0]["mode"] == "read"
    assert result[0]["params"] == {}


@pytest.mark.asyncio
async def test_read_calls_backend(gateway, sys_admin) -> None:
    tool_gateway, thingsboard, sessions = gateway
    session = sessions.create("tb-token", sys_admin)

    result = await tool_gateway.call(
        session.session_id,
        "thingsboard.listTenants",
        {},
    )

    assert result["status"] == "OK"
    assert result["data"] == {"data": [{"id": "tenant-1"}]}
    assert thingsboard.calls[0]["token"] == "tb-token"


@pytest.mark.asyncio
async def test_write_only_creates_proposal(gateway, sys_admin) -> None:
    tool_gateway, thingsboard, sessions = gateway
    session = sessions.create("tb-token", sys_admin)

    result = await tool_gateway.call(
        session.session_id,
        "thingsboard.createTenant",
        {"title": "测试厂商"},
    )

    assert result["status"] == "PROPOSED"
    assert result["operation_id"] == "thingsboard.createTenant"
    assert result["risk"] == "medium"
    assert thingsboard.calls == []

    proposals = sessions.drain_proposals(session.session_id)
    assert len(proposals) == 1
    assert proposals[0].type == "thingsboard.createTenant"
    assert proposals[0].params == {"title": "测试厂商"}
    assert proposals[0].risk == "medium"


@pytest.mark.asyncio
async def test_write_injects_session_tsl_when_missing(gateway, tenant_admin) -> None:
    tool_gateway, _, sessions = gateway
    tsl = {"profile": {"ProductId": "P1"}, "properties": []}
    session = sessions.create("tb-token", tenant_admin, tsl=tsl)

    result = await tool_gateway.call(
        session.session_id,
        "thing_model.updateThingModel",
        {"productId": "P1"},
    )

    assert result["status"] == "PROPOSED"
    proposals = sessions.drain_proposals(session.session_id)
    assert proposals[0].params["tsl"] == tsl


@pytest.mark.asyncio
async def test_write_replaces_null_tsl_with_session_tsl(gateway, tenant_admin) -> None:
    tool_gateway, _, sessions = gateway
    tsl = {"profile": {"ProductId": "P1"}, "properties": []}
    session = sessions.create("tb-token", tenant_admin, tsl=tsl)

    result = await tool_gateway.call(
        session.session_id,
        "thing_model.updateThingModel",
        {"productId": "P1", "tsl": None},
    )

    assert result["status"] == "PROPOSED"
    proposals = sessions.drain_proposals(session.session_id)
    assert proposals[0].params["tsl"] == tsl


@pytest.mark.asyncio
async def test_write_requires_tsl_when_no_attachment(gateway, tenant_admin) -> None:
    tool_gateway, _, sessions = gateway
    session = sessions.create("tb-token", tenant_admin)

    result = await tool_gateway.call(
        session.session_id,
        "thing_model.updateThingModel",
        {"productId": "P1"},
    )

    assert result["status"] == "ERROR"
    assert result["code"] == "API_PARAMETER_REQUIRED"
    assert sessions.drain_proposals(session.session_id) == []


@pytest.mark.asyncio
async def test_unknown_operation_is_rejected(gateway, sys_admin) -> None:
    tool_gateway, _, sessions = gateway
    session = sessions.create("tb-token", sys_admin)

    result = await tool_gateway.call(session.session_id, "missing", {})

    assert result["status"] == "ERROR"
    assert result["code"] == "OPERATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_missing_session_is_rejected(gateway) -> None:
    tool_gateway, _, _ = gateway

    result = await tool_gateway.call("missing", "thingsboard.listTenants", {})

    assert result["status"] == "ERROR"
    assert result["code"] == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_write_parameters_are_validated(gateway, sys_admin) -> None:
    tool_gateway, thingsboard, sessions = gateway
    session = sessions.create("tb-token", sys_admin)

    result = await tool_gateway.call(
        session.session_id,
        "thingsboard.createTenant",
        {},
    )

    assert result["status"] == "ERROR"
    assert result["code"] == "API_PARAMETER_REQUIRED"
    assert thingsboard.calls == []
    assert sessions.drain_proposals(session.session_id) == []




