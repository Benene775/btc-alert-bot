"""L'ouverture de l'agenda.

Une animation est du code qui ne lève jamais d'erreur : quand elle casse, elle
se contente d'être moche, ou de rejouer au mauvais moment. Ces tests tiennent
les trois choses qui la rendraient pénible plutôt que jolie.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")


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


def test_la_couverture_se_rabat_franchement():
    """Sept degrés, c'était un frémissement que personne ne voyait — l'élève a
    signalé qu'il ne voyait aucune animation, et il avait raison. Un geste doit
    être franc pour se lire comme un geste : le panneau part de la tranche."""
    bloc = STYLE[STYLE.index(".agenda-dedans {"):]
    bloc = bloc[: bloc.index("}")]
    degres = float(bloc.split("rotateX(-")[1].split("deg)")[0])
    assert degres >= 75, f"la couverture ne bascule que de {degres}°"
    assert "transform-origin: top center" in bloc, "la charnière n'est pas en haut"

    # La perspective se pose sur le parent : dans la transformation de l'enfant,
    # elle s'applique après coup et le pli s'aplatit.
    parent = STYLE[STYLE.index(".agenda-deplie {"):]
    parent = parent[: parent.index("}")]
    assert "perspective: " in parent, "sans perspective, la rotation écrase la page"


def test_l_ombre_du_pli_se_retire_en_meme_temps():
    """Sans elle, la rotation se lit comme un effet ; avec elle, comme du
    papier qui prend la lumière en s'ouvrant."""
    assert ".agenda-dedans::after" in STYLE
    assert '.agenda-deplie[data-ouvert="oui"] .agenda-dedans::after { opacity: 0; }' in STYLE


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
    bloc = STYLE[STYLE.rindex("@media (prefers-reduced-motion: reduce) {"):]
    # Le bloc qui suit la vague, celui qui couvre l'agenda.
    bloc = STYLE[STYLE.index("@keyframes jour-signale"):]
    bloc = bloc[bloc.index("@media (prefers-reduced-motion: reduce) {"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "animation: none" in bloc
    assert "transform: none" in bloc, "le pli de papier continue de basculer"
