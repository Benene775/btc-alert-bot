"""Les tests tournent hors ligne : mode démonstration, base jetable, aucun appel API."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE.parent))

_base = Path(tempfile.mkdtemp(prefix="controle-blanc-tests-")) / "test.sqlite3"
os.environ["CB_DEMO_MODE"] = "1"
os.environ["CB_DB_PATH"] = str(_base)
os.environ["CB_ADMIN_TOKEN"] = "jeton-de-test"
os.environ["CB_PUBLIC_BASE_URL"] = "https://exemple.test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(RACINE))
from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def session(client: TestClient) -> str:
    return client.post("/api/session").json()["session_id"]


@pytest.fixture()
def photo_factice() -> bytes:
    """Un PNG minimal valide — le mode démonstration ne le regarde pas."""
    import base64

    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
