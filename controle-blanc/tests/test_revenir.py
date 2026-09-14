"""Revenir en arrière, partout et par le même geste.

Deux écrans sur treize portaient un retour — « ← Ma page », chacun le sien,
câblé en dur sur la page perso. Sur les onze autres on était pris : il fallait
repasser par le menu de la marque, et savoir que c'était par là, ce qui n'est
écrit nulle part. Signalé en usage réel depuis l'écran d'une fiche.

Ce qui doit tenir :

1. Un seul bouton, toujours à la même place, qui rend l'écran d'où l'on vient.
2. Le même geste au doigt, DEPUIS LE BORD GAUCHE seulement. La fiche est un
   paquet de cartes qu'on fait glisser horizontalement : un balayage vers la
   droite au milieu de l'écran veut dire « carte précédente », et doit
   continuer à le vouloir dire.
3. Une pile, pas une table de destinations : la fiche se rejoint de quatre
   endroits, et « revenir » veut dire l'endroit d'où l'on vient.
4. On ne revient pas sur ses pas en boucle, et on ne revient jamais dans un
   contrôle qu'on a quitté.
5. Quitter un contrôle EN COURS se demande : les questions ne sont pas gardées
   et en relancer un coûte un contrôle du mois.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")


def bloc(nom: str) -> str:
    debut = SCRIPT.index("function " + nom + "(")
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_un_seul_bouton_pour_toute_l_application():
    assert 'id="bouton-retour"' in PAGE
    # Il vit dans la coque, hors des écrans : un bouton par écran, c'était deux
    # libellés différents et onze écrans sans rien.
    assert PAGE.index('<main id="scene">') < PAGE.index('id="bouton-retour"')
    assert PAGE.index('id="bouton-retour"') < PAGE.index('<section id="ecran-accueil"')
    # Et les deux retours d'écran ont disparu avec lui.
    for ancien in ('id="retour-etagere"', 'id="atelier-retour"'):
        assert ancien not in PAGE, f"{ancien} fait doublon avec le retour global"
    assert "$('bouton-retour').onclick = () => revenir();" in SCRIPT


def test_il_ne_parait_que_s_il_y_a_où_revenir():
    """Sur la page perso, l'accueil ou la connexion, il n'y a pas de « avant » :
    une flèche morte apprend à ne plus regarder les flèches."""
    assert "function peutRevenir()" in SCRIPT
    peut = bloc("peutRevenir")
    assert "pileEcrans.length > 0" in peut
    assert "RACINES.has(ecranCourant())" in peut
    racines = SCRIPT[SCRIPT.index("const RACINES = new Set("):]
    racines = racines[: racines.index(")")]
    for racine in ("ecran-accueil", "ecran-connexion", "ecran-espace"):
        assert racine in racines
    assert "$('bouton-retour').hidden = !peutRevenir();" in SCRIPT


def test_la_pile_ne_tourne_pas_en_rond():
    """Page → matière → page → matière empilerait quatre écrans pour deux
    endroits, et il faudrait quatre retours pour remonter d'un cran."""
    montrer = bloc("montrer")
    assert "const deja = pileEcrans.lastIndexOf(id);" in montrer
    assert "if (deja >= 0) pileEcrans.length = deja;" in montrer
    # Et revenir ne repousse pas l'écran qu'on quitte, sinon la flèche ferait
    # l'aller-retour entre deux pages sans jamais remonter.
    assert "montrer(precedent, { retour: true });" in bloc("revenirVraiment")
    assert "if (!options.retour" in montrer


def test_on_ne_revient_jamais_dans_un_controle_quitte():
    """Ses questions ne sont pas gardées : y « revenir » rendrait un écran
    vide, et l'élève chercherait ce qu'il a mal fait."""
    jamais = SCRIPT[SCRIPT.index("const JAMAIS_REVENIR_VERS = new Set("):]
    jamais = jamais[: jamais.index(")")]
    assert "ecran-controle" in jamais and "ecran-connexion" in jamais
    assert "!JAMAIS_REVENIR_VERS.has(quitte)" in bloc("montrer")


def test_l_ecran_retrouve_est_redessine():
    """Rendu tel qu'on l'a laissé, il montrerait une fiche qu'on vient de
    supprimer ou un compteur d'avant."""
    assert "const AU_RETOUR = {" in SCRIPT
    au_retour = SCRIPT[SCRIPT.index("const AU_RETOUR = {"):]
    au_retour = au_retour[: au_retour.index("};")]
    assert "'ecran-espace': () => dessinerEspace()" in au_retour
    assert "'ecran-matiere': () => dessinerMatiere()" in au_retour
    assert "if (AU_RETOUR[precedent]) AU_RETOUR[precedent]();" in bloc("revenirVraiment")


def test_le_balayage_part_du_bord_et_de_nulle_part_ailleurs():
    """La fiche est un paquet de cartes qu'on fait glisser horizontalement. Un
    balayage vers la droite au milieu de l'écran veut dire « carte
    précédente » : si le retour le prenait, on ne pourrait plus relire la carte
    d'avant. C'est la règle du système sur un téléphone, et celle que le pouce
    connaît déjà."""
    geste = bloc("armerLeGlissementDeRetour")
    assert "const BORD_RETOUR" in SCRIPT
    assert "if (doigt.clientX > BORD_RETOUR) return;" in geste
    # Vertical : c'est un défilement, on rend la main pour de bon.
    assert "if (Math.abs(dy) > Math.abs(dx)) { glissementRetour = null; return; }" in geste
    # Une boîte ouverte prend le geste : on ne navigue pas derrière elle.
    assert "document.querySelector('dialog[open]')" in geste
    # Et la course doit être franche : un frôlement ne change pas de page.
    assert "const COURSE_RETOUR" in SCRIPT
    assert "glissementRetour.alle >= COURSE_RETOUR" in geste


def test_le_glissement_ne_laisse_pas_la_page_de_travers():
    """La scène est déplacée pendant le geste. Oublier de rendre sa position
    laisserait toute l'application décalée de cent soixante-dix pixels."""
    geste = bloc("armerLeGlissementDeRetour")
    assert "scene.style.transform = '';" in geste
    assert "scene.style.opacity = '';" in geste
    assert "touchcancel" in geste, "un geste interrompu laisserait la page de travers"
    # La transition est coupée pendant le geste, sinon la page traîne derrière
    # le doigt.
    assert "#scene[data-glisse] { transition: none; }" in STYLE


def test_quitter_un_controle_en_cours_se_demande():
    """Les questions ne sont pas gardées et en relancer un coûte un contrôle du
    mois. Ce n'est pas un geste qu'on fait du pouce sans le vouloir."""
    revenir = bloc("revenir")
    assert "ecranCourant() === 'ecran-controle'" in revenir
    assert "Quitter le contrôle ?" in revenir
    assert "coûtera un contrôle de ton mois" in revenir
    # Et on ne part pas tant qu'on n'a pas dit oui.
    assert "return false;" in revenir
    assert "controleEnCours = null; revenirVraiment();" in revenir
