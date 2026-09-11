"""Rouvrir l'application, c'est retrouver ses fiches — pas l'argumentaire.

La page d'accueil est une vitrine : le titre, la promesse, la fiche d'exemple
qui défile. Elle sert à convaincre quelqu'un qui ne connaît pas le produit.
Jusqu'ici, un élève déjà inscrit y atterrissait à CHAQUE ouverture et devait
cliquer « Ma page » pour arriver à ses affaires. Trois fois par semaine pendant
un mois, ça fait une douzaine de traversées de magasin pour atteindre son casier.

Le piège du correctif est ailleurs : « Reprendre » se réglait sur « etat », qui
est vide à la réouverture puisque personne n'a encore relu le navigateur. En
routant vers la page perso sans y toucher, un élève ayant laissé un cours en
plan n'aurait plus eu aucun chemin pour y revenir.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")


def _fin_d_initialiser() -> str:
    debut = SCRIPT.index("async function initialiser()")
    return SCRIPT[debut:SCRIPT.index("function remplirSelecteur", debut)]


def test_un_eleve_connecte_atterrit_sur_sa_page():
    bloc = _fin_d_initialiser()
    assert "if (compte) {" in bloc
    assert "return ouvrirEspace();" in bloc
    # Et l'accueil reste la porte de celui qui n'a pas de compte.
    assert "montrer('ecran-accueil');" in bloc


def test_l_accueil_reste_pour_qui_n_a_pas_de_compte():
    """Le premier écran d'un inconnu doit rester la vitrine : c'est le seul
    endroit qui explique ce que fait le produit."""
    bloc = _fin_d_initialiser()
    sans_compte = bloc[bloc.index("if (!compte) {"):]
    sans_compte = sans_compte[:sans_compte.index("return;")]
    assert "montrer(depuisLien ? 'ecran-connexion' : 'ecran-accueil')" in sans_compte


def test_un_lien_de_reprise_passe_avant_la_page_perso():
    """Ouvrir un lien reçu, c'est demander CE cours-là. Le poser sur sa page
    perso obligerait à le retrouver à la main."""
    bloc = _fin_d_initialiser()
    assert bloc.index("if (depuisLien) {") < bloc.index("if (compte) {")


def test_reprendre_marche_a_froid():
    """À la réouverture, « etat » est vide : la séance dort dans le navigateur.
    C'est précisément le moment où « Reprendre » doit marcher."""
    bloc = SCRIPT[SCRIPT.index("function reprendreLaDerniere()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "laSeanceDuRetour()" in bloc
    assert "etat = trouve;" in bloc
    assert "lirePages(etat.sessionId)" in bloc, "les photos du cours doivent revenir aussi"


def test_le_menu_voit_la_seance_endormie():
    bloc = SCRIPT[SCRIPT.index("function ouvrirMenuMarque"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "!laSeanceDuRetour()" in bloc, "le menu ne doit plus se régler sur « etat » seul"


def test_les_deux_portes_mènent_au_meme_endroit():
    """Le bouton de l'accueil et l'entrée du menu faisaient deux choses
    différentes : l'un relisait le navigateur, l'autre non."""
    assert "$('bouton-reprendre').onclick = () => reprendreLaDerniere();" in SCRIPT
    assert "ouvrirMenuMarque(false); reprendreLaDerniere();" in SCRIPT


def test_la_page_perso_vide_n_est_pas_un_cul_de_sac():
    """Un élève qui vient de s'inscrire y arrive sans aucun cours : il doit y
    trouver quoi faire, sinon le raccourci devient un mur."""
    page = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
    debut = page.index('id="ecran-espace"')
    espace = page[debut:page.index('id="bouton-quitter-espace"', debut)]
    # Le grand bouton dit quoi faire, et il est au-dessus du pli depuis qu'on a
    # remis la page dans l'ordre. Le menu des matières est là aussi : il liste
    # les douze, y compris quand on n'a encore rien fait.
    assert 'id="bouton-espace-nouveau"' in espace
    assert "Photographier un nouveau cours" in espace
    assert 'id="choix-matiere"' in espace


def test_le_retour_est_mesure():
    """Le tableau de bord compte les ouvertures par origine : sans ça, on ne
    saurait pas si les élèves reviennent."""
    bloc = _fin_d_initialiser()
    assert "tracer('ouverture', { origine: 'page_perso' })" in bloc
