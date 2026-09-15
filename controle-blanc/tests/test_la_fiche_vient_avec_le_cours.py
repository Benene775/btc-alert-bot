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
    """Il l'était déjà : la dernière carte du paquet porte « Passer au contrôle
    blanc », et son libellé s'adapte — « Me tester sur ces 3 notions » quand il
    reste des notions à revoir. Un second bouton avait été ajouté sous le paquet
    sans qu'on ait vu celui-là : deux appels au même geste, l'un moins bien
    écrit que l'autre. Il a été retiré."""
    assert "bouton-apres-fiche" in SCRIPT
    assert "fiche-suite" not in PAGE, "le doublon est revenu"
    assert "fiche-suite" not in SCRIPT
    assert "fiche-suite" not in STYLE


def test_le_passage_au_controle_depuis_la_fiche_se_mesure():
    """La mesure des deux chemins est partie avec le carrefour. Celle-ci pose la
    même question après coup : combien passent au contrôle en sortant de leur
    fiche. Elle doit être posée sur TOUTES les portes de la carte de fin, sinon
    elle ne compte qu'une partie des élèves."""
    bloc = SCRIPT[SCRIPT.index("function testerDepuisLaFiche("):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "tracer('teste_depuis_fiche'" in bloc
    assert "lancerControle(notions)" in bloc
    # Aucune des portes de la carte de fin ne doit court-circuiter la mesure.
    fin = SCRIPT[SCRIPT.index("function majCarteFin()"):]
    fin = fin[: fin.index("\n/* --- La fiche sur papier")]
    assert "lancerControle(" not in fin, "une porte de la carte de fin ne se mesure pas"


def test_la_fiche_s_ouvre_entiere():
    """Le paquet de cartes reste le meilleur objet pour réviser, mais il
    s'ouvrait par défaut : depuis que la fiche arrive AVEC le cours au lieu
    d'être demandée, l'élève tombe dessus sans l'avoir cherchée, et un paquet
    horizontal se prend pour une carte unique."""
    bloc = SCRIPT[SCRIPT.index("function vueDeLaFiche()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "return 'colonne'" in bloc, "le défaut n'est pas la fiche entière"
    assert "'paquet' : 'colonne'" in bloc, "le choix de l'élève doit pouvoir gagner"
    assert "appliquerVueFiche(vueDeLaFiche())" in SCRIPT, "la fiche s'ouvre sans consulter la vue"


def test_le_bouton_dit_ou_il_mene_depuis_les_deux_vues():
    """« Revenir aux cartes » supposait qu'on en venait. Ce n'est plus vrai."""
    bloc = SCRIPT[SCRIPT.index("function appliquerVueFiche("):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "Voir carte par carte" in bloc
    assert "Tout afficher d’un coup" in bloc
    assert "Revenir aux cartes" not in SCRIPT


def test_la_position_de_lecture_ne_se_retient_pas_en_colonne():
    """L'observateur suit les cartes DANS le paquet. En colonne le paquet n'est
    plus ce qui défile : toutes les cartes seraient vues en même temps, et la
    position retenue serait la dernière — donc « Reprendre à » renverrait
    toujours à la fin de la fiche."""
    bloc = SCRIPT[SCRIPT.index("function appliquerVueFiche("):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "observateurCartes.disconnect()" in bloc
    assert bloc.index("if (colonne)") < bloc.index("else suivreCartes()")


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


def test_on_ne_dit_pas_fais_glisser_a_une_fiche_qui_ne_glisse_pas():
    """Envoyer l'élève chercher un geste qui ne répond pas, c'est lui faire
    douter de son téléphone — et la fiche s'ouvre maintenant en colonne."""
    bloc = SCRIPT[SCRIPT.index("function appliquerVueFiche("):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "fais glisser" in bloc, "la mention doit être posée par la vue"
    assert "colonne ? '' :" in bloc, "elle reste en colonne"
    # Et posée à un seul endroit : deux sources pour la même ligne, et l'une
    # repasserait devant l'autre selon l'ordre des appels. On compte le texte
    # écrit, pas les commentaires qui le citent.
    assert SCRIPT.count("' · fais glisser'") == 1
