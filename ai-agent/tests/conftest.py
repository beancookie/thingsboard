import pytest

from app.auth.thingsboard import CurrentUser
from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        enabled=True,
        openai_api_key="test-key",
        openai_base_url="http://ai.local/v1",
        openai_model="test-model",
        thingsboard_url="http://tb.local",
        thing_model_url="http://tm.local",
        timeout_seconds=5,
    )


@pytest.fixture
def sys_admin() -> CurrentUser:
    return CurrentUser(
        user_id="u-sys",
        tenant_id=None,
        authority="SYS_ADMIN",
        email="sys@example.com",
    )


@pytest.fixture
def tenant_admin() -> CurrentUser:
    return CurrentUser(
        user_id="u-tenant",
        tenant_id="tenant-1",
        authority="TENANT_ADMIN",
        email="tenant@example.com",
    )
