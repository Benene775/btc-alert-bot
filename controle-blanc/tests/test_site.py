"""Le site public, et ce qu'il ne doit pas casser.

Ce qu'il est : une page. La racine EST Repère, pas un sommaire, et le compte
s'ouvre vide — comme pour un élève qui arrive. Deux choses ont été retirées en
cours de route pour ça : une page de choix entre deux matières, et le classeur
pré-rempli de dix cours.

Trois pannes réelles sont derrière ces tests.

1. Le favicon est une data-URI qui contient du SVG, donc des « > ». L'extraire
   en coupant au premier « > » tronquait l'attribut, et le navigateur avalait
   alors tout le <head> — feuille de style comprise. La page s'affichait nue.
2. La politique de sécurité de `netlify.toml` interdisait `blob:` aux images :
   la page marchait, mais les vignettes du cahier disparaissaient — la promesse
   du produit, cassée en silence.
3. La publication lance `site.py _site` depuis la racine du dépôt. Ce chemin
   relatif était interprété depuis `controle-blanc/`, et la fabrication mourait
   sur un `FileNotFoundError`. En local on passait toujours un chemin absolu :
   invisible ici, fatal sur la machine de GitHub. D'où un test qui appelle
   l'outil exactement comme la publication le fait.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DEPOT = RACINE.parent


def construire(dossier: Path) -> dict[str, str]:
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "site.py"), str(dossier)],
        capture_output=True, text=True, cwd=RACINE)
    assert fait.returncode == 0, fait.stderr
    return {f.name: f.read_text(encoding="utf-8") for f in dossier.glob("*.html")}


def test_le_site_est_une_page_et_c_est_repere():
    """Le premier jet posait un sommaire à la racine : on envoyait le lien à
    quelqu'un, et il tombait sur un menu au lieu du produit."""
    with tempfile.TemporaryDirectory() as dossier:
        pages = construire(Path(dossier))
    assert set(pages) == {"index.html"}
    index = pages["index.html"]
    # La vraie page d'accueil de Repère, pas une page fabriquée pour l'occasion.
    assert 'id="ecran-accueil"' in index
    assert "Passe le contrôle" in index
    assert 'id="ecran-connexion"' in index, "on doit pouvoir s'inscrire"


def test_le_compte_s_ouvre_vide():
    """Un visiteur doit voir ce que verra un élève : rien. Le classeur factice
    de dix cours sert aux démonstrations envoyées à la main, pas au site."""
    with tempfile.TemporaryDirectory() as dossier:
        index = construire(Path(dossier))["index.html"]
    assert "const DEMO_VIERGE = true" in index
    # Le semis existe toujours dans le code — il est simplement débranché.
    assert "semerLePasse" in index
    assert "DEMO_VIERGE" in index.split("function ouvrirDemo")[1][:900], \
        "le semis n'est pas conditionné"


def test_l_onglet_ne_nomme_pas_un_cours_que_la_page_n_a_pas():
    """Le titre portait « Repère — Histoire » : hérité des deux démonstrations,
    qu'il fallait distinguer dans une galerie. Sur le site public il n'y a qu'une
    page, et elle est vierge — l'onglet annonçait donc un cours d'histoire à
    quelqu'un qui n'a rien encore."""
    with tempfile.TemporaryDirectory() as dossier:
        index = construire(Path(dossier))["index.html"]
    assert "<title>Repère</title>" in index
    assert "Repère — Histoire" not in index

    # Les démonstrations envoyées à la main, elles, gardent leur nom de cours :
    # c'est ce qui les sépare l'une de l'autre.
    with tempfile.TemporaryDirectory() as dossier:
        page = Path(dossier) / "d.html"
        fait = subprocess.run(
            [sys.executable, str(RACINE / "outils" / "artefact.py"),
             "--contenu", "espagnol", str(page)],
            capture_output=True, text=True, cwd=RACINE)
        assert fait.returncode == 0, fait.stderr
        assert "<title>Repère — Espagnol</title>" in page.read_text(encoding="utf-8")


def test_une_seance_qui_n_a_rien_ne_s_affiche_pas():
    """S'inscrire ouvre une séance avant qu'on ait demandé la matière. La page
    perso montrait donc « Matière à préciser · 0 fiche », et « 1 cours » à côté
    de « 0 matière » — deux chiffres qui se contredisent devant quelqu'un qui
    n'a encore rien fait."""
    script = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
    assert "function sessionsFaites" in script
    for dessin in ("function dessinerEspace", "function dessinerMatiere",
                   "function dessinerRonds"):
        bloc = script[script.index(dessin):]
        bloc = bloc[: bloc.index("\n}\n")]
        assert "sessionsFaites()" in bloc, f"« {dessin} » lit encore les séances vides"


def test_le_site_n_appelle_personne():
    """Même promesse que les démonstrations : rien ne sort de la page."""
    with tempfile.TemporaryDirectory() as dossier:
        pages = construire(Path(dossier))
    for nom, contenu in pages.items():
        externes = re.findall(r'(?:src|href)=["\']https?://', contenu)
        externes += re.findall(r"url\(https?://", contenu)
        assert not externes, f"{nom} appelle {len(externes)} ressource(s) externe(s)"


def test_la_politique_de_securite_laisse_passer_les_vignettes_du_cahier():
    """`img-src data:` seul bloquait les blob: — donc les photos du cours. La
    page marchait, et le cœur du produit disparaissait sans un mot."""
    netlify = (DEPOT / "netlify.toml").read_text(encoding="utf-8")
    csp = re.search(r'Content-Security-Policy = "([^"]+)"', netlify).group(1)
    assert "blob:" in csp, "les vignettes du cahier sont des URL.createObjectURL"
    assert "img-src data: blob:" in csp
    # Et ce qui doit rester fermé.
    assert "default-src 'none'" in csp
    assert "connect-src" not in csp, "aucune requête sortante n'est prévue"


def test_le_deploiement_ne_publie_que_les_demonstrations():
    """Ni clé d'API, ni base, ni code serveur : ce qui part sur un hébergement
    de fichiers ne doit contenir que des pages autonomes."""
    workflow = (DEPOT / ".github" / "workflows" / "demos.yml").read_text(encoding="utf-8")
    assert "outils/site.py _site" in workflow
    assert "path: _site" in workflow
    for secret in ("ANTHROPIC_API_KEY", "CB_ADMIN_TOKEN", "CB_SMTP"):
        assert secret not in workflow, f"« {secret} » n'a rien à faire dans une publication statique"
    netlify = (DEPOT / "netlify.toml").read_text(encoding="utf-8")
    assert 'publish = "_site"' in netlify
    assert "ANTHROPIC_API_KEY" not in netlify


def test_la_fabrication_marche_comme_la_publication_l_appelle(tmp_path, monkeypatch):
    """`python controle-blanc/outils/site.py _site`, depuis la racine du dépôt,
    avec un chemin de sortie relatif. C'est la commande exacte du workflow — et
    c'est celle qui échouait pendant que tous les tests passaient, parce qu'ils
    passaient tous un chemin absolu."""
    monkeypatch.chdir(tmp_path)
    # On recrée la situation : la racine du dépôt est ailleurs, la sortie est
    # relative au dossier courant.
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "site.py"), "_site"],
        capture_output=True, text=True, cwd=tmp_path)
    assert fait.returncode == 0, fait.stderr

    produit = tmp_path / "_site"
    assert produit.is_dir(), "le dossier de sortie n'est pas là où on l'a demandé"
    assert (produit / "index.html").exists(), "index.html manque"
    assert (produit / "index.html").stat().st_size > 100_000


def test_le_workflow_appelle_l_outil_comme_le_test_le_verifie():
    """Si la commande du workflow change, le test ci-dessus ne vérifie plus rien.
    On s'assure que les deux parlent bien de la même chose."""
    workflow = (DEPOT / ".github" / "workflows" / "demos.yml").read_text(encoding="utf-8")
    assert "python controle-blanc/outils/site.py _site" in workflow
