from typing import Any

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import app


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def search(self, query: str, *, service=None, limit: int = 5):
        return [
            {
                "id": "thingsboard.listTenants",
                "summary": query,
                "service": service,
                "limit": limit,
            }
        ]

    async def call(
        self,
        session_id: str,
        operation_id: str,
        params: dict[str, Any],
    ):
        self.calls.append((session_id, operation_id, params))
        return {"status": "OK", "data": []}


class FakeAgent:
    def __init__(self) -> None:
        self.tool_gateway = FakeGateway()

    async def close(self) -> None:
        pass


def _prepare(internal_token: str | None = "secret") -> FakeAgent:
    agent = FakeAgent()
    with TestClient(app) as client:
        app.state.settings.internal_tool_token = (
            SecretStr(internal_token) if internal_token else None
        )
        app.state.agent = agent
    return agent


def test_internal_search_requires_token() -> None:
    agent = _prepare()
    with TestClient(app) as client:
        app.state.settings.internal_tool_token = SecretStr("secret")
        app.state.agent = agent
        response = client.post(
            "/internal/dsh/api/search",
            json={"query": "租户"},
        )

    assert response.status_code == 403


def test_internal_search_returns_results() -> None:
    agent = _prepare()
    with TestClient(app) as client:
        app.state.settings.internal_tool_token = SecretStr("secret")
        app.state.agent = agent
        response = client.post(
            "/internal/dsh/api/search",
            headers={"X-Internal-Token": "secret"},
            json={"query": "租户", "service": "thingsboard", "limit": 3},
        )

    assert response.status_code == 200
    assert response.json()[0]["id"] == "thingsboard.listTenants"
    assert response.json()[0]["limit"] == 3


def test_internal_call_forwards_payload() -> None:
    agent = _prepare()
    with TestClient(app) as client:
        app.state.settings.internal_tool_token = SecretStr("secret")
        app.state.agent = agent
        response = client.post(
            "/internal/dsh/api/call",
            headers={"X-Internal-Token": "secret"},
            json={
                "session_id": "s1",
                "operation_id": "thingsboard.listTenants",
                "params": {"page": 0},
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    assert agent.tool_gateway.calls == [
        ("s1", "thingsboard.listTenants", {"page": 0})
    ]


def test_internal_disabled_without_token() -> None:
    agent = _prepare(internal_token=None)
    with TestClient(app) as client:
        app.state.settings.internal_tool_token = None
        app.state.agent = agent
        response = client.post(
            "/internal/dsh/api/search",
            json={"query": "租户"},
        )

    assert response.status_code == 503
    assert response.json()["code"] == "INTERNAL_TOOL_DISABLED"
