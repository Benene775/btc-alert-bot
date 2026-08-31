"""L'ouverture de l'agenda.

Une animation est du code qui ne lève jamais d'erreur : quand elle casse, elle
se contente d'être moche, ou de rejouer au mauvais moment. Ces tests tiennent
les trois choses qui la rendraient pénible plutôt que jolie.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

# Les commentaires disent souvent ce qu'on a REFUSÉ de faire — « pas de
# backface-visibility: hidden », par exemple. Les chercher sans les retirer
# ferait échouer un test sur la phrase qui explique précisément qu'on s'en
# abstient.
STYLE_NU = re.sub(r"/\*.*?\*/", "", STYLE, flags=re.S)


def test_la_vague_ne_rejoue_pas_a_chaque_clic():
    """La grille est redessinée à chaque clic sur une date : sans marqueur, les
    cases sont neuves et l'animation repart de zéro sous le doigt de l'élève.
    C'est le défaut qui transforme un bel effet en page qui tremble."""
    assert '.agenda-deplie[data-anime="oui"] .jour {' in STYLE, (
        "l'animation n'est pas conditionnée à un marqueur"
    )
    assert '[data-ouvert="oui"] .jour {' not in STYLE, (
        "l'animation joue encore sur le simple fait d'être ouvert"
    )
    assert "function animerAgenda()" in SCRIPT
    assert "delete bloc.dataset.anime" in SCRIPT, "le marqueur n'est jamais retiré"


def test_la_vague_joue_a_l_ouverture_et_au_changement_de_mois():
    """Les deux gestes ouvrent un mois. Le second sans animation ferait un
    à-coup juste après en avoir vu une."""
    bascule = SCRIPT[SCRIPT.index("function basculerAgenda("):]
    bascule = bascule[: bascule.index("\n}\n")]
    assert "animerAgenda()" in bascule
    assert "$('mois-precedent').onclick = () => { animerAgenda();" in SCRIPT
    assert "$('mois-suivant').onclick = () => { animerAgenda();" in SCRIPT


def test_le_rang_est_diagonal_pas_lineaire():
    """Case après case de gauche à droite, c'est un balayage de machine.
    En diagonale, la grille se pose."""
    bloc = SCRIPT[SCRIPT.index("const rang = decalage + n - 1;"):]
    bloc = bloc[: bloc.index("\n\n")]
    assert "(rang % 7) + Math.floor(rang / 7)" in bloc


def test_seules_les_dates_qui_attendent_quelque_chose_s_allument():
    """Le halo sert à poser l'œil sur ce pour quoi l'élève a ouvert son agenda.
    Une date passée n'attend plus rien : la faire clignoter serait du bruit."""
    assert ('.agenda-deplie[data-anime="oui"] .jour[data-occupe="oui"]:not([data-passe="oui"])'
            in STYLE)
    assert "@keyframes jour-signale" in STYLE


def test_l_agenda_a_une_couverture_qui_pivote():
    """Un rabat vers l'avant restait « un panneau qui se déplie » — l'élève l'a
    dit deux fois. Ce qu'on reconnaît, c'est une COUVERTURE qui pivote sur sa
    charnière et découvre la page."""
    assert 'class="agenda-couverture"' in PAGE
    bloc = STYLE[STYLE.index(".agenda-couverture {"):]
    bloc = bloc[: bloc.index("}")]
    assert "transform-origin: left center" in bloc, "la charnière n'est pas sur le côté"
    assert "rotateY(0deg)" in bloc, "fermée, la couverture doit être de face"

    ouverte = STYLE[STYLE.index('[data-ouvert="oui"] .agenda-couverture {'):]
    ouverte = ouverte[: ouverte.index("}")]
    degres = float(ouverte.split("rotateY(-")[1].split("deg)")[0])
    assert degres >= 110, f"la couverture ne s'écarte que de {degres}°"


def test_la_perspective_est_sur_le_parent_direct():
    """Posée plus haut, elle ne franchit pas l'étage intermédiaire : le pivot
    s'écrase alors en un simple rétrécissement horizontal, et on ne lit plus
    un carton qui tourne."""
    bloc = STYLE[STYLE.index(".agenda-dedans {"):]
    bloc = bloc[: bloc.index("}")]
    assert "perspective:" in bloc


def test_la_couverture_ne_disparait_pas_au_milieu_du_geste():
    """backface-visibility: hidden l'escamotait net au passage de la tranche,
    en plein milieu. On voit son intérieur continuer de tourner."""
    bloc = STYLE_NU[STYLE_NU.index(".agenda-couverture {"):]
    bloc = bloc[: bloc.index("}")]
    assert "backface-visibility: hidden" not in bloc


def test_la_couverture_ne_parle_pas_aux_lecteurs_d_ecran():
    """C'est du carton. Personne n'a à l'entendre s'ouvrir."""
    bloc = PAGE[PAGE.index('class="agenda-couverture"') - 60:]
    bloc = bloc[: bloc.index("</div>")]
    assert 'aria-hidden="true"' in bloc


def test_la_reliure_marque_le_pli():
    """Sans elle, la page découverte est un rectangle ; avec, c'est la page de
    droite d'un carnet ouvert."""
    assert ".agenda-dedans::before" in STYLE


def test_la_vague_attend_que_la_couverture_soit_ouverte():
    """Jouée sous le pli, elle se perdrait derrière."""
    bloc = STYLE[STYLE.index('.agenda-deplie[data-anime="oui"] .jour {'):]
    bloc = bloc[: bloc.index("}")]
    assert "calc(.34s +" in bloc, "la vague part avant que la page soit ouverte"


def test_l_allumage_attend_que_la_grille_soit_posee():
    """Allumé pendant la vague, il se noierait dedans. C'est l'instant où l'œil
    arrive qui compte."""
    bloc = STYLE[STYLE.index('.jour[data-occupe="oui"]:not([data-passe="oui"]) {'):]
    bloc = bloc[: bloc.index("}")]
    assert "jour-signale" in bloc and ".34s +" in bloc and "+ .42s" in bloc, (
        "le halo ne part pas après l'arrivée de la case"
    )


def test_tout_s_arrete_pour_qui_demande_moins_de_mouvement():
    bloc = STYLE[STYLE.index("@keyframes jour-signale"):]
    bloc = bloc[bloc.index("@media (prefers-reduced-motion: reduce) {"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "animation: none" in bloc
    assert ".agenda-couverture { display: none; }" in bloc, (
        "la couverture continue de pivoter"
    )
