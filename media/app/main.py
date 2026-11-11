import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import get_settings
from app.web import routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    db.init_db()
    logger.info(
        "Media console started: db=%s hls=%s webrtc=%s",
        settings.db_path,
        settings.mediamtx_hls_public_url,
        settings.mediamtx_webrtc_public_url,
    )
    yield


settings = get_settings()

app = FastAPI(
    title="ThingsBoard Media Console",
    version="0.1.0",
    root_path=settings.root_path,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
app.include_router(routes.router)
