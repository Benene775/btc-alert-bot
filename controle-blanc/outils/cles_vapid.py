#!/usr/bin/env python3
"""Fabrique la paire de clés VAPID qui signe les rappels de contrôle.

À lancer UNE FOIS, sur ta machine, avant de configurer l'hébergeur :

    python -m outils.cles_vapid

Il affiche deux lignes à coller dans les variables d'environnement du service.
Rien n'est écrit sur le disque, et surtout rien dans le dépôt — qui est public.

Ce que sont ces clés, en une phrase : le service de push d'Apple et de Google
accepte un message pour un élève seulement si l'expéditeur le signe avec une
clé privée dont la publique a été donnée au navigateur au moment de
l'inscription. C'est ce qui empêche n'importe qui d'écrire aux abonnés de
Repère en connaissant leur adresse de push.

Les changer coupe les rappels de tout le monde : les navigateurs déjà inscrits
l'ont été avec l'ancienne clé publique, et devront se réinscrire. On ne les
régénère donc que si la privée a fuité — auquel cas il faut le faire tout de
suite, et prévenir les familles que les rappels s'arrêteront le temps d'un tour.
"""

from __future__ import annotations

import base64
import sys


def _b64(octets: bytes) -> str:
    """base64url sans remplissage : la forme attendue partout dans Web Push."""
    return base64.urlsafe_b64encode(octets).rstrip(b"=").decode("ascii")


def fabriquer() -> tuple[str, str]:
    """La publique (65 octets, point non compressé) et la privée (32 octets)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    cle = ec.generate_private_key(ec.SECP256R1())
    privee = cle.private_numbers().private_value.to_bytes(32, "big")
    publique = cle.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return _b64(publique), _b64(privee)


def main() -> int:
    try:
        publique, privee = fabriquer()
    except ImportError:
        print("Il manque « cryptography » : pip install -r requirements.txt", file=sys.stderr)
        return 1

    print("# À coller dans les variables d'environnement du service.")
    print("# La privée ne doit JAMAIS entrer dans le dépôt.")
    print()
    print("CB_VAPID_CLE_PUBLIQUE=" + publique)
    print("CB_VAPID_CLE_PRIVEE=" + privee)
    print("CB_VAPID_CONTACT=mailto:ton-adresse@exemple.fr")
    print()
    print("# Sans les trois, les rappels n'existent pas : aucun réglage ne s'affiche")
    print("# chez l'élève, et aucune tâche de fond ne démarre.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
