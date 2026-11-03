from typing import Any

from openai import AsyncOpenAI

from app.common.errors import AgentError, AgentUnavailable
from app.config import Settings


class OpenAiChatClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: AsyncOpenAI | None = None

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ):
        client = self._get_client()
        try:
            return await client.chat.completions.create(
                model=self._settings.openai_model,
                messages=messages,
                tools=tools or None,
                tool_choice="auto" if tools else None,
                temperature=0.2,
                max_tokens=self._settings.max_tokens,
            )
        except Exception as exc:
            raise AgentUnavailable("AI 模型调用失败，请稍后重试") from exc

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

    def _get_client(self) -> AsyncOpenAI:
        if not self._settings.openai_api_key:
            raise AgentError(
                "AI Agent 未配置 AI_AGENT_OPENAI_API_KEY",
                status_code=503,
                code="AI_NOT_CONFIGURED",
            )
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._settings.openai_api_key.get_secret_value(),
                base_url=self._settings.openai_base_url,
                timeout=self._settings.timeout_seconds,
            )
        return self._client
