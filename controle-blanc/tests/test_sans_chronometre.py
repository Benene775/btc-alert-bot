"""Le contrôle blanc n'est pas chronométré.

Il l'a été : un compte à rebours en face de la progression, qui passait au
rouge sous deux minutes et terminait la copie tout seul à zéro. L'intention
était juste — « au format réel », et un vrai contrôle a une durée. Le résultat
ne l'était pas : un élève qui révise chez lui, le soir, seul, n'a rien à gagner
à se battre contre une horloge. Le produit promet de ne jamais mettre de note ;
lui mettre un chronomètre sous les yeux revient à la même chose par un autre
chemin — une pression qu'on subit au lieu d'un cours qu'on relit.

Ce qui doit tenir :

1. Aucun compte à rebours, nulle part.
2. Aucune durée ne quitte le serveur. Une durée affichée est un chronomètre qui
   s'ignore : « 40 min » sur une porte produit la même appréhension que 39:58
   qui défile.
3. Aucun mot du produit ne dit que le contrôle est chronométré.
4. Mais le sujet reste calibré sur un vrai contrôle. La durée cible du format
   et celle des questions restent côté serveur, où elles disent au modèle quelle
   taille faire et où la garde s'en sert pour distinguer un contrôle d'un quiz.
   « Au format réel de la matière » est la promesse du produit, et la longueur
   fait partie du format.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")
DEVANT = (PAGE, SCRIPT, STYLE)


def test_aucun_compte_a_rebours():
    for quoi, source in zip(("la page", "le script", "le style"), DEVANT):
        for trace in ("chrono", "finPrevue", "minuteur "):
            assert trace not in source, f"« {trace} » est revenu dans {quoi}"
    assert 'role="timer"' not in PAGE
    # Et plus personne ne termine la copie à la place de l'élève.
    assert "Le temps est écoulé" not in SCRIPT


def test_aucune_duree_ne_quitte_le_serveur():
    """Le total du contrôle et la durée de chaque question restaient dans la
    réponse de l'API longtemps après que plus rien ne les affichait."""
    main = (RACINE / "app" / "main.py").read_text(encoding="utf-8")
    assert 'CHAMPS_INTERNES = ("duree_minutes",)' in main
    reponse = main[main.index('"controle_id": controle_id'):]
    reponse = reponse[: reponse.index("}")]
    assert "duree_minutes" not in reponse, "le total repart vers le navigateur"
    assert "CHAMPS_CORRIGE + CHAMPS_INTERNES" in main, \
        "les questions repartent avec leur durée"


def test_aucune_seconde_ne_part_avec_la_copie():
    """Chaque réponse envoyée au serveur portait un « secondes », vestige du
    compte à rebours : le client l'envoyait toujours à zéro et personne ne le
    lisait — ni la correction, ni le modèle, ni la base. Un champ mort qu'un
    jour quelqu'un aurait rempli, et le chronomètre serait revenu par là."""
    schemas = (RACINE / "app" / "schemas.py").read_text(encoding="utf-8")
    reponse = schemas[schemas.index("class ReponseEleve"):]
    reponse = reponse[: reponse.index("class ")]
    assert "secondes" not in reponse
    envoi = SCRIPT[SCRIPT.index("envoyerJson('/api/correction'"):]
    envoi = envoi[: envoi.index("});")]
    assert "secondes" not in envoi


def test_aucun_mot_ne_dit_que_c_est_chronometre():
    for quoi, source in zip(("la page", "le script"), (PAGE, SCRIPT)):
        bas = source.lower()
        for mot in ("chronométré", "chronometre", "chronomètre", "temps restant",
                    "compte à rebours", "40 min"):
            assert mot not in bas, f"« {mot} » se lit encore dans {quoi}"
    readme = (RACINE / "README.md").read_text(encoding="utf-8").lower()
    assert "chronomètre" not in readme


def test_mais_le_sujet_reste_calibre_sur_un_vrai_controle():
    """Ce qui n'est PAS parti, et pourquoi : sans durée cible, le modèle n'a plus
    d'échelle pour savoir quelle taille de sujet écrire, et la garde perd le
    signal qui sépare un contrôle d'un quiz. Rien de tout ça n'atteint l'élève."""
    formats = (RACINE / "app" / "formats.py").read_text(encoding="utf-8")
    assert "duree_minutes: int" in formats, "les formats ont perdu leur durée cible"

    prompts = (RACINE / "app" / "prompts.py").read_text(encoding="utf-8")
    assert "Durée cible" in prompts
    assert '"duree_minutes": {"type": "integer"}' in prompts

    garde = (RACINE / "outils" / "garde.py").read_text(encoding="utf-8")
    assert "le contrôle est devenu un quiz" in garde
    assert 'q.get("duree_minutes", 0) >= 5' in garde
