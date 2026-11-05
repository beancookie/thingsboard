import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.agent.orchestrator import AgentService
from app.api import agent, health
from app.common.errors import AgentError
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.agent = AgentService(settings)
    logger.info("AI Agent started: enabled=%s model=%s", settings.enabled, settings.openai_model)
    try:
        yield
    finally:
        await app.state.agent.close()


app = FastAPI(
    title="Thing Model AI Agent",
    version="0.1.0",
    docs_url="/swagger-ui.html",
    redoc_url=None,
    lifespan=lifespan,
)
app.include_router(health.router)
app.include_router(agent.router)


@app.exception_handler(AgentError)
async def handle_agent_error(_: Request, exc: AgentError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message, "code": exc.code},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "message": "请求参数校验失败",
            "code": "BAD_REQUEST",
            "issues": exc.errors(),
        },
    )
