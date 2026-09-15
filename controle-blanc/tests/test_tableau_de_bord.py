"""Le tableau de bord doit répondre AVANT qu'on ait cherché.

Il ne s'adresse qu'à une personne, et cette personne a une question qui décide
de tout : est-ce qu'un abonnement paie l'élève qui le consomme ? La version
précédente contenait la réponse, dispersée dans huit tableaux de même poids —
le chiffre qui décide avait la taille du nombre de questions signalées.

Ce que ces tests tiennent :
- la réponse est écrite en toutes lettres, en euros, avec ce qui reste ;
- elle bascule quand le coût dépasse l'abonnement, au lieu d'afficher un reste
  négatif que l'oeil lit comme un bénéfice ;
- le plafond est calculé sur les prix mesurés, et un poste jamais appelé est
  nommé au lieu d'être compté pour rien en silence.
"""

from __future__ import annotations

import pytest

from app import config, store
from tests.conftest import inscrire

TARIF = {"entree": 5.0, "sortie": 25.0, "cache_ecriture": 6.25, "cache_lecture": 0.50}


@pytest.fixture()
def usage_nu(monkeypatch):
    with store.curseur() as cur:
        cur.execute("DELETE FROM usages")
    monkeypatch.setattr(config, "PRIX_USD_PAR_MTOK_PAR_MODELE", {"opus": TARIF})
    monkeypatch.setattr(config, "PRIX_USD_PAR_MTOK", TARIF)
    yield
    with store.curseur() as cur:
        cur.execute("DELETE FROM usages")


def _poser(session_id: str, action: str, entree=0, quantite=1):
    store.enregistrer_usage(session_id, action, {
        "tokens_entree": entree, "tokens_sortie": 0,
        "cache_ecriture": 0, "cache_lecture": 0, "modele": "claude-opus-5",
    }, quantite=quantite)


def _page(client) -> str:
    return client.get("/admin/metriques", params={"token": "jeton-de-test"}).text


# --- Le plafond : ce que coûterait le pire élève ------------------------------

def test_le_plafond_multiplie_le_prix_mesure_par_les_droits(client, session, usage_nu):
    """La moyenne dit ce que coûtent les élèves d'aujourd'hui ; le plafond dit ce
    que coûterait le pire. Un prix d'abonnement fixé sur la moyenne tient tant
    que personne ne se sert vraiment du produit."""
    # 800 000 tokens d'entrée à 5 $ le million font 4 $, pour 4 pages : 1 $ la page.
    _poser(session, "analyse", entree=800_000, quantite=4)

    plafond = store.plafond_du_mois()
    photos = next(l for l in plafond["lignes"] if l["poste"] == "analyse")
    assert photos["unitaire_usd"] == pytest.approx(1.0)
    assert photos["droits"] == config.QUOTAS_MOIS["analyse"]
    assert photos["cout_usd"] == pytest.approx(config.QUOTAS_MOIS["analyse"])


def test_la_correction_est_plafonnee_comme_le_controle(usage_nu):
    """Elle n'a pas de plafond à elle : il y en a une par contrôle, jamais deux.
    Lui en inventer un autre ferait mentir le pire cas dans les deux sens."""
    assert store.droits_du_mois()["correction"] == config.QUOTAS_MOIS["controle"]


def test_un_poste_jamais_appele_est_nomme_et_pas_deviné(client, session, usage_nu):
    """Sans prix mesuré, la ligne vaut zéro. Un total amputé qui ne le dit pas
    ferait passer l'abonnement pour rentable sur une colonne manquante."""
    _poser(session, "analyse", entree=1_000_000, quantite=1)

    plafond = store.plafond_du_mois()
    assert "controle" in plafond["sans_mesure"]
    assert "analyse" not in plafond["sans_mesure"]

    page = _page(client)
    assert "Jamais appelé, donc jamais chiffré" in page
    assert "un plancher, pas le vrai plafond" in page


def test_le_plafond_complet_ne_crie_pas_au_manque(client, session, usage_nu):
    for poste in store.POSTES:
        _poser(session, poste, entree=1_000_000, quantite=1)
    assert store.plafond_du_mois()["sans_mesure"] == []
    assert "Jamais appelé" not in _page(client)


# --- Le verdict : la réponse avant la recherche ------------------------------

def test_le_verdict_dit_ce_qu_il_reste_sur_un_abonnement(client, session, usage_nu,
                                                         monkeypatch):
    """Le coût était en dollars hors taxes, l'abonnement en euros : il fallait
    faire la conversion de tête pour savoir si ça tenait."""
    monkeypatch.setattr(config, "TAUX_EURO_POUR_UN_DOLLAR", 1.0)
    monkeypatch.setattr(config, "PRIX_ABONNEMENT_EUR", 10.0)
    _poser(session, "analyse", entree=400_000)     # 2 $ sur le mois du compte

    page = _page(client)
    assert "Est-ce qu'un abonnement paie l'élève qui le consomme ?" in page
    assert "2,00 €" in page, "ce que prend le modèle"
    assert "8,00 €" in page, "ce qu'il reste"


def test_le_verdict_bascule_quand_l_eleve_coute_plus_que_son_abonnement(
        client, session, usage_nu, monkeypatch):
    """« Il te reste −4,00 € » se lit de loin comme un reste. La phrase doit
    changer, pas seulement le signe."""
    monkeypatch.setattr(config, "TAUX_EURO_POUR_UN_DOLLAR", 1.0)
    monkeypatch.setattr(config, "PRIX_ABONNEMENT_EUR", 2.0)
    _poser(session, "analyse", entree=1_200_000)   # 6 $ sur le mois du compte

    page = _page(client)
    assert "Chaque abonné te fait perdre" in page
    assert "4,00 €" in page
    assert "Il te reste" not in page
    # La barre sature à 100 % : une étiquette à 300 % sous une barre pleine
    # ferait douter des deux.
    bandeau = page.split("</section>")[0]
    assert "Le modèle prend 300 % de l'abonnement" in bandeau
    assert "Il ne reste rien" in bandeau
    assert "−" not in page.split("</section>")[0], "pas de reste négatif dans le bandeau"


def test_sans_le_moindre_mois_facture_le_verdict_ne_s_invente_pas(client):
    """Une base neuve, et la démonstration : du volume sans coût. Annoncer
    « il te reste 7,99 € » serait une réponse fabriquée."""
    page = _page(client)
    assert "Pas encore de réponse" in page
    assert "Il te reste" not in page


def test_les_euros_suivent_le_taux_reglé(client, session, usage_nu, monkeypatch):
    """Le taux est fixe et se règle : un taux qui bouge tout seul ferait passer
    une variation de change pour une dérive des coûts."""
    monkeypatch.setattr(config, "TAUX_EURO_POUR_UN_DOLLAR", 0.5)
    _poser(session, "analyse", entree=2_000_000)   # 10 $
    page = _page(client)
    assert "10,00 $" in page
    assert "5,00 €" in page


# --- Ce qui ne doit pas se perdre dans la refonte ----------------------------

def test_la_page_reste_lisible_par_un_eleve_qui_ecrit_mal(client, session, usage_nu):
    """Prénom, niveau, énoncé et motif sont tous écrits par des élèves."""
    _poser(session, "analyse", entree=1000, quantite=2)
    with store.curseur() as cur:
        cur.execute("UPDATE comptes SET prenom = ?, niveau = ?",
                    ("<script>alert(1)</script>", "<b>3e</b>"))
    page = _page(client)
    assert "<script>alert(1)</script>" not in page
    assert "<b>3e</b>" not in page
    assert "&lt;script&gt;" in page


def test_le_tableau_par_eleve_dit_qu_il_cumule_depuis_le_debut(client, session, usage_nu):
    """Le bandeau parle d'un MOIS, ce tableau cumule TOUT. Les deux côte à côte
    sans le dire, et le lecteur croit comparer deux fois la même grandeur."""
    _poser(session, "analyse", entree=1000, quantite=2)
    page = _page(client)
    section = page[page.index("Ce que coûte chaque élève"):]
    assert "cumulés depuis le début" in section[: section.index("<h2>")]


def test_les_prenoms_sortent_sans_les_adresses(client, session, usage_nu):
    """Reconnaître un élève, pas l'identifier au-delà du nécessaire."""
    _poser(session, "analyse", entree=1000, quantite=2)
    page = _page(client)
    section = page[page.index("Ce que coûte chaque élève"):]
    section = section[: section.index("<h2>")]
    assert "Lina" in section
    assert "@" not in section


def test_zero_s_ecrit_zero_et_pas_zero_virgule_zero_zero_zero(client):
    """« 0,000 $ » se lit comme une mesure très fine. C'est l'inverse : il n'y a
    rien à mesurer. Une base neuve et le mode démonstration sont dans ce cas."""
    from app import tableau_de_bord

    assert tableau_de_bord.sous(0) == "0 $"
    assert tableau_de_bord.euros(0) == "0 €"
    # La précision reste là où elle sert : une page coûte deux centimes de dollar,
    # et la troisième décimale est ce qui distingue 0,018 $ de 0,023 $.
    assert tableau_de_bord.sous(0.0234) == "0,023 $"
    assert tableau_de_bord.sous(1.5) == "1,50 $"

    page = _page(client)
    assert "0,000 $" not in page
    assert "0,000 €" not in page


def test_le_prix_de_l_abonnement_garde_ses_centimes(client, session, usage_nu, monkeypatch):
    """7,99 € est un prix affiché, pas une mesure : « 8 € » ne serait plus lui."""
    monkeypatch.setattr(config, "PRIX_ABONNEMENT_EUR", 7.99)
    _poser(session, "analyse", entree=1000)
    assert "7,99 €" in _page(client)
