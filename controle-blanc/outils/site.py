#!/usr/bin/env python3
"""Fabrique le site statique des démonstrations.

Ce que c'est : Repère, en un seul fichier HTML autonome. Aucune dépendance,
aucun serveur — ça se pose sur GitHub Pages, Netlify, ou n'importe quel
hébergement de fichiers.

Deux choses ont été retirées en cours de route, pour la même raison :

- une page de choix entre deux matières, qui faisait atterrir sur un sommaire
  au lieu du produit ;
- le classeur pré-rempli (dix cours déjà faits), qui donnait un compte neuf
  déjà plein.

Quelqu'un à qui on envoie le lien doit voir la page d'accueil de Repère, et
s'inscrire sur un compte vide — exactement ce que vivra un élève.

Ce que ce n'est PAS : le produit. Le vrai Repère a un serveur (comptes, appels
au modèle, quotas, corrigés gardés hors du navigateur) et ne peut pas tourner
sur un hébergement statique. Ces pages rejouent le parcours avec des contenus
d'exemple et un faux serveur en JavaScript.

Usage : python3 outils/site.py [dossier-de-sortie]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
WEB = RACINE / "web"

# Le contenu qui sortira une fois des photos envoyées. L'histoire de 3e : la
# Première Guerre mondiale est le chapitre que n'importe quel professeur
# reconnaît en une ligne. Il n'apparaît qu'après coup — rien n'est pré-rempli.
CONTENU = "histoire"


def main() -> int:
    analyseur = argparse.ArgumentParser(description="Fabrique le site.")
    analyseur.add_argument("sortie", nargs="?", default=str(RACINE / "_site"))
    arguments = analyseur.parse_args()
    # « .resolve() » n'est pas cosmétique : artefact.py est lancé avec cwd=RACINE,
    # donc un chemin relatif donné depuis la racine du dépôt (« _site », ce que
    # fait la publication) serait interprété depuis controle-blanc/ et pointerait
    # sur un dossier qui n'existe pas. En local on passait toujours un chemin
    # absolu — d'où un bug invisible ici et fatal sur la machine de GitHub.
    sortie = Path(arguments.sortie).resolve()
    sortie.mkdir(parents=True, exist_ok=True)

    index = sortie / "index.html"
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "artefact.py"),
         "--contenu", CONTENU, "--vierge", str(index)],
        capture_output=True, text=True, cwd=RACINE)
    if fait.returncode != 0:
        print(fait.stderr, file=sys.stderr)
        return 1
    print(fait.stdout.strip())

    contenu = index.read_text(encoding="utf-8")
    externes = re.findall(r'(?:src|href)=["\']https?://', contenu)
    externes += re.findall(r"url\(https?://", contenu)
    if externes:
        raise SystemExit(f"le site appelle {len(externes)} ressource(s) externe(s)")
    if "const DEMO_VIERGE = true" not in contenu:
        raise SystemExit("le classeur pré-rempli est encore là")

    print(f"{sortie} — 1 page, {index.stat().st_size / 1024:.0f} Ko, "
          "aucune requête externe, aucun contenu pré-rempli")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
