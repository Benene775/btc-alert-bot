"""Stockage serveur, réduit au strict nécessaire.

Ce qu'on garde ici, et pourquoi :
  - un identifiant de session aléatoire, sans aucune donnée personnelle ;
  - les compteurs d'usage (les quotas doivent être infalsifiables, donc côté serveur) ;
  - le corrigé d'un contrôle en cours (sinon le navigateur reçoit les réponses
    attendues avant que l'élève ait répondu) ;
  - des événements anonymes pour les trois métriques du test.

  - depuis l'entrée par mail : une adresse par compte, et rien d'autre. Pas de
    mot de passe — on n'en demande pas — donc rien à voler qui ouvre autre chose.
    Le code à six chiffres et le jeton de connexion ne sont gardés que hachés.

Ce qu'on ne garde pas : les photos du cours (traitées en mémoire puis jetées),
le texte du cours, les réponses de l'élève, ses fiches. Tout ça vit dans son
navigateur.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterator

from . import config

_verrou = threading.Lock()
_connexion: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,
    cree_le       TEXT NOT NULL,
    vu_le         TEXT NOT NULL,
    niveau        TEXT,
    matiere       TEXT,
    date_controle TEXT
);

CREATE TABLE IF NOT EXISTS usages (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT NOT NULL,
    action         TEXT NOT NULL,
    jour           TEXT NOT NULL,
    horodatage     TEXT NOT NULL,
    tokens_entree  INTEGER DEFAULT 0,
    tokens_sortie  INTEGER DEFAULT 0,
    cache_ecriture INTEGER DEFAULT 0,
    cache_lecture  INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_usages_session ON usages (session_id, action, jour);

CREATE TABLE IF NOT EXISTS evenements (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    type       TEXT NOT NULL,
    details    TEXT,
    jour       TEXT NOT NULL,
    horodatage TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evenements_session ON evenements (session_id, type);
CREATE INDEX IF NOT EXISTS idx_evenements_jour ON evenements (jour);

CREATE TABLE IF NOT EXISTS comptes (
    id      TEXT PRIMARY KEY,
    email   TEXT NOT NULL UNIQUE,
    cree_le TEXT NOT NULL,
    vu_le   TEXT NOT NULL
);

-- Un seul code vivant par adresse : en demander un deuxième annule le premier.
-- L'empreinte, jamais le code : une base volée ne doit pas ouvrir les boîtes.
CREATE TABLE IF NOT EXISTS codes (
    email      TEXT PRIMARY KEY,
    empreinte  TEXT NOT NULL,
    expire_le  TEXT NOT NULL,
    essais     INTEGER NOT NULL DEFAULT 0,
    demande_le TEXT NOT NULL
);

-- Compte les demandes par adresse pour la limite horaire. Purgé avec l'âge.
CREATE TABLE IF NOT EXISTS demandes_code (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT '',
    horodatage TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_demandes_email ON demandes_code (email, horodatage);
CREATE INDEX IF NOT EXISTS idx_demandes_source ON demandes_code (source, horodatage);

-- Le jeton de connexion, haché lui aussi : il vaut le compte.
CREATE TABLE IF NOT EXISTS jetons (
    empreinte TEXT PRIMARY KEY,
    compte_id TEXT NOT NULL,
    cree_le   TEXT NOT NULL,
    expire_le TEXT NOT NULL,
    vu_le     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jetons_compte ON jetons (compte_id);

CREATE TABLE IF NOT EXISTS corriges (
    controle_id TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    contenu     TEXT NOT NULL,
    cree_le     TEXT NOT NULL
);
"""


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def aujourdhui() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # Les séances d'avant l'entrée par mail n'ont pas de colonne compte_id.
    # SQLite n'a pas d'« ADD COLUMN IF NOT EXISTS » : on regarde d'abord.
    colonnes = {ligne[1] for ligne in conn.execute("PRAGMA table_info(sessions)")}
    if "compte_id" not in colonnes:
        conn.execute("ALTER TABLE sessions ADD COLUMN compte_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_compte ON sessions (compte_id)")
    demandes = {ligne[1] for ligne in conn.execute("PRAGMA table_info(demandes_code)")}
    if demandes and "source" not in demandes:
        conn.execute("ALTER TABLE demandes_code ADD COLUMN source TEXT NOT NULL DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_demandes_source ON demandes_code (source, horodatage)")
    conn.commit()


def connexion() -> sqlite3.Connection:
    global _connexion
    with _verrou:
        if _connexion is None:
            config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            _connexion = sqlite3.connect(config.DB_PATH, check_same_thread=False)
            _connexion.row_factory = sqlite3.Row
            _connexion.execute("PRAGMA journal_mode=WAL")
            _init(_connexion)
        return _connexion


@contextmanager
def curseur() -> Iterator[sqlite3.Cursor]:
    conn = connexion()
    with _verrou:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        finally:
            cur.close()


def reinitialiser_pour_tests() -> None:
    """Referme la connexion (les tests pointent CB_DB_PATH ailleurs)."""
    global _connexion
    with _verrou:
        if _connexion is not None:
            _connexion.close()
            _connexion = None


# --- Sessions --------------------------------------------------------------

def creer_session(compte_id: str) -> str:
    identifiant = secrets.token_urlsafe(9)
    with curseur() as cur:
        cur.execute(
            "INSERT INTO sessions (id, cree_le, vu_le, compte_id) VALUES (?, ?, ?, ?)",
            (identifiant, maintenant(), maintenant(), compte_id),
        )
    return identifiant


def session_existe(session_id: str, compte_id: str | None = None) -> bool:
    """Sans compte_id, la question est « cette séance existe-t-elle ». Avec, elle
    devient « est-elle à ce compte » : le lien de reprise d'un camarade ne doit
    pas ouvrir son cours. Les séances d'avant l'entrée par mail n'ont pas de
    compte : la première personne qui les rouvre se les approprie."""
    with curseur() as cur:
        cur.execute("SELECT compte_id FROM sessions WHERE id = ?", (session_id,))
        ligne = cur.fetchone()
        if ligne is None:
            return False
        if compte_id is None:
            return True
        if ligne["compte_id"] is None:
            cur.execute("UPDATE sessions SET compte_id = ? WHERE id = ?", (compte_id, session_id))
            return True
        return ligne["compte_id"] == compte_id


def toucher_session(session_id: str, **champs: Any) -> None:
    """Met à jour la dernière visite, et éventuellement niveau/matière/date."""
    autorises = {"niveau", "matiere", "date_controle"}
    maj = {k: v for k, v in champs.items() if k in autorises and v}
    with curseur() as cur:
        cur.execute("UPDATE sessions SET vu_le = ? WHERE id = ?", (maintenant(), session_id))
        for cle, valeur in maj.items():
            cur.execute(f"UPDATE sessions SET {cle} = ? WHERE id = ?", (valeur, session_id))


# --- Comptes, codes, jetons -------------------------------------------------
#
# Trois règles, et tout le reste en découle :
#   1. On ne stocke jamais un secret en clair. Le code à six chiffres et le
#      jeton de connexion sont hachés ; la base volée n'ouvre aucune boîte.
#   2. On ne dit jamais si une adresse est connue. « Un code est parti » est la
#      seule réponse possible, sinon le formulaire devient un annuaire d'élèves.
#   3. On borne tout : cinq essais par code, un code par minute, quinze par
#      heure. Sans ça, six chiffres se devinent et une boîte mail se noie.

class ErreurAuth(Exception):
    """Refus d'entrée, avec un message dicible à un élève."""

    def __init__(self, message: str, genre: str = "refus", attendre: int = 0):
        super().__init__(message)
        self.message = message
        self.genre = genre
        self.attendre = attendre


# Volontairement permissif : on valide la forme, pas l'existence. C'est le code
# reçu qui prouve l'adresse — un motif trop strict ne fait que rejeter des
# adresses valides et rares.
MOTIF_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s.]+(\.[^@\s.]+)+$")
MAX_LONGUEUR_EMAIL = 254


def normaliser_email(brut: str) -> str:
    """Minuscules et espaces retirés : « Lina@Ex.Fr » et « lina@ex.fr » sont la
    même personne, et deux comptes pour une élève, c'est son travail coupé en deux."""
    email = (brut or "").strip().lower()
    if len(email) > MAX_LONGUEUR_EMAIL or not MOTIF_EMAIL.match(email):
        raise ErreurAuth("Cette adresse ne ressemble pas à une adresse mail.", "email")
    return email


def _empreinte(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _plus_tard(minutes: int = 0, jours: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes, days=jours)).isoformat(
        timespec="seconds")


def _expire(horodatage: str) -> bool:
    return datetime.fromisoformat(horodatage) < datetime.now(timezone.utc)


def preparer_code(email: str, source: str = "") -> str:
    """Fabrique le code, l'enregistre haché, et rend le clair — une seule fois,
    à l'appelant qui va l'envoyer par courrier. Il n'est plus lisible ensuite."""
    _verifier_cadence(email, source)
    # secrets, pas random : un code prévisible est un code déjà connu.
    code = f"{secrets.randbelow(1_000_000):06d}"
    with curseur() as cur:
        cur.execute(
            "INSERT OR REPLACE INTO codes (email, empreinte, expire_le, essais, demande_le)"
            " VALUES (?, ?, ?, 0, ?)",
            (email, _empreinte(code), _plus_tard(minutes=config.DUREE_CODE_MINUTES), maintenant()),
        )
        cur.execute("INSERT INTO demandes_code (email, source, horodatage) VALUES (?, ?, ?)",
                    (email, source, maintenant()))
    return code


def _verifier_cadence(email: str, source: str = "") -> None:
    depuis_une_heure = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with curseur() as cur:
        cur.execute("DELETE FROM demandes_code WHERE horodatage < ?", (depuis_une_heure,))
        cur.execute("SELECT COUNT(*) AS n FROM demandes_code WHERE email = ?", (email,))
        if int(cur.fetchone()["n"]) >= config.MAX_CODES_PAR_HEURE:
            raise ErreurAuth(
                "Trop de codes demandés pour cette adresse. Réessaie dans une heure.",
                "cadence", 3600)
        # La limite par adresse protège une boîte mail ; elle ne protège de rien
        # contre quelqu'un qui arrose mille adresses différentes depuis la même
        # machine. Ce sont nos courriers qui partiraient, et notre expéditeur qui
        # finirait sur une liste noire.
        if source:
            cur.execute("SELECT COUNT(*) AS n FROM demandes_code WHERE source = ?", (source,))
            if int(cur.fetchone()["n"]) >= config.MAX_CODES_PAR_HEURE_ET_SOURCE:
                raise ErreurAuth(
                    "Trop de codes demandés depuis cet appareil. Réessaie dans une heure.",
                    "cadence", 3600)
        cur.execute("SELECT demande_le FROM codes WHERE email = ?", (email,))
        ligne = cur.fetchone()
    if ligne:
        ecoule = (datetime.now(timezone.utc)
                  - datetime.fromisoformat(ligne["demande_le"])).total_seconds()
        reste = int(config.DELAI_ENTRE_CODES_SECONDES - ecoule)
        if reste > 0:
            raise ErreurAuth(
                f"Un code vient de partir. Attends {reste} seconde"
                f"{'s' if reste > 1 else ''} avant d'en redemander un.",
                "cadence", reste)


def verifier_code(email: str, code: str) -> str:
    """Rend l'identifiant du compte, créé au passage si l'adresse est nouvelle.
    Le code est brûlé dans tous les cas : réussi, il a servi ; raté cinq fois,
    il ne doit plus servir."""
    propre = "".join(c for c in (code or "") if c.isdigit())
    with curseur() as cur:
        cur.execute("SELECT empreinte, expire_le, essais FROM codes WHERE email = ?", (email,))
        ligne = cur.fetchone()
        if ligne is None:
            raise ErreurAuth("Aucun code en attente pour cette adresse. Redemandes-en un.", "absent")
        if _expire(ligne["expire_le"]):
            cur.execute("DELETE FROM codes WHERE email = ?", (email,))
            raise ErreurAuth("Ce code a expiré. Redemandes-en un.", "expire")
        if ligne["essais"] >= config.MAX_ESSAIS_CODE:
            cur.execute("DELETE FROM codes WHERE email = ?", (email,))
            raise ErreurAuth("Trop d'essais. Redemande un code.", "essais")
        # compare_digest : le temps de comparaison ne doit rien dire du code.
        if not secrets.compare_digest(ligne["empreinte"], _empreinte(propre)):
            cur.execute("UPDATE codes SET essais = essais + 1 WHERE email = ?", (email,))
            reste = config.MAX_ESSAIS_CODE - int(ligne["essais"]) - 1
            raise ErreurAuth(
                "Ce code ne correspond pas." + (f" Encore {reste} essai{'s' if reste > 1 else ''}."
                                                if reste > 0 else " Redemande un code."),
                "faux")
        cur.execute("DELETE FROM codes WHERE email = ?", (email,))
        cur.execute("SELECT id FROM comptes WHERE email = ?", (email,))
        compte = cur.fetchone()
        if compte:
            cur.execute("UPDATE comptes SET vu_le = ? WHERE id = ?", (maintenant(), compte["id"]))
            return compte["id"]
        identifiant = secrets.token_urlsafe(9)
        cur.execute("INSERT INTO comptes (id, email, cree_le, vu_le) VALUES (?, ?, ?, ?)",
                    (identifiant, email, maintenant(), maintenant()))
    return identifiant


def ouvrir_jeton(compte_id: str) -> str:
    jeton = secrets.token_urlsafe(32)
    with curseur() as cur:
        cur.execute(
            "INSERT INTO jetons (empreinte, compte_id, cree_le, expire_le, vu_le)"
            " VALUES (?, ?, ?, ?, ?)",
            (_empreinte(jeton), compte_id, maintenant(),
             _plus_tard(jours=config.DUREE_JETON_JOURS), maintenant()),
        )
    return jeton


def compte_du_jeton(jeton: str | None) -> dict[str, str] | None:
    if not jeton:
        return None
    with curseur() as cur:
        cur.execute(
            "SELECT c.id, c.email, j.expire_le FROM jetons j JOIN comptes c ON c.id = j.compte_id"
            " WHERE j.empreinte = ?", (_empreinte(jeton),))
        ligne = cur.fetchone()
        if ligne is None:
            return None
        if _expire(ligne["expire_le"]):
            cur.execute("DELETE FROM jetons WHERE empreinte = ?", (_empreinte(jeton),))
            return None
        cur.execute("UPDATE jetons SET vu_le = ? WHERE empreinte = ?",
                    (maintenant(), _empreinte(jeton)))
    return {"id": ligne["id"], "email": ligne["email"]}


def fermer_jeton(jeton: str | None) -> None:
    if not jeton:
        return
    with curseur() as cur:
        cur.execute("DELETE FROM jetons WHERE empreinte = ?", (_empreinte(jeton),))


def purger_auth() -> int:
    """Codes expirés, jetons expirés, demandes trop vieilles. Rien de tout ça ne
    sert plus, et une adresse gardée sans raison est une adresse de trop."""
    maintenant_iso = maintenant()
    vieux = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with curseur() as cur:
        cur.execute("DELETE FROM codes WHERE expire_le < ?", (maintenant_iso,))
        efface = cur.rowcount
        cur.execute("DELETE FROM jetons WHERE expire_le < ?", (maintenant_iso,))
        efface += cur.rowcount
        cur.execute("DELETE FROM demandes_code WHERE horodatage < ?", (vieux,))
        efface += cur.rowcount
    return efface


def supprimer_compte(compte_id: str) -> None:
    """Le droit à l'effacement, en une fonction : l'adresse part, les séances
    aussi. Ce qui reste — usages et événements — ne porte aucun nom."""
    with curseur() as cur:
        cur.execute("SELECT id FROM sessions WHERE compte_id = ?", (compte_id,))
        seances = [ligne["id"] for ligne in cur.fetchall()]
        for seance in seances:
            cur.execute("DELETE FROM corriges WHERE session_id = ?", (seance,))
        cur.execute("DELETE FROM sessions WHERE compte_id = ?", (compte_id,))
        cur.execute("DELETE FROM jetons WHERE compte_id = ?", (compte_id,))
        cur.execute("SELECT email FROM comptes WHERE id = ?", (compte_id,))
        ligne = cur.fetchone()
        if ligne:
            cur.execute("DELETE FROM codes WHERE email = ?", (ligne["email"],))
            cur.execute("DELETE FROM demandes_code WHERE email = ?", (ligne["email"],))
        cur.execute("DELETE FROM comptes WHERE id = ?", (compte_id,))


# --- Quotas ----------------------------------------------------------------

class QuotaDepasse(Exception):
    def __init__(self, action: str, portee: str, message: str):
        super().__init__(message)
        self.action = action
        self.portee = portee
        self.message = message


def _compte(session_id: str, action: str, jour: str | None) -> int:
    with curseur() as cur:
        if jour:
            cur.execute(
                "SELECT COUNT(*) AS n FROM usages WHERE session_id = ? AND action = ? AND jour = ?",
                (session_id, action, jour),
            )
        else:
            cur.execute(
                "SELECT COUNT(*) AS n FROM usages WHERE session_id = ? AND action = ?",
                (session_id, action),
            )
        return int(cur.fetchone()["n"])


def etat_quota(session_id: str, action: str) -> dict[str, int]:
    limites = config.QUOTAS.get(action)
    if not limites:
        return {"restant_jour": 9999, "restant_session": 9999}
    return {
        "restant_jour": max(0, limites["jour"] - _compte(session_id, action, aujourdhui())),
        "restant_session": max(0, limites["session"] - _compte(session_id, action, None)),
    }


MESSAGES_QUOTA = {
    ("controle", "jour"): (
        "Tu as déjà passé tes contrôles blancs du jour. Reviens demain : "
        "réviser deux jours de suite marche bien mieux qu'un gros bloc d'un coup."
    ),
    ("controle", "session"): (
        "Tu as atteint le nombre de contrôles blancs prévus pour ce cours."
    ),
    ("analyse", "jour"): (
        "Tu as déjà analysé plusieurs séries de photos aujourd'hui. Reviens demain "
        "pour en ajouter d'autres."
    ),
    ("fiche_generale", "jour"): "Tu as déjà généré tes fiches générales du jour. Reviens demain.",
    ("fiche_ciblee", "jour"): "Tu as déjà généré tes fiches ciblées du jour. Reviens demain.",
}


def verifier_quota(session_id: str, action: str) -> None:
    limites = config.QUOTAS.get(action)
    if not limites:
        return
    if _compte(session_id, action, None) >= limites["session"]:
        raise QuotaDepasse(
            action, "session",
            MESSAGES_QUOTA.get((action, "session"), "Limite atteinte pour ce cours."),
        )
    if _compte(session_id, action, aujourdhui()) >= limites["jour"]:
        raise QuotaDepasse(
            action, "jour",
            MESSAGES_QUOTA.get((action, "jour"), "Limite atteinte pour aujourd'hui. Reviens demain."),
        )


def enregistrer_usage(session_id: str, action: str, usage: dict[str, int] | None = None) -> None:
    usage = usage or {}
    with curseur() as cur:
        cur.execute(
            "INSERT INTO usages (session_id, action, jour, horodatage, tokens_entree,"
            " tokens_sortie, cache_ecriture, cache_lecture) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id, action, aujourdhui(), maintenant(),
                usage.get("tokens_entree", 0), usage.get("tokens_sortie", 0),
                usage.get("cache_ecriture", 0), usage.get("cache_lecture", 0),
            ),
        )


# --- Événements (métriques) -------------------------------------------------

TYPES_EVENEMENTS = {
    "ouverture",            # le lien a été ouvert
    "photos_analysees",
    "perimetre_confirme",
    "chemin_choisi",        # details: {"chemin": "revise" | "teste"}
    "fiche_generee",        # details: {"type": "generale" | "ciblee", "rang": n}
    "controle_commence",    # details: {"rang": n}
    "controle_termine",
    "question_signalee",
    "correction_vue",
}


MAX_OCTETS_DETAILS = 2000


def enregistrer_evenement(session_id: str, type_: str, details: dict[str, Any] | None = None) -> None:
    if type_ not in TYPES_EVENEMENTS:
        return
    # Les détails viennent du navigateur : on les borne pour qu'une session ne
    # puisse pas gonfler la base.
    encode = json.dumps(details or {}, ensure_ascii=False)
    if len(encode.encode("utf-8")) > MAX_OCTETS_DETAILS:
        details = {"tronque": True}
    with curseur() as cur:
        cur.execute(
            "INSERT INTO evenements (session_id, type, details, jour, horodatage)"
            " VALUES (?, ?, ?, ?, ?)",
            (session_id, type_, json.dumps(details or {}, ensure_ascii=False),
             aujourdhui(), maintenant()),
        )


# --- Corrigés (réponses attendues, jamais envoyées au navigateur avant) ------

def enregistrer_corrige(controle_id: str, session_id: str, contenu: dict[str, Any]) -> None:
    with curseur() as cur:
        cur.execute(
            "INSERT OR REPLACE INTO corriges (controle_id, session_id, contenu, cree_le)"
            " VALUES (?, ?, ?, ?)",
            (controle_id, session_id, json.dumps(contenu, ensure_ascii=False), maintenant()),
        )


def lire_corrige(controle_id: str, session_id: str) -> dict[str, Any] | None:
    with curseur() as cur:
        cur.execute(
            "SELECT contenu FROM corriges WHERE controle_id = ? AND session_id = ?",
            (controle_id, session_id),
        )
        ligne = cur.fetchone()
    return json.loads(ligne["contenu"]) if ligne else None


def purger_corriges_anciens() -> int:
    limite = (datetime.now(timezone.utc) - timedelta(days=config.RETENTION_CORRIGES_JOURS)).isoformat()
    with curseur() as cur:
        cur.execute("DELETE FROM corriges WHERE cree_le < ?", (limite,))
        return cur.rowcount


# --- Métriques --------------------------------------------------------------

def metriques() -> dict[str, Any]:
    """Les trois chiffres qui décident de la suite, plus la comparaison des deux chemins."""
    with curseur() as cur:
        cur.execute("SELECT COUNT(DISTINCT session_id) AS n FROM evenements WHERE type = 'ouverture'")
        ouvertures = int(cur.fetchone()["n"])

        # Métrique 2 : une 2e fiche générée sans qu'on le demande.
        cur.execute(
            "SELECT COUNT(*) AS n FROM (SELECT session_id FROM evenements"
            " WHERE type = 'fiche_generee' GROUP BY session_id HAVING COUNT(*) >= 2)"
        )
        deux_fiches = int(cur.fetchone()["n"])

        # Métrique 3 : revenus un autre jour que le premier. La seule qui compte.
        cur.execute(
            "SELECT COUNT(*) AS n FROM (SELECT session_id FROM evenements"
            " GROUP BY session_id HAVING COUNT(DISTINCT jour) >= 2)"
        )
        revenus = int(cur.fetchone()["n"])

        # Revenus dès le lendemain précisément.
        cur.execute(
            "SELECT session_id, MIN(jour) AS premier FROM evenements GROUP BY session_id"
        )
        premiers = {r["session_id"]: r["premier"] for r in cur.fetchall()}
        cur.execute("SELECT DISTINCT session_id, jour FROM evenements")
        jours_par_session: dict[str, set[str]] = {}
        for ligne in cur.fetchall():
            jours_par_session.setdefault(ligne["session_id"], set()).add(ligne["jour"])

        revenus_j1 = 0
        for sid, premier in premiers.items():
            lendemain = (date.fromisoformat(premier) + timedelta(days=1)).isoformat()
            if lendemain in jours_par_session.get(sid, set()):
                revenus_j1 += 1

        # Répartition des deux chemins de l'étape 3, et retour le lendemain par chemin.
        cur.execute(
            "SELECT session_id, details FROM evenements WHERE type = 'chemin_choisi'"
            " GROUP BY session_id"
        )
        chemins: dict[str, str] = {}
        for ligne in cur.fetchall():
            try:
                chemins[ligne["session_id"]] = json.loads(ligne["details"]).get("chemin", "?")
            except (TypeError, ValueError):
                continue

        par_chemin: dict[str, dict[str, int]] = {}
        for sid, chemin in chemins.items():
            bloc = par_chemin.setdefault(chemin, {"sessions": 0, "revenus": 0})
            bloc["sessions"] += 1
            if len(jours_par_session.get(sid, set())) >= 2:
                bloc["revenus"] += 1

        cur.execute("SELECT COUNT(*) AS n FROM evenements WHERE type = 'controle_termine'")
        controles_termines = int(cur.fetchone()["n"])
        cur.execute("SELECT COUNT(*) AS n FROM evenements WHERE type = 'question_signalee'")
        questions_signalees = int(cur.fetchone()["n"])

        cur.execute(
            "SELECT action, COUNT(*) AS n, SUM(tokens_entree) AS e, SUM(tokens_sortie) AS s,"
            " SUM(cache_ecriture) AS ce, SUM(cache_lecture) AS cl FROM usages GROUP BY action"
        )
        cout_total = 0.0
        detail_cout = []
        for ligne in cur.fetchall():
            p = config.PRIX_USD_PAR_MTOK
            cout = (
                (ligne["e"] or 0) * p["entree"]
                + (ligne["s"] or 0) * p["sortie"]
                + (ligne["ce"] or 0) * p["cache_ecriture"]
                + (ligne["cl"] or 0) * p["cache_lecture"]
            ) / 1_000_000
            cout_total += cout
            detail_cout.append({"action": ligne["action"], "appels": ligne["n"], "cout_usd": round(cout, 4)})

        cur.execute("SELECT COUNT(*) AS n FROM sessions")
        sessions_creees = int(cur.fetchone()["n"])

    return {
        "sessions_creees": sessions_creees,
        "ouvertures": ouvertures,
        "deux_fiches_ou_plus": deux_fiches,
        "revenus_un_autre_jour": revenus,
        "revenus_le_lendemain": revenus_j1,
        "controles_termines": controles_termines,
        "questions_signalees": questions_signalees,
        "par_chemin": par_chemin,
        "cout_usd_total": round(cout_total, 4),
        "cout_usd_par_session": round(cout_total / sessions_creees, 4) if sessions_creees else 0.0,
        "detail_cout": detail_cout,
    }


def questions_signalees_detail(limite: int = 50) -> list[dict[str, Any]]:
    with curseur() as cur:
        cur.execute(
            "SELECT details, horodatage FROM evenements WHERE type = 'question_signalee'"
            " ORDER BY id DESC LIMIT ?",
            (limite,),
        )
        sorties = []
        for ligne in cur.fetchall():
            try:
                details = json.loads(ligne["details"])
            except (TypeError, ValueError):
                details = {}
            sorties.append({**details, "horodatage": ligne["horodatage"]})
    return sorties
