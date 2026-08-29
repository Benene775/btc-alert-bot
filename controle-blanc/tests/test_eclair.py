"""Le contrôle éclair de la page d'accueil.

Ce que c'est : le produit, jouable avant même de s'inscrire. On prête un extrait
de cours, on pose trois questions dessus, et on rend ce que Repère rend
vraiment.

Ce qui doit tenir, dans l'ordre d'importance :

1. Aucune note, jamais. C'est la règle du produit, et c'est ici qu'elle est la
   plus fragile : à la fin d'un questionnaire, « 2/3 » s'écrit tout seul. Le
   verdict nomme les notions fragiles et l'endroit du cours où les relire.
2. Rien ne part sur le réseau. Un visiteur qui joue ne doit rien coûter : les
   questions, les réponses et les corrections sont écrites dans la page.
3. Les questions se tiennent : trois choix, une seule bonne réponse, une
   correction pour chacun. Une faute de frappe dans un « data-juste » rendrait
   une question infaisable sans que rien ne le signale.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

ACCUEIL = PAGE.split('id="ecran-accueil"')[1].split('id="ecran-connexion"')[0]
ARME = SCRIPT[SCRIPT.index("function armerEclair"):]
ARME = ARME[: ARME.index("\n}\n")]


class _Questions(HTMLParser):
    """Relève les trois questions et leurs choix, tels qu'ils sont écrits."""

    def __init__(self) -> None:
        super().__init__()
        self.questions: list[dict] = []
        self._dans_choix = False

    def handle_starttag(self, tag, attributs):
        a = dict(attributs)
        classes = (a.get("class") or "").split()
        if "eclair-q" in classes:
            self.questions.append({"notion": a.get("data-notion"),
                                   "ou": a.get("data-ou"), "choix": []})
        elif "eclair-choix" in classes:
            self._dans_choix = True
        elif tag == "button" and self._dans_choix and self.questions:
            self.questions[-1]["choix"].append(
                {"juste": a.get("data-juste"), "note": a.get("data-note")})

    def handle_endtag(self, tag):
        if tag == "div":
            self._dans_choix = False


def _questions() -> list[dict]:
    analyseur = _Questions()
    analyseur.feed(ACCUEIL)
    return analyseur.questions


def test_le_verdict_ne_donne_jamais_de_note():
    """La règle du produit, à l'endroit exact où elle est le plus tentante à
    trahir : au bout d'un questionnaire, « 2/3 » s'écrit tout seul. Ce que
    Repère rend, c'est ce qu'il reste à revoir — jamais ce que l'élève vaudrait.
    """
    verdict = ARME[ARME.index("function direCeQuiManque"):]

    # Ni fraction, ni pourcentage, ni vocabulaire de note.
    for forme in (r"/\s*20", r"/\s*3\b", r"\bsur\s+3\b", r"%'"):
        assert not re.search(forme, verdict), f"une note apparaît dans le verdict ({forme})"
    for mot in ("note :", "score", "points", "moyenne", "/20"):
        assert mot not in verdict.lower(), f"« {mot} » n'a rien à faire dans le verdict"

    # Ce qu'il rend à la place : la notion, et où la relire.
    assert "dataset.notion" in verdict, "le verdict ne nomme pas les notions"
    assert "dataset.ou" in verdict, "le verdict ne dit pas où relire"
    assert "Pas de note" in verdict, "la règle n'est pas écrite là où on attend la note"


def test_jouer_ne_coute_rien():
    """Un visiteur qui joue ne doit rien coûter : pas d'appel au modèle, pas de
    requête. Tout — questions, réponses, corrections — est écrit dans la page.
    """
    for appel in ("fetch(", "api(", "XMLHttpRequest", "navigator.sendBeacon"):
        assert appel not in ARME, f"« {appel} » : le contrôle éclair appelle le réseau"
    # Les corrections sont dans la page, pas fabriquées à la volée.
    assert ACCUEIL.count("data-note=") == 9, "les neuf corrections ne sont pas écrites dans la page"


def test_chaque_question_se_tient():
    """Trois choix, une seule bonne réponse, une correction pour chacun, une
    notion nommée et un endroit où la relire. Une faute de frappe dans un
    « data-juste » rendrait la question infaisable sans rien signaler."""
    questions = _questions()
    assert len(questions) == 3, f"{len(questions)} question(s) au lieu de trois"

    for rang, q in enumerate(questions, 1):
        assert q["notion"], f"question {rang} : aucune notion nommée"
        assert q["ou"], f"question {rang} : on ne dit pas où relire"
        assert len(q["choix"]) == 3, f"question {rang} : {len(q['choix'])} choix"
        justes = [c for c in q["choix"] if c["juste"] == "oui"]
        assert len(justes) == 1, f"question {rang} : {len(justes)} bonne(s) réponse(s)"
        for c in q["choix"]:
            assert c["juste"] in ("oui", "non"), f"question {rang} : « data-juste » douteux"
            assert c["note"] and len(c["note"]) > 30, \
                f"question {rang} : une correction manque ou tient en trois mots"

    # Les notions sont distinctes : trois fois la même ligne dans le verdict
    # ne dirait rien à personne.
    noms = [q["notion"] for q in questions]
    assert len(set(noms)) == 3, f"deux questions portent la même notion : {noms}"


def test_la_carte_reste_lisible_si_le_script_ne_l_arme_pas():
    """Toute l'application demande JavaScript : la question n'est pas « et sans
    JS ? » mais « et si cette fonction-là échoue ? ». Rien ne doit être masqué
    par la feuille de style, sinon la page d'accueil garde un cadre vide en son
    milieu."""
    assert "hidden" not in ACCUEIL.split('class="eclair-q"')[1].split(">")[0]

    # Même règle que pour les révélations : cacher est permis, mais seulement
    # derrière un état que le script pose. « data-replie » en est un — c'est
    # ainsi qu'une question corrigée se referme quand on passe à la suivante.
    #
    # On regarde chaque sélecteur du groupe, pas le groupe entier : une règle
    # « .eclair-q .eclair-choix, .eclair-q[data-replie="oui"] .eclair-note »
    # contient bien « data-replie », et cacherait pourtant les réponses de
    # toutes les questions.
    for groupe, corps in re.findall(r"([^{}]*\.eclair-q[^{}]*)\{([^}]*)\}", STYLE):
        if "display: none" not in corps:
            continue
        for selecteur in groupe.split(","):
            if ".eclair-q" not in selecteur:
                continue
            assert "data-replie" in selecteur, \
                f"« {selecteur.strip()} » cache les questions sans garde JavaScript"
    assert "dataset.replie = 'oui'" in ARME, "le script ne pose jamais l'état replié"
    # C'est le script qui masque, et il le fait après avoir trouvé ses trois
    # questions — pas avant.
    assert "questions.forEach((q) => { q.hidden = true; });" in ARME
    assert ARME.index("questions.length !== 3") < ARME.index("q.hidden = true")


def test_l_eclair_tient_la_colonne_de_lecture_au_large():
    """À 900 px, « .bloc » devient une marge de cahier de 210 px plus le corps.
    Sans placement explicite, la carte tombait dans la marge et le cours se
    lisait un mot par ligne — c'est ce qu'on voyait à 1280 px."""
    large = STYLE[STYLE.index("@media (min-width: 900px)"):]
    regle = re.search(r"\.deroule, \.eclair \{ grid-column: 2; \}", large)
    assert regle, "« .eclair » n'est pas placé dans la colonne de lecture"


def test_la_jauge_ne_mesure_rien_avant_la_premiere_question():
    """Trois traits vides au-dessus d'un cours qu'on est en train de lire
    ressemblent à une barre de progression à zéro : ils annoncent un score."""
    assert "'eclair-jauge'" in ARME
    pose = ARME.index("$('eclair-jauge').hidden = false;")
    assert ARME.index("function poserQuestion") < pose, \
        "la jauge s'affiche avant la première question"


def test_une_question_corrigee_se_replie_quand_on_passe_a_la_suivante():
    """Trois questions corrigées dépliées faisaient une carte de 4 000 px : on
    défilait dans ses propres réponses pour trouver le verdict. Repliée, une
    question garde sa trace — l'énoncé et la marque — sans garder la place."""
    assert "questions[rang].dataset.replie = 'oui';" in ARME
    # Le repli précède l'avancement : replier après aurait fermé la suivante.
    poser = ARME[ARME.index("function poserQuestion"):]
    poser = poser[: poser.index("\n  }\n")]
    assert poser.index("dataset.replie") < poser.index("rang += 1"), \
        "on replie la mauvaise question"
    # La marque ✓ / ✗ de la ligne repliée vient de la réponse donnée.
    assert "question.dataset.juste =" in ARME
    for etat in ('[data-replie="oui"][data-juste="oui"]', '[data-replie="oui"][data-juste="non"]'):
        assert etat in STYLE, f"la ligne repliée ne porte pas sa marque ({etat})"
