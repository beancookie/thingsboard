import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models import row_to_camera

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    display_name TEXT,
    location TEXT,
    description TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    push_username TEXT,
    push_password TEXT,
    push_protocol TEXT NOT NULL DEFAULT 'rtsp',
    created_at TEXT,
    updated_at TEXT
)
"""


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    db_file = Path(settings.db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(_CREATE_TABLE)
        conn.commit()
    finally:
        conn.close()


def list_cameras() -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
    finally:
        conn.close()
    return [row_to_camera(row) for row in rows]


def get_camera(camera_id: int) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,)).fetchone()
    finally:
        conn.close()
    return row_to_camera(row) if row else None


def get_camera_by_path(path: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM cameras WHERE path = ?", (path,)).fetchone()
    finally:
        conn.close()
    return row_to_camera(row) if row else None


def create_camera(
    path: str,
    display_name: str | None,
    location: str | None,
    description: str | None,
    enabled: bool,
    push_username: str | None,
    push_password: str | None,
) -> int:
    now = _now()
    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO cameras (path, display_name, location, description, enabled,
                                 push_username, push_password, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (path, display_name, location, description, int(enabled),
             push_username, push_password, now, now),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def update_camera(
    camera_id: int,
    display_name: str | None,
    location: str | None,
    description: str | None,
    enabled: bool,
    push_username: str | None,
    push_password: str | None,
) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE cameras
            SET display_name = ?, location = ?, description = ?, enabled = ?,
                push_username = ?, push_password = ?, updated_at = ?
            WHERE id = ?
            """,
            (display_name, location, description, int(enabled),
             push_username, push_password, _now(), camera_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_camera(camera_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
        conn.commit()
    finally:
        conn.close()
