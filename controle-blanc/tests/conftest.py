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
# La suite tourne en mode démonstration à une adresse publique factice — soit
# exactement ce que le garde-fou de démarrage refuse. Elle l'assume, comme
# devrait le faire toute démonstration mise en ligne volontairement.
os.environ["CB_DEMO_ASSUMEE"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(RACINE))
from app.main import app  # noqa: E402


MDP_DE_TEST = "chocolatine-du-matin"


def adresse_neuve() -> str:
    """Une adresse par test. Le serveur ne laisse partir qu'un code par minute
    et par adresse, et compte les essais ratés : partager la même ferait échouer
    le sixième test pour une raison qui n'a rien à voir avec ce qu'il vérifie."""
    return f"eleve-{secrets.token_hex(4)}@exemple.test"


def inscrire(c: TestClient, email: str | None = None, mot_de_passe: str = MDP_DE_TEST) -> str:
    """Ouvre un compte et laisse le client connecté (le TestClient garde le
    cookie). Rend l'adresse utilisée."""
    email = email or adresse_neuve()
    reponse = c.post("/api/auth/inscription", json={
        "email": email, "mot_de_passe": mot_de_passe, "prenom": "Lina", "niveau": "4e"})
    assert reponse.status_code == 200, reponse.text
    return email


def connecter(c: TestClient, email: str, mot_de_passe: str = MDP_DE_TEST):
    return c.post("/api/auth/connexion", json={"email": email, "mot_de_passe": mot_de_passe})


def code_recu(c: TestClient, email: str) -> str:
    """Le code de réinitialisation. En mode démonstration il revient dans la
    réponse — c'est ce qui permet de tester sans serveur de courrier."""
    reponse = c.post("/api/auth/oubli", json={"email": email})
    assert reponse.status_code == 200, reponse.text
    return reponse.json()["code_demonstration"]


@pytest.fixture()
def visiteur() -> TestClient:
    """Personne d'entré : sert à vérifier que les portes sont bien fermées."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client() -> TestClient:
    """L'état normal de l'application : un élève connecté. Le TestClient garde
    le cookie, donc tous les appels suivants sont authentifiés."""
    with TestClient(app) as c:
        inscrire(c)
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
