"""Sa page perso : six portes carrées, et rien d'autre.

Elle a empilé, dans l'ordre : une carte d'élève en papier seyès qui se
retournait, trois compteurs, une frise de l'année, la prochaine échéance dans
son encadré, un menu de matières, une liste des trois dernières fiches avec son
filtre par matière, deux cartes d'outils, un grand bouton, et les liens de
compte. Chaque morceau se défendait seul. Ensemble ils faisaient une page qu'on
PARCOURT, alors que c'est une page d'où l'on PART.

Ce qui doit tenir :

1. Une porte par destination, et rien sur la page qui ne soit une porte.
2. Les six sont le même objet : même carré, même trait, même famille de
   couleurs. C'est de là que vient l'harmonie, pas d'un dégradé.
3. Ce qui FABRIQUE annonce une durée ; ce qui OUVRE annonce un contenu. C'est
   ce qui remplace le verbe : un élève a un jour cliqué « Fiche de révision »
   en croyant y trouver les siennes, et s'en est fabriqué une de plus.
4. Ce qu'on revient chercher le plus souvent — ses fiches — est à un doigt.
5. La page parle à l'élève, pas de lui.
6. Les six tiennent sous le pli d'un téléphone. Mesuré sur 390 × 844 : carrés
   de 169 px, la sixième porte finit à 756 px — 88 px avant le pli. La pile
   d'avant faisait 2,4 écrans, et « Photographier un nouveau cours » — l'action
   première du produit — arrivait à 1 681 px, un écran entier SOUS le pli.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

ESPACE = PAGE[PAGE.index('id="ecran-espace"') : PAGE.index('id="ecran-matiere"')]
PORTES = ("porte-photo", "bouton-agenda", "choix-matiere",
          "outil-controle", "outil-fiche", "porte-travail")


def bloc(nom: str) -> str:
    debut = SCRIPT.index("function " + nom)
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_les_six_portes_sont_la_dans_l_ordre():
    place = [ESPACE.index(f'id="{p}"') for p in PORTES]
    assert place == sorted(place), "l'ordre des portes a changé"
    # La première est celle sans laquelle les cinq autres n'ouvrent rien.
    assert "tuile-phare" in ESPACE[place[0] - 200 : place[0]]


def test_rien_sur_la_page_qui_ne_soit_une_porte():
    """Les panneaux qui remplissaient la page — les fiches récentes, les outils,
    le menu dans son encadré, la prochaine échéance — n'ont plus de raison
    d'être : ce qu'ils contenaient se lit derrière la porte qui le concerne."""
    for disparu in ("pan-fiches", "pan-outils", "pan-choix", "prochain",
                    "carte-annee", "carte-chiffres", "liste-fiches-recentes",
                    "bouton-espace-nouveau", "frise-porte"):
        assert f'id="{disparu}"' not in ESPACE, f"« {disparu} » est revenu sur la page"
    # Il ne reste, hors des portes, que l'identité, l'atelier qu'elle ouvre,
    # l'agenda que sa porte déplie, et le pied de page.
    sections = re.findall(r'<section class="pan"[^>]*id="([\w-]+)"', ESPACE)
    assert not sections, f"des panneaux sont revenus : {sections}"


def test_les_six_sont_le_meme_objet():
    """L'harmonie ne vient pas d'un dégradé : elle vient de ce que les six
    carrés sont le même carré, dans les six teintes de l'application."""
    assert ESPACE.count('class="tuile-porte') + ESPACE.count('"tuile-porte ') >= 6

    regle = STYLE[STYLE.index(".tuile-porte {"):].split("}")[0]
    assert "aspect-ratio: 1" in regle, "les portes ne sont plus carrées"

    # Les teintes des portes sont celles des cartes, dans leur ordre.
    for rang in range(1, 6):
        assert f'.tuile-porte[data-teinte="{rang}"]' in STYLE
        assert f"var(--t{rang})" in STYLE[STYLE.index(f'.tuile-porte[data-teinte="{rang}"]'):][:160]

    # Et les six signes sont de la même main que le soleil et la lune.
    for signe in ("appareil", "agenda", "matieres", "controle", "fiche", "travail"):
        symbole = PAGE[PAGE.index(f'id="glyphe-{signe}"'):]
        symbole = symbole[: symbole.index("</symbol>")]
        assert 'viewBox="0 0 24 24"' in symbole, f"« {signe} » n'est pas au même gabarit"
        assert 'stroke="currentColor"' in symbole, f"« {signe} » n'est pas au trait"
        assert 'stroke-width="1.7"' in symbole, f"« {signe} » n'a pas la même graisse"


def test_fabriquer_annonce_un_geste_ouvrir_annonce_un_contenu():
    """Ce qui remplace le verbe. « Fiche de révision » posé sur une page où
    vivaient aussi des fiches se lisait comme la porte de ces fiches-là ; il en
    fabriquait une de plus. Sous le nom d'une porte qui FABRIQUE, on écrit donc
    ce qui va se passer — un geste, ou le temps que ça prend ; sous une porte
    qui OUVRE, ce qu'on va trouver."""
    def mot(identifiant):
        porte = ESPACE[ESPACE.index(f'id="{identifiant}"'):]
        return porte[: porte.index("</button>")] if "</button>" in porte else porte

    assert "à rédiger" in mot("outil-controle"), "le contrôle n'annonce pas le geste"
    assert "9 min" in mot("outil-fiche"), "la fiche n'annonce pas sa durée"

    portes = bloc("dessinerLesPortes")
    assert "fiches > 1 ? ' fiches' : ' fiche'" in portes, \
        "la porte des archives n'annonce pas ce qu'elle contient"
    assert "Fiches et contrôles" in ESPACE, "la porte des matières n'annonce rien"


def test_ce_qu_on_revient_chercher_est_a_un_doigt():
    """Une fiche se relit ; un contrôle se passe une fois. Ses fiches étaient à
    trois gestes : ouvrir une matière, descendre, parcourir. Elles sont à un."""
    assert "$('porte-travail').onclick = () => ouvrirMatiere(null)" in SCRIPT
    # Et la porte dit combien il y en a avant qu'on l'ouvre.
    assert 'id="mot-travail"' in ESPACE
    assert "'Rien encore'" in bloc("dessinerLesPortes")


def test_le_menu_des_matieres_est_la_tuile():
    """On ne dessine pas une imitation de menu : le « select » du système est
    étendu sur toute la porte et rendu invisible. Douze tuiles de matières
    feraient onze cents pixels sur un téléphone ; le sélecteur, lui, s'ouvre en
    plein écran, au pouce, et l'élève sait déjà s'en servir."""
    d = ESPACE.index("tuile-matieres")
    porte = ESPACE[d : ESPACE.index("</label>", d)]
    assert 'id="choix-matiere"' in porte
    assert "<label" in ESPACE[ESPACE.index("tuile-matieres") - 40 : ESPACE.index("tuile-matieres")]

    regle = STYLE[STYLE.index(".choix-matiere {"):].split("}")[0]
    assert "position: absolute" in regle and "inset: 0" in regle
    assert "opacity: 0" in regle
    # 16 px : en dessous, Safari iOS zoome la page dès qu'un champ prend le focus.
    assert "font-size: 16px" in regle

    # La règle générale des champs pose 20 px de marge haute aux « label » : la
    # porte des matières tombait vingt pixels sous ses voisines de rangée.
    assert "margin: 0;" in STYLE[STYLE.index(".tuile-porte {"):].split("}")[0]


def test_la_page_parle_a_l_eleve_pas_de_lui():
    for tournure in ("'Ses fiches'", "'Ses contrôles blancs'"):
        assert tournure not in SCRIPT, f"{tournure} parle de l'élève à la troisième personne"
    assert "'Tes fiches'" in SCRIPT and "'Tes contrôles blancs'" in SCRIPT
    for nom in ("Ton agenda", "Tes matières", "Tout ton travail"):
        assert f">{nom}<" in ESPACE


def test_la_pastille_de_couleur_est_sa_couleur():
    """Les six pastilles du choix de teinte n'avaient jamais eu de style : six
    capsules grises identiques, où l'on choisissait sa couleur à l'aveugle. Sur
    la page qu'on personnalise, c'est le seul geste de personnalisation."""
    for rang in range(1, 6):
        regle = f'.choix-teinte[data-teinte="{rang}"]'
        assert regle in STYLE, f"la pastille {rang} n'a pas de couleur"
        assert f"var(--t{rang})" in STYLE[STYLE.index(regle):][:110]
    # Et celle qui est choisie se distingue de celle qu'on survole : au doigt,
    # il n'y a pas de survol pour comparer.
    choisie = STYLE[STYLE.index('.choix-teinte[aria-pressed="true"] {'):].split("}")[0]
    assert "var(--accent)" in choisie and "box-shadow" in choisie


def test_la_teinte_choisie_habille_l_embleme():
    """C'est tout ce qui reste de la carte d'élève en papier. Elle habillait un
    bandeau teinté ; ce bandeau était laid et il a disparu, alors la couleur se
    pose sur le seul objet qui soit vraiment à l'élève — et un aplat de 56 px
    dit une couleur mieux qu'une bande pâle sur toute la largeur."""
    assert "$('moi').dataset.teinte" in SCRIPT
    for rang in range(1, 6):
        assert f'.moi[data-teinte="{rang}"] .embleme' in STYLE


def test_le_prenom_n_est_pas_un_champ_de_formulaire():
    """Il était écrit sans cadre et dans la fonte des titres depuis le premier
    jour — et il sortait quand même encadré, en 16 px, dans la fonte du texte
    courant. La règle générale des champs le visait par « input[type="text"] »,
    qui pèse (0,1,1) là où une classe seule pèse (0,1,0) : un sélecteur
    d'attribut compte comme une classe et s'ajoute à l'élément. Elle gagnait en
    silence contre l'intention écrite juste en dessous.

    Le test garde la spécificité, pas seulement l'intention : c'est elle qui
    avait cédé."""
    assert ".moi .champ-prenom {" in STYLE, \
        "la règle du prénom est retombée à une seule classe : le formulaire regagne"
    regle = STYLE[STYLE.index(".moi .champ-prenom {"):].split("}")[0]
    assert "var(--titre)" in regle, "le prénom n'est pas dans la fonte des titres"
    assert "border: 0" in regle and "background: none" in regle

    # Le cadre revient au survol et au focus : au repos, c'est un nom. Et tant
    # que le champ est vide, un trait dit qu'il y a là un blanc à remplir.
    for etat in (".moi .champ-prenom:hover", ".moi .champ-prenom:focus",
                 ".moi .champ-prenom:placeholder-shown"):
        assert etat in STYLE, f"« {etat} » manque : le champ ne dit plus qu'il s'écrit"
