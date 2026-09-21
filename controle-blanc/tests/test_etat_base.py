"""L'outil de diagnostic doit marcher le jour où on en a besoin.

Il ne sert qu'en panne — donc il n'est jamais lancé, donc il pourrit sans
bruit. Une requête qui ne passe plus, et on l'apprend le soir où le tableau de
bord ne bouge pas et où un élève attend.
"""

from __future__ import annotations

import importlib.util
import io
import contextlib
from pathlib import Path

from app import store

RACINE = Path(__file__).resolve().parent.parent


def _outil():
    chemin = RACINE / "outils" / "etat_base.py"
    spec = importlib.util.spec_from_file_location("etat_base", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sortie(module) -> str:
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        module.le_mode()
        module.la_base()
        module.l_activite()
        module.les_eleves()
    return tampon.getvalue()


def test_il_tourne_sur_une_base_vide(client):
    """Une base neuve est le cas où on le lance le plus tôt — et celui où une
    requête sur une table vide casse le plus facilement."""
    with store.curseur() as cur:
        cur.execute("DELETE FROM usages")
    texte = _sortie(_outil())
    assert "LE MODE" in texte
    assert "Aucun appel enregistré" in texte


def test_il_nomme_le_mode_demonstration(client):
    """C'est la panne la plus grave et la moins visible : l'élève reçoit une
    fiche inventée, et rien ne le dit."""
    texte = _sortie(_outil())
    assert "Mode démonstration" in texte
    assert "CONTENUS FACTICES" in texte, "le mode démonstration doit crier"


def test_il_compte_les_seances_sans_compte(client, session):
    """« Ce que coûte chaque élève » ne lit que les séances rattachées à un
    compte : une séance orpheline dépense dans le total et dans aucune ligne.

    Le nombre attendu se relit dans la base plutôt que de s'écrire en dur : la
    base est partagée par la suite, et un test voisin qui ouvre une séance
    ferait échouer celui-ci sans rien dire du vrai sujet.
    """
    with store.curseur() as cur:
        cur.execute("UPDATE sessions SET compte_id = NULL")
        combien = cur.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE compte_id IS NULL").fetchone()["n"]
    assert combien >= 1, "le test ne prouverait rien sans séance orpheline"

    texte = _sortie(_outil())
    assert f"Séances sans compte : {combien}" in texte
    assert "AUCUNE" in texte, "le cas doit être expliqué, pas seulement compté"


def test_il_ne_montre_aucune_adresse_ni_aucune_cle(client, session):
    """Il s'affiche dans un terminal partagé et se copie dans une conversation."""
    texte = _sortie(_outil())
    assert "@" not in texte
    with store.curseur() as cur:
        adresse = cur.execute("SELECT email FROM comptes LIMIT 1").fetchone()
    if adresse:
        assert adresse["email"] not in texte
