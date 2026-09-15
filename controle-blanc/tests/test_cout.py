"""Chiffrer le coût pour de vrai.

Le produit enregistre déjà, à chaque appel, les compteurs de tokens que l'API
renvoie elle-même : il n'y a rien à estimer, seulement à lire. Ces tests tiennent
les trois choses qui rendaient cette lecture trompeuse — un tarif unique pour
tous les modèles, un coût rapporté à la séance plutôt qu'au compte, et un tarif
manquant qui se taisait.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config, store
from app.main import app
from tests.conftest import inscrire

RACINE = Path(__file__).resolve().parent.parent

TARIF = {"entree": 5.0, "sortie": 25.0, "cache_ecriture": 6.25, "cache_lecture": 0.50}


@pytest.fixture()
def usage_nu(monkeypatch):
    """Une base sans usages, et un seul tarif connu — pour que le calcul soit
    vérifiable à la main."""
    with store.curseur() as cur:
        cur.execute("DELETE FROM usages")
    monkeypatch.setattr(config, "PRIX_USD_PAR_MTOK_PAR_MODELE", {"opus": TARIF})
    monkeypatch.setattr(config, "PRIX_USD_PAR_MTOK", TARIF)
    yield
    with store.curseur() as cur:
        cur.execute("DELETE FROM usages")


def _poser(session_id: str, action: str, modele: str, entree=0, sortie=0, ce=0, cl=0,
           quantite=1):
    store.enregistrer_usage(session_id, action, {
        "tokens_entree": entree, "tokens_sortie": sortie,
        "cache_ecriture": ce, "cache_lecture": cl, "modele": modele,
    }, quantite=quantite)


def test_le_modele_qui_a_servi_est_enregistre(client, session, usage_nu):
    """Sans lui, comparer deux modèles est impossible : tout finit dans le même
    sac, au même tarif."""
    _poser(session, "analyse", "claude-opus-5", entree=1000, sortie=500)
    with store.curseur() as cur:
        cur.execute("SELECT modele FROM usages")
        assert cur.fetchone()["modele"] == "claude-opus-5"


def test_deux_modeles_ne_sont_pas_chiffres_au_meme_tarif(client, session, usage_nu,
                                                          monkeypatch):
    """Le cœur du banc d'essai : un essai Sonnet facturé au tarif Opus ne
    prouverait rien du tout."""
    monkeypatch.setattr(config, "PRIX_USD_PAR_MTOK_PAR_MODELE", {
        "opus": TARIF,
        "sonnet": {"entree": 1.0, "sortie": 5.0, "cache_ecriture": 1.25, "cache_lecture": 0.10},
    })
    _poser(session, "analyse", "claude-opus-5", entree=1_000_000)
    _poser(session, "analyse", "claude-sonnet-5", entree=1_000_000)

    par_modele = {d["modele"]: d["cout_usd"] for d in store.metriques()["detail_cout"]}
    assert par_modele["claude-opus-5"] == pytest.approx(5.0)
    assert par_modele["claude-sonnet-5"] == pytest.approx(1.0)


def test_un_tarif_manquant_ne_se_tait_pas(client, session, usage_nu):
    """Un modèle absent de la table est chiffré au tarif par défaut. Le chiffre
    est alors faux, et un tableau de bord qui ne le dit pas est pire qu'inutile."""
    _poser(session, "analyse", "un-modele-inconnu", entree=1000)
    mesures = store.metriques()
    assert "un-modele-inconnu" in mesures["tarifs_inconnus"]

    page = client.get("/admin/metriques", params={"token": "jeton-de-test"}).text
    assert "Tarif inconnu" in page
    assert "un-modele-inconnu" in page


def test_un_appel_sans_tokens_ne_declenche_pas_l_alerte(client, session, usage_nu):
    """Le mode démonstration n'appelle rien et n'enregistre aucun modèle. Crier
    au tarif manquant sur zéro token noierait la vraie alerte."""
    _poser(session, "analyse", "")
    assert store.metriques()["tarifs_inconnus"] == []


def test_le_cout_se_calcule_au_token_pres(client, session, usage_nu):
    """Quatre compteurs, quatre tarifs. La lecture de cache est dix fois moins
    chère que l'entrée : c'est tout l'intérêt du cache, et il faut que ça se voie."""
    _poser(session, "controle", "claude-opus-5",
           entree=1_000_000, sortie=1_000_000, ce=1_000_000, cl=1_000_000)
    attendu = 5.0 + 25.0 + 6.25 + 0.50
    assert store.metriques()["cout_usd_total"] == pytest.approx(attendu)


def test_le_cout_se_rapporte_au_compte_et_au_mois(usage_nu):
    """C'est l'unité de l'abonnement. Le coût par séance ne dit rien du prix à
    fixer : un élève ouvre autant de séances qu'il veut."""
    with TestClient(app) as lina:
        inscrire(lina)
        for _ in range(3):
            _poser(lina.post("/api/session").json()["session_id"],
                   "analyse", "claude-opus-5", entree=1_000_000)

    with TestClient(app) as sacha:
        inscrire(sacha)
        _poser(sacha.post("/api/session").json()["session_id"],
               "analyse", "claude-opus-5", entree=1_000_000)

    mesures = store.metriques()
    assert mesures["comptes_mois_mesures"] == 2, "les séances d'un compte doivent se regrouper"
    assert mesures["cout_usd_max_compte_mois"] == pytest.approx(15.0)
    assert mesures["cout_usd_moyen_compte_mois"] == pytest.approx(10.0)


def test_le_tableau_de_bord_montre_le_cout_par_compte(client, session, usage_nu):
    _poser(session, "analyse", "claude-opus-5", entree=1_000_000)
    page = client.get("/admin/metriques", params={"token": "jeton-de-test"}).text
    assert "Le chiffre qui décide de l’abonnement" in page
    # Trois lectures du même mois : une moyenne seule laisserait un gros usager
    # se cacher derrière la foule, ou l'inverse.
    for lecture in ("L’élève moyen", "L’élève médian", "Le plus gourmand"):
        assert lecture in page, lecture


def test_le_tableau_de_bord_dit_ce_que_coute_QUOI_par_eleve(client, session, usage_nu):
    """Trois nombres — moyenne, médiane, maximum — disent COMBIEN et jamais
    POURQUOI. Quand l'un d'eux dérape, il faut savoir s'il faut baisser les
    pages, les contrôles ou les fiches : trois plafonds différents, et les
    photos font l'essentiel de la note."""
    _poser(session, "analyse", "claude-opus-5", entree=1_000_000, quantite=8)
    _poser(session, "controle", "claude-opus-5", entree=200_000)
    page = client.get("/admin/metriques", params={"token": "jeton-de-test"}).text

    assert "Ce que coûte chaque élève" in page
    # Le prénom, pour reconnaître l'élève — pas l'adresse mail.
    assert "Lina" in page
    assert "@" not in page.split("Ce que coûte chaque élève")[1].split("<h2>")[0]
    # Les deux postes, chacun avec son volume.
    assert "Photos" in page and "Contrôles" in page
    assert "8 pages" in page

    # Et le prix d'UNE unité, qui est ce qui sert à régler un plafond.
    assert "Où va l’argent" in page
    assert "l’unité" in page


def test_un_tableau_de_bord_sans_le_moindre_appel_ne_tombe_pas(client):
    """L'état d'une base neuve, et celui de la démonstration : du volume sans
    coût. Une part de « x / 0 » renverrait une erreur 500 au lieu du tableau."""
    page = client.get("/admin/metriques", params={"token": "jeton-de-test"})
    assert page.status_code == 200
    assert "Aucun appel facturé pour l’instant" in page.text \
        or "Aucun appel facturé pour l'instant" in page.text


# --- La table de tarifs elle-même -------------------------------------------


def test_sonnet_5_a_son_propre_tarif():
    """Ajouté pour pouvoir comparer les modèles sans fausser la comparaison."""
    prix, connu = config.prix_du_modele("claude-sonnet-5")
    assert connu
    assert (prix["entree"], prix["sortie"]) == (2.0, 10.0)


def test_une_cle_vague_n_attrape_pas_un_voisin_au_mauvais_tarif():
    """« sonnet » tout court ramasserait Sonnet 4.6, qui n'est pas au tarif de
    Sonnet 5. Mieux vaut un modèle signalé comme inconnu qu'un chiffre faux
    présenté comme juste — c'est toute la raison d'être de cette table."""
    _, connu = config.prix_du_modele("claude-sonnet-4-6")
    assert not connu, "Sonnet 4.6 serait chiffré au tarif de Sonnet 5"


def test_la_cle_la_plus_precise_gagne(monkeypatch):
    """Sans tri par longueur, l'ordre du dictionnaire déciderait du tarif."""
    monkeypatch.setattr(config, "PRIX_USD_PAR_MTOK_PAR_MODELE", {
        "sonnet": {"entree": 3.0, "sortie": 15.0, "cache_ecriture": 3.75, "cache_lecture": 0.30},
        "sonnet-5": {"entree": 2.0, "sortie": 10.0, "cache_ecriture": 2.50, "cache_lecture": 0.20},
    })
    assert config.prix_du_modele("claude-sonnet-5")[0]["entree"] == 2.0
    assert config.prix_du_modele("claude-sonnet-4-6")[0]["entree"] == 3.0


def test_le_cache_est_dix_fois_moins_cher_que_l_entree():
    """C'est tout l'intérêt de mettre le cours en cache : si ce rapport se perd
    dans la table, l'économie qu'on croit faire n'existe plus."""
    for modele, prix in config.PRIX_USD_PAR_MTOK_PAR_MODELE.items():
        assert prix["cache_lecture"] == pytest.approx(prix["entree"] * 0.1), modele


def test_le_prix_d_ecriture_suit_la_duree_de_cache_demandee():
    """Deux tarifs d'écriture existent, et c'est le code qui choisit lequel
    s'applique : 1,25x l'entrée pour cinq minutes, 2x pour une heure. La table
    portait le premier pendant que llm.py demandait la seconde — chaque mise en
    cache était donc sous-estimée de 60 %, sans le dire.

    Le test lit la durée dans le code plutôt que de la répéter : c'est le seul
    moyen que changer l'une oblige à changer l'autre.
    """
    source = (Path(__file__).resolve().parent.parent / "app" / "llm.py").read_text(encoding="utf-8")
    attendu = 2.0 if '"ttl": "1h"' in source else 1.25
    for modele, prix in config.PRIX_USD_PAR_MTOK_PAR_MODELE.items():
        assert prix["cache_ecriture"] == pytest.approx(prix["entree"] * attendu), modele


# --- La lisibilité du tableau de bord, qui est le sujet ----------------------

def test_chaque_poste_a_un_nom_une_unite_et_une_couleur():
    """Un poste ajouté sans son nom afficherait une colonne vide ; sans son
    unité, « 8 » sans dire huit quoi ; sans sa couleur, une barre trouée."""
    source = (RACINE / "app" / "tableau_de_bord.py").read_text(encoding="utf-8")
    for poste in store.POSTES:
        assert poste in store.NOM_DU_POSTE, poste
        assert poste in store.UNITE_DU_POSTE, poste
        assert len(store.UNITE_DU_POSTE[poste]) == 2, f"{poste} : singulier et pluriel"
        assert f'"{poste}": "#' in source, f"{poste} n'a pas de teinte"


@pytest.mark.parametrize("poste, combien, attendu", [
    ("analyse", 1, "page"),
    ("analyse", 8, "pages"),
    ("fiche_ciblee", 1, "fiche ciblée"),
    ("fiche_ciblee", 4, "fiches ciblées"),
    ("controle", 1, "contrôle"),
])
def test_les_unites_savent_compter(poste, combien, attendu):
    """« 1 fiches » se lit comme un tableau négligé — et on croit alors moins
    ses chiffres."""
    assert store.unite(poste, combien) == attendu


def test_le_total_ne_se_trouve_pas_au_bout_du_defilement(client, session, usage_nu):
    """Le tableau est plus large qu'un téléphone : il défile. Le total est le
    chiffre qu'on vient chercher, il doit donc être le premier après le prénom
    — mesuré sur une capture, où il tombait hors de l'écran."""
    _poser(session, "analyse", "claude-opus-5", entree=1000, quantite=3)
    page = client.get("/admin/metriques", params={"token": "jeton-de-test"}).text
    entete = page[page.index("<th>Élève</th>"):]
    entete = entete[: entete.index("</tr>")]
    colonnes = re.findall(r">([^<>]+)</th>", entete)
    assert colonnes[0] == "Élève"
    assert colonnes[1] == "Total", f"le total doit suivre le prénom, pas fermer la ligne : {colonnes}"


def test_un_tableau_plus_large_que_l_ecran_dit_qu_il_defile(client, session, usage_nu):
    """Sur un téléphone, la dernière colonne est simplement coupée : rien ne
    distingue « il n'y a rien de plus » de « la suite est hors de l'écran »."""
    _poser(session, "analyse", "claude-opus-5", entree=1000, quantite=3)
    page = client.get("/admin/metriques", params={"token": "jeton-de-test"}).text
    assert page.count("défile vers la droite") >= 3, "les trois tableaux larges"


def test_les_teintes_suivent_le_poste_et_pas_son_rang():
    """Deux captures prises à une semaine d'écart doivent se comparer. Une
    couleur attribuée par rang repeindrait tout dès qu'un élève change d'ordre.
    """
    source = (RACINE / "app" / "tableau_de_bord.py").read_text(encoding="utf-8")
    bloc = source[source.index("TEINTES = {"):]
    bloc = bloc[: bloc.index("}")]
    for poste in store.POSTES:
        assert f'"{poste}"' in bloc
    # Les cinq teintes validées pour le daltonisme sur ce fond, dans cet ordre.
    for teinte in ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"):
        assert teinte in bloc


def test_un_prenom_hostile_ne_sort_pas_du_tableau(client, session, usage_nu):
    """Le prénom est écrit par l'élève et arrive maintenant dans la page."""
    _poser(session, "analyse", "claude-opus-5", entree=1000, quantite=2)
    with store.curseur() as cur:
        cur.execute("UPDATE comptes SET prenom = ?", ("<script>alert(1)</script>",))
    page = client.get("/admin/metriques", params={"token": "jeton-de-test"}).text
    assert "<script>alert(1)</script>" not in page
