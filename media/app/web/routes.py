from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.config import get_settings
from app.models import is_valid_path
from app.utils import (
    build_hls_preview_url,
    build_push_url,
    build_webrtc_preview_url,
    mask_push_url,
)

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def app_path(path: str) -> str:
    root = get_settings().root_path.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{root}{path}" if root else path


templates.env.globals["app_path"] = app_path


def _render(request: Request, name: str, **context: Any) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=context,
    )


def _enrich(cameras: list[dict[str, Any]]) -> list[dict[str, Any]]:
    settings = get_settings()
    for camera in cameras:
        camera["push_url"] = build_push_url(camera, settings)
        camera["push_url_masked"] = mask_push_url(camera["push_url"])
        camera["hls_preview_url"] = build_hls_preview_url(camera, settings)
        camera["webrtc_preview_url"] = build_webrtc_preview_url(camera, settings)
    return cameras


def _camera_values(
    path: str,
    display_name: str,
    location: str,
    description: str,
    enabled: bool,
    push_username: str,
    push_password: str,
) -> dict[str, Any]:
    return {
        "path": path,
        "display_name": display_name,
        "location": location,
        "description": description,
        "enabled": enabled,
        "push_username": push_username,
        "push_password": push_password,
    }


@router.get("/", include_in_schema=False)
async def index() -> RedirectResponse:
    return RedirectResponse(app_path("/cameras"), status_code=303)


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@router.get("/api/cameras/{camera_id}")
async def camera_detail(camera_id: int) -> JSONResponse:
    camera = db.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="摄像头不存在")
    return JSONResponse(camera)


@router.get("/cameras", response_class=HTMLResponse)
async def camera_list(request: Request) -> HTMLResponse:
    cameras = _enrich(db.list_cameras())
    return _render(request, "cameras/list.html", cameras=cameras,
                   error=None, values=None, open_dialog=None)


@router.post("/cameras", response_class=HTMLResponse)
async def camera_create(
    request: Request,
    path: str = Form(""),
    display_name: str = Form(""),
    location: str = Form(""),
    description: str = Form(""),
    enabled: bool = Form(False),
    push_username: str = Form(""),
    push_password: str = Form(""),
) -> HTMLResponse:
    path = path.strip()
    values = _camera_values(path, display_name, location, description, enabled,
                            push_username, push_password)

    error = None
    if not is_valid_path(path):
        error = "路径只能包含字母、数字、下划线和短横线，例如 lzzz001"
    elif db.get_camera_by_path(path):
        error = "该路径已存在"

    if error:
        cameras = _enrich(db.list_cameras())
        return _render(request, "cameras/list.html", cameras=cameras,
                       error=error, values=values, open_dialog="add-dialog")

    db.create_camera(path, display_name.strip() or None, location.strip() or None,
                     description.strip() or None, enabled,
                     push_username.strip() or None, push_password.strip() or None)
    return RedirectResponse(app_path("/cameras"), status_code=303)


@router.post("/cameras/{camera_id}", response_class=HTMLResponse)
async def camera_update(
    camera_id: int,
    display_name: str = Form(""),
    location: str = Form(""),
    description: str = Form(""),
    enabled: bool = Form(False),
    push_username: str = Form(""),
    push_password: str = Form(""),
) -> RedirectResponse:
    if not db.get_camera(camera_id):
        raise HTTPException(status_code=404, detail="摄像头不存在")

    db.update_camera(camera_id, display_name.strip() or None, location.strip() or None,
                     description.strip() or None, enabled,
                     push_username.strip() or None, push_password.strip() or None)
    return RedirectResponse(app_path("/cameras"), status_code=303)


@router.post("/cameras/{camera_id}/delete", response_class=HTMLResponse)
async def camera_delete(camera_id: int) -> RedirectResponse:
    db.delete_camera(camera_id)
    return RedirectResponse(app_path("/cameras"), status_code=303)
