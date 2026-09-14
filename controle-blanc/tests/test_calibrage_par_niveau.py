"""La classe de l'élève doit changer ce qu'on lui sert.

Un 6e et un 3e ne reçoivent pas la même chose — pas le même CONTENU, qui sort
de leurs cahiers respectifs, mais la même exigence : longueur des réponses,
autonomie, vocabulaire, longueur des phrases.

MESURÉ, pas supposé. Même cours (le Néolithique, corpus d'histoire 6e), deux
niveaux déclarés, un appel réel par cas :

    contrôle 6e ... 8 questions, 55 mots/énoncé, 13,2 mots par critère attendu
    contrôle 3e ... 6 questions, 66 mots/énoncé, 20,3 mots par critère attendu

Le sens est le bon : au 6e, plus de questions, plus courtes, plus guidées — des
définitions, un vrai/faux justifié, un document recopié en entier, et jusqu'au
vocabulaire suggéré pour le paragraphe final. Au 3e, moins de questions, plus
longues, dont une comparaison à conclure et un développement construit avec
« une introduction, un développement organisé en plusieurs idées, et une
conclusion ».

LA FICHE, ELLE, NE BOUGEAIT PAS. La même mesure donnait quatre parties dans les
deux cas, et des titres qui allaient dans le mauvais sens : le 6e recevait « Le
passage de la prédation à la production » quand le 3e recevait « Qu'est-ce que
le Néolithique ? ». La consigne de la fiche ne disait rien du niveau — une
seule ligne de préambule sur le registre de langue, contre un paragraphe entier
côté contrôle. C'est ce que ce fichier garde.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PROMPTS = (RACINE / "app" / "prompts.py").read_text(encoding="utf-8")
LLM = (RACINE / "app" / "llm.py").read_text(encoding="utf-8")


def test_le_niveau_atteint_les_quatre_appels():
    """Fiche, fiche ciblée, contrôle, correction : le préambule les porte tous,
    et c'est lui qui dit à qui l'on parle."""
    assert "adapté à un élève de {niveau}" in PROMPTS
    assert LLM.count("_systeme_avec_cours(niveau, chapitres,") == 4
    for action in ("fiche_generale", "fiche_ciblee", "controle", "correction"):
        assert f'_systeme_avec_cours(niveau, chapitres, "{action}")' in LLM


def test_le_controle_ajuste_son_exigence_au_niveau():
    """Le format d'une matière est le même de la 6e à la terminale : c'est une
    charpente. Ce qui change, c'est ce qu'on demande à l'élève d'en faire."""
    consigne = PROMPTS[PROMPTS.index("CONTROLE_CONSIGNE = "):]
    consigne = consigne[: consigne.index('"""', consigne.index('"""') + 3)]
    assert "c'est à toi de l'ajuster au niveau" in consigne
    assert "ni la même longueur de réponse, ni \\\nla même autonomie, ni le même vocabulaire" \
        in consigne or "la même autonomie" in consigne
    assert "pas pour la matière en général" in consigne


def test_la_fiche_aussi():
    """Elle ne le faisait pas. Une seule ligne de préambule sur le registre de
    langue ne suffit pas : mesuré sur le même cours, les deux niveaux rendaient
    la même fiche, aux titres près — et les titres allaient dans le mauvais
    sens."""
    consigne = PROMPTS[PROMPTS.index("FICHE_GENERALE_CONSIGNE = "):]
    consigne = consigne[: consigne.index('"""', consigne.index('"""') + 3)]
    assert "{niveau}" in consigne, "la consigne de la fiche ignore la classe"
    assert "pas pour la matière en général" in consigne
    # Ce qui change et ce qui ne change pas : le niveau ne fait pas sortir du
    # cours de l'élève, il change la façon de le dire.
    assert "tu ne sors jamais des pages de l'élève" in consigne
    assert "En 6e et 5e" in consigne and "En 3e et au lycée" in consigne

    ciblee = PROMPTS[PROMPTS.index("FICHE_CIBLEE_CONSIGNE = "):]
    ciblee = ciblee[: ciblee.index('"""', ciblee.index('"""') + 3)]
    assert "{niveau}" in ciblee


def test_la_consigne_recoit_vraiment_le_niveau():
    """« {niveau} » écrit dans une chaîne qu'on n'appelle jamais avec « niveau= »
    part tel quel au modèle, accolades comprises. Personne ne le verrait."""
    assert "prompts.FICHE_GENERALE_CONSIGNE.format(niveau=niveau)" in LLM
    assert "prompts.FICHE_CIBLEE_CONSIGNE.format(notions=liste, niveau=niveau)" in LLM
