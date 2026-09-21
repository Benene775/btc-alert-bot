#!/usr/bin/env python3
"""Ce que la base a vraiment enregistré, ces derniers jours.

À lancer sur le serveur quand le tableau de bord ne bouge pas alors que des
élèves travaillent. Il ne répond pas « ça marche » ou « ça ne marche pas » : il
montre où la chaîne se coupe, parce que trois pannes très différentes se
ressemblent depuis la page des mesures.

    1. LE MODE DÉMONSTRATION. Sans ANTHROPIC_API_KEY, le produit continue de
       marcher — mais il sert des contenus factices et enregistre des appels à
       zéro token. Sur le tableau de bord, les volumes montent et le coût reste
       à zéro. C'est la panne la plus grave, parce qu'un élève révise alors sur
       une fiche inventée sans que personne ne s'en rende compte.

    2. LA BASE QUI REPART DE ZÉRO. Si CB_DB_PATH ne pointe pas sur le disque
       persistant, chaque déploiement efface tout. On le voit à ceci : la plus
       vieille trace de la base est plus récente que le dernier déploiement.

    3. LES SÉANCES SANS COMPTE. « Ce que coûte chaque élève » ne lit que les
       séances rattachées à un compte. Une séance orpheline dépense de l'argent
       qui apparaît dans le total et dans aucune ligne d'élève.

N'écrit rien, n'appelle rien, ne coûte rien. N'affiche aucune adresse mail ni
aucune clé — seulement des prénoms, comme le tableau de bord.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, store  # noqa: E402

JOURS = 10


def titre(texte: str) -> None:
    print("\n" + texte)
    print("─" * len(texte))


def humaniser(quand: str) -> str:
    """« il y a 2 jours », qui se lit d'un coup, là où une date demande un calcul."""
    try:
        moment = datetime.fromisoformat(quand.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return quand or "jamais"
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    ecart = datetime.now(timezone.utc) - moment
    jours, heures = ecart.days, ecart.seconds // 3600
    if jours > 0:
        return f"{quand[:16]} — il y a {jours} jour{'s' if jours > 1 else ''}"
    if heures > 0:
        return f"{quand[:16]} — il y a {heures} h"
    return f"{quand[:16]} — il y a moins d'une heure"


def le_mode() -> None:
    titre("1. LE MODE")
    cle = bool(config.CLE_API)
    print(f"  ANTHROPIC_API_KEY posée : {'oui' if cle else 'NON'}")
    print(f"  CB_DEMO_MODE            : {os.environ.get('CB_DEMO_MODE', '(non défini)')}")
    print(f"  Mode démonstration      : {'OUI' if config.DEMO_MODE else 'non'}")
    if config.DEMO_MODE:
        print()
        print("  ⚠  LES ÉLÈVES REÇOIVENT DES CONTENUS FACTICES.")
        print("     Les fiches et les contrôles sont inventés, aucun appel n'est")
        print("     facturé, et le tableau de bord montre des volumes à 0 $.")
        print("     Poser ANTHROPIC_API_KEY (et CB_DEMO_MODE=0) dans Render.")


def la_base() -> None:
    titre("2. LA BASE")
    chemin = Path(config.DB_PATH)
    print(f"  Fichier : {chemin}")
    if not chemin.exists():
        print("  ⚠  IL N'EXISTE PAS. Rien n'a jamais été écrit à cet endroit.")
        return
    stat = chemin.stat()
    cree = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    print(f"  Taille  : {stat.st_size // 1024} Kio")
    print(f"  Modifié : {humaniser(cree)}")

    with store.curseur() as cur:
        for nom, table in (("comptes", "comptes"), ("séances", "sessions"),
                           ("appels", "usages"), ("événements", "evenements")):
            n = cur.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            print(f"  {nom:<12}: {n}")
        vieux = cur.execute("SELECT MIN(cree_le) AS q FROM comptes").fetchone()["q"]
    print(f"  Plus ancien compte : {humaniser(vieux) if vieux else 'aucun'}")
    if vieux:
        print("  (si cette date colle avec ton dernier déploiement, le disque")
        print("   n'est pas persistant et la base repart de zéro à chaque fois)")


def l_activite() -> None:
    titre(f"3. CE QUI EST ARRIVÉ CES {JOURS} DERNIERS JOURS")
    depuis = (date.today() - timedelta(days=JOURS)).isoformat()
    with store.curseur() as cur:
        lignes = cur.execute(
            "SELECT jour, action, COUNT(*) AS appels, SUM(quantite) AS quantite,"
            " SUM(tokens_entree + tokens_sortie) AS tokens"
            " FROM usages WHERE jour >= ? GROUP BY jour, action ORDER BY jour DESC, action",
            (depuis,),
        ).fetchall()
        dernier = cur.execute("SELECT MAX(horodatage) AS q FROM usages").fetchone()["q"]

    if not lignes:
        print("  Aucun appel enregistré sur la période.")
    else:
        print(f"  {'jour':<12}{'poste':<16}{'appels':>7}{'quantité':>10}{'tokens':>10}")
        for l in lignes:
            marque = "   ← 0 token : démonstration" if not l["tokens"] else ""
            print(f"  {l['jour']:<12}{l['action']:<16}{l['appels']:>7}"
                  f"{l['quantite'] or 0:>10}{l['tokens'] or 0:>10}{marque}")
    print(f"\n  Dernier appel enregistré : {humaniser(dernier) if dernier else 'jamais'}")


def les_eleves() -> None:
    titre("4. LES ÉLÈVES, ET CE QUI LEUR EST RATTACHÉ")
    with store.curseur() as cur:
        orphelines = cur.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE compte_id IS NULL").fetchone()["n"]
        lignes = cur.execute(
            "SELECT c.prenom AS prenom, c.niveau AS niveau,"
            " (SELECT COUNT(*) FROM sessions s WHERE s.compte_id = c.id) AS seances,"
            " (SELECT COUNT(*) FROM usages u JOIN sessions s ON s.id = u.session_id"
            "  WHERE s.compte_id = c.id) AS appels,"
            " (SELECT MAX(u.horodatage) FROM usages u JOIN sessions s ON s.id = u.session_id"
            "  WHERE s.compte_id = c.id) AS dernier"
            " FROM comptes c ORDER BY dernier IS NULL, dernier DESC"
        ).fetchall()

    if not lignes:
        print("  Aucun compte.")
    for l in lignes:
        print(f"  {(l['prenom'] or '(sans prénom)'):<14}{(l['niveau'] or ''):<6}"
              f"{l['seances']:>3} séance(s){l['appels']:>5} appel(s)"
              f"   dernier : {humaniser(l['dernier']) if l['dernier'] else 'jamais'}")

    print(f"\n  Séances sans compte : {orphelines}")
    if orphelines:
        print("  ⚠  Leurs appels comptent dans « Dépensé en tout » mais dans AUCUNE")
        print("     ligne d'élève. Un élève qui travaille déconnecté fait ça.")


if __name__ == "__main__":
    print("État de la base de Repère —", datetime.now().strftime("%d/%m/%Y %H:%M"))
    le_mode()
    la_base()
    l_activite()
    les_eleves()
    print()
