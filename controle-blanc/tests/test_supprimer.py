"""Supprimer une fiche, un contrôle blanc.

Demandé en usage réel. Sans ça l'archive ne fait que grossir : une fiche
ratée, un contrôle lancé par erreur, un chapitre qu'on ne révise plus restent
là pour l'année, et ce qu'on cherche s'y noie.

Ce qui doit tenir :

1. Le bouton est À CÔTÉ de la ligne, jamais dedans. Dans la ligne, un doigt
   qui vise « ouvrir » tomberait une fois sur dix sur « supprimer ».
2. On demande avant, et on dit ce qui part : une fiche et un contrôle
   n'emportent pas la même chose avec eux.
3. La suppression tient au rechargement. Écrire dans une COPIE de la séance
   ouverte l'aurait perdue au premier enregistrement suivant.
4. Le rouge est dans la boîte de confirmation, pas sur la ligne : au bord de
   chaque fiche, il serait une alarme permanente.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")


def bloc(nom: str) -> str:
    debut = SCRIPT.index("function " + nom + "(")
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_le_bouton_est_a_cote_de_la_ligne_pas_dedans():
    archive = bloc("dessinerArchive")
    assert "li.appendChild(boutonSupprimer(genre, e));" in archive, \
        "le bouton n'est pas posé à côté de la ligne"
    # La ligne elle-même reste un bouton entier : c'est elle qu'on ouvre.
    ligne = bloc("ligneArchive")
    assert "ligne-effacer" not in ligne
    # Et le « li » est nommé, car la liste porte aussi des en-têtes de mois qui
    # ne doivent pas se mettre en rangée avec un bouton de suppression.
    assert "li.className = 'archive-ligne'" in ligne
    assert ".archive-ligne { display: flex" in STYLE


def test_on_demande_avant_et_on_dit_ce_qui_part():
    assert 'id="dialogue-suppression"' in PAGE
    demander = bloc("demanderSuppression")
    assert "boite.showModal()" in demander
    assert "elle ne reviendra pas" in demander, "on ne dit pas ce que coûte une fiche"
    assert "tes réponses et sa correction partent avec lui" in demander, \
        "on ne dit pas ce qu'emporte un contrôle"
    # Rien ne part tant qu'on n'a pas dit oui.
    assert "if (boite.returnValue === 'oui') supprimerDeLArchive(genre, e);" in demander


def test_la_suppression_tient_au_rechargement():
    """La séance ouverte doit être modifiée EN MÉMOIRE puis sauvée par le chemin
    habituel. La recharger depuis le stockage rendrait une copie, et tout ce que
    l'élève ferait ensuite écraserait la suppression."""
    corps = bloc("supprimerDeLArchive")
    assert "const courante = Boolean(etat && etat.sessionId === id);" in corps
    assert "const session = courante ? etat : charger(id);" in corps
    assert "session[champ].splice(e.rang, 1);" in corps
    assert "sauver();" in corps, "la séance ouverte n'est pas enregistrée"
    assert "monterPlusTard(id);" in corps, "le serveur la ferait revenir à la synchro"
    # Et l'écran se redessine : la ligne supprimée ne reste pas à l'écran.
    assert "dessinerMatiere();" in corps


def test_le_rouge_est_dans_la_boite_pas_sur_la_ligne():
    ligne = STYLE[STYLE.index(".ligne-effacer {"):].split("}")[0]
    assert "var(--rouge)" not in ligne, "la ligne porte une alarme permanente"
    assert "var(--rouge)" in STYLE[STYLE.index(".ligne-effacer:hover {"):].split("}")[0]
    assert ".bouton-danger" in STYLE


def test_le_menage_est_compte():
    """Savoir si les élèves suppriment dit si l'archive tient sur une année."""
    from app import store
    assert "suppression" in store.TYPES_EVENEMENTS
    assert "tracer('suppression'" in SCRIPT
