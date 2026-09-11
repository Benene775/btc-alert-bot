"""Les fiches d'un côté, les contrôles de l'autre.

Les deux archives étaient l'une sous l'autre. Sur un téléphone, ça donnait deux
listes de lignes grises qui se ressemblent, séparées par un titre qu'on passe
sans le lire : il fallait faire défiler la première pour atteindre la seconde, et
deviner où elle s'arrêtait. Or on ne les cherche pas dans le même geste — une
fiche se relit, un contrôle se passe une fois.

Une bascule à deux moitiés règle les deux problèmes : on choisit, on ne voit que
ça, et le compte affiché dit ce qu'on trouvera de l'autre côté avant d'y aller.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

ECRAN = PAGE[PAGE.index('id="ecran-matiere"'):]
ECRAN = ECRAN[: ECRAN.index("<!-- ÉTAPE 1a")]
BASCULER = SCRIPT[SCRIPT.index("function basculerArchive("):]
BASCULER = BASCULER[: BASCULER.index("\n}\n")]


def test_la_bascule_a_deux_cotes():
    assert 'id="bascule-archives"' in ECRAN
    assert 'id="onglet-fiches"' in ECRAN
    assert 'id="onglet-controles"' in ECRAN


def test_un_seul_panneau_a_la_fois():
    """C'est tout l'objet : « scinder vraiment », c'est n'en montrer qu'un."""
    assert "$('pan-mes-fiches').hidden = !surLesFiches" in BASCULER
    assert "$('pan-mes-controles').hidden = surLesFiches" in BASCULER


def test_les_contoles_sont_caches_au_chargement():
    """Sinon les deux paraissent avant que le script ne tourne, et l'écran
    sautille au premier affichage."""
    controles = ECRAN[ECRAN.index('id="pan-mes-controles"'):]
    controles = controles[: controles.index(">")]
    assert "hidden" in controles


def test_ce_sont_des_onglets_pour_un_lecteur_d_ecran():
    """« Onglet 1 sur 2, sélectionné » plutôt que « bouton » : sans ça, le fait
    qu'il y ait un autre côté n'est dit nulle part."""
    assert 'role="tablist"' in ECRAN
    assert ECRAN.count('role="tab"') == 2
    assert ECRAN.count('role="tabpanel"') == 2
    assert 'aria-controls="pan-mes-fiches"' in ECRAN
    assert 'aria-controls="pan-mes-controles"' in ECRAN
    assert "setAttribute('aria-selected'" in BASCULER, "l'état doit être dit, pas seulement peint"


def test_le_compte_dit_ce_qu_il_y_a_de_l_autre_cote():
    """Un onglet vide qu'on découvre après avoir cliqué est un aller-retour
    pour rien."""
    assert 'id="compte-onglet-fiches"' in ECRAN
    assert 'id="compte-onglet-controles"' in ECRAN
    dessiner = SCRIPT[SCRIPT.index("function dessinerMatiere()"):]
    dessiner = dessiner[: dessiner.index("\n}\n")]
    assert "$('compte-onglet-fiches').textContent" in dessiner
    assert "$('compte-onglet-controles').textContent" in dessiner
    assert "String(combienDeFiches || 0)" in dessiner, (
        "le zéro est le chiffre le plus utile : il évite d'aller voir"
    )
    assert "String(combienDeControles || 0)" in dessiner


def test_les_fiches_sont_le_cote_par_defaut():
    """Une fiche se relit, un contrôle se passe une fois : c'est la fiche qu'on
    revient chercher."""
    assert "let archiveOuverte = 'fiches'" in SCRIPT
    assert "quoi === 'controles' ? 'controles' : 'fiches'" in BASCULER


def test_deux_moities_egales():
    """Deux largeurs de texte diraient que l'une compte plus que l'autre."""
    bloc = STYLE[STYLE.index(".bascule {"):]
    bloc = bloc[: bloc.index("}")]
    assert "repeat(2, minmax(0, 1fr))" in bloc


def test_plus_de_deux_colonnes_sur_grand_ecran():
    """La bascule n'en montre qu'une : la laisser dans une demi-largeur
    laisserait un vide à côté d'elle."""
    bloc = STYLE[STYLE.index(".matiere-listes"):]
    bloc = bloc[: bloc.index("}")]
    assert "grid-template-columns" not in bloc


def test_le_defilement_n_a_plus_lieu_d_etre():
    """Il compensait l'empilement. Le garder ferait bouger une page qui montre
    déjà la bonne chose."""
    assert "viserUnPanneau" not in SCRIPT
