from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from threading import Lock
from uuid import uuid4

from app.agent.models import AgentFile
from app.common.errors import AgentError

_INVALID_FILENAME = re.compile(r"[^\w.\- ]+", re.UNICODE)
_MAX_FILENAME_LENGTH = 255


@dataclass
class StoredFile:
    id: str
    name: str
    mime_type: str
    data: bytes
    user_id: str
    expires_at: float


class FileStore:
    def __init__(self, ttl_seconds: int = 600, max_bytes: int = 2_000_000):
        self._files: dict[str, StoredFile] = {}
        self._lock = Lock()
        self._ttl_seconds = max(1, ttl_seconds)
        self._max_bytes = max(1, max_bytes)

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    def create(
        self,
        data: bytes,
        name: str,
        mime_type: str,
        user_id: str,
    ) -> AgentFile:
        if len(data) > self._max_bytes:
            raise AgentError(
                f"文件不能超过 {self._max_bytes} 字节",
                status_code=413,
                code="FILE_TOO_LARGE",
            )
        filename = self._safe_name(name)
        now = time.monotonic()
        stored = StoredFile(
            id=uuid4().hex,
            name=filename,
            mime_type=mime_type or "application/octet-stream",
            data=data,
            user_id=user_id,
            expires_at=now + self._ttl_seconds,
        )
        with self._lock:
            self._purge_expired(now)
            self._files[stored.id] = stored
        return self.to_agent_file(stored)

    def get(self, file_id: str, user_id: str) -> StoredFile | None:
        now = time.monotonic()
        with self._lock:
            self._purge_expired(now)
            stored = self._files.get(file_id)
            if stored is None or stored.user_id != user_id:
                return None
            return stored

    def to_agent_file(self, stored: StoredFile) -> AgentFile:
        return AgentFile(
            id=stored.id,
            name=stored.name,
            mime_type=stored.mime_type,
            size=len(stored.data),
        )

    def clear(self) -> None:
        with self._lock:
            self._files.clear()

    def _purge_expired(self, now: float) -> None:
        expired = [
            file_id for file_id, stored in self._files.items()
            if stored.expires_at <= now
        ]
        for file_id in expired:
            self._files.pop(file_id, None)

    @staticmethod
    def _safe_name(name: str) -> str:
        value = unicodedata.normalize("NFC", name or "")
        value = value.replace("\\", "/").rsplit("/", 1)[-1]
        value = "".join(ch for ch in value if unicodedata.category(ch)[0] != "C")
        value = _INVALID_FILENAME.sub("_", value).strip(" .")
        if not value:
            return "upload.bin"
        if len(value) <= _MAX_FILENAME_LENGTH:
            return value
        stem, dot, suffix = value.rpartition(".")
        if dot and stem and len(suffix) <= 16:
            keep = _MAX_FILENAME_LENGTH - len(suffix) - 1
            stem = stem[:keep].rstrip(" ._") or "file"
            return f"{stem}.{suffix}"
        return value[:_MAX_FILENAME_LENGTH].rstrip(" ._") or "upload.bin"
