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

import html
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Cookie, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, courrier, formats, llm, schemas, store
from .schemas import (
    Connexion,
    ContexteSession,
    DemandeCode,
    DemandeControle,
    DemandeCorrection,
    DemandeFiche,
    DemandeFicheCiblee,
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
    yield


app = FastAPI(title="Repère", docs_url=None, redoc_url=None, lifespan=cycle_de_vie)


@app.exception_handler(store.QuotaDepasse)
def gerer_quota(_: Request, exc: store.QuotaDepasse) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"erreur": "quota", "action": exc.action, "portee": exc.portee, "message": exc.message},
    )


@app.exception_handler(llm.ErreurModele)
def gerer_modele(_: Request, exc: llm.ErreurModele) -> JSONResponse:
    return JSONResponse(status_code=503, content={"erreur": "modele", "message": str(exc)})


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
    compte_id = store.inscrire(email, corps.mot_de_passe, corps.prenom, corps.niveau)
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
        "envoye": True,
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
    # une fois qu'on sait combien de photos il porte.
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

    # Les octets ne sortent pas d'ici : envoyés au modèle, jamais écrits sur disque.
    resultat, usage = llm.analyser_photos(images, formats.nom_niveau(niveau), matiere)
    store.enregistrer_usage(session_id, "analyse", usage, quantite=len(images))
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
    store.verifier_quota(corps.session_id, "fiche_generale")
    fiche, usage = llm.fiche_generale(
        _chapitres_en_dicts(corps.chapitres), formats.nom_niveau(corps.niveau)
    )
    store.enregistrer_usage(corps.session_id, "fiche_generale", usage)
    store.enregistrer_evenement(corps.session_id, "fiche_generee", {"type": "generale"})
    fiche["type"] = "generale"
    return fiche


@app.post("/api/fiche/ciblee")
def creer_fiche_ciblee(corps: DemandeFicheCiblee,
                       compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    _session_valide(corps.session_id, compte)
    store.verifier_quota(corps.session_id, "fiche_ciblee")
    fiche, usage = llm.fiche_ciblee(
        _chapitres_en_dicts(corps.chapitres),
        formats.nom_niveau(corps.niveau),
        [n.model_dump() for n in corps.notions],
    )
    store.enregistrer_usage(corps.session_id, "fiche_ciblee", usage)
    store.enregistrer_evenement(corps.session_id, "fiche_generee", {"type": "ciblee"})
    fiche["type"] = "ciblee"
    return fiche


# --- Étapes 4 et 7 : le contrôle blanc -------------------------------------

CHAMPS_CORRIGE = ("points_attendus", "ou_dans_le_cours")


@app.post("/api/controle")
def creer_controle(corps: DemandeControle,
                   compte: dict = Depends(compte_connecte)) -> dict[str, Any]:
    _session_valide(corps.session_id, compte)
    store.verifier_quota(corps.session_id, "controle")

    fmt = formats.format_matiere(corps.matiere)
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
        raise HTTPException(status_code=502, detail="contrôle vide")

    controle_id = uuid.uuid4().hex
    # Le corrigé reste ici. Le navigateur reçoit les énoncés, pas les réponses.
    store.enregistrer_corrige(
        controle_id,
        corps.session_id,
        {"questions": questions, "titre": brut.get("titre", "")},
    )
    store.enregistrer_usage(corps.session_id, "controle", usage)
    store.enregistrer_evenement(
        corps.session_id,
        "controle_commence",
        {"cible": bool(corps.notions_ciblees), "questions": len(questions)},
    )

    publiques = [
        {cle: valeur for cle, valeur in q.items() if cle not in CHAMPS_CORRIGE}
        for q in questions
    ]
    return {
        "controle_id": controle_id,
        "titre": brut.get("titre", "Contrôle blanc"),
        "consigne_generale": brut.get("consigne_generale", ""),
        "matiere": fmt["nom"],
        "duree_minutes": max(10, sum(int(q.get("duree_minutes", 5)) for q in questions)),
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

    # La correction n'est pas décomptée : elle fait partie du contrôle déjà compté.
    resultat, usage = llm.corriger(
        _chapitres_en_dicts(corps.chapitres),
        formats.nom_niveau(corps.niveau),
        corrige["questions"],
        reponses,
        signales,
    )
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
 body {{ font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 24px; max-width: 720px;
        background: #faf9f7; color: #1c1a17; }}
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
</style>
<h1>Repère — mesures du test</h1>
<h2>Les trois chiffres qui décident</h2>
<table>
 {ligne("Liens ouverts", m["ouvertures"], "sessions distinctes")}
 {ligne("2 fiches ou plus", m["deux_fiches_ou_plus"], "sans qu'on le demande")}
 {ligne("Revenus le lendemain", m["revenus_le_lendemain"], "la seule qui compte vraiment", classe="cle")}
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
 {ligne("Total", f"{m['cout_usd_total']} $", f"{m['cout_usd_par_session']} $ par séance")}
</table>
<h2>Coût par compte et par mois</h2>
<p class='n'>C'est ce chiffre-là qui décide du prix de l'abonnement — pas le pire cas,
qui suppose un élève saturant les quatre compteurs.</p>
<table>
 {ligne("Moyenne", f"{m['cout_usd_moyen_compte_mois']} $",
        "à comparer à ce qu'un abonnement encaisse net", classe="cle")}
 {ligne("Médiane", f"{m['cout_usd_median_compte_mois']} $", "l'élève ordinaire")}
 {ligne("Maximum", f"{m['cout_usd_max_compte_mois']} $", "le plus gourmand : les plafonds tiennent-ils ?")}
 {ligne("Mesuré sur", m["comptes_mois_mesures"], "couples compte × mois")}
</table>
<h2>Questions signalées</h2>
<ul>{liste_signalees}</ul>
"""
    return HTMLResponse(page_html)


app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
