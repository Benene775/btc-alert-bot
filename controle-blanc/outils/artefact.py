#!/usr/bin/env python3
"""Fabrique une version autonome de l'application, en un seul fichier HTML.

À quoi ça sert : montrer le parcours complet sans serveur, sans clé API et sans
dépense — pour faire cliquer un professeur ou un élève avant d'héberger quoi que
ce soit. Aucune requête sortante : polices, styles et scripts sont embarqués.

Le seul écart avec le produit, c'est le transport. Les fonctions api() et
envoyerJson() sont remplacées par des équivalents locaux de mêmes signatures,
si bien que tout le reste — écrans, état, minuteur, localStorage — est le code
réel, inchangé.

Usage : python3 outils/artefact.py [sortie.html] [--contenu histoire|espagnol]

Le jeu de contenus se choisit avec --contenu : un fichier de outils/demonstration/,
qui fournit le cours, la fiche et les questions. La logique, elle, ne change pas.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
WEB = RACINE / "web"
DEMO = RACINE / "outils" / "demonstration"

MENTION = (
    "Démonstration : les photos ne sont pas vraiment analysées. Le cours d'exemple "
    "est un chapitre d'histoire de 3e, pour juger le format des questions."
)


def sans_couche_reseau(source: str) -> str:
    """Retire api(), envoyerJson() et tracer() : le faux serveur les remplace."""
    debut = source.index("/* ------------------------------------------------------------------ api --- */")
    fin = source.index("/* --------------------------------------------------------------- écrans --- */")
    allege = source[:debut] + source[fin:]
    if "fetch(" in allege:
        raise SystemExit("il reste un appel réseau dans app.js")
    return allege


# Le nom du cours embarqué, pour distinguer les démonstrations entre elles.
TITRES = {
    "histoire": "Histoire",
    "espagnol": "Espagnol",
}


def contenus_disponibles() -> list[str]:
    exclus = {"faux-serveur", "commun"}
    return sorted(f.stem for f in DEMO.glob("*.js") if f.stem not in exclus)


def main() -> int:
    analyseur = argparse.ArgumentParser(description="Fabrique la démonstration autonome.")
    analyseur.add_argument("sortie", nargs="?", default=str(RACINE / "controle-blanc-demo.html"))
    analyseur.add_argument("--contenu", default="histoire", choices=contenus_disponibles(),
                           help="le jeu de contenus à embarquer")
    analyseur.add_argument("--vierge", action="store_true",
                           help="pas de classeur pré-rempli : le compte s'ouvre vide, "
                                "comme pour un élève qui arrive")
    arguments = analyseur.parse_args()
    sortie = Path(arguments.sortie)

    polices = (WEB / "polices.css").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    app = sans_couche_reseau((WEB / "app.js").read_text(encoding="utf-8"))
    commun = (DEMO / "commun.js").read_text(encoding="utf-8")
    donnees = (DEMO / f"{arguments.contenu}.js").read_text(encoding="utf-8")
    faux = (DEMO / "faux-serveur.js").read_text(encoding="utf-8")

    # Le favicon est repris tel quel de la page : c'est une data-URI, donc il
    # traverse sans requête. Sans lui, le navigateur va chercher /favicon.ico et
    # se prend un 404 — invisible pour l'élève, mais c'est une requête sortante
    # dans une page qui promet de n'en faire aucune.
    icone = re.search(r'<link rel="icon" href="[^"]+">', html)
    if not icone:
        raise SystemExit("index.html n'a plus de favicon")

    # Lu par faux-serveur.js au moment de l'inscription : avec ce drapeau, aucun
    # classeur factice n'est semé et l'élève arrive sur une page perso vide.
    vierge = "const DEMO_VIERGE = true;\n\n" if arguments.vierge else ""
    titre = "Repère" if arguments.vierge else (
        f"Repère — {TITRES.get(arguments.contenu, arguments.contenu.capitalize())}")

    corps = html.split("<body>", 1)[1].split("</body>", 1)[0]
    corps = corps.replace('<script src="/app.js"></script>', "").strip()
    corps = corps.replace("Mode démonstration : contenus d'exemple, rien n'est analysé.", MENTION)

    page = (
        # Sans cette balise, un serveur statique qui n'annonce pas de jeu de
        # caractères fait rendre « Repère » en « RepÃ¨re ». La plateforme
        # d'artefacts fournit le sien, pas un hébergement quelconque.
        '<meta charset="utf-8">\n'
        # Les deux démonstrations portaient le même titre : dans une galerie
        # d'artefacts, elles apparaissaient comme deux entrées identiques et
        # rien ne disait laquelle contenait quel cours. Le site public, lui, est
        # seul et vierge : y accrocher « — Histoire » annoncerait dans l'onglet
        # un cours que la page ne contient pas.
        f"<title>{titre}</title>\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f"{icone.group(0)}\n"
        f"<style>\n{polices}\n{styles}\n</style>\n\n{corps}\n\n"
        f"<script>\n{vierge}{donnees}\n\n{commun}\n\n{faux}\n\n{app}\n</script>\n"
    )

    externes = re.findall(r'(?:src|href)=["\']https?://', page) + re.findall(r"url\(https?://", page)
    if externes:
        raise SystemExit(f"la page appelle {len(externes)} ressource(s) externe(s)")

    sortie.write_text(page, encoding="utf-8")
    print(f"{sortie} — {arguments.contenu} — {len(page.encode()) // 1024} Ko, "
          f"aucune requête externe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
