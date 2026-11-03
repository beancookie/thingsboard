import httpx
import pytest

from app.clients.thing_model import ThingModelClient
from app.clients.thingsboard import ThingsBoardClient
from app.common.errors import AgentError


@pytest.mark.asyncio
async def test_thingsboard_create_tenant() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/tenant"
        assert request.headers["X-Authorization"] == "Bearer tb-token"
        assert request.content == b'{"title":"Test Tenant"}'
        return httpx.Response(200, json={"id": {"id": "tenant-1"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ThingsBoardClient(client, "http://tb.local").create_tenant(
            "tb-token", "Test Tenant"
        )

    assert result["id"]["id"] == "tenant-1"


@pytest.mark.asyncio
async def test_thingsboard_create_device() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/device"
        assert b'"deviceProfileId"' in request.content
        assert b'"profile-1"' in request.content
        return httpx.Response(200, json={"id": {"id": "device-1"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ThingsBoardClient(client, "http://tb.local").create_device(
            "tb-token", "device_1", "profile-1"
        )

    assert result["id"]["id"] == "device-1"


@pytest.mark.asyncio
async def test_thingsboard_error_is_mapped() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AgentError) as error:
            await ThingsBoardClient(client, "http://tb.local").list_tenants("token")

    assert error.value.status_code == 502
    assert error.value.code == "THINGSBOARD_API_ERROR"


@pytest.mark.asyncio
async def test_thing_model_create_product_and_provision() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        assert request.headers["X-Authorization"] == "Bearer tb-token"
        if request.url.path == "/api/products":
            return httpx.Response(200, json={"productId": "P1"})
        if request.url.path == "/api/admin/tenants/tenant-1/provision-auto":
            return httpx.Response(200, json={"tenantId": "tenant-1"})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        thing_model = ThingModelClient(client, "http://tm.local")
        product = await thing_model.create_product("tb-token", {"productId": "P1"})
        account = await thing_model.provision_auto("tb-token", "tenant-1")

    assert product["productId"] == "P1"
    assert account["tenantId"] == "tenant-1"
    assert calls == [
        "/api/products",
        "/api/admin/tenants/tenant-1/provision-auto",
    ]
