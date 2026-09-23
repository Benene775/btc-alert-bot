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


# --- La fiche dans la nouvelle identité --------------------------------------

STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")


def _bloc_js(nom: str) -> str:
    debut = SCRIPT.index("function " + nom)
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_la_fiche_dit_ce_qu_elle_contient():
    """Elle ne le disait jamais : le paquet obligeait à le découvrir en
    glissant, la colonne à faire défiler. Dans les deux cas l'élève commençait
    sans savoir combien il en avait pour son temps."""
    assert 'id="sommaire-fiche"' in PAGE
    corps = _bloc_js("dessinerSommaireFiche")
    assert "allerASection(titre)" in corps, "une ligne du sommaire ne mène nulle part"
    assert "padStart(2, '0')" in corps


def test_le_sommaire_ne_liste_que_ce_qu_il_y_a_a_apprendre():
    """Les mots, les pièges et la carte de fin sont l'appareil de la fiche, pas
    son contenu. Un sommaire qui les liste fait croire à cinq notions quand il
    y en a trois."""
    assert "HORS_SOMMAIRE" in SCRIPT
    debut = SCRIPT.index("const HORS_SOMMAIRE")
    declaration = SCRIPT[debut : SCRIPT.index("]);", debut)]
    for service in ("Les mots", "Les pièges", "Tu te souviens ?", "C’est tout"):
        assert service in declaration, service


def test_le_sommaire_se_tait_quand_il_n_a_rien_a_dire():
    """Une seule notion, ou un second tour : un sommaire d'une ligne n'occupe
    que la place."""
    corps = _bloc_js("dessinerSommaireFiche")
    assert "secondTour" in corps
    assert "notions.length < 2" in corps


def test_en_colonne_les_cartes_deviennent_des_sections():
    """Le paquet reste un paquet — teinte, arrondi, ombre, une notion par écran,
    c'est le bon objet pour réviser au doigt. En colonne c'est une page qu'on
    lit d'une traite : les mêmes cartes empilées faisaient vingt rectangles
    pastel arrondis, c'est-à-dire le défaut que la refonte devait corriger."""
    bloc = STYLE[STYLE.index('.paquet[data-vue="colonne"] .carte-fiche {'):]
    bloc = bloc[: bloc.index("\n}")]
    assert "background: none" in bloc
    assert "border-radius: 0" in bloc
    assert "box-shadow: none" in bloc
    assert "border-bottom: 1px solid var(--trait)" in bloc


def test_le_masque_de_la_phrase_a_retenir_survit_a_la_refonte():
    """C'est le seul moment de la fiche où l'élève se teste. Le retirer aurait
    rendu la page plus belle et moins utile — une maquette ne décide pas de ce
    qu'on apprend."""
    assert '.retenir[data-masque="oui"] mark' in STYLE
    assert "Tu te souviens" in SCRIPT
    # Et le bloc porte la couleur de ce sur quoi on agit : on touche pour révéler.
    bloc = STYLE[STYLE.index('.paquet[data-vue="colonne"] .carte-retenir {'):]
    assert "border-left: 3px solid var(--accent)" in bloc[: bloc.index("\n}")]


def test_la_barre_du_paquet_disparait_en_colonne():
    """Les rubans disent à quelle carte on en est. En colonne il n'y a plus de
    carte courante, et le bouton de la vue d'ensemble restait seul sur sa ligne
    sans rien à commander."""
    assert '.ecran-fiche:has(.paquet[data-vue="colonne"]) .barre-fiche { display: none; }' in STYLE


def test_le_sommaire_ouvre_sur_le_titre_vise():
    """Mesuré dans un navigateur : « le plus près » amenait bien la notion à
    l'écran, mais par le bas — on cliquait « L'arrière et l'année 1917 » et on
    tombait sur la fin de « La violence de masse », le titre visé à mi-hauteur.
    Un sommaire qui n'ouvre pas sur son titre n'est pas un sommaire."""
    corps = _bloc_js("allerACarte")
    assert "dataset.vue === 'colonne'" in corps, "la visée doit dépendre de la vue"
    assert "window.scrollTo" in corps
    # Le bandeau est collant : viser le haut de la page sans le retrancher
    # glisse le titre dessous.
    assert "bandeau" in corps


def test_une_notion_coupee_en_deux_ne_repete_pas_son_titre():
    """Une section trop longue tient sur deux cartes. Empilées en colonne, on
    lisait « La violence de masse / 1 sur 2 » puis « La violence de masse /
    2 sur 2 » : un journal qui recommence l'article à chaque colonne."""
    assert "carte.dataset.suite = 'oui'" in SCRIPT
    assert SCRIPT.count("if (morceau > 0) carte.dataset.suite = 'oui';") == 3, (
        "les trois découpages — notions, mots, pièges — marquent leur suite"
    )
    assert '.paquet[data-vue="colonne"] .carte-fiche[data-suite] > .carte-tete' in STYLE
    assert '.paquet[data-vue="colonne"] .carte-suite { display: none; }' in STYLE


def test_le_trait_separe_deux_notions_pas_deux_morceaux_de_la_meme():
    """Sinon la page découpe au mauvais endroit : un filet au milieu d'une
    notion et rien entre deux."""
    assert (
        '.paquet[data-vue="colonne"] .carte-fiche:has(+ .carte-fiche[data-suite]) {'
        in STYLE
    )
    bloc = STYLE[STYLE.index(
        '.paquet[data-vue="colonne"] .carte-fiche:has(+ .carte-fiche[data-suite]) {'
    ):]
    assert "border-bottom: 0" in bloc[: bloc.index("\n}")]


def test_la_provenance_ne_passe_plus_par_dessus_la_suite():
    """Elle a une marge basse négative : elle mord dans le rembourrage de la
    carte pour gagner trente pixels de texte. En colonne il n'y a plus de
    rembourrage à mordre, et la vignette recouvrait le premier point du morceau
    suivant — vu à l'écran, pas déduit."""
    assert '.paquet[data-vue="colonne"] .provenance { margin-bottom: 0; }' in STYLE
    # Et elle se dit une fois par notion, pas une fois par morceau.
    assert (
        '.paquet[data-vue="colonne"] .carte-fiche:has(+ .carte-fiche[data-suite]) .provenance'
        in STYLE
    )


def test_la_page_ne_s_allume_pas_sous_la_souris():
    """La lueur au survol dit « ceci est un objet qu'on manipule ». En colonne
    il n'y a plus d'objets, il y a une page."""
    assert '.paquet[data-vue="colonne"] .carte-fiche::after { display: none; }' in STYLE


def test_sur_un_ordinateur_la_colonne_garde_la_largeur_d_un_texte():
    """La fiche s'élargit à 1120 pixels pour montrer deux cartes entières —
    c'est le paquet qui en a besoin. En colonne, la même largeur donnait des
    lignes de cent trente caractères : on perd la ligne suivante en revenant à
    la marge."""
    assert '.ecran-fiche:has(.paquet[data-vue="paquet"]) { max-width:' in STYLE
    assert ".ecran-fiche { max-width: min(var(--large), 92vw); }" not in STYLE
