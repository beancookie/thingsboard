from fastapi.testclient import TestClient

from app.agent.models import AgentChatRequest, AgentChatResponse
from app.auth.thingsboard import CurrentUser
from app.common.errors import AgentUnauthorized
from app.main import app


class FakeAgent:
    def __init__(self) -> None:
        self.last_request: AgentChatRequest | None = None
        self.last_token: str | None = None

    async def verify_token(self, token: str) -> CurrentUser:
        if token == "bad-token":
            raise AgentUnauthorized()
        return CurrentUser(
            user_id="u-1",
            tenant_id="tenant-1",
            authority="TENANT_ADMIN",
            email="tenant@example.com",
        )

    async def chat(
        self,
        request: AgentChatRequest,
        token: str,
        user: CurrentUser,
    ) -> AgentChatResponse:
        self.last_request = request
        self.last_token = token
        return AgentChatResponse(reply=f"hello {user.authority}")

    async def close(self) -> None:
        pass


def test_chat_requires_token() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"mode": "chat", "messages": []},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_chat_rejects_invalid_token() -> None:
    fake = FakeAgent()
    with TestClient(app) as client:
        app.state.agent = fake
        response = client.post(
            "/chat",
            headers={"X-Authorization": "Bearer bad-token"},
            json={"mode": "chat", "messages": []},
        )

    assert response.status_code == 401


def test_chat_returns_agent_response() -> None:
    fake = FakeAgent()
    with TestClient(app) as client:
        app.state.agent = fake
        response = client.post(
            "/chat",
            headers={"X-Authorization": "Bearer good-token"},
            json={
                "mode": "chat",
                "messages": [{"role": "user", "content": "你好"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["reply"] == "hello TENANT_ADMIN"
    assert fake.last_token == "good-token"
    assert fake.last_request.messages[0].content == "你好"


def test_chat_accepts_authorization_header() -> None:
    fake = FakeAgent()
    with TestClient(app) as client:
        app.state.agent = fake
        response = client.post(
            "/chat",
            headers={"Authorization": "Bearer good-token"},
            json={"mode": "chat", "messages": []},
        )

    assert response.status_code == 200
    assert fake.last_token == "good-token"


def test_chat_rejects_invalid_mode() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"X-Authorization": "Bearer good-token"},
            json={"mode": "invalid", "messages": []},
        )

    assert response.status_code == 400
    assert response.json()["code"] == "BAD_REQUEST"


def test_chat_rejects_invalid_message_role() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"X-Authorization": "Bearer good-token"},
            json={
                "mode": "chat",
                "messages": [{"role": "system", "content": "bad"}],
            },
        )

    assert response.status_code == 400
    assert response.json()["code"] == "BAD_REQUEST"
