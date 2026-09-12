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


def _espace() -> str:
    espace = PAGE[PAGE.index('id="ecran-espace"'):]
    return espace[: espace.index('id="ecran-matiere"')]


def test_le_choix_est_en_haut_de_la_page_perso():
    """En bas, il fallait savoir qu'il existait. En haut, on le voit en
    arrivant — et c'est là qu'on y pense, en ouvrant l'application le soir."""
    espace = _espace()
    for identifiant in ("apparence-claire", "apparence-sombre"):
        assert f'id="{identifiant}"' in espace, identifiant
    # Sur la ligne d'identité, tout en haut : c'est un réglage de l'élève, pas
    # une destination — il n'a rien à faire parmi les six portes.
    assert espace.index('class="apparence"') < espace.index('class="tuiles"')
    assert espace.index('class="moi"') < espace.index('class="apparence"')


def test_deux_dessins_plutot_que_deux_mots():
    """Un soleil et une lune se lisent avant d'être lus. Tracés au trait en
    « currentColor », ils prennent la couleur du bouton : allumé ou éteint,
    clair ou sombre, sans deux jeux d'images à tenir à jour."""
    assert 'id="glyphe-soleil"' in PAGE and 'id="glyphe-lune"' in PAGE
    assert 'href="#glyphe-soleil"' in PAGE and 'href="#glyphe-lune"' in PAGE
    for glyphe in ("glyphe-soleil", "glyphe-lune"):
        bloc = PAGE[PAGE.index(f'id="{glyphe}"'):]
        bloc = bloc[: bloc.index("</symbol>")]
        assert "currentColor" in bloc, glyphe
    # Un dessin sans mot doit être nommé pour qui ne le voit pas.
    assert 'aria-label="Mode jour"' in PAGE
    assert 'aria-label="Mode nuit"' in PAGE


def test_il_n_y_a_pas_de_bouton_auto():
    """Demandé ainsi. Le comportement automatique reste celui de départ — qui
    n'y touche jamais suit son téléphone — mais on ne peut plus y revenir après
    avoir choisi. C'est le prix de deux boutons au lieu de trois.

    « auto » reste une valeur interne : c'est l'état d'un élève qui n'a encore
    rien décidé."""
    assert 'data-apparence="auto"' not in PAGE
    assert "const APPARENCES = ['auto', 'light', 'dark']" in SCRIPT


def test_le_bouton_allume_est_celui_qu_on_a_sous_les_yeux():
    """Et pas celui qu'on a rangé : sans choix, aucun des deux ne serait allumé
    alors que l'écran est bien dans l'un des deux états."""
    bloc = SCRIPT[SCRIPT.index("function dessinerApparence()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "apparenceEffective()" in bloc
    effective = SCRIPT[SCRIPT.index("function apparenceEffective()"):]
    effective = effective[: effective.index("\n}\n")]
    assert "(prefers-color-scheme: dark)" in effective


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
    """Une seule balise dont on écrit la couleur. Deux balises qui se relaient
    par media query sont le réflexe, mais rien ne garantit qu'un navigateur
    réévalue un « media » changé à chaud : l'élève bascule en sombre et garde
    un liseré crème."""
    assert 'id="couleur-barre"' in PAGE
    assert PAGE.count('name="theme-color"') == 1, "une seule, sinon on ne sait plus qui gagne"
    bloc = SCRIPT[SCRIPT.index("function peindreLaBordure("):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "getPropertyValue('--papier')" in bloc, (
        "la couleur doit venir de la feuille de style, pas d'une constante recopiée"
    )


def test_le_mode_auto_suit_l_appareil_qui_change_d_avis():
    """Beaucoup de téléphones basculent tout seuls le soir. La page suivrait
    (la media query fait son travail), mais la barre garderait la couleur du
    matin."""
    bloc = SCRIPT[SCRIPT.index("function suivreLaLumiereDeLAppareil()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "'change'" in bloc
    assert "apparenceChoisie() !== 'auto'" in bloc, (
        "un choix explicite ne doit pas être écrasé par l'appareil"
    )
    assert "dessinerApparence()" in bloc, (
        "sinon le soleil reste allumé sur un écran passé en nuit"
    )


def test_le_navigateur_sait_que_la_page_est_sombre():
    """« color-scheme » ne change rien à la page : il décide de ce qui est peint
    AUTOUR — la zone sûre d'un téléphone, les cases à cocher, les barres de
    défilement, et sur iOS la barre d'état d'une application installée. Sans
    elle, le système tenait la page pour claire malgré un fond noir et gardait
    un bandeau crème en haut de l'écran."""
    assert "color-scheme: light;" in STYLE
    assert STYLE.count("color-scheme: dark;") == 2, (
        "les deux chemins vers le sombre — le choix explicite et l'appareil"
    )
    # Et chacune au bon endroit : dans le bloc qui pose déjà la palette.
    explicite = STYLE[STYLE.index(':root[data-theme="dark"] {'):]
    assert "color-scheme: dark;" in explicite[: explicite.index("}")]


def test_les_deux_couleurs_recopiees_dans_l_entete_sont_les_bonnes():
    """L'en-tête ne peut pas lire la feuille de style, qui n'est pas encore
    chargée : il recopie « --papier ». C'est le seul endroit du produit où ces
    couleurs sont écrites deux fois."""
    import re

    tete = PAGE[: PAGE.index("</head>")]
    bloc = tete[tete.index("<script>"):tete.index("</script>")]
    recopiees = set(re.findall(r"#[0-9a-fA-F]{6}", bloc))
    assert recopiees, "l'en-tête ne pose aucune couleur"

    def papier(selecteur):
        morceau = STYLE[STYLE.index(selecteur):]
        morceau = morceau[: morceau.index("}")]
        return re.search(r"--papier:\s*(#[0-9a-fA-F]{6})", morceau).group(1)

    attendues = {papier(":root {"), papier(':root[data-theme="dark"] {')}
    assert recopiees == attendues, (
        f"l'en-tête dit {sorted(recopiees)}, la feuille de style {sorted(attendues)}"
    )


def test_le_reglage_ne_quitte_pas_l_appareil():
    """C'est un réglage d'écran, pas une préférence de compte : le téléphone du
    soir et l'ordinateur du week-end n'ont pas la même lumière autour d'eux."""
    poser = SCRIPT[SCRIPT.index("function poserApparence("):]
    poser = poser[: poser.index("\n}\n")]
    assert "api(" not in poser and "fetch(" not in poser


def test_l_etat_est_dit_pas_seulement_peint():
    """Deux boutons dont un seul est allumé : sans aria-checked, un lecteur
    d'écran annonce deux boutons identiques."""
    assert 'role="radiogroup"' in PAGE
    assert PAGE.count('role="radio"') == 2
    dessiner = SCRIPT[SCRIPT.index("function dessinerApparence()"):]
    dessiner = dessiner[: dessiner.index("\n}\n")]
    assert "setAttribute('aria-checked'" in dessiner


def test_l_allume_se_distingue_sans_pastille():
    """À deux boutons de la taille d'une icône, un fond plein ferait une tache
    en haut de la page : c'est la couleur d'accent qui dit lequel est le sien."""
    bloc = STYLE[STYLE.index('.apparence-cote[aria-checked="true"] {'):]
    bloc = bloc[: bloc.index("}")]
    assert "var(--accent)" in bloc


def test_l_etat_est_redessine_en_ouvrant_sa_page():
    """Sinon le bouton allumé reste celui du chargement, et ne suit pas un choix
    fait depuis un autre onglet."""
    bloc = SCRIPT[SCRIPT.index("function dessinerEspace()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "dessinerApparence()" in bloc
