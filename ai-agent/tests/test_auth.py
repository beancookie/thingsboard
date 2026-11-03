import json

import httpx
import pytest

from app.auth.thingsboard import ThingsBoardAuth
from app.common.errors import AgentUnauthorized, AgentUnavailable


@pytest.mark.asyncio
async def test_verifies_user_and_strips_bearer_prefix() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.path == "/api/auth/user"
        assert request.headers["X-Authorization"] == "Bearer token-1"
        return httpx.Response(
            200,
            json={
                "id": {"id": "user-1"},
                "tenantId": {"id": "tenant-1"},
                "authority": "TENANT_ADMIN",
                "email": "tenant@example.com",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        auth = ThingsBoardAuth(client, "http://tb.local", cache_seconds=60)
        user = await auth.verify("Bearer token-1")
        cached = await auth.verify("token-1")

    assert user.authority == "TENANT_ADMIN"
    assert user.tenant_id == "tenant-1"
    assert cached == user
    assert calls == 1


@pytest.mark.asyncio
async def test_maps_401_to_unauthorized() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "unauthorized"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        auth = ThingsBoardAuth(client, "http://tb.local", cache_seconds=60)
        with pytest.raises(AgentUnauthorized):
            await auth.verify("bad-token")


@pytest.mark.asyncio
async def test_maps_server_error_to_unavailable() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text=json.dumps({"message": "boom"}))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        auth = ThingsBoardAuth(client, "http://tb.local", cache_seconds=60)
        with pytest.raises(AgentUnavailable):
            await auth.verify("token-1")
