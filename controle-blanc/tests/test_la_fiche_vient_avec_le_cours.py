"""La fiche n'est plus un choix : elle vient avec le cours.

Il y avait un carrefour après les photos — « je révise d'abord » ou « je me
teste tout de suite » — et le second chemin ne donnait jamais de fiche. Les
premiers élèves ont tranché : ce qu'ils préfèrent, ce sont les fiches, et un sur
deux ne les voyait jamais. Un produit ne cache pas ce qu'il fait de mieux
derrière un choix posé avant que l'élève sache ce qu'il choisit.

Ce que ces tests tiennent :
- le carrefour a bien disparu, partout, et pas seulement de l'écran ;
- confirmer ses chapitres demande la fiche, sans détour ;
- le contrôle blanc est au bout de la fiche, et seulement quand il a de quoi
  être fabriqué ;
- le plafond de fiches du jour ne bride plus le nombre de cours — depuis que la
  fiche est automatique, c'est lui qui arrêterait l'élève, sur un refus qui ne
  parlerait même pas de photos.
"""

from __future__ import annotations

from pathlib import Path

from app import config

RACINE = Path(__file__).resolve().parent.parent
WEB = RACINE / "web"
PAGE = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPT = (WEB / "app.js").read_text(encoding="utf-8")
STYLE = (WEB / "styles.css").read_text(encoding="utf-8")


def test_le_carrefour_a_disparu_partout():
    """Un écran retiré de la page mais gardé dans le script et la feuille de
    style, c'est du code mort qu'on croit vivant à la relecture suivante."""
    assert 'id="ecran-carrefour"' not in PAGE
    assert "cases-carrefour" not in PAGE
    for mort in ("dessinerCarrefour", "choisirChemin", "case-carrefour"):
        assert mort not in SCRIPT, mort
    assert "carrefour" not in STYLE


def test_confirmer_ses_chapitres_demande_la_fiche():
    bloc = SCRIPT[SCRIPT.index("function confirmerPerimetre()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "demanderFicheGenerale()" in bloc
    assert "ecran-carrefour" not in bloc


def test_le_controle_blanc_est_au_bout_de_la_fiche():
    """La fiche était un cul-de-sac : on la lisait, et il fallait deviner par où
    passer pour se tester — le contrôle se cherchait dans le menu de la marque."""
    assert 'id="fiche-suite"' in PAGE
    assert 'id="bouton-tester-depuis-fiche"' in PAGE
    assert "$('bouton-tester-depuis-fiche').onclick" in SCRIPT


def test_le_bouton_ne_parait_pas_quand_il_n_a_rien_a_tester():
    """Une fiche relue depuis l'archive, hors séance, n'a pas de cours derrière
    elle : un bouton qui échouerait là ferait passer l'archive pour cassée. Et
    pas au second tour non plus — on vient d'y mettre ce qui n'était pas acquis,
    y renvoyer tout de suite ne mesurerait qu'une lecture de trente secondes."""
    bloc = SCRIPT[SCRIPT.index("function majSuiteDeLaFiche("):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "secondTour" in bloc
    assert "!etat" in bloc
    assert "chapitresRetenus().length" in bloc


def test_une_fiche_refusee_ne_laisse_pas_l_eleve_en_plan():
    """Depuis que la fiche vient d'office, son refus tombe au milieu du parcours.
    Sans rattrapage, l'élève reste sur l'écran des chapitres devant un bouton qui
    vient de ne rien faire — alors que son cours est photographié et enregistré."""
    bloc = SCRIPT[SCRIPT.index("async function demanderFicheGenerale("):]
    bloc = bloc[: bloc.index("\nasync function demanderFicheCiblee(")]
    assert "genre === 'quota'" in bloc
    assert "montrer('ecran-espace')" in bloc
    # Et dans cet ordre : changer d'écran efface les messages persistants. Posé
    # avant, le refus arrivait sur une page où il n'était plus lisible — l'élève
    # se retrouvait sur sa page sans savoir pourquoi. Vu dans un navigateur,
    # invisible à la lecture du code.
    assert bloc.index("montrer('ecran-espace')") < bloc.index("message(e.message"), \
        "on emmène d'abord, on explique ensuite"


def test_le_plafond_de_fiches_du_jour_ne_bride_pas_les_cours():
    """Une fiche par cours, maintenant. Si le plafond de fiches du jour est plus
    bas que le nombre de cours qu'une journée de photos autorise, c'est lui qui
    arrête l'élève — au quatrième cours d'un samedi après-midi, sur un message
    qui parle de fiches alors qu'il vient d'envoyer des photos."""
    photos = config.QUOTAS["analyse"]
    fiches = config.QUOTAS["fiche_generale"]
    cours_par_jour = photos["jour"] // photos["session"]
    assert fiches["jour"] >= cours_par_jour, (
        f"{fiches['jour']} fiches par jour pour {cours_par_jour} cours possibles")

    cours_par_mois = config.QUOTAS_MOIS["analyse"] // photos["session"]
    assert config.QUOTAS_MOIS["fiche_generale"] >= cours_par_mois, (
        f"{config.QUOTAS_MOIS['fiche_generale']} fiches par mois pour "
        f"{cours_par_mois} cours possibles")


def test_le_parcours_annonce_le_bon_nombre_d_etapes():
    """Une marche en moins : l'annoncer encore reviendrait à promettre un écran
    qui ne viendra pas."""
    assert "Étape 1 sur 3" in PAGE
    assert "sur 4" not in PAGE
