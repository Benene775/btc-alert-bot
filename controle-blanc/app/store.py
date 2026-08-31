"""Stockage serveur, réduit au strict nécessaire.

Ce qu'on garde ici, et pourquoi :
  - un identifiant de session aléatoire, sans aucune donnée personnelle ;
  - les compteurs d'usage (les quotas doivent être infalsifiables, donc côté serveur) ;
  - le corrigé d'un contrôle en cours (sinon le navigateur reçoit les réponses
    attendues avant que l'élève ait répondu) ;
  - des événements anonymes pour les trois métriques du test.

  - depuis les comptes : l'adresse, le prénom et la classe de l'élève, plus son
    mot de passe haché par scrypt. Le code de réinitialisation et le jeton de
    connexion sont hachés eux aussi. Rien n'est gardé en clair.

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
    cache_lecture  INTEGER DEFAULT 0,
    modele         TEXT NOT NULL DEFAULT ''
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
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    mot_de_passe  TEXT NOT NULL DEFAULT '',
    prenom        TEXT NOT NULL DEFAULT '',
    niveau        TEXT NOT NULL DEFAULT '',
    cree_le       TEXT NOT NULL,
    vu_le         TEXT NOT NULL
);

-- Les essais de connexion ratés, pour bloquer celui qui essaie mille mots de
-- passe. Purgée avec l'âge, comme demandes_code.
CREATE TABLE IF NOT EXISTS tentatives (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT '',
    horodatage TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tentatives_email ON tentatives (email, horodatage);
CREATE INDEX IF NOT EXISTS idx_tentatives_source ON tentatives (source, horodatage);

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


def mois_courant() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # Les séances d'avant les comptes n'ont pas de colonne compte_id.
    # SQLite n'a pas d'« ADD COLUMN IF NOT EXISTS » : on regarde d'abord.
    colonnes = {ligne[1] for ligne in conn.execute("PRAGMA table_info(sessions)")}
    if "compte_id" not in colonnes:
        conn.execute("ALTER TABLE sessions ADD COLUMN compte_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_compte ON sessions (compte_id)")
    # Les usages d'avant la comparaison de modèles ne disent pas lequel a servi.
    usages = {ligne[1] for ligne in conn.execute("PRAGMA table_info(usages)")}
    if usages and "modele" not in usages:
        conn.execute("ALTER TABLE usages ADD COLUMN modele TEXT NOT NULL DEFAULT ''")
    demandes = {ligne[1] for ligne in conn.execute("PRAGMA table_info(demandes_code)")}
    if demandes and "source" not in demandes:
        conn.execute("ALTER TABLE demandes_code ADD COLUMN source TEXT NOT NULL DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_demandes_source ON demandes_code (source, horodatage)")
    # Les comptes ouverts avant le mot de passe n'en ont pas. Ils gardent une
    # empreinte vide : impossible à deviner (aucun mot de passe ne s'y compare),
    # et « mot de passe oublié » leur en donne un.
    comptes = {ligne[1] for ligne in conn.execute("PRAGMA table_info(comptes)")}
    for colonne in ("mot_de_passe", "prenom", "niveau"):
        if comptes and colonne not in comptes:
            conn.execute(f"ALTER TABLE comptes ADD COLUMN {colonne} TEXT NOT NULL DEFAULT ''")
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
    pas ouvrir son cours. Les séances d'avant les comptes n'ont pas de
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


# --- Comptes, mots de passe, jetons -----------------------------------------
#
# Quatre règles, et tout le reste en découle :
#
#   1. On ne stocke jamais un secret en clair. Le mot de passe passe par scrypt,
#      le code de réinitialisation et le jeton de connexion par SHA-256. Une base
#      volée n'ouvre ni un compte, ni une boîte mail.
#   2. On ne dit jamais si une adresse est connue. « Adresse ou mot de passe
#      incorrect » et « un code est parti » sont les seules réponses possibles ;
#      sinon le formulaire devient un annuaire d'élèves.
#   3. On borne tout : les essais de mot de passe, les codes envoyés, par adresse
#      et par machine. Sans ça, un mot de passe d'élève se devine en une nuit.
#   4. Une réponse ne doit pas se laisser chronométrer. Une adresse inconnue coûte
#      le même temps qu'une adresse connue — d'où le hachage à vide plus bas.
#
# Pourquoi scrypt : il est dans la bibliothèque standard (donc pas de dépendance
# à installer et à tenir à jour), et il est coûteux en mémoire, ce qui rend une
# carte graphique bien moins efficace pour l'attaquer qu'avec un simple SHA.

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


# --- Les mots de passe ------------------------------------------------------

# n = 2^14, r = 8, p = 1 : environ 16 Mo de mémoire et quelques dizaines de
# millisecondes par vérification. Assez cher pour l'attaquant, assez rapide pour
# ne pas faire attendre un élève sur un téléphone.
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MEM = 64 * 1024 * 1024

MIN_LONGUEUR_MDP = 8
# scrypt encaisserait n'importe quelle longueur, mais un mot de passe d'un mega-
# octet ne sert qu'à faire ramer le serveur.
MAX_LONGUEUR_MDP = 128

# Les mots de passe qu'un attaquant essaie en premier. Une liste courte : elle
# attrape ce qu'un élève tape par réflexe, pas ce qu'un dictionnaire contient.
TROP_COURANTS = {
    "12345678", "123456789", "1234567890", "motdepasse", "password", "azertyui",
    "qwertyui", "azerty123", "qwerty123", "password1", "motdepasse1", "11111111",
    "00000000", "abcd1234", "iloveyou", "princesse", "football", "doudou12",
}


def verifier_forme_mot_de_passe(clair: str, email: str = "", prenom: str = "") -> str:
    """Ce qu'on refuse, et rien de plus.

    Pas de « une majuscule, un chiffre, un caractère spécial » : ces règles
    poussent à « Motdepasse1! », que tout dictionnaire connaît, et à écrire le
    mot de passe sur un cahier. On exige de la longueur, et on refuse les
    évidences — dont son propre prénom et sa propre adresse.
    """
    if not clair or len(clair) < MIN_LONGUEUR_MDP:
        raise ErreurAuth(
            f"Ton mot de passe doit faire au moins {MIN_LONGUEUR_MDP} caractères.", "mdp")
    if len(clair) > MAX_LONGUEUR_MDP:
        raise ErreurAuth(f"{MAX_LONGUEUR_MDP} caractères au maximum.", "mdp")
    bas = clair.lower()
    if bas in TROP_COURANTS:
        raise ErreurAuth("Ce mot de passe est trop courant. Trouve autre chose.", "mdp")
    if prenom and len(prenom) >= 3 and prenom.lower() in bas:
        raise ErreurAuth("Évite ton prénom dans ton mot de passe.", "mdp")
    if email and email.split("@")[0].lower() in bas:
        raise ErreurAuth("Évite ton adresse mail dans ton mot de passe.", "mdp")
    return clair


def _hacher_mot_de_passe(clair: str) -> str:
    sel = secrets.token_bytes(16)
    brut = hashlib.scrypt(clair.encode("utf-8"), salt=sel, n=SCRYPT_N, r=SCRYPT_R,
                          p=SCRYPT_P, dklen=32, maxmem=SCRYPT_MEM)
    # Les paramètres voyagent avec l'empreinte : le jour où on les durcit, les
    # anciennes empreintes restent vérifiables.
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${sel.hex()}${brut.hex()}"


# Une empreinte qui ne correspond à rien, pour les adresses inconnues. Sans elle,
# une adresse inexistante répondrait en une microseconde et une adresse inscrite
# en cinquante millisecondes : le chronomètre suffirait à faire l'annuaire.
_EMPREINTE_LEURRE: str | None = None


def _leurre() -> str:
    global _EMPREINTE_LEURRE
    if _EMPREINTE_LEURRE is None:
        _EMPREINTE_LEURRE = _hacher_mot_de_passe(secrets.token_urlsafe(24))
    return _EMPREINTE_LEURRE


def _mot_de_passe_correspond(clair: str, empreinte: str) -> bool:
    if not empreinte:
        # Compte d'avant les mots de passe : rien ne peut s'y comparer. On brûle
        # quand même le temps du hachage pour ne rien laisser voir.
        hashlib.scrypt(clair.encode("utf-8"), salt=b"0" * 16, n=SCRYPT_N, r=SCRYPT_R,
                       p=SCRYPT_P, dklen=32, maxmem=SCRYPT_MEM)
        return False
    try:
        marque, n, r, pp, sel, attendu = empreinte.split("$")
        if marque != "scrypt":
            return False
        calcule = hashlib.scrypt(clair.encode("utf-8"), salt=bytes.fromhex(sel),
                                 n=int(n), r=int(r), p=int(pp), dklen=len(attendu) // 2,
                                 maxmem=SCRYPT_MEM)
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(calcule.hex(), attendu)



def _plus_tard(minutes: int = 0, jours: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes, days=jours)).isoformat(
        timespec="seconds")


def _expire(horodatage: str) -> bool:
    return datetime.fromisoformat(horodatage) < datetime.now(timezone.utc)


def preparer_code(email: str, source: str = "", garder: bool = True) -> str:
    """Fabrique le code, l'enregistre haché, et rend le clair — une seule fois,
    à l'appelant qui va l'envoyer par courrier. Il n'est plus lisible ensuite.

    `garder=False` pour une adresse sans compte : on décompte quand même la
    cadence — sinon le temps de réponse et le quota trahiraient les adresses
    inscrites — mais on n'écrit pas un code que personne ne pourra utiliser.
    """
    _verifier_cadence(email, source)
    # secrets, pas random : un code prévisible est un code déjà connu.
    code = f"{secrets.randbelow(1_000_000):06d}"
    with curseur() as cur:
        if garder:
            cur.execute(
                "INSERT OR REPLACE INTO codes (email, empreinte, expire_le, essais, demande_le)"
                " VALUES (?, ?, ?, 0, ?)",
                (email, _empreinte(code), _plus_tard(minutes=config.DUREE_CODE_MINUTES),
                 maintenant()),
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
        cur.execute("SELECT MAX(horodatage) AS dernier FROM demandes_code WHERE email = ?",
                    (email,))
        ligne = cur.fetchone()
    if ligne and ligne["dernier"]:
        ecoule = (datetime.now(timezone.utc)
                  - datetime.fromisoformat(ligne["dernier"])).total_seconds()
        reste = int(config.DELAI_ENTRE_CODES_SECONDES - ecoule)
        if reste > 0:
            raise ErreurAuth(
                f"Un code vient de partir. Attends {reste} seconde"
                f"{'s' if reste > 1 else ''} avant d'en redemander un.",
                "cadence", reste)


def verifier_code(email: str, code: str) -> None:
    """Vérifie le code de réinitialisation. Il est brûlé dans tous les cas :
    réussi, il a servi ; raté cinq fois, il ne doit plus servir."""
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


# --- Ouvrir un compte, s'y connecter ----------------------------------------

MAX_LONGUEUR_PRENOM = 40


def nettoyer_prenom(brut: str) -> str:
    """On garde ce que l'élève écrit, borné. Le prénom sert à personnaliser sa
    page ; il n'a pas à être validé comme un état civil."""
    prenom = " ".join((brut or "").split())[:MAX_LONGUEUR_PRENOM]
    return prenom


def inscrire(email: str, mot_de_passe: str, prenom: str = "", niveau: str = "") -> str:
    """Ouvre un compte. Rend son identifiant.

    Une adresse déjà inscrite est refusée — et c'est le seul endroit du produit
    qui révèle qu'une adresse existe. On ne peut pas y couper : accepter en
    silence donnerait un deuxième compte fantôme à qui se réinscrit par erreur,
    et son travail resterait dans l'autre.
    """
    verifier_forme_mot_de_passe(mot_de_passe, email, prenom)
    with curseur() as cur:
        cur.execute("SELECT 1 FROM comptes WHERE email = ?", (email,))
        if cur.fetchone():
            raise ErreurAuth(
                "Un compte existe déjà avec cette adresse. Connecte-toi, ou utilise "
                "« mot de passe oublié ».", "existe")
        identifiant = secrets.token_urlsafe(9)
        cur.execute(
            "INSERT INTO comptes (id, email, mot_de_passe, prenom, niveau, cree_le, vu_le)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (identifiant, email, _hacher_mot_de_passe(mot_de_passe),
             nettoyer_prenom(prenom), (niveau or "").strip()[:16],
             maintenant(), maintenant()),
        )
    return identifiant


def connecter(email: str, mot_de_passe: str, source: str = "") -> str:
    """Rend l'identifiant du compte, ou lève. Le message de refus est le même
    pour une adresse inconnue et un mot de passe faux : deux messages
    différents, et le formulaire dit qui est inscrit."""
    _verifier_tentatives(email, source)
    with curseur() as cur:
        cur.execute("SELECT id, mot_de_passe FROM comptes WHERE email = ?", (email,))
        ligne = cur.fetchone()

    # Adresse inconnue : on hache quand même, pour que la réponse mette le même
    # temps que pour une adresse inscrite.
    empreinte = ligne["mot_de_passe"] if ligne else _leurre()
    bon = _mot_de_passe_correspond(mot_de_passe or "", empreinte)

    if not ligne or not bon:
        with curseur() as cur:
            cur.execute("INSERT INTO tentatives (email, source, horodatage) VALUES (?, ?, ?)",
                        (email, source, maintenant()))
        raise ErreurAuth("Adresse ou mot de passe incorrect.", "refus")

    with curseur() as cur:
        cur.execute("DELETE FROM tentatives WHERE email = ?", (email,))
        cur.execute("UPDATE comptes SET vu_le = ? WHERE id = ?", (maintenant(), ligne["id"]))
    return ligne["id"]


def _verifier_tentatives(email: str, source: str = "") -> None:
    """Dix essais ratés par quart d'heure, par adresse et par machine. Un élève
    qui cherche son mot de passe en fait trois ; un programme en fait mille."""
    depuis = (datetime.now(timezone.utc)
              - timedelta(minutes=config.FENETRE_TENTATIVES_MINUTES)).isoformat()
    with curseur() as cur:
        cur.execute("DELETE FROM tentatives WHERE horodatage < ?", (depuis,))
        cur.execute("SELECT COUNT(*) AS n FROM tentatives WHERE email = ?", (email,))
        par_adresse = int(cur.fetchone()["n"])
        par_machine = 0
        if source:
            cur.execute("SELECT COUNT(*) AS n FROM tentatives WHERE source = ?", (source,))
            par_machine = int(cur.fetchone()["n"])
    if max(par_adresse, par_machine) >= config.MAX_TENTATIVES:
        raise ErreurAuth(
            f"Trop d'essais. Attends {config.FENETRE_TENTATIVES_MINUTES} minutes, ou "
            "utilise « mot de passe oublié ».",
            "cadence", config.FENETRE_TENTATIVES_MINUTES * 60)


def changer_mot_de_passe(email: str, nouveau: str) -> str:
    """Après un code vérifié. Rend l'identifiant du compte.

    Toutes les autres connexions sont fermées : si quelqu'un avait pris le
    compte, c'est ici qu'il en sort.
    """
    with curseur() as cur:
        cur.execute("SELECT id, prenom FROM comptes WHERE email = ?", (email,))
        ligne = cur.fetchone()
    if ligne is None:
        raise ErreurAuth("Aucun compte avec cette adresse.", "absent")
    verifier_forme_mot_de_passe(nouveau, email, ligne["prenom"])
    with curseur() as cur:
        cur.execute("UPDATE comptes SET mot_de_passe = ?, vu_le = ? WHERE id = ?",
                    (_hacher_mot_de_passe(nouveau), maintenant(), ligne["id"]))
        cur.execute("DELETE FROM jetons WHERE compte_id = ?", (ligne["id"],))
        cur.execute("DELETE FROM tentatives WHERE email = ?", (email,))
    return ligne["id"]


def compte_existe(email: str) -> bool:
    """Sert au serveur pour ne pas fabriquer de code pour une adresse inconnue.
    La réponse HTTP, elle, reste la même dans les deux cas."""
    with curseur() as cur:
        cur.execute("SELECT 1 FROM comptes WHERE email = ?", (email,))
        return cur.fetchone() is not None


def profil(compte_id: str) -> dict[str, str] | None:
    with curseur() as cur:
        cur.execute("SELECT id, email, prenom, niveau FROM comptes WHERE id = ?", (compte_id,))
        ligne = cur.fetchone()
    return dict(ligne) if ligne else None


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
            "SELECT c.id, c.email, c.prenom, c.niveau, j.expire_le FROM jetons j"
            " JOIN comptes c ON c.id = j.compte_id WHERE j.empreinte = ?", (_empreinte(jeton),))
        ligne = cur.fetchone()
        if ligne is None:
            return None
        if _expire(ligne["expire_le"]):
            cur.execute("DELETE FROM jetons WHERE empreinte = ?", (_empreinte(jeton),))
            return None
        cur.execute("UPDATE jetons SET vu_le = ? WHERE empreinte = ?",
                    (maintenant(), _empreinte(jeton)))
    return {"id": ligne["id"], "email": ligne["email"],
            "prenom": ligne["prenom"], "niveau": ligne["niveau"]}


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
        cur.execute("DELETE FROM tentatives WHERE horodatage < ?", (vieux,))
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
            cur.execute("DELETE FROM tentatives WHERE email = ?", (ligne["email"],))
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


def _usages_du_mois(compte_id: str, action: str, mois: str) -> int:
    """Les usages de tout le compte sur le mois, séances confondues.

    C'est là toute la différence avec _compte() : le passage par
    sessions.compte_id fait qu'ouvrir une nouvelle séance ne remet rien à zéro.
    Toute séance appartient à un compte (creer_session en exige un), il n'y a
    donc pas de porte de côté.
    """
    with curseur() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM usages u JOIN sessions s ON s.id = u.session_id"
            " WHERE s.compte_id = ? AND u.action = ? AND substr(u.jour, 1, 7) = ?",
            (compte_id, action, mois),
        )
        return int(cur.fetchone()["n"])


def _compte_du_mois(session_id: str, action: str, mois: str) -> int:
    with curseur() as cur:
        cur.execute("SELECT compte_id FROM sessions WHERE id = ?", (session_id,))
        ligne = cur.fetchone()
    compte_id = ligne["compte_id"] if ligne else None
    if compte_id:
        return _usages_du_mois(compte_id, action, mois)
    # Une séance d'avant les comptes : faute de compte à qui la rattacher, on la
    # plafonne sur elle-même. Personne n'en ouvre plus de pareilles.
    with curseur() as cur:
        cur.execute(
            "SELECT COUNT(*) AS n FROM usages WHERE session_id = ? AND action = ?"
            " AND substr(jour, 1, 7) = ?",
            (session_id, action, mois),
        )
        return int(cur.fetchone()["n"])


def quotas_du_compte(compte_id: str) -> dict[str, dict[str, int]]:
    """Ce qu'il reste à ce compte ce mois-ci, action par action.

    Sert à l'afficher sur la page perso : mieux vaut voir venir la limite que
    la découvrir au moment de lancer un contrôle.
    """
    mois = mois_courant()
    return {
        action: {
            "plafond": plafond,
            "restant": max(0, plafond - _usages_du_mois(compte_id, action, mois)),
        }
        for action, plafond in config.QUOTAS_MOIS.items()
    }


def etat_quota(session_id: str, action: str) -> dict[str, int]:
    limites = config.QUOTAS.get(action)
    plafond_mois = config.QUOTAS_MOIS.get(action)
    if not limites:
        return {"restant_jour": 9999, "restant_session": 9999, "restant_mois": 9999}
    return {
        "restant_jour": max(0, limites["jour"] - _compte(session_id, action, aujourdhui())),
        "restant_session": max(0, limites["session"] - _compte(session_id, action, None)),
        "restant_mois": (
            max(0, plafond_mois - _compte_du_mois(session_id, action, mois_courant()))
            if plafond_mois else 9999
        ),
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
    # Le mois, lui, ne se rattrape pas demain : le message doit le dire, et
    # rappeler que ce qui est déjà fait reste sur la page perso.
    ("analyse", "mois"): (
        "Tu as photographié tous les cours prévus ce mois-ci. Ton compteur repart le 1er ; "
        "les cours déjà rentrés restent là."
    ),
    ("fiche_generale", "mois"): (
        "Tu as fait toutes tes fiches du mois. Celles que tu as déjà sont toujours sur ta page ; "
        "le compteur repart le 1er."
    ),
    ("controle", "mois"): (
        "Tu as passé tous tes contrôles blancs du mois. Tes corrections restent consultables ; "
        "le compteur repart le 1er."
    ),
    ("fiche_ciblee", "mois"): (
        "Tu as fait toutes tes fiches ciblées du mois. Le compteur repart le 1er."
    ),
}


def verifier_quota(session_id: str, action: str) -> None:
    # Le mois passe en premier : c'est le plafond de l'abonnement, et lui seul
    # ne se rattrape pas. Annoncer « reviens demain » alors que le mois est
    # épuisé enverrait l'élève se cogner à la même porte le lendemain.
    plafond_mois = config.QUOTAS_MOIS.get(action)
    if plafond_mois and _compte_du_mois(session_id, action, mois_courant()) >= plafond_mois:
        raise QuotaDepasse(
            action, "mois",
            MESSAGES_QUOTA.get((action, "mois"), "Tu as atteint ta limite du mois."),
        )
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


def enregistrer_usage(session_id: str, action: str, usage: dict[str, Any] | None = None) -> None:
    usage = usage or {}
    with curseur() as cur:
        cur.execute(
            "INSERT INTO usages (session_id, action, jour, horodatage, tokens_entree,"
            " tokens_sortie, cache_ecriture, cache_lecture, modele)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id, action, aujourdhui(), maintenant(),
                usage.get("tokens_entree", 0), usage.get("tokens_sortie", 0),
                usage.get("cache_ecriture", 0), usage.get("cache_lecture", 0),
                usage.get("modele", ""),
            ),
        )


# --- Événements (métriques) -------------------------------------------------

TYPES_EVENEMENTS = {
    "ouverture",            # le lien a été ouvert
    "espace",               # la page perso a été ouverte
    "photos_analysees",
    "perimetre_confirme",
    "chemin_choisi",        # details: {"chemin": "revise" | "teste"}
    "fiche_generee",        # details: {"type": "generale" | "ciblee", "rang": n}
    "controle_commence",    # details: {"rang": n}
    "controle_termine",
    "question_signalee",
    "transcription_signalee",  # details: {"chapitre": "..."} — le cours a été mal lu
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

        # Le coût, par action ET par modèle. Sans le modèle, un essai Sonnet
        # serait chiffré au tarif Opus et le banc d'essai ne prouverait rien.
        cur.execute(
            "SELECT action, modele, COUNT(*) AS n, SUM(tokens_entree) AS e,"
            " SUM(tokens_sortie) AS s, SUM(cache_ecriture) AS ce, SUM(cache_lecture) AS cl"
            " FROM usages GROUP BY action, modele"
        )
        cout_total = 0.0
        detail_cout = []
        tarifs_inconnus: set[str] = set()
        for ligne in cur.fetchall():
            cout = _cout_usd(ligne, tarifs_inconnus)
            cout_total += cout
            detail_cout.append({
                "action": ligne["action"],
                "modele": ligne["modele"] or "—",
                "appels": ligne["n"],
                "cout_usd": round(cout, 4),
            })
        detail_cout.sort(key=lambda d: -d["cout_usd"])

        # Le chiffre qui décide du prix de l'abonnement : ce que coûte un compte
        # sur un mois. Pas le pire cas — la moyenne, et le maximum à côté pour
        # savoir si les plafonds tiennent.
        cur.execute(
            "SELECT s.compte_id AS compte, substr(u.jour, 1, 7) AS mois, u.modele AS modele,"
            " COUNT(*) AS n, SUM(u.tokens_entree) AS e, SUM(u.tokens_sortie) AS s,"
            " SUM(u.cache_ecriture) AS ce, SUM(u.cache_lecture) AS cl"
            " FROM usages u JOIN sessions s ON s.id = u.session_id"
            " WHERE s.compte_id IS NOT NULL GROUP BY s.compte_id, mois, u.modele"
        )
        par_compte_mois: dict[tuple[str, str], float] = {}
        for ligne in cur.fetchall():
            cle = (ligne["compte"], ligne["mois"])
            par_compte_mois[cle] = par_compte_mois.get(cle, 0.0) + _cout_usd(ligne, tarifs_inconnus)
        couts_mensuels = sorted(par_compte_mois.values())

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
        "comptes_mois_mesures": len(couts_mensuels),
        "cout_usd_moyen_compte_mois": (
            round(sum(couts_mensuels) / len(couts_mensuels), 4) if couts_mensuels else 0.0
        ),
        "cout_usd_median_compte_mois": (
            round(couts_mensuels[len(couts_mensuels) // 2], 4) if couts_mensuels else 0.0
        ),
        "cout_usd_max_compte_mois": round(couts_mensuels[-1], 4) if couts_mensuels else 0.0,
        # Un tarif manquant fausse tout le tableau en silence : on le nomme.
        "tarifs_inconnus": sorted(tarifs_inconnus),
    }


def _cout_usd(ligne: Any, inconnus: set[str] | None = None) -> float:
    """Le coût d'un paquet d'appels, au tarif du modèle qui les a servis."""
    prix, connu = config.prix_du_modele(ligne["modele"] or "")
    if not connu and inconnus is not None and (ligne["e"] or ligne["s"]):
        inconnus.add(ligne["modele"] or "(non enregistré)")
    return (
        (ligne["e"] or 0) * prix["entree"]
        + (ligne["s"] or 0) * prix["sortie"]
        + (ligne["ce"] or 0) * prix["cache_ecriture"]
        + (ligne["cl"] or 0) * prix["cache_lecture"]
    ) / 1_000_000


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
