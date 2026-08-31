"""Ce qui ne doit jamais atteindre un élève.

Deux réglages sont sans danger en local et catastrophiques en ligne, et aucun
des deux ne fait de bruit : le site démarre, il répond, il a l'air d'aller bien.

Le mode démonstration s'active TOUT SEUL quand ANTHROPIC_API_KEY manque — une
variable oubliée au déploiement suffit. L'élève photographie son cours de maths
et reçoit une fiche sur la Première Guerre mondiale ; la seule mention à l'écran
est sur l'accueil, or un élève connecté arrive sur sa page et ne la voit jamais.
Pendant une phase de test dont on mesure la qualité, ça empoisonne toutes les
données sans qu'on l'apprenne avant la fin.
"""

from __future__ import annotations

import pytest

from app import config


@pytest.fixture()
def en_ligne(monkeypatch):
    """Le signal de « déployé » : on ne définit CB_PUBLIC_BASE_URL que pour ça."""
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://repere.exemple.fr")
    monkeypatch.setattr(config, "DEMO_ASSUMEE", False)
    monkeypatch.setattr(config, "AUTH_CODE_EN_CLAIR", False)
    monkeypatch.setattr(config, "DEMO_MODE", False)


def test_une_cle_oubliee_empeche_le_demarrage(en_ligne, monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)
    fautes = config.fautes_de_configuration()
    assert fautes, "un déploiement en mode démonstration doit être refusé"
    assert "ANTHROPIC_API_KEY" in fautes[0], "le message doit dire quoi faire"


def test_le_code_en_clair_empeche_le_demarrage(en_ligne, monkeypatch):
    """Il renvoie le code de réinitialisation dans la réponse HTTP : n'importe
    qui prend n'importe quel compte."""
    monkeypatch.setattr(config, "AUTH_CODE_EN_CLAIR", True)
    assert config.fautes_de_configuration()


def test_une_demonstration_assumee_passe(en_ligne, monkeypatch):
    """Mettre la démonstration en ligne exprès reste possible — mais il faut le
    dire. Les deux garde-fous se lèvent ensemble : ils décrivent la même
    situation, et les séparer laisserait croire qu'on peut assumer l'un sans
    l'autre."""
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(config, "AUTH_CODE_EN_CLAIR", True)
    monkeypatch.setattr(config, "DEMO_ASSUMEE", True)
    assert config.fautes_de_configuration() == []


def test_en_local_rien_ne_gene(monkeypatch):
    """Sans adresse publique, on développe : le garde-fou ne doit jamais se
    mettre en travers, sinon il finira contourné une fois pour toutes."""
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "")
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(config, "AUTH_CODE_EN_CLAIR", True)
    monkeypatch.setattr(config, "DEMO_ASSUMEE", False)
    assert config.fautes_de_configuration() == []


def test_le_demarrage_s_arrete_vraiment(monkeypatch):
    """Un avertissement de plus dans les journaux n'aurait servi à rien :
    personne ne les lit au moment où ça compte. Le démarrage doit échouer."""
    source = (config.BASE_DIR / "app" / "main.py").read_text(encoding="utf-8")
    bloc = source[source.index("fautes = config.fautes_de_configuration()"):]
    bloc = bloc[: bloc.index("yield")]
    assert "raise SystemExit" in bloc, "les fautes ne font que se journaliser"
