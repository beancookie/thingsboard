from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEDIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    root_path: str = ""
    db_path: str = "./data/media.db"

    mediamtx_rtsp_host: str = "129.211.239.229"
    mediamtx_rtsp_port: int = 8554
    mediamtx_hls_public_url: str = "http://129.211.239.229:8888"
    mediamtx_webrtc_public_url: str = "http://129.211.239.229:8889"


@lru_cache
def get_settings() -> Settings:
    return Settings()
