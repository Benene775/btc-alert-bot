#!/usr/bin/env python3
"""Voir ce que la tournée des rappels voit, et l'obliger à passer maintenant.

    python -m outils.essai_rappel              # regarde, n'envoie rien
    python -m outils.essai_rappel --envoyer    # envoie pour de vrai, tout de suite
    python -m outils.essai_rappel --oublier    # efface les « déjà annoncés » du jour visé

Quand un rappel n'arrive pas, il y a cinq endroits où ça peut casser, et le
journal du serveur n'en montre aucun : personne d'abonné, agenda pas monté,
aucun contrôle à la bonne date, rappel déjà marqué comme envoyé, ou refus du
service de push. Cet outil les montre tous les cinq, dans l'ordre.

« --envoyer » sert à ne pas attendre 18 h pour savoir. « --oublier » sert à
retester le même contrôle : sans lui, la deuxième tentative ne part pas, et on
croit à une panne alors que c'est la protection contre les doublons.

Rien de secret n'est affiché : ni clé, ni adresse mail, ni adresse de push.
"""

from __future__ import annotations

import asyncio
import sys


def raconter(jour: str) -> int:
    from app import rappels, store

    abonnes = store.comptes_abonnes()
    print(f"Jour visé : {jour} (ce que « demain » veut dire à l'heure du serveur)")
    print()
    if not abonnes:
        print("PERSONNE N'EST ABONNÉ.")
        print("  Aucun navigateur n'a activé les rappels. Sur le téléphone : ouvre")
        print("  Repère DEPUIS L'ICÔNE de l'écran d'accueil (pas Safari), va dans ton")
        print("  agenda, et touche « Me prévenir la veille ».")
        return 1

    aucun = True
    for compte_id in abonnes:
        appareils = len(store.abonnements_du_compte(compte_id))
        print(f"Compte {compte_id[:8]}… — {appareils} appareil(s) abonné(s)")
        agenda = store.lire_agenda(compte_id)
        if not agenda:
            print("  aucun agenda monté au serveur : rien à annoncer")
            continue
        rendez_vous = rappels.rendez_vous_le(agenda["contenu"], jour)
        if not rendez_vous:
            print(f"  aucun contrôle noté le {jour}")
            print("  (l'agenda est bien là, mais rien à cette date — c'est la date du")
            print("   contrôle qui compte, pas celle du jour où on veut être prévenu)")
            continue
        for rv in rendez_vous:
            nom = rappels.nom_court(rv["matiere"]) or rv["matiere"] or "(sans matière)"
            deja = store.rappel_deja_envoye(compte_id, jour, rv["matiere"])
            etat = "DÉJÀ ANNONCÉ (ne repartira pas — voir --oublier)" if deja else "à annoncer"
            print(f"  {nom} : {etat}")
            if not deja:
                aucun = False

    print()
    if aucun:
        print("Rien à envoyer en l'état.")
        return 1
    apercu = None
    for compte_id in abonnes:
        agenda = store.lire_agenda(compte_id)
        if not agenda:
            continue
        matieres = [rv["matiere"] for rv in rappels.rendez_vous_le(agenda["contenu"], jour)
                    if not store.rappel_deja_envoye(compte_id, jour, rv["matiere"])]
        if matieres:
            apercu = rappels.texte_du_rappel(matieres)
            break
    if apercu:
        print("Ce qui partira :")
        print(f"  « {apercu['titre']} »")
        print(f"  « {apercu['corps']} »")
    return 0


def main() -> int:
    sys.path.insert(0, ".")
    from app import config, rappels, store

    if not config.RAPPELS_ACTIFS:
        print("Les rappels ne sont pas configurés : lance d'abord")
        print("  python -m outils.verifier_rappels")
        return 1

    jour = rappels.jour_vise()

    if "--oublier" in sys.argv:
        efface = store.oublier_rappels_du_jour(jour)
        print(f"{efface} marque(s) « déjà annoncé » effacée(s) pour le {jour}.")
        print("Le prochain passage repartira de zéro pour cette date.")
        return 0

    code = raconter(jour)

    if "--envoyer" in sys.argv:
        print()
        if code != 0:
            print("Rien à envoyer : on n'essaie pas.")
            return code
        bilan = asyncio.run(rappels.tournee(jour))
        print(f"Envoyés : {bilan['envoyes']} · abonnements périmés retirés : "
              f"{bilan['morts']} · échecs : {bilan['rates']}")
        if bilan["envoyes"]:
            print()
            print("Le service de push a ACCEPTÉ le message. S'il n'apparaît pas sur le")
            print("téléphone, ce n'est plus le serveur : regarde les notifications de")
            print("Repère dans les réglages du téléphone, et vérifie que l'application")
            print("a bien été ouverte depuis l'écran d'accueil au moins une fois depuis")
            print("la mise à jour.")
        elif bilan["rates"]:
            print()
            print("Le service de push a REFUSÉ. Les journaux du serveur portent la raison")
            print("(ligne « rappel non délivré »).")
        return 0

    if code == 0:
        print()
        print("Pour l'envoyer tout de suite : python -m outils.essai_rappel --envoyer")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
