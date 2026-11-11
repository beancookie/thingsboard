from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.agent.dsh import DshAgentClient, format_dsh_input
from app.agent.models import AgentAction, AgentChatRequest, AgentMessage
from app.agent.orchestrator import AgentService
from app.common.errors import AgentError, AgentUnavailable
from app.config import Settings


def test_format_dsh_input_includes_context_and_history(tenant_admin) -> None:
    text = format_dsh_input(
        [
            AgentMessage(role="user", content="查询租户"),
            AgentMessage(role="assistant", content="请稍等"),
            AgentMessage(role="user", content="继续"),
        ],
        tenant_admin,
        tsl_attached=True,
        max_messages=3,
    )

    assert "[运行上下文]" in text
    assert "authority: TENANT_ADMIN" in text
    assert "tenant_id: tenant-1" in text
    assert "tsl_attached: 是" in text
    assert "[对话历史]" in text
    assert "user: 查询租户" in text
    assert "[当前请求]" in text
    assert "user: 继续" in text


def test_format_dsh_input_rejects_empty_messages(tenant_admin) -> None:
    with pytest.raises(AgentError) as error:
        format_dsh_input([], tenant_admin, tsl_attached=False, max_messages=20)

    assert error.value.code == "DSH_MESSAGE_REQUIRED"


def test_dsh_client_writes_patch(tmp_path: Path, settings: Settings) -> None:
    template = tmp_path / "thingsboard.patch.yml"
    template.write_text(
        "- insert:\n    - id: thingsboard-api\n      name: '__THINGSBOARD_PLUGIN_PATH__'\n",
        encoding="utf-8",
    )
    plugin = tmp_path / "plugin" / "index.js"
    plugin.parent.mkdir()
    plugin.write_text("export function apply() {}\n", encoding="utf-8")

    settings.dsh_home = str(tmp_path / "home")
    settings.dsh_patch_template = str(template)
    settings.dsh_plugin_path = str(plugin)

    client = DshAgentClient(settings)

    patch = tmp_path / "home" / "thingsboard.patch.yml"
    assert patch.is_file()
    assert plugin.resolve().as_posix() in patch.read_text(encoding="utf-8")
    assert client is not None


def test_dsh_client_requires_api_key(tmp_path: Path, settings: Settings) -> None:
    template = tmp_path / "thingsboard.patch.yml"
    template.write_text("- insert: []\n", encoding="utf-8")
    plugin = tmp_path / "index.js"
    plugin.write_text("export function apply() {}\n", encoding="utf-8")

    settings.dsh_home = str(tmp_path / "home")
    settings.dsh_patch_template = str(template)
    settings.dsh_plugin_path = str(plugin)
    settings.deepseek_api_key = None
    settings.openai_api_key = None

    client = DshAgentClient(settings)

    with pytest.raises(AgentUnavailable, match="API Key"):
        client._ensure_started()


def test_dsh_client_builds_runtime_config(
    tmp_path: Path,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = tmp_path / "thingsboard.patch.yml"
    template.write_text("- insert: []\n", encoding="utf-8")
    plugin = tmp_path / "index.js"
    plugin.write_text("export function apply() {}\n", encoding="utf-8")

    class FakeHarness:
        def __init__(self, config):
            self.config = config
            self.started = False

        def start(self) -> None:
            self.started = True

        def close(self) -> None:
            pass

    monkeypatch.setattr("app.agent.dsh.DeepSeekHarness", FakeHarness)

    settings.dsh_home = str(tmp_path / "home")
    settings.dsh_patch_template = str(template)
    settings.dsh_plugin_path = str(plugin)
    settings.deepseek_api_key = SecretStr("dummy")
    settings.internal_tool_token = SecretStr("tool-token")
    settings.internal_agent_url = "http://127.0.0.1:9000"
    settings.dsh_model = "deepseek-v4-flash"

    client = DshAgentClient(settings)
    harness = client._ensure_started()

    assert isinstance(harness, FakeHarness)
    assert harness.started is True
    assert harness.config.profile == "sdk-minimal"
    assert harness.config.model == "deepseek-v4-flash"
    assert harness.config.api_key == "dummy"
    assert harness.config.env["THINGSBOARD_AGENT_URL"] == "http://127.0.0.1:9000"
    assert harness.config.env["THINGSBOARD_AGENT_TOKEN"] == "tool-token"
    assert harness.config.patches == (str(tmp_path / "home" / "thingsboard.patch.yml"),)


def test_dsh_client_requires_internal_token(tmp_path: Path, settings: Settings) -> None:
    template = tmp_path / "thingsboard.patch.yml"
    template.write_text("- insert: []\n", encoding="utf-8")
    plugin = tmp_path / "index.js"
    plugin.write_text("export function apply() {}\n", encoding="utf-8")

    settings.dsh_home = str(tmp_path / "home")
    settings.dsh_patch_template = str(template)
    settings.dsh_plugin_path = str(plugin)
    settings.deepseek_api_key = SecretStr("dummy")
    settings.internal_tool_token = None

    client = DshAgentClient(settings)

    with pytest.raises(AgentUnavailable, match="内部工具令牌"):
        client._ensure_started()


@pytest.mark.asyncio
async def test_agent_service_dsh_chat_drains_proposals(
    tmp_path: Path,
    settings: Settings,
    tenant_admin,
) -> None:
    template = tmp_path / "thingsboard.patch.yml"
    template.write_text("- insert: []\n", encoding="utf-8")
    plugin = tmp_path / "index.js"
    plugin.write_text("export function apply() {}\n", encoding="utf-8")

    settings.engine = "dsh"
    settings.dsh_home = str(tmp_path / "home")
    settings.dsh_patch_template = str(template)
    settings.dsh_plugin_path = str(plugin)
    settings.dsh_timeout_seconds = 5

    service = AgentService(settings)

    class FakeDsh:
        async def run(self, session_id: str, input_text: str):
            service._sessions.add_proposal(
                session_id,
                AgentAction(
                    id="a1",
                    type="thingsboard.createTenant",
                    summary="创建租户",
                    params={"title": "Test"},
                    risk="medium",
                ),
            )
            return SimpleNamespace(
                final_response="已生成待确认操作",
                finish_reason="completed",
            )

        async def close(self) -> None:
            pass

    service._dsh = FakeDsh()

    response = await service.chat(
        AgentChatRequest(
            mode="chat",
            messages=[AgentMessage(role="user", content="创建租户")],
        ),
        "token",
        tenant_admin,
    )

    assert response.reply == "已生成待确认操作"
    assert len(response.actions) == 1
    assert response.actions[0].risk == "medium"
    await service.close()

