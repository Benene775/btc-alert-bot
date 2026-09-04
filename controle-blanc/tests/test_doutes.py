"""Ce dont le modèle n'est pas sûr, il le demande.

Une transcription fausse ne se voit pas. L'élève lit une fiche impeccable bâtie
sur un mot mal lu, et tout ce qui suit — le contrôle, la correction, les notions
fragiles — hérite de l'erreur sans que rien ne le signale. C'est le seul défaut
du produit qu'un utilisateur ne peut pas repérer par lui-même.

Le seul qui sache lire cette écriture, c'est celui qui l'a écrite. Ces tests
tiennent les deux moitiés de cette idée : que la question soit posée, et qu'elle
reste assez courte pour qu'on y réponde.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")
CODE_NU = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", SCRIPT, flags=re.S))


def corps(nom: str) -> str:
    debut = CODE_NU.index("function " + nom + "(")
    return CODE_NU[debut : CODE_NU.index("\n}\n", debut)]


def test_le_modele_doit_dire_ce_qu_il_n_a_pas_lu_avec_certitude():
    from app import prompts

    assert "doutes" in prompts.SCHEMA_ANALYSE["properties"], "rien ne remonte les hésitations"
    assert "doutes" in prompts.SCHEMA_ANALYSE["required"], "le champ est facultatif"
    champs = prompts.SCHEMA_ANALYSE["properties"]["doutes"]["items"]["properties"]
    assert set(champs) == {"page", "lu", "pourquoi"}
    # « lu » doit être le texte exact de la transcription, sinon on ne peut rien
    # remplacer : c'est la seule contrainte qui rend la correction possible.
    assert "caractère" in champs["lu"]["description"]


def test_le_plafond_est_defini_a_un_seul_endroit():
    """Le nombre de questions est un réglage produit, pas une constante recopiée
    dans quatre fichiers. Le jour où il bouge, il doit bouger partout — sinon le
    schéma en autorise sept, la consigne en annonce deux, et le client tronque à
    cinq sans que personne ne s'en aperçoive."""
    from app import config, prompts

    # Le schéma ne peut PAS porter le plafond : l'API refuse « maxItems ». Il ne
    # tient donc qu'à la consigne et au client — raison de plus pour vérifier les
    # deux, puisqu'il n'y a pas de troisième filet.
    assert "maxItems" not in prompts.SCHEMA_ANALYSE["properties"]["doutes"], (
        "l'API renvoie un 400 sur maxItems, et toute l'analyse échoue"
    )
    assert str(config.MAX_DOUTES) in prompts.SCHEMA_ANALYSE["properties"]["doutes"]["description"]
    assert "{max_doutes}" in prompts.ANALYSE_SYSTEME, "la consigne code le nombre en dur"
    assert "config.MAX_DOUTES" in (RACINE / "app" / "llm.py").read_text(encoding="utf-8"), (
        "la consigne part sans son plafond, et « {max_doutes} » arrivera tel quel au modèle"
    )
    # Le client tronque aussi : un modèle peut toujours en renvoyer un de plus.
    assert "config.max_doutes" in CODE_NU, "le client fait confiance au modèle sur le nombre"
    assert '"max_doutes": config.MAX_DOUTES' in (RACINE / "app" / "main.py").read_text(encoding="utf-8")


def test_le_plafond_n_est_pas_un_objectif():
    """C'est la consigne qui décide si l'écran protège ou s'il fatigue.

    Un plafond élevé invite à le remplir. Un élève à qui on pose sept questions
    inutiles apprend à cliquer sans lire — et la fois où le doute est réel, il
    cliquera aussi. On aurait alors détruit la seule protection qui existe contre
    une transcription fausse, en croyant la renforcer.
    """
    from app import prompts

    consigne = prompts.ANALYSE_SYSTEME
    assert "ZÉRO" in consigne, "rien ne dit que zéro est une réponse, et la plus fréquente"
    assert "plafond, pas un objectif" in consigne
    # Et la distinction qui évite les questions pour rien : un passage important
    # n'est pas un passage illisible.
    assert "Important et illisible sont deux choses" in consigne


def test_la_consigne_vise_ce_qui_coute_cher_a_se_tromper():
    """Une tournure mal lue se devine à la relecture ; « 1,2 % » transcrit
    « 1 à 2 % » se révise faux jusqu'au contrôle."""
    from app import prompts

    for mot in ("chiffre", "date", "nom propre"):
        assert mot in prompts.ANALYSE_SYSTEME, mot


def test_la_correction_de_l_eleve_entre_dans_la_transcription():
    """Sans ça, l'écran ne serait qu'un sondage : tout ce qui suit lit la
    transcription, jamais les photos."""
    assert "function corrigerTranscription" in CODE_NU
    c = corps("corrigerTranscription")
    assert "c.transcription = c.transcription" in c, "la transcription n'est pas réécrite"
    # Le modèle ne recopie pas toujours au caractère près : on retente sans les
    # espaces plutôt que d'abandonner la correction en silence.
    assert "aplati" in c and "indexOf(plat)" in c
    # Et en un seul passage : comparer des tranches une à une figerait le
    # téléphone sur une transcription de huit pages.
    assert c.count("for (") == 1, "la recherche tolérante fait plus d'un balayage"


def test_ne_pas_savoir_est_une_reponse():
    """L'élève qui ne sait pas doit pouvoir passer. Sinon il invente, et une
    correction inventée est pire que l'hésitation du modèle."""
    c = corps("dessinerDoutes")
    assert "Je ne sais pas" in c
    assert "doute_ignore" in c, "l'abandon n'est pas mesuré"
    for evenement in ("doute_confirme", "doute_corrige"):
        assert evenement in c, evenement


def test_la_question_est_posee_avant_le_reste_de_l_ecran():
    """Elle arrive après les photos et avant la fiche : c'est le seul moment où
    la transcription est encore modifiable et où l'élève a son cahier ouvert."""
    assert 'id="doutes"' in PAGE
    assert PAGE.index('id="doutes"') < PAGE.index('id="liste-chapitres"')
    assert "dessinerDoutes();" in corps("dessinerPerimetre")


def test_le_texte_du_modele_n_entre_jamais_en_html():
    """Il sort d'une photo choisie par l'élève."""
    c = corps("dessinerDoutes")
    assert "innerHTML" not in c
    assert "replaceChildren" in c


def test_la_demonstration_pose_la_question():
    """Elle sert à faire cliquer un professeur dans tout le parcours : si l'écran
    n'y apparaît jamais, personne ne le verra avant la mise en ligne."""
    from app import demo

    doutes = demo.analyse(3)["doutes"]
    assert 1 <= len(doutes) <= 2
    assert all({"page", "lu", "pourquoi"} <= set(d) for d in doutes)
    faux_serveur = (RACINE / "outils" / "demonstration" / "faux-serveur.js").read_text(encoding="utf-8")
    assert "doutes: DOUTES" in faux_serveur
    for contenu in ("histoire.js", "espagnol.js"):
        source = (RACINE / "outils" / "demonstration" / contenu).read_text(encoding="utf-8")
        assert "const DOUTES" in source, contenu


def test_les_schemas_n_emploient_que_ce_que_l_api_accepte():
    """La sortie structurée ne prend qu'un sous-ensemble de JSON Schema.

    « maxItems » a coûté une analyse entière : l'API renvoie un 400 et tout
    l'appel échoue. Aucun test hors ligne ne pouvait l'attraper — la suite tourne
    en démonstration, sans appel réel — et le schéma avait l'air parfaitement
    valide. Cette liste blanche transforme la découverte en garde-fou : ajouter
    un mot-clé inhabituel devient une décision, pas une supposition.
    """
    from app import prompts

    CONNUS = {"type", "properties", "items", "required", "additionalProperties",
              "description", "enum"}

    def parcourir(noeud, chemin="racine"):
        if isinstance(noeud, dict):
            inconnus = set(noeud) - CONNUS
            # Les clés d'un bloc « properties » sont des noms de champs, pas des
            # mots-clés de schéma : on descend sans les juger.
            if not chemin.endswith("properties"):
                assert not inconnus, (
                    f"{chemin} : {sorted(inconnus)} — vérifie contre un vrai appel avant"
                )
            for cle, valeur in noeud.items():
                parcourir(valeur, chemin + "." + cle)
        elif isinstance(noeud, list):
            for element in noeud:
                parcourir(element, chemin + "[]")

    for nom in dir(prompts):
        if nom.startswith("SCHEMA_"):
            parcourir(getattr(prompts, nom), nom)


def test_la_question_doit_tenir_en_un_coup_d_oeil():
    """Mesuré sur un vrai cours : le modèle renvoyait des phrases entières, dont
    une de deux lignes, pour faire vérifier un chiffre. Faire relire trois lignes
    est le meilleur moyen que l'élève réponde sans regarder — et une réponse
    donnée sans regarder ne protège rien."""
    from app import prompts

    assert "AUSSI COURT QUE POSSIBLE" in prompts.ANALYSE_SYSTEME
    assert "pas une phrase entière" in prompts.ANALYSE_SYSTEME
