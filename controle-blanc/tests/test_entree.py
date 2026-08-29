"""L'entrée par adresse mail : ce qu'elle laisse passer, et ce qu'elle refuse.

Une porte d'entrée est le seul endroit du produit où un défaut ne se voit pas :
tant qu'elle s'ouvre pour l'élève, personne ne remarque qu'elle s'ouvre aussi
pour les autres. D'où ces tests, écrits contre les cinq façons connues de la
forcer :

  1. deviner le code à six chiffres (bridé à cinq essais) ;
  2. réutiliser un code déjà servi, ou périmé ;
  3. se servir du formulaire comme d'un annuaire (« cette adresse existe-t-elle ? ») ;
  4. inonder la boîte mail d'un camarade en redemandant des codes ;
  5. entrer sans code du tout, en appelant l'API directement.

Et contre celle qui n'est pas une attaque mais un vrai dégât : le lien de
reprise d'un camarade, neuf caractères, qui ouvrirait son cours.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config, store

from conftest import adresse_neuve, entrer


# --- Le parcours normal -----------------------------------------------------

def test_une_adresse_un_code_et_on_est_entre(visiteur: TestClient):
    email = adresse_neuve()
    demande = visiteur.post("/api/auth/code", json={"email": email})
    assert demande.status_code == 200
    corps = demande.json()
    assert corps["envoye"] is True
    assert corps["expire_dans_minutes"] == config.DUREE_CODE_MINUTES

    code = corps["code_demonstration"]
    assert re.fullmatch(r"\d{6}", code), "le code doit faire six chiffres"

    entree = visiteur.post("/api/auth/entrer", json={"email": email, "code": code})
    assert entree.status_code == 200
    assert entree.json()["email"] == email

    moi = visiteur.get("/api/auth/moi").json()
    assert moi["connecte"] is True and moi["email"] == email


def test_le_compte_est_le_meme_a_la_deuxieme_entree(visiteur: TestClient):
    """Sinon l'élève qui se reconnecte repart d'un classeur vide."""
    email = adresse_neuve()
    entrer(visiteur, email)
    premier = visiteur.get("/api/auth/moi").json()["compte"]
    visiteur.post("/api/auth/sortir")
    entrer(visiteur, email)
    assert visiteur.get("/api/auth/moi").json()["compte"] == premier


def test_la_casse_et_les_espaces_ne_font_pas_deux_comptes(visiteur: TestClient):
    """« Lina@Exemple.Test » et « lina@exemple.test » sont la même élève. Deux
    comptes, ce serait son travail coupé en deux sans qu'elle comprenne."""
    base = adresse_neuve()
    entrer(visiteur, base)
    premier = visiteur.get("/api/auth/moi").json()["compte"]
    visiteur.post("/api/auth/sortir")
    entrer(visiteur, "  " + base.upper() + " ")
    assert visiteur.get("/api/auth/moi").json()["compte"] == premier


def test_sortir_ferme_vraiment(visiteur: TestClient):
    entrer(visiteur)
    visiteur.post("/api/auth/sortir")
    assert visiteur.get("/api/auth/moi").json()["connecte"] is False
    assert visiteur.post("/api/session").status_code == 401


# --- Ce qui doit être refusé ------------------------------------------------

def test_sans_entrer_toutes_les_portes_sont_fermees(visiteur: TestClient):
    assert visiteur.post("/api/session").status_code == 401
    assert visiteur.get("/api/session/nimporte").status_code == 401
    assert visiteur.post("/api/evenement",
                         json={"session_id": "x", "type": "ouverture"}).status_code == 401
    assert visiteur.post("/api/fiche/generale",
                         json={"session_id": "x", "chapitres": []}).status_code == 401


def test_toute_route_api_est_gardee_sauf_la_configuration_et_l_entree():
    """Ce test vaut plus que les précédents : il attrape la route qu'on ajoutera
    dans six mois en oubliant la dépendance. Il énumère l'application au lieu de
    faire confiance à une liste écrite à la main."""
    from app.main import app, compte_connecte

    libres = {"/api/config"}
    oubliees = []
    for route in app.routes:
        chemin = getattr(route, "path", "")
        if not chemin.startswith("/api/") or chemin.startswith("/api/auth/") or chemin in libres:
            continue
        gardiens = [d.call for d in getattr(route, "dependant", None).dependencies] \
            if getattr(route, "dependant", None) else []
        if compte_connecte not in gardiens:
            oubliees.append(chemin)
    assert not oubliees, f"routes ouvertes à tout le monde : {oubliees}"


def test_le_code_ne_se_devine_pas(visiteur: TestClient):
    email = adresse_neuve()
    vrai = visiteur.post("/api/auth/code", json={"email": email}).json()["code_demonstration"]
    faux = f"{(int(vrai) + 1) % 1_000_000:06d}"

    for essai in range(config.MAX_ESSAIS_CODE):
        reponse = visiteur.post("/api/auth/entrer", json={"email": email, "code": faux})
        assert reponse.status_code == 400, "un code faux ne doit jamais ouvrir"

    # Le code est brûlé : même le vrai ne marche plus.
    apres = visiteur.post("/api/auth/entrer", json={"email": email, "code": vrai})
    assert apres.status_code == 400
    assert visiteur.get("/api/auth/moi").json()["connecte"] is False


def test_un_code_ne_sert_qu_une_fois(visiteur: TestClient):
    email = adresse_neuve()
    code = visiteur.post("/api/auth/code", json={"email": email}).json()["code_demonstration"]
    assert visiteur.post("/api/auth/entrer", json={"email": email, "code": code}).status_code == 200
    visiteur.post("/api/auth/sortir")
    rejoue = visiteur.post("/api/auth/entrer", json={"email": email, "code": code})
    assert rejoue.status_code == 400, "un code rejoué doit être refusé"


def test_un_code_perime_ne_marche_plus(visiteur: TestClient):
    email = adresse_neuve()
    code = visiteur.post("/api/auth/code", json={"email": email}).json()["code_demonstration"]
    passe = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(timespec="seconds")
    with store.curseur() as cur:
        cur.execute("UPDATE codes SET expire_le = ? WHERE email = ?", (passe, email))
    reponse = visiteur.post("/api/auth/entrer", json={"email": email, "code": code})
    assert reponse.status_code == 400
    assert "expir" in reponse.json()["message"].lower()


def test_on_ne_peut_pas_inonder_une_boite_mail(visiteur: TestClient):
    """Sans cadence, le formulaire devient un moyen d'envoyer cent messages à
    l'adresse d'un camarade — et de faire blacklister notre expéditeur."""
    email = adresse_neuve()
    assert visiteur.post("/api/auth/code", json={"email": email}).status_code == 200
    trop_tot = visiteur.post("/api/auth/code", json={"email": email})
    assert trop_tot.status_code == 400
    assert trop_tot.json()["attendre"] > 0, "on doit dire combien de temps attendre"


def test_le_formulaire_n_est_pas_un_annuaire(visiteur: TestClient):
    """Demander un code pour une adresse inconnue et pour une adresse inscrite
    doit donner exactement la même réponse. Sinon on sait qui est inscrit."""
    connue = adresse_neuve()
    entrer(visiteur, connue)
    with store.curseur() as cur:  # on efface la cadence, pas le compte
        cur.execute("DELETE FROM demandes_code WHERE email = ?", (connue,))
        cur.execute("DELETE FROM codes WHERE email = ?", (connue,))

    a = visiteur.post("/api/auth/code", json={"email": connue})
    b = visiteur.post("/api/auth/code", json={"email": adresse_neuve()})
    assert a.status_code == b.status_code == 200
    assert set(a.json()) - {"code_demonstration"} == set(b.json()) - {"code_demonstration"}


@pytest.mark.parametrize("mauvaise", ["", "pas-une-adresse", "a@b", "@exemple.test",
                                      "deux@@exemple.test", "espace @exemple.test"])
def test_une_adresse_qui_n_en_est_pas_une_est_refusee(visiteur: TestClient, mauvaise: str):
    reponse = visiteur.post("/api/auth/code", json={"email": mauvaise})
    assert reponse.status_code == 400


# --- Ce qui appartient à qui ------------------------------------------------

def test_le_lien_de_reprise_d_un_camarade_n_ouvre_rien(client: TestClient, visiteur: TestClient):
    """Un identifiant de séance fait neuf caractères et voyage dans une URL
    qu'on se passe. Il ne doit pas suffire à lire le cours de quelqu'un."""
    sienne = client.post("/api/session").json()["session_id"]
    entrer(visiteur)  # un autre élève
    assert visiteur.get(f"/api/session/{sienne}").status_code == 404
    assert visiteur.post("/api/session/contexte",
                         json={"session_id": sienne, "matiere": "espagnol"}).status_code == 404
    # Le propriétaire, lui, y accède toujours.
    assert client.get(f"/api/session/{sienne}").status_code == 200


def test_une_seance_d_avant_les_comptes_revient_a_qui_la_rouvre(client: TestClient):
    """La base contient des séances créées quand il n'y avait pas de compte.
    Les jeter ferait perdre leur travail aux premiers testeurs ; les laisser
    ouvertes à tous serait pire. Le premier qui rouvre se les approprie."""
    orpheline = client.post("/api/session").json()["session_id"]
    with store.curseur() as cur:
        cur.execute("UPDATE sessions SET compte_id = NULL WHERE id = ?", (orpheline,))
    assert client.get(f"/api/session/{orpheline}").status_code == 200
    with store.curseur() as cur:
        cur.execute("SELECT compte_id FROM sessions WHERE id = ?", (orpheline,))
        assert cur.fetchone()["compte_id"] is not None


def test_supprimer_son_compte_efface_tout(client: TestClient):
    """Le droit à l'effacement doit être un bouton, pas un courrier à écrire."""
    seance = client.post("/api/session").json()["session_id"]
    compte = client.get("/api/auth/moi").json()["compte"]
    assert client.post("/api/auth/supprimer").status_code == 200

    with store.curseur() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM comptes WHERE id = ?", (compte,))
        assert int(cur.fetchone()["n"]) == 0
        cur.execute("SELECT COUNT(*) AS n FROM sessions WHERE id = ?", (seance,))
        assert int(cur.fetchone()["n"]) == 0
    assert client.get("/api/auth/moi").json()["connecte"] is False


# --- Ce qu'on n'écrit jamais en clair ---------------------------------------

def test_ni_le_code_ni_le_jeton_ne_sont_stockes_en_clair(visiteur: TestClient):
    """Une base volée ne doit ouvrir aucune boîte mail ni aucun compte."""
    email = adresse_neuve()
    code = visiteur.post("/api/auth/code", json={"email": email}).json()["code_demonstration"]
    with store.curseur() as cur:
        cur.execute("SELECT empreinte FROM codes WHERE email = ?", (email,))
        assert cur.fetchone()["empreinte"] != code

    visiteur.post("/api/auth/entrer", json={"email": email, "code": code})
    jeton = visiteur.cookies.get("cb_jeton")
    assert jeton, "le jeton doit être posé en cookie"
    with store.curseur() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM jetons WHERE empreinte = ?", (jeton,))
        assert int(cur.fetchone()["n"]) == 0, "le jeton est stocké tel quel"


def test_le_jeton_ne_se_lit_pas_depuis_la_page(visiteur: TestClient):
    """HttpOnly : une faille d'affichage dans une fiche ne doit pas donner le
    compte. C'est aussi pourquoi le jeton ne va pas dans localStorage."""
    email = adresse_neuve()
    code = visiteur.post("/api/auth/code", json={"email": email}).json()["code_demonstration"]
    reponse = visiteur.post("/api/auth/entrer", json={"email": email, "code": code})
    pose = reponse.headers["set-cookie"].lower()
    assert "httponly" in pose
    assert "samesite=lax" in pose


def test_en_production_le_code_ne_revient_jamais_dans_la_reponse(monkeypatch,
                                                                 visiteur: TestClient):
    """CB_AUTH_CODE_EN_CLAIR ouvre la porte en grand : il ne doit exister qu'en
    démonstration, et le code ne doit alors sortir que là."""
    monkeypatch.setattr(config, "AUTH_CODE_EN_CLAIR", False)
    corps = visiteur.post("/api/auth/code", json={"email": adresse_neuve()}).json()
    assert "code_demonstration" not in corps
    assert not any(re.fullmatch(r"\d{6}", str(v)) for v in corps.values())


def test_un_serveur_de_courrier_desactive_le_mode_en_clair(monkeypatch):
    """Le garde-fou vit dans config.py ; on vérifie qu'il tient encore."""
    import importlib

    monkeypatch.setenv("CB_SMTP_HOTE", "smtp.exemple.test")
    monkeypatch.setenv("CB_AUTH_CODE_EN_CLAIR", "1")
    recharge = importlib.reload(config)
    try:
        assert recharge.AUTH_CODE_EN_CLAIR is False
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_le_courrier_ne_contient_que_le_code_et_ce_qu_il_faut_savoir():
    """Pas de lien à cliquer : un message qui contient un lien d'entrée apprend
    aux élèves à cliquer sur les liens d'entrée reçus par mail."""
    from app import courrier

    message = courrier._message("eleve@exemple.test", "123456")
    corps = "\n".join(part.get_content() for part in message.walk()
                      if part.get_content_type().startswith("text/"))
    assert "123456" in corps
    assert "http://" not in corps and "https://" not in corps
    assert str(config.DUREE_CODE_MINUTES) in corps


def test_on_ne_peut_pas_arroser_mille_adresses_depuis_une_machine(visiteur: TestClient,
                                                                  monkeypatch):
    """La limite par adresse protège une boîte mail. Elle ne dit rien de celui
    qui demande un code pour mille adresses différentes : ce sont nos courriers
    qui partent, et notre expéditeur qui finit sur une liste noire."""
    monkeypatch.setattr(config, "MAX_CODES_PAR_HEURE_ET_SOURCE", 3)
    with store.curseur() as cur:  # on part d'une machine « neuve »
        cur.execute("DELETE FROM demandes_code")

    for _ in range(3):
        assert visiteur.post("/api/auth/code",
                             json={"email": adresse_neuve()}).status_code == 200
    refus = visiteur.post("/api/auth/code", json={"email": adresse_neuve()})
    assert refus.status_code == 400
    assert "appareil" in refus.json()["message"]


def test_l_entete_x_forwarded_for_n_est_pas_cru_sur_parole(monkeypatch, visiteur: TestClient):
    """Sinon la limite par machine se contourne en changeant un en-tête. On ne
    la lit que si l'exploitant affirme qu'un proxy la pose (CB_PROXY_DE_CONFIANCE)."""
    from app.main import _source

    class FausseRequete:
        headers = {"x-forwarded-for": "1.2.3.4"}
        client = type("C", (), {"host": "10.0.0.1"})()

    monkeypatch.setattr(config, "PROXY_DE_CONFIANCE", False)
    assert _source(FausseRequete()) == "10.0.0.1"
    monkeypatch.setattr(config, "PROXY_DE_CONFIANCE", True)
    assert _source(FausseRequete()) == "1.2.3.4"
