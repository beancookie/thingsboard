import re
from typing import Any

PATH_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

CAMERA_FIELDS = (
    "path",
    "display_name",
    "location",
    "description",
    "enabled",
    "push_username",
    "push_password",
)


def is_valid_path(path: str) -> bool:
    return bool(PATH_PATTERN.match(path or ""))


def row_to_camera(row: Any) -> dict[str, Any]:
    camera = dict(row)
    camera["enabled"] = bool(camera.get("enabled"))
    return camera
