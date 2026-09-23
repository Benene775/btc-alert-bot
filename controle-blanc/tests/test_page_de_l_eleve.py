"""Sa page : une carcasse qui ne bouge pas, et une page qui change dedans.

Trois formes se sont succédé. Une pile d'objets — carte d'élève, compteurs,
frise, menu, cartes d'outils — qu'on PARCOURAIT alors que c'est une page d'où
l'on PART. Puis six portes carrées : « on repasse par un damier entre deux
endroits, et tout est une carte arrondie ». Puis une barre de rubriques, qui a
tenu quelques jours avant le grief suivant : « je veux un truc où on s'y
retrouve facilement ».

On ne s'y retrouvait pas parce que les rubriques REMPLAÇAIENT la page. D'où un
« Revenir » orphelin de 57 px entre le bouton et le pied, et rien, jamais, qui
dise où l'on est. Tous les outils qu'un élève ouvre déjà tiennent la même règle,
et c'est elle qu'on applique : la barre reste, le centre change.

Ce qui doit tenir :

1. La carcasse vit HORS des écrans : « montrer() » les cache tous, et une
   navigation rangée dans l'un d'eux s'éteindrait avec lui.
2. Elle porte les quatre sections, et marque celle où l'on est — sur sa page ET
   sur l'écran d'une matière.
3. Elle ne paraît que là où l'on navigue : pas pendant un contrôle.
4. La page a un TITRE et son action en tête, pas un aplat en bas.
5. Ce qui presse porte son action dedans.
6. Les cours sont une liste indexée, en colonnes sur un écran large, avec leur
   état ÉCRIT — pas seulement une couleur, qu'un daltonien ne lit pas.
7. La page parle à l'élève, pas de lui.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

ESPACE = PAGE[PAGE.index('id="ecran-espace"') : PAGE.index('id="ecran-matiere"')]
CARCASSE = PAGE[PAGE.index('<nav class="carcasse"') : PAGE.index('<main id="scene">')]
# Les identifiants des anciennes rubriques sont conservés : tout le script de
# l'agenda et des archives s'appuie dessus, et les renommer aurait été un
# chantier de plus pour le même résultat.
RUBRIQUES = ("onglet-cours", "porte-fiches", "porte-controles", "bouton-agenda")


def bloc(nom: str) -> str:
    debut = SCRIPT.index("function " + nom)
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_la_carcasse_vit_hors_des_ecrans():
    """C'est toute la raison d'être du chantier. « montrer() » cache TOUTES les
    sections ; une navigation rangée dans l'une d'elles s'éteint avec elle —
    d'où la page qui se remplaçait, et le « Revenir » orphelin pour en sortir.
    """
    assert '<nav class="carcasse"' in PAGE
    assert PAGE.index('<nav class="carcasse"') < PAGE.index('<main id="scene">')
    assert 'id="carcasse"' not in ESPACE, "la navigation est retournée dans la page"
    # Et le corps lui fait sa place, plutôt que d'emboîter les treize écrans
    # dans une grille pour en refaire un seul.
    assert "padding-left: var(--carcasse-large)" in STYLE


def test_la_carcasse_porte_les_quatre_sections():
    place = [CARCASSE.index(f'id="{r}"') for r in RUBRIQUES]
    assert place == sorted(place), "l'ordre des sections a changé"
    # Chacune porte son compte : une liste nommée dit combien elle contient.
    for compteur in ("carcasse-compte-cours", "mot-fiches", "mot-controles"):
        assert f'id="{compteur}"' in CARCASSE, compteur


def test_la_carcasse_n_est_pas_la_bascule_de_la_connexion():
    """« .onglets » désigne déjà la bascule Connexion / Inscription, avec son
    fond en gélule et son curseur glissant. Une collision de classes avait déjà
    fait hériter la barre d'un habillage qui n'était pas le sien — vu à l'écran,
    invisible à la lecture."""
    assert 'class="carcasse-lien"' in CARCASSE
    assert 'class="onglet"' not in CARCASSE, "la collision de classes est revenue"
    assert ".carcasse-lien[data-ici]" in STYLE


def test_la_section_ouverte_est_marquee():
    corps = bloc("marquerOnglet")
    for rubrique in RUBRIQUES:
        assert rubrique in corps, rubrique
    assert "dataset.ici" in corps
    assert ".carcasse-lien[data-ici]" in STYLE, "rien ne distingue la section ouverte"
    # Et elle est marquée SUR L'ÉCRAN D'UNE MATIÈRE aussi : une barre qui ne se
    # souvient pas d'où l'on est ne sert à rien dès qu'on quitte sa page.
    majeur = bloc("majCarcasse")
    assert "ecran-matiere" in majeur
    assert "archiveOuverte" in majeur


def test_la_carcasse_se_tait_pendant_un_controle():
    """Une barre de navigation devant quelqu'un qui compose est une sortie de
    secours offerte au mauvais moment — et un contrôle qu'on quitte n'existe
    plus. Ces écrans gardent le « ← Retour », qui rend l'endroit d'où l'on
    vient plutôt que de proposer quatre ailleurs."""
    assert "const ECRANS_AVEC_CARCASSE = new Set(['ecran-espace', 'ecran-matiere'])" in SCRIPT
    corps = bloc("majCarcasse")
    assert "carcasse.hidden = !dessus" in corps
    assert "Boolean(compte)" in corps, "la carcasse paraîtrait sans compte"


def test_la_page_a_un_titre_et_son_action_en_tete():
    """On tombait sur une liste sans savoir de quoi elle était la liste, et
    l'action principale était un aplat de 96 px tout en bas — donc plus visible
    que l'alerte qu'elle devait laisser passer devant."""
    assert 'class="tete-page"' in ESPACE
    assert ESPACE.index('class="tete-page"') < ESPACE.index('id="echeance"')
    assert ESPACE.index('id="porte-photo"') < ESPACE.index('id="rangs-cours"')
    assert 'id="compte-cours"' in ESPACE


def test_ce_qui_presse_porte_son_action():
    """La bande nommait trois notions fragiles et laissait l'élève deviner
    qu'on les retravaille depuis la liste, deux écrans plus loin."""
    assert 'id="echeance-action"' in ESPACE
    assert "function poserActionEcheance" in SCRIPT
    corps = bloc("dessinerLesOnglets")
    assert "poserActionEcheance(" in corps
    # Elle porte la couleur de l'urgence, pas celle de l'accent : c'est la
    # seule chose de la page qui presse, et deux bleus côte à côte se valent.
    assert ".echeance-action" in STYLE
    assert "var(--sur-rouge)" in STYLE


def test_la_liste_passe_en_colonnes_sur_un_ecran_large():
    """Ce que fait tout outil sérieux devant une liste. La matière et la date
    sortent alors de la phrase, où elles étaient empaquetées avec le reste."""
    assert 'id="rangs-tete"' in ESPACE
    assert ".rang-matiere" in STYLE and ".rang-quand" in STYLE
    corps = bloc("dessinerLesCours")
    assert "colonneMatiere" in corps and "colonneQuand" in corps
    # Et ce qui fait doublon s'éteint : le même fait écrit deux fois sur la
    # même ligne est du bruit.
    assert ".rang-sous-mat" in STYLE and ".rang-sous-quand" in STYLE


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
    for element in RUBRIQUES + ("carcasse-photo", "carcasse-matieres", "carcasse-moi"):
        assert f'id="{element}"' in CARCASSE, element


def test_la_page_parle_a_l_eleve_pas_de_lui():
    for mot in ("Mes cours", "Mes fiches", "Mes contrôles", "Agenda"):
        assert mot in CARCASSE, mot
    for mot in ("Mes cours", "Photographier un cours", "Mon compte"):
        assert mot in ESPACE, mot
    entier = CARCASSE + ESPACE
    assert "Ses fiches" not in entier and "Son agenda" not in entier


def test_l_agenda_ouvert_laisse_la_carcasse():
    """L'effacer avec le reste enfermait l'élève dans le calendrier : il fallait
    deviner que le bouton du téléphone le ramènerait. Depuis que la navigation
    vit dehors, rien de ce qui vide la page ne peut plus l'atteindre — c'était
    précisément l'intérêt de l'en sortir."""
    mode = '#ecran-espace[data-agenda="ouvert"]'
    for efface in (".tete-page", ".echeance", ".colonnes-espace", ".mon-compte"):
        assert f"{mode} {efface}" in STYLE, efface
    assert f"{mode} .carcasse" not in STYLE, "l'agenda efface la navigation"


def test_une_liste_vide_n_est_pas_un_cul_de_sac():
    corps = bloc("dessinerLesCours")
    assert "rangs-vide" in corps
    assert "Photographie ton premier" in corps
    # Et le bouton qui fabrique reste là, en tête : c'est tout l'objet de
    # l'écran vide. Les en-têtes de colonnes, elles, se taisent — elles ne
    # coifferaient rien.
    assert 'id="porte-photo"' in ESPACE
    assert "$('rangs-tete').hidden = true" in corps


def test_la_carcasse_liste_ses_matieres():
    """Le second niveau d'une barre latérale. Il ne paraît que sur la colonne :
    sur un téléphone, la barre du bas ne porte que des destinations."""
    assert 'id="carcasse-matieres"' in CARCASSE
    corps = bloc("dessinerCarcasse")
    assert "matieres(sessions)" in corps
    assert "ouvrirMatiere(m.cle" in corps
    # Dans l'ordre où elles pressent — le même que celui de la liste. Deux
    # ordres pour les mêmes objets sur le même écran, et l'élève cherche
    # pourquoi. C'est « matieres() » qui trie, et il trie par échéance.
    assert "codeMatiere(m.cle)" in corps and "teinteMatiere(m.cle)" in corps
    assert '.carcasse-matiere-code[data-teinte="0"]' in STYLE
    assert ".carcasse-matieres { display: none; }" in STYLE \
        or ".carcasse-tete, .carcasse-rubrique, .carcasse-matieres, .carcasse-moi { display: none; }" in STYLE


def test_le_rail_dit_ce_qui_vient_et_ou_j_en_suis():
    """Trois choses qu'on ne peut pas lire ailleurs sans un clic : la semaine,
    le mois, et où l'on s'était arrêté."""
    assert 'id="rail-espace"' in ESPACE
    corps = bloc("dessinerRail")
    assert "rail-semaine" in corps and "prochainesEcheances" in corps
    assert "rail-reprise" in corps
    # Il ne paraît que là où il y a la place d'une troisième colonne.
    assert "@media (min-width: 1180px)" in STYLE
    assert ".rail { display: none; }" in STYLE


def test_le_mois_est_compte_en_pages_pas_en_cours():
    """Le serveur compte l'analyse EN PAGES — huit cours de huit. « 12 cours
    sur 64 » serait un chiffre faux écrit proprement."""
    corps = bloc("peindreCompteursDuRail")
    assert "'analyse'" in corps
    assert "Pages photographiées" in corps
    assert "etatQuota.plafond" in corps and "etatQuota.restant" in corps


def test_le_bandeau_vide_ne_laisse_pas_une_rayure():
    """Sur la colonne de gauche, la marque vit dans la carcasse : sans séance en
    cours, le bandeau ne gardait qu'un filet de 21 px au-dessus de la page —
    mesuré dans un navigateur, pas supposé."""
    assert "bandeau.dataset.vide = dansMaPage && !etat ? 'oui' : 'non';" in SCRIPT
    assert '#bandeau[data-vide="oui"] { display: none; }' in STYLE


def test_la_barre_de_retour_se_replie_quand_elle_est_vide():
    """40 px de vide en tête de page perso, où la carcasse remplace le retour."""
    assert ".barre-retour:has(.retour[hidden]) { min-height: 0; }" in STYLE
