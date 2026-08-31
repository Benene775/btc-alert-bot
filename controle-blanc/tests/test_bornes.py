"""Ce que le navigateur peut renvoyer comme cours.

Le navigateur est propriétaire de l'état : il renvoie le cours à chaque appel,
et ce texte part au modèle en entrée. Sans plafond, un appel coûte ce que le
navigateur décide — et le quota compte quand même « une fiche ». Il n'y faut
aucune mauvaise volonté : un élève qui photographie tout son trimestre dans une
seule séance produit le même effet.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import schemas


def _chapitre(caracteres: int) -> dict:
    return {"titre": "Chapitre", "notions": ["a"], "transcription": "x" * caracteres,
            "photos": [0]}


@pytest.mark.parametrize("chemin, corps", [
    ("/api/fiche/generale", {"niveau": "3e"}),
    ("/api/fiche/ciblee", {"niveau": "3e", "notions": [{"notion": "n"}]}),
    ("/api/controle", {"niveau": "3e", "matiere": "histoire-geographie"}),
    ("/api/correction", {"niveau": "3e", "controle_id": "x", "reponses": []}),
])
def test_aucune_route_n_accepte_un_cours_sans_fin(client: TestClient, session, chemin, corps):
    """Les quatre routes qui reçoivent le cours doivent le borner. Une seule
    oubliée suffit : c'est par là que tout passerait."""
    enorme = [_chapitre(schemas.MAX_CAR_TRANSCRIPTION) for _ in range(10)]
    reponse = client.post(chemin, json={"session_id": session, "chapitres": enorme, **corps})
    assert reponse.status_code == 422, f"{chemin} a accepté {10 * schemas.MAX_CAR_TRANSCRIPTION} caractères"


def test_un_seul_chapitre_ne_peut_pas_tout_faire_passer(client: TestClient, session):
    """La borne par champ existe aussi : sinon un chapitre unique et démesuré
    passerait sous le plafond du total."""
    reponse = client.post("/api/fiche/generale", json={
        "session_id": session, "niveau": "3e",
        "chapitres": [_chapitre(schemas.MAX_CAR_TRANSCRIPTION + 1)]})
    assert reponse.status_code == 422


def test_le_nombre_de_chapitres_est_borne(client: TestClient, session):
    reponse = client.post("/api/fiche/generale", json={
        "session_id": session, "niveau": "3e",
        "chapitres": [_chapitre(10) for _ in range(schemas.MAX_CHAPITRES + 1)]})
    assert reponse.status_code == 422


def test_la_copie_de_l_eleve_est_bornee_aussi(client: TestClient, session):
    """Elle repart au modèle pour la correction : c'est une entrée comme le cours."""
    reponse = client.post("/api/correction", json={
        "session_id": session, "controle_id": "x", "niveau": "3e",
        "chapitres": [_chapitre(10)],
        "reponses": [{"numero": 1, "texte": "z" * 5_001}]})
    assert reponse.status_code == 422


def test_un_cours_de_taille_normale_passe(client: TestClient, session, photo_factice):
    """Les bornes doivent gêner l'absurde, pas l'usage : un trimestre de cours
    tient largement dedans."""
    trimestre = [_chapitre(4_000) for _ in range(12)]   # ≈ 96 pages denses
    assert sum(len(c["transcription"]) for c in trimestre) < schemas.MAX_CAR_COURS_TOTAL
    reponse = client.post("/api/fiche/generale", json={
        "session_id": session, "niveau": "3e", "chapitres": trimestre})
    assert reponse.status_code == 200, reponse.text
