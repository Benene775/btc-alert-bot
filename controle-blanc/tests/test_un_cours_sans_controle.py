"""Photographier un cours n'oblige pas à annoncer un contrôle.

L'écran demandait « C'est quoi, ce contrôle ? » et posait d'office une date à
sept jours. Un élève qui photographie son cours pour en avoir la fiche — sans
que rien ne tombe — repartait donc avec une échéance qu'il n'avait pas choisie :
elle entrait dans son agenda, décomptait les jours dans le bandeau, et depuis
que les rappels existent, le faisait prévenir la veille d'un contrôle qui
n'existe pas.

Signalé en usage réel, le jour où de vrais élèves ont commencé : « ça se trouve
ce n'est pas directement pour un contrôle ».

Ce qui doit tenir :

1. La question porte sur le COURS. Le contrôle est une chose qu'on ajoute si
   elle est vraie, pas une case du formulaire qu'on subit.
2. Rien de coché, rien d'enregistré : pas de date, donc pas d'agenda, pas de
   décompte, pas de rappel.
3. Ce qui est enregistré se relit tel quel en rouvrant le formulaire — c'est ce
   qui distingue un réglage d'un formulaire qu'on remplit à l'aveugle.
4. Venir de l'agenda, c'est venir avec un contrôle : la case se coche seule.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

CODE_NU = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", SCRIPT, flags=re.S))
CONTEXTE = PAGE[PAGE.index('id="ecran-contexte"') : PAGE.index('id="ecran-photos"')]


def bloc(nom: str) -> str:
    debut = CODE_NU.index("function " + nom + "(")
    return CODE_NU[debut : CODE_NU.index("\n}\n", debut)]


def test_la_question_porte_sur_le_cours():
    assert "C’est quoi, ce cours ?" in CONTEXTE
    assert "C’est quoi, ce contrôle ?" not in PAGE


def test_le_controle_est_une_case_a_cocher():
    assert 'id="champ-a-controle"' in CONTEXTE
    assert 'type="checkbox"' in CONTEXTE
    # La date ne se montre que si elle a une raison d'être.
    assert 'id="bloc-date" hidden' in CONTEXTE
    assert "function montrerLaDate" in CODE_NU
    # Et la ligne entière se touche : viser un carré de 24 px sur un téléphone
    # est un pari.
    assert re.search(r"\.coche \{[^}]*min-height: (\d+)px", STYLE, re.S)
    assert int(re.search(r"\.coche \{[^}]*min-height: (\d+)px", STYLE, re.S).group(1)) >= 44


def test_rien_de_coche_rien_d_enregistre():
    """C'est tout le sujet : une date non choisie déclenchait un rappel la
    veille d'un contrôle qui n'existe pas."""
    corps = bloc("validerContexte")
    assert "$('champ-a-controle').checked ? $('champ-date').value : ''" in corps


def test_le_formulaire_se_relit_tel_qu_on_l_a_laisse():
    """Il ne se remplissait que de valeurs par défaut et gardait ensuite ce
    qu'on y avait tapé : rouvrir « Changer » deux fois montrait la première
    saisie, pas l'état courant. Ça marchait par accident tant que rien ne
    pouvait être vide."""
    assert "function dessinerContexte" in CODE_NU
    corps = bloc("dessinerContexte")
    assert "Boolean(etat.dateControle)" in corps
    assert "$('champ-date').value = etat.dateControle || dateParDefaut()" in corps
    assert "if (id === 'ecran-contexte') dessinerContexte();" in CODE_NU


def test_venir_de_l_agenda_coche_la_case():
    corps = bloc("demarrerSession")
    assert "$('champ-a-controle').checked = Boolean(etat.dateControle)" in corps


def test_l_ecran_des_photos_dit_les_deux_cas():
    """Sans cette ligne, « aucun contrôle prévu » serait un silence — et un
    silence se lit comme un oubli."""
    corps = bloc("dessinerResumeContexte")
    assert "'aucun contrôle prévu'" in corps
    assert "'contrôle le ' + dateCourte(etat.dateControle)" in corps
