"""Un contrôle noté s'annule, et se décale.

Le bouton de suppression existait : une croix de 32 px, sans étiquette, posée
à côté de la croix qui referme la fiche du jour. Deux signes identiques sur le
même écran, l'un qui ferme une feuille et l'autre qui efface un contrôle pour
de bon. Demandé en usage réel — « je voudrais qu'on ait la possibilité de
supprimer dans l'agenda » — c'est-à-dire : pas trouvé.

Et l'autre moitié manquait vraiment. « Si ça se trouve ça peut être annulé ou
décalé » : un professeur absent, une sortie scolaire, un chapitre pas fini. Il
fallait supprimer puis recréer, en reperdant ce qui tombe — la seule
information que l'élève ait saisie à la main.

Ce qui doit tenir :

1. L'action se lit en toutes lettres, et se touche avec un doigt.
2. Modifier ouvre le MÊME formulaire que pour ajouter : deux formulaires
   finiraient par diverger sur « ce qui tombe », saisissable nulle part ailleurs.
3. La date y est, et elle seule permet de décaler.
4. Supprimer se lit en toutes lettres aussi, à deux gestes de distance — pas
   derrière un signe qu'on touche par erreur en voulant fermer la fiche.
5. Le format d'un champ date suit le téléphone et rien ne peut le changer :
   la date en toutes lettres lève le doute.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

CODE_NU = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", SCRIPT, flags=re.S))


def bloc(nom: str) -> str:
    debut = CODE_NU.index("function " + nom + "(")
    return CODE_NU[debut : CODE_NU.index("\n}\n", debut)]


def test_l_action_se_lit_au_lieu_de_se_deviner():
    """« × » disait « ferme cette feuille » deux centimètres plus haut."""
    corps = bloc("dessinerJourChoisi")
    assert "'Modifier'" in corps
    assert "rendez-vous-retirer" not in SCRIPT, "la croix anonyme est revenue"
    assert "textContent = '×'" not in corps


def test_la_cible_fait_la_taille_d_un_doigt():
    """Mesuré à 27 px à la première écriture : c'est le défaut qu'on répare,
    pas seulement le mot qui manquait."""
    regle = re.search(r"\.rendez-vous-changer \{[^}]*\}", STYLE, re.S)
    assert regle, "la règle a disparu"
    taille = re.search(r"min-height: (\d+)px", regle.group(0))
    assert taille and int(taille.group(1)) >= 44, regle.group(0)


def test_modifier_et_ajouter_partagent_le_formulaire():
    """Deux formulaires auraient fini par diverger sur « ce qui tombe », que
    rien d'autre dans le produit ne permet de saisir."""
    assert "function formulaireRendezVous(existant)" in CODE_NU
    corps = bloc("formulaireRendezVous")
    assert "'Modifier ce contrôle'" in corps and "'Ajouter un contrôle'" in corps
    # Le même champ « ce qui tombe » sert dans les deux cas, pré-rempli en modification.
    assert "note.value = existant.note" in corps


def test_la_date_permet_de_decaler():
    corps = bloc("formulaireRendezVous")
    assert "quand.type = 'date'" in corps
    assert "quand.value = existant.date" in corps
    # Et seulement en modification : à l'ajout, c'est le jour qu'on vient de
    # toucher dans le calendrier.
    assert corps.index("if (existant) {") < corps.index("quand.type = 'date'")
    assert "modifierRendezVous(existant.id" in corps
    # La fiche suit le contrôle à sa nouvelle date : c'est la preuve du déplacement.
    assert "jourChoisi = nouvelleDate" in corps


def test_la_date_se_lit_aussi_en_toutes_lettres():
    """Le format d'un champ date suit le téléphone — 20/09 ici, 09/20 ailleurs —
    et aucune ligne de la page ne peut le changer."""
    corps = bloc("formulaireRendezVous")
    assert "dateCourte(existant.date)" in corps
    assert "décaler le contrôle" in corps


def test_supprimer_se_lit_en_toutes_lettres():
    corps = bloc("formulaireRendezVous")
    assert "'Supprimer ce contrôle'" in corps
    assert "retirerRendezVous(existant.id)" in corps
    # En rouge, et distinct du bouton qui enregistre.
    assert re.search(r"\.ajout-rv-effacer \{[^}]*color: var\(--rouge\)", STYLE, re.S)
    # Et on peut en sortir sans rien changer.
    assert "'Annuler'" in corps


def test_une_modification_abandonnee_ne_survit_pas_a_la_fermeture():
    """Rouvrir l'agenda sur un autre jour ne doit pas retrouver un formulaire
    de modification ouvert sur un contrôle qu'on ne voit plus."""
    assert "rvModifie = null" in bloc("basculerAgenda")
    assert CODE_NU.count("rvModifie = null") >= 3


def test_modifier_garde_ce_qu_on_ne_touche_pas():
    """Un décalage ne doit pas effacer ce qui tombe : c'est la seule chose que
    l'élève ait écrite à la main."""
    corps = bloc("modifierRendezVous")
    assert "Object.assign({}, r, champs)" in corps
