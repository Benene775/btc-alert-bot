"""Configuration lue dans l'environnement.

Tout est réglable sans toucher au code : voir .env.example.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "oui", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip())
    except (TypeError, ValueError):
        return default


# Modèle. On ne descend pas en gamme sans décision explicite : la qualité de la
# lecture d'une écriture manuscrite et de la correction est tout le produit.
MODEL = os.environ.get("CB_MODEL", "claude-opus-5").strip() or "claude-opus-5"

# Mode démonstration : aucun appel API, contenus factices en français.
# Sert à faire cliquer le prof / les élèves dans tout le parcours sans dépenser.
DEMO_MODE = _flag("CB_DEMO_MODE", default=not bool(os.environ.get("ANTHROPIC_API_KEY")))

DB_PATH = Path(os.environ.get("CB_DB_PATH", BASE_DIR / "donnees" / "controle-blanc.sqlite3"))

# Jeton du tableau de bord /admin/metriques. Vide = tableau de bord désactivé.
ADMIN_TOKEN = os.environ.get("CB_ADMIN_TOKEN", "").strip()

# URL publique, utilisée pour fabriquer le lien de reprise ("garde ce lien").
# Vide = déduite de la requête.
PUBLIC_BASE_URL = os.environ.get("CB_PUBLIC_BASE_URL", "").strip().rstrip("/")

# --- Limites d'usage -------------------------------------------------------
# Chaque appel coûte de l'argent. Le premier contrôle blanc passe forcément ;
# ensuite on plafonne par jour, ce qui pousse aussi à revenir le lendemain
# (c'est la métrique qui nous intéresse).
QUOTAS: dict[str, dict[str, int]] = {
    "analyse": {"jour": _int("CB_QUOTA_ANALYSE_JOUR", 4), "session": _int("CB_QUOTA_ANALYSE_SESSION", 20)},
    "fiche_generale": {"jour": _int("CB_QUOTA_FICHE_JOUR", 3), "session": _int("CB_QUOTA_FICHE_SESSION", 12)},
    "controle": {"jour": _int("CB_QUOTA_CONTROLE_JOUR", 3), "session": _int("CB_QUOTA_CONTROLE_SESSION", 12)},
    "fiche_ciblee": {"jour": _int("CB_QUOTA_CIBLEE_JOUR", 5), "session": _int("CB_QUOTA_CIBLEE_SESSION", 20)},
}

# La correction n'est pas comptée : elle fait partie du contrôle déjà décompté.
# Facturer la correction reviendrait à faire payer un contrôle sans résultat.

# Et le plafond du mois, par compte cette fois. Les limites ci-dessus sont par
# séance : en ouvrir une nouvelle les remet à zéro, ce qui ne coûte rien à
# l'élève et tout à nous. C'est celui-ci qui tient l'abonnement.
#
# Calibré sur un abonnement à 7,99 € TTC, soit ~6,20 € net une fois la TVA et
# les frais de paiement retirés.
#
# Ce n'est PAS le pire cas qu'on budgète : saturer les quatre compteurs le même
# mois demande un acharnement que presque personne n'a, et dimensionner dessus
# revient à priver tout le monde pour un élève sur vingt. C'est le coût MOYEN
# par compte qui décide, et c'est celui que /admin/metriques mesure une fois
# une vraie clé posée.
#
# Ordre de grandeur, à partir de la taille des prompts et JAMAIS mesuré contre
# l'API : au plafond des quatre compteurs, ~5,30 € contre ~6,20 € encaissés ;
# un élève ordinaire tourne bien plus bas. À refaire avec les vrais chiffres.
QUOTAS_MOIS: dict[str, int] = {
    "analyse": _int("CB_QUOTA_ANALYSE_MOIS", 8),
    "fiche_generale": _int("CB_QUOTA_FICHE_MOIS", 8),
    "controle": _int("CB_QUOTA_CONTROLE_MOIS", 8),
    "fiche_ciblee": _int("CB_QUOTA_CIBLEE_MOIS", 8),
}

MAX_PHOTOS_PAR_ANALYSE = _int("CB_MAX_PHOTOS", 12)
MAX_OCTETS_PAR_PHOTO = _int("CB_MAX_OCTETS_PHOTO", 5 * 1024 * 1024)

# Durée de conservation du corrigé (les réponses attendues, gardées côté serveur
# pour que le navigateur ne les voie pas avant d'avoir répondu).
RETENTION_CORRIGES_JOURS = _int("CB_RETENTION_JOURS", 30)

# Tarifs en $/million de tokens, par modèle — sert à chiffrer les appels dans
# /admin/metriques. La clé est un morceau du nom de modèle renvoyé par l'API
# (usages.modele), pour qu'un essai Sonnet ne soit pas facturé au tarif Opus :
# c'est précisément l'erreur qu'un banc d'essai doit éviter.
#
# CES CHIFFRES SONT À VÉRIFIER sur la page de tarifs avant de s'y fier. Ils ne
# sont pas lus depuis l'API — rien ne les corrige tout seuls s'ils vieillissent.
PRIX_USD_PAR_MTOK_PAR_MODELE: dict[str, dict[str, float]] = {
    "opus": {"entree": 5.0, "sortie": 25.0, "cache_ecriture": 6.25, "cache_lecture": 0.50},
}

# Utilisé quand le nom du modèle n'est pas reconnu. Le tableau de bord le
# signale au lieu d'afficher un chiffre faux sans le dire.
PRIX_USD_PAR_MTOK = PRIX_USD_PAR_MTOK_PAR_MODELE["opus"]


def prix_du_modele(modele: str) -> tuple[dict[str, float], bool]:
    """Les tarifs pour ce modèle, et si on les connaît vraiment."""
    nom = (modele or "").lower()
    for cle, prix in PRIX_USD_PAR_MTOK_PAR_MODELE.items():
        if cle in nom:
            return prix, True
    return PRIX_USD_PAR_MTOK, False


# --- Le compte --------------------------------------------------------------
# Adresse mail et mot de passe. Le mot de passe est haché par scrypt (voir
# store.py) ; les réglages ci-dessous concernent le « mot de passe oublié », qui
# envoie un code à six chiffres, et les limites qui protègent les deux.

DUREE_CODE_MINUTES = _int("CB_DUREE_CODE_MINUTES", 10)
# Cinq essais, puis le code est brûlé : six chiffres se devinent en un million
# de coups, pas en cinq.
MAX_ESSAIS_CODE = _int("CB_MAX_ESSAIS_CODE", 5)
# Un code par minute et par adresse, quinze par heure : de quoi renvoyer un code
# perdu, pas de quoi se servir du serveur pour inonder une boîte mail.
DELAI_ENTRE_CODES_SECONDES = _int("CB_DELAI_CODES", 60)
MAX_CODES_PAR_HEURE = _int("CB_MAX_CODES_HEURE", 15)
# Et cinquante par heure et par machine : la limite par adresse ne dit rien de
# celui qui arrose mille adresses différentes. Derrière un proxy, régler
# CB_PROXY_DE_CONFIANCE=1 pour lire X-Forwarded-For au lieu de l'IP du proxy.
MAX_CODES_PAR_HEURE_ET_SOURCE = _int("CB_MAX_CODES_HEURE_SOURCE", 50)
PROXY_DE_CONFIANCE = _flag("CB_PROXY_DE_CONFIANCE", default=False)
# Une rentrée scolaire tient dans trente jours de connexion.
DUREE_JETON_JOURS = _int("CB_DUREE_JETON_JOURS", 30)

# Essais de mot de passe ratés avant blocage temporaire, par adresse et par
# machine. Un élève qui cherche son mot de passe en fait trois ; un programme
# en fait mille.
MAX_TENTATIVES = _int("CB_MAX_TENTATIVES", 10)
FENETRE_TENTATIVES_MINUTES = _int("CB_FENETRE_TENTATIVES", 15)

# Envoi du courrier. Sans serveur SMTP configuré, le code part dans les
# journaux : ça suffit en développement, jamais en production.
SMTP_HOTE = os.environ.get("CB_SMTP_HOTE", "").strip()
SMTP_PORT = _int("CB_SMTP_PORT", 587)
SMTP_UTILISATEUR = os.environ.get("CB_SMTP_UTILISATEUR", "").strip()
SMTP_MOT_DE_PASSE = os.environ.get("CB_SMTP_MOT_DE_PASSE", "")
SMTP_EXPEDITEUR = os.environ.get("CB_SMTP_EXPEDITEUR", "Repère <ne-pas-repondre@localhost>").strip()

# Renvoyer le code dans la réponse HTTP, pour cliquer dans le parcours sans
# serveur de courrier. C'est la porte grande ouverte : réservé à la
# démonstration, et refusé dès qu'un SMTP est configuré.
AUTH_CODE_EN_CLAIR = _flag("CB_AUTH_CODE_EN_CLAIR", default=DEMO_MODE) and not SMTP_HOTE
