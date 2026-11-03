import os
from typing import Any

import httpx
import pytest

from app.agent.executor import AgentActionExecutor
from app.auth.thingsboard import ThingsBoardAuth
from app.clients.thing_model import ThingModelClient
from app.clients.thingsboard import ThingsBoardClient

TB_URL = os.getenv("AI_AGENT_THINGSBOARD_URL", "http://localhost:18080").rstrip("/")
TM_URL = os.getenv("AI_AGENT_THING_MODEL_URL", "http://localhost:8090").rstrip("/")
SYS_USERNAME = os.getenv("TB_SYSADMIN_USERNAME")
SYS_PASSWORD = os.getenv("TB_SYSADMIN_PASSWORD")
TENANT_USERNAME = os.getenv("TB_TENANT_ADMIN_USERNAME")
TENANT_PASSWORD = os.getenv("TB_TENANT_ADMIN_PASSWORD")


@pytest.fixture(scope="session")
def integration_config() -> None:
    missing = [
        name for name, value in {
            "TB_SYSADMIN_USERNAME": SYS_USERNAME,
            "TB_SYSADMIN_PASSWORD": SYS_PASSWORD,
            "TB_TENANT_ADMIN_USERNAME": TENANT_USERNAME,
            "TB_TENANT_ADMIN_PASSWORD": TENANT_PASSWORD,
        }.items() if not value
    ]
    if missing:
        pytest.skip("Missing integration environment: " + ", ".join(missing))


@pytest.fixture
async def http() -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        yield client


async def login(http: httpx.AsyncClient, username: str, password: str) -> str:
    response = await http.post(
        f"{TB_URL}/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


@pytest.fixture
async def tokens(http: httpx.AsyncClient, integration_config: None) -> dict[str, Any]:
    sys_token = await login(http, SYS_USERNAME, SYS_PASSWORD)
    tenant_token = await login(http, TENANT_USERNAME, TENANT_PASSWORD)
    auth = ThingsBoardAuth(http, TB_URL, cache_seconds=0)
    sys_user = await auth.verify(sys_token)
    tenant_user = await auth.verify(tenant_token)
    return {
        "sys_token": sys_token,
        "tenant_token": tenant_token,
        "sys_user": sys_user,
        "tenant_user": tenant_user,
    }


@pytest.fixture
def thingsboard(http: httpx.AsyncClient) -> ThingsBoardClient:
    return ThingsBoardClient(http, TB_URL)


@pytest.fixture
def thing_model(http: httpx.AsyncClient) -> ThingModelClient:
    return ThingModelClient(http, TM_URL)


@pytest.fixture
def executor(thingsboard: ThingsBoardClient, thing_model: ThingModelClient) -> AgentActionExecutor:
    return AgentActionExecutor(thingsboard, thing_model)
