from functools import lru_cache

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
    openai_base_url: str = "https://api.deepseek.com/v1"
    openai_api_key: SecretStr | None = None
    openai_model: str = "deepseek-chat"
    timeout_seconds: float = 60.0
    max_tokens: int = 2048

    thing_model_url: str = "http://thing-model:8090"
    thingsboard_url: str = "http://thingsboard:8080"
    auth_cache_seconds: int = 60

    max_messages: int = 20
    max_tsl_bytes: int = 2_000_000
    max_actions: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
