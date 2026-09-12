"""On peut revenir sur une question du contrôle, et la corriger.

On ne pouvait pas. C'était un choix assumé — « pas de retour en arrière, comme
le jour J » — et il était mauvais pour deux raisons.

La première : le jour J, justement, on revient. La copie est sous les yeux, on
relit la 2 en traitant la 5, on corrige une date écrite trop vite. Ce qu'on ne
peut pas faire le jour du contrôle, c'est recommencer. L'interdiction imitait le
mauvais détail du vrai contrôle.

La seconde, et c'est celle qui compte : ici l'élève RÉVISE. Se rappeler à la
question 5 qu'on a mal répondu à la 2, ne pas pouvoir y retourner, et devoir
attendre la correction pour le vérifier — c'est transformer une révision en
punition. Le produit ne met pas de note ; il n'a pas à punir autrement.

Ce qui doit tenir :

1. On circule dans les deux sens, et vers n'importe quelle question.
2. Ce qu'on avait écrit revient tel quel, y compris une réponse jamais validée.
3. Ce qu'on corrige en revenant est ce qui part au serveur.
4. Le fil dit lesquelles sont répondues — sinon on rend sans voir les trous.
5. Plus un seul mot du produit ne promet l'inverse.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

ECRAN = PAGE[PAGE.index('id="ecran-controle"') : PAGE.index("</section>", PAGE.index('id="ecran-controle"'))]


def bloc(nom: str) -> str:
    debut = SCRIPT.index("function " + nom + "(")
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_on_circule_dans_les_deux_sens():
    assert 'id="bouton-question-precedente"' in ECRAN
    assert 'id="bouton-question-suivante"' in ECRAN
    assert "$('bouton-question-precedente').onclick = questionPrecedente;" in SCRIPT
    # Et vers n'importe laquelle, par le fil : « à n'importe quel moment ».
    assert "pastille.onclick = () => allerAQuestion(rang);" in bloc("dessinerFilDesQuestions")
    # Le retour disparaît sur la première : il n'y a rien derrière.
    assert "$('bouton-question-precedente').hidden = controleEnCours.index === 0;" in SCRIPT


def test_ce_qu_on_avait_ecrit_revient():
    """Y compris une réponse en cours de frappe, jamais validée : mémoriser
    seulement à « Suivante » l'aurait effacée au premier retour en arrière — ce
    qui serait pire que de ne pas pouvoir revenir du tout."""
    assert "function memoriserReponse()" in SCRIPT
    for chemin in ("allerAQuestion", "questionSuivante", "terminerControle"):
        assert "memoriserReponse()" in bloc(chemin), \
            f"« {chemin} » quitte la question sans mémoriser ce qui est écrit"
    assert "$('champ-reponse').value = controleEnCours.reponses[question.numero] || '';" in SCRIPT


def test_la_correction_recoit_la_derniere_version():
    """« On écrase, on ne complète pas » : l'ancien code n'enregistrait la
    réponse affichée que si la question n'en avait pas déjà une, ce qui aurait
    jeté toute correction faite en revenant."""
    fin = bloc("terminerControle")
    assert "reponses[courante.numero] === undefined" not in fin, \
        "une correction de dernière seconde serait ignorée"
    memoriser = bloc("memoriserReponse")
    assert "controleEnCours.reponses[question.numero] = $('champ-reponse').value" in memoriser


def test_le_fil_dit_ce_qui_est_repondu():
    assert 'id="fil-questions"' in ECRAN
    fil = bloc("dessinerFilDesQuestions")
    assert "pastille.dataset.repondue = 'oui'" in fil
    assert "aria-current" in fil, "le fil ne dit pas où l'on est aux lecteurs d'écran"
    assert '.fil-pas[data-repondue="oui"]' in STYLE
    assert '.fil-pas[aria-current="true"]' in STYLE
    # La jauge qu'il remplace ne disait qu'une chose et ne commandait rien.
    assert "jauge-remplie" not in PAGE and "jauge-remplie" not in SCRIPT

    # Et sur la question d'où l'on rend, on compte les trous qui restent : la
    # circulation libre rend le saut possible, donc l'oubli aussi.
    assert 'id="reste-sans-reponse"' in ECRAN
    assert "sans réponse — les cases vides du fil te disent lesquelles" in SCRIPT


def test_plus_rien_ne_promet_l_inverse():
    """On ne regarde que ce que l'élève LIT. Le script a le droit d'expliquer en
    commentaire pourquoi on a changé d'avis — c'est même le seul endroit où
    cette histoire est écrite."""
    for mot in ("retour en arrière", "revenir en arrière", "comme le jour J"):
        assert mot not in PAGE, f"« {mot} » se lit encore dans la page"
    assert "Tu peux revenir sur une question" in PAGE
    demo = (RACINE / "app" / "demo.py").read_text(encoding="utf-8")
    assert "Tu ne peux pas revenir en arrière" not in demo
    # La consigne du modèle disait « sans retour en arrière possible » pour
    # justifier la recopie des documents. La recopie reste — deux questions ne
    # sont jamais visibles ensemble — mais la raison a changé.
    prompts = (RACINE / "app" / "prompts.py").read_text(encoding="utf-8")
    assert "sans retour en arrière possible" not in prompts
    assert "Il peut revenir sur les" in prompts
    assert "tu le \\\nrecopies EN ENTIER" in prompts or "recopies EN ENTIER" in prompts
