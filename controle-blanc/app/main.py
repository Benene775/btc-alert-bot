"""API de Repère.

Une seule page web côté élève ; ici, les quelques routes qu'elle appelle.

Trois principes de découpage :
- Le navigateur garde le cours, les réponses et les fiches. Le serveur n'en voit
  rien, et n'en garde rien.
- Sauf le corrigé du contrôle en cours : si on l'envoyait avec les questions,
  n'importe quel élève le lirait dans les outils de développement avant de répondre.
- On entre par son adresse mail et un code reçu dessus. Pas de mot de passe :
  il n'y a donc aucun mot de passe d'élève à se faire voler. Toutes les routes
  /api sauf /api/config et /api/auth/* exigent d'être entré.
"""

from __future__ import annotations

import html
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Cookie, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, courrier, formats, llm, store
from .schemas import (
    ContexteSession,
    DemandeCode,
    DemandeControle,
    DemandeCorrection,
    DemandeEntree,
    DemandeFiche,
    DemandeFicheCiblee,
    Evenement,
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
            "AUCUN SERVEUR DE COURRIER : les codes d'entrée partent dans ces journaux. "
            "Définir CB_SMTP_HOTE pour les envoyer vraiment."
        )
    if config.AUTH_CODE_EN_CLAIR:
        logger.warning(
            "CB_AUTH_CODE_EN_CLAIR : le code est renvoyé dans la réponse HTTP. "
            "N'importe qui entre avec n'importe quelle adresse — démonstration seulement."
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


# --- L'entrée : une adresse mail, un code reçu dessus -----------------------
#
# Pas de mot de passe. L'élève donne son adresse, reçoit six chiffres, les
# recopie. Ce qu'on garde de lui tient en une ligne : son adresse. Le code et le
# jeton ne sont stockés que hachés (voir store.py).
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


@app.post("/api/auth/code")
def demander_code(corps: DemandeCode, request: Request) -> dict[str, Any]:
    """Envoie un code. Répond pareil que l'adresse soit connue ou non : sinon ce
    formulaire devient un moyen de savoir qui est inscrit."""
    email = store.normaliser_email(corps.email)
    code = store.preparer_code(email, _source(request))
    try:
        courrier.envoyer_code(email, code)
    except courrier.ErreurCourrier as erreur:
        raise HTTPException(status_code=502, detail=str(erreur)) from erreur
    reponse: dict[str, Any] = {
        "envoye": True,
        "expire_dans_minutes": config.DUREE_CODE_MINUTES,
        "renvoi_dans_secondes": config.DELAI_ENTRE_CODES_SECONDES,
    }
    if config.AUTH_CODE_EN_CLAIR:
        # Démonstration seulement : voir le garde-fou dans config.py.
        reponse["code_demonstration"] = code
    return reponse


@app.post("/api/auth/entrer")
def entrer(corps: DemandeEntree, request: Request) -> JSONResponse:
    email = store.normaliser_email(corps.email)
    compte_id = store.verifier_code(email, corps.code)
    jeton = store.ouvrir_jeton(compte_id)
    reponse = JSONResponse({"connecte": True, "email": email, "compte": compte_id})
    _poser_cookie(reponse, jeton, request)
    return reponse


@app.get("/api/auth/moi")
def qui_suis_je(cb_jeton: str | None = Cookie(default=None)) -> dict[str, Any]:
    compte = store.compte_du_jeton(cb_jeton)
    if compte is None:
        return {"connecte": False}
    return {"connecte": True, "email": compte["email"], "compte": compte["id"]}


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
    store.verifier_quota(session_id, "analyse")

    if not photos:
        raise HTTPException(status_code=400, detail="aucune photo reçue")
    if len(photos) > config.MAX_PHOTOS_PAR_ANALYSE:
        raise HTTPException(
            status_code=400,
            detail=f"{config.MAX_PHOTOS_PAR_ANALYSE} photos au maximum en une fois",
        )

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
    store.enregistrer_usage(session_id, "analyse", usage)
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
        f"<td class='n'>{d['cout_usd']} $</td></tr>"
        for d in m["detail_cout"]
    ) or "<tr><td colspan='3' class='n'>Aucun appel facturé.</td></tr>"

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
<h2>Coût</h2>
<table>
 {couts}
 {ligne("Total", f"{m['cout_usd_total']} $", f"{m['cout_usd_par_session']} $ par session")}
</table>
<h2>Questions signalées</h2>
<ul>{liste_signalees}</ul>
"""
    return HTMLResponse(page_html)


app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
