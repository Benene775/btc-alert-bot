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


def test_l_ordre_des_pages_est_visible_et_corrigeable():
    """L'ordre vient du téléphone, pas du produit : l'élève doit pouvoir le corriger.

    Depuis que chaque partie de la fiche renvoie à une page précise, une page
    mal placée ouvre la mauvaise feuille sans rien dire.
    """
    assert 'id="aide-ordre"' in PAGE, "rien ne dit à l'élève que l'ordre compte"
    assert 'id="annonce-photos"' in PAGE, "aucune annonce pour les lecteurs d'écran"
    assert "numero-page" in SCRIPT and ".numero-page" in STYLE, "le numéro de page n'est pas affiché"
    assert "function deplacerPage" in SCRIPT, "aucun déplacement de page"
    assert "setPointerCapture" in SCRIPT, "le glissement ne suit pas le doigt"
    assert "ArrowLeft" in SCRIPT and "ArrowRight" in SCRIPT, "pas de déplacement au clavier"


def test_seule_la_poignee_bloque_le_defilement():
    """« touch-action: none » sur la grille entière rendrait la page impossible à faire défiler."""
    import re

    poignee = re.search(r"\.vignettes \.poignee \{[^}]*\}", STYLE)
    assert poignee, "la poignée doit être stylée via « .vignettes .poignee »"
    assert "touch-action: none" in poignee.group(0)
    # « .vignettes button » est plus spécifique : sans « top: auto », la poignée
    # se replaçait en haut à droite et recouvrait la croix « retirer ».
    assert "top: auto" in poignee.group(0), "la poignée recouvrirait la croix « retirer »"
    grille = re.search(r"\.vignettes \{[^}]*\}", STYLE)
    assert "touch-action" not in grille.group(0), "la grille ne doit pas bloquer le défilement"


def test_la_page_reste_lisible_sans_javascript():
    """Les révélations au défilement ne doivent jamais pouvoir effacer la page.

    L'état caché est posé par le script (« data-revelations »), pas par la
    feuille de style : si le script ne tourne pas, tout reste visible. Une
    règle « .a-reveler { opacity: 0 } » sans garde rendrait la moitié de la
    page publique invisible chez qui bloque JavaScript.
    """
    import re

    for regle in re.findall(r"([^{}]*\.a-reveler[^{}]*)\{([^}]*)\}", STYLE):
        selecteur, corps = regle
        if "opacity: 0" in corps or "opacity:0" in corps:
            assert 'data-revelations' in selecteur, (
                f"« {selecteur.strip()} » cache du contenu sans garde JavaScript"
            )
    assert "dataset.revelations = 'oui'" in SCRIPT, "le script ne prend jamais la main"


def test_le_seuil_de_revelation_reste_atteignable():
    """Une marge en pourcentage a déjà rendu le pied de page inatteignable.

    Sur un grand écran, la page ne défile pas d'assez pour lui faire franchir
    la ligne de déclenchement : le pied restait invisible pour toujours.
    """
    import re

    marge = re.search(r"rootMargin:\s*'([^']+)'", SCRIPT)
    assert marge, "aucune rootMargin trouvée"
    assert "%" not in marge.group(1), (
        f"rootMargin en pourcentage ({marge.group(1)}) : le bas de page peut devenir inatteignable"
    )
