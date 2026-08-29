"""La marque : « Repère », son glyphe, et le rond qui mène à sa page.

Trois pannes réelles sont derrière ces tests.

1. Le premier dessin de logo était une puce couleur papier posée sur du papier :
   à 32 px il ne restait qu'un carré blanc. Un logo doit se voir.
2. Le bandeau se cachait sur l'écran d'une matière — la marque disparaissait
   d'un écran sur onze, et avec elle le rond d'accès à sa page.
3. L'ancienne porte d'entrée était une bannière large. On l'a remplacée par un
   rond ; rien n'empêchait qu'elle revienne.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
WEB = RACINE / "web"
PAGE = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPT = (WEB / "app.js").read_text(encoding="utf-8")
STYLE = (WEB / "styles.css").read_text(encoding="utf-8")

NOM = "Repère"


def test_le_site_s_appelle_repere_et_pas_le_nom_de_ce_qu_il_fabrique():
    """« Contrôle blanc » reste le nom de l'épreuve, pas celui du site : les deux
    dans la même phrase, l'élève ne sait plus lequel il ouvre."""
    titre = re.search(r"<title>(.*?)</title>", PAGE, re.S).group(1)
    assert titre.startswith(NOM), f"le titre de la page est « {titre} »"
    assert "contrôle blanc" not in titre.lower()
    assert f"<span>{NOM}</span>" in PAGE, "la signature du héros ne porte pas le nom"


def test_le_glyphe_est_defini_une_fois_et_reutilise():
    """Trois copies du même SVG dans la page, c'est trois dessins à corriger le
    jour où il change — et deux qu'on oublie."""
    assert PAGE.count('<symbol id="glyphe-repere"') == 1, "le glyphe est dupliqué"
    assert PAGE.count('href="#glyphe-repere"') >= 3, "le glyphe n'est pas repris partout"
    # héros, bandeau, pied de page : la marque tient les trois échelles.
    for classe in (".logo-marque", ".logo-bandeau", ".logo-pied"):
        assert classe in STYLE, f"« {classe} » n'a pas de taille"


def test_le_glyphe_se_voit_sur_le_papier():
    """Le premier essai peignait la puce en « --carte » sur un fond « --papier » :
    deux teintes séparées par 1 % de luminosité. Le fond doit être l'accent."""
    symbole = re.search(r"<symbol id=\"glyphe-repere\".*?</symbol>", PAGE, re.S).group(0)
    assert 'fill="var(--accent)"' in symbole, "la puce n'est pas peinte à l'accent"
    assert "var(--sur-accent)" in symbole, "les traits ne sont pas dans la couleur de contraste"
    # « --sur-accent » s'inverse avec le thème : le glyphe suit donc tout seul.
    assert "--sur-accent" in STYLE


def test_le_favicon_ne_demande_rien_a_personne():
    """Un onglet ne lit pas nos variables CSS, et l'artefact interdit toute
    requête externe : le dessin est donc en dur, dans une data-URI."""
    icone = re.search(r'<link rel="icon" href="([^"]+)"', PAGE).group(1)
    assert icone.startswith("data:image/svg+xml,"), "le favicon est un fichier à télécharger"
    # `xmlns` est une étiquette, pas une adresse à joindre : ce qu'on interdit,
    # c'est une ressource que le navigateur irait vraiment chercher.
    assert not re.search(r"(?:href|src)='https?://|url\(https?://", icone)


def test_on_entre_dans_sa_page_par_un_rond_pas_par_une_banniere():
    assert 'class="rond-perso"' in PAGE
    assert ".rond-perso {" in STYLE
    # La bannière retirée : ni sa classe, ni son style ne doivent revenir.
    assert ".porte" not in STYLE, "la bannière large est revenue"
    assert 'class="porte' not in PAGE
    # Un rond seul n'annonce rien : deux mots le nomment.
    assert 'class="acces-perso-mot"' in PAGE
    assert "ma page" in PAGE.lower()


def test_le_rond_dit_ou_il_mene():
    """Il est lu à la voix. « Ouvrir ma page — contrôle dans 1 jours » ne se dit
    pas, et depuis sa page le même rond ramène à la séance : il ne peut pas
    s'annoncer comme la porte de la page où l'on est déjà."""
    bloc = SCRIPT[SCRIPT.index("function dessinerRonds"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "'aujourd’hui'" in bloc and "'demain'" in bloc, "la pastille se dit « dans 1 jours »"
    assert "Revenir à ma séance" in bloc, "le rond du bandeau ment sur sa destination"


def test_la_marque_reste_visible_sur_l_ecran_d_une_matiere():
    """Le bandeau ne s'affichait que s'il y avait une séance en cours : ouvrir
    une matière depuis sa page laissait l'élève sans en-tête et sans rond."""
    bloc = SCRIPT[SCRIPT.index("function majBandeau"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "ecran-matiere" in bloc, "l'écran d'une matière n'est pas traité"
    assert "dansMaPage" in bloc


def test_le_bandeau_se_cale_sur_l_ecran_qu_il_coiffe():
    """Sa page tient 1120 px, une fiche 620 : avec une seule règle, la marque
    flottait au milieu du bandeau pendant que la page dessous commençait à
    80 px du bord."""
    assert '#bandeau[data-large="oui"]' in STYLE, "le bandeau n'a qu'une largeur"
    assert "var(--large)" in STYLE.split('#bandeau[data-large="oui"]')[1][:200]
    assert "bandeau.dataset.large" in SCRIPT, "rien ne bascule la largeur"
    # Les trois écrans larges sont exactement ceux qui tiennent --large.
    regle = next(l for l in STYLE.splitlines() if "max-width: var(--large)" in l)
    for ecran in ("ecran-accueil", "ecran-espace", "ecran-matiere"):
        assert ecran in regle, f"« {ecran} » ne tient plus la largeur"


def test_l_ancien_nom_ne_traine_plus_comme_nom_de_produit():
    """Partout où « contrôle blanc » désigne l'épreuve, il reste. Là où il
    désignait le site — titres, en-têtes de fichier, README — il part."""
    for fichier, premiere_ligne in (
        (RACINE / "README.md", "# Repère"),
        (WEB / "app.js", "/* Repère —"),
        (WEB / "styles.css", "/* Repère —"),
    ):
        debut = fichier.read_text(encoding="utf-8").splitlines()[0]
        assert debut.startswith(premiere_ligne), f"{fichier.name} s'ouvre sur « {debut} »"
    api = (RACINE / "app" / "main.py").read_text(encoding="utf-8")
    assert 'FastAPI(title="Repère"' in api
    fabrique = (RACINE / "outils" / "artefact.py").read_text(encoding="utf-8")
    assert "<title>Repère — " in fabrique


def test_la_demonstration_autonome_porte_la_marque_et_ne_demande_rien():
    """Le fabricant d'artefact reconstruit sa propre en-tête : le titre et le
    favicon de la page n'y arrivent pas tout seuls. Sans le favicon, le
    navigateur allait chercher /favicon.ico — une requête sortante dans une
    page qui promet de n'en faire aucune."""
    import subprocess
    import sys
    import tempfile

    with tempfile.TemporaryDirectory() as dossier:
        cible = Path(dossier) / "demo.html"
        fait = subprocess.run(
            [sys.executable, str(RACINE / "outils" / "artefact.py"), "--contenu", "espagnol", str(cible)],
            capture_output=True, text=True, cwd=RACINE)
        assert fait.returncode == 0, fait.stderr
        page = cible.read_text(encoding="utf-8")

    assert "<title>Repère — Espagnol</title>" in page
    assert 'rel="icon" href="data:image/svg+xml,' in page, "pas de favicon : /favicon.ico partira en 404"
    assert '<symbol id="glyphe-repere"' in page, "le logo n'a pas suivi dans la démonstration"
    assert not re.search(r'(?:src|href)=["\']https?://', page), "la démonstration appelle l'extérieur"
