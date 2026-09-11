"""« Refaire un tour sur cette notion » doit refaire un tour.

Signalé en usage réel : le bouton ne faisait rien. L'écran montrait déjà la
contradiction — « 0 notion · à revoir » deux lignes au-dessus d'une carte qui
annonçait « 1 notion à revoir. »

La cause : « etat.marques » appartient à la SÉANCE, pas à une fiche, et il est
rangé par titre de partie. Une notion mise de côté dans la fiche générale y
restait quand on ouvrait la fiche ciblée, dont les parties portent d'autres
titres. La carte de fin comptait cette marque ; le second tour, qui filtre les
parties de la fiche ouverte, n'en retenait aucune. Le bouton rebâtissait donc un
paquet vide, identique à l'écran qu'on avait sous les yeux : rien ne bougeait.

Reproduit dans un navigateur avec une marque étrangère injectée dans la séance,
avant et après correction.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")

A_REVOIR = SCRIPT[SCRIPT.index("function notionsARevoir()"):]
A_REVOIR = A_REVOIR[: A_REVOIR.index("\n}\n")]


def test_on_ne_compte_que_les_marques_de_la_fiche_ouverte():
    """Sans ça, la carte de fin promet un second tour que la fiche ne peut pas
    tenir."""
    assert "ficheCourante" in A_REVOIR, "le filtre ne regarde pas la fiche ouverte"
    assert "sections" in A_REVOIR
    assert "parties.has(titre)" in A_REVOIR


def test_la_carte_de_fin_et_le_second_tour_comptent_la_meme_chose():
    """C'est l'invariant : ce que la carte annonce, le second tour doit pouvoir
    le montrer. Les deux passent par la même fonction."""
    carte = SCRIPT[SCRIPT.index("function majCarteFin()"):]
    carte = carte[: carte.index("\n}\n")]
    assert carte.count("notionsARevoir()") == 2, (
        "le compte affiché et le paquet rebâti doivent venir de la même source"
    )
    filtre = SCRIPT[SCRIPT.index("const sections = secondTour"):]
    filtre = filtre[: filtre.index(";")]
    assert "options.notions.includes(s.titre)" in filtre, (
        "le second tour filtre par titre de partie : c'est ce que le compte doit suivre"
    )


def test_les_marques_des_autres_fiches_ne_sont_pas_effacees():
    """Elles doivent revenir quand on rouvre la fiche à laquelle elles
    appartiennent : on filtre à la lecture, on ne nettoie pas le stockage."""
    marquer = SCRIPT[SCRIPT.index("function marquerNotion("):]
    marquer = marquer[: marquer.index("\n}\n")]
    assert "delete " not in marquer
    assert "etat.marques = {}" not in SCRIPT, "un nettoyage global perdrait les autres fiches"
