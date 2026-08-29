"""Toute bibliothèque qu'on importe doit être déclarée.

Ce test existe à cause d'une panne réelle : la première publication du site sur
GitHub Pages a échoué. En local, 143 tests passaient ; sur une machine neuve,
un seul échouait — `ModuleNotFoundError: No module named 'PIL'`. Pillow était
installé ici depuis longtemps, et n'avait jamais été déclaré nulle part.

C'est la pire forme de dépendance manquante : invisible tant qu'on travaille sur
sa propre machine, et fatale à la première installation ailleurs. On ne peut pas
compter sur quelqu'un pour y penser ; on peut demander à une machine de vérifier.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent

# Nos propres modules, et ceux que pytest injecte dans le chemin des tests.
NOTRES = {"app", "outils", "tests", "conftest", "banc_essai"}

# Le nom qu'on importe n'est pas toujours celui qu'on installe.
PAQUET = {
    "PIL": "pillow",
    "fontTools": "fonttools",
    "multipart": "python-multipart",
    "yaml": "pyyaml",
    "dateutil": "python-dateutil",
}


def modules_importes() -> dict[str, set[str]]:
    """Chaque bibliothèque tierce importée, et par quels fichiers."""
    par_module: dict[str, set[str]] = {}
    for fichier in RACINE.rglob("*.py"):
        if "__pycache__" in fichier.parts or ".venv" in fichier.parts:
            continue
        arbre = ast.parse(fichier.read_text(encoding="utf-8"), filename=str(fichier))
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Import):
                noms = [alias.name for alias in noeud.names]
            elif isinstance(noeud, ast.ImportFrom) and noeud.level == 0 and noeud.module:
                noms = [noeud.module]
            else:
                continue
            for nom in noms:
                racine = nom.split(".")[0]
                if racine in sys.stdlib_module_names or racine in NOTRES:
                    continue
                par_module.setdefault(racine, set()).add(
                    str(fichier.relative_to(RACINE)))
    return par_module


def paquets_declares() -> set[str]:
    declares = set()
    for nom in ("requirements.txt", "requirements-dev.txt"):
        for ligne in (RACINE / nom).read_text(encoding="utf-8").splitlines():
            ligne = ligne.split("#")[0].strip()
            if not ligne or ligne.startswith("-"):
                continue
            # « fonttools[woff]>=4.50 » → « fonttools »
            declares.add(re.split(r"[\[<>=!;\s]", ligne)[0].lower())
    return declares


def test_toute_bibliotheque_importee_est_declaree():
    declares = paquets_declares()
    manquantes = {
        module: sorted(fichiers)
        for module, fichiers in modules_importes().items()
        if PAQUET.get(module, module).lower() not in declares
    }
    assert not manquantes, (
        "importées mais absentes de requirements : "
        + ", ".join(f"{m} ({', '.join(f)})" for m, f in sorted(manquantes.items()))
    )


def test_le_serveur_ne_depend_pas_des_outils():
    """`app/` tourne en production ; Pillow et fontTools servent à fabriquer des
    polices et à mesurer des coûts. Les installer sur le serveur, ce serait
    charger deux bibliothèques de traitement d'image pour rien."""
    production = set()
    for ligne in (RACINE / "requirements.txt").read_text(encoding="utf-8").splitlines():
        ligne = ligne.split("#")[0].strip()
        if ligne and not ligne.startswith("-"):
            production.add(re.split(r"[\[<>=!;\s]", ligne)[0].lower())
    for outil in ("pillow", "fonttools", "pytest", "httpx"):
        assert outil not in production, f"« {outil} » n'a rien à faire en production"

    # Et l'inverse : tout ce qu'importe app/ doit être en production.
    importes = {
        module for module, fichiers in modules_importes().items()
        if any(f.startswith("app/") for f in fichiers)
    }
    for module in importes:
        assert PAQUET.get(module, module).lower() in production, \
            f"app/ importe « {module} », absent de requirements.txt"
