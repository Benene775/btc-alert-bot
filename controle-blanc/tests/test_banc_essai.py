"""Le banc d’essai lui-même.

Il appelle le vrai modèle, donc on ne le lance pas ici. Ce qu’on vérifie, c’est
sa plomberie : le rendu du rapport, qui est la partie la plus fragile (beaucoup
de HTML assemblé à la main), et le refus de partir sans clé API.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def banc():
    chemin = RACINE / "outils" / "essai.py"
    spec = importlib.util.spec_from_file_location("banc_essai", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def essai_factice():
    from app import demo

    chapitres = demo.analyse(3)["chapitres"]
    controle = demo.controle(chapitres, None, False)
    reponses = {q["numero"]: "une réponse" for q in controle["questions"]}
    correction = demo.correction(controle["questions"], reponses, set())
    return {
        "horodatage": "27/08/2026 14:00",
        "modele": "claude-opus-5",
        "niveau": "3e",
        "matiere": "Histoire-Géographie / EMC",
        "analyse": demo.analyse(3),
        "fiche_generale": demo.fiche_generale(chapitres),
        "controle": controle,
        "reponses": reponses,
        "correction": correction,
        "fiche_ciblee": demo.fiche_ciblee(correction["notions_fragiles"]),
        "second_controle": demo.controle(chapitres, ["La notion de guerre totale"], True),
        "couts": [
            {"etape": "Lecture du cours", "secondes": 21.4, "cout_usd": 0.0412,
             "tokens_entree": 5200, "tokens_sortie": 2100, "cache_lecture": 0},
        ],
        "cout_total": 0.0412,
        "secondes_total": 61.2,
    }


def test_le_rapport_couvre_tout_le_parcours(banc, essai_factice, tmp_path):
    chemin = tmp_path / "rapport.html"
    banc.rapport_html(essai_factice, chemin)
    page = chemin.read_text(encoding="utf-8")

    assert "Lecture des photos" in page
    assert "Contrôle blanc" in page
    assert "Correction" in page
    assert "Notions fragiles" in page
    assert "Coût" in page
    # La photo illisible doit ressortir, c’est le premier signal utile.
    assert "illisible" in page
    # Le corrigé attendu figure dans le rapport : c’est ce qu’on vient juger.
    assert "Corrigé attendu" in page
    assert "0.0412" in page


def test_le_rapport_echappe_le_contenu(banc, essai_factice, tmp_path):
    """Les réponses viennent d’un élève, le cours d’une photo : rien n’est sûr."""
    essai_factice["reponses"][1] = "<script>alert('x')</script>"
    essai_factice["analyse"]["chapitres"][0]["titre"] = "<img src=x onerror=alert(1)>"
    chemin = tmp_path / "rapport.html"
    banc.rapport_html(essai_factice, chemin)
    page = chemin.read_text(encoding="utf-8")

    assert "<script>alert" not in page
    assert "<img src=x" not in page
    assert "&lt;script&gt;" in page


def test_le_rapport_tient_sans_second_tour(banc, essai_factice, tmp_path):
    essai_factice["fiche_ciblee"] = None
    essai_factice["second_controle"] = None
    chemin = tmp_path / "rapport.html"
    banc.rapport_html(essai_factice, chemin)
    assert "Correction" in chemin.read_text(encoding="utf-8")


def test_les_reponses_se_lisent_dans_un_fichier(banc, tmp_path):
    fichier = tmp_path / "reponses.txt"
    fichier.write_text(
        "1: La guerre commence en 1914.\net se termine en 1918.\n"
        "2: Une guerre totale mobilise tout le pays.\n",
        encoding="utf-8",
    )
    questions = [{"numero": 1}, {"numero": 2}, {"numero": 3}]
    reponses = banc.lire_reponses(questions, str(fichier), vide=False)

    assert reponses[1] == "La guerre commence en 1914.\net se termine en 1918."
    assert reponses[2] == "Une guerre totale mobilise tout le pays."
    assert reponses[3] == "", "une question sans réponse reste vide, elle n’est pas oubliée"


def test_option_vide(banc):
    questions = [{"numero": 1}, {"numero": 2}]
    assert banc.lire_reponses(questions, None, vide=True) == {1: "", 2: ""}


def test_refuse_de_partir_sans_cle_api():
    """Un banc d’essai qui produirait les contenus d’exemple ne testerait rien."""
    environnement = {"PATH": "/usr/bin:/bin", "HOME": "/tmp"}
    resultat = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "essai.py"), "photo.jpg"],
        capture_output=True, text=True, env=environnement,
    )
    assert resultat.returncode == 2
    assert "ANTHROPIC_API_KEY" in resultat.stdout


def test_les_photos_sont_reduites_avant_envoi(banc, tmp_path):
    """Le navigateur réduit à 1568 px ; le banc d’essai doit faire pareil,
    sinon le coût mesuré ne serait pas celui des élèves."""
    from PIL import Image

    grande = tmp_path / "page.jpg"
    Image.new("RGB", (4032, 3024), "white").save(grande)
    images = banc.charger_images([str(grande)])

    assert len(images) == 1
    mime, octets = images[0]
    assert mime == "image/jpeg"
    relue = Image.open(__import__("io").BytesIO(octets))
    assert max(relue.size) == banc.COTE_MAX


def test_chaque_corpus_couvre_son_programme(banc):
    """Histoire : 3 thèmes, 9 chapitres. Maths : les 6 domaines du programme 2025."""
    chapitres = banc.corpus_disponible()
    assert len({c["id"] for c in chapitres}) == len(chapitres), "identifiants en double"

    histoire = [c for c in chapitres if c["matiere"] == "histoire-geographie"]
    assert len(histoire) == 9
    assert sorted({c["groupe"] for c in histoire}) == [1, 2, 3]

    maths = [c for c in chapitres if c["matiere"] == "mathematiques"]
    assert sorted({c["groupe"] for c in maths}) == [1, 2, 3, 4, 5, 6], "les six domaines"

    for chapitre in chapitres:
        assert len(chapitre["transcription"]) > 1200, chapitre["id"]
        assert len(chapitre["notions"]) >= 4, chapitre["id"]
        assert chapitre["groupe_nom"], chapitre["id"]
        # Un cours de 6e a des définitions : c’est ce qui rend les questions
        # générées vérifiables plutôt qu’inventées.
        assert "Déf" in chapitre["transcription"], chapitre["id"]


def test_les_corpus_declarent_leur_programme_de_reference(banc):
    """Les programmes changent : celui de maths a basculé en 2025, celui
    d’histoire basculera en 2027. Chaque corpus doit dire lequel il suit."""
    for chapitre in banc.corpus_disponible():
        assert "arrêté" in chapitre["programme"], chapitre["id"]
        assert chapitre["niveau"] == "6e"


def test_un_chapitre_du_corpus_prend_la_forme_d_une_transcription(banc):
    chapitre = banc.chapitre_du_corpus("revolution-neolithique")
    assert chapitre["photos"] == [], "un chapitre de corpus ne vient d’aucune photo"
    assert "Croissant fertile" in chapitre["transcription"]
    assert chapitre["matiere"] == "histoire-geographie"


def test_le_corpus_de_maths_porte_ses_notations(banc):
    """Les maths écrivent des fractions, des puissances et des symboles. C’est
    précisément ce que le produit ne sait pas encore afficher."""
    fractions = banc.chapitre_du_corpus("fractions")
    assert "3/4" in fractions["transcription"]
    aires = banc.chapitre_du_corpus("longueurs-aires")
    assert "cm²" in aires["transcription"]
    angles = banc.chapitre_du_corpus("droites-angles")
    assert "⊥" in angles["transcription"] and "//" in angles["transcription"]


def test_chapitre_inconnu_refuse_avec_la_liste(banc):
    with pytest.raises(SystemExit) as erreur:
        banc.chapitre_du_corpus("napoleon")
    assert "revolution-neolithique" in str(erreur.value), "le message doit lister les choix"


def test_photos_et_corpus_sont_exclusifs():
    environnement = {"PATH": "/usr/bin:/bin", "HOME": "/tmp"}
    for arguments in (["p.jpg", "--corpus", "debuts-humanite"], []):
        resultat = subprocess.run(
            [sys.executable, str(RACINE / "outils" / "essai.py"), *arguments],
            capture_output=True, text=True, env=environnement,
        )
        assert resultat.returncode == 2
        assert "soit des photos, soit --corpus" in resultat.stderr


def test_chaque_etape_est_chiffree_au_tarif_de_son_modele():
    """Le banc sert d'abord à comparer deux modèles. S'il chiffre toutes les
    étapes au même tarif — c'était le cas, celui d'Opus, quel que soit le modèle
    qui avait tourné — la moitié de la comparaison ne veut rien dire : un essai
    sur Sonnet ressortait 2,5 fois trop cher, et un essai mixte n'avait aucun
    sens du tout.
    """
    source = (RACINE / "outils" / "essai.py").read_text(encoding="utf-8")
    corps = source[source.index("    def etape("):]
    corps = corps[: corps.index("\n    #")]
    assert "config.prix_du_modele(modele)" in corps, "un tarif unique pour tous les modèles"
    assert "config.PRIX_USD_PAR_MTOK" not in corps, "le tarif de repli sert encore de tarif"
    # Le modèle vient de la réponse de l'API, pas de la configuration.
    assert 'usage.get("modele"' in corps
    # Et un tarif inconnu se dit, au lieu de sortir un chiffre faux en silence.
    assert "tarif inconnu" in corps


def test_le_rapport_nomme_le_modele_de_chaque_etape():
    """Depuis qu'un appel peut avoir son propre modèle, un seul nom en tête du
    rapport mentirait sur un essai mixte."""
    source = (RACINE / "outils" / "essai.py").read_text(encoding="utf-8")
    assert '"modele": config.MODEL,' not in source, "l'en-tête répète la config"
    assert 'c.get(\'modele\')' in source or 'c["modele"]' in source
    assert "<th>Modèle</th>" in source, "le tableau des coûts ne dit pas quel modèle"


def test_le_modele_se_choisit_en_ligne_de_commande():
    """Deux lancements sur les mêmes photos, c'est tout ce que la comparaison
    demande — pas trois variables d'environnement à poser avant."""
    source = (RACINE / "outils" / "essai.py").read_text(encoding="utf-8")
    for option in ("--modele", "--modele-photos", "--modele-texte", "--modele-appel"):
        assert f'"{option}"' in source, option
    # Les modèles sont posés AVANT l'import de config, qui lit l'environnement
    # à l'import : après, ils ne serviraient à rien.
    assert source.index('os.environ["CB_MODEL"]') < source.index("from app import config")


def test_un_appel_inconnu_est_refuse():
    """« --modele-appel corection=… » doit s'arrêter là, pas tourner une heure
    sur la configuration par défaut en croyant tester autre chose."""
    resultat = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "essai.py"), "--corpus", "x",
         "--modele-appel", "corection=un-modele"],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": "/tmp", "ANTHROPIC_API_KEY": "factice"},
    )
    assert resultat.returncode == 2
    assert "--modele-appel attend" in resultat.stderr
