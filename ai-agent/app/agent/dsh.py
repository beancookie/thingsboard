from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from deepseek_harness import DeepSeekHarness, DeepSeekHarnessConfig, RunResult

from app.agent.models import AgentMessage
from app.agent.tsl_prompt import tsl_generation_rules
from app.auth.thingsboard import CurrentUser
from app.common.errors import AgentError, AgentUnavailable
from app.config import Settings

logger = logging.getLogger(__name__)

DSH_SYSTEM_PROMPT = """你是中国中铁物联网平台的 AI 助手。

职责：
- 帮助平台管理员查询和操作 ThingsBoard 与 thing-model。
- 任何平台操作必须先调用 search_api_operations，拿到 operation_id 后再调用 call_api_operation。
- 不得编造 operation_id，不得访问目录之外的接口。
- 普通写操作只生成待确认动作，不要声称已经执行。
- 查询遥测时，先通过设备名称查询设备 UUID，再调用 telemetry 接口。
- 没有遥测键时，先查询遥测键；最新值不带 startTs/endTs，历史值带毫秒时间戳。
- 用户提供 TSL 时优先使用；未提供时根据产品名称、型号和描述生成合法 TSL，并放入 create_product 或 update_thing_model 的 tsl 参数。
- 更新已有产品物模型时，必须先搜索“更新物模型”接口，并把完整 TSL 放入 tsl 参数；不能只传 tslVersion，也不能传 tsl=null。
- 无法判断具体属性时，生成 properties 为空的最小合法 TSL，不要拒绝创建产品。
- 所有操作结果只以文本形式回复，不生成或返回文件。
- 只使用当前提供的工具，不要尝试 shell、文件、网络或未提供的工具。
- 不输出 JWT、密码、API Key、完整 TSL。
- 使用简体中文回复。
"""

DSH_SYSTEM_PROMPT = f"{DSH_SYSTEM_PROMPT}\n\n{tsl_generation_rules()}"


class DshAgentClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._harness: DeepSeekHarness | None = None
        self._run_lock = asyncio.Lock()
        self._patch_path = self._write_patch()

    async def start(self) -> None:
        await asyncio.to_thread(self._ensure_started)

    async def run(self, session_id: str, input_text: str) -> RunResult:
        async with self._run_lock:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._run_sync, session_id, input_text),
                    timeout=self._settings.dsh_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                raise AgentUnavailable("AI 模型响应超时，请稍后重试") from exc
            except AgentError:
                raise
            except Exception as exc:
                logger.exception("DSH run failed")
                raise AgentUnavailable("AI 模型调用失败，请稍后重试") from exc

    async def close(self) -> None:
        harness = self._harness
        self._harness = None
        if harness is not None:
            await asyncio.to_thread(harness.close)

    def _run_sync(self, session_id: str, input_text: str) -> RunResult:
        harness = self._ensure_started()
        return harness.run(input_text, session_id=session_id)

    def _ensure_started(self) -> DeepSeekHarness:
        if self._harness is not None:
            return self._harness

        settings = self._settings
        deepseek_key = (
            settings.deepseek_api_key.get_secret_value()
            if settings.deepseek_api_key is not None
            else ""
        )
        openai_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key is not None
            else ""
        )
        api_key = deepseek_key or openai_key
        if not api_key:
            raise AgentUnavailable("AI Agent 未配置 DeepSeek API Key")

        home = Path(settings.dsh_home)
        workspace = Path(settings.dsh_workspace)
        home.mkdir(parents=True, exist_ok=True)
        workspace.mkdir(parents=True, exist_ok=True)

        internal_token = (
            settings.internal_tool_token.get_secret_value()
            if settings.internal_tool_token is not None
            else ""
        )
        if not internal_token:
            raise AgentUnavailable("AI Agent 未配置内部工具令牌")

        config = DeepSeekHarnessConfig(
            dsh_home=str(home.resolve()),
            cwd=str(workspace.resolve()),
            profile=settings.dsh_profile,
            patches=(str(self._patch_path),),
            provider=settings.dsh_provider,
            model=settings.dsh_model,
            api_key=api_key,
            base_url=settings.deepseek_base_url,
            max_tokens=settings.max_tokens,
            request_timeout_seconds=settings.dsh_timeout_seconds,
            env={
                "DSH_SYSTEM_PROMPT": DSH_SYSTEM_PROMPT,
                "THINGSBOARD_AGENT_URL": settings.internal_agent_url,
                "THINGSBOARD_AGENT_TOKEN": internal_token,
            },
        )
        harness = DeepSeekHarness(config)
        harness.start()
        self._harness = harness
        return harness

    def _write_patch(self) -> Path:
        settings = self._settings
        template = Path(settings.dsh_patch_template)
        plugin = Path(settings.dsh_plugin_path)
        if not template.is_file():
            raise AgentUnavailable(f"DSH profile 补丁不存在: {template}")
        if not plugin.is_file():
            raise AgentUnavailable(f"DSH 插件不存在: {plugin}")

        home = Path(settings.dsh_home)
        home.mkdir(parents=True, exist_ok=True)
        patch = home / "thingsboard.patch.yml"
        content = template.read_text(encoding="utf-8").replace(
            "__THINGSBOARD_PLUGIN_PATH__",
            plugin.resolve().as_posix(),
        )
        patch.write_text(content, encoding="utf-8")
        return patch


def format_dsh_input(
    messages: list[AgentMessage],
    user: CurrentUser,
    *,
    tsl_attached: bool,
    max_messages: int,
    attachment_context: str = "",
) -> str:
    if not messages:
        raise AgentError("缺少对话消息", status_code=400, code="DSH_MESSAGE_REQUIRED")

    window = messages[-max_messages:] if max_messages > 0 else []
    if not window:
        raise AgentError("缺少对话消息", status_code=400, code="DSH_MESSAGE_REQUIRED")

    lines = [
        "[运行上下文]",
        f"authority: {user.authority}",
        f"tenant_id: {user.tenant_id or '无'}",
        f"tsl_attached: {'是' if tsl_attached else '否'}",
        "",
    ]
    if attachment_context:
        lines.extend(["[附件内容]", attachment_context, ""])
    if len(window) > 1:
        lines.append("[对话历史]")
        for message in window[:-1]:
            lines.append(f"{message.role}: {message.content}")
        lines.append("")
    last = window[-1]
    lines.extend(["[当前请求]", f"{last.role}: {last.content}"])
    return "\n".join(lines)
