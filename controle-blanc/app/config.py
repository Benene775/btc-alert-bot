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


# --- Les modèles -----------------------------------------------------------
#
# Deux modèles, parce que les cinq appels n'ont pas le même risque.
#
# Un seul regarde des PHOTOS d'écriture manuscrite : l'analyse. Et tout le reste
# est bâti sur ce qu'il en tire — la fiche, le contrôle et la correction lisent
# la transcription, jamais les images. Une ligne mal lue ne reste donc pas
# locale : elle se propage, avec assurance, jusque dans la copie corrigée. Un
# modèle qui dit « je n'arrive pas à lire » est rattrapable ; un modèle qui lit
# de travers ne le signale pas — c'est pour ça que l'écran de périmètre montre
# la transcription et laisse dire « ce n'est pas ce que dit mon cours »
# (événement « transcription_signalee »). C'est le seul contrôle qui existe sur
# cette étape, et le signal qui dira si le modèle choisi lit assez bien.
#
# PENDANT LA PHASE DE TEST, c'est quand même le modèle le moins cher qui lit les
# photos. C'est un choix, pas un oubli : les testeurs sont des élèves qu'on
# connaît, à qui on ne facture rien et qu'on a prévenus qu'il y aurait des
# ratés. Faire tourner l'essai sur le modèle cher n'apprendrait justement rien
# sur ce qu'on peut se permettre ensuite.
#
# LE JOUR OÙ C'EST PAYANT, cette ligne redevient une décision : soit
# CB_MODEL=claude-opus-5 pour remettre la lecture des photos en gamme haute
# (elle seule, les quatre autres appels restant au tarif bas), soit une mesure
# qui montre que ce n'est pas la peine — voir « Chiffrer le coût » dans le README.
MODEL = os.environ.get("CB_MODEL", "claude-sonnet-5").strip() or "claude-sonnet-5"

# Les quatre autres appels ne voient jamais les photos : ils raisonnent sur du
# texte déjà transcrit, et leurs erreurs sont visibles par l'élève — qui a un
# bouton « signaler ». C'est là que l'économie se prend sans jouer le produit,
# et c'est le réglage qui restera bas même une fois le produit payant.
MODELE_TEXTE = os.environ.get("CB_MODEL_TEXTE", "claude-sonnet-5").strip() or "claude-sonnet-5"


def modele_pour(action: str) -> str:
    """Le modèle d'un appel. Découper là ne coûte aucune lecture de cache : le
    bloc de cours mis en cache ne sert qu'aux appels « texte », puisque l'analyse
    tourne avant que le cours existe."""
    return MODEL if action == "analyse" else MODELE_TEXTE

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
# L'analyse se compte en PAGES, pas en appels : c'est la seule unité qui suive
# la dépense. Une page photographiée vaut ~2 350 tokens d'entrée (réduite à
# 1568 px par le navigateur, découpée en carreaux de 28×28 px), et les photos
# font 55 à 79 % du coût d'un parcours. Compter les appels revenait à facturer
# pareil quatre pages et cinquante. C'est aussi l'unité que l'élève comprend.
QUOTAS: dict[str, dict[str, int]] = {
    "analyse": {"jour": _int("CB_QUOTA_ANALYSE_JOUR", 48), "session": _int("CB_QUOTA_ANALYSE_SESSION", 96)},
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
# l'API. Au plafond des quatre compteurs, contre ~6,20 € encaissés :
#
#   Sonnet 5 (le réglage par défaut)  1,28 € à 2,09 €   soit 21 à 34 % du net
#   Opus (CB_MODEL=claude-opus-5)     3,21 € à 5,24 €   soit 52 à 85 % du net
#
# La fourchette va de l'écriture aérée (500 caractères la page) à l'écriture
# dense (2 000). Un élève ordinaire — quatre parcours de six pages dans le mois
# — coûte ~0,27 €, soit 4 % du net.
#
# Ce que ce tableau dit : à 12 par mois, le pire cas tient largement sur Sonnet
# et ne tient plus vraiment sur Opus. Remonter le modèle et remonter les quotas
# sont deux décisions qui ne se prennent pas séparément.
#
# À refaire avec les vrais chiffres dès qu'une clé API existe.
QUOTAS_MOIS: dict[str, int] = {
    "analyse": _int("CB_QUOTA_ANALYSE_MOIS", 144),  # en pages : 12 analyses pleines
    "fiche_generale": _int("CB_QUOTA_FICHE_MOIS", 12),
    "controle": _int("CB_QUOTA_CONTROLE_MOIS", 12),
    "fiche_ciblee": _int("CB_QUOTA_CIBLEE_MOIS", 12),
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
#
# La clé doit être assez précise pour ne pas attraper un voisin moins cher ou
# plus cher : « sonnet » tout court ramasserait Sonnet 4.6, qui n'est pas au
# tarif de Sonnet 5. Un modèle absent d'ici n'est pas deviné — il est signalé.
# L'écriture de cache vaut 1,25 fois l'entrée, la lecture 0,1 fois.
PRIX_USD_PAR_MTOK_PAR_MODELE: dict[str, dict[str, float]] = {
    # Opus 5, 4.8, 4.7 et 4.6 partagent le même tarif.
    # L'écriture de cache vaut 2x l'entrée, pas 1,25x : c'est le tarif du TTL
    # d'une heure, que llm.py demande explicitement. Le 1,25x est celui du TTL
    # de cinq minutes. Se tromper de ligne sous-estime chaque mise en cache de
    # 60 %, sans que rien ne le signale — le tableau de bord affichait alors un
    # coût plus bas que la facture.
    "opus": {"entree": 5.0, "sortie": 25.0, "cache_ecriture": 10.0, "cache_lecture": 0.50},
    "sonnet-5": {"entree": 2.0, "sortie": 10.0, "cache_ecriture": 4.0, "cache_lecture": 0.20},
}

# Utilisé quand le nom du modèle n'est pas reconnu. Le tableau de bord le
# signale au lieu d'afficher un chiffre faux sans le dire.
PRIX_USD_PAR_MTOK = PRIX_USD_PAR_MTOK_PAR_MODELE["opus"]


def prix_du_modele(modele: str) -> tuple[dict[str, float], bool]:
    """Les tarifs pour ce modèle, et si on les connaît vraiment."""
    nom = (modele or "").lower()
    # La clé la plus longue gagne : « sonnet-5 » doit passer avant un éventuel
    # « sonnet » générique, sinon la plus vague raflerait la mise.
    for cle in sorted(PRIX_USD_PAR_MTOK_PAR_MODELE, key=len, reverse=True):
        if cle in nom:
            return PRIX_USD_PAR_MTOK_PAR_MODELE[cle], True
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


# --- Le garde-fou du démarrage ----------------------------------------------
#
# Deux réglages sont sans danger en local et catastrophiques en ligne. Le
# problème est qu'ils ne font pas de bruit : le site démarre, il répond, il a
# l'air d'aller bien.
#
# Le mode démonstration en est un. Il s'active TOUT SEUL quand ANTHROPIC_API_KEY
# manque — une variable oubliée au déploiement suffit. Un élève photographie son
# cours de maths et reçoit une fiche sur la Première Guerre mondiale ; la seule
# mention à l'écran est sur l'accueil, or un élève connecté arrive sur sa page et
# ne la voit jamais. Pendant une phase de test dont on mesure la qualité, ça
# empoisonne toutes les données sans qu'on l'apprenne avant la fin.
#
# On préfère un démarrage qui échoue bruyamment. Se déployer est un geste
# délibéré ; servir de la fiction à des élèves ne doit jamais l'être par défaut.
#
# CB_DEMO_ASSUMEE=1 lève les deux garde-fous d'un coup, et c'est voulu : ils
# décrivent la même situation — une démonstration mise en ligne exprès, où les
# contenus sont factices ET les portes ouvertes. Les séparer laisserait croire
# qu'on peut assumer l'un sans l'autre.
DEMO_ASSUMEE = _flag("CB_DEMO_ASSUMEE", default=False)


def fautes_de_configuration() -> list[str]:
    """Ce qui ne doit jamais partir en ligne. Vide si tout va bien.

    Le signal de « en ligne », c'est CB_PUBLIC_BASE_URL : on ne la définit que
    pour déployer. Tourner en local n'est donc jamais gêné.
    """
    fautes = []
    if not PUBLIC_BASE_URL:
        return fautes
    if DEMO_MODE and not DEMO_ASSUMEE:
        fautes.append(
            "MODE DÉMONSTRATION à une adresse publique : les élèves recevraient des "
            "contenus factices sans le savoir. Définir ANTHROPIC_API_KEY. "
            "Pour montrer la démonstration en connaissance de cause : CB_DEMO_ASSUMEE=1."
        )
    if AUTH_CODE_EN_CLAIR and not DEMO_ASSUMEE:
        fautes.append(
            "CB_AUTH_CODE_EN_CLAIR à une adresse publique : le code de réinitialisation "
            "revient dans la réponse HTTP, donc n'importe qui prend n'importe quel compte."
        )
    return fautes
