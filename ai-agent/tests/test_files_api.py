from fastapi.testclient import TestClient

from app.agent.files import FileStore
from app.auth.thingsboard import CurrentUser
from app.main import app


class FakeAgent:
    def __init__(self) -> None:
        self.file_store = FileStore()

    async def verify_token(self, token: str) -> CurrentUser:
        return CurrentUser(
            user_id="user-1",
            tenant_id="tenant-1",
            authority="TENANT_ADMIN",
        )

    async def close(self) -> None:
        pass


def test_upload_file() -> None:
    fake = FakeAgent()
    with TestClient(app) as client:
        app.state.agent = fake
        upload = client.post(
            "/files",
            headers={"X-Authorization": "Bearer token"},
            files={"file": ("test.txt", b"hello", "text/plain")},
        )

    assert upload.status_code == 200
    data = upload.json()
    assert data["name"] == "test.txt"
    assert data["size"] == 5
    assert fake.file_store.get(data["id"], "user-1") is not None


def test_upload_file_preserves_chinese_name() -> None:
    fake = FakeAgent()
    with TestClient(app) as client:
        app.state.agent = fake
        upload = client.post(
            "/files",
            headers={"X-Authorization": "Bearer token"},
            files={"file": ("温度传感器.json", b"{}", "application/json")},
        )

    assert upload.status_code == 200
    data = upload.json()
    assert data["name"] == "温度传感器.json"
