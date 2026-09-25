"""La marque ramène chez soi.

Elle a ouvert un menu de quatre entrées — ma page, mes fiches, mes contrôles,
reprendre. C'était le seul chemin de retour du temps où la page perso était un
damier de tuiles : rien d'autre ne menait nulle part, et il fallait savoir que
c'était par là, ce qui n'était écrit nulle part.

La carcasse porte ces destinations maintenant, et ne disparaît plus. Le menu ne
faisait donc que redire ce qui est déjà à l'écran, en demandant deux gestes pour
celui qu'on fait dix fois par jour. Signalé par le commanditaire : « quand on
clique sur le bouton Repère, je veux que ça ramène à la page perso ».

Ce qui doit tenir :

1. Les deux marques — celle du bandeau, celle de la colonne — ramènent à sa
   page, en un geste.
2. Le menu est parti EN ENTIER : sa page, son script, ses styles. Un menu à
   moitié retiré est du code mort qu'on croit vivant à la relecture suivante.
3. Rien de ce qu'il portait n'est perdu : chaque entrée a sa porte ailleurs.
4. La matière reste écrite, à côté de la marque et non dedans — pendant un
   contrôle blanc, c'est le seul endroit de l'écran qui dise sur quoi il porte.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")


def test_les_deux_marques_ramenent_a_sa_page():
    assert 'id="bouton-accueil"' in PAGE and 'id="carcasse-accueil"' in PAGE
    assert "$('bouton-accueil').onclick = () => ouvrirEspace();" in SCRIPT
    assert "$('carcasse-accueil').onclick = () => ouvrirEspace();" in SCRIPT


def test_la_marque_de_la_colonne_est_un_bouton():
    """C'était un paragraphe : joli, et rien ne se passait au clic. Un mot de
    marque qui ne répond pas est pire qu'un mot de marque qui n'appelle rien."""
    debut = PAGE.index('<nav class="carcasse"')
    bloc = PAGE[debut : PAGE.index("</nav>", debut)]
    assert '<button type="button" class="carcasse-marque"' in bloc
    assert '<p class="carcasse-marque"' not in bloc


def test_le_menu_est_parti_en_entier():
    """Un menu à moitié retiré est du code mort qu'on croit vivant."""
    for mort in ('id="menu-marque"', 'id="menu-espace"', 'id="menu-fiche"',
                 'id="menu-controle"', 'id="menu-reprendre"', "marque-chevron"):
        assert mort not in PAGE, mort
    for mort in ("ouvrirMenuMarque", "armerMenuMarque"):
        assert mort not in SCRIPT, mort
    for mort in (".menu-marque", ".menu-entree", ".menu-paire", ".menu-moitie",
                 ".menu-signe", ".marque-chevron"):
        assert mort not in STYLE, mort


def test_rien_de_ce_que_le_menu_portait_n_est_perdu():
    """« Ma page » est la marque elle-même. Les deux archives sont dans la
    carcasse. « Reprendre » vit sur l'accueil, dans le rail de sa page, et sous
    le rond du bandeau, qui ramène à la séance en cours."""
    carcasse = PAGE[PAGE.index('<nav class="carcasse"') : PAGE.index("<main id=\"scene\">")]
    assert 'id="porte-fiches"' in carcasse and 'id="porte-controles"' in carcasse
    assert 'id="rail-reprise-porte"' in PAGE
    assert 'id="bouton-reprendre"' in PAGE
    assert 'id="bouton-espace"' in PAGE


def test_la_matiere_s_ecrit_a_cote_de_la_marque_pas_dedans():
    """Un bouton qui affiche « Histoire-Géographie » et mène à « Ma page »
    demande à l'élève de deviner ce qu'il commande."""
    debut = PAGE.index('<div class="marque-bandeau">')
    bloc = PAGE[debut : PAGE.index("</div>", debut)]
    assert 'id="bandeau-matiere"' not in bloc[: bloc.index("</button>")], \
        "la matière est redevenue le libellé du bouton"
    assert 'id="bandeau-matiere"' in bloc
    assert "$('bandeau-matiere').hidden = dansMaPage || !matiere;" in SCRIPT
    # Un filet la sépare de la marque : sans lui, « Repère Histoire-Géo » se lit
    # comme un seul titre et la porte disparaît dans l'étiquette.
    assert ".bandeau-contexte::before" in STYLE
