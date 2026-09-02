"""Ce qui ne tient pas encore : relier une notion fragile à ce qu'il y a à relire.

Le panneau ne proposait qu'une chose — repasser un contrôle. C'est la sortie la
plus chère du produit : un quota, un quart d'heure, un appel au modèle. La
fiche, elle, est déjà écrite et déjà payée ; l'élève l'a sous la main sans le
savoir, parce que rien dans les données ne relie « la notion ratée » à « la
section de la fiche qui en parle ».

Ces tests tiennent les deux promesses du lien : proposer d'abord ce qui est
gratuit, et n'ouvrir que la bonne page. Un lien qui promet la bonne section et
en ouvre une autre coûte plus cher que pas de lien du tout.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

CODE_NU = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", SCRIPT, flags=re.S))


def bloc(nom: str) -> str:
    """Le corps d'une fonction, commentaires retirés."""
    debut = CODE_NU.index("function " + nom + "(")
    return CODE_NU[debut : CODE_NU.index("\n}\n", debut)]


def test_la_relecture_est_proposee_avant_le_test():
    """Relire coûte cinq minutes ; se retester coûte un quota, un quart d'heure
    et de l'argent. Le panneau doit donc offrir la fiche d'abord."""
    corps = bloc("ligneNotion")
    assert "fichesPourNotion" in corps, "la notion ne propose aucune fiche"
    assert corps.index("fichesPourNotion") < corps.index("Me retester là-dessus"), (
        "le contrôle blanc est proposé avant la relecture"
    )


def test_les_fiches_proposees_viennent_du_cours_ou_la_notion_a_ete_ratee():
    """Une fiche d'un autre chapitre qui emploie les mêmes mots n'a rien à dire
    ici : l'élève qui l'ouvrirait n'y trouverait pas son erreur."""
    corps = bloc("fichesPourNotion")
    assert "ou.indexOf(session.sessionId) < 0) return" in corps, (
        "les fiches ne sont pas restreintes aux séances de la notion"
    )
    # Et une notion ratée dans deux cours garde les deux.
    assert "deja.seances.push(session.sessionId)" in bloc("notionsQuiReviennent")


def test_une_fiche_ciblee_hors_sujet_n_est_jamais_proposee():
    """Une fiche ciblée ne traite QUE les notions dont elle est née. Sans
    section correspondante, la proposer revient à envoyer l'élève relire les
    erreurs de quelqu'un d'autre — la fiche générale, elle, couvre le chapitre.
    """
    assert "if (!section && fiche.type === 'ciblee') return;" in bloc("fichesPourNotion")


def test_le_lien_ouvre_la_fiche_a_la_bonne_section():
    """Ouvrir « la fiche » quand on a cliqué sur une notion, c'est retomber à la
    carte 1 d'un paquet de vingt et rendre une recherche au lieu d'une réponse.
    """
    assert "function allerASection" in CODE_NU
    assert "if (section) allerASection(section);" in bloc("ouvrirFicheGardee")
    corps = bloc("allerASection")
    assert "groupesCourants.indexOf(titre)" in corps, "la section n'est pas cherchée par son rang"
    assert "Number(c.dataset.ruban) === rang" in corps
    # Viser avant la mise en page envoie sur la mauvaise carte.
    assert "requestAnimationFrame(() => allerACarte(premiere))" in corps


def test_la_section_retenue_est_la_meilleure_et_jamais_une_egalite():
    """« Verdun et la guerre de tranchées » partage le mot « guerre » avec la
    section d'ouverture et tout le reste avec celle des tranchées : prendre la
    première rencontrée renverrait sur la mauvaise. Et deux sections à égalité,
    c'est qu'on ne sait pas laquelle ouvrir — on rend alors la fiche entière.
    """
    corps = bloc("sectionQuiTraite")
    assert "score > suivante" in corps, "une égalité peut encore gagner"
    assert "score >= PART_COMMUNE" in corps


def test_les_mots_qui_ne_distinguent_rien_sont_ecartes():
    """La liste des mots vides est française ; les cours de langue sont en
    espagnol ou en anglais, où « los » et « the » passent au travers. Mesuré sur
    la démonstration d'espagnol : « Los acuerdos de género y de número »
    atterrissait sur la section du tourisme, par « los » et « número ».
    """
    assert "function motsDistinctifs" in CODE_NU
    assert "motsDistinctifs(sections, mots)" in bloc("sectionQuiTraite")
    # Un mot présent dans une seule section la distingue toujours, même en
    # fiche courte : l'écarter viderait la comparaison.
    assert "combien < 2 ||" in bloc("motsDistinctifs")


def test_la_fiche_du_chapitre_ne_se_fait_pas_passer_pour_la_bonne_page():
    """Promettre la section et ouvrir la fiche entière est pire que ne rien
    promettre : l'élève cherche ce qu'on lui a dit d'y trouver."""
    corps = bloc("ligneNotion")
    assert "'toute la '" in corps, "la fiche entière s'annonce comme une section"
    assert "dataset.precise" in corps, "rien ne distingue les deux qualités de lien"
    assert '.revient-fiche[data-precise="oui"]' in STYLE


# --- Le comportement, pas seulement le texte du fichier ---------------------

MATCHEUR = ("sansAccent", "MOTS_VIDES", "motsUtiles", "PART_COMMUNE",
            "texteSection", "motsDistinctifs", "partCommune", "sectionQuiTraite")


def _extraire(nom: str) -> str:
    """Une fonction ou une constante du script, telle quelle."""
    debut = SCRIPT.index(("const " if nom.isupper() else "function ") + nom)
    fin = SCRIPT.index("]);", debut) + 3 if nom == "MOTS_VIDES" else (
        SCRIPT.index(";", debut) + 1 if nom.isupper() else SCRIPT.index("\n}\n", debut) + 2)
    return SCRIPT[debut:fin]


@pytest.mark.skipif(shutil.which("node") is None, reason="node absent")
def test_les_notions_de_la_demonstration_tombent_sur_la_bonne_section():
    """Le seuil et les mots écartés ne se jugent pas sur le code : on les mesure
    sur les contenus réels. Les cinq notions de la démonstration d'histoire
    doivent atterrir sur la section qui les traite, et une notion étrangère au
    chapitre ne doit tomber nulle part.
    """
    sys.path.insert(0, str(RACINE))
    os.environ.setdefault("CB_DEMO_MODE", "1")
    from app import demo

    fiche = demo.fiche_generale([{"titre": "La Première Guerre mondiale"}])
    attendu = {
        "Les trois phases de la guerre": "Une guerre d’un type nouveau",
        "La notion de guerre totale": "Une guerre d’un type nouveau",
        "Verdun et la guerre de tranchées": "La violence de masse",
        "Le génocide des Arméniens": "La violence de masse",
        "La mobilisation de l’arrière et le rôle des femmes": "L’arrière et l’année 1917",
        # Le chapitre n'en parle nulle part : aucune section ne doit gagner.
        "Le traité de Versailles et ses conséquences": None,
    }

    programme = "\n".join(_extraire(n) for n in MATCHEUR) + """
const { fiche, notions } = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const sortie = {};
notions.forEach((n) => {
  const s = sectionQuiTraite(fiche.sections, motsUtiles(n));
  sortie[n] = s ? s.titre : null;
});
console.log(JSON.stringify(sortie));
"""
    with tempfile.TemporaryDirectory() as dossier:
        js = Path(dossier) / "matcheur.js"
        js.write_text(programme, encoding="utf-8")
        donnees = Path(dossier) / "donnees.json"
        donnees.write_text(json.dumps({"fiche": fiche, "notions": list(attendu)},
                                      ensure_ascii=False), encoding="utf-8")
        fait = subprocess.run(["node", str(js), str(donnees)],
                              capture_output=True, text=True)
    assert fait.returncode == 0, fait.stderr
    assert json.loads(fait.stdout) == attendu
