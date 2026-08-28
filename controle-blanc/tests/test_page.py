"""La page et son script doivent parler des mêmes éléments.

Ce test existe à cause d'une panne réelle : le script cherchait un élément
« #visionneuse » que le HTML ne contenait pas encore. `initialiser()` levait
« Cannot set properties of null », s'arrêtait avant d'afficher le premier
écran, et l'application s'ouvrait entièrement blanche — sans la moindre erreur
visible pour l'élève. Un identifiant oublié ne doit plus jamais coûter ça.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
PAGE = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPT = (WEB / "app.js").read_text(encoding="utf-8")
STYLE = (WEB / "styles.css").read_text(encoding="utf-8")

# `$('truc')` et `document.getElementById('truc')` : les deux façons dont le
# script va chercher un élément par son identifiant.
IDENTIFIANTS = sorted(
    set(re.findall(r"\$\('([a-z0-9-]+)'\)", SCRIPT))
    | set(re.findall(r"getElementById\('([a-z0-9-]+)'\)", SCRIPT))
)


def test_le_script_ne_cherche_que_des_elements_qui_existent():
    assert IDENTIFIANTS, "aucun identifiant repéré : l'extraction est cassée"
    presents = set(re.findall(r'id="([a-z0-9-]+)"', PAGE))
    manquants = [i for i in IDENTIFIANTS if i not in presents]
    assert not manquants, f"le script cherche des éléments absents de la page : {manquants}"


def test_le_cahier_de_l_eleve_est_dans_la_page():
    """La vignette du cahier est la promesse du produit : la fiche vient de SES pages."""
    for identifiant in ("visionneuse", "page-cahier", "legende-page", "fermer-visionneuse"):
        assert f'id="{identifiant}"' in PAGE, f"« {identifiant} » manque dans la page"
    for classe in (".provenance", ".provenance-vignette", ".visionneuse", ".page-cahier"):
        assert classe in STYLE, f"« {classe} » n'a pas de style"


def test_les_pages_photographiees_ne_sont_jamais_renvoyees_au_serveur():
    """Elles restent dans IndexedDB. Aucun `fetch` ne doit les reprendre."""
    assert "indexedDB.open(BASE_PAGES" in SCRIPT
    for interdit in ("photosDuCours)", "photosDuCours,"):
        assert f"body: {interdit}" not in SCRIPT
    envois = re.findall(r"api\([^)]*photosDuCours", SCRIPT)
    assert not envois, f"les pages gardées repartent vers le serveur : {envois}"


def test_le_cours_transmis_au_modele_porte_les_frontieres_de_page():
    """Sans marque de page, le modèle ne peut pas dire d'où vient une section.

    La fiche renverrait alors « pages: [] » partout et l'élève ne verrait plus
    aucun bout de son cahier — la vignette marcherait en démonstration et
    nulle part ailleurs.
    """
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app import demo, prompts

    bloc = prompts.bloc_cours([demo.CHAPITRE])
    assert "[[page 0]]" in bloc, "le cours de démonstration ne porte pas de marque de page"
    assert "[[page N]]" in bloc, "rien n'explique la marque au modèle qui la lit"
    assert "[[page N]]" in prompts.ANALYSE_SYSTEME, "l'analyse ne produit pas les marques"
    assert "[[page N]]" in prompts.FICHE_GENERALE_CONSIGNE, "la fiche ne s'appuie pas dessus"
