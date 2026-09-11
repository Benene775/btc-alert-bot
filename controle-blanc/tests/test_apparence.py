"""Choisir clair, sombre, ou suivre le téléphone.

Le thème sombre existait dans la feuille de style depuis le début — trois états
prévus, les variables dédoublées — mais rien ne permettait de le demander :
l'élève subissait le réglage de son appareil. Or on révise le soir, souvent dans
un lit, et le téléphone d'un collégien est réglé par quelqu'un d'autre aussi
souvent que par lui.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

TETE = PAGE[: PAGE.index("</head>")]


def test_les_trois_choix_sont_sur_la_page_perso():
    espace = PAGE[PAGE.index('id="ecran-espace"'):]
    espace = espace[: espace.index('id="ecran-matiere"')]
    for identifiant in ("apparence-auto", "apparence-claire", "apparence-sombre"):
        assert f'id="{identifiant}"' in espace, identifiant


def test_trois_choix_et_pas_deux():
    """Un interrupteur clair/sombre retire le basculement automatique du soir —
    celui qu'on avait AVANT d'y toucher, et qu'on ne retrouverait plus."""
    assert "const APPARENCES = ['auto', 'light', 'dark']" in SCRIPT
    assert 'data-apparence="auto"' in PAGE


def test_auto_est_le_defaut_et_n_ecrit_rien():
    """Revenir à « auto », c'est ne plus avoir d'avis : la clé disparaît plutôt
    que de garder la chaîne « auto », qu'il faudrait ensuite savoir lire."""
    bloc = SCRIPT[SCRIPT.index("function apparenceChoisie()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "|| 'auto'" in bloc or "'auto'" in bloc
    poser = SCRIPT[SCRIPT.index("function poserApparence("):]
    poser = poser[: poser.index("\n}\n")]
    assert "localStorage.removeItem(CLE_APPARENCE)" in poser
    assert "delete document.documentElement.dataset.theme" in poser


def test_le_choix_est_pose_avant_la_premiere_peinture():
    """Depuis app.js, chargé en fin de body, la page s'afficherait d'abord dans
    le thème du téléphone puis basculerait — un éclair blanc à 22 h, ce que le
    mode sombre veut précisément éviter."""
    assert "<script>" in TETE, "rien ne s'exécute avant la feuille de style"
    assert "cb.apparence" in TETE
    assert "document.documentElement.dataset.theme" in TETE


def test_le_script_de_l_entete_survit_a_un_stockage_refuse():
    """Navigation privée, stockage bloqué : localStorage peut lever. Une
    exception ici empêcherait TOUTE la page de se charger."""
    bloc = TETE[TETE.index("<script>"):TETE.index("</script>")]
    assert "try {" in bloc and "catch" in bloc


def test_la_barre_du_telephone_suit():
    """Deux balises « theme-color » se relaient par media query. Sans les
    reprendre, l'application installée garde une barre blanche autour d'un
    écran noir."""
    assert 'id="couleur-claire"' in PAGE and 'id="couleur-sombre"' in PAGE
    bloc = SCRIPT[SCRIPT.index("function peindreLaBordure("):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "'not all'" in bloc
    assert "(prefers-color-scheme: dark)" in bloc


def test_le_reglage_ne_quitte_pas_l_appareil():
    """C'est un réglage d'écran, pas une préférence de compte : le téléphone du
    soir et l'ordinateur du week-end n'ont pas la même lumière autour d'eux."""
    poser = SCRIPT[SCRIPT.index("function poserApparence("):]
    poser = poser[: poser.index("\n}\n")]
    assert "api(" not in poser and "fetch(" not in poser


def test_l_etat_est_dit_pas_seulement_peint():
    """Trois boutons dont un seul est allumé : sans aria-checked, un lecteur
    d'écran annonce trois boutons identiques."""
    assert 'role="radiogroup"' in PAGE
    assert PAGE.count('role="radio"') == 3
    dessiner = SCRIPT[SCRIPT.index("function dessinerApparence()"):]
    dessiner = dessiner[: dessiner.index("\n}\n")]
    assert "setAttribute('aria-checked'" in dessiner


def test_le_choix_actif_se_peint_comme_un_onglet_actif():
    """Même composant que la bascule des archives : deux grammaires visuelles
    pour le même geste obligeraient à réapprendre."""
    assert '.bascule-cote[aria-checked="true"]' in STYLE
    assert ".bascule-trois { grid-template-columns: repeat(3, minmax(0, 1fr)); }" in STYLE


def test_l_etat_est_redessine_en_ouvrant_sa_page():
    """Sinon le bouton allumé reste celui du chargement, et ne suit pas un choix
    fait depuis un autre onglet."""
    bloc = SCRIPT[SCRIPT.index("function dessinerEspace()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "dessinerApparence()" in bloc
