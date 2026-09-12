"""La fiche sur papier : deux A4 au plus, le recto-verso d'une feuille.

La contrainte vient du classeur de l'élève, pas d'une préférence : au-delà, une
fiche cesse d'être une fiche. Elle est vérifiable, et elle l'a été — trois
calibres passés en vrai PDF A4 par un navigateur :

    fiche de démonstration (3 parties, 11 points) ....... 1 page
    6 parties × 6 points, phrases ordinaires ............ 2 pages
    6 parties × 6 points, phrases longues .............. 2 pages

Six parties de six points est le maximum que la consigne autorise au modèle
(FICHE_GENERALE_CONSIGNE) : c'est donc le pire cas réel, pas une hypothèse.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

IMPRESSION = STYLE[STYLE.index("@media print {"):]


def test_la_feuille_est_hors_de_l_application():
    """L'impression cache tout ce qui n'est pas elle, « main » compris. Posée
    dedans, elle disparaissait avec le reste : le PDF sortait blanc."""
    assert PAGE.index("</main>") < PAGE.index('id="fiche-papier"')
    assert "body > *:not(#fiche-papier) { display: none !important; }" in IMPRESSION


def test_elle_ne_se_voit_jamais_a_l_ecran():
    assert "#fiche-papier { display: none; }" in STYLE


def test_elle_est_batie_a_part_pas_deguisee_du_paquet():
    """Les cartes coupent une partie en deux quand la liste est longue, répètent
    leur titre à chaque morceau, cachent la phrase à retenir derrière un « Tu te
    souviens ? » et finissent par une carte de bilan. Rien de tout ça ne veut
    dire quoi que ce soit sur du papier."""
    bloc = SCRIPT[SCRIPT.index("function dessinerFichePapier("):]
    bloc = bloc[: bloc.index("\nfunction imprimerFiche")]
    assert "fiche.sections" in bloc, "la feuille doit repartir des données"
    assert "carte" not in bloc.replace("écarte", ""), "elle ne doit pas relire le paquet"
    for morceau in ("a_retenir", "definitions", "pieges"):
        assert morceau in bloc, f"« {morceau} » manque à la feuille"


def test_le_bouton_est_sur_l_ecran_de_la_fiche():
    fiche = PAGE[PAGE.index('id="ecran-fiche"'):]
    fiche = fiche[: fiche.index("</section>")]
    assert 'id="bouton-imprimer"' in fiche
    assert "$('bouton-imprimer').onclick" in SCRIPT
    assert "window.print()" in SCRIPT


def test_deux_colonnes_et_pas_de_pied_orphelin():
    """Une ligne de texte sur 188 mm se lit mal et gâche la place : une fiche est
    faite de listes courtes. Et « column-fill: auto » faisait occuper toute la
    hauteur de page au bloc, ce qui offrait une page entière au seul pied."""
    regle = IMPRESSION[IMPRESSION.index(".papier-corps {"):]
    regle = regle[: regle.index("}")]
    assert "column-count: 2;" in regle
    # Dans la RÈGLE, pas dans le commentaire qui explique pourquoi on l'a retiré.
    assert "column-fill" not in regle
    bloc = SCRIPT[SCRIPT.index("function dessinerFichePapier("):]
    bloc = bloc[: bloc.index("\nfunction imprimerFiche")]
    assert "ajouter(corps, 'footer'" in bloc, "le pied doit être dans le flux des colonnes"


def test_le_corps_reste_lisible():
    """Tenir dans deux pages ne sert à rien si personne ne les lit : 10 pt est le
    plancher sous lequel un élève de troisième renonce à relire."""
    corps = IMPRESSION[IMPRESSION.index("#fiche-papier {"):]
    corps = corps[: corps.index("}")]
    taille = re.search(r"font-size:\s*([\d.]+)pt", corps)
    assert taille and float(taille.group(1)) >= 10, "le corps est descendu sous 10 pt"


def test_elle_s_imprime_en_noir_sur_blanc():
    """Une cartouche couleur coûte plus cher que le mois d'abonnement qu'on vise,
    et la moitié des familles impriment au collège."""
    corps = IMPRESSION[IMPRESSION.index("#fiche-papier {"):]
    corps = corps[: corps.index("}")]
    assert "color: #000" in corps and "background: #fff" in corps
    couleurs = set(re.findall(r"#[0-9a-fA-F]{3,6}", IMPRESSION))
    hors_gris = {c for c in couleurs
                 if len(c) == 7 and not (c[1:3] == c[3:5] == c[5:7])}
    assert not hors_gris, f"couleurs à l'impression : {sorted(hors_gris)}"


def test_l_impression_est_comptee():
    """Savoir combien d'élèves impriment dit si la feuille sert."""
    from app import store
    assert "impression" in store.TYPES_EVENEMENTS
    assert "tracer('impression'" in SCRIPT
