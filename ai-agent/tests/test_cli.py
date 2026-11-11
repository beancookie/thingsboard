import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

import app.cli as cli
from app.clients.thingsboard import ThingsBoardClient


@pytest.fixture
def catalog_dir(tmp_path: Path) -> Path:
    (tmp_path / "thingsboard.yaml").write_text(
        """
- id: thingsboard.listTenants
  service: thingsboard
  method: GET
  path: /api/tenants
  summary: 查询租户列表
  aliases: [租户]
  mode: read
  code_access: read
  permission: SYS_ADMIN
  risk: low
  params: {}

- id: thingsboard.createTenant
  service: thingsboard
  method: POST
  path: /api/tenant
  summary: 创建租户
  aliases: [创建租户]
  mode: write
  code_access: write
  permission: SYS_ADMIN
  risk: medium
  handler: create_tenant
  params:
    title:
      in: body
      type: string
      required: true
""",
        encoding="utf-8",
    )
    (tmp_path / "overrides.yaml").write_text("{}\n", encoding="utf-8")
    return tmp_path


def test_catalog_validate_and_search(catalog_dir: Path, capsys) -> None:
    assert cli.main(["catalog", "validate", "--catalog-dir", str(catalog_dir), "--json"]) == 0
    validate_output = capsys.readouterr().out
    assert json.loads(validate_output)["operations"] == 2

    assert cli.main(
        ["catalog", "search", "租户", "--catalog-dir", str(catalog_dir), "--json"]
    ) == 0
    results = json.loads(capsys.readouterr().out)
    assert results[0]["id"] == "thingsboard.listTenants"


def test_catalog_show(catalog_dir: Path, capsys) -> None:
    assert cli.main(
        [
            "catalog",
            "show",
            "thingsboard.listTenants",
            "--catalog-dir",
            str(catalog_dir),
            "--json",
        ]
    ) == 0

    data = json.loads(capsys.readouterr().out)
    assert data["id"] == "thingsboard.listTenants"
    assert data["mode"] == "read"


def test_catalog_call_read(monkeypatch, catalog_dir: Path, capsys) -> None:
    async def fake_request(self, method, path, token, *, params=None, json=None):
        return {"data": [{"id": "tenant-1"}]}

    monkeypatch.setattr(ThingsBoardClient, "request", fake_request)

    assert cli.main(
        [
            "catalog",
            "call",
            "thingsboard.listTenants",
            "--token",
            "token",
            "--authority",
            "SYS_ADMIN",
            "--catalog-dir",
            str(catalog_dir),
        ]
    ) == 0

    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "OK"
    assert data["data"]["data"][0]["id"] == "tenant-1"


def test_catalog_call_write_only_proposes(monkeypatch, catalog_dir: Path, capsys) -> None:
    async def fake_request(self, method, path, token, *, params=None, json=None):
        raise AssertionError("写操作不应调用后端")

    monkeypatch.setattr(ThingsBoardClient, "request", fake_request)

    assert cli.main(
        [
            "catalog",
            "call",
            "thingsboard.createTenant",
            "--token",
            "token",
            "--authority",
            "SYS_ADMIN",
            "--params",
            '{"title":"测试"}',
            "--catalog-dir",
            str(catalog_dir),
        ]
    ) == 0

    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "PROPOSED"
    assert data["operation_id"] == "thingsboard.createTenant"
    assert data["risk"] == "medium"


def test_chat_posts_request(capsys) -> None:
    with respx.mock(base_url="http://test") as mock:
        route = mock.post("/chat").mock(
            return_value=httpx.Response(
                200,
                json={
                    "reply": "你好",
                    "actions": [],
                    "executed": [],
                },
            )
        )
        assert cli.main(
            [
                "chat",
                "你好",
                "--token",
                "token",
                "--url",
                "http://test",
                "--json",
            ]
        ) == 0

    assert route.called
    data = json.loads(capsys.readouterr().out)
    assert data["reply"] == "你好"


def test_chat_defaults_to_top_level_message(capsys) -> None:
    with respx.mock(base_url="http://test") as mock:
        route = mock.post("/chat").mock(
            return_value=httpx.Response(
                200,
                json={"reply": "你好", "actions": [], "executed": []},
            )
        )
        assert cli.main(
            ["你好", "--token", "token", "--url", "http://test", "--json"]
        ) == 0

    assert route.called
    assert json.loads(capsys.readouterr().out)["reply"] == "你好"


def test_chat_uses_token_from_environment(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AI_AGENT_CLI_TOKEN", "env-token")

    with respx.mock(base_url="http://test") as mock:
        route = mock.post("/chat").mock(
            return_value=httpx.Response(
                200,
                json={"reply": "ok", "actions": [], "executed": []},
            )
        )
        assert cli.main(["chat", "你好", "--url", "http://test", "--json"]) == 0

    assert route.called
    assert route.calls[-1].request.headers["X-Authorization"] == "Bearer env-token"
    assert json.loads(capsys.readouterr().out)["reply"] == "ok"


def test_chat_interactive_mode(monkeypatch, capsys) -> None:
    inputs = iter(["你好", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    with respx.mock(base_url="http://test") as mock:
        route = mock.post("/chat").mock(
            return_value=httpx.Response(
                200,
                json={"reply": "你好呀", "actions": [], "executed": []},
            )
        )
        assert cli.main(
            ["chat", "--token", "token", "--url", "http://test", "--interactive"]
        ) == 0

    assert route.called
    output = capsys.readouterr().out
    assert "AI>" in output
    assert "你好呀" in output


def test_chat_reports_http_error(capsys) -> None:
    with respx.mock(base_url="http://test") as mock:
        mock.post("/chat").mock(
            return_value=httpx.Response(
                403,
                json={"code": "FORBIDDEN", "message": "没有权限"},
            )
        )
        assert cli.main(
            ["chat", "你好", "--token", "token", "--url", "http://test", "--json"]
        ) == 1

    data = json.loads(capsys.readouterr().out)
    assert data["code"] == "FORBIDDEN"


def test_dsh_smoke_uses_client(monkeypatch, capsys) -> None:
    calls: list[str] = []

    class FakeDsh:
        def __init__(self, settings):
            self.settings = settings

        async def start(self) -> None:
            calls.append("start")

        async def run(self, session_id: str, input_text: str):
            calls.append("run")
            return type("Result", (), {"final_response": "ok", "finish_reason": "completed"})()

        async def close(self) -> None:
            calls.append("close")

    monkeypatch.setattr(cli, "DshAgentClient", FakeDsh)

    assert cli.main(["dsh", "smoke", "--json"]) == 0
    assert calls == ["start", "close"]

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ok"


def test_config_show_redacts_secrets(monkeypatch, capsys) -> None:
    monkeypatch.setenv("AI_AGENT_OPENAI_API_KEY", "super-secret")
    monkeypatch.setenv("AI_AGENT_INTERNAL_TOOL_TOKEN", "internal-secret")

    assert cli.main(["config", "show"]) == 0

    output = capsys.readouterr().out
    assert "super-secret" not in output
    assert "internal-secret" not in output
    assert '"***"' in output


def test_openapi_import_delegates(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_main(argv):
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(cli.openapi_importer, "main", fake_main)

    assert cli.main(
        [
            "openapi",
            "import",
            "--service",
            "thingsboard",
            "--spec",
            "spec.json",
            "--out",
            "out.yaml",
            "--overrides",
            "overrides.yaml",
            "--check",
        ]
    ) == 0

    assert captured["argv"] == [
        "--service",
        "thingsboard",
        "--spec",
        "spec.json",
        "--out",
        "out.yaml",
        "--overrides",
        "overrides.yaml",
        "--check",
    ]
