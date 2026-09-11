"""Une clé présente mais refusée, c'est une panne muette.

Rencontré au premier déploiement. La clé était posée sur l'hébergeur, non vide ;
le site a démarré, servi ses pages, affiché sa page d'accueil sans le bandeau de
démonstration — tout avait l'air d'aller. Seule l'analyse échouait, avec
« Réessaie » à chaque tentative, et la vraie raison n'existait que dans une ligne
de journal que personne ne lisait :

    erreur API (401) : authentication_error — API key is invalid.

Copier 108 caractères dans le formulaire d'un hébergeur rate une fois sur
quelques-unes. Ce que ce fichier fixe : ça se voit au démarrage, pas dans le
téléphone d'un élève.
"""

from __future__ import annotations

import logging
from pathlib import Path

import anthropic
import pytest

from app import config, llm

RACINE = Path(__file__).resolve().parent.parent


class FausseReponse:
    status_code = 401
    headers: dict[str, str] = {}
    request = None

    def json(self):  # le SDK va la lire pour construire son message
        return {"type": "error", "error": {"type": "authentication_error",
                                           "message": "API key is invalid."}}


def _erreur(classe):
    """Fabrique une erreur du SDK sans passer par le réseau."""
    return classe(
        "Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', "
        "'message': 'API key is invalid.'}}",
        response=FausseReponse(),  # type: ignore[arg-type]
        body=None,
    )


class FauxClient:
    def __init__(self, leve: Exception | None = None) -> None:
        self.leve = leve
        self.appels: list[dict] = []
        self.messages = self

    def count_tokens(self, **kwargs):
        self.appels.append(kwargs)
        if self.leve is not None:
            raise self.leve
        return {"input_tokens": 3}


@pytest.fixture(autouse=True)
def client_neuf(monkeypatch):
    """llm garde son client en mémoire : chaque test repart de zéro."""
    monkeypatch.setattr(llm, "_client", None)
    monkeypatch.setattr(config, "DEMO_MODE", False)
    yield
    llm._client = None


def _poser(monkeypatch, faux: FauxClient) -> None:
    monkeypatch.setattr(llm, "client", lambda: faux)


def test_une_cle_refusee_donne_une_raison(monkeypatch):
    faux = FauxClient(_erreur(anthropic.AuthenticationError))
    _poser(monkeypatch, faux)
    raison = llm.verifier_la_cle()
    assert raison is not None
    assert "ANTHROPIC_API_KEY" in raison
    assert "espace invisible" in raison, "la raison doit dire quoi aller regarder"


def test_une_cle_sans_acces_au_modele_le_dit(monkeypatch):
    _poser(monkeypatch, FauxClient(_erreur(anthropic.PermissionDeniedError)))
    raison = llm.verifier_la_cle()
    assert raison is not None
    assert config.modele_pour("analyse") in raison


def test_une_cle_valide_ne_dit_rien(monkeypatch):
    faux = FauxClient()
    _poser(monkeypatch, faux)
    assert llm.verifier_la_cle() is None
    assert faux.appels, "la vérification doit vraiment appeler le fournisseur"


def test_la_verification_est_gratuite(monkeypatch):
    """count_tokens ne facture rien. Un vrai appel au modèle à chaque démarrage
    ferait payer un redéploiement, et il y en a plusieurs par jour."""
    faux = FauxClient()
    _poser(monkeypatch, faux)
    llm.verifier_la_cle()
    assert len(faux.appels) == 1
    assert faux.appels[0]["messages"] == [{"role": "user", "content": "."}]


def test_une_panne_de_reseau_ne_bloque_pas_le_demarrage(monkeypatch, caplog):
    """Refuser de démarrer parce que le fournisseur tousse couperait le site à
    chaque hoquet. Ce n'est pas une faute de configuration."""
    _poser(monkeypatch, FauxClient(RuntimeError("connexion perdue")))
    with caplog.at_level(logging.WARNING, logger="app.llm"):
        assert llm.verifier_la_cle() is None
    assert "vérification de la clé impossible" in caplog.text


def test_le_mode_demonstration_n_appelle_personne(monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    faux = FauxClient()
    _poser(monkeypatch, faux)
    assert llm.verifier_la_cle() is None
    assert not faux.appels


def test_la_cle_est_nettoyee_de_ses_espaces(monkeypatch):
    """Le défaut d'origine : un retour à la ligne collé avec les 108 caractères.
    Le SDK l'envoie tel quel et le fournisseur répond 401."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "  sk-ant-test-123\n")
    # Les tests tournent en mode démonstration assumé ; ici on veut justement
    # savoir ce que la clé décide toute seule.
    monkeypatch.delenv("CB_DEMO_MODE", raising=False)
    import importlib
    recharge = importlib.reload(config)
    try:
        assert recharge.CLE_API == "sk-ant-test-123"
        assert not recharge.DEMO_MODE, "une clé propre doit sortir du mode démonstration"
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_le_client_ne_relit_pas_l_environnement():
    """Passer par config.CLE_API plutôt que laisser le SDK relire la variable :
    sinon le nettoyage ci-dessus ne sert à rien."""
    source = (RACINE / "app" / "llm.py").read_text(encoding="utf-8")
    bloc = source[source.index("def client()"):source.index("def verifier_la_cle")]
    assert "api_key=config.CLE_API" in bloc


def test_le_demarrage_refuse_une_cle_invalide_en_ligne():
    """Et seulement en ligne : exiger le réseau à chaque lancement local
    rendrait le développement dépendant du fournisseur."""
    source = (RACINE / "app" / "main.py").read_text(encoding="utf-8")
    bloc = source[source.index("fautes = config.fautes_de_configuration()"):]
    bloc = bloc[:bloc.index("yield")]
    assert "if config.PUBLIC_BASE_URL:" in bloc
    assert "llm.verifier_la_cle()" in bloc
    assert "fautes.append(refus)" in bloc
    assert bloc.index("verifier_la_cle") < bloc.index("raise SystemExit")
