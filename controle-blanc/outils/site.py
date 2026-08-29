#!/usr/bin/env python3
"""Fabrique le site statique des démonstrations.

Ce que c'est : les deux démonstrations autonomes, plus une page pour choisir
entre elles. Trois fichiers HTML, aucune dépendance, aucun serveur — ça se pose
sur GitHub Pages, Netlify, ou n'importe quel hébergement de fichiers.

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

DEMOS = [
    ("espagnol", "Espagnol", "Un cours d’espagnol de 4e : le tourisme en Espagne.",
     "Vocabulaire, chiffres, débat — et un contrôle au format de la matière."),
    ("histoire", "Histoire", "Un chapitre d’histoire de 3e : la Première Guerre mondiale.",
     "Guerre totale, Verdun, violence de masse — questions à développer et documents."),
]


def glyphe() -> str:
    """Le logo, repris de la page réelle : un seul dessin pour tout le produit."""
    page = (WEB / "index.html").read_text(encoding="utf-8")
    debut = page.index('<symbol id="glyphe-repere"')
    fin = page.index("</symbol>", debut) + len("</symbol>")
    return page[debut:fin]


def jetons() -> str:
    """La palette seulement, pas les 3 000 lignes de l'application.

    Le premier jet embarquait styles.css en entier : 200 Ko pour une page à deux
    liens, et une hauteur de 32 000 px parce que des règles écrites pour les
    écrans du produit s'appliquaient à ce qui traînait ici. Une page de choix
    n'a besoin que des couleurs, des espacements et des polices.
    """
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    blocs = []
    for depart in (":root {", "@media (prefers-color-scheme: dark) {", ':root[data-theme="dark"] {'):
        debut = css.index(depart)
        # On compte les accolades pour attraper le bloc entier, media compris.
        profondeur, fin = 0, debut
        for fin in range(debut, len(css)):
            if css[fin] == "{":
                profondeur += 1
            elif css[fin] == "}":
                profondeur -= 1
                if profondeur == 0:
                    break
        blocs.append(css[debut:fin + 1])
    return "\n\n".join(blocs)


GABARIT = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#fbf7f2">
<meta name="theme-color" content="#17130e" media="(prefers-color-scheme: dark)">
<meta name="description" content="Repère : passe le contrôle avant le contrôle. Deux démonstrations à parcourir.">
<title>Repère — les démonstrations</title>
{icone}
<style>
{polices}
{styles}

/* La page de choix n'existe que sur le site statique : elle n'est pas un écran
   du produit, juste le hall qui mène aux deux démonstrations. Elle reprend la
   palette et les polices, et pose le reste elle-même — embarquer les 3 000
   lignes de l'application donnait une page de 200 Ko haute de 32 000 px. */
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--papier); color: var(--encre);
  font-family: var(--texte); font-size: 1rem; line-height: 1.6;
  -webkit-font-smoothing: antialiased; }}
.hall {{ max-width: 720px; margin: 0 auto; padding: var(--e6) var(--gouttiere) var(--e7); }}
.hall-marque {{ display: flex; flex-direction: column; align-items: center; text-align: center; }}
.hall-marque svg {{ width: 72px; height: 72px; border-radius: 19px;
  box-shadow: 0 2px 4px color-mix(in srgb, var(--encre) 12%, transparent),
              0 18px 36px -18px color-mix(in srgb, var(--accent) 55%, transparent); }}
.hall h1 {{ margin: 16px 0 0; font-family: var(--titre); font-weight: 600;
  font-size: clamp(1.9rem, 6vw, 2.4rem); letter-spacing: -.015em; }}
.hall-accroche {{ margin: 6px 0 0; color: var(--encre-douce); }}
.hall-liste {{ display: grid; gap: var(--e3); margin-top: var(--e6); }}
.hall-carte {{ display: block; padding: var(--e4); border-radius: 20px; text-decoration: none;
  color: inherit; background: var(--carte); border: 1px solid var(--trait);
  box-shadow: var(--ombre-carte); transition: transform .2s cubic-bezier(.2,.7,.3,1),
  box-shadow .2s ease; }}
.hall-carte h2 {{ margin: 0; font-family: var(--titre); font-size: 1.3rem; font-weight: 600; }}
.hall-carte p {{ margin: 8px 0 0; color: var(--encre-douce); font-size: .94rem; line-height: 1.5; }}
.hall-carte .quoi {{ margin-top: 12px; font-family: var(--mono); font-size: .72rem;
  letter-spacing: .1em; text-transform: uppercase; color: var(--accent); }}
@media (hover: hover) and (pointer: fine) {{
  .hall-carte:hover {{ transform: translateY(-3px);
    box-shadow: 0 2px 5px color-mix(in srgb, var(--encre) 12%, transparent),
                0 22px 40px -20px color-mix(in srgb, var(--encre) 45%, transparent); }}
}}
.hall-note {{ margin-top: var(--e6); padding-top: var(--e3); border-top: 1px solid var(--trait);
  font-size: .84rem; line-height: 1.6; color: var(--encre-douce); }}
</style>
</head>
<body>
<svg width="0" height="0" aria-hidden="true" focusable="false" style="position:absolute">
{glyphe}
</svg>

<main class="hall">
  <div class="hall-marque">
    <svg aria-hidden="true" focusable="false"><use href="#glyphe-repere"/></svg>
    <h1>Repère</h1>
    <p class="hall-accroche">Passe le contrôle avant le contrôle.</p>
  </div>

  <div class="hall-liste">
{cartes}
  </div>

  <p class="hall-note">
    Ces deux pages sont des démonstrations : les photos ne sont pas analysées, les
    contenus sont des exemples, et tout se passe dans ce navigateur. Le produit réel
    a un serveur — comptes, lecture des photos, correction — qui ne peut pas tourner
    sur un hébergement de fichiers.
  </p>
</main>
</body>
</html>
"""

CARTE = """    <a class="hall-carte" href="{fichier}">
      <h2>{titre}</h2>
      <p>{sous_titre}</p>
      <p class="quoi">{quoi}</p>
    </a>"""


def main() -> int:
    analyseur = argparse.ArgumentParser(description="Fabrique le site des démonstrations.")
    analyseur.add_argument("sortie", nargs="?", default=str(RACINE / "_site"))
    arguments = analyseur.parse_args()
    # « .resolve() » n'est pas cosmétique : artefact.py est lancé avec cwd=RACINE,
    # donc un chemin relatif donné depuis la racine du dépôt (« _site », ce que
    # fait la publication) serait interprété depuis controle-blanc/ et pointerait
    # sur un dossier qui n'existe pas. En local on passait toujours un chemin
    # absolu — d'où un bug invisible ici et fatal sur la machine de GitHub.
    sortie = Path(arguments.sortie).resolve()
    sortie.mkdir(parents=True, exist_ok=True)

    for cle, *_ in DEMOS:
        fait = subprocess.run(
            [sys.executable, str(RACINE / "outils" / "artefact.py"),
             "--contenu", cle, str(sortie / f"{cle}.html")],
            capture_output=True, text=True, cwd=RACINE)
        if fait.returncode != 0:
            print(fait.stderr, file=sys.stderr)
            return 1
        print(fait.stdout.strip())

    # Le href du favicon est une data-URI qui contient du SVG, donc des « > ».
    # Couper au premier « > » tronquait l'attribut, et le parseur avalait alors
    # tout le <head> jusqu'au guillemet suivant — feuille de style comprise.
    page = (WEB / "index.html").read_text(encoding="utf-8")
    trouve = re.search(r'<link rel="icon" href="[^"]*">', page)
    if not trouve:
        raise SystemExit("index.html n'a plus de favicon")
    icone = trouve.group(0)

    cartes = "\n".join(
        CARTE.format(fichier=f"{cle}.html", titre=titre, sous_titre=sous_titre, quoi=quoi)
        for cle, titre, sous_titre, quoi in DEMOS)

    index = GABARIT.format(
        icone=icone,
        polices=(WEB / "polices.css").read_text(encoding="utf-8"),
        styles=jetons(),
        glyphe=glyphe(),
        cartes=cartes,
    )
    (sortie / "index.html").write_text(index, encoding="utf-8")

    # Même promesse que pour les démonstrations : rien ne sort de la page.
    externes = index.count('src="http') + index.count("url(http")
    if externes:
        raise SystemExit(f"la page de choix appelle {externes} ressource(s) externe(s)")

    poids = sum(f.stat().st_size for f in sortie.glob("*.html")) / 1024
    print(f"{sortie} — {len(DEMOS) + 1} pages, {poids:.0f} Ko, aucune requête externe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
