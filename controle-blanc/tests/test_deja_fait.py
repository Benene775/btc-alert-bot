"""Relire ce qu'on a déjà fait, depuis sa séance.

L'écran de reprise disait « Fiche générale lue » et « 0 contrôle blanc passé ».
C'est un état, pas une porte : l'élève qui revient sur sa séance veut RELIRE sa
fiche, pas apprendre qu'elle existe. Il devait ressortir, ouvrir sa page, puis
la matière, puis la liste — quatre gestes pour revenir à ce qu'il avait sous les
yeux la veille.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")

# Jusqu'à la fin du corps : l'écran contient maintenant ses propres sections,
# et couper au premier « </section> » s'arrêtait au milieu.
REPRISE = PAGE[PAGE.index('id="ecran-reprise"'):]
REPRISE = REPRISE[: REPRISE.index("</main>")]
BLOC = SCRIPT[SCRIPT.index("function dessinerDejaFait()"):]
BLOC = BLOC[: BLOC.index("\nfunction dessinerReprise")]


def test_les_deux_listes_sont_sur_l_ecran_de_reprise():
    for identifiant in ("pan-deja-fiches", "pan-deja-controles",
                        "liste-deja-fiches", "liste-deja-controles"):
        assert f'id="{identifiant}"' in REPRISE, identifiant


def test_c_est_la_matiere_pas_la_seule_seance():
    """Un élève photographie son cours en deux fois, ou reprend un chapitre plus
    tard : ses fiches d'histoire sont ses fiches d'histoire."""
    assert "(s.matiere || '') === matiere" in BLOC
    assert "sessionsFaites()" in BLOC


def test_une_ligne_ouvre_vraiment_ce_qu_elle_montre():
    """Sinon c'est la liste d'étapes avec une autre mise en page."""
    assert "ouvrirFicheGardee" in BLOC
    assert "ouvrirControleGarde" in BLOC
    assert "ligneArchive(" in BLOC, "les lignes doivent être celles des archives"


def test_un_panneau_vide_ne_parait_pas():
    """« Tes contrôles blancs dans cette matière » suivi de rien est une
    promesse que l'écran ne tient pas."""
    assert "pan.hidden = elements.length === 0" in BLOC
    for identifiant in ("pan-deja-fiches", "pan-deja-controles"):
        balise = REPRISE[REPRISE.index(f'id="{identifiant}"'):]
        assert "hidden" in balise[: balise.index(">")], f"{identifiant} paraît au chargement"


def test_la_liste_est_bornee_et_le_reste_a_une_porte():
    """Une matière d'une année entière, ce n'est pas trois fiches."""
    assert "DEJA_SUR_LA_PAGE" in BLOC
    assert "slice(0, DEJA_SUR_LA_PAGE)" in BLOC
    assert "ouvrirMatiere(matiere)" in BLOC, "rien ne mène au reste"
    assert 'id="tout-voir-matiere"' in REPRISE


def test_elle_se_redessine_en_rouvrant_la_seance():
    bloc = SCRIPT[SCRIPT.index("function dessinerReprise()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "dessinerDejaFait()" in bloc
