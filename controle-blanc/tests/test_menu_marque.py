"""Le menu de la marque.

Depuis n'importe quel écran, l'élève doit pouvoir rejoindre sa page, lancer un
contrôle blanc ou une fiche. Avant, il fallait repasser par sa page — et savoir
que c'était par là, ce qui n'est écrit nulle part.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

BLOC = SCRIPT[SCRIPT.index("function ouvrirMenuMarque("):SCRIPT.index("function reprendre()")]


def test_les_trois_destinations_sont_la():
    for identifiant in ("menu-espace", "menu-controle", "menu-fiche"):
        assert f'id="{identifiant}"' in PAGE, identifiant


def test_chaque_entree_mene_ou_elle_dit():
    assert "$('menu-espace').onclick" in BLOC and "ouvrirEspace()" in BLOC
    assert "ouvrirAtelier('controle')" in BLOC
    assert "ouvrirAtelier('fiche')" in BLOC


def test_deux_entrees_ne_portent_pas_le_meme_signe():
    """Un menu se parcourt du regard. Deux lignes identiques à l'œil obligent
    à les lire, ce qui annule le gain."""
    signes = re.findall(r'<span class="menu-signe" aria-hidden="true">(.+?)</span>', PAGE)
    assert len(signes) == len(set(signes)), f"signes en double : {signes}"


def test_les_outils_disparaissent_sans_cours_photographie():
    """ouvrirAtelier() ne fait rien sans cours : l'entrée resterait cliquable
    et sans effet, et l'élève chercherait ce qu'il a mal fait."""
    assert "coursRepassables()" in BLOC
    assert "$('menu-controle').hidden = cours.size === 0" in BLOC
    assert "$('menu-fiche').hidden = cours.size === 0" in BLOC


def test_le_menu_se_referme_de_trois_facons():
    """Un menu qu'on ne peut pas refermer sans choisir est un piège."""
    armer = SCRIPT[SCRIPT.index("function armerMenuMarque()"):]
    armer = armer[: armer.index("\n}\n")]
    assert "'Escape'" in armer, "Échap ne referme pas"
    assert "menu.contains(evenement.target)" in armer, "cliquer à côté ne referme pas"
    for entree in ("menu-espace", "menu-controle", "menu-fiche"):
        assert f"$('{entree}').onclick = () => {{ ouvrirMenuMarque(false);" in armer, entree


def test_changer_d_ecran_referme_le_menu():
    """Sinon il flotte au-dessus du nouvel écran, ancré à rien."""
    montrer = SCRIPT[SCRIPT.index("function montrer(id)"):]
    montrer = montrer[: montrer.index("\n}\n")]
    assert "ouvrirMenuMarque(false)" in montrer


def test_le_menu_s_ancre_sous_le_bouton_pas_sur_la_fenetre():
    """Le bandeau est en position: sticky. Un position: fixed se calerait
    ailleurs qu'on ne croit — c'est le piège qui avait déjà coûté la fiche du
    jour, docké à la colonne de lecture au lieu de la fenêtre."""
    bloc = STYLE[STYLE.index(".menu-marque {"):]
    bloc = bloc[: bloc.index("}")]
    assert "position: absolute" in bloc
    assert ".marque-menu { position: relative; }" in STYLE, "rien n'ancre le menu"


def test_le_bouton_annonce_son_menu():
    entete = PAGE[PAGE.index('id="bouton-accueil"'):]
    entete = entete[: entete.index("</button>")]
    assert 'aria-haspopup="true"' in entete
    assert 'aria-controls="menu-marque"' in entete
    assert "aria-expanded" in entete
    assert "setAttribute('aria-expanded'" in BLOC, "aria-expanded ne suit pas l'état"
