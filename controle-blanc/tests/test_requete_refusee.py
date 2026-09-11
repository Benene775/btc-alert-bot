"""Un refus du serveur doit se lire.

Un élève a vu « [object Object] » en rouge, sur l'écran de correction, devant le
seul bouton qui l'intéressait. Deux défauts se rejoignaient là.

Le premier est l'affichage : « detail » n'est une phrase que la moitié du temps
— quand la validation échoue, FastAPI y met une LISTE d'objets, un par champ
fautif. Passée telle quelle à Error(), elle donne « [object Object] ».

Le second est la cause. « NotionFragile » plafonnait ses trois champs, alors que
le schéma de la correction n'impose au modèle aucune longueur : un « pourquoi »
bavard suffisait à faire refuser la demande de fiche ciblée.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi.exceptions import RequestValidationError

from app import main
from app.schemas import NotionFragile

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")


class FausseRequete:
    class url:
        path = "/api/fiche/ciblee"


def _refus():
    return RequestValidationError([
        {"loc": ("body", "notions", 0, "pourquoi"),
         "msg": "String should have at most 1000 characters",
         "type": "string_too_long"},
    ])


def test_le_serveur_repond_une_phrase_pas_une_liste():
    reponse = main.gerer_validation(FausseRequete(), _refus())
    corps = json.loads(reponse.body)
    assert reponse.status_code == 422
    assert isinstance(corps["message"], str)
    assert "Réessaie" in corps["message"]


def test_le_serveur_garde_la_trace_de_ce_qui_clochait(caplog):
    """Sans elle, un 422 est muet des deux côtés : l'élève voit un message
    générique et personne ne sait quel champ a fâché."""
    with caplog.at_level(logging.ERROR, logger="controle-blanc"):
        main.gerer_validation(FausseRequete(), _refus())
    assert "REQUÊTE REFUSÉE" in caplog.text
    assert "/api/fiche/ciblee" in caplog.text
    assert "notions.0.pourquoi" in caplog.text, "le champ fautif doit être nommé"


def test_le_navigateur_n_affiche_jamais_un_objet():
    bloc = SCRIPT[SCRIPT.index("const dit = [corps.detail, corps.message]"):]
    bloc = bloc[: bloc.index("'autre');") + 9]
    assert "typeof m === 'string'" in bloc, "un « detail » non textuel doit être écarté"
    assert "console.error(" in bloc, "le détail doit rester consultable quelque part"


def test_une_notion_trop_longue_est_coupee_pas_refusee():
    """Ces champs sont écrits par le modèle, pas saisis par l'élève : perdre la
    fin d'une phrase vaut mieux que perdre la fiche."""
    n = NotionFragile(notion="a" * 500, chapitre="b" * 400, pourquoi="c" * 3000)
    assert len(n.notion) == 300
    assert len(n.chapitre) == 300
    assert len(n.pourquoi) == 1000


def test_une_notion_ordinaire_n_est_pas_touchee():
    n = NotionFragile(notion="Les trois phases de la guerre",
                      chapitre="La Première Guerre mondiale",
                      pourquoi="L'élève a inversé position et mouvement.")
    assert n.notion == "Les trois phases de la guerre"
    assert n.pourquoi.endswith("mouvement.")


def test_la_coupure_laisse_une_trace(caplog):
    with caplog.at_level(logging.WARNING, logger="controle-blanc.schemas"):
        NotionFragile(notion="a" * 500)
    assert "tronquée" in caplog.text
