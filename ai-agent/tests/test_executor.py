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
        "profile": {"ProductId": "P1"}
    }


@pytest.mark.asyncio
async def test_create_product_without_tsl_fails(clients, tenant_admin) -> None:
    executor = AgentActionExecutor(*clients)
    action = AgentAction(
        id="a1",
        type="create_product",
        params={"product_id": "P1", "name": "Product"},
    )

    result = await executor.execute(action, tenant_admin, "token", None)

    assert result.success is False
    assert "TSL" in result.message


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

