"""Quel modèle sert quel appel.

Les cinq appels n'ont pas le même risque. Un seul regarde des photos d'écriture
manuscrite — l'analyse — et tout le reste est bâti sur ce qu'il en tire. Les
quatre autres raisonnent sur du texte déjà transcrit, et leurs erreurs sont
visibles par l'élève. C'est ce partage que tiennent ces tests : il est silencieux
quand il casse, puisqu'un mauvais modèle répond quand même.
"""

from __future__ import annotations

import re
from pathlib import Path

from app import config

SOURCE = (Path(__file__).resolve().parent.parent / "app" / "llm.py").read_text(encoding="utf-8")

# Les cinq actions, telles qu'elles sont nommées partout : dans llm.py, dans les
# quotas, et dans la colonne « action » des usages.
ACTIONS = {"analyse", "fiche_generale", "fiche_ciblee", "controle", "correction"}


def test_chaque_appel_dit_de_quelle_action_il_est():
    """Un appel qui oublie son action lèverait une erreur — mais seulement en
    mode réel, jamais dans les tests, qui ne passent pas par là."""
    appels = SOURCE.count("return _appel(")
    nommes = len(re.findall(r'action="(\w+)"', SOURCE))
    assert appels == 5, f"{appels} appels au modèle, cinq attendus"
    assert nommes == appels, f"{appels - nommes} appel(s) sans action"


def test_les_actions_nommees_sont_celles_du_reste_du_produit():
    """Les mêmes noms servent aux quotas et à la ligne « action » des usages :
    un nom qui diverge ferait un modèle mal routé et un coût mal rangé."""
    assert set(re.findall(r'action="(\w+)"', SOURCE)) == ACTIONS


def test_la_lecture_des_photos_a_son_propre_reglage(monkeypatch):
    """Pendant la phase de test les deux modèles sont le même — c'est voulu. Ce
    qui doit tenir, c'est que la lecture des photos reste RÉGLABLE à part : le
    jour où le produit est payant, la remonter en gamme doit être une variable
    d'environnement, pas une modification du code."""
    assert config.modele_pour("analyse") == config.MODEL

    monkeypatch.setattr(config, "MODEL", "un-modele-cher")
    monkeypatch.setattr(config, "MODELE_TEXTE", "un-modele-bon-marche")
    assert config.modele_pour("analyse") == "un-modele-cher"
    for action in ACTIONS - {"analyse"}:
        assert config.modele_pour(action) == "un-modele-bon-marche", action


def test_les_quatre_appels_sur_texte_prennent_le_modele_texte():
    for action in ACTIONS - {"analyse"}:
        assert config.modele_pour(action) == config.MODELE_TEXTE, action


def test_le_partage_ne_coute_aucune_lecture_de_cache():
    """Le bloc de cours mis en cache ne sert qu'aux appels « texte » : l'analyse
    tourne avant que le cours existe. Si elle se mettait à l'utiliser, séparer
    les modèles ferait perdre des lectures de cache — dix fois moins chères que
    l'entrée — sans que rien ne le signale."""
    debut = SOURCE.index("def analyser_photos(")
    corps = SOURCE[debut:SOURCE.index("\ndef ", debut + 1)]
    assert "_systeme_avec_cours" not in corps
    # Et l'inverse : les quatre autres s'en servent bien.
    assert SOURCE.count("_systeme_avec_cours(niveau, chapitres)") == 4
