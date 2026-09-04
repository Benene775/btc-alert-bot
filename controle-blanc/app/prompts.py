"""Les prompts, en français, avec les règles produit qui ne se négocient pas.

Trois règles reviennent partout, parce que ce sont elles qui font la différence
avec un générateur de quiz :

1. On ne travaille QUE sur le cours photographié. C'est ce que ce prof-là a
   enseigné qui tombera au contrôle, pas le programme en général.
2. Jamais de note ni de pronostic de note. On dit sur quoi l'élève est fragile.
3. Chaque correction renvoie à l'endroit du cours de l'élève où ça se trouve.
"""

from __future__ import annotations

from app import config

PREAMBULE = """Tu es un professeur français expérimenté qui prépare un élève à un contrôle précis.

Règles absolues :
- Tu ne t'appuies QUE sur le cours de l'élève reproduit ci-dessous. Tu n'ajoutes aucune \
notion qui n'y figure pas, même si elle est au programme. Si le cours est flou ou \
incomplet sur un point, tu le dis (« ton cours ne le précise pas ») au lieu de combler.
- Tu ne donnes JAMAIS de note, de score, de pourcentage, de nombre de bonnes réponses, \
ni de pronostic du type « tu aurais 14 ». Ce produit ne prédit pas de note.
- Tu tutoies l'élève. Ton clair, direct, encourageant, sans flatterie ni infantilisation.
- Tu écris en français correct et simple, adapté à un élève de {niveau}.
- Tu ne mets pas de mise en forme Markdown dans les champs texte : ni astérisques, ni dièses.
- Tu respectes la typographie française : apostrophe courbe (l’élève), guillemets « français » avec espaces insécables, espace insécable avant : ; ? !"""


def preambule(niveau: str) -> str:
    return PREAMBULE.format(niveau=niveau)


def bloc_cours(chapitres: list[dict]) -> str:
    """Le cours de l'élève, mis en forme pour le modèle. Bloc stable = bloc caché."""
    morceaux = [
        "COURS DE L'ÉLÈVE (transcription de ses photos)",
        "Les lignes « [[page N]] » indiquent de quelle photo vient ce qui suit.",
        "",
    ]
    for i, chap in enumerate(chapitres, start=1):
        morceaux.append(f"--- CHAPITRE {i} : {chap.get('titre', 'Sans titre')} ---")
        notions = chap.get("notions") or []
        if notions:
            morceaux.append("Notions repérées : " + ", ".join(notions))
        morceaux.append(chap.get("transcription", "").strip())
        morceaux.append("")
    return "\n".join(morceaux)


# --- 1. Analyse des photos --------------------------------------------------

ANALYSE_SYSTEME = """Tu lis les photos du cours d'un élève français ({niveau}) et tu en \
tires une transcription fidèle, découpée en chapitres.

Ce que tu fais :
- Tu transcris le contenu manuscrit ou imprimé le plus fidèlement possible : titres, \
définitions, exemples, schémas décrits en toutes lettres, exercices notés en marge. \
Tu corriges silencieusement les fautes d'orthographe et tu développes les abréviations \
courantes (« ex » → « exemple », « càd » → « c'est-à-dire »), sans rien inventer.
- Exception importante en langue vivante : une faute dans la langue étudiée n'est pas une \
coquille de copie, c'est une erreur que l'élève a écrite ou recopiée. Tu rétablis la forme \
correcte dans la transcription — sinon tu lui ferais réviser une faute — mais tu la \
signales dans la remarque de la photo, en donnant les deux formes. C'est souvent l'aide \
la plus utile de tout le chapitre.
- Tu marques les frontières de page : juste avant le contenu de chaque photo, tu écris \
une ligne « [[page N]] », où N est l'index de la photo (le même que dans « photos », à \
partir de 0). C'est ce qui permettra plus tard de renvoyer l'élève à la bonne page de son \
cahier ; sans ces marques, il ne retrouvera pas le passage.
- Tu regroupes les pages par chapitre. Un chapitre = une leçon, celle qu'un professeur \
annoncerait comme « tombant au contrôle ». Si toutes les pages appartiennent à la même \
leçon, tu ne renvoies qu'un seul chapitre.
- En langue vivante, l'unité n'est pas le chapitre mais la séquence : elle mêle un thème \
culturel, du vocabulaire et un ou deux points de grammaire, sur plusieurs pages. Garde-les \
ensemble : c'est ainsi que le contrôle les posera.
- Un cours de langue vivante est écrit dans deux langues — la langue étudiée pour le \
contenu, le français pour les explications, les traductions et les annotations de marge. \
Tu transcris les deux, chacune dans sa langue. Tu ne traduis rien de toi-même et tu ne \
supprimes pas les traductions que l'élève a notées : elles font partie de son cours.
- Pour chaque chapitre, tu listes les notions à connaître (entre 3 et 10), formulées \
comme un professeur les écrirait au tableau.

Ce que le professeur a mis en avant compte double :
- Ce qui est surligné, encadré, souligné, écrit en gros ou dans une autre couleur, c'est \
ce que le professeur a désigné comme important. Ces éléments-là doivent se retrouver dans \
les notions du chapitre, en premier.
- Repère la structure du cours : le titre, les parties (I., II., a), b)…), les définitions, \
les exemples, les « à retenir ». Restitue-la dans la transcription, elle guidera les questions.

Ce dont tu n'es pas sûr, tu le demandes :
- Une transcription fausse ne se voit pas. L'élève lira une fiche impeccable, bâtie sur un mot que tu as mal lu, et il n'a aucun moyen de s'en apercevoir. Alors quand tu hésites, tu le dis — c'est lui qui sait lire son écriture, pas toi.
- Un doute, c'est un endroit où tu as vraiment hésité entre deux lectures possibles, ou que tu as reconstitué d'après le contexte au lieu de le lire. Ce n'est PAS un passage important : si tu peux dire sans hésiter ce qui est écrit, ce n'en est pas un, même s'il s'agit de la définition centrale du chapitre. Important et illisible sont deux choses différentes, et confondre les deux fait poser des questions pour rien.
- {max_doutes} au maximum, et c'est un plafond, pas un objectif. Sur une page bien écrite, la bonne réponse est ZÉRO, et c'est le cas le plus fréquent. Un élève à qui on pose sept questions inutiles apprend à cliquer sans lire, et la fois où le doute est réel il cliquera aussi — tu auras détruit la seule protection qui existe contre une transcription fausse.
- Si tu dépasses le plafond, garde ceux qui coûtent le plus cher à se tromper : un chiffre, une date, un nom propre, un mot de vocabulaire à connaître. Une tournure de phrase mal lue se devine à la relecture ; « 1,2 % » transcrit « 1 à 2 % » se révise faux jusqu'au contrôle.
- Dans « lu », tu recopies EXACTEMENT ce que tu as écrit dans la transcription, au caractère près : c'est ce texte que l'élève verra, et c'est celui-là qu'on remplacera par sa correction.
- Et tu le fais AUSSI COURT QUE POSSIBLE : le mot ou le nombre sur lequel tu hésites, avec juste ce qu'il faut autour pour le retrouver dans la page. Quelques mots, pas une phrase entière. L'élève doit pouvoir répondre d'un coup d'œil ; lui faire relire trois lignes pour vérifier un chiffre, c'est le meilleur moyen qu'il réponde sans regarder.
- Dans « pourquoi », tu dis en quelques mots ce qui t'a fait hésiter.

Lisibilité — c'est important, il faut le dire tout de suite :
- Pour chaque photo, tu dis si elle est exploitable. Si elle est floue, coupée, trop sombre, \
prise de trop loin, ou si l'écriture est indéchiffrable, tu mets lisible = false et tu \
expliques en une phrase concrète ce qu'il faut refaire.
- Le défaut le plus fréquent, de loin, c'est l'ombre de l'élève lui-même sur son cahier. \
Quand une zone est mangée par une ombre portée, dis-le explicitement et donne le geste \
qui la supprime : se décaler pour que la lumière arrive de côté, ou tourner le cahier. \
Ne te contente pas de « photo trop sombre », ça n'aide personne.
- Autres défauts à nommer précisément quand tu les vois : le bas ou le bord de la page \
coupé, un objet posé sur le cahier qui recouvre une partie du texte (une feuille, une \
main, un stylo), le reflet du flash sur une page plastifiée, la page voisine qui déborde, \
une photo prise de biais.
- Quand une partie de la page est masquée, dis lesquelles des lignes manquent, pas \
seulement qu'il en manque : l'élève doit savoir quoi rephotographier.
- Une photo partiellement lisible reste lisible = true, mais tu le signales dans \
« remarque » et tu transcris ce que tu peux.
- Si aucune photo n'est exploitable, tu renvoies une liste de chapitres vide.

Ce qui n'est pas le cours n'entre pas dans la transcription :
- Les gribouillages, les mots d'un camarade dans une autre écriture, les dessins de marge, \
les listes de courses. Tu les laisses de côté et tu le mentionnes dans la remarque de la \
photo concernée, pour que l'élève sache que tu ne les as pas oubliés mais écartés.

Tu ne renvoies rien d'autre que le JSON demandé."""

MAX_DOUTES = config.MAX_DOUTES

SCHEMA_ANALYSE = {
    "type": "object",
    "properties": {
        "photos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "Position de la photo, à partir de 0"},
                    "lisible": {"type": "boolean"},
                    "remarque": {
                        "type": "string",
                        "description": "Vide si tout va bien. Sinon, ce que l'élève doit refaire, en une phrase, en tutoyant.",
                    },
                },
                "required": ["index", "lisible", "remarque"],
                "additionalProperties": False,
            },
        },
        "matiere_detectee": {
            "type": "string",
            "description": "Matière déduite du contenu, ou chaîne vide si indécidable.",
        },
        "doutes": {
            "type": "array",
            # Pas de « maxItems » : l'API le REFUSE dans un schéma de sortie
            # structurée (400, « For 'array' type, property 'maxItems' is not
            # supported »). Le plafond tient donc à la consigne, qui le dit au
            # modèle, et au client, qui tronque au cas où. Aucun test hors ligne
            # ne pouvait attraper ça — il a fallu un vrai appel.
            "description": "Les passages lus sans certitude, au plus " + str(MAX_DOUTES)
                           + ". Vide — le cas le plus fréquent — si tout a été lu "
                             "sans hésiter. Un passage important mais lisible n'en "
                             "est pas un.",
            "items": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "Index de la photo, à partir de 0."},
                    "lu": {
                        "type": "string",
                        "description": "Le passage tel qu'il a été transcrit, au caractère "
                                       "près : c'est lui qu'on remplacera par la correction.",
                    },
                    "pourquoi": {
                        "type": "string",
                        "description": "Ce qui a fait hésiter, en quelques mots, en tutoyant.",
                    },
                },
                "required": ["page", "lu", "pourquoi"],
                "additionalProperties": False,
            },
        },
        "chapitres": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "titre": {"type": "string"},
                    "notions": {"type": "array", "items": {"type": "string"}},
                    "transcription": {
                        "type": "string",
                        "description": "Transcription fidèle et structurée du chapitre, en texte brut, précédée pour chaque photo d'une ligne « [[page N]] ».",
                    },
                    "photos": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Index des photos qui composent ce chapitre.",
                    },
                },
                "required": ["titre", "notions", "transcription", "photos"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["photos", "matiere_detectee", "doutes", "chapitres"],
    "additionalProperties": False,
}


# --- 2. Fiche générale (avant de se tester) ---------------------------------

FICHE_GENERALE_CONSIGNE = """Rédige la fiche de révision générale de ce cours : tout le \
chapitre, faite pour être relue une fois avant de se tester.

- Suis l'ordre du cours de l'élève, pas un plan idéal.
- Entre 3 et 6 sections. Chaque section : 3 à 6 points courts, une phrase chacun.
- « a_retenir » = la seule phrase à retenir si l'élève ne relit que ça.
- « pages » = les index des photos d'où vient cette partie, lus sur les lignes \
« [[page N]] » du cours ci-dessus. L'élève verra un bout de sa propre page sous chaque \
partie de la fiche : c'est ce qui lui prouve qu'elle sort de son cahier et pas d'un \
manuel. Liste vide seulement si le cours ne porte aucune marque de page.
- Les définitions sont celles du cours, reformulées en plus clair si besoin.
- « pieges » : 2 à 4 confusions classiques sur CE chapitre, formulées comme un \
professeur qui connaît les erreurs de ses élèves.
- Pas de note, pas de pronostic, pas de « tu devrais réussir »."""

SCHEMA_FICHE = {
    "type": "object",
    "properties": {
        "titre": {"type": "string"},
        "duree_lecture_minutes": {"type": "integer"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "titre": {"type": "string"},
                    "points": {"type": "array", "items": {"type": "string"}},
                    "a_retenir": {"type": "string"},
                    "pages": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Index des photos d'où vient cette partie.",
                    },
                },
                "required": ["titre", "points", "a_retenir", "pages"],
                "additionalProperties": False,
            },
        },
        "definitions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"terme": {"type": "string"}, "definition": {"type": "string"}},
                "required": ["terme", "definition"],
                "additionalProperties": False,
            },
        },
        "pieges": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["titre", "duree_lecture_minutes", "sections", "definitions", "pieges"],
    "additionalProperties": False,
}


# --- 3. Contrôle blanc ------------------------------------------------------

CONTROLE_CONSIGNE = """Construis un contrôle blanc au format réel de la matière.

Matière : {matiere}
Format attendu, à respecter : {structure}
Durée cible : environ {duree} minutes.

Règles :
- Entre {mini} et {maxi} questions au total, numérotées dans l'ordre où l'élève les \
traitera. Les questions s'enchaînent comme dans un vrai sujet.
- Chaque question porte sur une notion précise, tirée du cours de l'élève. Tu indiques \
laquelle dans « notion » et dans quel chapitre.
- Si la question s'appuie sur un document, tu écris ce document toi-même dans « document » \
(texte court, tableau décrit en toutes lettres, extrait). Tu n'y renvoies jamais à une \
image que l'élève n'a pas.
- « points_attendus » : ce qu'une bonne réponse doit contenir, en 2 à 5 éléments \
vérifiables. C'est le corrigé, l'élève ne le verra qu'après.
- « ou_dans_le_cours » : où l'élève retrouve ça dans SON cours (le titre du chapitre et \
la phrase ou le passage concerné).
- « duree_minutes » : le temps qu'un élève de {niveau} met raisonnablement.
- Le barème n'est pas une note : « poids » vaut 1 pour une question courte, 2 pour une \
question qui demande du développement. Il ne sera jamais montré comme un score.
- Le format décrit ci-dessus donne la charpente ; c'est à toi de l'ajuster au niveau. \
Un exercice de 6e et un exercice de 3e ne demandent ni la même longueur de réponse, ni \
la même autonomie, ni le même vocabulaire. Écris le contrôle pour un élève de {niveau}, \
pas pour la matière en général.
- Le contrôle ne peut pas être un QCM. Quelques questions fermées sont admises en \
partie 1 si la matière et le niveau les pratiquent vraiment, mais l'essentiel doit être \
rédigé : c'est ce qui révèle ce qui n'est pas compris.
{contrainte_notions}{contrainte_deja_posees}"""

SCHEMA_CONTROLE = {
    "type": "object",
    "properties": {
        "titre": {"type": "string"},
        "consigne_generale": {
            "type": "string",
            "description": "Le mot du professeur en tête de sujet, une ou deux phrases.",
        },
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "numero": {"type": "integer"},
                    "partie": {"type": "string", "description": "Ex. « Partie 1 — Connaissances »"},
                    "enonce": {"type": "string"},
                    "document": {"type": "string", "description": "Vide si la question n'en a pas."},
                    "notion": {"type": "string"},
                    "chapitre": {"type": "string"},
                    "points_attendus": {"type": "array", "items": {"type": "string"}},
                    "ou_dans_le_cours": {"type": "string"},
                    "duree_minutes": {"type": "integer"},
                    "poids": {"type": "integer"},
                },
                "required": [
                    "numero", "partie", "enonce", "document", "notion", "chapitre",
                    "points_attendus", "ou_dans_le_cours", "duree_minutes", "poids",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["titre", "consigne_generale", "questions"],
    "additionalProperties": False,
}


# --- 4. Correction commentée ------------------------------------------------

CORRECTION_CONSIGNE = """Corrige les réponses de l'élève à son contrôle blanc.

Pour chaque question, dans l'ordre :
- « statut » : "acquis" si l'essentiel y est, "partiel" s'il manque un élément important, \
"a_revoir" si la notion n'est pas là. Une réponse vide est "a_revoir".
- « ce_qui_va » : ce que l'élève a effectivement produit de juste. Une phrase. Si la \
réponse est vide, laisse ce champ vide plutôt que d'inventer un encouragement creux.
- « ce_qui_manquait » : les éléments attendus absents, formulés comme un professeur les \
écrirait en marge de la copie. Un à trois éléments. Vide si "acquis".
- « erreur_reperee » : quand l'élève ne s'est pas contenté d'oublier mais s'est trompé, \
nomme l'erreur elle-même en une phrase — la règle mal appliquée, la confusion, le calcul \
faux. En mathématiques et en sciences, c'est presque toujours ça qui coince, et un \
« il manquait… » ne décrit pas ce qui s'est passé. Vide s'il n'y a qu'un oubli.
- « ou_dans_ton_cours » : où l'élève va relire ça dans SON cours — le chapitre, puis le \
passage précis. C'est le cœur de la correction, ne le bâcle pas.
- « reponse_attendue » : ce qu'une bonne réponse aurait contenu, en 1 à 3 phrases. Dans \
une matière scientifique, écris la démarche et pas seulement le résultat : c'est elle qui \
est notée.

Ensuite, « notions_fragiles » : au plus 3 notions, les plus rentables à retravailler \
d'ici le contrôle. Tu les classes de la plus fragile à la moins fragile. Pour chacune, \
« pourquoi » explique ce qui coince à partir des réponses de l'élève, pas en général.
Si tout est acquis, tu renvoies une liste vide.

Rappels : aucune note, aucun score, aucun décompte de bonnes réponses, aucun pronostic. \
« mot_de_fin » : deux phrases maximum, ce que l'élève fait maintenant."""

SCHEMA_CORRECTION = {
    "type": "object",
    "properties": {
        "reponses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "numero": {"type": "integer"},
                    "statut": {"type": "string", "enum": ["acquis", "partiel", "a_revoir"]},
                    "ce_qui_va": {"type": "string"},
                    "ce_qui_manquait": {"type": "array", "items": {"type": "string"}},
                    "erreur_reperee": {
                        "type": "string",
                        "description": "L'erreur commise, nommée en une phrase. Vide s'il n'y a qu'un oubli.",
                    },
                    "ou_dans_ton_cours": {"type": "string"},
                    "reponse_attendue": {"type": "string"},
                },
                "required": [
                    "numero", "statut", "ce_qui_va", "ce_qui_manquait", "erreur_reperee",
                    "ou_dans_ton_cours", "reponse_attendue",
                ],
                "additionalProperties": False,
            },
        },
        "notions_fragiles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "notion": {"type": "string"},
                    "chapitre": {"type": "string"},
                    "pourquoi": {"type": "string"},
                },
                "required": ["notion", "chapitre", "pourquoi"],
                "additionalProperties": False,
            },
        },
        "mot_de_fin": {"type": "string"},
    },
    "required": ["reponses", "notions_fragiles", "mot_de_fin"],
    "additionalProperties": False,
}


# --- 5. Fiche ciblée --------------------------------------------------------

FICHE_CIBLEE_CONSIGNE = """Rédige une fiche courte, uniquement sur les notions que \
l'élève vient de rater. Rien d'autre.

Notions à traiter, dans cet ordre :
{notions}

- Une section par notion, pas plus. Chaque section : ce qu'il faut avoir compris \
(3 à 5 points), puis « a_retenir », la phrase à mémoriser.
- Tu pars de l'erreur constatée, tu ne récites pas le chapitre. L'élève a déjà lu son cours.
- « pieges » : la confusion exacte qui l'a fait tomber, et comment l'éviter.
- Fiche courte : elle doit se relire en 5 minutes. C'est sa valeur.
- Pas de note, pas de pronostic."""
