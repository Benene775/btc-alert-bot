"""Le quiz éclair : l'objet complémentaire du contrôle blanc.

Le contrôle fait rédiger, et c'est ce qui révèle ce qu'on n'a pas compris. Mais
rédiger coûte dix minutes par question, et avant un gros contrôle un élève doit
repasser vingt notions en dix. Le quiz fait reconnaître ; la reconnaissance se
répète, et c'est la répétition qui fait tenir.

Ce qui doit tenir, dans l'ordre :

1. Le corrigé ne descend jamais dans le navigateur. Pour un QCM c'est plus vrai
   encore que pour un contrôle : la bonne réponse tient dans un entier, et
   n'importe qui la lirait dans les outils de développement.
2. Répondre ne coûte rien. C'est une lecture du corrigé déjà écrit, pas un
   appel au modèle — sinon un quiz de huit questions se paierait neuf fois.
3. Aucune note, nulle part. À la place, les notions à revoir.
4. Le quiz porte sur un cours vraiment photographié : le TEXTE des pages, pas
   un titre de chapitre.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")

CHAPITRE = {"titre": "Civils et militaires", "notions": ["La guerre totale"],
            "transcription": "…", "photos": [0]}


def _quiz(client: TestClient, session: str):
    reponse = client.post("/api/quiz", json={
        "session_id": session, "niveau": "3e",
        "matiere": "histoire-geographie", "chapitres": [CHAPITRE]})
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


def test_le_corrige_ne_descend_pas_dans_le_navigateur(client, session):
    """La bonne réponse d'un QCM tient dans un entier : envoyée avec l'énoncé,
    elle se lit en trois secondes dans les outils de développement."""
    quiz = _quiz(client, session)
    assert quiz["questions"], "quiz vide"
    for question in quiz["questions"]:
        for interdit in ("juste", "pourquoi_juste", "pourquoi_faux", "ou_dans_le_cours"):
            assert interdit not in question, f"« {interdit} » part avec l'énoncé"
        # Ce qu'il faut bien, en revanche, pour jouer.
        for attendu in ("numero", "enonce", "propositions", "notion"):
            assert attendu in question, f"« {attendu} » manque"
        assert len(question["propositions"]) >= 2


def test_repondre_dit_pourquoi_sans_rien_couter(client, session):
    """Se tromper doit apprendre quelque chose : la phrase qui nomme la
    confusion, ce qu'était la bonne réponse, et où la relire."""
    quiz = _quiz(client, session)
    numero = quiz["questions"][0]["numero"]

    juste = None
    for choix in range(len(quiz["questions"][0]["propositions"])):
        r = client.post("/api/quiz/reponse", json={
            "session_id": session, "quiz_id": quiz["quiz_id"],
            "numero": numero, "choix": choix}).json()
        assert r["pourquoi"], f"le choix {choix} n'explique rien"
        assert r["ou_dans_le_cours"], "aucun renvoi au cours"
        if r["juste"]:
            juste = choix
    assert juste is not None, "aucune proposition n'est juste"

    # Répondre ne consomme aucun quota : le quiz se paie une fois, pas huit.
    # Quatre réponses viennent d'être envoyées ; le second quiz doit donc être
    # le deuxième décompté du jour, pas le sixième.
    from app import config
    second = _quiz(client, session)
    assert second["quotas"]["restant_jour"] == config.QUOTAS["quiz"]["jour"] - 2, \
        second["quotas"]


def test_un_quiz_inconnu_ou_sans_chapitre_est_refuse(client, session):
    _quiz(client, session)
    r = client.post("/api/quiz/reponse", json={
        "session_id": session, "quiz_id": "0" * 32, "numero": 1, "choix": 0})
    assert r.status_code == 404
    r = client.post("/api/quiz", json={"session_id": session, "niveau": "3e",
                                       "matiere": "histoire-geographie", "chapitres": []})
    assert r.status_code == 400


def test_une_question_injouable_est_ecartee():
    """Un index juste hors des propositions rend la question impossible :
    l'élève ne peut avoir raison sur aucun choix. Mieux vaut sept questions que
    huit dont une piégée."""
    from app.main import _question_quiz_tenable

    bonne = {"propositions": ["a", "b", "c", "d"], "juste": 2}
    assert _question_quiz_tenable(bonne)
    for mauvaise in ({"propositions": ["a", "b"], "juste": 5},
                     {"propositions": ["a", "b"], "juste": -1},
                     {"propositions": ["a"], "juste": 0},
                     {"propositions": [], "juste": 0},
                     {"propositions": ["a", "b"], "juste": None}):
        assert not _question_quiz_tenable(mauvaise), mauvaise


def test_la_consigne_interdit_la_note_et_les_fausses_reponses_absurdes():
    """Une proposition manifestement fausse ne fait pas travailler : elle se
    raye sans lire. Les trois fausses doivent être les erreurs que les élèves
    font vraiment."""
    from app import prompts

    consigne = prompts.QUIZ_CONSIGNE
    assert "Pas de note" in consigne
    assert "absurde" in consigne, "rien n'interdit la fausse réponse qui se raye sans lire"
    assert "erreurs que les élèves font vraiment" in consigne
    # Et le contrôle reste ce qu'il est : le quiz ne le remplace pas.
    assert "Le contrôle ne peut pas être un QCM" in prompts.CONTROLE_CONSIGNE


def test_le_quiz_porte_sur_un_cours_vraiment_photographie():
    """Un titre de chapitre n'est pas des pages. Sans transcription il n'y a
    rien à interroger, et le modèle inventerait des questions sur un titre."""
    bloc = SCRIPT[SCRIPT.index("function coursQuizzables"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "c.transcription" in bloc, "un cours sans texte se proposerait au quiz"


def test_le_bilan_du_quiz_ne_donne_pas_de_note():
    """C'est à la fin d'un QCM que « 6/8 » s'écrit tout seul. À cet endroit
    exact, on nomme les notions à revoir."""
    bloc = SCRIPT[SCRIPT.index("function finirQuiz"):]
    bloc = bloc[: bloc.index("\n}\n")]
    for interdit in ("/ ' +", "score", "sur ' +", "%"):
        assert interdit not in bloc, f"« {interdit} » ressemble à une note"
    assert "notions à revoir" in bloc
    assert "Pas de note" in PAGE[PAGE.index('id="quiz-bilan"'):][:1200]


def test_les_trois_outils_sont_visibles_ensemble_sur_sa_page():
    """Le quiz fait reconnaître, le contrôle fait rédiger, la fiche fait
    relire : trois choses différentes, et c'est pour ça qu'elles se présentent
    ensemble. Le choix de l'outil est le geste."""
    espace = PAGE[PAGE.index('id="ecran-espace"') : PAGE.index('id="ecran-matiere"')]
    assert 'id="pan-outils"' in espace
    for outil in ("outil-quiz", "outil-controle", "outil-fiche"):
        assert f'id="{outil}"' in espace, f"« {outil} » manque sur la page perso"
    # Sans cours photographié, on le dit au lieu d'offrir trois boutons morts.
    assert 'id="vide-outils"' in espace
    bloc = SCRIPT[SCRIPT.index("function dessinerAccesQuiz"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "$('vide-outils').hidden" in bloc


def test_les_trois_outils_partagent_un_seul_ecran_de_choix():
    """Ils posent la même question — sur quoi ? — et ne diffèrent qu'ensuite.
    Trois écrans de choix auraient divergé à la première retouche."""
    assert 'id="ecran-atelier"' in PAGE
    for champ in ("atelier-titre", "atelier-chapeau", "bouton-lancer-atelier",
                  "quiz-matiere", "quiz-chapitres"):
        assert f'id="{champ}"' in PAGE, f"« {champ} » manque à l'atelier"

    assert "const OUTILS = {" in SCRIPT
    for outil in ("quiz:", "controle:", "fiche:"):
        assert outil in SCRIPT[SCRIPT.index("const OUTILS = {"):][:1400], outil

    bloc = SCRIPT[SCRIPT.index("async function lancerAtelier"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "lancerQuiz(" in bloc and "demanderFicheGenerale(" in bloc and "lancerControle(" in bloc


def test_choisir_un_perimetre_n_ampute_pas_la_seance():
    """Décocher un chapitre pour une fiche rapide ne doit pas rogner le
    périmètre de la séance : l'élève retrouverait son cours entamé sans savoir
    pourquoi. Les chapitres cochés passent en argument, ils ne marquent rien."""
    bloc = SCRIPT[SCRIPT.index("async function lancerAtelier"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert ".actif" not in bloc, "l'atelier marque les chapitres de la séance"
    assert "async function demanderFicheGenerale(chapitres = null)" in SCRIPT
    assert "async function lancerControle(notionsCiblees = [], chapitres = null)" in SCRIPT
    assert "chapitres: chapitres || chapitresRetenus()" in SCRIPT
