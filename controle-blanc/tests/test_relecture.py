"""« Voir ce que j'ai lu » : rendre la transcription vérifiable par l'élève.

Tout le produit est bâti sur ce texte — la fiche, le contrôle et la correction
le lisent, jamais les photos. Une ligne mal lue se propage donc partout, et sans
cet écran personne ne peut s'en apercevoir : une fiche fausse a l'air d'une
fiche. C'est aussi le seul signal qui dira, pendant la phase de test, si le
modèle choisi lit correctement une écriture manuscrite.
"""

from __future__ import annotations

import re
from pathlib import Path

from app import store

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

BLOC = SCRIPT[SCRIPT.index("function blocRelecture("):]
BLOC = BLOC[: BLOC.index("\n}\n")]


def test_le_perimetre_montre_la_transcription():
    corps = SCRIPT[SCRIPT.index("function dessinerPerimetre()"):]
    corps = corps[: corps.index("\n}\n")]
    assert "blocRelecture(chapitre)" in corps, "la transcription n'est affichée nulle part"


def test_elle_est_repliee_par_defaut():
    """La question de cet écran reste « c'est bien tout ce qui tombe ? ». Trois
    pages de texte dépliées d'office la noieraient."""
    assert "document.createElement('details')" in BLOC
    assert ".open = true" not in BLOC and "open" not in BLOC.split("createElement('details')")[1][:200]


def test_un_chapitre_sans_transcription_n_a_pas_de_depliant():
    """Un titre repéré sans texte lisible : proposer d'ouvrir un cadre vide
    ferait douter l'élève de son cours plutôt que de la lecture."""
    assert "if (!texte) return null;" in BLOC


def test_la_transcription_n_est_jamais_injectee_en_html():
    """Elle sort du modèle, qui a lu des photos que l'élève a choisies. Elle
    n'entre dans la page que par textContent."""
    rendu = SCRIPT[SCRIPT.index("function morceauTranscription("):]
    rendu = rendu[: rendu.index("\n/* « Voici")]
    assert "innerHTML" not in BLOC and "innerHTML" not in rendu
    assert "bloc.textContent = propre;" in rendu


def test_le_marqueur_de_page_ne_reste_pas_a_l_ecran():
    """« [[page N]] » est écrit pour le modèle, et N part de zéro. Tel quel,
    l'élève lit « [[page 0]] » en tête de son cours et croit à un bug."""
    rendu = SCRIPT[SCRIPT.index("const MARQUEUR_PAGE"):SCRIPT.index("/* « Voici")]
    assert "'Page ' + (Number(trouve[1]) + 1)" in rendu, "les pages restent numérotées à zéro"
    assert "relire-page" in rendu


def test_l_eleve_peut_dire_que_c_est_mal_lu():
    assert "relire-faux" in BLOC
    assert "tracer('transcription_signalee'" in BLOC


def test_le_signalement_n_est_pas_avale_en_silence():
    """enregistrer_evenement ignore un type inconnu sans rien lever : un nom qui
    ne figure pas dans TYPES_EVENEMENTS disparaîtrait sans laisser de trace, et
    on croirait que personne n'a signalé."""
    types = set(re.findall(r"tracer\('(\w+)'", SCRIPT))
    inconnus = types - store.TYPES_EVENEMENTS
    assert not inconnus, f"types tracés côté navigateur mais jamais enregistrés : {inconnus}"


def test_le_signalement_arrive_bien_jusqu_a_la_base(client, session):
    client.post("/api/evenement", json={
        "session_id": session, "type": "transcription_signalee",
        "details": {"chapitre": "La Première Guerre mondiale"},
    })
    with store.curseur() as cur:
        cur.execute(
            "SELECT details FROM evenements WHERE session_id = ? AND type = 'transcription_signalee'",
            (session,),
        )
        ligne = cur.fetchone()
    assert ligne is not None, "le signalement n'est pas enregistré"
    assert "Première Guerre" in ligne["details"]


def test_une_longue_transcription_ne_pousse_pas_le_bouton_hors_de_l_ecran():
    """« Oui, c'est tout » est sous la liste. Trois pages de texte déplié le
    repousseraient hors de vue, et l'élève resterait bloqué là."""
    bloc = STYLE[STYLE.index(".relire-texte {"):]
    bloc = bloc[: bloc.index("}")]
    assert "max-height" in bloc
    assert "overflow-y: auto" in bloc
    # Les retours à la ligne du cours sont ce qui le rend relisable.
    assert "white-space: pre-wrap" in bloc
