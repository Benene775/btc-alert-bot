"""API de Repère.

Une seule page web côté élève ; ici, les quelques routes qu'elle appelle.

Trois principes de découpage :
- Le navigateur garde le cours, les réponses et les fiches. Le serveur n'en voit
  rien, et n'en garde rien.
- Sauf le corrigé du contrôle en cours : si on l'envoyait avec les questions,
  n'importe quel élève le lirait dans les outils de développement avant de répondre.
- On entre avec son adresse mail et son mot de passe. Le mot de passe passe par
  scrypt avant d'être écrit ; « oublié » renvoie un code à six chiffres par
  courrier. Toutes les routes /api sauf /api/config et /api/auth/* exigent
  d'être connecté.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Cookie, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, courrier, formats, llm, rappels, schemas, store
from .schemas import (
    AbonnementPush,
    Connexion,
    ContexteSession,
    DemandeCode,
    DemandeControle,
    DemandeCorrection,
    DemandeFiche,
    DemandeFicheCiblee,
    DesabonnementPush,
    Evenement,
    Inscription,
    Reinitialisation,
    SeanceRangee,
    SignalementQuestion,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("controle-blanc")

TYPES_IMAGES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@asynccontextmanager
async def cycle_de_vie(_: FastAPI):
    store.connexion()
    supprimes = store.purger_corriges_anciens()
    if supprimes:
        logger.info("purge : %s corrigé(s) au-delà de la rétention supprimé(s)", supprimes)
    perimes = store.purger_auth()
    if perimes:
        logger.info("purge : %s code(s) et jeton(s) périmé(s) supprimé(s)", perimes)
    if not config.SMTP_HOTE:
        logger.warning(
            "AUCUN SERVEUR DE COURRIER : les codes de réinitialisation partent dans "
            "ces journaux. Définir CB_SMTP_HOTE pour les envoyer vraiment."
        )
    if config.AUTH_CODE_EN_CLAIR:
        logger.warning(
            "CB_AUTH_CODE_EN_CLAIR : le code de réinitialisation est renvoyé dans la "
            "réponse HTTP. N'importe qui prend n'importe quel compte — démonstration seulement."
        )
    if config.DEMO_MODE:
        logger.warning(
            "MODE DÉMONSTRATION : aucun appel au modèle, contenus factices. "
            "Définir ANTHROPIC_API_KEY et CB_DEMO_MODE=0 pour le mode réel."
        )
    # Et le refus, pour ce qui ne doit pas atteindre un élève. Un avertissement
    # de plus dans les journaux n'aurait servi à rien : personne ne les lit au
    # moment où ça compte.
    fautes = config.fautes_de_configuration()

    # Et la clé, qu'on ne peut pas juger sans demander au fournisseur. Elle peut
    # être présente, non vide, et refusée : c'est arrivé au premier déploiement,
    # où un copier-coller de 108 caractères a suffi. Rien ne le signalait —
    # seuls les élèves l'auraient découvert, un par un, derrière un « Réessaie »
    # qui ne marchait jamais. La vérification est gratuite et on ne la fait
    # qu'en ligne, pour ne pas exiger le réseau à chaque lancement local.
    if config.PUBLIC_BASE_URL:
        refus = llm.verifier_la_cle()
        if refus:
            fautes.append(refus)

    if fautes:
        for faute in fautes:
            logger.error("CONFIGURATION REFUSÉE : %s", faute)
        raise SystemExit(
            "Démarrage refusé : " + " | ".join(fautes)
        )

    # La tournée des rappels : une tâche qui dort et se réveille le soir. Elle
    # ne démarre pas sans clés VAPID — le produit marche très bien sans, et un
    # déploiement qui n'en veut pas ne doit pas avoir à le dire.
    veilleuse = None
    if config.RAPPELS_ACTIFS:
        veilleuse = asyncio.create_task(rappels.boucle())
        logger.info("rappels de contrôle actifs : tournée à %s h (%s)",
                    config.RAPPEL_HEURE, config.FUSEAU_RAPPELS)
    try:
        yield
    finally:
        if veilleuse:
            veilleuse.cancel()


app = FastAPI(title="Repère", docs_url=None, redoc_url=None, lifespan=cycle_de_vie)


@app.exception_handler(store.QuotaDepasse)
def gerer_quota(_: Request, exc: store.QuotaDepasse) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"erreur": "quota", "action": exc.action, "portee": exc.portee, "message": exc.message},
    )


@app.exception_handler(RequestValidationError)
def gerer_validation(requete: Request, exc: RequestValidationError) -> JSONResponse:
    """Une requête que le serveur refuse de lire.

    Ce n'est jamais la faute de l'élève : le navigateur envoie ce que le produit
    lui a fait ranger. C'est donc un défaut de notre côté, et il doit laisser
    une trace ICI — la réponse de FastAPI, elle, est une liste d'objets qui
    s'affichait « [object Object] » sur le téléphone d'un élève, devant le seul
    bouton qui l'intéressait.
    """
    ou = "; ".join(
        ".".join(str(morceau) for morceau in erreur.get("loc", ()))
        + " — " + str(erreur.get("msg", ""))
        for erreur in exc.errors()
    )
    logger.error("REQUÊTE REFUSÉE sur %s : %s", requete.url.path, ou[:600])
    return JSONResponse(
        status_code=422,
        content={"erreur": "requete",
                 "message": "On n'a pas réussi à envoyer ta demande. Réessaie — "
                            "si ça recommence, préviens ton professeur."},
    )


@app.exception_handler(llm.ErreurModele)
def gerer_modele(_: Request, exc: llm.ErreurModele) -> JSONResponse:
    # « reessayable » distingue l'incident de la panne : sur une panne de crédit,
    # inviter à réessayer envoie l'élève se cogner à la même porte indéfiniment.
    reessayable = not isinstance(exc, llm.CreditEpuise)
    return JSONResponse(status_code=503,
                        content={"erreur": "modele", "message": str(exc),
                                 "reessayable": reessayable})


@app.exception_handler(store.ErreurAuth)
def gerer_auth(_: Request, exc: store.ErreurAuth) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"erreur": "auth", "genre": exc.genre, "message": exc.message,
                 "attendre": exc.attendre},
    )


# --- Le compte : adresse mail et mot de passe -------------------------------
#
# Connexion, inscription, et « mot de passe oublié » qui envoie un code à six
# chiffres. Le mot de passe passe par scrypt, le code et le jeton par SHA-256 :
# rien n'est stocké en clair (voir store.py).
#
# Le jeton voyage dans un cookie HttpOnly : le script de la page ne peut pas le
# lire, donc une faille d'affichage ne le donne pas. SameSite=Lax suffit — toutes
# les écritures passent en POST, qu'un site tiers ne peut pas déclencher avec
# le cookie.

NOM_COOKIE = "cb_jeton"


def _source(requete: Request) -> str:
    """D'où vient la demande, pour la limite par machine.

    Derrière un proxy, l'IP vue est celle du proxy : toutes les demandes se
    ressembleraient, et la limite s'appliquerait à tout le monde d'un coup.
    On ne lit X-Forwarded-For que si l'exploitant l'affirme (CB_PROXY_DE_CONFIANCE) :
    sinon n'importe qui poserait l'en-tête et contournerait la limite en une ligne."""
    if config.PROXY_DE_CONFIANCE:
        transmis = requete.headers.get("x-forwarded-for", "")
        if transmis:
            return transmis.split(",")[0].strip()[:64]
    return (requete.client.host if requete.client else "")[:64]


def _poser_cookie(reponse: JSONResponse, jeton: str, requete: Request) -> None:
    reponse.set_cookie(
        NOM_COOKIE, jeton,
        max_age=config.DUREE_JETON_JOURS * 86400,
        httponly=True,
        samesite="lax",
        # En clair sur http://localhost pendant le développement ; jamais dès que
        # le site est servi en https.
        secure=requete.url.scheme == "https",
        path="/",
    )
    # Le piège du déploiement derrière un proxy : uvicorn ne croit l'en-tête
    # « X-Forwarded-Proto » que des machines listées dans --forwarded-allow-ips,
    # et par défaut il n'y a que 127.0.0.1. Sur Render, Railway ou Fly, le proxy
    # a une autre adresse : l'application voit du http, et ce cookie part sans
    # Secure sans que rien ne le signale. On le signale — à la première
    # connexion, et fort.
    if requete.url.scheme != "https" and config.PUBLIC_BASE_URL.startswith("https://"):
        logger.critical(
            "COOKIE SANS « Secure » — le site est annoncé en https (%s) mais la requête "
            "arrive en http : le proxy n'est pas reconnu. Pose CB_IPS_PROXY=* sur la "
            "plateforme, sinon le jeton de connexion circule en clair.",
            config.PUBLIC_BASE_URL)


def compte_connecte(cb_jeton: str | None = Cookie(default=None)) -> dict[str, str]:
    """Dépendance des routes protégées. 401 : la page renvoie vers l'entrée."""
    compte = store.compte_du_jeton(cb_jeton)
    if compte is None:
        raise HTTPException(status_code=401, detail="entrée requise")
    return compte


@app.post("/api/auth/inscription")
def inscription(corps: Inscription, request: Request) -> JSONResponse:
    """Ouvrir un compte, et être connecté dans la foulée : demander de se
    reconnecter juste après s'être inscrit, c'est un formulaire pour rien."""
    email = store.normaliser_email(corps.email)
    compte_id = store.inscrire(email, corps.mot_de_passe, corps.prenom, corps.niveau,
                               majeur_15=corps.majeur_15,
                               accord_parental=corps.accord_parental)
    jeton = store.ouvrir_jeton(compte_id)
    reponse = JSONResponse({"connecte": True, "email": email, "compte": compte_id,
                            "prenom": store.nettoyer_prenom(corps.prenom),
                            "niveau": (corps.niveau or "").strip()})
    _poser_cookie(reponse, jeton, request)
    return reponse


@app.post("/api/auth/connexion")
def connexion(corps: Connexion, request: Request) -> JSONResponse:
    email = store.normaliser_email(corps.email)
    compte_id = store.connecter(email, corps.mot_de_passe, _source(request))
    jeton = store.ouvrir_jeton(compte_id)
    fiche = store.profil(compte_id) or {}
    reponse = JSONResponse({"connecte": True, "email": email, "compte": compte_id,
                            "prenom": fiche.get("prenom", ""), "niveau": fiche.get("niveau", "")})
    _poser_cookie(reponse, jeton, request)
    return reponse


@app.post("/api/auth/oubli")
def mot_de_passe_oublie(corps: DemandeCode, request: Request) -> dict[str, Any]:
    """Envoie un code de réinitialisation.

    Répond pareil que l'adresse soit connue ou non : sinon ce formulaire devient
    un moyen de savoir qui est inscrit. Un code n'est réellement fabriqué et
    envoyé que si le compte existe — mais la cadence est décomptée dans les deux
    cas, sans quoi le temps de réponse trahirait la différence.
    """
    email = store.normaliser_email(corps.email)
    connu = store.compte_existe(email)
    # La cadence est décomptée dans les deux cas ; le code n'est gardé que s'il
    # peut servir. Sans ça, la table se remplit de codes pour des adresses qui
    # n'ont pas de compte.
    code = store.preparer_code(email, _source(request), garder=connu)
    reponse: dict[str, Any] = {
        # La vérité, pas une politesse : sans serveur de courrier, le code part
        # dans les journaux et nulle part ailleurs (voir courrier.envoyer_code).
        # Annoncer « ton code est parti » enverrait l'élève surveiller une boîte
        # mail où rien n'arrivera jamais — et conclure que l'application est
        # cassée. C'est une constante du service, pas un fait sur ce compte :
        # elle ne dit donc rien de qui est inscrit.
        "envoye": bool(config.SMTP_HOTE),
        "expire_dans_minutes": config.DUREE_CODE_MINUTES,
        "renvoi_dans_secondes": config.DELAI_ENTRE_CODES_SECONDES,
    }
    if not connu:
        # Rien ne part : on n'écrit pas à quelqu'un qui n'a pas de compte chez
        # nous. L'élève qui s'est trompé d'adresse ne verra pas de code arriver,
        # ce qui est exactement l'information dont il a besoin.
        return reponse
    try:
        courrier.envoyer_code(email, code)
    except courrier.ErreurCourrier as erreur:
        raise HTTPException(status_code=502, detail=str(erreur)) from erreur
    if config.AUTH_CODE_EN_CLAIR:
        # Démonstration seulement : voir le garde-fou dans config.py.
        reponse["code_demonstration"] = code
    return reponse


@app.post("/api/auth/reinitialiser")
def reinitialiser(corps: Reinitialisation, request: Request) -> JSONResponse:
    email = store.normaliser_email(corps.email)
    store.verifier_code(email, corps.code)
    compte_id = store.changer_mot_de_passe(email, corps.mot_de_passe)
    # changer_mot_de_passe ferme toutes les connexions ouvertes : si quelqu'un
    # avait pris le compte, il en sort ici. On en rouvre une pour l'élève.
    jeton = store.ouvrir_jeton(compte_id)
    fiche = store.profil(compte_id) or {}
    reponse = JSONResponse({"connecte": True, "email": email, "compte": compte_id,
                            "prenom": fiche.get("prenom", ""), "niveau": fiche.get("niveau", "")})
    _poser_cookie(reponse, jeton, request)
    return reponse


@app.get("/api/auth/moi")
def qui_suis_je(cb_jeton: str | None = Cookie(default=None)) -> dict[str, Any]:
    compte = store.compte_du_jeton(cb_jeton)
    if compte is None:
        return {"connecte": False}
    return {"connecte": True, "email": compte["email"], "compte": compte["id"],
            "prenom": compte.get("prenom", ""), "niveau": compte.get("niveau", "")}


@app.get("/api/compte/quotas")
def quotas_du_compte(compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    """Ce qu'il reste au compte ce mois-ci. Affiché sur la page perso : voir la
    limite venir vaut mieux que la découvrir en lançant un contrôle."""
    return {"mois": store.mois_courant(), "quotas": store.quotas_du_compte(compte["id"])}


@app.post("/api/auth/sortir")
def sortir(cb_jeton: str | None = Cookie(default=None)) -> JSONResponse:
    store.fermer_jeton(cb_jeton)
    reponse = JSONResponse({"connecte": False})
    reponse.delete_cookie(NOM_COOKIE, path="/")
    return reponse


@app.post("/api/auth/supprimer")
def supprimer(cb_jeton: str | None = Cookie(default=None),
              compte: dict = Depends(compte_connecte)) -> JSONResponse:
    """Le droit à l'effacement, à un clic. Il n'a pas à passer par un courrier
    au responsable de traitement : c'est nous, et le bouton est dans la page."""
    store.supprimer_compte(compte["id"])
    reponse = JSONResponse({"supprime": True})
    reponse.delete_cookie(NOM_COOKIE, path="/")
    return reponse


def _session_valide(session_id: str, compte: dict[str, str] | None = None) -> str:
    """Une séance appartient à un compte. Sans ce contrôle, le lien de reprise
    d'un camarade — neuf caractères — ouvrirait son cours et brûlerait ses quotas."""
    compte_id = compte["id"] if compte else None
    if not session_id or not store.session_existe(session_id, compte_id):
        raise HTTPException(status_code=404, detail="session inconnue")
    store.toucher_session(session_id)
    return session_id


def _chapitres_en_dicts(chapitres: list) -> list[dict[str, Any]]:
    return [c.model_dump() for c in chapitres]


# --- Page et configuration --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def page() -> FileResponse:
    return FileResponse(config.WEB_DIR / "index.html")


@app.get("/api/config")
def configuration() -> dict[str, Any]:
    return {
        "matieres": formats.liste_matieres(),
        "niveaux": formats.NIVEAUX,
        "mode_demonstration": config.DEMO_MODE,
        "max_photos": config.MAX_PHOTOS_PAR_ANALYSE,
        "max_doutes": config.MAX_DOUTES,
        # Vide quand les clés VAPID ne sont pas posées : le navigateur n'affiche
        # alors aucun réglage de rappel, plutôt qu'un bouton qui ne marche pas.
        "vapid_publique": config.VAPID_CLE_PUBLIQUE if config.RAPPELS_ACTIFS else "",
    }


# --- Le classeur ------------------------------------------------------------
#
# Un compte promet qu'on retrouve ses affaires ailleurs. Jusqu'ici le classeur
# vivait dans le seul navigateur où il avait été fait : changer d'appareil, ou
# vider ses données, le perdait entièrement. Ces deux routes le font monter.
#
# Le modèle est volontairement pauvre : une séance entière, la plus récente
# gagne. Pas de fusion champ par champ — c'est un élève sur un ou deux
# appareils, et une fusion se paierait en pertes silencieuses.

@app.get("/api/classeur")
def lire_classeur(depuis: str = "", compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    """Les séances modifiées depuis « depuis ». Sans lui, tout le classeur.

    « maintenant » est l'horodatage à renvoyer au prochain appel : le prendre du
    serveur évite qu'une horloge de téléphone en avance fasse sauter des séances.
    """
    return {
        "seances": store.lire_classeur(compte["id"], depuis or None),
        # L'agenda part entier à chaque fois : c'est une liste de dates, elle
        # pèse quelques centaines d'octets. Le découper par date coûterait plus
        # de code que ça n'économiserait d'octets.
        "agenda": store.lire_agenda(compte["id"]),
        # L'horodatage à renvoyer au prochain appel. Il vient du serveur et se
        # compare à range_le, jamais à l'heure d'un téléphone.
        "maintenant": store.maintenant_precis(),
    }


@app.put("/api/agenda")
def ranger_agenda(corps: SeanceRangee, compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    try:
        json.loads(corps.contenu)
    except ValueError:
        raise HTTPException(status_code=400, detail="contenu illisible")
    return {"range": store.poser_agenda(compte["id"], corps.contenu, corps.maj_le)}


# --- Les rappels de contrôle ------------------------------------------------
#
# Les routes disent « rappels » et non « abonnement » : le mot veut dire
# « payant » pour un élève, et le produit promet qu'il n'y a rien à payer —
# c'est même tenu par un test (test_age_et_accord). Le terme technique du
# protocole reste dans store.py, que personne ne lit à quinze ans.
#
# Le navigateur s'inscrit, le serveur garde l'adresse, et la tournée du soir
# (app/rappels.py) lit l'agenda pour savoir quoi dire. Rien d'autre ne part
# d'ici : pas de message commercial, pas de relance parce qu'on n'est pas venu.

@app.post("/api/rappels/activer")
def activer_rappels(corps: AbonnementPush,
                    compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    if not config.RAPPELS_ACTIFS:
        raise HTTPException(status_code=503, detail="les rappels ne sont pas configurés")
    store.abonner_push(compte["id"], corps.endpoint, corps.p256dh, corps.auth)
    return {"abonne": True}


@app.post("/api/rappels/arreter")
def arreter_rappels(corps: DesabonnementPush,
                    compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    # Pas de vérification du compte : l'endpoint est un secret que seul ce
    # navigateur connaît, et refuser un désabonnement est bien pire que
    # d'en accepter un de trop — on garderait quelqu'un abonné contre son gré.
    store.desabonner_push(corps.endpoint)
    return {"abonne": False}


@app.get("/api/rappels/etat")
def etat_rappels(compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    return {
        "possible": config.RAPPELS_ACTIFS,
        "appareils": len(store.abonnements_du_compte(compte["id"])),
    }


@app.put("/api/classeur/{seance_id}")
def ranger_seance(seance_id: str, corps: SeanceRangee,
                  compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    if not store.session_existe(seance_id, compte["id"]):
        raise HTTPException(status_code=404, detail="session inconnue")
    try:
        json.loads(corps.contenu)
    except ValueError:
        raise HTTPException(status_code=400, detail="contenu illisible")
    # Le plafond ne vaut que pour une séance NOUVELLE : refuser la mise à jour
    # d'une séance déjà rangée bloquerait un élève au plafond sur son propre
    # travail — il ne pourrait plus rien sauvegarder de ce qu'il a déjà.
    if (not store.seance_rangee(compte["id"], seance_id)
            and store.compter_seances(compte["id"]) >= schemas.MAX_SEANCES_PAR_COMPTE):
        raise HTTPException(status_code=413, detail="classeur plein")
    ecrit = store.poser_seance(compte["id"], seance_id, corps.contenu, corps.maj_le)
    return {"range": ecrit}


@app.delete("/api/classeur/{seance_id}")
def effacer_seance(seance_id: str, compte: dict = Depends(compte_connecte)) -> dict[str, str]:
    """Effacée sur le téléphone, effacée ici : sinon la synchronisation suivante
    la ferait revenir, et l'élève ne comprendrait pas."""
    store.oublier_seance(compte["id"], seance_id)
    return {"etat": "ok"}


# --- Session ----------------------------------------------------------------

@app.post("/api/session")
def nouvelle_session(request: Request,
                     compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    session_id = store.creer_session(compte["id"])
    base = config.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    store.enregistrer_evenement(session_id, "ouverture", {"origine": "creation"})
    return {"session_id": session_id, "lien_de_reprise": f"{base}/?s={session_id}"}


@app.get("/api/session/{session_id}")
def etat_session(session_id: str, request: Request,
                 compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    _session_valide(session_id, compte)
    base = config.PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    return {
        "session_id": session_id,
        "lien_de_reprise": f"{base}/?s={session_id}",
        "quotas": {action: store.etat_quota(session_id, action) for action in config.QUOTAS},
    }


@app.post("/api/session/contexte")
def enregistrer_contexte(corps: ContexteSession,
                        compte: dict = Depends(compte_connecte)) -> dict[str, str]:
    _session_valide(corps.session_id, compte)
    store.toucher_session(
        corps.session_id,
        niveau=corps.niveau,
        matiere=corps.matiere,
        date_controle=corps.date_controle,
    )
    return {"etat": "ok"}


@app.post("/api/evenement")
def evenement(corps: Evenement, compte: dict = Depends(compte_connecte)) -> dict[str, str]:
    _session_valide(corps.session_id, compte)
    store.enregistrer_evenement(corps.session_id, corps.type, corps.details)
    return {"etat": "ok"}


# --- Étape 1 : les photos ---------------------------------------------------

@app.post("/api/analyse")
async def analyser(
    session_id: str = Form(...),
    niveau: str = Form("3e"),
    matiere: str = Form(""),
    photos: list[UploadFile] = File(...),
    compte: dict = Depends(compte_connecte),
) -> dict[str, Any]:
    _session_valide(session_id, compte)

    if not photos:
        raise HTTPException(status_code=400, detail="aucune photo reçue")
    if len(photos) > config.MAX_PHOTOS_PAR_ANALYSE:
        raise HTTPException(
            status_code=400,
            detail=f"{config.MAX_PHOTOS_PAR_ANALYSE} photos au maximum en une fois",
        )
    # L'analyse se compte en pages : on vérifie ce que cet envoi VA consommer,
    # une fois qu'on sait combien de photos il porte. Un premier refus ici évite
    # de lire pour rien quarante mégaoctets ; la place, elle, se prend plus bas.
    store.verifier_quota(session_id, "analyse", len(photos))

    images: list[tuple[str, bytes]] = []
    for fichier in photos:
        mime = (fichier.content_type or "").lower()
        if mime not in TYPES_IMAGES:
            raise HTTPException(status_code=400, detail=f"format d'image non géré : {mime}")
        octets = await fichier.read()
        if len(octets) > config.MAX_OCTETS_PAR_PHOTO:
            raise HTTPException(status_code=413, detail="photo trop lourde après compression")
        images.append((mime, octets))

    # La place est prise ICI, juste avant la dépense, et d'un seul tenant : la
    # lecture des fichiers ci-dessus rend la main dès qu'une photo dépasse 1 Mo,
    # et deux envois simultanés passaient tous les deux (voir store.reserver_quota).
    usage_id = store.reserver_quota(session_id, "analyse", len(images))
    try:
        # Les octets ne sortent pas d'ici : envoyés au modèle, jamais écrits sur disque.
        resultat, usage = llm.analyser_photos(images, formats.nom_niveau(niveau), matiere)
    except Exception:
        store.liberer_quota(usage_id)
        raise
    store.completer_usage(usage_id, usage)
    store.enregistrer_evenement(
        session_id,
        "photos_analysees",
        {"photos": len(images), "chapitres": len(resultat.get("chapitres", []))},
    )
    resultat["quotas"] = store.etat_quota(session_id, "analyse")
    return resultat


# --- Étape 3 et 6 : les fiches ---------------------------------------------

@app.post("/api/fiche/generale")
def creer_fiche_generale(corps: DemandeFiche,
                         compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    _session_valide(corps.session_id, compte)
    usage_id = store.reserver_quota(corps.session_id, "fiche_generale")
    try:
        fiche, usage = llm.fiche_generale(
            _chapitres_en_dicts(corps.chapitres), formats.nom_niveau(corps.niveau)
        )
    except Exception:
        store.liberer_quota(usage_id)
        raise
    store.completer_usage(usage_id, usage)
    store.enregistrer_evenement(corps.session_id, "fiche_generee", {"type": "generale"})
    fiche["type"] = "generale"
    return fiche


@app.post("/api/fiche/ciblee")
def creer_fiche_ciblee(corps: DemandeFicheCiblee,
                       compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    _session_valide(corps.session_id, compte)
    usage_id = store.reserver_quota(corps.session_id, "fiche_ciblee")
    try:
        fiche, usage = llm.fiche_ciblee(
            _chapitres_en_dicts(corps.chapitres),
            formats.nom_niveau(corps.niveau),
            [n.model_dump() for n in corps.notions],
        )
    except Exception:
        store.liberer_quota(usage_id)
        raise
    store.completer_usage(usage_id, usage)
    store.enregistrer_evenement(corps.session_id, "fiche_generee", {"type": "ciblee"})
    fiche["type"] = "ciblee"
    return fiche


# --- Étapes 4 et 7 : le contrôle blanc -------------------------------------

CHAMPS_CORRIGE = ("points_attendus", "ou_dans_le_cours")

# Ce que le modèle produit pour lui-même, et que le navigateur n'a pas à voir.
# « duree_minutes » servait à un compte à rebours ; le compte à rebours est
# parti, et la durée reste ici, où elle calibre le sujet et où la garde s'en
# sert pour distinguer un contrôle d'un quiz. Sur le téléphone d'un élève, elle
# n'a plus rien à faire : une durée affichée est un chronomètre qui s'ignore.
CHAMPS_INTERNES = ("duree_minutes",)


@app.post("/api/controle")
def creer_controle(corps: DemandeControle,
                   compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    _session_valide(corps.session_id, compte)
    usage_id = store.reserver_quota(corps.session_id, "controle")

    fmt = formats.format_matiere(corps.matiere)
    try:
        brut, usage = llm.generer_controle(
            _chapitres_en_dicts(corps.chapitres),
            formats.nom_niveau(corps.niveau),
            fmt["nom"],
            fmt["structure"],
            fmt["duree_minutes"],
            notions_ciblees=corps.notions_ciblees or None,
            enonces_deja_poses=corps.enonces_deja_poses or None,
        )
        questions = brut.get("questions", [])
        if not questions:
            # Rien à passer : le contrôle n'est pas décompté.
            raise HTTPException(status_code=502, detail="contrôle vide")
    except Exception:
        store.liberer_quota(usage_id)
        raise

    controle_id = uuid.uuid4().hex
    # Le corrigé reste ici. Le navigateur reçoit les énoncés, pas les réponses.
    store.enregistrer_corrige(
        controle_id,
        corps.session_id,
        {"questions": questions, "titre": brut.get("titre", "")},
    )
    store.completer_usage(usage_id, usage)
    store.enregistrer_evenement(
        corps.session_id,
        "controle_commence",
        {"cible": bool(corps.notions_ciblees), "questions": len(questions)},
    )

    caches = CHAMPS_CORRIGE + CHAMPS_INTERNES
    publiques = [
        {cle: valeur for cle, valeur in q.items() if cle not in caches}
        for q in questions
    ]
    return {
        "controle_id": controle_id,
        "titre": brut.get("titre", "Contrôle blanc"),
        "consigne_generale": brut.get("consigne_generale", ""),
        "matiere": fmt["nom"],
        "questions": publiques,
        "quotas": store.etat_quota(corps.session_id, "controle"),
    }


# --- Étape 5 : la correction commentée -------------------------------------

@app.post("/api/correction")
def corriger(corps: DemandeCorrection,
             compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    _session_valide(corps.session_id, compte)
    corrige = store.lire_corrige(corps.controle_id, corps.session_id)
    if not corrige:
        raise HTTPException(status_code=404, detail="contrôle introuvable ou expiré")

    reponses = {r.numero: r.texte for r in corps.reponses}
    signales = set(corps.numeros_signales)

    # La correction n'est pas décomptée : elle fait partie du contrôle déjà
    # compté, et faire payer un contrôle sans résultat n'aurait pas de sens.
    # Mais « pas décomptée » ne veut pas dire « sans limite » : rien n'empêchait
    # de rejouer cet appel sur le même contrôle, à 0,06 $ la fois, indéfiniment.
    # Une copie se corrige une fois — le nombre de corrections d'un mois ne peut
    # alors pas dépasser celui des contrôles, qui est plafonné.
    if not store.marquer_corrige(corps.controle_id, corps.session_id):
        raise HTTPException(
            status_code=409,
            detail="Cette copie a déjà été corrigée. Ta correction est sur ta page.",
        )
    try:
        resultat, usage = llm.corriger(
            _chapitres_en_dicts(corps.chapitres),
            formats.nom_niveau(corps.niveau),
            corrige["questions"],
            reponses,
            signales,
        )
    except Exception:
        # Pas de correction, donc le droit d'en redemander une : sinon une panne
        # du modèle enfermerait l'élève devant une copie qu'il ne verra jamais.
        store.liberer_correction(corps.controle_id, corps.session_id)
        raise
    store.enregistrer_usage(corps.session_id, "correction", usage)
    store.enregistrer_evenement(corps.session_id, "controle_termine", {"questions": len(reponses)})
    store.enregistrer_evenement(corps.session_id, "correction_vue", {})

    # On rattache l'énoncé et la réponse de l'élève à chaque correction : le
    # navigateur n'a plus qu'à afficher.
    par_numero = {q["numero"]: q for q in corrige["questions"]}
    for ligne in resultat.get("reponses", []):
        question = par_numero.get(ligne.get("numero"), {})
        ligne["enonce"] = question.get("enonce", "")
        ligne["notion"] = question.get("notion", "")
        ligne["document"] = question.get("document", "")
        ligne["ta_reponse"] = reponses.get(ligne.get("numero"), "")
        ligne["signalee"] = ligne.get("numero") in signales
    return resultat


# --- « Cette question me semble fausse » ------------------------------------

@app.post("/api/signalement")
def signaler(corps: SignalementQuestion,
             compte: dict = Depends(compte_connecte)) -> dict[str, str]:
    _session_valide(corps.session_id, compte)
    store.enregistrer_evenement(
        corps.session_id,
        "question_signalee",
        {
            "controle_id": corps.controle_id,
            "numero": corps.numero,
            "enonce": corps.enonce[:400],
            "motif": corps.motif[:400],
        },
    )
    return {
        "etat": "ok",
        "message": "C'est noté, merci. Cette question ne comptera pas contre toi.",
    }


# --- Tableau de bord du test ------------------------------------------------

@app.get("/admin/metriques", response_class=HTMLResponse)
def tableau_de_bord(token: str = "") -> HTMLResponse:
    if not config.ADMIN_TOKEN:
        raise HTTPException(status_code=404, detail="tableau de bord désactivé")
    if token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="jeton invalide")

    m = store.metriques()
    par_eleve = store.cout_par_eleve()
    signalees = store.questions_signalees_detail(30)

    # Tout ce qui suit est écrit par des élèves (motifs de signalement, énoncés,
    # nom du chemin choisi). Ça ne rentre pas dans la page sans être échappé.
    def txt(valeur: Any) -> str:
        return html.escape(str(valeur), quote=True)

    def ligne(titre: str, valeur: Any, note: str = "", classe: str = "") -> str:
        attribut = f" class='{classe}'" if classe else ""
        return (
            f"<tr{attribut}><th>{titre}</th><td class='v'>{valeur}</td>"
            f"<td class='n'>{note}</td></tr>"
        )

    chemins = "".join(
        f"<tr><th>{txt(cle)}</th><td class='v'>{v['sessions']}</td>"
        f"<td class='n'>{v['revenus']} revenus un autre jour</td></tr>"
        for cle, v in sorted(m["par_chemin"].items())
    ) or "<tr><td colspan='3' class='n'>Aucun choix enregistré pour l'instant.</td></tr>"

    couts = "".join(
        f"<tr><th>{txt(d['action'])}</th><td class='v'>{d['appels']}</td>"
        f"<td class='n'>{d['cout_usd']} $ &middot; {txt(d['modele'])}</td></tr>"
        for d in m["detail_cout"]
    ) or "<tr><td colspan='3' class='n'>Aucun appel facturé.</td></tr>"

    # Un tarif manquant fausse la colonne entière sans rien casser : on le dit.
    alerte_tarifs = (
        "<p class='alerte'>Tarif inconnu pour "
        + txt(", ".join(m["tarifs_inconnus"]))
        + " — ces lignes sont chiffrées au tarif par défaut, donc fausses. "
        + "Ajouter le modèle dans <code>PRIX_USD_PAR_MTOK_PAR_MODELE</code>.</p>"
    ) if m["tarifs_inconnus"] else ""

    # --- Ce que coûte chaque élève, poste par poste --------------------------
    #
    # La moyenne, la médiane et le maximum disaient COMBIEN et jamais POURQUOI.
    # Quand un chiffre dérape, il faut savoir s'il faut baisser les pages, les
    # contrôles ou les fiches : trois plafonds différents, et les photos font
    # l'essentiel de la note.
    #
    # Les teintes suivent le POSTE, jamais son rang du jour : deux captures
    # prises à une semaine d'écart doivent se comparer. Elles sont validées pour
    # le daltonisme sur ce fond (contraste faible pour trois d'entre elles, d'où
    # la règle : tout chiffre est écrit en toutes lettres dans le tableau, la
    # barre ne fait que résumer ce qui est déjà lisible).
    TEINTES = {
        "analyse": "#2a78d6",
        "controle": "#eb6834",
        "correction": "#1baf7a",
        "fiche_generale": "#eda100",
        "fiche_ciblee": "#e87ba4",
    }

    def sous(valeur: float) -> str:
        """Des sous, écrits comme on les lit : trois décimales sous le dollar."""
        return (f"{valeur:.3f}" if valeur < 1 else f"{valeur:.2f}").replace(".", ",") + " $"

    def barre(postes: dict[str, Any], total: float) -> str:
        """La composition d'une dépense, en une barre. Elle ne porte aucun
        chiffre : ils sont tous dans les cellules, à côté."""
        if total <= 0:
            return ""
        morceaux = []
        for poste in store.POSTES:
            part = postes[poste]["cout_usd"] / total * 100
            if part <= 0:
                continue
            morceaux.append(
                f"<span style='width:{part:.2f}%;background:{TEINTES[poste]}'"
                f" title='{txt(store.NOM_DU_POSTE[poste])}'></span>"
            )
        return "<span class='barre'>" + "".join(morceaux) + "</span>"

    legende = "".join(
        f"<span class='cle-couleur'><i style='background:{TEINTES[poste]}'></i>"
        f"{txt(store.NOM_DU_POSTE[poste])}</span>"
        for poste in store.POSTES
    )

    entetes = "".join(f"<th class='v'>{txt(store.NOM_DU_POSTE[p])}</th>" for p in store.POSTES)

    def cellule(nom_poste: str, poste: dict[str, Any]) -> str:
        if not poste["quantite"] and not poste["cout_usd"]:
            return "<td class='v vide'>—</td>"
        combien = poste["quantite"]
        return (f"<td class='v'>{sous(poste['cout_usd'])}"
                f"<small>{combien} {txt(store.unite(nom_poste, combien))}</small></td>")

    lignes_eleves = "".join(
        f"<tr><th class='qui'>{txt(e['prenom'])}"
        + (f"<small>{txt(e['niveau'])}</small>" if e["niveau"] else "")
        + barre(e["postes"], e["cout_usd"])
        + "</th>"
        + f"<td class='v total'>{sous(e['cout_usd'])}<small>en tout</small></td>"
        + "".join(cellule(p, e["postes"][p]) for p in store.POSTES)
        + "</tr>"
        for e in par_eleve["eleves"]
    ) or ("<tr><td colspan='7' class='n'>Aucun appel facturé pour l’instant : "
          "aucun élève n’a encore rentré de cours.</td></tr>")

    # --- Où va l'argent, tous élèves confondus, et ce que coûte UNE unité ----
    total_general = par_eleve["cout_usd_total"]
    nb_eleves = len(par_eleve["eleves"]) or 1
    # Un volume sans coût, c'est le mode démonstration — et c'est aussi l'état
    # d'une base neuve. La part de chaque poste vaut alors zéro, pas une
    # division par zéro qui renverrait une erreur 500 au lieu du tableau.
    part_de = (lambda c: c / total_general * 100) if total_general > 0 else (lambda c: 0.0)
    lignes_postes = "".join(
        f"<tr><th><i class='pastille' style='background:{TEINTES[poste]}'></i>"
        f"{txt(store.NOM_DU_POSTE[poste])}</th>"
        f"<td class='v'>{sous(t['cout_usd'])}"
        f"<small>{part_de(t['cout_usd']):.0f} % du total</small></td>"
        f"<td class='v'>{t['quantite']}"
        f"<small>{txt(store.unite(poste, t['quantite']))}</small></td>"
        f"<td class='v'>{sous(t['cout_usd'] / t['quantite']) if t['quantite'] else '—'}"
        f"<small>l’unité</small></td>"
        f"<td class='v'>{sous(t['cout_usd'] / nb_eleves)}<small>par élève</small></td></tr>"
        for poste, t in ((p, par_eleve["totaux"][p]) for p in store.POSTES)
        if t["cout_usd"] or t["quantite"]
    ) or "<tr><td colspan='5' class='n'>Rien à répartir.</td></tr>"

    liste_signalees = "".join(
        f"<li><b>Q{txt(signal.get('numero', '?'))}</b> — {txt(signal.get('enonce', '')[:160])}"
        + (f"<br><i>{txt(signal.get('motif'))}</i>" if signal.get("motif") else "")
        + "</li>"
        for signal in signalees
    ) or "<li class='n'>Aucune question signalée.</li>"

    page_html = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Repère — mesures du test</title>
<style>
 body {{ font: 16px/1.5 system-ui, sans-serif; margin: 0 auto; padding: 24px;
        max-width: 980px; background: #faf9f7; color: #1c1a17; }}
 /* Le texte explicatif garde une longueur de ligne lisible : une phrase qui
    court sur 980 px se relit deux fois. Les tableaux, eux, prennent la place. */
 h1, h2, p {{ max-width: 46em; }}
 h1 {{ font-size: 1.4rem; }} h2 {{ font-size: 1rem; margin-top: 32px; text-transform: uppercase;
      letter-spacing: .06em; color: #6b6560; }}
 table {{ width: 100%; border-collapse: collapse; }}
 th {{ text-align: left; font-weight: 500; padding: 10px 0; border-bottom: 1px solid #e5e1db; }}
 td {{ padding: 10px 0; border-bottom: 1px solid #e5e1db; }}
 td.v {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; width: 90px; }}
 td.n {{ color: #6b6560; font-size: .85rem; padding-left: 16px; }}
 .cle td.v {{ color: #b4530a; font-size: 1.3rem; }}
 .alerte {{ background: #fdf1e3; border-left: 3px solid #b4530a; padding: 10px 14px;
            font-size: .85rem; margin: 12px 0; }}
 code {{ font-size: .85em; }}
 ul {{ padding-left: 18px; }} li {{ margin-bottom: 10px; font-size: .9rem; }}

 /* Le tableau par élève est large : il défile plutôt qu'il ne se comprime.
    Comprimé, les colonnes se chevauchent et on ne lit plus rien. */
 .large {{ overflow-x: auto; margin: 0 -24px; padding: 0 24px; }}
 .large table {{ min-width: 640px; }}
 .large th, .large td {{ white-space: nowrap; }}
 td.v small, th small {{ display: block; font-weight: 400; font-size: .72rem;
                         color: #6b6560; letter-spacing: 0; }}
 td.v {{ width: auto; padding-left: 14px; }}
 td.vide {{ color: #c7c1b8; }}
 td.total {{ color: #b4530a; }}
 th {{ font-weight: 600; }}
 /* Sans ce rembourrage, les en-têtes se soudent : « CONTRÔLESCORRECTIONSFICHES ».
    Ils doivent suivre les cellules qu'ils coiffent, pas la règle des <th> de gauche. */
 thead th {{ font-size: .78rem; text-transform: uppercase; letter-spacing: .04em;
             color: #6b6560; font-weight: 600; }}
 thead th.v {{ text-align: right; padding-left: 18px; }}
 .large td.v {{ padding-left: 18px; }}

 /* La barre ne porte aucun chiffre : ils sont tous dans les cellules à côté.
    Elle répond à « où part l'argent de cet élève » d'un coup d'oeil, et le
    filet de 2 px empêche deux teintes voisines de se souder. */
 th.qui {{ min-width: 150px; }}
 .barre {{ display: flex; gap: 2px; height: 8px; border-radius: 4px; margin-top: 7px;
           overflow: hidden; background: #ece7e0; }}
 .barre span {{ display: block; height: 100%; }}
 .legende {{ display: flex; flex-wrap: wrap; gap: 14px; margin: 10px 0 14px;
             font-size: .8rem; color: #6b6560; }}
 .cle-couleur {{ display: inline-flex; align-items: center; gap: 6px; }}
 .cle-couleur i, .pastille {{ width: 10px; height: 10px; border-radius: 3px;
                              display: inline-block; flex: 0 0 auto; }}
 .pastille {{ margin-right: 8px; vertical-align: baseline; }}
</style>
<h1>Repère — mesures du test</h1>
<h2>Par élève — ce que le test doit répondre</h2>
<table>
 {ligne("Élèves actifs", m["eleves_actifs"], "ont fait au moins une chose")}
 {ligne("Revenus un autre jour", m["eleves_revenus_un_autre_jour"], "pas le même jour que la découverte")}
 {ligne("Revenus une semaine après", m["eleves_revenus_une_semaine_apres"], "le seul signe d'un usage qui tient", classe="cle")}
 {ligne("Jours actifs (médiane)", m["jours_actifs_median_par_eleve"], "par élève")}
 {ligne("Ont rentré 2 cours ou plus", m["eleves_deux_cours_ou_plus"], "un seul cours = un essai")}
</table>

<h2>Par cours</h2>
<table>
 {ligne("Liens ouverts", m["ouvertures"], "séances distinctes")}
 {ligne("2 fiches ou plus", m["deux_fiches_ou_plus"], "sans qu'on le demande")}
 {ligne("Cours rouverts le lendemain", m["revenus_le_lendemain"], "un cours, pas un élève")}
</table>
<h2>Détail</h2>
<table>
 {ligne("Sessions créées", m["sessions_creees"])}
 {ligne("Revenus un autre jour", m["revenus_un_autre_jour"], "pas forcément J+1")}
 {ligne("Contrôles terminés", m["controles_termines"])}
 {ligne("Questions signalées", m["questions_signalees"], "« me semble fausse »")}
</table>
<h2>Étape 3 — quel chemin, et lequel fait revenir</h2>
<table>{chemins}</table>
<h2>Coût par appel</h2>
{alerte_tarifs}
<table>
 {couts}
 {ligne("Total", sous(m['cout_usd_total']), f"{sous(m['cout_usd_par_session'])} par séance")}
</table>
<h2>Ce que coûte chaque élève</h2>
<p class='n'>Une ligne par élève, du plus cher au moins cher. Chaque case donne ce que
le poste a coûté, et en dessous ce qu'il a consommé. La barre sous le prénom résume
d'où vient sa dépense — elle ne dit rien que les chiffres de la ligne ne disent déjà.</p>
<div class='legende'>{legende}</div>
<div class='large'><table>
 <thead><tr><th>Élève</th><th class='v'>Total</th>{entetes}</tr></thead>
 <tbody>{lignes_eleves}</tbody>
</table></div>

<h2>Où va l’argent, et ce que coûte une unité</h2>
<p class='n'>La colonne « l’unité » est celle qui sert à décider : c'est le prix d'UNE page
photographiée, d'UN contrôle blanc, d'UNE fiche. Les plafonds du mois se règlent là-dessus.</p>
<p class='n'><b>Tout est en dollars et hors taxes</b> — ce sont les tarifs affichés du
fournisseur. Selon ton statut, la facture peut porter 20 % de TVA en plus, et elle est
en euros : c'est elle qui fait foi, pas cette page.</p>
<div class='large'><table>
 <thead><tr><th>Poste</th><th class='v'>Coût</th><th class='v'>Volume</th>
 <th class='v'>À l’unité</th><th class='v'>Par élève</th></tr></thead>
 <tbody>{lignes_postes}</tbody>
</table></div>

<h2>Le chiffre qui décide de l’abonnement</h2>
<p class='n'>Le coût d'un compte sur un mois. Pas le pire cas, qui suppose un élève
saturant les quatre compteurs — la moyenne, avec le maximum à côté pour savoir si
les plafonds tiennent.</p>
<table>
 {ligne("Moyenne", sous(m['cout_usd_moyen_compte_mois']),
        "à comparer à ce qu'un abonnement encaisse net", classe="cle")}
 {ligne("Médiane", sous(m['cout_usd_median_compte_mois']), "l'élève ordinaire")}
 {ligne("Maximum", sous(m['cout_usd_max_compte_mois']), "le plus gourmand : les plafonds tiennent-ils ?")}
 {ligne("Mesuré sur", m["comptes_mois_mesures"], "couples compte × mois")}
</table>
<h2>Questions signalées</h2>
<ul>{liste_signalees}</ul>
"""
    return HTMLResponse(page_html)


# --- Combien de temps le navigateur a le droit de garder un fichier ----------
#
# Sans en-tête, un navigateur invente sa propre règle : il garde le fichier une
# fraction du temps écoulé depuis sa dernière modification. Ça ne se voit jamais
# en développement, où l'on recharge de force, et ça se voit très mal en ligne —
# le site est à jour pour celui qui vide son cache, périmé pour tous les autres.
#
# Pendant la phase de test, le code change plusieurs fois par jour. Un élève sur
# un téléphone qu'on ne peut pas inspecter signalerait alors un défaut déjà
# corrigé, ou ne verrait pas une correction qu'on lui a annoncée. Trouvé comme
# ça, justement : un « app.js » corrigé et en ligne, invisible depuis le
# navigateur qui l'avait déjà.
#
# « no-cache » ne veut pas dire « ne garde rien » : le navigateur garde le
# fichier et redemande simplement au serveur s'il a changé. La réponse ordinaire
# est un 304 vide — un aller-retour, pas un téléchargement.
COQUE = {
    "/", "/index.html", "/app.js", "/styles.css", "/polices.css",
    "/manifeste.json", "/agent.js",
}

# Les icônes ne changent pas : les redemander à chaque démarrage serait payer un
# aller-retour pour rien, sur des connexions qui n'en ont pas les moyens.
UN_AN = 60 * 60 * 24 * 365


def duree_de_cache(chemin: str) -> str | None:
    """L'en-tête pour ce chemin, ou None si on ne se prononce pas.

    Une fonction plutôt qu'un bloc dans le middleware : c'est la règle
    elle-même qu'on veut pouvoir interroger, depuis un test comme depuis le
    serveur, sans avoir à fabriquer une requête.
    """
    if chemin.startswith("/api/") or chemin.startswith("/admin/"):
        # Un classeur ou un quota servis depuis le cache feraient réapparaître
        # du travail effacé. L'agent de service le refuse déjà de son côté ;
        # rien ne dit que le navigateur en fasse autant.
        return "no-store"
    if chemin in COQUE:
        return "no-cache"
    if chemin.startswith("/icones/"):
        return f"public, max-age={UN_AN}, immutable"
    return None


@app.middleware("http")
async def poser_la_duree_de_cache(requete: Request, suite):
    reponse = await suite(requete)
    entete = duree_de_cache(requete.url.path)
    if entete:
        reponse.headers["Cache-Control"] = entete
    return reponse


app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
