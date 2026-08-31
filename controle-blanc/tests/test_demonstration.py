"""La démonstration autonome doit suivre le produit.

Elle sert à faire cliquer quelqu'un dans le parcours complet sans serveur ni
clé API. Son faux serveur rejoue les routes à la main — et à chaque route
ajoutée au produit, il prend du retard sans que rien ne le signale : la page
se charge, l'écran s'affiche, et seul l'appel manquant échoue en silence.

C'est arrivé trois fois : les quotas, le classeur, l'agenda.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
FAUX = (RACINE / "outils" / "demonstration" / "faux-serveur.js").read_text(encoding="utf-8")


def _chemins_appeles() -> set[str]:
    """Les routes que le navigateur appelle, réduites à leur préfixe stable.

    « '/api/classeur/' + id » compte comme /api/classeur/ : c'est ce que le
    faux serveur reconnaît avec startsWith.
    """
    bruts = set(re.findall(r"""['"](/api/[a-z0-9/_-]*)['"]""", SCRIPT))
    return {c for c in bruts if c != "/api/"}


def test_le_faux_serveur_connait_toutes_les_routes():
    manquantes = sorted(c for c in _chemins_appeles() if c not in FAUX)
    assert not manquantes, (
        "routes appelées par le navigateur et absentes du faux serveur : "
        + ", ".join(manquantes)
    )


def test_les_deux_envoyerJson_ont_la_meme_signature():
    """Le faux serveur remplace envoyerJson() par le sien. Une signature en
    retard fait partir un PUT en POST — sans erreur, et sans effet."""
    def signature(source: str) -> str:
        debut = source.index("function envoyerJson(")
        return source[debut:source.index(")", debut) + 1]

    assert signature(SCRIPT) == signature(FAUX)


def test_le_faux_serveur_rend_les_memes_champs_pour_le_classeur():
    """Un champ oublié dans la réponse et la synchronisation lit undefined :
    elle ne casse pas, elle ne fait simplement rien."""
    for champ in ("seances", "agenda", "maintenant"):
        assert champ in FAUX, f"le faux /api/classeur ne rend pas « {champ} »"
