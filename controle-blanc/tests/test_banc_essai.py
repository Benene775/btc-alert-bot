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


def test_le_corpus_couvre_tout_le_programme_de_6e(banc):
    """Neuf chapitres, trois thèmes : c’est le programme d’histoire de 6e entier."""
    chapitres = banc.corpus_disponible()
    assert len(chapitres) == 9
    assert sorted({c["theme"] for c in chapitres}) == [1, 2, 3]
    assert len({c["id"] for c in chapitres}) == 9, "identifiants en double"
    for chapitre in chapitres:
        assert len(chapitre["transcription"]) > 1200, chapitre["id"]
        assert len(chapitre["notions"]) >= 4, chapitre["id"]
        # Un cours de 6e a des définitions et des repères datés : c’est ce qui
        # rend les questions générées vérifiables.
        assert "Déf" in chapitre["transcription"], chapitre["id"]
        assert "Dates" in chapitre["transcription"], chapitre["id"]


def test_un_chapitre_du_corpus_prend_la_forme_d_une_transcription(banc):
    chapitre = banc.chapitre_du_corpus("revolution-neolithique")
    assert set(chapitre) == {"titre", "notions", "transcription", "photos"}
    assert chapitre["photos"] == [], "un chapitre de corpus ne vient d’aucune photo"
    assert "Croissant fertile" in chapitre["transcription"]


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
