"""La palette : une seule identité, et elle doit rester lisible.

L'application entière porte désormais le papier chaud de la fiche. Deux choses
peuvent casser sans que rien ne plante : un jeton qu'on retire mais qui reste
utilisé quelque part, et un couple couleur/fond qui descend sous le seuil de
lisibilité. Les deux se vérifient ici, pas à l'oeil.
"""

from __future__ import annotations

import re
from pathlib import Path

STYLE = (Path(__file__).resolve().parent.parent / "web" / "styles.css").read_text(encoding="utf-8")


def _jetons(bloc: str) -> dict[str, str]:
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", bloc))


def _bloc(entete: str) -> str:
    debut = STYLE.index(entete) + len(entete)
    return STYLE[debut : STYLE.index("}", debut)]


CLAIR = _jetons(_bloc(":root {"))
SOMBRE = _jetons(_bloc(':root[data-theme="dark"] {'))


def _luminance(hexa: str) -> float:
    hexa = hexa.strip().lstrip("#")
    canaux = [int(hexa[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lineaire = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
    return 0.2126 * lineaire[0] + 0.7152 * lineaire[1] + 0.0722 * lineaire[2]


def _contraste(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# Les couples qui portent du texte. Le bouton principal en fait partie : c'est
# lui qui a révélé le problème — du blanc sur l'ambre clair du mode sombre
# tombait à 2,2:1, illisible, et personne ne l'aurait vu sur une capture claire.
COUPLES = [
    ("--encre", "--papier"),
    ("--encre", "--carte"),
    ("--encre-douce", "--papier"),
    ("--accent", "--papier"),
    ("--sur-accent", "--accent"),
    ("--stylo-eleve", "--papier"),
    ("--rouge", "--papier"),
    ("--acquis", "--papier"),
    ("--partiel", "--papier"),
    ("--encre", "--t0"),
    ("--encre", "--t1"),
    ("--encre", "--t2"),
    ("--encre", "--t3"),
    ("--encre", "--t4"),
    ("--encre", "--t5"),
    ("--encre", "--stylo-eleve-doux"),
]


def test_tout_ce_qui_porte_du_texte_reste_lisible():
    faibles = []
    for nom, jetons in (("clair", CLAIR), ("sombre", SOMBRE)):
        for devant, derriere in COUPLES:
            rapport = _contraste(jetons[devant], jetons[derriere])
            if rapport < 4.5:
                faibles.append(f"{nom} : {devant} sur {derriere} = {rapport:.2f}")
    assert not faibles, "contraste insuffisant — " + " ; ".join(faibles)


def test_les_deux_themes_definissent_les_memes_jetons():
    """Un jeton défini en clair mais oublié en sombre disparaît sans erreur."""
    couleurs = {j for j in CLAIR if not j.startswith(("--titre", "--texte", "--mono", "--manuscrit"))}
    couleurs -= {"--rayon", "--rayon-carte", "--marge", "--colonne", "--ombre-carte"}
    manquants = sorted(couleurs - set(SOMBRE))
    assert not manquants, f"absents du thème sombre : {manquants}"


def test_aucun_jeton_utilise_n_est_indefini():
    """« --alerte-fiche » a vécu dans la surcouche de la fiche ; en la retirant
    on aurait pu laisser derrière soi des « var() » qui ne valent plus rien."""
    definis = set(CLAIR) | set(SOMBRE) | set(_jetons(_bloc(':root:not([data-theme="light"]) {')))
    utilises = set(re.findall(r"var\((--[a-z0-9-]+)", STYLE))
    assert not utilises - definis, f"jetons utilisés mais jamais définis : {sorted(utilises - definis)}"


def test_la_palette_chaude_est_celle_de_toute_l_application():
    """Elle vivait derrière « [data-ecran=\"fiche\"] » : le reste était bleu et froid."""
    assert ':root[data-ecran="fiche"] {' not in STYLE, "la palette est de nouveau réservée à un écran"
    assert CLAIR["--papier"].strip() == "#fbf7f2"
    assert "--t0" in CLAIR and "--t5" in CLAIR, "les teintes des cartes ne sont pas globales"
