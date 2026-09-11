"""Le menu de la marque.

Depuis n'importe quel écran, l'élève doit pouvoir rejoindre sa page et retrouver
ce qu'il a déjà fait. Avant, il fallait repasser par sa page — et savoir que
c'était par là, ce qui n'est écrit nulle part.

Les deux entrées menaient d'abord à l'atelier, c'est-à-dire à en FABRIQUER un
nouveau. C'était se tromper de geste : « Contrôle blanc » dans un menu de
navigation, on s'attend à y trouver les siens. Et un menu qui navigue ne doit pas
non plus dépenser — chaque fabrication coûte un appel au modèle et entame un
plafond mensuel, ce qui se décide devant les compteurs de sa page, pas dans un
menu déroulant.
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
    assert "ouvrirMatiere(null, 'controles')" in BLOC
    assert "ouvrirMatiere(null, 'fiches')" in BLOC


def test_le_menu_ne_fabrique_rien():
    """Chaque fabrication coûte un appel au modèle et entame un plafond. Ça se
    décide devant les compteurs de sa page, pas dans un menu déroulant."""
    assert "ouvrirAtelier(" not in BLOC


def test_les_entrees_disent_qu_elles_menent_aux_siens():
    """« Contrôle blanc » pouvait se lire « en faire un ». « Mes contrôles
    blancs » ne se lit que d'une façon."""
    menu = PAGE[PAGE.index('id="menu-marque"'):PAGE.index('id="menu-reprendre"')]
    assert "Mes contrôles blancs" in menu
    assert "Mes fiches de révision" in menu


def test_on_arrive_sur_le_bon_panneau():
    """Les deux archives sont l'une sous l'autre sur un téléphone : venir
    chercher ses contrôles ne doit pas obliger à faire défiler les fiches."""
    assert 'id="pan-mes-fiches"' in PAGE
    assert 'id="pan-mes-controles"' in PAGE
    viser = SCRIPT[SCRIPT.index("function viserUnPanneau("):]
    viser = viser[: viser.index("\n}\n")]
    assert "scrollIntoView" in viser
    assert "requestAnimationFrame" in viser, "montrer() remet la page en haut : il faut attendre le rendu"
    assert "innerHeight" in viser, "un panneau déjà visible ne doit pas bouger"


def test_deux_entrees_ne_portent_pas_le_meme_signe():
    """Un menu se parcourt du regard. Deux lignes identiques à l'œil obligent
    à les lire, ce qui annule le gain."""
    signes = re.findall(r'<span class="menu-signe" aria-hidden="true">(.+?)</span>', PAGE)
    assert len(signes) == len(set(signes)), f"signes en double : {signes}"


def test_une_entree_ne_paraît_que_s_il_y_a_quelque_chose_derriere():
    """Une entrée qui mène à « Aucune fiche encore » est du bruit : l'élève
    clique, ne trouve rien, et cherche ce qu'il a mal fait."""
    assert "tousLesControles(faites).length === 0" in BLOC
    assert "toutesLesFiches(faites).length === 0" in BLOC
    assert "coursRepassables()" not in BLOC, (
        "avoir photographié un cours ne veut pas dire avoir une fiche"
    )


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
