from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from app.agent.api_catalog import ApiCatalog, ServiceName
from app.agent.api_executor import ApiExecutor
from app.agent.models import AgentAction
from app.agent.sessions import SessionStore
from app.common.errors import AgentError

logger = logging.getLogger(__name__)


class AgentToolGateway:
    def __init__(
        self,
        catalog: ApiCatalog,
        executor: ApiExecutor,
        sessions: SessionStore,
    ):
        self._catalog = catalog
        self._executor = executor
        self._sessions = sessions

    @property
    def catalog(self) -> ApiCatalog:
        return self._catalog

    @property
    def sessions(self) -> SessionStore:
        return self._sessions

    def search(
        self,
        query: str,
        *,
        service: ServiceName | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        return [
            self._catalog.search_result(operation)
            for operation in self._catalog.search(query, service=service, limit=limit)
        ]

    async def call(
        self,
        session_id: str,
        operation_id: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return _error("SESSION_NOT_FOUND", "会话不存在或已过期")

        operation = self._catalog.get(operation_id)
        if operation is None or not operation.enabled:
            return _error("OPERATION_NOT_FOUND", "未找到或未启用该接口")

        try:
            values = dict(params or {})
            if (
                session.tsl is not None
                and "tsl" in operation.params
                and values.get("tsl") is None
            ):
                values["tsl"] = session.tsl

            if operation.mode == "read":
                data = await self._executor.execute(
                    operation,
                    session.token,
                    session.user,
                    values,
                )
                return {"status": "OK", "data": data}

            self._executor.prepare(operation, values, session.user)
            action = AgentAction(
                id=uuid4().hex,
                type=operation.id,
                summary=operation.summary,
                params=values,
                status="PROPOSED",
                risk=operation.risk,
            )
            self._sessions.add_proposal(session_id, action)
            return {
                "status": "PROPOSED",
                "action_id": action.id,
                "operation_id": operation.id,
                "summary": operation.summary,
                "risk": operation.risk,
            }
        except AgentError as exc:
            return _error(exc.code, exc.message)
        except Exception:
            logger.exception("API operation failed: %s", operation_id)
            return _error("API_EXECUTION_FAILED", "接口执行失败，请查看服务日志")


def _error(code: str, message: str) -> dict[str, Any]:
    return {"status": "ERROR", "code": code, "message": message}
