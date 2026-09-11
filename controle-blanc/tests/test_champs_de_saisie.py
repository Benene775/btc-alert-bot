"""Aucun champ de saisie sous 16 pixels.

Sous ce seuil, Safari iOS agrandit la page à la mise au point du champ — et
n'en ressort pas tout seul : l'élève tape trois lettres dans la recherche et se
retrouve avec une page zoomée qu'il doit repincer pour lire son résultat.

La parade habituelle est « maximum-scale=1 » dans la balise viewport. On ne la
prend pas : elle interdit aussi le zoom volontaire, dont a besoin qui voit mal.
On règle la taille des champs à la place.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

SANS_CLAVIER = ('type="hidden"', 'type="file"', 'type="radio"', 'type="checkbox"')


def _classes_de_champs() -> set[str]:
    classes = set()
    for m in re.finditer(r"<(input|select|textarea)\b[^>]*>", PAGE):
        balise = m.group(0)
        if any(t in balise for t in SANS_CLAVIER):
            continue
        trouve = re.search(r'class="([^"]+)"', balise)
        if trouve:
            classes.update(trouve.group(1).split())
    return classes


def _en_pixels(valeur: str) -> float | None:
    valeur = valeur.strip()
    if valeur.endswith("rem"):
        return float(valeur[:-3]) * 16
    if valeur.endswith("px"):
        return float(valeur[:-2])
    return None  # clamp(), calc()… : jugés à la main, et tous au-dessus


def test_aucun_champ_ne_descend_sous_seize_pixels():
    trop_petits = []
    for classe in sorted(_classes_de_champs()):
        for regle in re.finditer(r"\." + re.escape(classe) + r"[^{]*\{([^}]*)\}", STYLE):
            taille = re.search(r"font-size:\s*([^;]+);", regle.group(1))
            if not taille:
                continue
            px = _en_pixels(taille.group(1))
            if px is not None and px < 16:
                trop_petits.append(f".{classe} = {taille.group(1).strip()} ({px:.1f} px)")
    assert not trop_petits, "iOS zoomera sur : " + ", ".join(trop_petits)


def test_la_regle_de_base_est_a_seize_pixels():
    """Les champs sans classe en dépendent entièrement."""
    bloc = STYLE[STYLE.index('select, input[type="date"]'):]
    bloc = bloc[: bloc.index("}")]
    assert "font-size: 1rem;" in bloc


def test_on_n_interdit_pas_le_zoom_pour_autant():
    """La parade facile serait « maximum-scale=1 ». Elle empêche aussi
    l'agrandissement volontaire, dont a besoin qui voit mal."""
    tete = PAGE[: PAGE.index("</head>")]
    viewport = re.search(r'<meta name="viewport"[^>]*>', tete).group(0)
    assert "maximum-scale" not in viewport
    assert "user-scalable" not in viewport
