"""Le site statique des démonstrations, et ce qu'il ne doit pas casser.

Trois pannes réelles sont derrière ces tests.

1. La page de choix embarquait `styles.css` en entier : 200 Ko pour deux liens,
   et une hauteur de 32 000 px, parce que des règles écrites pour les écrans du
   produit s'appliquaient à ce qui traînait là.
2. Le favicon est une data-URI qui contient du SVG, donc des « > ». L'extraire
   en coupant au premier « > » tronquait l'attribut, et le navigateur avalait
   alors tout le <head> — feuille de style comprise. La page s'affichait nue.
3. La politique de sécurité de `netlify.toml` interdisait `blob:` aux images :
   la page marchait, mais les vignettes du cahier disparaissaient — la promesse
   du produit, cassée en silence.
4. La publication lance `site.py _site` depuis la racine du dépôt. Ce chemin
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


def test_le_site_se_fabrique_avec_ses_trois_pages():
    with tempfile.TemporaryDirectory() as dossier:
        pages = construire(Path(dossier))
    assert set(pages) == {"index.html", "espagnol.html", "histoire.html"}
    assert "<title>Repère — Espagnol</title>" in pages["espagnol.html"]
    assert "<title>Repère — Histoire</title>" in pages["histoire.html"]
    for cible in ("espagnol.html", "histoire.html"):
        assert f'href="{cible}"' in pages["index.html"], f"pas de lien vers {cible}"


def test_la_page_de_choix_a_bien_sa_feuille_de_style():
    """Le favicon truncated avalait le <head> : la page sortait sans style, et
    rien ne le signalait — elle s'affichait, simplement moche."""
    with tempfile.TemporaryDirectory() as dossier:
        index = construire(Path(dossier))["index.html"]
    assert index.count("<style>") == 1 and index.count("</style>") == 1
    style = index[index.index("<style>"):index.index("</style>")]
    # Les jetons de couleur doivent y être : sans eux, le logo tombe en noir.
    assert "--papier:" in style and "--accent:" in style
    assert ".hall-carte" in style
    # Et le <link> du favicon doit être entier.
    lien = re.search(r'<link rel="icon" href="[^"]*">', index)
    assert lien and lien.group(0).endswith('</svg>">'), "le favicon est tronqué"


def test_la_page_de_choix_n_embarque_pas_toute_l_application():
    """3 000 lignes de CSS écrites pour les écrans du produit n'ont rien à faire
    sur une page à deux liens — et elles y font des dégâts."""
    with tempfile.TemporaryDirectory() as dossier:
        index = construire(Path(dossier))["index.html"]
    poids = len(index.encode("utf-8")) / 1024
    assert poids < 130, f"la page de choix pèse {poids:.0f} Ko"
    for regle in (".ecran {", ".carte-fiche", "#scene", ".rond-perso"):
        assert regle not in index, f"« {regle} » vient de l'application"


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
    for page in ("index.html", "espagnol.html", "histoire.html"):
        assert (produit / page).exists(), f"{page} manque"
        assert (produit / page).stat().st_size > 1000


def test_le_workflow_appelle_l_outil_comme_le_test_le_verifie():
    """Si la commande du workflow change, le test ci-dessus ne vérifie plus rien.
    On s'assure que les deux parlent bien de la même chose."""
    workflow = (DEPOT / ".github" / "workflows" / "demos.yml").read_text(encoding="utf-8")
    assert "python controle-blanc/outils/site.py _site" in workflow
