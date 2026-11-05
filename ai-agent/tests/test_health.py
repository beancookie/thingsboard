from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready() -> None:
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_swagger_ui() -> None:
    with TestClient(app) as client:
        response = client.get("/swagger-ui.html")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
