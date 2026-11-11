from pathlib import Path
from typing import Any

import pytest

from app.agent.api_catalog import ApiCatalog, ApiOperation
from app.agent.api_executor import ApiExecutor
from app.common.errors import AgentError, AgentForbidden


class FakeClient:
    def __init__(self) -> None:
        self.last: dict[str, Any] | None = None

    async def request(
        self,
        method: str,
        path: str,
        token: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        self.last = {
            "method": method,
            "path": path,
            "token": token,
            "params": params,
            "json": json,
        }
        return {"ok": True}


def _operation(**overrides: Any) -> ApiOperation:
    data = {
        "id": "thingsboard.getDevice",
        "service": "thingsboard",
        "method": "GET",
        "path": "/api/device/{deviceId}",
        "summary": "查询设备",
        "mode": "read",
        "code_access": "read",
        "permission": "TENANT_ADMIN",
        "params": {
            "deviceId": {"in": "path", "type": "string", "required": True},
            "pageSize": {"in": "query", "name": "pageSize", "type": "integer"},
            "label": {"in": "body", "name": "label", "type": "string"},
        },
    }
    data.update(overrides)
    return ApiOperation.model_validate(data)


@pytest.mark.asyncio
async def test_execute_builds_path_query_and_body(tenant_admin) -> None:
    thingsboard = FakeClient()
    thing_model = FakeClient()
    executor = ApiExecutor(thingsboard, thing_model)

    result = await executor.execute(
        _operation(),
        "tb-token",
        tenant_admin,
        {"deviceId": "device-1", "pageSize": 25, "label": "设备 1"},
    )

    assert result == {"ok": True}
    assert thingsboard.last == {
        "method": "GET",
        "path": "/api/device/device-1",
        "token": "tb-token",
        "params": {"pageSize": 25},
        "json": {"label": "设备 1"},
    }


@pytest.mark.asyncio
async def test_permission_is_checked(sys_admin) -> None:
    executor = ApiExecutor(FakeClient(), FakeClient())

    with pytest.raises(AgentForbidden):
        await executor.execute(_operation(), "tb-token", sys_admin, {"deviceId": "d1"})


@pytest.mark.asyncio
async def test_unknown_parameter_is_rejected(tenant_admin) -> None:
    executor = ApiExecutor(FakeClient(), FakeClient())

    with pytest.raises(AgentError) as error:
        await executor.execute(
            _operation(),
            "tb-token",
            tenant_admin,
            {"deviceId": "d1", "unexpected": "x"},
        )

    assert error.value.code == "API_PARAMETER_UNKNOWN"


@pytest.mark.asyncio
async def test_required_parameter_is_enforced(tenant_admin) -> None:
    executor = ApiExecutor(FakeClient(), FakeClient())

    with pytest.raises(AgentError) as error:
        await executor.execute(_operation(), "tb-token", tenant_admin, {})

    assert error.value.code == "API_PARAMETER_REQUIRED"


@pytest.mark.asyncio
async def test_disabled_operation_is_rejected(tenant_admin) -> None:
    executor = ApiExecutor(FakeClient(), FakeClient())

    with pytest.raises(AgentError) as error:
        await executor.execute(
            _operation(enabled=False),
            "tb-token",
            tenant_admin,
            {"deviceId": "d1"},
        )

    assert error.value.code == "API_DISABLED"


@pytest.mark.asyncio
async def test_tenant_parameter_is_scoped(tenant_admin) -> None:
    operation = _operation(
        id="thingsboard.getTenant",
        path="/api/tenant/{tenant_id}",
        permission="ANY",
        tenant_param="tenant_id",
        params={
            "tenant_id": {"in": "path", "type": "string", "required": True}
        },
    )
    thingsboard = FakeClient()
    executor = ApiExecutor(thingsboard, FakeClient())

    await executor.execute(operation, "tb-token", tenant_admin, {"tenant_id": "tenant-1"})

    assert thingsboard.last["path"] == "/api/tenant/tenant-1"

    with pytest.raises(AgentForbidden):
        await executor.execute(
            operation,
            "tb-token",
            tenant_admin,
            {"tenant_id": "tenant-2"},
        )


@pytest.mark.asyncio
async def test_raw_body_is_supported(tenant_admin) -> None:
    operation = _operation(
        id="thing_model.validate",
        service="thing_model",
        method="POST",
        path="/api/products/{productId}/thing-model/validate",
        mode="read",
        params={
            "productId": {"in": "path", "type": "string", "required": True},
            "$body": {"in": "body", "type": "object", "required": True},
        },
    )
    thing_model = FakeClient()
    executor = ApiExecutor(FakeClient(), thing_model)

    await executor.execute(
        operation,
        "tb-token",
        tenant_admin,
        {"productId": "P1", "$body": {"properties": []}},
    )

    assert thing_model.last["json"] == {"properties": []}


@pytest.mark.asyncio
async def test_telemetry_catalog_operation_builds_query(tenant_admin) -> None:
    root = Path(__file__).resolve().parents[1] / 'config' / 'api'
    catalog = ApiCatalog.load(root)
    operation = next(
        item
        for item in catalog.all()
        if item.path == '/api/plugins/telemetry/{entityType}/{entityId}/values/timeseries'
        and item.method == 'GET'
    )
    thingsboard = FakeClient()
    executor = ApiExecutor(thingsboard, FakeClient())

    await executor.execute(
        operation,
        'tb-token',
        tenant_admin,
        {
            'entityType': 'DEVICE',
            'entityId': 'device-1',
            'keys': 'temperature',
            'startTs': 1,
            'endTs': 2,
        },
    )

    assert thingsboard.last['path'] == '/api/plugins/telemetry/DEVICE/device-1/values/timeseries'
    assert thingsboard.last['params']['keys'] == 'temperature'
    assert thingsboard.last['params']['startTs'] == 1
    assert thingsboard.last['params']['endTs'] == 2

