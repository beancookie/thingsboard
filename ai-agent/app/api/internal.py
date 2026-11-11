import secrets
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.agent.api_catalog import ServiceName
from app.common.errors import AgentError, AgentForbidden

router = APIRouter(tags=["internal"], prefix="/internal")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    service: ServiceName | None = None
    limit: int = Field(default=5, ge=1, le=10)


class CallRequest(BaseModel):
    session_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


@router.post("/dsh/api/search")
async def search_api_operations(payload: SearchRequest, request: Request) -> list[dict[str, Any]]:
    _verify_internal_token(request)
    gateway = _gateway(request)
    return gateway.search(payload.query, service=payload.service, limit=payload.limit)


@router.post("/dsh/api/call")
async def call_api_operation(payload: CallRequest, request: Request) -> dict[str, Any]:
    _verify_internal_token(request)
    gateway = _gateway(request)
    return await gateway.call(payload.session_id, payload.operation_id, payload.params)


def _verify_internal_token(request: Request) -> None:
    configured = request.app.state.settings.internal_tool_token
    if configured is None or not configured.get_secret_value():
        raise AgentError(
            "内部工具接口未配置",
            status_code=503,
            code="INTERNAL_TOOL_DISABLED",
        )
    provided = request.headers.get("X-Internal-Token") or ""
    if not secrets.compare_digest(provided, configured.get_secret_value()):
        raise AgentForbidden("内部工具接口认证失败")


def _gateway(request: Request):
    gateway = getattr(request.app.state.agent, "tool_gateway", None)
    if gateway is None:
        raise AgentError(
            "API 目录未初始化",
            status_code=503,
            code="API_CATALOG_UNAVAILABLE",
        )
    return gateway
