import asyncio
import hashlib
import time

import httpx
from pydantic import BaseModel

from app.common.errors import AgentUnauthorized, AgentUnavailable


class CurrentUser(BaseModel):
    user_id: str | None = None
    tenant_id: str | None = None
    authority: str
    email: str | None = None

    @property
    def is_sys_admin(self) -> bool:
        return self.authority.upper() == "SYS_ADMIN"

    @property
    def is_tenant_admin(self) -> bool:
        return self.authority.upper() == "TENANT_ADMIN"


class ThingsBoardAuth:
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        cache_seconds: int = 60,
    ):
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._cache_seconds = cache_seconds
        self._cache: dict[str, tuple[CurrentUser, float]] = {}
        self._lock = asyncio.Lock()

    async def verify(self, raw_token: str) -> CurrentUser:
        token = normalize_token(raw_token)
        key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and cached[1] > now:
            return cached[0]

        async with self._lock:
            cached = self._cache.get(key)
            if cached and cached[1] > now:
                return cached[0]

            try:
                response = await self._client.get(
                    f"{self._base_url}/api/auth/user",
                    headers=auth_headers(token),
                )
            except httpx.HTTPError as exc:
                raise AgentUnavailable("无法连接 ThingsBoard 校验登录状态") from exc

            if response.status_code == 401:
                raise AgentUnauthorized()
            if response.status_code >= 400:
                raise AgentUnavailable(
                    f"ThingsBoard 用户校验失败: HTTP {response.status_code}"
                )

            payload = response.json()
            tenant_id = _entity_id(payload.get("tenantId"))
            user = CurrentUser(
                user_id=_entity_id(payload.get("id")),
                tenant_id=tenant_id,
                authority=str(payload.get("authority") or ""),
                email=payload.get("email"),
            )
            self._cache[key] = (user, now + self._cache_seconds)
            return user


def normalize_token(token: str) -> str:
    value = (token or "").strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    if not value:
        raise AgentUnauthorized()
    return value


def auth_headers(token: str) -> dict[str, str]:
    return {"X-Authorization": f"Bearer {token}"}


def _entity_id(value) -> str | None:
    if isinstance(value, dict):
        entity_id = value.get("id")
        return str(entity_id) if entity_id else None
    if value:
        return str(value)
    return None
