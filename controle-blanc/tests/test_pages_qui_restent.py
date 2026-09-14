"""Ce qu'il reste, dit au moment où l'élève photographie son cours.

Le compteur de pages existait, mais il se cachait tant qu'on n'était pas à
vingt pages de la limite : l'idée était qu'un compteur permanent transforme
« photographie ton cours » en « attention à ta consommation ». Demandé dans
l'autre sens en usage réel — rappeler ici combien de cours il reste — parce que
l'élève qui pose ses feuilles sur la table veut le savoir AVANT de les
photographier, pas au moment où on les lui refuse.

Et le dire en COURS, pas en pages : « il te reste 64 pages » demandait une
division avant de vouloir dire quelque chose. Le budget, lui, se compte
toujours en pages côté serveur — c'est l'affichage qui traduit.

Ce qui doit tenir :

1. La phrase est là dès l'arrivée sur l'écran, sans attendre le réseau.
2. Elle parle en cours. Les pages ne reviennent qu'aux deux endroits où elles
   sont la seule vérité : sous un cours entier (cinq feuilles en fin de mois),
   et quand il faut retirer des photos qui dépassent.
3. Le nombre de cours est un PLANCHER — huit pages par cours, arrondi vers le
   bas. Il peut annoncer moins que ce qui est possible, jamais plus.
4. Elle ne ment jamais sur ce qui est déjà posé sur l'écran : les pages en
   attente sont comptées dedans, et la phrase le dit.
5. Sans compte ni réseau, elle se tait plutôt que d'annoncer un chiffre faux.
6. Le compteur des fiches et des contrôles parle la même langue : la chose et
   ce qu'il en reste, pas « il t'en reste 8 sur 8 ».
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

CODE_NU = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", SCRIPT, flags=re.S))

PHOTOS = PAGE[PAGE.index('id="ecran-photos"') : PAGE.index('id="ecran-perimetre"')]


def bloc(nom: str) -> str:
    debut = CODE_NU.index("function " + nom + "(")
    return CODE_NU[debut : CODE_NU.index("\n}\n", debut)]


def test_le_rappel_vit_sur_l_ecran_des_photos():
    """Ailleurs, ce serait une note de frais. Ici, c'est l'information dont on a
    besoin juste avant d'appuyer."""
    assert 'id="reste-pages"' in PHOTOS
    # Sous la zone qui ajoute, pas au-dessus : l'action d'abord, son coût après.
    assert PHOTOS.index('id="zone-photos"') < PHOTOS.index('id="reste-pages"')
    assert PHOTOS.index('id="reste-pages"') < PHOTOS.index('id="bouton-analyser"')


def test_il_s_affiche_sans_attendre_la_reponse_du_serveur():
    """Les quotas sont redemandés à l'entrée, et la réponse met un aller-retour
    à venir. L'écran s'ouvrirait donc sans son rappel, une fois sur deux, sur un
    réseau de collège."""
    assert "if (id === 'ecran-photos') { peindreRestePages(); rafraichirQuotas(); }" in CODE_NU
    # Et il est repeint quand la vraie réponse arrive.
    assert "peindreRestePages()" in bloc("peindreQuotas")
    # Et à chaque photo ajoutée ou retirée.
    assert "peindreRestePages()" in bloc("dessinerPhotos")


def test_plus_aucun_seuil_ne_le_cache():
    """Le seuil était la raison d'être de l'ancien compteur ; c'est lui que la
    demande renverse. S'il revient, le rappel disparaît les trois quarts du
    mois — exactement quand il sert."""
    assert "SEUIL_RESTE_PAGES" not in SCRIPT
    corps = bloc("peindreRestePages")
    cachettes = corps.count("cible.hidden = true")
    assert cachettes == 1, "le rappel se cache ailleurs que hors ligne"
    assert "if (!compteur)" in corps


def test_les_cours_se_comptent_a_la_baisse():
    """Math.floor, et pas round : annoncer un cours qu'on ne peut pas
    photographier en entier, c'est promettre ce qu'on refusera ensuite."""
    assert "Math.floor(pages / (config.max_photos || 8))" in bloc("cequiReste")
    # Sous un cours entier, les pages reprennent la main.
    assert "phrasePages(pages)" in bloc("cequiReste")


def test_les_pages_ne_reviennent_que_la_ou_elles_sont_la_seule_verite():
    """Le chiffre du mois ne se dit plus en pages : c'est ce qui a été demandé.
    Mais retirer « deux cours de trop » ne veut rien dire quand ce sont des
    photos qu'on enlève une par une."""
    corps = bloc("peindreRestePages")
    assert "cequiReste(restant)" in corps
    assert corps.count("phrasePages(") == 1, "les pages parlent ailleurs que sur le dépassement"
    assert "de trop" in corps[corps.index("phrasePages(") :]


def test_la_ligne_reste_lisible_maintenant_qu_on_la_lit_a_chaque_fois():
    assert ".reste-pages[data-epuise] { color: var(--rouge); }" in STYLE
    taille = re.search(r"\.reste-pages \{[^}]*?font-size: (\.?\d*\.?\d+)rem", STYLE, re.S)
    assert taille, "la taille du rappel n'est plus fixée"
    assert float(taille.group(1)) >= 0.76, "trop petit pour une phrase permanente"


# --- Les phrases elles-mêmes, exécutées ------------------------------------

MORCEAUX = ("phrasePages", "phraseCours", "cequiReste", "peindreRestePages")

CAS = [
    # (pages restantes au serveur, photos déjà posées) -> phrase, épuisé
    ((64, 0), "Il te reste 8 cours à photographier ce mois-ci.", False),
    ((64, 4), "Après celui-ci, il te restera 7 cours à photographier ce mois-ci.", False),
    ((16, 0), "Il te reste 2 cours à photographier ce mois-ci.", False),
    # Un plancher : quinze pages ne font pas deux cours.
    ((15, 0), "Il te reste un cours à photographier ce mois-ci.", False),
    # La fin du mois, où les pages redeviennent la seule vérité utile.
    ((7, 0), "Il te reste 7 pages à photographier ce mois-ci.", False),
    ((1, 0), "Il te reste une page à photographier ce mois-ci.", False),
    ((10, 4), "Après celui-ci, il te restera 6 pages à photographier ce mois-ci.", False),
    ((8, 8), "Avec celles-ci, c\u2019est ton dernier cours du mois. \u00c7a repart le 1er.", True),
    ((0, 0), "Tu as photographié tous tes cours du mois. Ça repart le 1er.", True),
    ((3, 4), "Ça fait une page de trop pour ce mois-ci. Retires-en, ou garde le reste pour le 1er.", True),
    ((3, 6), "Ça fait 3 pages de trop pour ce mois-ci. Retires-en, ou garde le reste pour le 1er.", True),
]


def _extraire(nom: str) -> str:
    debut = SCRIPT.index("function " + nom + "(")
    return SCRIPT[debut : SCRIPT.index("\n}\n", debut) + 2]


@pytest.mark.skipif(shutil.which("node") is None, reason="node absent")
def test_chaque_etat_du_mois_donne_sa_phrase():
    """Les cas limites de ce rappel sont tous à un mot près — « reste » et
    « restera », « un cours » et « 1 cours », « avec celles-ci » quand il n'y a
    pas de celles-ci, et le basculement des cours vers les pages en fin de
    mois. On les lit donc pour de vrai."""
    programme = "\n".join(_extraire(n) for n in MORCEAUX) + """
const cible = { hidden: null, textContent: '', dataset: {} };
function $(id) { return id === 'reste-pages' ? cible : null; }
let config = { max_photos: 8 };
let quotasMois = null;
let photosEnAttente = [];

const sortie = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8')).map(([reste, poses]) => {
  quotasMois = { analyse: { plafond: 64, restant: reste } };
  photosEnAttente = Array.from({ length: poses });
  cible.dataset = {};
  peindreRestePages();
  return [cible.textContent, Boolean(cible.dataset.epuise), cible.hidden];
});

// Hors ligne : rien du tout, pas un zéro.
quotasMois = null;
cible.textContent = 'reste d’avant';
peindreRestePages();
sortie.push([cible.textContent, Boolean(cible.dataset.epuise), cible.hidden]);
console.log(JSON.stringify(sortie));
"""
    with tempfile.TemporaryDirectory() as dossier:
        js = Path(dossier) / "rappel.js"
        js.write_text(programme, encoding="utf-8")
        entrees = Path(dossier) / "cas.json"
        entrees.write_text(json.dumps([etat for etat, _, _ in CAS]), encoding="utf-8")
        fait = subprocess.run(["node", str(js), str(entrees)], capture_output=True, text=True)

    assert fait.returncode == 0, fait.stderr
    rendu = json.loads(fait.stdout)
    for (etat, phrase, epuise), (dit, rouge, cache) in zip(CAS, rendu):
        assert dit == phrase, f"{etat} : « {dit} »"
        assert rouge is epuise, f"{etat} : la couleur d'alerte tombe mal"
        assert cache is False, f"{etat} : le rappel se cache"
    assert rendu[-1][2] is True, "sans quota connu, le rappel devrait se taire"


# --- La même langue sous le bouton qui fabrique ------------------------------

def test_le_compteur_des_outils_nomme_la_chose_au_lieu_de_compter_sur_huit():
    """« Il t'en reste 8 sur 8 » demande de tenir deux chiffres et de deviner de
    quoi on parle. Sous une liste de fiches, « il te reste 8 fiches » se lit
    sans rien tenir du tout."""
    corps = bloc("dessinerFabriquer")
    assert "phraseOutil(surLesFiches, etatQuota.restant)" in corps
    assert "etatQuota.plafond" not in corps, "le dénominateur est revenu"
    assert "Plafond atteint" not in corps, "la langue administrative est revenue"
    # Épuisé, on dit quand ça repart — comme sur l'écran des photos.
    assert "Ça repart le 1er." in corps


@pytest.mark.skipif(shutil.which("node") is None, reason="node absent")
def test_le_pluriel_de_controle_blanc_n_est_pas_un_s_colle_au_bout():
    """Le piège de la phrase : « contrôle blancs ». Les deux formes s'écrivent
    en entier, et on le vérifie plutôt que de l'espérer."""
    programme = _extraire("phraseOutil") + """
console.log(JSON.stringify([[true, 1], [true, 8], [false, 1], [false, 8]]
  .map(([f, n]) => phraseOutil(f, n))));
"""
    with tempfile.TemporaryDirectory() as dossier:
        js = Path(dossier) / "outils.js"
        js.write_text(programme, encoding="utf-8")
        fait = subprocess.run(["node", str(js)], capture_output=True, text=True)
    assert fait.returncode == 0, fait.stderr
    assert json.loads(fait.stdout) == [
        "une fiche", "8 fiches", "un contrôle blanc", "8 contrôles blancs",
    ]
