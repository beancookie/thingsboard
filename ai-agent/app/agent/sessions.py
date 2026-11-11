from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4

from app.agent.models import AgentAction
from app.auth.thingsboard import CurrentUser


@dataclass
class SessionContext:
    session_id: str
    token: str
    user: CurrentUser
    tsl: Any | None = None
    proposals: list[AgentAction] = field(default_factory=list)
    expires_at: float = 0.0


class SessionStore:
    def __init__(self, max_proposals: int = 10):
        self._sessions: dict[str, SessionContext] = {}
        self._lock = Lock()
        self._max_proposals = max(1, max_proposals)

    def create(
        self,
        token: str,
        user: CurrentUser,
        *,
        tsl: Any | None = None,
        ttl_seconds: float = 90.0,
    ) -> SessionContext:
        now = time.monotonic()
        context = SessionContext(
            session_id=uuid4().hex,
            token=token,
            user=user,
            tsl=tsl,
            expires_at=now + max(1.0, ttl_seconds),
        )
        with self._lock:
            self._purge_expired(now)
            self._sessions[context.session_id] = context
        return context

    def get(self, session_id: str) -> SessionContext | None:
        now = time.monotonic()
        with self._lock:
            self._purge_expired(now)
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def add_proposal(self, session_id: str, action: AgentAction) -> None:
        with self._lock:
            context = self._sessions.get(session_id)
            if context is None:
                return
            context.proposals.append(action)
            if len(context.proposals) > self._max_proposals:
                del context.proposals[: -self._max_proposals]

    def drain_proposals(self, session_id: str) -> list[AgentAction]:
        with self._lock:
            context = self._sessions.get(session_id)
            if context is None:
                return []
            proposals = list(context.proposals)
            context.proposals.clear()
            return proposals

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def _purge_expired(self, now: float) -> None:
        expired = [
            session_id
            for session_id, context in self._sessions.items()
            if context.expires_at <= now
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)
