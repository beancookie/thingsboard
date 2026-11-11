from typing import Any

import pytest

from app.agent.api_catalog import ApiCatalog, ApiOperation
from app.agent.api_executor import ApiExecutor
from app.agent.executor import AgentActionExecutor
from app.agent.models import AgentAction


class FakeThingsBoard:
    def __init__(self) -> None:
        self.created_tenant_payload: dict[str, Any] | None = None
        self.created_device_payload: dict[str, Any] | None = None
        self.saved_attributes: dict[str, Any] | None = None

    async def create_tenant(self, token: str, title: str, description: str | None = None):
        self.created_tenant_payload = {"title": title, "description": description}
        return {"id": {"id": "tenant-1"}}

    async def create_user(self, *args, **kwargs):
        return {"id": {"id": "user-1"}}

    async def create_device(
        self, token: str, name: str, device_profile_id: str, label: str | None = None
    ):
        self.created_device_payload = {
            "name": name,
            "deviceProfileId": device_profile_id,
            "label": label,
        }
        return {"id": {"id": "device-1"}}

    async def save_device_attributes(self, token: str, device_id: str, attributes):
        self.saved_attributes = {"deviceId": device_id, "attributes": attributes}

    async def list_tenants(self, token: str):
        return {"data": [{"id": {"id": "tenant-1"}}]}

    async def list_tenant_devices(self, token: str, page_size: int, page: int):
        return {"data": [{"id": {"id": "device-1"}}]}

    async def request(self, method: str, path: str, token: str, **kwargs):
        return {"method": method, "path": path}


class FakeThingModel:
    def __init__(self) -> None:
        self.provisioned_tenant: str | None = None
        self.created_product_payload: dict[str, Any] | None = None
        self.updated_thing_model: dict[str, Any] | None = None

    async def provision_auto(self, token: str, tenant_id: str, force: bool = False):
        self.provisioned_tenant = tenant_id
        return {"tenantId": tenant_id}

    async def list_products(self, token: str, keyword: str | None = None):
        return [{"productId": "P1", "name": "Product"}]

    async def get_product(self, token: str, product_id: str):
        return {
            "product": {
                "productId": product_id,
                "tbProfileId": "profile-1",
                "tslVersion": "1.0",
            }
        }

    async def create_product(self, token: str, payload: dict[str, Any]):
        self.created_product_payload = payload
        return {
            "productId": payload["productId"],
            "tbProfileId": "profile-1",
            "tbAssetId": "asset-1",
            "tbRuleChainId": "chain-1",
            "status": "PUBLISHED",
        }

    async def update_thing_model(
        self, token: str, product_id: str, payload: dict[str, Any]
    ):
        self.updated_thing_model = {"productId": product_id, "payload": payload}
        return {
            "productId": product_id,
            "tslVersion": payload.get("tslVersion", "1.0"),
            "tbProfileId": "profile-1",
            "tbAssetId": "asset-1",
            "tbRuleChainId": "chain-1",
            "status": "PUBLISHED",
        }


@pytest.fixture
def clients():
    return FakeThingsBoard(), FakeThingModel()


@pytest.mark.asyncio
async def test_create_tenant_provisions_service_account(clients, sys_admin) -> None:
    thingsboard, thing_model = clients
    executor = AgentActionExecutor(thingsboard, thing_model)
    action = AgentAction(
        id="a1",
        type="create_tenant",
        params={"title": "Test Tenant", "description": "demo"},
    )

    result = await executor.execute(action, sys_admin, "token", None)

    assert result.success is True
    assert result.data == {"tenantId": "tenant-1", "provisioned": True}
    assert thingsboard.created_tenant_payload == {
        "title": "Test Tenant",
        "description": "demo",
    }
    assert thing_model.provisioned_tenant == "tenant-1"


@pytest.mark.asyncio
async def test_tenant_admin_cannot_create_tenant(clients, tenant_admin) -> None:
    executor = AgentActionExecutor(*clients)
    action = AgentAction(id="a1", type="create_tenant", params={"title": "Nope"})

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is False
    assert "SYS_ADMIN" in result.message


@pytest.mark.asyncio
async def test_create_product_requires_tsl_and_uses_tenant_admin(clients, tenant_admin) -> None:
    _, thing_model = clients
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="create_product",
        params={
            "product_id": "P1",
            "name": "Product",
            "model": "M1",
            "category_id": "1",
            "tsl_version": "1.0",
        },
    )

    result = await executor.execute(
        action, tenant_admin, "token", {"profile": {"ProductId": "P1"}}
    )

    assert result.success is True
    assert result.data["productId"] == "P1"
    assert thing_model.created_product_payload["tsl"] == {
        "version": "1.0",
        "profile": {"ProductId": "P1"},
        "properties": [],
    }


@pytest.mark.asyncio
async def test_create_product_uses_ai_generated_tsl(clients, tenant_admin) -> None:
    _, thing_model = clients
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="create_product",
        params={
            "product_id": "P1",
            "name": "Product",
            "tsl": {
                "version": "1.0",
                "profile": {"ProductId": "P1"},
                "properties": [
                    {
                        "id": "temperature",
                        "name": "温度",
                        "mode": "r",
                        "define": {"type": "float", "unit": "℃"},
                    }
                ],
            },
        },
    )

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is True
    assert thing_model.created_product_payload["tsl"]["properties"][0]["id"] == "temperature"


@pytest.mark.asyncio
async def test_create_product_without_tsl_uses_minimal_tsl(clients, tenant_admin) -> None:
    _, thing_model = clients
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="create_product",
        params={"product_id": "P1", "name": "Product"},
    )

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is True
    assert thing_model.created_product_payload["tsl"] == {
        "version": "1.0",
        "profile": {"ProductId": "P1"},
        "properties": [],
    }


@pytest.mark.asyncio
async def test_update_thing_model_uses_action_tsl(clients, tenant_admin) -> None:
    _, thing_model = clients
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="update_thing_model",
        params={
            "productId": "P1",
            "tslVersion": "1.1",
            "tsl": {
                "version": "1.1",
                "profile": {"ProductId": "P1"},
                "properties": [
                    {
                        "id": "temperature",
                        "name": "温度",
                        "mode": "r",
                        "define": {"type": "float"},
                    }
                ],
            },
        },
    )

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is True
    assert result.data["tslVersion"] == "1.1"
    assert thing_model.updated_thing_model["productId"] == "P1"
    assert thing_model.updated_thing_model["payload"]["tsl"]["properties"][0]["id"] == "temperature"


@pytest.mark.asyncio
async def test_update_thing_model_uses_attached_tsl(clients, tenant_admin) -> None:
    _, thing_model = clients
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="update_thing_model",
        params={"productId": "P1"},
    )

    result = await executor.execute(
        action,
        tenant_admin,
        "token",
        {"profile": {"ProductId": "P1"}, "properties": []},
    )

    assert result.success is True
    assert thing_model.updated_thing_model["payload"]["tsl"]["profile"]["ProductId"] == "P1"


@pytest.mark.asyncio
async def test_update_thing_model_requires_tsl(clients, tenant_admin) -> None:
    _, thing_model = clients
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="update_thing_model",
        params={"productId": "P1"},
    )

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is False
    assert "缺少物模型 TSL" in result.message
    assert thing_model.updated_thing_model is None


@pytest.mark.asyncio
async def test_update_thing_model_rejects_product_id_mismatch(clients, tenant_admin) -> None:
    _, thing_model = clients
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="update_thing_model",
        params={
            "productId": "P1",
            "tsl": {"profile": {"ProductId": "P2"}, "properties": []},
        },
    )

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is False
    assert "ProductId" in result.message
    assert thing_model.updated_thing_model is None


@pytest.mark.asyncio
async def test_update_thing_model_enforces_size_limit(clients, tenant_admin) -> None:
    _, thing_model = clients
    executor = AgentActionExecutor(*clients, max_tsl_bytes=10)
    action = AgentAction(
        id="a1",
        type="update_thing_model",
        params={"productId": "P1", "tsl": {"profile": {"ProductId": "P1"}}},
    )

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is False
    assert "不能超过" in result.message
    assert thing_model.updated_thing_model is None


@pytest.mark.asyncio
async def test_create_device_resolves_profile_and_writes_attributes(
    clients, tenant_admin
) -> None:
    thingsboard, _ = clients
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="create_device",
        params={
            "product_id": "P1",
            "device_name": "device_1",
            "label": "设备 1",
            "site_code": "S-001",
        },
    )

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is True
    assert result.data == {"deviceId": "device-1", "deviceName": "device_1"}
    assert thingsboard.created_device_payload["deviceProfileId"] == "profile-1"
    assert thingsboard.saved_attributes["attributes"]["product_id"] == "P1"
    assert thingsboard.saved_attributes["attributes"]["site_code"] == "S-001"


@pytest.mark.asyncio
async def test_tenant_admin_cannot_create_user_in_other_tenant(
    clients, tenant_admin
) -> None:
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="create_user",
        params={"tenant_id": "tenant-2", "email": "u@example.com"},
    )

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is False
    assert "其他租户" in result.message


@pytest.mark.asyncio
async def test_catalog_handler_action_is_executed(clients, sys_admin) -> None:
    catalog = ApiCatalog(
        [
            ApiOperation.model_validate(
                {
                    "id": "thingsboard.createTenant",
                    "service": "thingsboard",
                    "method": "POST",
                    "path": "/api/tenant",
                    "summary": "创建租户",
                    "mode": "write",
                    "handler": "create_tenant",
                    "permission": "SYS_ADMIN",
                    "params": {
                        "title": {"in": "body", "type": "string", "required": True}
                    },
                }
            )
        ]
    )
    executor = AgentActionExecutor(*clients, catalog, ApiExecutor(*clients))
    action = AgentAction(
        id="a1",
        type="thingsboard.createTenant",
        params={"title": "Test Tenant"},
    )

    result = await executor.execute(action, sys_admin, "token", None)

    assert result.success is True
    assert result.data == {"tenantId": "tenant-1", "provisioned": True}


@pytest.mark.asyncio
async def test_catalog_generic_action_is_executed(clients, sys_admin) -> None:
    catalog = ApiCatalog(
        [
            ApiOperation.model_validate(
                {
                    "id": "thingsboard.deleteTenant",
                    "service": "thingsboard",
                    "method": "DELETE",
                    "path": "/api/tenant/{tenantId}",
                    "summary": "删除租户",
                    "mode": "write",
                    "permission": "SYS_ADMIN",
                    "risk": "high",
                    "params": {
                        "tenantId": {"in": "path", "type": "string", "required": True}
                    },
                }
            )
        ]
    )
    executor = AgentActionExecutor(*clients, catalog, ApiExecutor(*clients))
    action = AgentAction(
        id="a1",
        type="thingsboard.deleteTenant",
        params={"tenantId": "tenant-1"},
        risk="high",
    )

    result = await executor.execute(action, sys_admin, "token", None)

    assert result.success is True
    assert result.data == {"method": "DELETE", "path": "/api/tenant/tenant-1"}



@pytest.mark.asyncio
async def test_create_product_rejects_mismatched_tsl_product_id(clients, tenant_admin) -> None:
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id='a1',
        type='create_product',
        params={
            'product_id': 'P1',
            'name': 'Product',
            'tsl': {
                'version': '1.0',
                'profile': {'ProductId': 'P2'},
                'properties': [],
            },
        },
    )

    result = await executor.execute(action, tenant_admin, 'token', None)

    assert result.success is False
    assert 'ProductId' in result.message


@pytest.mark.asyncio
async def test_create_product_rejects_oversized_tsl(clients, tenant_admin) -> None:
    executor = AgentActionExecutor(*clients, max_tsl_bytes=20)
    action = AgentAction(
        id='a1',
        type='create_product',
        params={
            'product_id': 'P1',
            'name': 'Product',
            'tsl': {
                'version': '1.0',
                'profile': {'ProductId': 'P1'},
                'properties': [{'id': 'temperature'}],
            },
        },
    )

    result = await executor.execute(action, tenant_admin, 'token', None)

    assert result.success is False
    assert 'TSL' in result.message

