"""Le classeur côté serveur.

Un compte promet qu'on retrouve ses affaires ailleurs. Jusqu'ici le classeur
vivait dans le seul navigateur où il avait été fait : changer d'appareil, ou
vider ses données, le perdait entièrement — sans message d'erreur, sans rien.
Pour un élève, ce n'est pas un bug, c'est un produit qui a perdu son travail.

Le modèle est volontairement pauvre : une séance entière, la plus récente gagne.
Ces tests tiennent surtout ce qui, dans une synchronisation, se casse en silence.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app import schemas, store
from app.main import app
from tests.conftest import inscrire

SEANCE = {"v": 1, "matiere": "histoire-geographie", "chapitres": [{"titre": "1914"}]}


def _pousser(c: TestClient, seance_id: str, contenu: dict, maj_le: str):
    return c.put(f"/api/classeur/{seance_id}",
                 json={"contenu": json.dumps(contenu), "maj_le": maj_le})


def test_un_autre_appareil_retrouve_le_classeur(client, session):
    """Le cœur du sujet : ce qui a été fait sur un téléphone doit se retrouver
    ailleurs, puisque c'est ce qu'un compte laisse croire."""
    assert _pousser(client, session, SEANCE, "2026-09-01T10:00:00+00:00").json()["range"]

    seances = client.get("/api/classeur").json()["seances"]
    assert [s["id"] for s in seances] == [session]
    assert json.loads(seances[0]["contenu"])["matiere"] == "histoire-geographie"


def test_la_plus_recente_gagne(client, session):
    _pousser(client, session, {"v": 1, "note": "matin"}, "2026-09-01T08:00:00+00:00")
    _pousser(client, session, {"v": 1, "note": "soir"}, "2026-09-01T20:00:00+00:00")

    contenu = json.loads(client.get("/api/classeur").json()["seances"][0]["contenu"])
    assert contenu["note"] == "soir"


def test_une_version_plus_ancienne_ne_recouvre_rien(client, session):
    """Le cas qui perd du travail sans prévenir : un appareil resté ouvert sur
    une vieille version pousse en retard et écrase ce qui a été fait depuis."""
    _pousser(client, session, {"v": 1, "note": "récent"}, "2026-09-01T20:00:00+00:00")
    retard = _pousser(client, session, {"v": 1, "note": "périmé"}, "2026-09-01T08:00:00+00:00")

    assert retard.json()["range"] is False, "le refus doit être annoncé au navigateur"
    contenu = json.loads(client.get("/api/classeur").json()["seances"][0]["contenu"])
    assert contenu["note"] == "récent"


def test_on_ne_redemande_que_ce_qui_a_bougé(client, session):
    """Sans « depuis », un élève retéléchargerait tout son trimestre à chaque
    ouverture — sur un téléphone en 4G, ça se voit."""
    _pousser(client, session, SEANCE, "2026-09-01T08:00:00+00:00")
    reponse = client.get("/api/classeur", params={"depuis": "2026-09-01T09:00:00+00:00"})
    assert reponse.json()["seances"] == []


def test_l_horodatage_de_reprise_vient_du_serveur(client):
    """Si le navigateur prenait le sien, une horloge de téléphone en avance
    ferait sauter toutes les séances rangées entre les deux."""
    assert client.get("/api/classeur").json()["maintenant"]


def test_le_classeur_d_un_autre_est_hors_de_portee(session, photo_factice):
    """Deux comptes, deux classeurs. C'est la séparation la plus élémentaire, et
    celle dont l'absence ne se voit jamais en s'en servant normalement."""
    with TestClient(app) as lina:
        inscrire(lina)
        seance = lina.post("/api/session").json()["session_id"]
        _pousser(lina, seance, SEANCE, "2026-09-01T10:00:00+00:00")

    with TestClient(app) as sacha:
        inscrire(sacha)
        assert sacha.get("/api/classeur").json()["seances"] == []
        # Et il ne peut pas non plus écrire dans la séance de Lina.
        assert _pousser(sacha, seance, {"v": 1}, "2026-09-02T10:00:00+00:00").status_code == 404


def test_une_seance_effacee_ne_revient_pas(client, session):
    """Effacée sur le téléphone, elle doit partir du serveur : sinon la
    synchronisation suivante la fait réapparaître, et l'élève ne comprend pas."""
    _pousser(client, session, SEANCE, "2026-09-01T10:00:00+00:00")
    assert client.delete(f"/api/classeur/{session}").status_code == 200
    assert client.get("/api/classeur").json()["seances"] == []


def test_effacer_son_compte_efface_le_classeur(client, session):
    """Le classeur contient le cours transcrit d'un élève identifié. Le droit à
    l'effacement porte dessus, et il ne doit rien laisser derrière."""
    _pousser(client, session, SEANCE, "2026-09-01T10:00:00+00:00")
    compte = client.get("/api/auth/moi").json()["compte"]
    assert store.compter_seances(compte) == 1

    client.post("/api/auth/supprimer")
    assert store.compter_seances(compte) == 0


def test_une_seance_sans_fin_est_refusee(client, session):
    """Même leçon que pour le cours : c'est le navigateur qui décide de la
    taille, donc c'est ici qu'on la borne."""
    enorme = json.dumps({"v": 1, "x": "z" * schemas.MAX_CAR_SEANCE})
    reponse = client.put(f"/api/classeur/{session}",
                         json={"contenu": enorme, "maj_le": "2026-09-01T10:00:00+00:00"})
    assert reponse.status_code == 422


def test_un_contenu_illisible_est_refuse(client, session):
    """Le serveur garde le contenu sans le relire, mais il vérifie que c'est du
    JSON : sinon la séance ne reviendrait qu'au moment de la relire ailleurs,
    trop tard pour prévenir qui que ce soit."""
    reponse = client.put(f"/api/classeur/{session}",
                         json={"contenu": "{ceci n'est pas du json",
                               "maj_le": "2026-09-01T10:00:00+00:00"})
    assert reponse.status_code == 400


def test_le_classeur_est_ferme_aux_visiteurs(visiteur):
    assert visiteur.get("/api/classeur").status_code == 401


# --- L'agenda ----------------------------------------------------------------
#
# Ce n'est pas une séance, mais c'est l'élève qui l'écrit : les dates de ses
# contrôles à venir. Le perdre en changeant de téléphone ferait exactement la
# même impression que perdre un cours.

AGENDA = [{"id": "rv-1", "date": "2026-09-15", "matiere": "maths", "note": "chapitre 2"}]


def test_l_agenda_suit_l_eleve(client):
    assert client.put("/api/agenda", json={
        "contenu": json.dumps(AGENDA), "maj_le": "2026-09-01T10:00:00+00:00"}).json()["range"]

    agenda = client.get("/api/classeur").json()["agenda"]
    assert json.loads(agenda["contenu"])[0]["note"] == "chapitre 2"


def test_l_agenda_le_plus_recent_gagne(client):
    client.put("/api/agenda", json={"contenu": json.dumps(AGENDA),
                                    "maj_le": "2026-09-01T20:00:00+00:00"})
    retard = client.put("/api/agenda", json={"contenu": json.dumps([]),
                                             "maj_le": "2026-09-01T08:00:00+00:00"})
    assert retard.json()["range"] is False
    assert json.loads(client.get("/api/classeur").json()["agenda"]["contenu"]) == AGENDA


def test_l_agenda_part_avec_le_compte(client):
    client.put("/api/agenda", json={"contenu": json.dumps(AGENDA),
                                    "maj_le": "2026-09-01T10:00:00+00:00"})
    compte = client.get("/api/auth/moi").json()["compte"]
    client.post("/api/auth/supprimer")
    assert store.lire_agenda(compte) is None


def test_l_agenda_d_un_autre_est_hors_de_portee():
    with TestClient(app) as lina:
        inscrire(lina)
        lina.put("/api/agenda", json={"contenu": json.dumps(AGENDA),
                                      "maj_le": "2026-09-01T10:00:00+00:00"})
    with TestClient(app) as sacha:
        inscrire(sacha)
        assert sacha.get("/api/classeur").json()["agenda"] is None


def test_une_horloge_de_telephone_faussee_ne_fait_pas_sauter_de_seance(client, session):
    """Le piège de toute synchronisation : filtrer « ce qui a bougé depuis »
    avec l'horodatage du navigateur. Un téléphone qui retarde de deux jours
    range des séances datées d'avant-hier ; l'appareil suivant demande « depuis
    hier » et ne les voit jamais. Personne ne s'en aperçoit — le travail a
    simplement disparu.

    D'où deux horodatages : maj_le (navigateur) départage les versions, range_le
    (serveur) répond à « qu'est-ce qui a bougé ».
    """
    repere = client.get("/api/classeur").json()["maintenant"]

    # Une séance rangée MAINTENANT, mais datée par un navigateur qui retarde.
    _pousser(client, session, SEANCE, "2020-01-01T00:00:00+00:00")

    seances = client.get("/api/classeur", params={"depuis": repere}).json()["seances"]
    assert [s["id"] for s in seances] == [session], (
        "la séance a été sautée : le filtre suit l'horloge du téléphone"
    )


def test_deux_seances_rangees_dans_la_meme_seconde_redescendent_toutes_les_deux(client):
    """À la seconde près, la seconde séance porterait le même repère que la
    première et ne repasserait jamais le filtre « depuis »."""
    ids = []
    for _ in range(2):
        seance = client.post("/api/session").json()["session_id"]
        ids.append(seance)
        _pousser(client, seance, SEANCE, "2026-09-01T10:00:00+00:00")

    seances = client.get("/api/classeur").json()["seances"]
    assert sorted(s["id"] for s in seances) == sorted(ids)
