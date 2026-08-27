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

MAX_PHOTOS_PAR_ANALYSE = _int("CB_MAX_PHOTOS", 12)
MAX_OCTETS_PAR_PHOTO = _int("CB_MAX_OCTETS_PHOTO", 5 * 1024 * 1024)

# Durée de conservation du corrigé (les réponses attendues, gardées côté serveur
# pour que le navigateur ne les voie pas avant d'avoir répondu).
RETENTION_CORRIGES_JOURS = _int("CB_RETENTION_JOURS", 30)

# Tarifs Claude Opus 5, $/million de tokens — sert uniquement à afficher un coût
# estimé dans le tableau de bord.
PRIX_USD_PAR_MTOK = {
    "entree": 5.0,
    "sortie": 25.0,
    "cache_ecriture": 6.25,
    "cache_lecture": 0.50,
}
