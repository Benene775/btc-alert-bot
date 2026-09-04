"""Appels au modèle. Un seul endroit, pour que le coût reste visible.

Choix techniques :
- Sortie structurée (`output_config.format`) partout : le navigateur reçoit du JSON
  validé, pas du texte à parser.
- Le cours de l'élève est mis en cache de prompt (TTL 1 h) : il est renvoyé à chaque
  appel de la séance (fiche, contrôle, correction, fiche ciblée), c'est le plus gros
  bloc et il ne bouge pas.
- Streaming : les transcriptions et les corrections peuvent être longues, le streaming
  évite les délais d'attente HTTP.
- Chaque appel renvoie sa consommation de tokens, enregistrée pour suivre le coût réel
  par élève.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from . import config, demo, prompts

logger = logging.getLogger("controle-blanc.llm")

_client: Any = None


class ErreurModele(Exception):
    """Le modèle n'a pas pu répondre. Message déjà formulé pour l'élève."""


def client() -> Any:
    global _client
    if _client is None:
        import anthropic  # importé tard : inutile en mode démonstration

        _client = anthropic.Anthropic()
    return _client


def _usage(reponse: Any) -> dict[str, Any]:
    """Les compteurs que l'API renvoie, plus le modèle qui a servi l'appel.

    On lit le modèle sur la RÉPONSE, pas sur config.MODEL : c'est ce qui a
    réellement tourné. Sans lui, comparer deux modèles est impossible — tous
    les appels finiraient chiffrés au même tarif dans le même sac.
    """
    u = getattr(reponse, "usage", None)
    if u is None:
        return {}
    return {
        "tokens_entree": getattr(u, "input_tokens", 0) or 0,
        "tokens_sortie": getattr(u, "output_tokens", 0) or 0,
        "cache_ecriture": getattr(u, "cache_creation_input_tokens", 0) or 0,
        "cache_lecture": getattr(u, "cache_read_input_tokens", 0) or 0,
        "modele": getattr(reponse, "model", "") or "",
    }


def _appel(
    *,
    action: str,
    blocs_systeme: list[dict[str, Any]],
    contenu_utilisateur: list[dict[str, Any]],
    schema: dict[str, Any],
    max_tokens: int = 16000,
    effort: str = "high",
) -> tuple[dict[str, Any], dict[str, Any]]:
    import anthropic

    try:
        with client().messages.stream(
            model=config.modele_pour(action),
            max_tokens=max_tokens,
            system=blocs_systeme,
            messages=[{"role": "user", "content": contenu_utilisateur}],
            thinking={"type": "adaptive"},
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        ) as flux:
            reponse = flux.get_final_message()
    except anthropic.RateLimitError as exc:
        logger.warning("limite de débit atteinte : %s", exc)
        raise ErreurModele(
            "Ça bouchonne en ce moment. Réessaie dans une minute, ton travail est gardé."
        ) from exc
    except anthropic.APIStatusError as exc:
        logger.error("erreur API (%s) : %s", exc.status_code, exc)
        raise ErreurModele(
            "L'analyse n'a pas abouti. Réessaie — si ça recommence, préviens ton professeur."
        ) from exc
    except anthropic.APIConnectionError as exc:
        logger.error("erreur réseau : %s", exc)
        raise ErreurModele("Connexion perdue pendant l'analyse. Réessaie.") from exc

    if reponse.stop_reason == "refusal":
        detail = getattr(reponse, "stop_details", None)
        logger.warning("refus du modèle : %s", getattr(detail, "category", None))
        raise ErreurModele(
            "Le contenu envoyé n'a pas pu être traité. Vérifie que les photos sont bien "
            "celles de ton cours."
        )
    if reponse.stop_reason == "max_tokens":
        logger.warning("réponse tronquée (max_tokens)")
        raise ErreurModele(
            "Il y a trop de contenu d'un coup. Réessaie avec moins de chapitres à la fois."
        )

    texte = next((b.text for b in reponse.content if b.type == "text"), "")
    try:
        donnees = json.loads(texte)
    except json.JSONDecodeError as exc:  # ne devrait pas arriver avec json_schema
        logger.error("JSON invalide reçu du modèle : %s", texte[:400])
        raise ErreurModele("Réponse illisible du correcteur. Réessaie.") from exc

    return donnees, _usage(reponse)


def _systeme_avec_cours(niveau: str, chapitres: list[dict], action: str) -> list[dict[str, Any]]:
    """Préambule stable, puis le cours — c'est là qu'on pose le point de cache.

    Le point n'est posé que si cet appel partage son modèle avec assez d'autres
    pour que le cache soit rentable : un cache appartient à un modèle, et celui
    que personne ne relit coûte le double d'un appel sans cache.
    """
    cours: dict[str, Any] = {"type": "text", "text": prompts.bloc_cours(chapitres)}
    if config.doit_cacher_le_cours(action):
        cours["cache_control"] = {"type": "ephemeral", "ttl": "1h"}
    return [{"type": "text", "text": prompts.preambule(niveau)}, cours]


# --- 1. Analyse des photos --------------------------------------------------

def analyser_photos(
    images: list[tuple[str, bytes]], niveau: str, matiere: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """images : liste de (type MIME, octets). Les photos ne sont jamais stockées."""
    if config.DEMO_MODE:
        return demo.analyse(len(images)), {}

    import base64

    contenu: list[dict[str, Any]] = []
    for i, (mime, octets) in enumerate(images):
        contenu.append({"type": "text", "text": f"Photo {i} :"})
        contenu.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime,
                "data": base64.standard_b64encode(octets).decode("ascii"),
            },
        })
    indication = f"Matière annoncée par l'élève : {matiere}." if matiere else ""
    contenu.append({
        "type": "text",
        "text": (
            f"Voici {len(images)} photo(s) du cours. {indication} "
            "Transcris-les et découpe-les en chapitres."
        ),
    })

    return _appel(
        action="analyse",
        blocs_systeme=[{"type": "text", "text": prompts.ANALYSE_SYSTEME.format(niveau=niveau)}],
        contenu_utilisateur=contenu,
        schema=prompts.SCHEMA_ANALYSE,
        max_tokens=32000,
        effort="high",
    )


# --- 2. Fiches --------------------------------------------------------------

def fiche_generale(
    chapitres: list[dict], niveau: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    if config.DEMO_MODE:
        return demo.fiche_generale(chapitres), {}
    return _appel(
        action="fiche_generale",
        blocs_systeme=_systeme_avec_cours(niveau, chapitres, "fiche_generale"),
        contenu_utilisateur=[{"type": "text", "text": prompts.FICHE_GENERALE_CONSIGNE}],
        schema=prompts.SCHEMA_FICHE,
        max_tokens=16000,
    )


def fiche_ciblee(
    chapitres: list[dict], niveau: str, notions: list[dict]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if config.DEMO_MODE:
        return demo.fiche_ciblee(notions), {}
    liste = "\n".join(
        f"- {n.get('notion', '')} (chapitre : {n.get('chapitre', '')}) — ce qui coince : "
        f"{n.get('pourquoi', '')}"
        for n in notions
    )
    return _appel(
        action="fiche_ciblee",
        blocs_systeme=_systeme_avec_cours(niveau, chapitres, "fiche_ciblee"),
        contenu_utilisateur=[
            {"type": "text", "text": prompts.FICHE_CIBLEE_CONSIGNE.format(notions=liste)}
        ],
        schema=prompts.SCHEMA_FICHE,
        max_tokens=12000,
    )


# --- 3. Contrôle blanc ------------------------------------------------------

def generer_controle(
    chapitres: list[dict],
    niveau: str,
    matiere_nom: str,
    structure: str,
    duree: int,
    notions_ciblees: list[str] | None = None,
    enonces_deja_poses: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if config.DEMO_MODE:
        return demo.controle(chapitres, notions_ciblees, bool(enonces_deja_poses)), {}

    contrainte_notions = ""
    if notions_ciblees:
        contrainte_notions = (
            "\n- Ce contrôle ne porte QUE sur les notions suivantes, que l'élève a ratées :\n"
            + "\n".join(f"  · {n}" for n in notions_ciblees)
            + "\n  Tu les abordes sous un angle différent de la première fois."
        )
    contrainte_deja = ""
    if enonces_deja_poses:
        contrainte_deja = (
            "\n- Ces énoncés ont DÉJÀ été posés à l'élève. Tu en poses de nouveaux, sur les "
            "mêmes notions, sans les reformuler à peine :\n"
            + "\n".join(f"  · {e}" for e in enonces_deja_poses[:20])
        )

    mini, maxi = (4, 6) if notions_ciblees else (5, 9)
    consigne = prompts.CONTROLE_CONSIGNE.format(
        matiere=matiere_nom,
        structure=structure,
        duree=duree,
        niveau=niveau,
        mini=mini,
        maxi=maxi,
        contrainte_notions=contrainte_notions,
        contrainte_deja_posees=contrainte_deja,
    )
    return _appel(
        action="controle",
        blocs_systeme=_systeme_avec_cours(niveau, chapitres, "controle"),
        contenu_utilisateur=[{"type": "text", "text": consigne}],
        schema=prompts.SCHEMA_CONTROLE,
        max_tokens=20000,
        effort="high",
    )



# --- 4. Correction ----------------------------------------------------------

def corriger(
    chapitres: list[dict],
    niveau: str,
    questions: list[dict],
    reponses: dict[int, str],
    numeros_signales: set[int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if config.DEMO_MODE:
        return demo.correction(questions, reponses, numeros_signales), {}

    copie = ["COPIE DE L'ÉLÈVE", ""]
    for q in questions:
        numero = q["numero"]
        copie.append(f"--- Question {numero} ({q.get('notion', '')}) ---")
        if q.get("document"):
            copie.append(f"Document fourni : {q['document']}")
        copie.append(f"Énoncé : {q.get('enonce', '')}")
        copie.append("Ce qui était attendu : " + " ; ".join(q.get("points_attendus", [])))
        copie.append(f"Repère dans le cours : {q.get('ou_dans_le_cours', '')}")
        reponse = (reponses.get(numero) or "").strip()
        copie.append("Réponse de l'élève : " + (reponse if reponse else "(aucune réponse)"))
        if numero in numeros_signales:
            copie.append(
                "L'élève a signalé cette question comme lui semblant fausse. Si tu penses "
                "qu'il a raison, dis-le franchement dans « ce_qui_va » et mets le statut "
                "à « acquis »."
            )
        copie.append("")

    return _appel(
        action="correction",
        blocs_systeme=_systeme_avec_cours(niveau, chapitres, "correction"),
        contenu_utilisateur=[
            {"type": "text", "text": "\n".join(copie)},
            {"type": "text", "text": prompts.CORRECTION_CONSIGNE},
        ],
        schema=prompts.SCHEMA_CORRECTION,
        max_tokens=20000,
        effort="high",
    )
