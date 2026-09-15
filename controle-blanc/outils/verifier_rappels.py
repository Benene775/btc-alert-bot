#!/usr/bin/env python3
"""Vérifie que les rappels de contrôle sont correctement configurés.

À lancer dans le shell du service, après avoir posé les trois variables :

    python -m outils.verifier_rappels

Le journal de démarrage dit seulement que les trois variables EXISTENT. Il ne
dit pas qu'elles sont justes — une clé tronquée au copier-coller, ou une
publique et une privée qui ne viennent pas de la même paire, passent ce
contrôle-là et ne se voient qu'à l'envoi, le soir, chez l'élève.

Les trois fautes que ça attrape :

1. Une variable oubliée. Les rappels sont alors simplement absents.
2. Une clé abîmée en la copiant. Le serveur démarre, annonce les rappels, et
   chaque envoi échoue.
3. Une publique et une privée dépareillées — deux exécutions de cles_vapid dont
   on a mélangé les lignes. C'est la pire : tout a l'air juste, les élèves
   s'inscrivent, et le service de push refuse chaque message parce que la
   signature ne correspond pas à la clé qu'ils ont reçue.

Rien de secret n'est affiché.
"""

from __future__ import annotations

import base64
import sys


def _octets(base64url: str) -> bytes:
    rembourre = base64url + "=" * ((4 - len(base64url) % 4) % 4)
    return base64.urlsafe_b64decode(rembourre)


def verifier() -> list[str]:
    """Rend la liste des fautes. Vide veut dire que tout est en ordre."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from py_vapid import Vapid

    from app import config

    fautes = []
    for nom, valeur in (("CB_VAPID_CLE_PUBLIQUE", config.VAPID_CLE_PUBLIQUE),
                        ("CB_VAPID_CLE_PRIVEE", config.VAPID_CLE_PRIVEE),
                        ("CB_VAPID_CONTACT", config.VAPID_CONTACT)):
        if not valeur:
            fautes.append(f"{nom} est vide ou absente")
    if fautes:
        return fautes

    # La privée doit se relire et signer pour de vrai.
    signataire = None
    try:
        signataire = Vapid.from_string(private_key=config.VAPID_CLE_PRIVEE)
        signataire.sign({"sub": config.VAPID_CONTACT, "aud": "https://exemple.test"})
    except Exception as exc:
        fautes.append("CB_VAPID_CLE_PRIVEE ne signe pas — recopiée en entier ? "
                      f"({type(exc).__name__})")

    # La publique doit être un point de courbe valide, 65 octets.
    try:
        brut = _octets(config.VAPID_CLE_PUBLIQUE)
        if len(brut) != 65 or brut[0] != 4:
            fautes.append(f"CB_VAPID_CLE_PUBLIQUE fait {len(brut)} octets au lieu de 65 "
                          "— elle a été coupée")
        else:
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), brut)
    except Exception:
        fautes.append("CB_VAPID_CLE_PUBLIQUE est illisible — recopiée en entier ?")

    # Et surtout : les deux doivent venir de LA MÊME paire.
    if signataire is not None and not fautes:
        attendue = signataire.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        if attendue != _octets(config.VAPID_CLE_PUBLIQUE):
            fautes.append("la publique et la privée ne vont pas ensemble : elles viennent "
                          "de deux exécutions différentes. Relance « python -m "
                          "outils.cles_vapid » et reprends LES DEUX lignes du même coup")

    if not config.VAPID_CONTACT.startswith(("https://", "mailto:")):
        fautes.append("CB_VAPID_CONTACT doit commencer par « https:// » ou « mailto: »")

    return fautes


def main() -> int:
    sys.path.insert(0, ".")
    try:
        fautes = verifier()
    except ImportError as exc:
        print(f"Il manque une bibliothèque : {exc}", file=sys.stderr)
        return 1

    from app import config

    if fautes:
        print("LES RAPPELS NE MARCHERONT PAS :")
        for faute in fautes:
            print("  - " + faute)
        return 1

    print("Les rappels sont bien configurés.")
    print(f"  tournée à {config.RAPPEL_HEURE} h ({config.FUSEAU_RAPPELS}), "
          f"{config.RAPPEL_JOURS_AVANT} jour avant le contrôle")
    print(f"  contact déclaré : {config.VAPID_CONTACT}")
    print()
    print("Il reste à activer les rappels sur ton téléphone : ouvre Repère depuis")
    print("l'icône de l'écran d'accueil, puis ton agenda, puis « Me prévenir la veille ».")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
