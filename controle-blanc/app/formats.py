"""Format réel d'un contrôle, par matière.

C'est ce qui distingue « un quiz généré » d'« un contrôle blanc » : un contrôle
d'histoire-géo ne ressemble pas à un contrôle de maths. Ces descriptions sont
injectées telles quelles dans le prompt de génération.

Ajouter une matière = ajouter une entrée ici, rien d'autre.
"""

from __future__ import annotations

from typing import TypedDict


class Format(TypedDict):
    nom: str
    duree_minutes: int
    structure: str


FORMATS: dict[str, Format] = {
    "francais": {
        "nom": "Français",
        "duree_minutes": 55,
        "structure": (
            "Un court texte ou extrait tiré du cours, suivi de questions de compréhension "
            "(3 à 5), puis 2 questions de langue (grammaire, conjugaison, vocabulaire ou "
            "figures de style vues en cours), puis une question d'écriture courte "
            "(un paragraphe argumenté ou rédigé, 8 à 12 lignes attendues)."
        ),
    },
    "mathematiques": {
        "nom": "Mathématiques",
        "duree_minutes": 55,
        "structure": (
            "Exercice 1 : questions d'application directe du cours (calcul, propriété à "
            "reconnaître). Exercice 2 : exercice guidé en 2 ou 3 questions qui s'enchaînent. "
            "Exercice 3 : un problème court à mettre en équation ou à justifier. "
            "Toujours demander la justification, pas seulement le résultat."
        ),
    },
    "histoire-geographie": {
        "nom": "Histoire-Géographie / EMC",
        "duree_minutes": 55,
        "structure": (
            "Partie 1 : questions de connaissances (dates, acteurs, définitions du cours). "
            "Partie 2 : étude d'un document court (texte de 4 à 8 lignes, ou description "
            "précise d'une carte ou d'une image) avec 2 ou 3 questions dont une de "
            "confrontation avec le cours. Partie 3 : un développement construit / paragraphe "
            "argumenté sur un sujet du chapitre."
        ),
    },
    "svt": {
        "nom": "SVT",
        "duree_minutes": 50,
        "structure": (
            "Partie 1 : restitution des connaissances (définitions, mécanisme à expliquer). "
            "Partie 2 : exploitation d'un document (résultat d'expérience, schéma, tableau de "
            "données décrit en toutes lettres) — « que peut-on en déduire ? ». "
            "Partie 3 : raisonnement scientifique reliant document et cours."
        ),
    },
    "physique-chimie": {
        "nom": "Physique-Chimie",
        "duree_minutes": 50,
        "structure": (
            "Exercice 1 : questions de cours (définition, loi, unité, formule). "
            "Exercice 2 : application numérique avec une formule du cours — la démarche et "
            "les unités comptent autant que le résultat. Exercice 3 : analyse d'une "
            "expérience ou d'un montage vu en cours."
        ),
    },
    "technologie": {
        "nom": "Technologie",
        "duree_minutes": 45,
        "structure": (
            "Questions de vocabulaire technique, lecture d'un schéma ou d'une chaîne "
            "d'information décrite en toutes lettres, puis un cas concret à analyser "
            "(fonction, contrainte, solution technique)."
        ),
    },
    "anglais": {
        "nom": "Anglais",
        "duree_minutes": 45,
        "structure": (
            "Compréhension : un court texte en anglais dans le vocabulaire du chapitre, avec "
            "3 questions. Langue : 3 questions ciblées sur le point de grammaire et le lexique "
            "du cours. Expression : une production écrite courte (5 à 8 phrases) sur le thème "
            "du chapitre. Les consignes sont en français, les réponses attendues en anglais."
        ),
    },
    "espagnol": {
        "nom": "Espagnol",
        "duree_minutes": 45,
        "structure": (
            "Compréhension d'un court texte en espagnol, 3 questions de langue sur le point "
            "de grammaire et le lexique du cours, une expression écrite courte. "
            "Consignes en français, réponses attendues en espagnol."
        ),
    },
    "allemand": {
        "nom": "Allemand",
        "duree_minutes": 45,
        "structure": (
            "Compréhension d'un court texte en allemand, 3 questions de langue sur le point "
            "de grammaire et le lexique du cours, une expression écrite courte. "
            "Consignes en français, réponses attendues en allemand."
        ),
    },
    "ses": {
        "nom": "SES",
        "duree_minutes": 55,
        "structure": (
            "Mobilisation des connaissances (2 questions : définir, illustrer). "
            "Étude d'un document statistique décrit en toutes lettres (lecture d'une donnée, "
            "puis interprétation). Raisonnement s'appuyant sur un mécanisme du cours."
        ),
    },
    "philosophie": {
        "nom": "Philosophie",
        "duree_minutes": 60,
        "structure": (
            "Explication d'une notion ou d'une distinction conceptuelle du cours, "
            "analyse d'une courte citation vue en cours, puis un problème à formuler et "
            "à discuter en un paragraphe avec un exemple et une objection."
        ),
    },
    "autre": {
        "nom": "Autre matière",
        "duree_minutes": 50,
        "structure": (
            "Partie 1 : questions de connaissances directes issues du cours (définitions, "
            "faits, méthode). Partie 2 : une application ou un cas concret à traiter. "
            "Partie 3 : une question de synthèse qui relie deux notions du chapitre."
        ),
    },
}

DEFAUT = "autre"


def format_matiere(cle: str | None) -> Format:
    """Renvoie le format d'une matière, avec repli sur un format générique."""
    if cle:
        normalise = cle.strip().lower().replace("_", "-")
        if normalise in FORMATS:
            return FORMATS[normalise]
    return FORMATS[DEFAUT]


def liste_matieres() -> list[dict[str, str]]:
    """Pour peupler le sélecteur côté navigateur."""
    return [{"cle": cle, "nom": f["nom"]} for cle, f in FORMATS.items()]


# Le sélecteur de niveau existe (demandé), mais on ne teste qu'un seul niveau en v1.
NIVEAUX = [
    {"cle": "6e", "nom": "6e"},
    {"cle": "5e", "nom": "5e"},
    {"cle": "4e", "nom": "4e"},
    {"cle": "3e", "nom": "3e"},
    {"cle": "2de", "nom": "Seconde"},
    {"cle": "1re", "nom": "Première"},
    {"cle": "terminale", "nom": "Terminale"},
]


def nom_niveau(cle: str | None) -> str:
    for n in NIVEAUX:
        if n["cle"] == cle:
            return n["nom"]
    return "collège"
