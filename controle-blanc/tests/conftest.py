"""Les tests tournent hors ligne : mode démonstration, base jetable, aucun appel API."""

from __future__ import annotations

import os
import secrets
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


def adresse_neuve() -> str:
    """Une adresse par test. Le serveur ne laisse partir qu'un code par minute
    et par adresse : partager la même ferait échouer le sixième test pour une
    raison qui n'a rien à voir avec ce qu'il vérifie."""
    return f"eleve-{secrets.token_hex(4)}@exemple.test"


def entrer(c: TestClient, email: str | None = None) -> str:
    """Fait entrer le client : adresse, code reçu, cookie posé. En mode
    démonstration le code revient dans la réponse — c'est ce qui permet de
    tester le parcours sans serveur de courrier (voir CB_AUTH_CODE_EN_CLAIR)."""
    email = email or adresse_neuve()
    demande = c.post("/api/auth/code", json={"email": email})
    assert demande.status_code == 200, demande.text
    code = demande.json()["code_demonstration"]
    entree = c.post("/api/auth/entrer", json={"email": email, "code": code})
    assert entree.status_code == 200, entree.text
    return email


@pytest.fixture()
def visiteur() -> TestClient:
    """Personne d'entré : sert à vérifier que les portes sont bien fermées."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client() -> TestClient:
    """L'état normal de l'application : un élève entré. Le TestClient garde le
    cookie, donc tous les appels suivants sont authentifiés."""
    with TestClient(app) as c:
        entrer(c)
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
