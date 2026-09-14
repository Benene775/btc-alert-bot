"""« Contrôle d'espagnol demain, pense à réviser. »

La seule notification que Repère envoie, et elle ne sort pas de nulle part :
elle lit l'agenda que l'élève a rempli lui-même et qui monte déjà au serveur
(PUT /api/agenda). Rien n'est deviné, rien n'est fabriqué pour faire revenir
quelqu'un — le produit n'a aucun intérêt à ce qu'un collégien ouvre une
application de plus le soir. Il en a un à ce qu'il ne découvre pas son contrôle
d'espagnol le matin même.

Trois précautions, parce que ce sont des mineurs et que c'est leur téléphone :

1. Une heure de jour, bornée dans config (7 h – 21 h). Un rappel à 23 h ne sert
   personne, et un réglage fautif ne doit pas pouvoir sonner la nuit.
2. La veille seulement. Prévenir une semaine avant fait un rappel qu'on oublie ;
   prévenir le matin même fait une mauvaise nouvelle dans le bus.
3. Une fois par contrôle. La table « rappels_envoyes » garde la trace, donc un
   redémarrage du serveur ne renvoie rien, et deux contrôles le même jour font
   deux annonces distinctes plutôt qu'une répétition.

Le transport est Web Push : le mécanisme du navigateur, sans coût par message,
sans numéro de téléphone, et sans appel au modèle. Il exige une paire de clés
VAPID ; sans elles, tout ce fichier ne fait rien (config.RAPPELS_ACTIFS).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app import config, formats, store

logger = logging.getLogger("controle-blanc")


# --- Ce qu'il y a à dire ----------------------------------------------------

def rendez_vous_le(agenda_brut: str, jour: str) -> list[dict[str, str]]:
    """Les rendez-vous posés pour ce jour-là, dans l'agenda d'un compte.

    L'agenda est un blob JSON écrit par le navigateur : on le lit avec méfiance.
    Une entrée mal formée ne doit pas faire tomber la tournée des autres.
    """
    try:
        liste = json.loads(agenda_brut or "[]")
    except ValueError:
        return []
    if not isinstance(liste, list):
        return []
    trouves = []
    for entree in liste:
        if not isinstance(entree, dict):
            continue
        if str(entree.get("date", "")).strip() != jour:
            continue
        trouves.append({
            "matiere": str(entree.get("matiere", "")).strip(),
            "note": str(entree.get("note", "")).strip(),
        })
    return trouves


# Le nom des matières tel qu'on l'écrit DANS UNE PHRASE, pas dans un menu.
# « Contrôle de Histoire-Géographie / EMC demain » n'est pas du français, et une
# notification se lit en entier ou pas du tout : sur un téléphone, le titre est
# coupé vers quarante signes. On dit donc ce qu'un élève dit — « maths »,
# « histoire-géo », « philo ».
COURT = {
    "francais": "français",
    "mathematiques": "maths",
    "histoire-geographie": "histoire-géo",
    "svt": "SVT",
    "physique-chimie": "physique-chimie",
    "technologie": "technologie",
    "anglais": "anglais",
    "espagnol": "espagnol",
    "allemand": "allemand",
    "ses": "SES",
    "philosophie": "philo",
    "autre": "",
}

# « de » s'élide devant une voyelle — d'espagnol, d'histoire-géo. Une liste
# explicite plutôt qu'une règle : les sigles commencent par une voyelle à
# l'oreille (SVT se dit « esse-vé-té ») et ne s'élident pourtant jamais à
# l'écrit. Une règle automatique écrirait « d'SVT ».
ELIDE = {"histoire-geographie", "anglais", "espagnol", "allemand"}


def nom_court(cle: str) -> str:
    return COURT.get(cle, "")


def de_la_matiere(cle: str) -> str:
    """« d'espagnol », « de maths », ou rien du tout pour « autre matière »."""
    nom = nom_court(cle)
    if not nom:
        return ""
    return ("d'" if cle in ELIDE else "de ") + nom


def texte_du_rappel(matieres: list[str]) -> dict[str, str]:
    """Le titre et le corps, à partir des matières qui tombent demain.

    Court, et sans reproche : la notification arrive chez quelqu'un qui n'a
    peut-être rien révisé, et lui rappeler ce qu'il sait déjà ne l'aide pas.
    Elle annonce et elle encourage — elle ne juge pas, et elle ne compte pas
    ce qui n'a pas été fait.
    """
    noms = [nom_court(cle) for cle in matieres if nom_court(cle)]
    corps = "Pense à réviser — tu as encore ce soir."
    if len(matieres) == 1:
        complement = de_la_matiere(matieres[0])
        titre = ("Contrôle " + complement + " demain") if complement else "Contrôle demain"
    elif len(noms) == 2:
        titre = "Deux contrôles demain : " + noms[0] + " et " + noms[1]
    else:
        # « Deux contrôles » puis « 3 contrôles » dans la même série de messages
        # se remarque. Au-delà de cinq, le chiffre reprend la main : un élève
        # qui a six contrôles le même jour a un autre problème que la typographie.
        chiffres = {3: "Trois", 4: "Quatre", 5: "Cinq"}
        titre = chiffres.get(len(matieres), str(len(matieres))) + " contrôles demain"
        if noms:
            # Le détail passe dans le corps : le titre serait coupé.
            corps = ", ".join(noms[:-1]) + " et " + noms[-1] + ". " + corps
    return {"titre": titre, "corps": corps}


# --- L'envoi ----------------------------------------------------------------

class PushMort(Exception):
    """Le navigateur ne répond plus : l'application a été désinstallée, ou
    l'abonnement révoqué. La ligne doit partir, sinon on réessaie chaque soir."""


def envoyer_a(abonnement: dict[str, str], charge: dict[str, Any]) -> None:
    """Un message, à un navigateur. Bloquant : appelé dans un fil (voir tournee)."""
    from pywebpush import WebPushException, webpush  # importé ici : optionnel au démarrage

    try:
        webpush(
            subscription_info={
                "endpoint": abonnement["endpoint"],
                "keys": {"p256dh": abonnement["p256dh"], "auth": abonnement["auth"]},
            },
            data=json.dumps(charge, ensure_ascii=False),
            vapid_private_key=config.VAPID_CLE_PRIVEE,
            vapid_claims={"sub": config.VAPID_CONTACT},
            ttl=20 * 3600,  # le rappel ne vaut plus rien après le contrôle
        )
    except WebPushException as exc:
        statut = getattr(getattr(exc, "response", None), "status_code", None)
        # 404 et 410 sont les deux réponses qui veulent dire « cet abonnement
        # n'existe plus ». Tout le reste (panne, 429) se réessaiera demain.
        if statut in (404, 410):
            raise PushMort(str(statut)) from exc
        raise


# --- La tournée -------------------------------------------------------------

def jour_vise(aujourdhui: date | None = None) -> str:
    """Le jour dont on parle : demain, en heure locale de l'élève."""
    base = aujourdhui or datetime.now(ZoneInfo(config.FUSEAU_RAPPELS)).date()
    return (base + timedelta(days=config.RAPPEL_JOURS_AVANT)).isoformat()


def a_prevenir(jour: str) -> list[dict[str, Any]]:
    """Qui prévenir, et de quoi. Sans rien envoyer : c'est ce qui rend la
    tournée lisible dans un test, et rejouable sans effet."""
    tournee = []
    for compte_id in store.comptes_abonnes():
        agenda = store.lire_agenda(compte_id)
        if not agenda:
            continue
        matieres = []
        for rv in rendez_vous_le(agenda["contenu"], jour):
            cle = rv["matiere"]
            if not cle or store.rappel_deja_envoye(compte_id, jour, cle):
                continue
            if cle not in matieres:
                matieres.append(cle)
        if matieres:
            tournee.append({"compte_id": compte_id, "matieres": matieres})
    return tournee


async def tournee(jour: str | None = None) -> dict[str, int]:
    """Un passage : on lit les agendas, on envoie, on note. Rend de quoi
    journaliser — c'est la seule trace qu'on garde d'un envoi."""
    jour = jour or jour_vise()
    envoyes = morts = rates = 0
    for cible in a_prevenir(jour):
        charge = texte_du_rappel(cible["matieres"])
        charge["jour"] = jour
        for abonnement in store.abonnements_du_compte(cible["compte_id"]):
            try:
                await asyncio.to_thread(envoyer_a, abonnement, charge)
                envoyes += 1
            except PushMort:
                store.desabonner_push(abonnement["endpoint"])
                morts += 1
            except Exception as exc:  # panne du service de push : demain, peut-être
                rates += 1
                logger.warning("rappel non délivré : %s", exc)
        # Noté même si tous les envois ont échoué : réessayer le lendemain
        # annoncerait « demain » la veille au soir d'un contrôle déjà passé.
        for cle in cible["matieres"]:
            store.noter_rappel(cible["compte_id"], jour, cle)
    return {"envoyes": envoyes, "morts": morts, "rates": rates}


async def boucle() -> None:
    """Une fois par jour, à l'heure dite. Dort le reste du temps.

    Pas de cron ni d'ordonnanceur externe : le service tourne déjà en continu
    (offre payante, disque persistant — voir DEPLOIEMENT.md), et une tâche qui
    dort ne coûte rien. Elle se réveille toutes les quinze minutes pour ne pas
    rater son heure après une mise en veille de la machine.
    """
    fuseau = ZoneInfo(config.FUSEAU_RAPPELS)
    dernier_jour = ""
    while True:
        try:
            ici = datetime.now(fuseau)
            if ici.hour >= config.RAPPEL_HEURE and ici.date().isoformat() != dernier_jour:
                dernier_jour = ici.date().isoformat()
                bilan = await tournee()
                if bilan["envoyes"] or bilan["morts"]:
                    logger.info("rappels : %s envoyé(s), %s abonnement(s) périmé(s)",
                                bilan["envoyes"], bilan["morts"])
                store.purger_rappels(ici.date().isoformat())
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # une tournée qui tombe ne doit pas tuer la boucle
            logger.exception("la tournée des rappels a échoué : %s", exc)
        await asyncio.sleep(15 * 60)
