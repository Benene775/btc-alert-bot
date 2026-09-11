"""Après un contrôle, « une fiche de révision » veut dire autre chose.

Signalé en usage réel : « quand j'ai voulu générer une fiche suite à mon
contrôle, sur les parties ratées, ça m'a généré exactement la même fiche. »

C'était exact, et la cause n'était pas le modèle. Vérifié en faisant tourner les
deux appels sur un vrai cours : la fiche ciblée rend bien deux sections nommées
d'après les notions ratées, aucun titre commun avec la générale, moitié moins de
texte. Le défaut était dans l'aiguillage — l'atelier « Fabriquer autre chose »
appelait toujours la fiche GÉNÉRALE, sur les mêmes chapitres. Il rendait donc,
très exactement, la feuille que l'élève venait de lire.

La fiche ciblée n'était joignable que depuis l'écran de correction, une fois.
Passé cet écran, elle n'existait plus.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")

LANCER = SCRIPT[SCRIPT.index("async function lancerAtelier()"):]
LANCER = LANCER[: LANCER.index("\n}\n")]
MAJ = SCRIPT[SCRIPT.index("function majLancerAtelier()"):]
MAJ = MAJ[: MAJ.index("\n}\n")]


def test_l_atelier_cible_quand_il_y_a_de_quoi_cibler():
    assert "demanderFicheCiblee(chapitres)" in LANCER
    assert "demanderFicheGenerale(chapitres)" in LANCER, "le cas sans contrôle reste"
    assert "fragiles.length ?" in LANCER


def test_il_lit_la_seance_choisie_pas_celle_qui_est_ouverte():
    """L'atelier travaille sur des séances qui ne sont pas forcément celle en
    cours : lire « etat » donnerait les notions d'un autre cours."""
    assert "session.notionsFragiles" in LANCER
    assert "(pris[0].session || {}).notionsFragiles" in SCRIPT


def test_il_le_dit_avant_de_depenser():
    """Une fiche de deux notions là où l'élève en attendait dix serait une
    mauvaise surprise, même quand c'est la bonne. Et chaque fiche coûte un
    appel au modèle et entame un plafond."""
    assert "sur ce que j’ai raté" in MAJ
    assert "notions fragiles" in MAJ
    assert "ne portera que là-dessus" in MAJ


def test_la_fiche_ciblee_accepte_un_perimetre():
    """Sinon elle reprend tous les chapitres de la séance, et décocher un
    chapitre dans l'atelier ne servirait à rien."""
    bloc = SCRIPT[SCRIPT.index("async function demanderFicheCiblee("):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "demanderFicheCiblee(chapitres = null)" in SCRIPT
    assert "chapitres: chapitres || chapitresRetenus()" in bloc


def test_la_consigne_du_modele_reste_celle_d_une_fiche_courte():
    """C'est elle qui fait la différence : le modèle a tout le cours sous les
    yeux, et doit s'en tenir aux notions ratées."""
    prompts = (RACINE / "app" / "prompts.py").read_text(encoding="utf-8")
    bloc = prompts[prompts.index("FICHE_CIBLEE_CONSIGNE"):]
    bloc = bloc[: bloc.index('"""', bloc.index('"""') + 3)]
    assert "uniquement sur les notions que" in bloc
    assert "Une section par notion" in bloc
    assert "tu ne récites pas le chapitre" in bloc
