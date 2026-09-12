"""Repasser un cours déjà photographié : le contrôle blanc et la fiche.

Ces deux-là ne servaient qu'à l'intérieur d'une séance ouverte, tout de suite
après les photos. Les lancer depuis sa page, sur n'importe quel cours déjà fait,
est ce qui sépare un classeur d'une archive.

Ce qui doit tenir :

1. Les deux sont visibles ensemble sur la page perso. Elles ne font pas la même
   chose — l'une fait rédiger, l'autre fait relire — et choisir laquelle est le
   geste.
2. Elles partagent un seul écran de choix. Deux copies auraient divergé à la
   première retouche.
3. Choisir un périmètre n'ampute pas la séance. Décocher un chapitre pour une
   fiche rapide ne doit pas rogner le cours pour de bon.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")


def test_les_deux_outils_sont_visibles_ensemble_sur_sa_page():
    """Chacun sa porte, côte à côte : ils ne font pas la même chose — le
    contrôle fait rédiger, la fiche fait relire — et c'est le choix qui est le
    geste."""
    espace = PAGE[PAGE.index('id="ecran-espace"') : PAGE.index('id="ecran-matiere"')]
    for outil in ("outil-controle", "outil-fiche"):
        assert f'id="{outil}"' in espace, f"« {outil} » manque sur la page perso"
        porte = espace[espace.index(f'id="{outil}"') - 120 : espace.index(f'id="{outil}"')]
        assert "tuile-porte" in porte, f"« {outil} » n'est pas une des six portes"


def test_sans_cours_les_deux_portes_sont_eteintes_pas_cachees():
    """Elles partent des pages de l'élève, pas d'ailleurs : sans cours
    photographié, elles n'ouvrent rien. Éteintes plutôt que cachées — une porte
    qui disparaît ne s'explique pas, une porte grise dit ce qui lui manque."""
    bloc = SCRIPT[SCRIPT.index("function dessinerLesPortes"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "$(id).disabled = cours === 0;" in bloc
    assert "Photographie un cours d’abord" in bloc
    assert ".tuile-porte:disabled" in (RACINE / "web" / "styles.css").read_text(encoding="utf-8")


def test_les_outils_partagent_un_seul_ecran_de_choix():
    assert 'id="ecran-atelier"' in PAGE
    for champ in ("atelier-titre", "atelier-chapeau", "bouton-lancer-atelier",
                  "atelier-matiere", "atelier-chapitres"):
        assert f'id="{champ}"' in PAGE, f"« {champ} » manque à l'atelier"

    assert "const OUTILS = {" in SCRIPT
    table = SCRIPT[SCRIPT.index("const OUTILS = {"):][:1200]
    for outil in ("controle:", "fiche:"):
        assert outil in table, outil

    bloc = SCRIPT[SCRIPT.index("async function lancerAtelier"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "demanderFicheGenerale(" in bloc and "lancerControle(" in bloc


def test_choisir_un_perimetre_n_ampute_pas_la_seance():
    """L'élève retrouverait son cours entamé, rogné, sans savoir pourquoi. Les
    chapitres cochés passent en argument, ils ne marquent rien dans la séance."""
    bloc = SCRIPT[SCRIPT.index("async function lancerAtelier"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert ".actif" not in bloc, "l'atelier marque les chapitres de la séance"
    assert "async function demanderFicheGenerale(chapitres = null)" in SCRIPT
    assert "async function lancerControle(notionsCiblees = [], chapitres = null)" in SCRIPT
    assert "chapitres: chapitres || chapitresRetenus()" in SCRIPT


def test_on_ne_repasse_qu_un_cours_vraiment_photographie():
    """Un titre de chapitre n'est pas des pages : sans transcription il n'y a
    rien à reprendre, et le modèle écrirait un contrôle sur un titre."""
    bloc = SCRIPT[SCRIPT.index("function coursRepassables"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "c.transcription" in bloc, "un cours sans texte se proposerait"
