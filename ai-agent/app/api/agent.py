from fastapi import APIRouter, Request

from app.agent.models import AgentChatRequest, AgentChatResponse
from app.agent.orchestrator import AgentService
from app.api.utils import extract_token

router = APIRouter(tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def chat(payload: AgentChatRequest, request: Request) -> AgentChatResponse:
    token = extract_token(request)
    agent: AgentService = request.app.state.agent
    user = await agent.verify_token(token)
    return await agent.chat(payload, token, user)
