"""Un document posé à la question 3 doit rester lisible à la question 4.

Trouvé par un testeur, pas par un test : « j'ai eu une question qui incluait une
étude de document qui est apparu en haut de la page, j'ai répondu, et la question
d'après portait sur ce même document mais il apparaissait plus, donc dur de
s'appuyer dessus. »

La cause n'est pas un hasard de génération, c'est un malentendu de forme. Le
modèle compose un sujet comme on l'imprime : le document figure une fois, et les
questions suivantes y renvoient. L'écran, lui, montre UNE question à la fois et
n'a pas de page précédente. Une question « d'après le document » sans document
est une question sans réponse possible.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import llm, prompts

RACINE = Path(__file__).resolve().parent.parent


def _controle(*questions: dict) -> dict:
    return {"titre": "T", "consigne_generale": "C", "questions": list(questions)}


def _q(numero: int, enonce: str, document: str = "") -> dict:
    return {"numero": numero, "partie": "Partie 1", "enonce": enonce,
            "document": document, "notion": "n", "chapitre": "c"}


TEXTE = "« La Révolution a commencé le 14 juillet 1789 », extrait d'un manuel."


def test_la_question_suivante_retrouve_le_document():
    controle = _controle(
        _q(1, "Présente le document.", TEXTE),
        _q(2, "D'après le document, quelle date retenir ?"),
    )
    llm._reprendre_les_documents(controle)
    assert controle["questions"][1]["document"] == TEXTE


@pytest.mark.parametrize("enonce", [
    "D'après le document, que peut-on dire ?",
    "Relève dans le texte deux arguments.",
    "Que montre le tableau ci-dessus ?",
    "Commente la carte.",
    "Explique ce graphique.",
    "Qui parle dans l'extrait ?",
    "Décris la caricature.",
])
def test_les_renvois_courants_sont_reconnus(enonce):
    controle = _controle(_q(1, "Lis.", TEXTE), _q(2, enonce))
    llm._reprendre_les_documents(controle)
    assert controle["questions"][1]["document"] == TEXTE, enonce


@pytest.mark.parametrize("enonce", [
    "Rédige un texte de dix lignes sur la Révolution.",
    "Cite deux causes de la Révolution.",
    "Explique en quoi 1789 est une rupture.",
    "Construis un tableau à deux colonnes.",
])
def test_une_question_qui_ne_renvoie_a_rien_reste_nue(enonce):
    """« un texte », « un tableau » : c'est ce qu'on demande à l'élève de
    produire, pas un document à lui montrer."""
    controle = _controle(_q(1, "Lis.", TEXTE), _q(2, enonce))
    llm._reprendre_les_documents(controle)
    assert controle["questions"][1]["document"] == ""


def test_un_nouveau_document_remplace_le_precedent():
    autre = "Tableau : population de Paris en 1789."
    controle = _controle(
        _q(1, "Lis.", TEXTE),
        _q(2, "D'après le document, que dire ?", autre),
        _q(3, "Et d'après le document, la population ?"),
    )
    llm._reprendre_les_documents(controle)
    assert controle["questions"][2]["document"] == autre


def test_sans_document_precedent_on_n_invente_rien():
    controle = _controle(_q(1, "D'après le document, que dire ?"))
    llm._reprendre_les_documents(controle)
    assert controle["questions"][0]["document"] == ""


def test_les_documents_sont_debarrasses_de_leurs_blancs():
    controle = _controle(_q(1, "Lis.", "  " + TEXTE + "\n\n"))
    llm._reprendre_les_documents(controle)
    assert controle["questions"][0]["document"] == TEXTE


def test_un_controle_vide_ou_biscornu_ne_casse_pas():
    for biscornu in ({}, {"questions": None}, {"questions": []}, {"questions": ["?"]}):
        llm._reprendre_les_documents(dict(biscornu))


def test_la_consigne_previent_le_modele():
    """Le filet rattrape ; la consigne évite d'avoir à rattraper. Sans elle, un
    document de trois paragraphes serait recopié par le serveur au lieu d'être
    écrit une fois pour chaque question qui en a besoin."""
    assert "UNE question à la fois" in prompts.CONTROLE_CONSIGNE
    assert "recopies EN ENTIER" in prompts.CONTROLE_CONSIGNE


def test_le_filet_est_pose_a_la_generation():
    source = (RACINE / "app" / "llm.py").read_text(encoding="utf-8")
    bloc = source[source.index("schema=prompts.SCHEMA_CONTROLE"):][:300]
    assert "_reprendre_les_documents(donnees)" in bloc


def test_l_ecran_affiche_le_document_de_la_question():
    """Le correctif tient au champ « document » de chaque question : si l'écran
    cessait de le lire, le filet ne servirait plus à rien."""
    script = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
    bloc = script[script.index("function dessinerQuestion()"):][:600]
    assert "question.document" in bloc
    assert "doc.hidden = !question.document" in bloc
