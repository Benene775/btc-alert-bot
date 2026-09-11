"""L'âge déclaré à l'inscription, et l'accord des parents en dessous de 15 ans.

En France, le consentement du seul mineur ne vaut qu'à partir de 15 ans
(article 8 du RGPD, article 45 de la loi Informatique et Libertés). En dessous,
il faut aussi celui d'un titulaire de l'autorité parentale.

Ce qui est posé ici est une DÉCLARATION, pas une vérification : un élève qui
veut passer outre coche la case. C'est un choix assumé pour le test fermé, avec
une dizaine de familles connues. La vérification — le parent qui agit lui-même —
reste à construire pour l'ouverture publique.

Ce que le code doit tenir malgré tout :

1. On refuse au lieu d'enregistrer sans accord. Pas de compte « en attendant » :
   un compte ouvert travaille.
2. Le refus est côté serveur. Une case cochée dans un navigateur ne coûte rien
   à contourner, et c'est précisément la trace qu'on garde.
3. Un client qui ne dit rien est traité comme un mineur sans accord, pas comme
   un majeur : le défaut doit fermer, pas ouvrir.
4. La déclaration est datée. Une case sans date ne prouve rien.
"""

from __future__ import annotations

from pathlib import Path

from app import store
from tests.conftest import adresse_neuve

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")


def inscription(visiteur, **champs):
    corps = {"email": adresse_neuve(), "mot_de_passe": "chocolatine-du-matin",
             "prenom": "Lina", "niveau": "4e"}
    corps.update(champs)
    return visiteur.post("/api/auth/inscription", json=corps)


def test_quinze_ans_ou_plus_passe_seul(visiteur):
    assert inscription(visiteur, majeur_15=True).status_code == 200


def test_moins_de_quinze_sans_accord_est_refuse(visiteur):
    reponse = inscription(visiteur, majeur_15=False, accord_parental=False)
    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["genre"] == "accord"
    assert "tes parents" in corps["message"]
    # Le message doit dire quoi faire, pas seulement non.
    assert "reviens" in corps["message"].lower()


def test_moins_de_quinze_avec_accord_passe(visiteur):
    assert inscription(visiteur, majeur_15=False, accord_parental=True).status_code == 200


def test_un_client_muet_est_refuse(visiteur):
    """Le défaut doit fermer. Un ancien navigateur en cache, un script tiers, un
    appel direct à l'API : rien de tout ça ne doit ouvrir un compte d'enfant."""
    assert inscription(visiteur).status_code == 400


def test_la_declaration_est_datee(visiteur, monkeypatch):
    email = adresse_neuve()
    assert inscription(visiteur, email=email, majeur_15=False,
                       accord_parental=True).status_code == 200
    with store.curseur() as cur:
        cur.execute("SELECT majeur_15, accord_le FROM comptes WHERE email = ?", (email,))
        ligne = cur.fetchone()
    assert ligne["majeur_15"] == 0
    assert ligne["accord_le"], "l'accord n'est pas daté : la case ne prouve rien"

    # Un élève de 15 ans ou plus n'a pas d'accord à donner : pas de date non plus.
    autre = adresse_neuve()
    inscription(visiteur, email=autre, majeur_15=True)
    with store.curseur() as cur:
        cur.execute("SELECT majeur_15, accord_le FROM comptes WHERE email = ?", (autre,))
        ligne = cur.fetchone()
    assert ligne["majeur_15"] == 1 and ligne["accord_le"] == ""


def test_on_ne_demande_pas_la_date_de_naissance():
    """Une tranche suffit à savoir quelle règle s'applique. Une date serait une
    donnée de plus à garder, à protéger et à effacer — pour rien."""
    from app.schemas import Inscription

    champs = set(Inscription.model_fields)
    assert "majeur_15" in champs
    for interdit in ("date_de_naissance", "naissance", "age", "anniversaire"):
        assert interdit not in champs, interdit


def test_l_ecran_pose_la_question_et_montre_quoi_dire_aux_parents():
    volet = PAGE[PAGE.index('id="volet-inscription"') : PAGE.index('id="volet-oubli"')]
    assert 'id="age-15"' in volet and 'id="age-moins"' in volet
    assert 'id="case-accord"' in volet
    # « Demande à tes parents » sans leur dire quoi demander ne sert à rien.
    for point in ("prénom, ta classe", "ne sont pas conservées", "Rien n’est vendu",
                  "effacer en un clic"):
        assert point in volet, f"ce qu'il doit montrer à ses parents ne dit pas : {point}"


def test_le_bloc_ne_parait_que_s_il_sert():
    """Posé d'emblée, il ferait lire un avertissement à des lycéens que ça ne
    concerne pas."""
    assert "$('bloc-accord').hidden = !$('age-moins').checked" in SCRIPT


def test_le_navigateur_ne_devine_pas_a_la_place_de_l_eleve():
    """Sans réponse, on demande — on ne suppose pas la majorité."""
    bloc = SCRIPT[SCRIPT.index("function ageDeclare()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "return null" in bloc
    assert "Dis-nous si tu as 15 ans ou plus." in SCRIPT


def test_rien_ne_demande_de_payer():
    """Le test est gratuit pour les dix familles. Rien dans le produit ne doit
    laisser croire le contraire — ni un prix, ni un abonnement, ni un refus de
    quota qui proposerait de « passer à la version supérieure ».

    Les messages de quota disent tous « le compteur repart le 1er » : ce sont
    des limites, pas des péages. Ce test empêche qu'un jour l'un d'eux devienne
    une invitation à payer sans que personne s'en aperçoive.
    """
    from app import store

    vu_par_l_eleve = (PAGE + SCRIPT
                      + " ".join(store.MESSAGES_QUOTA.values())
                      + (RACINE / "app" / "courrier.py").read_text(encoding="utf-8"))
    # On interdit l'INVITATION à payer, pas le mot : le produit dit justement
    # qu'il n'y a aucun paiement, et il doit pouvoir le dire.
    for tournure in ("abonnement", "s’abonner", "passe à la version",
                     "version supérieure", "premium", "débloquer",
                     "payer pour", "carte bancaire requise", "essai gratuit"):
        assert tournure not in vu_par_l_eleve.lower(), (
            f"« {tournure} » apparaît dans ce que voit l'élève"
        )


def test_et_le_produit_le_dit():
    """Un parent qui donne son accord se demande d'abord si ça va lui coûter
    quelque chose. Répondre avant qu'il pose la question vaut mieux que de le
    laisser chercher le piège."""
    volet = PAGE[PAGE.index('id="volet-inscription"') : PAGE.index('id="volet-oubli"')]
    assert "aucun paiement dans l’application" in volet
    # Et ça doit se retrouver le jour où le test s'arrête.
    assert PAGE.count("À REPRENDRE À LA FIN DU TEST") == 1
    assert "à reprendre à la fin du test" in PAGE.lower()
