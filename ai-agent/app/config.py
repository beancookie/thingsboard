from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AI_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = True
    engine: Literal["openai", "dsh"] = "openai"
    openai_base_url: str = "https://api.deepseek.com/v1"
    openai_api_key: SecretStr | None = None
    openai_model: str = "deepseek-chat"
    timeout_seconds: float = 60.0
    max_tokens: int = 2048

    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str | None = None
    dsh_home: str = ".dsh-home"
    dsh_workspace: str = ".dsh-workspace"
    dsh_profile: str = "sdk-minimal"
    dsh_patch_template: str = "dsh/thingsboard.patch.yml"
    dsh_plugin_path: str = "dsh-plugin-thingsboard/index.js"
    dsh_provider: str = "deepseek-official"
    dsh_model: str = "deepseek-v4-flash"
    dsh_timeout_seconds: float = 60.0
    internal_agent_url: str = "http://127.0.0.1:8000"

    thing_model_url: str = "http://thing-model:8090"
    thingsboard_url: str = "http://thingsboard:8080"
    auth_cache_seconds: int = 60

    max_messages: int = 20
    max_tsl_bytes: int = 2_000_000
    max_actions: int = 10
    max_tool_rounds: int = 8

    api_catalog_dir: str = "config/api"
    api_max_response_bytes: int = 262_144
    internal_tool_token: SecretStr | None = None
    file_ttl_seconds: int = 600
    file_max_bytes: int = 2_000_000
    file_text_max_bytes: int = 65_536


@lru_cache
def get_settings() -> Settings:
    return Settings()
