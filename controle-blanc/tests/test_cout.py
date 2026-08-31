"""Chiffrer le coût pour de vrai.

Le produit enregistre déjà, à chaque appel, les compteurs de tokens que l'API
renvoie elle-même : il n'y a rien à estimer, seulement à lire. Ces tests tiennent
les trois choses qui rendaient cette lecture trompeuse — un tarif unique pour
tous les modèles, un coût rapporté à la séance plutôt qu'au compte, et un tarif
manquant qui se taisait.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config, store
from app.main import app
from tests.conftest import inscrire

TARIF = {"entree": 5.0, "sortie": 25.0, "cache_ecriture": 6.25, "cache_lecture": 0.50}


@pytest.fixture()
def usage_nu(monkeypatch):
    """Une base sans usages, et un seul tarif connu — pour que le calcul soit
    vérifiable à la main."""
    with store.curseur() as cur:
        cur.execute("DELETE FROM usages")
    monkeypatch.setattr(config, "PRIX_USD_PAR_MTOK_PAR_MODELE", {"opus": TARIF})
    monkeypatch.setattr(config, "PRIX_USD_PAR_MTOK", TARIF)
    yield
    with store.curseur() as cur:
        cur.execute("DELETE FROM usages")


def _poser(session_id: str, action: str, modele: str, entree=0, sortie=0, ce=0, cl=0):
    store.enregistrer_usage(session_id, action, {
        "tokens_entree": entree, "tokens_sortie": sortie,
        "cache_ecriture": ce, "cache_lecture": cl, "modele": modele,
    })


def test_le_modele_qui_a_servi_est_enregistre(client, session, usage_nu):
    """Sans lui, comparer deux modèles est impossible : tout finit dans le même
    sac, au même tarif."""
    _poser(session, "analyse", "claude-opus-5", entree=1000, sortie=500)
    with store.curseur() as cur:
        cur.execute("SELECT modele FROM usages")
        assert cur.fetchone()["modele"] == "claude-opus-5"


def test_deux_modeles_ne_sont_pas_chiffres_au_meme_tarif(client, session, usage_nu,
                                                          monkeypatch):
    """Le cœur du banc d'essai : un essai Sonnet facturé au tarif Opus ne
    prouverait rien du tout."""
    monkeypatch.setattr(config, "PRIX_USD_PAR_MTOK_PAR_MODELE", {
        "opus": TARIF,
        "sonnet": {"entree": 1.0, "sortie": 5.0, "cache_ecriture": 1.25, "cache_lecture": 0.10},
    })
    _poser(session, "analyse", "claude-opus-5", entree=1_000_000)
    _poser(session, "analyse", "claude-sonnet-5", entree=1_000_000)

    par_modele = {d["modele"]: d["cout_usd"] for d in store.metriques()["detail_cout"]}
    assert par_modele["claude-opus-5"] == pytest.approx(5.0)
    assert par_modele["claude-sonnet-5"] == pytest.approx(1.0)


def test_un_tarif_manquant_ne_se_tait_pas(client, session, usage_nu):
    """Un modèle absent de la table est chiffré au tarif par défaut. Le chiffre
    est alors faux, et un tableau de bord qui ne le dit pas est pire qu'inutile."""
    _poser(session, "analyse", "un-modele-inconnu", entree=1000)
    mesures = store.metriques()
    assert "un-modele-inconnu" in mesures["tarifs_inconnus"]

    page = client.get("/admin/metriques", params={"token": "jeton-de-test"}).text
    assert "Tarif inconnu" in page
    assert "un-modele-inconnu" in page


def test_un_appel_sans_tokens_ne_declenche_pas_l_alerte(client, session, usage_nu):
    """Le mode démonstration n'appelle rien et n'enregistre aucun modèle. Crier
    au tarif manquant sur zéro token noierait la vraie alerte."""
    _poser(session, "analyse", "")
    assert store.metriques()["tarifs_inconnus"] == []


def test_le_cout_se_calcule_au_token_pres(client, session, usage_nu):
    """Quatre compteurs, quatre tarifs. La lecture de cache est dix fois moins
    chère que l'entrée : c'est tout l'intérêt du cache, et il faut que ça se voie."""
    _poser(session, "controle", "claude-opus-5",
           entree=1_000_000, sortie=1_000_000, ce=1_000_000, cl=1_000_000)
    attendu = 5.0 + 25.0 + 6.25 + 0.50
    assert store.metriques()["cout_usd_total"] == pytest.approx(attendu)


def test_le_cout_se_rapporte_au_compte_et_au_mois(usage_nu):
    """C'est l'unité de l'abonnement. Le coût par séance ne dit rien du prix à
    fixer : un élève ouvre autant de séances qu'il veut."""
    with TestClient(app) as lina:
        inscrire(lina)
        for _ in range(3):
            _poser(lina.post("/api/session").json()["session_id"],
                   "analyse", "claude-opus-5", entree=1_000_000)

    with TestClient(app) as sacha:
        inscrire(sacha)
        _poser(sacha.post("/api/session").json()["session_id"],
               "analyse", "claude-opus-5", entree=1_000_000)

    mesures = store.metriques()
    assert mesures["comptes_mois_mesures"] == 2, "les séances d'un compte doivent se regrouper"
    assert mesures["cout_usd_max_compte_mois"] == pytest.approx(15.0)
    assert mesures["cout_usd_moyen_compte_mois"] == pytest.approx(10.0)


def test_le_tableau_de_bord_montre_le_cout_par_compte(client, session, usage_nu):
    _poser(session, "analyse", "claude-opus-5", entree=1_000_000)
    page = client.get("/admin/metriques", params={"token": "jeton-de-test"}).text
    assert "Coût par compte et par mois" in page
    assert "Médiane" in page
