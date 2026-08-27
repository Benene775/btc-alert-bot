"""Le parcours complet, dans l'ordre du cahier des charges, plus les garde-fous.

Ce qui est vérifié ici, ce sont les promesses produit :
  - le corrigé ne part jamais dans le navigateur avant que l'élève ait répondu ;
  - aucune note, nulle part ;
  - le bouton « cette question me semble fausse » existe et remonte ;
  - les quotas tiennent côté serveur ;
  - les trois métriques du test se calculent.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app import config, store


def _analyser(client: TestClient, session: str, photo: bytes, nombre: int = 3):
    fichiers = [("photos", (f"p{i}.png", photo, "image/png")) for i in range(nombre)]
    return client.post(
        "/api/analyse",
        data={"session_id": session, "niveau": "3e", "matiere": "histoire-geographie"},
        files=fichiers,
    )


def test_configuration_exposee(client: TestClient):
    corps = client.get("/api/config").json()
    assert corps["mode_demonstration"] is True
    assert any(m["cle"] == "histoire-geographie" for m in corps["matieres"])
    # Le sélecteur de niveau existe, même si on ne teste qu'un niveau en v1.
    assert any(n["cle"] == "3e" for n in corps["niveaux"])


def test_session_donne_un_lien_de_reprise(client: TestClient):
    corps = client.post("/api/session").json()
    assert corps["session_id"]
    assert corps["lien_de_reprise"].startswith("https://exemple.test/?s=")


def test_etape_1_photos_illisibles_signalees_tout_de_suite(client, session, photo_factice):
    reponse = _analyser(client, session, photo_factice, nombre=3)
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["chapitres"], "l'analyse doit renvoyer au moins un chapitre"
    illisibles = [p for p in corps["photos"] if not p["lisible"]]
    assert illisibles, "une photo illisible doit être signalée"
    assert illisibles[0]["remarque"], "et dire quoi refaire"


def test_etape_2_le_perimetre_arrive_avec_ses_notions(client, session, photo_factice):
    chapitre = _analyser(client, session, photo_factice).json()["chapitres"][0]
    assert chapitre["titre"]
    assert len(chapitre["notions"]) >= 3
    assert chapitre["transcription"]


def test_etape_3_fiche_generale(client, session, photo_factice):
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    fiche = client.post(
        "/api/fiche/generale",
        json={"session_id": session, "niveau": "3e", "chapitres": chapitres},
    ).json()
    assert fiche["type"] == "generale"
    assert fiche["sections"]
    assert all(s["a_retenir"] for s in fiche["sections"])


def test_etape_4_le_corrige_ne_part_pas_dans_le_navigateur(client, session, photo_factice):
    """Le point le plus important : les réponses attendues restent côté serveur."""
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    controle = client.post(
        "/api/controle",
        json={
            "session_id": session,
            "niveau": "3e",
            "matiere": "histoire-geographie",
            "chapitres": chapitres,
        },
    ).json()

    assert controle["questions"], "un contrôle sans question n'a pas de sens"
    for question in controle["questions"]:
        assert "points_attendus" not in question
        assert "ou_dans_le_cours" not in question
        assert question["enonce"]
        assert question["notion"]
    # …mais le serveur, lui, l'a bien gardé.
    corrige = store.lire_corrige(controle["controle_id"], session)
    assert corrige and corrige["questions"][0]["points_attendus"]


def test_etape_4_format_reel_de_la_matiere(client, session, photo_factice):
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    controle = client.post(
        "/api/controle",
        json={"session_id": session, "niveau": "3e", "matiere": "histoire-geographie",
              "chapitres": chapitres},
    ).json()
    assert controle["matiere"].startswith("Histoire-Géographie")
    assert controle["duree_minutes"] >= 10
    # Un vrai sujet a des parties, et au moins une question s'appuie sur un document.
    assert any(q["partie"] for q in controle["questions"])
    assert any(q["document"] for q in controle["questions"])


def test_etape_5_correction_renvoie_au_cours_de_l_eleve(client, session, photo_factice):
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    controle = client.post(
        "/api/controle",
        json={"session_id": session, "niveau": "3e", "matiere": "histoire-geographie",
              "chapitres": chapitres},
    ).json()
    reponses = [{"numero": q["numero"], "texte": "", "secondes": 30} for q in controle["questions"]]

    correction = client.post(
        "/api/correction",
        json={
            "session_id": session,
            "controle_id": controle["controle_id"],
            "niveau": "3e",
            "chapitres": chapitres,
            "reponses": reponses,
            "numeros_signales": [],
        },
    ).json()

    assert len(correction["reponses"]) == len(controle["questions"])
    for ligne in correction["reponses"]:
        assert ligne["statut"] in {"acquis", "partiel", "a_revoir"}
        assert ligne["ou_dans_ton_cours"], "chaque correction doit dire où relire"
        assert "enonce" in ligne and "ta_reponse" in ligne
    assert 0 < len(correction["notions_fragiles"]) <= 3


def test_aucune_note_nulle_part(client, session, photo_factice):
    """« Pas de note prédictive » : on le vérifie sur tout ce qui sort de l'API."""
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    controle = client.post(
        "/api/controle",
        json={"session_id": session, "niveau": "3e", "matiere": "histoire-geographie",
              "chapitres": chapitres},
    ).json()
    correction = client.post(
        "/api/correction",
        json={
            "session_id": session,
            "controle_id": controle["controle_id"],
            "niveau": "3e",
            "chapitres": chapitres,
            "reponses": [{"numero": q["numero"], "texte": "une réponse"} for q in controle["questions"]],
            "numeros_signales": [],
        },
    ).text

    interdits = [r"\b\d{1,2}\s*/\s*20\b", r"\bnote\s*:", r"\bscore\b", r"\b\d{1,3}\s*%"]
    for motif in interdits:
        assert not re.search(motif, correction, re.IGNORECASE), f"note détectée : {motif}"


def test_question_signalee_ne_compte_pas_contre_l_eleve(client, session, photo_factice):
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    controle = client.post(
        "/api/controle",
        json={"session_id": session, "niveau": "3e", "matiere": "histoire-geographie",
              "chapitres": chapitres},
    ).json()
    premiere = controle["questions"][0]["numero"]

    signalement = client.post(
        "/api/signalement",
        json={"session_id": session, "controle_id": controle["controle_id"],
              "numero": premiere, "enonce": "…", "motif": "pas dans mon cours"},
    )
    assert signalement.status_code == 200
    assert "compter" in signalement.json()["message"] or "comptera" in signalement.json()["message"]

    correction = client.post(
        "/api/correction",
        json={
            "session_id": session,
            "controle_id": controle["controle_id"],
            "niveau": "3e",
            "chapitres": chapitres,
            "reponses": [{"numero": q["numero"], "texte": ""} for q in controle["questions"]],
            "numeros_signales": [premiere],
        },
    ).json()

    ligne = next(l for l in correction["reponses"] if l["numero"] == premiere)
    assert ligne["signalee"] is True
    assert ligne["statut"] == "acquis", "une question signalée ne pénalise pas"
    notion_signalee = controle["questions"][0]["notion"]
    assert notion_signalee not in [n["notion"] for n in correction["notions_fragiles"]], (
        "une notion issue d'une question signalée ne doit pas être retenue comme fragile"
    )


def test_etape_7_second_controle_pose_d_autres_questions(client, session, photo_factice):
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    premier = client.post(
        "/api/controle",
        json={"session_id": session, "niveau": "3e", "matiere": "histoire-geographie",
              "chapitres": chapitres},
    ).json()
    enonces = [q["enonce"] for q in premier["questions"]]

    second = client.post(
        "/api/controle",
        json={
            "session_id": session,
            "niveau": "3e",
            "matiere": "histoire-geographie",
            "chapitres": chapitres,
            "notions_ciblees": ["La notion de guerre totale"],
            "enonces_deja_poses": enonces,
        },
    ).json()

    assert second["controle_id"] != premier["controle_id"]
    assert not set(q["enonce"] for q in second["questions"]) & set(enonces)


def test_fiche_ciblee_est_plus_courte_que_la_generale(client, session, photo_factice):
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    generale = client.post(
        "/api/fiche/generale",
        json={"session_id": session, "niveau": "3e", "chapitres": chapitres},
    ).json()
    ciblee = client.post(
        "/api/fiche/ciblee",
        json={
            "session_id": session,
            "niveau": "3e",
            "chapitres": chapitres,
            "notions": [{"notion": "La notion de guerre totale", "chapitre": "…", "pourquoi": "…"}],
        },
    ).json()
    assert ciblee["type"] == "ciblee"
    assert ciblee["duree_lecture_minutes"] <= generale["duree_lecture_minutes"]


def test_quota_controle_tient_cote_serveur(client, session, photo_factice):
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    corps = {"session_id": session, "niveau": "3e", "matiere": "histoire-geographie",
             "chapitres": chapitres}

    for _ in range(config.QUOTAS["controle"]["jour"]):
        assert client.post("/api/controle", json=corps).status_code == 200

    refuse = client.post("/api/controle", json=corps)
    assert refuse.status_code == 429
    corps_refus = refuse.json()
    assert corps_refus["erreur"] == "quota"
    assert "demain" in corps_refus["message"].lower()


def test_session_inconnue_refusee(client: TestClient):
    reponse = client.post(
        "/api/fiche/generale",
        json={"session_id": "n-existe-pas", "niveau": "3e", "chapitres": []},
    )
    assert reponse.status_code == 404


def test_photo_non_image_refusee(client, session):
    reponse = client.post(
        "/api/analyse",
        data={"session_id": session, "niveau": "3e", "matiere": ""},
        files=[("photos", ("cours.pdf", b"%PDF-1.4", "application/pdf"))],
    )
    assert reponse.status_code == 400


def test_metriques_du_test(client, photo_factice):
    session = client.post("/api/session").json()["session_id"]
    client.post("/api/evenement", json={"session_id": session, "type": "chemin_choisi",
                                        "details": {"chemin": "teste"}})
    chapitres = _analyser(client, session, photo_factice).json()["chapitres"]
    client.post("/api/fiche/generale",
                json={"session_id": session, "niveau": "3e", "chapitres": chapitres})
    client.post("/api/fiche/ciblee",
                json={"session_id": session, "niveau": "3e", "chapitres": chapitres,
                      "notions": [{"notion": "n", "chapitre": "c", "pourquoi": "p"}]})

    page = client.get("/admin/metriques", params={"token": "jeton-de-test"})
    assert page.status_code == 200
    assert "Revenus le lendemain" in page.text
    assert "la seule qui compte vraiment" in page.text

    mesures = store.metriques()
    assert mesures["ouvertures"] >= 1
    assert mesures["deux_fiches_ou_plus"] >= 1          # métrique 2
    assert "teste" in mesures["par_chemin"]             # répartition de l'étape 3


def test_tableau_de_bord_protege(client: TestClient):
    assert client.get("/admin/metriques").status_code == 403
    assert client.get("/admin/metriques", params={"token": "faux"}).status_code == 403


def test_la_page_est_servie(client: TestClient):
    page = client.get("/")
    assert page.status_code == 200
    assert "Passe le contrôle" in page.text
    assert client.get("/app.js").status_code == 200
    assert client.get("/styles.css").status_code == 200


def test_le_tableau_de_bord_echappe_ce_qu_ecrivent_les_eleves(client, session, photo_factice):
    """Le motif de signalement est du texte libre écrit par un élève : il ne doit
    pas pouvoir s'exécuter dans le navigateur du professeur."""
    client.post(
        "/api/signalement",
        json={
            "session_id": session,
            "controle_id": "peu-importe",
            "numero": 1,
            "enonce": "<img src=x onerror=alert(1)>",
            "motif": "<script>alert('xss')</script>",
        },
    )
    page = client.get("/admin/metriques", params={"token": "jeton-de-test"}).text
    # Les chevrons sont neutralisés : le texte s'affiche, il ne s'exécute pas.
    assert "<script>alert" not in page
    assert "<img src=x" not in page
    assert "&lt;script&gt;" in page
    assert "&lt;img src=x" in page


def test_details_d_evenement_bornes(client, session):
    client.post(
        "/api/evenement",
        json={"session_id": session, "type": "chemin_choisi",
              "details": {"chemin": "teste", "bourrage": "x" * 5000}},
    )
    with store.curseur() as cur:
        cur.execute(
            "SELECT details FROM evenements WHERE session_id = ? AND type = 'chemin_choisi'",
            (session,),
        )
        stocke = cur.fetchone()["details"]
    assert len(stocke) < 200
