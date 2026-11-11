import re
from typing import Any
from urllib.parse import quote

from app.config import Settings

_MASK_PATTERN = re.compile(r"(://[^:/@]+):[^@]*@")


def build_push_url(camera: dict[str, Any], settings: Settings) -> str:
    protocol = camera.get("push_protocol") or "rtsp"
    username = quote(camera.get("push_username") or "", safe="")
    password = quote(camera.get("push_password") or "", safe="")
    auth = f"{username}:{password}@" if (username or password) else ""
    return f"{protocol}://{auth}{settings.mediamtx_rtsp_host}:{settings.mediamtx_rtsp_port}/{camera['path']}"


def mask_push_url(push_url: str) -> str:
    return _MASK_PATTERN.sub(r"\1:***@", push_url)


def build_hls_preview_url(camera: dict[str, Any], settings: Settings) -> str:
    base = settings.mediamtx_hls_public_url.rstrip("/")
    return f"{base}/{camera['path']}/"


def build_webrtc_preview_url(camera: dict[str, Any], settings: Settings) -> str:
    base = settings.mediamtx_webrtc_public_url.rstrip("/")
    return f"{base}/{camera['path']}/"
