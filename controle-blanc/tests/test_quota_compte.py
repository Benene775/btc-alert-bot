"""Les plafonds du mois, par compte.

Les limites par séance ne tenaient rien : ouvrir une nouvelle séance les
remettait à zéro, ce qui est gratuit et se fait en un clic. C'est ce que
vérifie surtout ce fichier — le reste (les messages, l'affichage) découle.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app import config, store
from app.main import app
from tests.conftest import inscrire


def _analyser(client: TestClient, session: str, photo: bytes, nombre: int = 2):
    fichiers = [("photos", (f"p{i}.png", photo, "image/png")) for i in range(nombre)]
    return client.post(
        "/api/analyse",
        data={"session_id": session, "niveau": "3e", "matiere": "histoire-geographie"},
        files=fichiers,
    )


@pytest.fixture()
def large(monkeypatch):
    """Les limites par jour et par séance écartées, pour que seul le mois parle."""
    monkeypatch.setitem(config.QUOTAS, "analyse", {"jour": 999, "session": 999})
    monkeypatch.setitem(config.QUOTAS, "fiche_generale", {"jour": 999, "session": 999})


def test_le_plafond_du_mois_survit_a_une_nouvelle_seance(client, photo_factice, large,
                                                         monkeypatch):
    """Le cœur du sujet : quatre pages autorisées, réparties sur deux séances de
    deux photos, et la troisième séance est refusée bien qu'elle soit neuve."""
    monkeypatch.setitem(config.QUOTAS_MOIS, "analyse", 4)

    premiere = client.post("/api/session").json()["session_id"]
    assert _analyser(client, premiere, photo_factice).status_code == 200

    seconde = client.post("/api/session").json()["session_id"]
    assert _analyser(client, seconde, photo_factice).status_code == 200

    troisieme = client.post("/api/session").json()["session_id"]
    refus = _analyser(client, troisieme, photo_factice)
    assert refus.status_code == 429, "une séance neuve remettait le compteur à zéro"
    assert refus.json()["portee"] == "mois"


def test_deux_comptes_ne_partagent_pas_le_compteur(photo_factice, large, monkeypatch):
    """Le plafond suit le compte, pas la machine ni le jour."""
    monkeypatch.setitem(config.QUOTAS_MOIS, "analyse", 2)  # deux pages : un seul envoi

    with TestClient(app) as lina:
        inscrire(lina)
        session = lina.post("/api/session").json()["session_id"]
        assert _analyser(lina, session, photo_factice).status_code == 200
        assert _analyser(lina, session, photo_factice).status_code == 429

    with TestClient(app) as sacha:
        inscrire(sacha)
        session = sacha.post("/api/session").json()["session_id"]
        assert _analyser(sacha, session, photo_factice).status_code == 200, (
            "le compte voisin héritait d'un plafond déjà épuisé"
        )



def test_le_mois_passe_avant_le_jour(client, session, photo_factice, monkeypatch):
    """Si les deux limites tombent, c'est le mois qu'on annonce : « reviens
    demain » serait faux, et l'élève reviendrait se cogner à la même porte."""
    monkeypatch.setitem(config.QUOTAS_MOIS, "analyse", 2)
    monkeypatch.setitem(config.QUOTAS, "analyse", {"jour": 2, "session": 2})

    assert _analyser(client, session, photo_factice).status_code == 200
    refus = _analyser(client, session, photo_factice)
    assert refus.status_code == 429
    assert refus.json()["portee"] == "mois"


def test_aucun_message_du_mois_ne_promet_demain():
    """Le mois ne se rattrape pas le lendemain. Un message qui le laisse croire
    est un mensonge, et le genre de détail qui fait écrire au service client."""
    for (action, portee), texte in store.MESSAGES_QUOTA.items():
        if portee != "mois":
            continue
        assert "demain" not in texte.lower(), f"{action} promet demain"
        assert "1er" in texte, f"{action} ne dit pas quand ça repart"


def test_toutes_les_actions_ont_un_message_du_mois():
    """Sans message, l'élève reçoit « Tu as atteint ta limite du mois. » — vrai,
    mais sec, et sans dire que son travail est toujours là."""
    for action in config.QUOTAS_MOIS:
        assert (action, "mois") in store.MESSAGES_QUOTA, action


def test_la_page_perso_lit_ce_qu_il_reste(client, session, photo_factice, large,
                                          monkeypatch):
    monkeypatch.setitem(config.QUOTAS_MOIS, "analyse", 6)

    avant = client.get("/api/compte/quotas").json()
    assert avant["quotas"]["analyse"] == {"plafond": 6, "restant": 6}

    _analyser(client, session, photo_factice, nombre=2)

    apres = client.get("/api/compte/quotas").json()
    assert apres["quotas"]["analyse"]["restant"] == 4, "deux pages doivent en retirer deux"


def test_ce_qu_il_reste_est_ferme_aux_visiteurs(visiteur):
    """Le compteur dit qui a fait quoi : il ne se lit pas sans être entré."""
    assert visiteur.get("/api/compte/quotas").status_code == 401


def test_etat_de_session_annonce_aussi_le_mois(client, session):
    """La réponse existante gagne restant_mois : le client n'a pas à deviner
    laquelle des trois limites va tomber."""
    quotas = client.get(f"/api/session/{session}").json()["quotas"]
    for action in config.QUOTAS_MOIS:
        assert "restant_mois" in quotas[action], action


# --- Ce que la page perso en montre ------------------------------------------
#
# Le serveur tient les plafonds ; le navigateur ne fait que les afficher. Ces
# tests-là tiennent le câblage, qui est silencieux quand il casse : une tuile
# sans compteur ne lève aucune erreur, elle se contente de ne rien dire.

from pathlib import Path  # noqa: E402

WEB = Path(__file__).resolve().parent.parent / "web"
PAGE = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPT = (WEB / "app.js").read_text(encoding="utf-8")
STYLE = (WEB / "styles.css").read_text(encoding="utf-8")


def test_chaque_outil_a_sa_ligne_de_reste():
    for outil in ("controle", "fiche"):
        assert f'id="reste-{outil}"' in PAGE, outil


def test_la_ligne_de_reste_a_sa_place_dans_la_tuile():
    """La tuile est une grille nommée. Une zone déclarée dans .outil-reste mais
    absente de grid-template-areas fait tomber la ligne n'importe où, sans
    erreur — le genre de casse qu'on ne voit qu'à l'œil."""
    zones = STYLE[STYLE.index(".outil {"):].split("}")[0]
    assert "reste reste" in zones, "grid-template-areas n'a pas de zone « reste »"
    bloc = STYLE[STYLE.index(".outil-reste {"):].split("}")[0]
    assert "grid-area: reste" in bloc


def test_la_page_perso_redemande_le_compteur_a_chaque_passage():
    """Une génération vient peut-être de le faire baisser. Peint une fois au
    démarrage, il mentirait le reste de la séance."""
    bloc = SCRIPT[SCRIPT.index("function dessinerEspace()"):]
    bloc = bloc[: bloc.index("\n}")]
    assert "rafraichirQuotas()" in bloc


def test_le_compteur_affiche_ne_bloque_pas_la_tuile():
    """Ce chiffre peut être en retard : l'élève a pu générer depuis un autre
    appareil. C'est le serveur qui refuse, avec la vraie raison — la tuile, elle,
    reste cliquable, sinon un compteur périmé enfermerait dehors."""
    bloc = SCRIPT[SCRIPT.index("function peindreQuotas()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "disabled" not in bloc
    assert "hidden = true" in bloc, "sans quota connu, il faut n'afficher rien"


def test_les_tuiles_pointent_vers_de_vraies_actions():
    """ACTIONS_OUTILS traduit un nom de tuile en nom de quota. Une faute de
    frappe ici n'affiche simplement jamais rien."""
    bloc = SCRIPT[SCRIPT.index("const ACTIONS_OUTILS = {"):]
    bloc = bloc[: bloc.index("}")]
    for action in ("controle", "fiche_generale"):
        assert f"'{action}'" in bloc, action
        assert action in config.QUOTAS_MOIS, action


def test_une_analyse_coute_ce_qu_elle_porte_de_pages(client, session, photo_factice,
                                                     large, monkeypatch):
    """Le point de départ : compter les appels facturait pareil quatre pages et
    cinquante, alors que les photos font 55 à 79 % du coût d'un parcours."""
    monkeypatch.setitem(config.QUOTAS_MOIS, "analyse", 20)

    _analyser(client, session, photo_factice, nombre=2)
    apres_deux = client.get("/api/compte/quotas").json()["quotas"]["analyse"]["restant"]

    _analyser(client, session, photo_factice, nombre=8)
    apres_huit = client.get("/api/compte/quotas").json()["quotas"]["analyse"]["restant"]

    assert apres_deux == 18
    assert apres_huit == 10, "un envoi de huit pages doit coûter quatre fois celui de deux"


def test_un_envoi_qui_depasserait_est_refuse_avant_l_appel(client, session, photo_factice,
                                                           large, monkeypatch):
    """Vérifier après coup laisserait passer le dépassement — et le facturerait.
    Trois pages libres, un envoi de huit : refusé, et rien n'est consommé."""
    monkeypatch.setitem(config.QUOTAS_MOIS, "analyse", 3)

    refus = _analyser(client, session, photo_factice, nombre=8)
    assert refus.status_code == 429
    assert refus.json()["portee"] == "mois"
    reste = client.get("/api/compte/quotas").json()["quotas"]["analyse"]["restant"]
    assert reste == 3, "un envoi refusé ne doit rien consommer"

    # Et ce qui tient encore passe : la limite porte sur les pages, pas sur le geste.
    assert _analyser(client, session, photo_factice, nombre=3).status_code == 200


def test_la_demonstration_annonce_les_memes_plafonds_que_le_produit():
    """La démonstration autonome tient ses propres compteurs, faute de serveur.
    S'ils s'écartent de config.py, elle ment sur ce que l'abonnement donne — à
    l'endroit précis où on la montre à quelqu'un pour le convaincre."""
    import json

    source = (Path(__file__).resolve().parent.parent
              / "outils" / "demonstration" / "faux-serveur.js").read_text(encoding="utf-8")
    brut = source[source.index("const PLAFONDS_MOIS = {"):]
    brut = brut[brut.index("{"): brut.index("}") + 1]
    plafonds = json.loads(re.sub(r"(\w+):", r'"\1":', brut).replace("'", '"'))
    assert plafonds == config.QUOTAS_MOIS


def test_les_pages_du_mois_et_les_fiches_du_mois_tombent_juste():
    """Un élève doit sortir du mois sans reste d'un côté ni de l'autre.

    Le quota d'analyse se compte en pages, celui des fiches en fiches : si les
    deux ne tombent pas sur le même nombre de cours, l'élève se retrouve soit
    avec des pages qu'aucune fiche ne peut exploiter, soit avec des fiches sans
    cours à leur donner. Les trois nombres sont liés — changer l'un oblige à
    regarder les deux autres, et c'est ce que ce test rend impossible d'oublier.
    """
    cours_possibles = config.QUOTAS_MOIS["analyse"] // config.MAX_PHOTOS_PAR_ANALYSE
    assert cours_possibles == config.QUOTAS_MOIS["fiche_generale"], (
        f"{config.QUOTAS_MOIS['analyse']} pages à {config.MAX_PHOTOS_PAR_ANALYSE} par cours "
        f"font {cours_possibles} cours, pour {config.QUOTAS_MOIS['fiche_generale']} fiches"
    )
    assert cours_possibles == config.QUOTAS_MOIS["controle"], "et autant de contrôles blancs"


def test_une_seance_ne_depasse_pas_un_cours():
    """La fiche se fait sur ce que la séance contient. Si une séance pouvait
    accumuler douze envois de huit pages, la fiche porterait sur un trimestre —
    et le plafond par cours ne voudrait plus rien dire."""
    assert config.QUOTAS["analyse"]["session"] == config.MAX_PHOTOS_PAR_ANALYSE
