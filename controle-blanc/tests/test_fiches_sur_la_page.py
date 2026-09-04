"""Les fiches de révision, sur la page perso.

Une fiche se relit ; un contrôle se passe une fois. C'est donc la fiche qu'un
élève revient chercher — et elle était à trois gestes de sa page : ouvrir une
matière, descendre jusqu'à la liste, la parcourir. Pire, la seule chose de la
page qui s'appelait « Fiche de révision » n'ouvrait pas ses fiches : elle en
fabriquait une nouvelle.

Ce qui doit tenir :

1. Ses fiches sont sur sa page, pas derrière un écran.
2. Elles se filtrent par matière sur place, tant qu'il y a plus d'une matière.
3. Ce qui fabrique porte un verbe, pour qu'on ne le confonde pas avec ce qui
   ouvre.
4. La page parle à l'élève, pas de lui.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")

ESPACE = PAGE[PAGE.index('id="ecran-espace"') : PAGE.index('id="ecran-matiere"')]


def bloc(nom: str) -> str:
    """Le corps d'une fonction de app.js, jusqu'à son accolade de fin."""
    debut = SCRIPT.index("function " + nom)
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_ses_fiches_sont_sur_sa_page():
    assert 'id="pan-fiches"' in ESPACE
    for champ in ("liste-fiches-recentes", "fiches-par-matiere", "bouton-toutes-fiches"):
        assert f'id="{champ}"' in ESPACE, f"« {champ} » manque au panneau des fiches"
    assert "Tes fiches de révision" in ESPACE


def test_les_fiches_passent_avant_ce_qui_en_fabrique():
    """On vient chercher la sienne bien plus souvent qu'on n'en crée une."""
    assert ESPACE.index('id="pan-fiches"') < ESPACE.index('id="pan-outils"')
    assert ESPACE.index('id="pan-fiches"') < ESPACE.index('id="pan-matieres"')


def test_la_page_les_dessine():
    assert "dessinerFichesRecentes(sessions)" in bloc("dessinerEspace")


def test_une_ligne_ouvre_la_fiche_qu_elle_nomme():
    corps = bloc("dessinerFichesRecentes")
    assert "ouvrirFicheGardee(fiche.session.sessionId, fiche.rang)" in corps
    # Le bouton dit le nombre : savoir qu'il y en a quinze est la moitié de
    # l'information, « voir tout » n'en donne aucune.
    assert "'Voir les ' + retenues.length" in corps


def test_le_filtre_ne_parait_pas_sous_une_seule_matiere():
    corps = bloc("dessinerFiltreFiches")
    assert "comptes.size < 2" in corps
    # Et il se relâche : sans ça, une fois filtré on ne revient plus à tout.
    assert "fichesMatiere === cle ? '' : cle" in corps


def test_une_matiere_effacee_ne_reste_pas_selectionnee():
    """Sa dernière fiche supprimée, la liste paraîtrait vide sans qu'on voie
    pourquoi."""
    assert "if (fichesMatiere && !comptes.has(fichesMatiere)) fichesMatiere = '';" \
        in bloc("dessinerFichesRecentes")


def test_la_pastille_dit_la_matiere_parce_qu_on_le_demande():
    """Elle se déduisait de l'écran ouvert. La page perso réutilise ces lignes
    hors de cet écran-là : le choix devient un argument."""
    assert "function ligneArchive(e, sousTitre, avecCode = !matiereOuverte)" in SCRIPT
    assert "ligneArchive(fiche, (f) => (f.type === 'ciblee' ? 'ciblée' : ''), true)" in SCRIPT


def test_ce_qui_fabrique_porte_un_verbe():
    """« Fiche de révision » posé sous une liste de fiches se lisait comme la
    porte de cette liste, alors qu'il en crée une de plus."""
    assert "Passer un contrôle blanc" in ESPACE
    assert "Créer une fiche" in ESPACE
    assert ">Fiche de révision<" not in ESPACE


def test_la_page_parle_a_l_eleve_pas_de_lui():
    for tournure in ("'Ses fiches'", "'Ses contrôles blancs'"):
        assert tournure not in SCRIPT, f"{tournure} parle de l'élève à la troisième personne"
    assert "'Tes fiches'" in SCRIPT and "'Tes contrôles blancs'" in SCRIPT
