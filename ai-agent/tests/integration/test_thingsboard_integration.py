import json
import logging
import os
from pathlib import Path
from uuid import uuid4

import pytest

from app.agent.executor import AgentActionExecutor
from app.agent.models import AgentAction
from app.clients.thing_model import ThingModelClient
from app.clients.thingsboard import ThingsBoardClient

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
TSL_PATH = REPO_ROOT / "thing-model" / "migrate" / "4DZDCQUA2D.tsl.json"

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_real_tokens_are_verified(tokens) -> None:
    assert tokens["sys_user"].is_sys_admin
    assert tokens["tenant_user"].is_tenant_admin
    assert tokens["tenant_user"].tenant_id


@pytest.mark.asyncio
async def test_create_tenant_and_provision_service_account(
    http,
    thingsboard: ThingsBoardClient,
    executor: AgentActionExecutor,
    tokens,
) -> None:
    title = f"AI_AGENT_E2E_{uuid4().hex[:8]}"
    action = AgentAction(
        id=uuid4().hex,
        type="create_tenant",
        params={"title": title, "description": "AI agent integration test"},
    )
    tenant_id = None
    try:
        result = await executor.execute(
            action, tokens["sys_user"], tokens["sys_token"], None
        )
        assert result.success, result.message
        tenant_id = result.data["tenantId"]
        assert result.data["provisioned"] is True

        response = await http.get(
            f"{thingsboard.base_url}/api/tenant/{tenant_id}",
            headers={"X-Authorization": f"Bearer {tokens['sys_token']}"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == title
    finally:
        if tenant_id:
            await _quiet(thingsboard.delete_tenant(tokens["sys_token"], tenant_id))


@pytest.mark.asyncio
async def test_create_product_and_device(
    http,
    thingsboard: ThingsBoardClient,
    thing_model: ThingModelClient,
    executor: AgentActionExecutor,
    tokens,
) -> None:
    product_id = f"AIE2E{uuid4().hex[:8].upper()}"
    tsl = json.loads(TSL_PATH.read_text(encoding="utf-8"))
    tsl["profile"]["ProductId"] = product_id
    device_id = None
    device_name = f"AI_E2E_{uuid4().hex[:8]}"
    try:
        product_result = await executor.execute(
            AgentAction(
                id=uuid4().hex,
                type="create_product",
                params={
                    "product_id": product_id,
                    "name": f"AI Agent Product {product_id}",
                    "model": product_id,
                    "category_id": "1",
                    "tsl_version": tsl.get("version", "1.0"),
                },
            ),
            tokens["tenant_user"],
            tokens["tenant_token"],
            tsl,
        )
        assert product_result.success, product_result.message
        assert product_result.data["productId"] == product_id
        assert product_result.data["tbProfileId"]

        device_result = await executor.execute(
            AgentAction(
                id=uuid4().hex,
                type="create_device",
                params={
                    "product_id": product_id,
                    "device_name": device_name,
                    "label": "AI 测试设备",
                    "site_code": "E2E",
                },
            ),
            tokens["tenant_user"],
            tokens["tenant_token"],
            None,
        )
        assert device_result.success, device_result.message
        device_id = device_result.data["deviceId"]
        assert device_id

        response = await http.get(
            f"{thingsboard.base_url}/api/device/{device_id}",
            headers={"X-Authorization": f"Bearer {tokens['tenant_token']}"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == device_name
    finally:
        if device_id:
            await _quiet(thingsboard.delete_device(tokens["tenant_token"], device_id))
        await _quiet(thing_model.delete_product(tokens["tenant_token"], product_id))


@pytest.mark.skipif(
    os.getenv("TB_TEST_SMTP_ENABLED", "").lower() != "true",
    reason="Set TB_TEST_SMTP_ENABLED=true to test activation email creation",
)
@pytest.mark.asyncio
async def test_create_tenant_admin(
    thingsboard: ThingsBoardClient,
    executor: AgentActionExecutor,
    tokens,
) -> None:
    tenant_id = tokens["tenant_user"].tenant_id
    email = f"ai-agent-{uuid4().hex[:8]}@example.com"
    user_id = None
    try:
        result = await executor.execute(
            AgentAction(
                id=uuid4().hex,
                type="create_tenant_admin",
                params={
                    "tenant_id": tenant_id,
                    "email": email,
                    "first_name": "AI",
                    "last_name": "Agent",
                },
            ),
            tokens["sys_user"],
            tokens["sys_token"],
            None,
        )
        assert result.success, result.message
        user_id = result.data["userId"]
        assert user_id
        assert result.data["email"] == email
    finally:
        if user_id:
            await _quiet(thingsboard.delete_user(tokens["sys_token"], user_id))


async def _quiet(coro) -> None:
    try:
        await coro
    except Exception as exc:
        logger.warning("Integration cleanup failed: %s", exc)
