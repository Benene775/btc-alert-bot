#!/usr/bin/env python3
"""Fabrique web/polices.css : les polices, découpées et embarquées en base64.

Deux raisons de ne pas les charger depuis Google :
  - une requête vers fonts.gstatic.com transmettrait l'adresse IP de chaque élève
    à un tiers, ce que tout le reste du produit s'applique à éviter ;
  - une police complète pèse plusieurs centaines de kilo-octets, ce qui se paie
    en données mobiles.

On ne garde donc que les caractères dont une application française a besoin.
Relancer après toute modification de la liste des polices.
"""

from __future__ import annotations

import base64
import io
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "web" / "polices.css"

# Surtout PAS un navigateur récent : Google renverrait alors des woff2 déjà
# découpés par plage Unicode (latin, latin-ext, cyrillique…), et « latin-ext »
# ne contient que les caractères rares, pas l'alphabet. Avec un client neutre,
# Google sert un TTF complet, que l'on découpe soi-même juste après.
NAVIGATEUR = "Python-urllib/3"

# Chaque graisse est une police de plus à télécharger. On s'en tient au strict
# nécessaire : un titrage, deux graisses de texte, une utilitaire, une manuscrite.
URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Caveat:wght@600"
    "&family=Fraunces:opsz,wght@9..144,600"
    "&family=IBM+Plex+Mono:wght@500"
    "&family=Schibsted+Grotesk:wght@400;700&display=swap"
)

# Ce dont une application française a besoin : l'ASCII imprimable, les lettres
# accentuées, les ligatures, la ponctuation typographique et les quelques signes
# que l'interface affiche (guillemets, tirets, puces, croix, chrono).
CARACTERES = (
    "".join(chr(c) for c in range(0x20, 0x7F))
    + "àâäáãåÀÂÄÁÃÅ"
    + "çÇ"
    + "èéêëÈÉÊË"
    + "îïíìÎÏÍÌ"
    + "ôöòóõÔÖÒÓÕ"
    + "ùûüúÙÛÜÚ"
    + "ÿŸñÑ"
    + "œŒæÆ"
    + "«»“”‘’‚„"
    + "—–‑…·•‣"
    + "€£°±×÷−"
    + "†‡§¶©®™"
    + "→←↑↓"
    + "✓✔✗✕×○●◦□■"
    + "＋"
    + "   "  # espaces insécables : « guillemets » et 12 000 km
)


# Caveat ne sert qu'à une phrase, celle de la copie sur la page d'accueil.
# Inutile d'embarquer un alphabet complet : c'est la police la plus lourde.
PHRASE_MANUSCRITE = (
    "C'est quand tout le pays travaille pour la guerre, pas seulement les soldats."
)

RESTREINTES = {"Caveat": PHRASE_MANUSCRITE}


def telecharger(url: str, binaire: bool = False):
    requete = urllib.request.Request(url, headers={"User-Agent": NAVIGATEUR})
    with urllib.request.urlopen(requete, timeout=90) as reponse:
        donnees = reponse.read()
    return donnees if binaire else donnees.decode()


def decouper(octets: bytes, caracteres: str = CARACTERES) -> bytes:
    """Réduit une police aux seuls caractères demandés."""
    with tempfile.TemporaryDirectory() as dossier:
        entree = Path(dossier) / "entree.woff2"
        sortie = Path(dossier) / "sortie.woff2"
        entree.write_bytes(octets)
        subprocess.run(
            [
                sys.executable, "-m", "fontTools.subset", str(entree),
                f"--text={caracteres}",
                "--flavor=woff2",
                f"--output-file={sortie}",
                "--layout-features=kern,liga,calt,tnum",
                "--no-hinting",
                "--desubroutinize",
            ],
            check=True,
            capture_output=True,
        )
        return sortie.read_bytes()


ECHANTILLON = "AaZzÉéÀàÇçÙùŒœ0123«»—’"


def verifier(famille: str, graisse: str, octets: bytes, jeu: str) -> None:
    """Refuse une police à qui il manque des caractères courants.

    Sans ce garde-fou, une police mal découpée se contente de se replier
    silencieusement sur une autre : la mise en page tient, mais le rendu n'est
    plus celui qu'on a dessiné.
    """
    from fontTools.ttLib import TTFont

    table = TTFont(io.BytesIO(octets)).getBestCmap()
    attendus = ECHANTILLON if jeu is CARACTERES else jeu
    absents = [c for c in attendus if ord(c) not in table and not c.isspace()]
    if absents:
        raise SystemExit(
            f"{famille} {graisse} : caractères manquants après découpe "
            f"({''.join(absents)}). Découpe interrompue."
        )


def main() -> int:
    css = telecharger(URL)
    blocs = [("", b) for b in re.findall(r"@font-face \{.*?\}", css, re.S)]

    morceaux = []
    avant = apres = 0
    vus = set()

    for _, bloc in blocs:
        lien = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", bloc)
        if not lien:
            continue

        famille = re.search(r"font-family: '([^']+)'", bloc).group(1)
        graisse = re.search(r"font-weight: (\S+);", bloc).group(1)
        if (famille, graisse) in vus:
            continue
        vus.add((famille, graisse))

        brut = telecharger(lien.group(1), binaire=True)
        jeu = RESTREINTES.get(famille, CARACTERES)
        reduit = decouper(brut, jeu)
        avant += len(brut)
        apres += len(reduit)

        verifier(famille, graisse, reduit, jeu)

        donnees = base64.b64encode(reduit).decode()
        bloc = re.sub(
            r"src: url\([^)]+\)[^;]*;",
            f"src: url(data:font/woff2;base64,{donnees}) format('woff2');",
            bloc,
        )
        bloc = re.sub(r"\n\s*unicode-range:[^;]+;", "", bloc)
        morceaux.append(bloc)

    entete = (
        "/* Polices embarquées — fabriqué par outils/polices.py, ne pas modifier à la main.\n"
        " *\n"
        " * Elles ne viennent pas de Google : une requête vers fonts.gstatic.com\n"
        " * transmettrait l'adresse IP de chaque élève à un tiers, ce que tout le reste\n"
        " * du produit s'applique à éviter.\n"
        " *\n"
        f" * Découpées aux caractères d'une application française : {avant // 1024} Ko\n"
        f" * de polices complètes réduits à {apres // 1024} Ko.\n"
        " */\n\n"
    )
    SORTIE.write_text(entete + "\n\n".join(morceaux) + "\n", encoding="utf-8")
    print(f"{len(morceaux)} polices — {avant // 1024} Ko → {apres // 1024} Ko "
          f"({SORTIE.stat().st_size // 1024} Ko de CSS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
