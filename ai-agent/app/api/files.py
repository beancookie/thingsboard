from fastapi import APIRouter, File, Request, UploadFile

from app.agent.models import AgentFile
from app.agent.orchestrator import AgentService
from app.api.utils import extract_token

router = APIRouter(tags=["files"])


@router.post("/files", response_model=AgentFile)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
) -> AgentFile:
    token = extract_token(request)
    agent: AgentService = request.app.state.agent
    user = await agent.verify_token(token)
    data = await file.read(agent.file_store.max_bytes + 1)
    owner = user.user_id or user.email or "unknown"
    return agent.file_store.create(
        data,
        file.filename or "upload.bin",
        file.content_type or "application/octet-stream",
        owner,
    )
