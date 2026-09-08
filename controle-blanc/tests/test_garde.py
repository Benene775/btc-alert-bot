"""La garde elle-même : ses vérifications doivent tenir sans appeler le modèle.

« outils/garde.py » lance la chaîne sur trois cours et vérifie ce qui doit
rester vrai. Ce fichier-ci vérifie la garde : qu'elle laisse passer un contrôle
correct, et qu'elle attrape chacune des cassures qu'elle prétend attraper.

Sans ça, la garde peut devenir un tampon vert qui ne regarde plus rien — et on
ne s'en apercevrait qu'en payant 0,33 $ le passage pour rien.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("garde", RACINE / "outils" / "garde.py")
garde = importlib.util.module_from_spec(_spec)
sys.modules["garde"] = garde
_spec.loader.exec_module(garde)


NOTIONS = [
    "La domestication des plantes et des animaux",
    "La naissance de l'agriculture et de l'élevage",
    "La sédentarisation et les premiers villages",
    "L'invention de la poterie et du tissage",
]


def fiche_correcte() -> dict:
    return {
        "titre": "La révolution néolithique",
        "duree_lecture_minutes": 6,
        "sections": [
            {"titre": "Domestication des plantes et des animaux",
             "points": ["Les hommes domestiquent le blé et l'orge.",
                        "Ils domestiquent aussi chèvres et moutons."],
             "a_retenir": "Domestiquer, c'est choisir les espèces qu'on élève."},
            {"titre": "Naissance de l'agriculture et de l'élevage",
             "points": ["L'agriculture apparaît au Proche-Orient.",
                        "L'élevage suit de peu la culture des céréales."],
             "a_retenir": "Agriculture et élevage naissent ensemble."},
            {"titre": "Sédentarisation et premiers villages",
             "points": ["Les hommes deviennent sédentaires.",
                        "Les premiers villages apparaissent."],
             "a_retenir": "Se sédentariser, c'est cesser de suivre le gibier."},
            {"titre": "Poterie et tissage",
             "points": ["L'invention de la poterie permet de stocker.",
                        "Le tissage habille autrement qu'avec des peaux."],
             "a_retenir": "Stocker change tout : on peut garder les récoltes."},
        ],
        "definitions": [
            {"terme": "Néolithique", "definition": "L'âge de la pierre polie."},
            {"terme": "Sédentaire", "definition": "Qui vit toute l'année au même endroit."},
            {"terme": "Domestication", "definition": "Élever une espèce sauvage pour en vivre."},
        ],
        "pieges": ["Ne confonds pas domestication et apprivoisement.",
                   "Le Néolithique n'est pas une révolution rapide : elle dure des siècles."],
    }


def question(numero: int, **remplace) -> dict:
    base = {
        "numero": numero,
        "enonce": "Explique comment la domestication des plantes et de l'élevage "
                  "a rendu les hommes sédentaires dans les premiers villages.",
        "notion": "Sédentarisation, agriculture et élevage, domestication, poterie",
        "points_attendus": ["La domestication précède la sédentarisation.",
                            "L'agriculture fixe les hommes près des champs."],
        "ou_dans_le_cours": "Partie II, « Des villages permanents »",
        "duree_minutes": 8,
    }
    base.update(remplace)
    return base


def controle_correct() -> dict:
    return {"questions": [question(n) for n in range(1, 7)]}


def correction_correcte() -> dict:
    return {
        "reponses": [
            {"numero": 1, "statut": "a_revoir", "ou_dans_ton_cours": "Partie II"},
            {"numero": 2, "statut": "partiel", "ou_dans_ton_cours": "Partie I"},
            {"numero": 3, "statut": "acquis", "ou_dans_ton_cours": ""},
        ],
        "notions_fragiles": [
            {"notion": "La sédentarisation", "pourquoi": "La réponse ne dit pas pourquoi."},
        ],
    }


QUESTIONS = [{"numero": 1}, {"numero": 2}, {"numero": 3}]


# --- Ce qui est correct passe ------------------------------------------------

def test_une_fiche_correcte_passe():
    garde.verifier_fiche(fiche_correcte(), NOTIONS)


def test_un_controle_correct_passe():
    garde.verifier_controle(controle_correct(), NOTIONS, 55)


def test_une_correction_correcte_passe():
    garde.verifier_correction(correction_correcte(), QUESTIONS, {1, 2})


# --- Chaque cassure que la garde prétend attraper ----------------------------

def test_une_fiche_sans_pieges_est_attrapee():
    """Sans ses pièges, la fiche redevient un résumé."""
    fiche = fiche_correcte()
    fiche["pieges"] = ["un seul"]
    with pytest.raises(garde.Manque, match="piège"):
        garde.verifier_fiche(fiche, NOTIONS)


def test_une_section_sans_a_retenir_est_attrapee():
    fiche = fiche_correcte()
    fiche["sections"][1]["a_retenir"] = "  "
    with pytest.raises(garde.Manque, match="à retenir"):
        garde.verifier_fiche(fiche, NOTIONS)


def test_une_fiche_hors_sujet_est_attrapee():
    """Une fiche qui ne parle pas du cours photographié est le pire des ratés :
    c'est le contenu générique qu'on refuse de vendre."""
    fiche = fiche_correcte()
    for section in fiche["sections"]:
        section["titre"] = "Le théorème de Pythagore"
        section["points"] = ["Le carré de l'hypoténuse."] * 2
        section["a_retenir"] = "Le carré de l'hypoténuse."
    with pytest.raises(garde.Manque, match="ne couvre"):
        garde.verifier_fiche(fiche, NOTIONS)


@pytest.mark.parametrize("enonce", [
    "Coche la bonne réponse : le Néolithique commence vers 10 000 av. J.-C., "
    "vers 3300 av. J.-C. ou vers 800 av. J.-C. ?",
    "Entoure la réponse exacte parmi les trois suivantes.",
    "Parmi ces propositions, laquelle décrit la sédentarisation ?",
])
def test_un_qcm_est_attrape(enonce):
    """Une question fermée passe — la consigne en admet quelques-unes en
    partie 1. Deux, c'est le contrôle qui bascule en quiz."""
    controle = controle_correct()
    controle["questions"][2]["enonce"] = enonce
    garde.verifier_controle(controle, NOTIONS, 55)

    controle["questions"][4]["enonce"] = enonce
    with pytest.raises(garde.Manque, match="au lieu de rédiger") as echec:
        garde.verifier_controle(controle, NOTIONS, 55)
    # Le message doit porter la preuve : sans elle, il faut relancer la garde
    # pour comprendre, et relancer coûte trente centimes.
    assert "«" in str(echec.value), "le message ne montre pas l'énoncé fautif"


@pytest.mark.parametrize("enonce", [
    # La numérotation normale des sous-questions d'un exercice.
    "a) Explique la domestication des plantes. "
    "b) Montre en quoi l'élevage rend les hommes sédentaires.",
    # Une consigne de cartographie : « entoure » sans choix à faire.
    "Entoure sur la carte les régions où l'agriculture et l'élevage "
    "apparaissent, puis explique la sédentarisation des premiers villages.",
    # « Choisis » un exemple, ce qui demande de rédiger, pas de cocher.
    "Choisis un des villages étudiés en cours et explique comment la "
    "domestication des plantes y a permis la sédentarisation.",
])
def test_ce_qui_ressemble_a_un_qcm_sans_en_etre_passe(enonce):
    """Chacun de ces trois énoncés a fait échouer une version du motif. Un signe
    de QCM pris isolé ne veut rien dire : il faut le verbe ET le choix."""
    controle = controle_correct()
    controle["questions"][0]["enonce"] = enonce
    garde.verifier_controle(controle, NOTIONS, 55)


def test_un_controle_devenu_quiz_est_attrape():
    """Douze questions de quatre minutes : la durée totale reste dans le format,
    mais plus rien ne se rédige."""
    controle = {"questions": [question(n, duree_minutes=4,
                                       points_attendus=["un mot", "un autre"])
                              for n in range(1, 13)]}
    with pytest.raises(garde.Manque, match="quiz"):
        garde.verifier_controle(controle, NOTIONS, 55)


def test_une_question_qui_ne_renvoie_nulle_part_est_attrapee():
    """Renvoyer à l'endroit du cours est toute la thèse du produit."""
    controle = controle_correct()
    controle["questions"][3]["ou_dans_le_cours"] = ""
    with pytest.raises(garde.Manque, match="renvoie à aucun endroit"):
        garde.verifier_controle(controle, NOTIONS, 55)


def test_une_seule_question_maigre_est_toleree_pas_deux():
    """Le schéma n'impose pas les « 2 à 5 éléments » que demande la consigne :
    le modèle en écrit parfois un seul. Une garde qui échoue là-dessus est une
    garde qu'on cesse de lancer."""
    controle = controle_correct()
    controle["questions"][0]["points_attendus"] = ["seul"]
    garde.verifier_controle(controle, NOTIONS, 55)

    controle["questions"][1]["points_attendus"] = ["seul"]
    with pytest.raises(garde.Manque, match="corrigeables"):
        garde.verifier_controle(controle, NOTIONS, 55)


def test_un_controle_hors_sujet_est_attrape():
    controle = {"questions": [question(
        n,
        notion="Le théorème de Pythagore",
        enonce="Calcule la longueur de l'hypoténuse de ce triangle rectangle.",
        points_attendus=["Le carré de l'hypoténuse.", "La racine carrée du total."],
        ou_dans_le_cours="Chapitre 7, « Triangle rectangle »",
    ) for n in range(1, 7)]}
    with pytest.raises(garde.Manque, match="ne touche que"):
        garde.verifier_controle(controle, NOTIONS, 55)


def test_une_note_chiffree_est_attrapee():
    """Le seul interdit absolu du produit."""
    correction = correction_correcte()
    correction["reponses"][0]["ou_dans_ton_cours"] = "Correct : tu aurais 12 à ce contrôle."
    with pytest.raises(garde.Manque, match="met une note"):
        garde.verifier_correction(correction, QUESTIONS, {1, 2})


def test_une_reponse_absurde_jugee_acquise_est_attrapee():
    """La garde répond volontairement à côté sur deux questions : si elles
    ressortent acquises, la correction ne corrige rien."""
    correction = correction_correcte()
    correction["reponses"][0]["statut"] = "acquis"
    with pytest.raises(garde.Manque, match="absurde"):
        garde.verifier_correction(correction, QUESTIONS, {1, 2})


def test_une_reponse_a_revoir_doit_dire_ou_relire():
    correction = correction_correcte()
    correction["reponses"][0]["ou_dans_ton_cours"] = ""
    with pytest.raises(garde.Manque, match="où relire"):
        garde.verifier_correction(correction, QUESTIONS, {1, 2})


def test_trop_de_doutes_est_attrape():
    analyse = {"photos": [{"lisible": True}],
               "chapitres": [{"transcription": "du texte", "notions": ["a", "b", "c"]}],
               "doutes": [{"lu": "x", "pourquoi": "y"} for _ in range(9)]}
    with pytest.raises(garde.Manque, match="plafond"):
        garde.verifier_analyse(analyse, 7)


def test_une_analyse_correcte_passe():
    analyse = {"photos": [{"lisible": True}],
               "chapitres": [{"transcription": "du texte", "notions": ["a", "b", "c"]}],
               "doutes": [{"lu": "interfécondité", "pourquoi": "écriture peu nette"}]}
    garde.verifier_analyse(analyse, 7)


# --- Les cas eux-mêmes -------------------------------------------------------

def test_les_trois_cas_existent_dans_le_corpus():
    """Un cas qui pointe sur un chapitre disparu ferait échouer la garde pour
    une raison qui n'a rien à voir avec le produit."""
    sys.path.insert(0, str(RACINE / "outils"))
    from essai import corpus_disponible
    connus = {c["id"] for c in corpus_disponible()}
    for cas in garde.CAS:
        assert cas["corpus"] in connus, f"« {cas['corpus'] } » n'est plus dans le corpus"
    assert sum(1 for c in garde.CAS if c["corriger"]) == 1, (
        "la correction est l'étape la plus chère : un seul cas doit la lancer")
