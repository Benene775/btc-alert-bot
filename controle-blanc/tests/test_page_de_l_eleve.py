"""Sa page : une barre de rubriques, ce qui presse, et ses cours en liste.

Elle a d'abord empilé une carte d'élève, trois compteurs, une frise de l'année,
un menu de matières et deux cartes d'outils : une page qu'on PARCOURT alors que
c'est une page d'où l'on PART. Elle est ensuite devenue six portes carrées, une
par destination — l'idée tenait, et produisait deux défauts que le
commanditaire a nommés en regardant le produit fini : on repassait par un
damier entre deux endroits, et une page où tout a le même poids n'a plus de
hiérarchie. « Tout est une carte arrondie. »

Elle prend maintenant la forme des outils qu'un élève ouvre déjà tous les jours.
Ce qui doit tenir :

1. Une barre de rubriques en haut, et l'une d'elles est marquée : une barre qui
   ne dit pas où l'on est ne sert à rien.
2. Ce qui presse est en tête, pas en petit sous le nom d'une tuile.
3. Les cours sont une liste indexée, avec leur état ÉCRIT — pas seulement une
   couleur, qu'un daltonien ne lit pas.
4. Rien n'est caché derrière un mécanisme : chaque destination a son élément.
5. La page parle à l'élève, pas de lui.
6. L'agenda ouvert laisse les rubriques : c'est par elles qu'on en sort.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

ESPACE = PAGE[PAGE.index('id="ecran-espace"') : PAGE.index('id="ecran-matiere"')]
RUBRIQUES = ("onglet-cours", "porte-fiches", "porte-controles", "bouton-agenda")


def bloc(nom: str) -> str:
    debut = SCRIPT.index("function " + nom)
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_les_rubriques_sont_la_dans_l_ordre():
    place = [ESPACE.index(f'id="{r}"') for r in RUBRIQUES]
    assert place == sorted(place), "l'ordre des rubriques a changé"
    # Elles viennent avant tout le reste : une barre de navigation qu'il faut
    # aller chercher en bas de page n'est pas une barre de navigation.
    assert ESPACE.index('id="rubriques-espace"') < ESPACE.index('id="rangs-cours"')


def test_les_rubriques_ne_sont_pas_celles_de_la_connexion():
    """« .onglets » désignait déjà la bascule Connexion / Inscription, avec son
    fond en gélule et son curseur glissant. Les deux jeux de règles
    s'appliquaient ensemble, et la barre héritait d'un habillage qui n'était pas
    le sien — vu à l'écran, invisible à la lecture."""
    assert 'class="rubrique"' in ESPACE
    assert 'class="onglet"' not in ESPACE, "la collision de classes est revenue"
    assert ".rubrique[data-ici]" in STYLE


def test_la_rubrique_ouverte_est_marquee():
    corps = bloc("marquerOnglet")
    for rubrique in RUBRIQUES:
        assert rubrique in corps, rubrique
    assert "dataset.ici" in corps
    assert ".rubrique[data-ici]" in STYLE, "rien ne distingue la rubrique ouverte"


def test_ce_qui_presse_est_en_tete():
    """C'était écrit en petit sous le nom d'une tuile de 169 px. C'est la seule
    chose de la page qui porte une date, et elle décide de la soirée."""
    assert ESPACE.index('id="echeance"') < ESPACE.index('id="rangs-cours"')
    corps = bloc("dessinerLesOnglets")
    assert "deLaMatiere(" in corps, "le nom de la matière n'est pas élidé"
    assert "ligneJours(" in corps


def test_la_matiere_s_elide_depuis_le_serveur():
    """« Contrôle de Histoire-Géographie / EMC » se lit aussi mal à l'écran que
    dans une notification. Le serveur tient déjà la table des noms courts et de
    leurs élisions pour les rappels : deux tables jumelles divergeraient."""
    principal = (RACINE / "app" / "main.py").read_text(encoding="utf-8")
    assert "rappels.de_la_matiere" in principal
    assert "rappels.nom_court" in principal
    assert "m.de" in bloc("deLaMatiere")
    assert "m.court" in bloc("courtMatiere")


def test_un_cours_porte_son_etat_ecrit():
    """Une pastille de couleur seule ne se lit pas par tout le monde, et un
    élève qui a huit cours ne retient pas ce que veut dire l'orange."""
    corps = bloc("dessinerLesCours")
    assert "MOT_DE_L_ETAT[etat]" in corps
    for mot in ("Acquis", "À revoir", "À tester", "En attente"):
        assert mot in SCRIPT, mot
    for etat in ("acquis", "a-revoir", "a-tester", "en-attente"):
        assert f'.pastille-etat[data-etat="{etat}"]' in STYLE, etat


def test_les_cours_sont_numerotes_sur_deux_chiffres():
    """« 01 » et « 10 » alignés : sinon la colonne des titres tremble d'une
    ligne à l'autre, et une liste qui tremble se lit comme un brouillon."""
    assert "padStart(2, '0')" in bloc("dessinerLesCours")
    assert "font-variant-numeric: tabular-nums" in STYLE


def test_ce_qui_presse_passe_devant():
    """Un élève ouvre sa page la veille d'un contrôle, pas pour relire son
    année : le cours dont l'échéance est la plus proche vient en premier."""
    corps = bloc("dessinerLesCours")
    assert "joursAvant" in corps
    assert "sort(" in corps


def test_rien_n_est_cache_derriere_un_mecanisme():
    for element in ("porte-photo", "porte-matieres", "rangs-cours", "echeance"):
        assert f'id="{element}"' in ESPACE, element


def test_la_page_parle_a_l_eleve_pas_de_lui():
    for mot in ("Mes cours", "Fiches", "Contrôles", "Agenda", "Ajouter un cours"):
        assert mot in ESPACE, mot
    assert "Ses fiches" not in ESPACE and "Son agenda" not in ESPACE


def test_l_agenda_ouvert_laisse_les_rubriques():
    """L'effacer avec le reste enfermait l'élève dans le calendrier : il fallait
    deviner que le bouton du téléphone le ramènerait."""
    mode = '#ecran-espace[data-agenda="ouvert"]'
    for efface in (".echeance", ".rangs", ".pied-cours"):
        assert f"{mode} {efface}" in STYLE, efface
    assert f"{mode} .rubriques" not in STYLE, "les rubriques s'effacent avec le reste"


def test_une_liste_vide_n_est_pas_un_cul_de_sac():
    corps = bloc("dessinerLesCours")
    assert "rangs-vide" in corps
    assert "Photographie ton premier" in corps
    # Et le bouton qui fabrique reste là : c'est tout l'objet de l'écran vide.
    assert 'id="porte-photo"' in ESPACE
