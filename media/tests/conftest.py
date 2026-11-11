import os
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = Path(tempfile.mkdtemp())
os.environ["MEDIA_DB_PATH"] = str(_TMP_DIR / "test.db")
os.environ["MEDIA_HLS_STATUS_PROBE_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    db_file = Path(os.environ["MEDIA_DB_PATH"])
    if db_file.exists():
        db_file.unlink()
    db.init_db()
    with TestClient(app) as test_client:
        yield test_client
