"""La frise : un aperçu du calendrier.

Elle regardait le passé — les jours travaillés des huit semaines écoulées. Elle
regarde maintenant devant, et ce qui est foncé, ce sont les jours qui portent un
contrôle : l'élève voit ce qui l'attend sans ouvrir l'agenda.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

BLOC = SCRIPT[SCRIPT.index("function dessinerRegularite("):]
BLOC = BLOC[: BLOC.index("\n}\n")]


def test_la_frise_regarde_devant():
    """Un aperçu d'agenda qui montre les huit semaines écoulées ne sert à rien :
    ce qu'un élève vient y chercher, c'est ce qui arrive."""
    assert "jourPlus(aujourdhui, -depuisLundi)" in BLOC, (
        "la frise ne part pas du lundi de la semaine en cours"
    )
    # Et elle avance : la boucle ajoute des semaines, elle n'en retire pas.
    assert "jourPlus(premier, semaine * 7 + jour)" in BLOC


def test_les_jours_de_controle_sont_fonces():
    assert "evenementsDuJour(cle, sessions)" in BLOC, (
        "la frise ne lit pas les mêmes échéances que l'agenda"
    )
    assert "case_.dataset.controle = 'oui'" in BLOC
    assert '.case-frise[data-controle="oui"]' in STYLE


def test_l_activite_reste_en_arriere_plan():
    """Deux marques de même force donneraient une grille où l'échéance se perd
    dans l'activité. Le jour travaillé est un fond, pas l'information."""
    def teinte(regle: str) -> int:
        # En début de ligne : le même sélecteur apparaît plus haut derrière
        # « .frise-porte:hover », dont la règle ne porte aucune couleur.
        bloc = STYLE[STYLE.index("\n" + regle) + 1:]
        bloc = bloc[: bloc.index("}")]
        trouve = re.search(r"var\(--accent\) (\d+)%", bloc)
        assert trouve, f"pas de teinte lisible dans « {regle} »"
        return int(trouve.group(1))

    assert teinte('.case-frise[data-travaille="oui"]') < teinte('.case-frise[data-controle="oui"]')


def test_la_grille_se_lit_comme_un_calendrier():
    """Sans mois en tête ni jours sur le côté, c'est une abstraction : on voit
    des carrés foncés sans savoir quand."""
    assert 'id="frise-mois"' in PAGE, "aucun mois en tête"
    assert 'class="frise-semaine"' in PAGE, "aucun jour de la semaine"
    semaine = PAGE[PAGE.index('class="frise-semaine"'):]
    semaine = semaine[: semaine.index("</span>")]
    assert re.findall(r"<i>(\w)</i>", semaine) == list("LMMJVSD")
    assert "function dessinerMoisFrise" in SCRIPT


def test_les_dates_ne_se_calculent_pas_en_millisecondes():
    """« getTime() + n * 86400000 » est juste onze mois sur douze. Au passage à
    l'heure d'hiver, un jour fait 25 h : la somme retombe la veille, et TOUT ce
    qui suit glisse d'une ligne. Mesuré en fuseau Europe/Paris : 126 cases sur
    la mauvaise ligne, à partir du 25 octobre."""
    assert "86400000" not in BLOC, "la frise recalcule des dates en millisecondes"
    assert "suivant.setDate(suivant.getDate() + jours)" in SCRIPT, (
        "jourPlus ne compte pas en jours de calendrier"
    )


def test_la_largeur_se_mesure_sur_le_cadre():
    """La grille est dimensionnée par son contenu : elle rend la largeur des
    colonnes qu'elle porte déjà, jamais la place dont elle dispose. La mesurer
    donnait huit semaines même sur une carte de 449 px, où vingt-six tiennent."""
    bloc = SCRIPT[SCRIPT.index("function semainesFrise()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "frise-cadre" in bloc
    assert "$('frise-regularite').clientWidth" not in bloc


def test_survoler_un_jour_marque_dit_lequel():
    """C'est toute l'idée d'un aperçu : savoir qu'il se passe quelque chose, et
    quoi, sans avoir à ouvrir l'agenda."""
    assert "case_.title =" in BLOC
    assert "nomMatiere(e.matiere)" in BLOC
