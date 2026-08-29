"""Le compte : inscription, connexion, mot de passe oublié — et ce qu'on refuse.

Une porte d'entrée est le seul endroit du produit où un défaut ne se voit pas :
tant qu'elle s'ouvre pour l'élève, personne ne remarque qu'elle s'ouvre aussi
pour les autres. D'où ces tests, écrits contre les façons connues de la forcer :

  1. essayer mille mots de passe (bridé par adresse ET par machine) ;
  2. lire les mots de passe dans une base volée (scrypt, jamais de clair) ;
  3. se servir des formulaires comme d'un annuaire (« cette adresse existe-t-elle ? ») ;
  4. deviner le code de réinitialisation, le rejouer, l'utiliser périmé ;
  5. inonder la boîte mail d'un camarade en redemandant des codes ;
  6. entrer sans rien, en appelant l'API directement.

Et contre celle qui n'est pas une attaque mais un vrai dégât : le lien de
reprise d'un camarade, neuf caractères, qui ouvrirait son cours.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config, store

from conftest import MDP_DE_TEST, adresse_neuve, code_recu, connecter, inscrire


# --- L'inscription ----------------------------------------------------------

def test_s_inscrire_ouvre_le_compte_et_connecte_dans_la_foulee(visiteur: TestClient):
    """Redemander de se connecter juste après s'être inscrit, c'est un
    formulaire pour rien."""
    email = adresse_neuve()
    reponse = visiteur.post("/api/auth/inscription", json={
        "email": email, "mot_de_passe": MDP_DE_TEST, "prenom": "Lina", "niveau": "4e"})
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["connecte"] is True and corps["email"] == email
    assert corps["prenom"] == "Lina" and corps["niveau"] == "4e"
    assert visiteur.get("/api/auth/moi").json()["connecte"] is True
    assert visiteur.post("/api/session").status_code == 200


def test_le_prenom_et_la_classe_reviennent_a_chaque_visite(visiteur: TestClient):
    """La page s'en sert : le prénom nomme la carte, la classe règle le niveau
    des contrôles. Les redemander à chaque fois serait les collecter pour rien."""
    email = inscrire(visiteur)
    visiteur.post("/api/auth/sortir")
    connecter(visiteur, email)
    moi = visiteur.get("/api/auth/moi").json()
    assert moi["prenom"] == "Lina" and moi["niveau"] == "4e"


def test_deux_fois_la_meme_adresse_ne_fait_pas_deux_comptes(visiteur: TestClient):
    """C'est le seul endroit du produit qui révèle qu'une adresse existe, et on
    ne peut pas y couper : accepter en silence donnerait un deuxième compte
    fantôme à qui se réinscrit par erreur, et son travail resterait dans l'autre."""
    email = inscrire(visiteur)
    encore = visiteur.post("/api/auth/inscription",
                           json={"email": email, "mot_de_passe": MDP_DE_TEST})
    assert encore.status_code == 400
    corps = encore.json()
    assert corps["genre"] == "existe", "la page doit pouvoir emmener au bon volet"
    assert "connecte-toi" in corps["message"].lower()


def test_la_casse_et_les_espaces_ne_font_pas_deux_comptes(visiteur: TestClient):
    """« Lina@Exemple.Test » et « lina@exemple.test » sont la même élève."""
    email = inscrire(visiteur)
    visiteur.post("/api/auth/sortir")
    assert connecter(visiteur, "  " + email.upper() + " ").status_code == 200


@pytest.mark.parametrize("faible, pourquoi", [
    ("court", "moins de huit caractères"),
    ("1234567", "sept chiffres"),
    ("motdepasse", "dans la liste des trop courants"),
    ("password", "idem, en anglais"),
])
def test_un_mot_de_passe_trop_faible_est_refuse(visiteur: TestClient, faible, pourquoi):
    reponse = visiteur.post("/api/auth/inscription",
                            json={"email": adresse_neuve(), "mot_de_passe": faible})
    assert reponse.status_code == 400, pourquoi
    assert reponse.json()["genre"] == "mdp"


def test_on_refuse_son_propre_prenom_et_sa_propre_adresse(visiteur: TestClient):
    """Ce sont les deux premières choses qu'un attaquant essaie, et les deux
    premières qu'un élève choisit."""
    assert visiteur.post("/api/auth/inscription", json={
        "email": "lina.martin@exemple.test", "mot_de_passe": "linalinalina",
        "prenom": "Lina"}).status_code == 400
    assert visiteur.post("/api/auth/inscription", json={
        "email": "lina.martin@exemple.test",
        "mot_de_passe": "lina.martin99"}).status_code == 400


def test_pas_de_regle_de_composition_absurde(visiteur: TestClient):
    """« Une majuscule, un chiffre, un caractère spécial » pousse à
    « Motdepasse1! », que tout dictionnaire connaît, et à écrire le mot de passe
    sur un cahier. Une phrase longue en minuscules doit passer."""
    reponse = visiteur.post("/api/auth/inscription", json={
        "email": adresse_neuve(), "mot_de_passe": "trois mots colles ensemble"})
    assert reponse.status_code == 200, reponse.text


@pytest.mark.parametrize("mauvaise", ["", "pas-une-adresse", "a@b", "@exemple.test",
                                      "deux@@exemple.test", "espace @exemple.test"])
def test_une_adresse_qui_n_en_est_pas_une_est_refusee(visiteur: TestClient, mauvaise: str):
    assert visiteur.post("/api/auth/inscription",
                         json={"email": mauvaise,
                               "mot_de_passe": MDP_DE_TEST}).status_code == 400


# --- La connexion -----------------------------------------------------------

def test_se_connecter_et_ressortir(visiteur: TestClient):
    email = inscrire(visiteur)
    visiteur.post("/api/auth/sortir")
    assert visiteur.get("/api/auth/moi").json()["connecte"] is False
    assert visiteur.post("/api/session").status_code == 401

    assert connecter(visiteur, email).status_code == 200
    assert visiteur.get("/api/auth/moi").json()["email"] == email


def test_un_mauvais_mot_de_passe_n_ouvre_rien(visiteur: TestClient):
    email = inscrire(visiteur)
    visiteur.post("/api/auth/sortir")
    refus = connecter(visiteur, email, "pas-le-bon-du-tout")
    assert refus.status_code == 400
    assert visiteur.get("/api/auth/moi").json()["connecte"] is False


def test_le_formulaire_de_connexion_n_est_pas_un_annuaire(visiteur: TestClient):
    """Adresse inconnue et mauvais mot de passe doivent donner exactement la
    même réponse. Deux messages différents, et le formulaire dit qui est
    inscrit — sur un site d'élèves, ça se paie cher."""
    email = inscrire(visiteur)
    visiteur.post("/api/auth/sortir")
    connu = connecter(visiteur, email, "mauvais-mot-de-passe")
    inconnu = connecter(visiteur, adresse_neuve(), "mauvais-mot-de-passe")
    assert connu.status_code == inconnu.status_code == 400
    assert connu.json() == inconnu.json()


def test_sans_compte_toutes_les_portes_sont_fermees(visiteur: TestClient):
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


def test_on_ne_peut_pas_essayer_mille_mots_de_passe(visiteur: TestClient, monkeypatch):
    """Un élève qui cherche son mot de passe en fait trois ; un programme en
    fait mille. Sans blocage, huit caractères tombent en une nuit."""
    monkeypatch.setattr(config, "MAX_TENTATIVES", 4)
    email = inscrire(visiteur)
    visiteur.post("/api/auth/sortir")
    with store.curseur() as cur:
        cur.execute("DELETE FROM tentatives")

    for _ in range(4):
        assert connecter(visiteur, email, "faux").status_code == 400
    bloque = connecter(visiteur, email, "faux")
    assert bloque.json()["genre"] == "cadence"
    assert bloque.json()["attendre"] > 0, "on doit dire combien de temps attendre"
    # Et même le bon mot de passe est refusé pendant le blocage.
    assert connecter(visiteur, email).status_code == 400


def test_le_blocage_vaut_aussi_pour_la_machine(visiteur: TestClient, monkeypatch):
    """Bloquer par adresse ne dit rien de celui qui essaie « azerty123 » sur
    mille adresses différentes — l'attaque qui marche vraiment."""
    monkeypatch.setattr(config, "MAX_TENTATIVES", 4)
    with store.curseur() as cur:
        cur.execute("DELETE FROM tentatives")
    for _ in range(4):
        connecter(visiteur, adresse_neuve(), "azerty123")
    bloque = connecter(visiteur, adresse_neuve(), "azerty123")
    assert bloque.status_code == 400 and bloque.json()["genre"] == "cadence"


def test_une_connexion_reussie_efface_l_ardoise(visiteur: TestClient):
    """Sinon trois fautes de frappe étalées sur la semaine finiraient par
    bloquer un élève qui n'a rien fait de mal."""
    email = inscrire(visiteur)
    visiteur.post("/api/auth/sortir")
    connecter(visiteur, email, "faux")
    connecter(visiteur, email, "faux")
    assert connecter(visiteur, email).status_code == 200
    with store.curseur() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM tentatives WHERE email = ?", (email,))
        assert int(cur.fetchone()["n"]) == 0


# --- Mot de passe oublié ----------------------------------------------------

def test_oublier_son_mot_de_passe_et_en_choisir_un_autre(visiteur: TestClient):
    email = inscrire(visiteur)
    visiteur.post("/api/auth/sortir")
    code = code_recu(visiteur, email)
    assert re.fullmatch(r"\d{6}", code), "le code doit faire six chiffres"

    change = visiteur.post("/api/auth/reinitialiser", json={
        "email": email, "code": code, "mot_de_passe": "un-tout-autre-secret"})
    assert change.status_code == 200, change.text
    # On est connecté dans la foulée, et l'ancien mot de passe ne marche plus.
    assert visiteur.get("/api/auth/moi").json()["email"] == email
    visiteur.post("/api/auth/sortir")
    assert connecter(visiteur, email, MDP_DE_TEST).status_code == 400
    assert connecter(visiteur, email, "un-tout-autre-secret").status_code == 200


def test_changer_de_mot_de_passe_ferme_les_autres_connexions(visiteur: TestClient):
    """C'est le geste qu'on fait quand on croit que quelqu'un a pris le compte.
    S'il restait connecté ailleurs, le geste ne servirait à rien."""
    from fastapi.testclient import TestClient as Client
    from app.main import app

    email = inscrire(visiteur)
    autre = Client(app)  # le téléphone resté chez le voleur
    assert connecter(autre, email).status_code == 200
    assert autre.get("/api/auth/moi").json()["connecte"] is True

    code = code_recu(visiteur, email)
    visiteur.post("/api/auth/reinitialiser",
                  json={"email": email, "code": code, "mot_de_passe": "un-tout-autre-secret"})
    assert autre.get("/api/auth/moi").json()["connecte"] is False


def test_le_formulaire_d_oubli_n_est_pas_un_annuaire(visiteur: TestClient):
    """Demander un code pour une adresse inconnue et pour une adresse inscrite
    doit donner la même réponse. Rien ne part pour l'adresse inconnue."""
    connue = inscrire(visiteur)
    with store.curseur() as cur:  # on efface la cadence, pas le compte
        cur.execute("DELETE FROM demandes_code WHERE email = ?", (connue,))

    inconnue = adresse_neuve()
    a = visiteur.post("/api/auth/oubli", json={"email": connue})
    b = visiteur.post("/api/auth/oubli", json={"email": inconnue})
    assert a.status_code == b.status_code == 200
    assert set(a.json()) - {"code_demonstration"} == set(b.json()) - {"code_demonstration"}
    # Aucun code n'est gardé pour une adresse sans compte : rien à deviner.
    with store.curseur() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM codes WHERE email = ?", (inconnue,))
        assert int(cur.fetchone()["n"]) == 0


def test_le_code_ne_se_devine_pas(visiteur: TestClient):
    email = inscrire(visiteur)
    vrai = code_recu(visiteur, email)
    faux = f"{(int(vrai) + 1) % 1_000_000:06d}"
    for _ in range(config.MAX_ESSAIS_CODE):
        assert visiteur.post("/api/auth/reinitialiser", json={
            "email": email, "code": faux,
            "mot_de_passe": "un-tout-autre-secret"}).status_code == 400
    # Le code est brûlé : même le vrai ne marche plus.
    assert visiteur.post("/api/auth/reinitialiser", json={
        "email": email, "code": vrai,
        "mot_de_passe": "un-tout-autre-secret"}).status_code == 400


def test_un_code_ne_sert_qu_une_fois(visiteur: TestClient):
    email = inscrire(visiteur)
    code = code_recu(visiteur, email)
    assert visiteur.post("/api/auth/reinitialiser", json={
        "email": email, "code": code, "mot_de_passe": "un-tout-autre-secret"}).status_code == 200
    rejoue = visiteur.post("/api/auth/reinitialiser", json={
        "email": email, "code": code, "mot_de_passe": "encore-un-autre-secret"})
    assert rejoue.status_code == 400, "un code rejoué doit être refusé"


def test_un_code_perime_ne_marche_plus(visiteur: TestClient):
    email = inscrire(visiteur)
    code = code_recu(visiteur, email)
    passe = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(timespec="seconds")
    with store.curseur() as cur:
        cur.execute("UPDATE codes SET expire_le = ? WHERE email = ?", (passe, email))
    refus = visiteur.post("/api/auth/reinitialiser", json={
        "email": email, "code": code, "mot_de_passe": "un-tout-autre-secret"})
    assert refus.status_code == 400
    assert "expir" in refus.json()["message"].lower()


def test_le_nouveau_mot_de_passe_passe_les_memes_regles(visiteur: TestClient):
    """Sinon « mot de passe oublié » devient la porte de service par laquelle on
    remet « 12345678 »."""
    email = inscrire(visiteur)
    code = code_recu(visiteur, email)
    refus = visiteur.post("/api/auth/reinitialiser",
                          json={"email": email, "code": code, "mot_de_passe": "12345678"})
    assert refus.status_code == 400 and refus.json()["genre"] == "mdp"


def test_on_ne_peut_pas_inonder_une_boite_mail(visiteur: TestClient):
    """Sans cadence, le formulaire devient un moyen d'envoyer cent messages à
    l'adresse d'un camarade — et de faire blacklister notre expéditeur."""
    email = inscrire(visiteur)
    assert visiteur.post("/api/auth/oubli", json={"email": email}).status_code == 200
    trop_tot = visiteur.post("/api/auth/oubli", json={"email": email})
    assert trop_tot.status_code == 400
    assert trop_tot.json()["attendre"] > 0, "on doit dire combien de temps attendre"


def test_on_ne_peut_pas_arroser_mille_adresses_depuis_une_machine(visiteur: TestClient,
                                                                  monkeypatch):
    """La limite par adresse protège une boîte mail. Elle ne dit rien de celui
    qui demande un code pour mille adresses différentes."""
    monkeypatch.setattr(config, "MAX_CODES_PAR_HEURE_ET_SOURCE", 3)
    with store.curseur() as cur:
        cur.execute("DELETE FROM demandes_code")
    for _ in range(3):
        assert visiteur.post("/api/auth/oubli",
                             json={"email": adresse_neuve()}).status_code == 200
    refus = visiteur.post("/api/auth/oubli", json={"email": adresse_neuve()})
    assert refus.status_code == 400
    assert "appareil" in refus.json()["message"]


def test_l_entete_x_forwarded_for_n_est_pas_cru_sur_parole(monkeypatch):
    """Sinon la limite par machine se contourne en changeant un en-tête. On ne
    la lit que si l'exploitant affirme qu'un proxy la pose."""
    from app.main import _source

    class FausseRequete:
        headers = {"x-forwarded-for": "1.2.3.4"}
        client = type("C", (), {"host": "10.0.0.1"})()

    monkeypatch.setattr(config, "PROXY_DE_CONFIANCE", False)
    assert _source(FausseRequete()) == "10.0.0.1"
    monkeypatch.setattr(config, "PROXY_DE_CONFIANCE", True)
    assert _source(FausseRequete()) == "1.2.3.4"


# --- Ce qui appartient à qui ------------------------------------------------

def test_le_lien_de_reprise_d_un_camarade_n_ouvre_rien(client: TestClient, visiteur: TestClient):
    """Un identifiant de séance fait neuf caractères et voyage dans une URL
    qu'on se passe. Il ne doit pas suffire à lire le cours de quelqu'un."""
    sienne = client.post("/api/session").json()["session_id"]
    inscrire(visiteur)  # un autre élève
    assert visiteur.get(f"/api/session/{sienne}").status_code == 404
    assert visiteur.post("/api/session/contexte",
                         json={"session_id": sienne, "matiere": "espagnol"}).status_code == 404
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

def test_le_mot_de_passe_n_est_jamais_stocke_en_clair(visiteur: TestClient):
    """Une base volée ne doit rendre aucun mot de passe. Et deux élèves qui
    choisissent le même doivent avoir deux empreintes différentes : sans sel,
    une seule table pré-calculée les casse tous d'un coup."""
    a, b = adresse_neuve(), adresse_neuve()
    for email in (a, b):
        visiteur.post("/api/auth/inscription",
                      json={"email": email, "mot_de_passe": MDP_DE_TEST})
        visiteur.post("/api/auth/sortir")
    with store.curseur() as cur:
        cur.execute("SELECT email, mot_de_passe FROM comptes WHERE email IN (?, ?)", (a, b))
        empreintes = {ligne["email"]: ligne["mot_de_passe"] for ligne in cur.fetchall()}
    assert MDP_DE_TEST not in empreintes[a]
    assert empreintes[a].startswith("scrypt$"), "on attend scrypt, pas un SHA nu"
    assert empreintes[a] != empreintes[b], "pas de sel : une table pré-calculée les casse tous"


def test_ni_le_code_ni_le_jeton_ne_sont_stockes_en_clair(visiteur: TestClient):
    email = inscrire(visiteur)
    code = code_recu(visiteur, email)
    with store.curseur() as cur:
        cur.execute("SELECT empreinte FROM codes WHERE email = ?", (email,))
        assert cur.fetchone()["empreinte"] != code

    jeton = visiteur.cookies.get("cb_jeton")
    assert jeton, "le jeton doit être posé en cookie"
    with store.curseur() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM jetons WHERE empreinte = ?", (jeton,))
        assert int(cur.fetchone()["n"]) == 0, "le jeton est stocké tel quel"


def test_le_jeton_ne_se_lit_pas_depuis_la_page(visiteur: TestClient):
    """HttpOnly : une faille d'affichage dans une fiche ne doit pas donner le
    compte. C'est aussi pourquoi le jeton ne va pas dans localStorage."""
    reponse = visiteur.post("/api/auth/inscription",
                            json={"email": adresse_neuve(), "mot_de_passe": MDP_DE_TEST})
    pose = reponse.headers["set-cookie"].lower()
    assert "httponly" in pose
    assert "samesite=lax" in pose


def test_en_production_le_code_ne_revient_jamais_dans_la_reponse(monkeypatch,
                                                                 visiteur: TestClient):
    """CB_AUTH_CODE_EN_CLAIR ouvre la porte en grand : il ne doit exister qu'en
    démonstration, et le code ne doit alors sortir que là."""
    email = inscrire(visiteur)
    monkeypatch.setattr(config, "AUTH_CODE_EN_CLAIR", False)
    corps = visiteur.post("/api/auth/oubli", json={"email": email}).json()
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
    """Pas de lien à cliquer : un message qui contient un lien apprend aux
    élèves à cliquer sur les liens de compte reçus par mail."""
    from app import courrier

    message = courrier._message("eleve@exemple.test", "123456")
    corps = "\n".join(part.get_content() for part in message.walk()
                      if part.get_content_type().startswith("text/"))
    assert "123456" in corps
    assert "http://" not in corps and "https://" not in corps
    assert str(config.DUREE_CODE_MINUTES) in corps


def test_une_adresse_inconnue_coute_le_meme_temps_qu_une_adresse_inscrite():
    """Sans le hachage à vide, une adresse inexistante répondrait en une
    microseconde et une adresse inscrite en cinquante millisecondes : le
    chronomètre suffirait à faire l'annuaire."""
    import time

    empreinte = store._hacher_mot_de_passe(MDP_DE_TEST)

    def duree(action) -> float:
        depart = time.perf_counter()
        action()
        return time.perf_counter() - depart

    connu = duree(lambda: store._mot_de_passe_correspond("faux", empreinte))
    inconnu = duree(lambda: store._mot_de_passe_correspond("faux", store._leurre()))
    # Même ordre de grandeur : on ne cherche pas l'égalité à la microseconde,
    # on cherche l'absence du facteur mille qui trahirait tout.
    assert 0.2 < inconnu / connu < 5, f"connu {connu:.4f}s, inconnu {inconnu:.4f}s"
