"""La fiche sur un écran d'ordinateur.

Le paquet de cartes est un geste de téléphone : on fait glisser. Sur un
ordinateur, la même mise en page tenait deux cartes dans une colonne de 660
pixels au milieu d'un écran vide aux trois quarts, coupait les parties de cinq
points en « 1 sur 2 » dans une carte à moitié vide, et sautait deux cartes à la
moindre impulsion de pavé tactile.

Mesuré sur un cours réel en 1280 x 820 : 17 cartes avant, 11 après.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")
CODE_NU = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", SCRIPT, flags=re.S))
STYLE_NU = re.sub(r"/\*.*?\*/", "", STYLE, flags=re.S)


def test_une_partie_n_est_plus_coupee_quand_la_place_existe():
    """Trois points par carte, c'était juste sur un téléphone et absurde sur un
    écran de 470 pixels de haut où six tiennent : l'élève perdait le fil d'une
    partie au milieu d'une carte à moitié vide."""
    assert "const POINTS_PAR_CARTE = 3;" not in CODE_NU, "le découpage est encore figé"
    assert "function pointsParCarte" in CODE_NU
    assert "pointsParCarte()" in CODE_NU[CODE_NU.index("function decouper("):]
    corps = CODE_NU[CODE_NU.index("function pointsParCarte("):]
    corps = corps[: corps.index("\n}\n")]
    # La mesure vient de la fenêtre, pas d'une supposition sur l'appareil.
    assert "window.innerHeight" in corps and "window.innerWidth" in corps
    # Et elle reste bornée des deux côtés : une carte de dix points redevient
    # une page qu'on fait défiler.
    assert "POINTS_PAR_CARTE_MIN" in corps and "POINTS_PAR_CARTE_MAX" in corps


def test_le_paquet_ne_saute_pas_de_carte():
    """Une impulsion de pavé tactile parcourt facilement trois cartes ; sans
    arrêt imposé, le défilement atterrit sur la plus proche et l'élève a sauté
    deux parties de sa fiche sans les voir."""
    assert "scroll-snap-stop: always" in STYLE_NU


def test_la_fiche_prend_la_largeur_sur_un_ordinateur():
    """Comme l'accueil et l'espace personnel le font déjà. Et c'est l'écran
    entier qui s'élargit, pas le seul paquet : sinon le titre et les rubans
    restent alignés sur l'ancienne colonne, à côté des cartes."""
    bureau = STYLE_NU[STYLE_NU.index("@media (min-width: 900px)"):]
    bureau = bureau[: bureau.index("\n}\n")]
    assert ".ecran-fiche" in bureau and "max-width" in bureau
    assert ".carte-fiche" in bureau


def test_les_fleches_font_avancer_d_une_carte():
    """Le geste que tout le monde essaie devant un écran d'ordinateur, et qui ne
    faisait rien."""
    assert "function armerClavierPaquet" in CODE_NU
    assert "armerClavierPaquet();" in CODE_NU, "le clavier n'est jamais branché"
    corps = CODE_NU[CODE_NU.index("function armerClavierPaquet("):]
    corps = corps[: corps.index("\n}\n")]
    assert "ArrowRight" in corps and "ArrowLeft" in corps
    # Sans voler les flèches à un champ de saisie ni aux raccourcis du système.
    assert "INPUT" in corps and "metaKey" in corps
    # Et une carte à la fois : c'est tout le problème qu'on corrige.
    assert "ici + pas" in corps
