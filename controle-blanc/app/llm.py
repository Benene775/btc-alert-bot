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
import re
from typing import Any

from . import config, demo, prompts

logger = logging.getLogger("controle-blanc.llm")

_client: Any = None


class ErreurModele(Exception):
    """Le modèle n'a pas pu répondre. Message déjà formulé pour l'élève."""


class CreditEpuise(ErreurModele):
    """Le compte n'a plus de crédit chez le fournisseur.

    Rangé à part parce que ce n'est pas un incident : c'est une panne
    d'exploitation. Tant que le compte n'est pas rechargé, AUCUN appel ne
    passera, pour PERSONNE. Dire « réessaie » à l'élève est alors un mensonge
    qui le fera revenir jusqu'à ce qu'il abandonne — et le seul qui puisse y
    faire quelque chose n'est pas devant l'écran.
    """


def _est_une_panne_de_credit(exc: Exception) -> bool:
    """L'API ne donne pas de code distinct : le même « invalid_request_error »
    sert à toutes les requêtes mal formées, et sur un appel en flux le statut
    remonte même à 200. Il ne reste que le message, cherché en minuscules et
    sans dépendre de sa ponctuation.

    Rencontré une fois, en vrai, au milieu d'un parcours :
    « Your credit balance is too low to access the Anthropic API. »
    """
    texte = str(getattr(exc, "message", "") or exc).lower()
    return "credit balance is too low" in texte or "purchase credits" in texte


def client() -> Any:
    global _client
    if _client is None:
        import anthropic  # importé tard : inutile en mode démonstration

        # On passe la clé explicitement plutôt que de laisser le SDK relire
        # l'environnement : c'est la version nettoyée de config qui doit servir.
        _client = anthropic.Anthropic(api_key=config.CLE_API)
    return _client


def verifier_la_cle() -> str | None:
    """La clé ouvre-t-elle vraiment la porte ? Rend None si oui, la raison sinon.

    Une clé peut être présente et refusée — recopiée de travers, révoquée,
    ou sans accès au modèle demandé. Le site démarre quand même, sert ses pages,
    et ne rate QUE les appels au modèle : chaque élève reçoit « Réessaie » sans
    que rien ne dise pourquoi. C'est exactement la panne qu'on veut voir au
    déploiement plutôt que dans le téléphone d'un élève.

    L'appel est gratuit : count_tokens ne facture rien et exige quand même une
    clé valide.

    On ne retient que le refus d'authentification. Une panne de réseau au
    démarrage n'est pas une faute de configuration, et refuser de démarrer pour
    ça couperait le site à chaque hoquet du fournisseur.
    """
    if config.DEMO_MODE:
        return None

    import anthropic

    try:
        client().messages.count_tokens(
            model=config.modele_pour("analyse"),
            messages=[{"role": "user", "content": "."}],
        )
    except anthropic.AuthenticationError as exc:
        return (
            "ANTHROPIC_API_KEY refusée par le fournisseur (" + str(exc)[:200] + "). "
            "Aucune analyse ne passera. Vérifier la valeur posée sur l'hébergeur : "
            "une clé se recopie mal, un espace invisible suffit."
        )
    except anthropic.PermissionDeniedError as exc:
        return (
            "ANTHROPIC_API_KEY sans accès au modèle " + config.modele_pour("analyse")
            + " (" + str(exc)[:200] + ")."
        )
    except Exception as exc:  # réseau, surcharge, indisponibilité passagère
        logger.warning(
            "vérification de la clé impossible au démarrage (%s) : %s — on démarre "
            "quand même, ce n'est pas une faute de configuration",
            type(exc).__name__, exc,
        )
    return None


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
) -> tuple[dict[str, Any], dict[str, Any]]:
    import anthropic

    try:
        with client().messages.stream(
            model=config.modele_pour(action),
            max_tokens=max_tokens,
            system=blocs_systeme,
            messages=[{"role": "user", "content": contenu_utilisateur}],
            thinking={"type": "adaptive"},
            output_config={"effort": config.effort_pour(action),
                           "format": {"type": "json_schema", "schema": schema}},
        ) as flux:
            reponse = flux.get_final_message()
    except anthropic.RateLimitError as exc:
        logger.warning("limite de débit atteinte : %s", exc)
        raise ErreurModele(
            "Ça bouchonne en ce moment. Réessaie dans une minute, ton travail est gardé."
        ) from exc
    except anthropic.APIStatusError as exc:
        if _est_une_panne_de_credit(exc):
            # « critical » et pas « error » : dans un journal, c'est la seule
            # ligne de la journée qui demande une action immédiate, et elle ne
            # doit pas se perdre au milieu des erreurs ordinaires.
            logger.critical(
                "CRÉDIT ÉPUISÉ chez le fournisseur — plus aucun appel ne passera, "
                "pour aucun élève, tant que le compte n'est pas rechargé : %s", exc)
            raise CreditEpuise(
                "Le service est à l'arrêt pour quelques heures. Ce n'est ni ta photo "
                "ni ton cours : ton travail est gardé, reviens tout à l'heure."
            ) from exc
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
        blocs_systeme=[{"type": "text", "text": prompts.ANALYSE_SYSTEME.format(niveau=niveau, max_doutes=config.MAX_DOUTES)}],
        contenu_utilisateur=contenu,
        schema=prompts.SCHEMA_ANALYSE,
        max_tokens=32000,
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
    donnees, usage = _appel(
        action="controle",
        blocs_systeme=_systeme_avec_cours(niveau, chapitres, "controle"),
        contenu_utilisateur=[{"type": "text", "text": consigne}],
        schema=prompts.SCHEMA_CONTROLE,
        max_tokens=20000,
    )
    _aplatir_corriges(donnees)
    _reprendre_les_documents(donnees)
    return donnees, usage


# Ce qui, dans un énoncé, renvoie à un document qu'on est censé avoir sous les
# yeux. Le déterminant compte : « le texte » désigne un document, « un texte »
# est ce qu'on demande à l'élève d'écrire.
_RENVOI_A_UN_DOCUMENT = re.compile(
    r"(?:\b(?:le|la|les|ce|cet|cette|ces|du|des|au|aux)\s+|\bl['’])"
    r"(?:document|texte|tableau|graphique|extrait|sch[eé]ma|carte|corpus|frise|figure"
    r"|illustration|photographie|image|courbe|affiche|caricature|témoignage)s?\b"
    r"|ci-(?:dessus|dessous|contre)",
    re.IGNORECASE,
)


def _reprendre_les_documents(controle: dict[str, Any]) -> None:
    """Une question qui renvoie à un document sans le porter reçoit le dernier vu.

    L'élève voit UNE question à la fois : le document écrit dans la question 3
    n'existe plus à l'écran à la question 4. Le modèle, lui, compose comme sur
    un sujet papier, où tout reste sous les yeux — il a posé la question 4
    « d'après le document » en laissant le champ vide, et la question est
    devenue sans réponse possible. Trouvé par un testeur, pas par un test.

    La consigne le dit maintenant. Mais une consigne se respecte « presque
    toujours », et presque toujours ne suffit pas quand le raté rend une
    question impossible. Ce filet ne se trompe que dans un sens : il peut
    afficher un document de trop, jamais en retirer un qui manquait.
    """
    dernier = ""
    for question in controle.get("questions") or []:
        if not isinstance(question, dict):
            continue
        porte = (question.get("document") or "").strip()
        if porte:
            question["document"] = porte
            dernier = porte
        elif dernier and _RENVOI_A_UN_DOCUMENT.search(question.get("enonce") or ""):
            logger.info(
                "question %s : renvoi à un document sans document — on reprend le précédent",
                question.get("numero"),
            )
            question["document"] = dernier


def _aplatir_corriges(controle: dict[str, Any]) -> None:
    """« corrige » redevient « points_attendus », la liste que tout le reste attend.

    Le schéma demande deux champs nommés plutôt qu'un tableau, parce que c'est
    le seul moyen d'imposer un minimum de deux éléments : l'API refuse
    « minItems » au-delà de 1. La conversion est faite ici, tout de suite, pour
    que la forme sur le fil reste une décision de ce fichier et de lui seul —
    ailleurs (la correction, la démonstration, le faux serveur, le rapport du
    banc, les tests), une question porte toujours « points_attendus ».
    """
    for question in controle.get("questions") or []:
        corrige = question.pop("corrige", None)
        if not isinstance(corrige, dict):
            continue
        points = [corrige.get("essentiel"), corrige.get("second")]
        points += corrige.get("en_plus") or []
        # Un champ obligatoire peut arriver vide : « required » impose sa
        # présence, pas son contenu. On ne garde que ce qui dit quelque chose.
        question["points_attendus"] = [p.strip() for p in points if isinstance(p, str) and p.strip()]



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
    )
