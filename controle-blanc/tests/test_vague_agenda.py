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


def test_l_agenda_s_ouvre_par_ses_deux_battants():
    """Un seul battant, c'était encore « un panneau qui bascule ». Deux battants
    articulés sur la reliure centrale, qui s'écartent vers l'extérieur, c'est le
    geste qu'on fait avec un carnet posé à plat."""
    assert 'class="volet volet-gauche"' in PAGE
    assert 'class="volet volet-droit"' in PAGE

    gauche = STYLE_NU[STYLE_NU.index(".volet-gauche {"):]
    gauche = gauche[: gauche.index("}")]
    assert "transform-origin: right center" in gauche, "la charnière gauche n'est pas au centre"

    droit = STYLE_NU[STYLE_NU.index(".volet-droit {"):]
    droit = droit[: droit.index("}")]
    assert "transform-origin: left center" in droit, "la charnière droite n'est pas au centre"

    # Et ils partent dans des sens opposés, sinon ils se suivent au lieu de
    # s'ouvrir.
    ouvert = STYLE_NU[STYLE_NU.index('[data-ouvert="oui"] .volet-gauche {'):]
    ouvert = ouvert[: ouvert.index("}")]
    assert "rotateY(-" in ouvert
    suite = STYLE_NU[STYLE_NU.index('[data-ouvert="oui"] .volet-droit {'):]
    suite = suite[: suite.index("}")]
    assert "rotateY(1" in suite, "les deux battants tournent du même côté"


def test_l_agenda_avance_vers_le_lecteur():
    """« Comme si on l'ouvrait devant nous » : sans ce rapprochement, l'objet
    reste plaqué au fond de la page."""
    bloc = STYLE_NU[STYLE_NU.index(".agenda-dedans {"):]
    bloc = bloc[: bloc.index("}")]
    assert "scale(" in bloc and "translateZ(" in bloc, "l'agenda n'avance pas"


def test_rien_ne_reste_en_travers_du_mois(client=None):
    """Le bug signalé, et la raison d'avoir simplifié.

    Les feuillets d'une version précédente tournaient EN PLUS de leur battant :
    passé un certain angle leur rotation cumulée les ramenait de face, et ils
    restaient plantés en travers de la grille — un grand bloc crème sur la
    moitié du mois, une fois l'ouverture terminée.

    Le dos masqué ne suffit donc pas à garantir qu'il ne reste rien : la
    couverture s'éteint aussi, explicitement, à la fin du geste."""
    assert "feuillet" not in PAGE, "les feuillets sont revenus"
    bloc = STYLE_NU[STYLE_NU.index(".agenda-couverture {"):]
    bloc = bloc[: bloc.index("}")]
    assert "opacity: 1" in bloc
    assert '[data-ouvert="oui"] .agenda-couverture { opacity: 0; }' in STYLE_NU


def test_la_perspective_traverse_les_deux_etages():
    """Elle vient de .agenda-deplie et doit atteindre les battants, deux niveaux
    plus bas. Sans preserve-3d sur le chemin, la rotation s'aplatit en un simple
    rétrécissement horizontal — et on ne lit plus un carton qui tourne."""
    assert "perspective: " in STYLE_NU[STYLE_NU.index(".agenda-deplie {"):][:400]
    for classe in (".agenda-dedans {", ".agenda-couverture {"):
        bloc = STYLE_NU[STYLE_NU.index(classe):]
        bloc = bloc[: bloc.index("}")]
        assert "transform-style: preserve-3d" in bloc, classe


def test_le_battant_ne_montre_pas_son_dos():
    """Ce qui passe la tranche montrerait son envers, et le mot « Agenda » y
    reviendrait à l'endroit inverse."""
    bloc = STYLE_NU[STYLE_NU.index(".volet {"):]
    bloc = bloc[: bloc.index("}")]
    assert "backface-visibility: hidden" in bloc


def test_la_couverture_ne_parle_pas_aux_lecteurs_d_ecran():
    """C'est du carton. Personne n'a à l'entendre s'ouvrir."""
    bloc = PAGE[PAGE.index('class="agenda-couverture"') - 60:]
    bloc = bloc[: bloc.index("</div>")]
    assert 'aria-hidden="true"' in bloc


def test_la_reliure_ne_reste_pas_une_fois_le_mois_affiche():
    """Elle marque le pli pendant l'ouverture. Après, la grille occupe toute la
    largeur : une ombre centrale permanente ne se lit plus comme une reliure,
    mais comme un défaut d'affichage."""
    assert ".agenda-dedans::before" in STYLE
    assert '[data-ouvert="oui"] .agenda-dedans::before { opacity: 0; }' in STYLE_NU


def test_la_vague_attend_que_la_couverture_soit_ouverte():
    """Jouée sous le pli, elle se perdrait derrière."""
    bloc = STYLE[STYLE.index('.agenda-deplie[data-anime="oui"] .jour {'):]
    bloc = bloc[: bloc.index("}")]
    assert "calc(.22s +" in bloc, "la vague part avant que la page soit ouverte"


def test_l_allumage_attend_que_la_grille_soit_posee():
    """Allumé pendant la vague, il se noierait dedans. C'est l'instant où l'œil
    arrive qui compte."""
    bloc = STYLE[STYLE.index('.jour[data-occupe="oui"]:not([data-passe="oui"]) {'):]
    bloc = bloc[: bloc.index("}")]
    assert "jour-signale" in bloc and ".22s +" in bloc and "+ .38s" in bloc, (
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
