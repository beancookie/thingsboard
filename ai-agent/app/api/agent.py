from fastapi import APIRouter, Request

from app.agent.models import AgentChatRequest, AgentChatResponse
from app.agent.orchestrator import AgentService
from app.common.errors import AgentUnauthorized

router = APIRouter(tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def chat(payload: AgentChatRequest, request: Request) -> AgentChatResponse:
    token = _extract_token(request)
    agent: AgentService = request.app.state.agent
    user = await agent.verify_token(token)
    return await agent.chat(payload, token, user)


def _extract_token(request: Request) -> str:
    value = request.headers.get("X-Authorization") or request.headers.get("Authorization")
    if not value or not value.strip():
        raise AgentUnauthorized("缺少访问令牌")
    token = value.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        raise AgentUnauthorized("缺少访问令牌")
    return token
