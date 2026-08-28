"""« Mon année » : le classeur de l'élève, et ce qu'il ne doit jamais devenir.

La page ressemble à un profil, et c'est exactement le piège. Le cahier des
charges interdit les comptes — les testeurs sont mineurs — et interdit la note.
Un espace personnel qui dérive vers le réseau social ou le tableau de scores
casserait les deux. Ces tests tiennent la frontière.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
PAGE = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPT = (WEB / "app.js").read_text(encoding="utf-8")
STYLE = (WEB / "styles.css").read_text(encoding="utf-8")

DEBUT = SCRIPT.index("/* ---------------------------------------------------------- mon année --- */")
FIN = SCRIPT.index("/* ------------------------------------------------------- pages du cahier --- */")
CODE = SCRIPT[DEBUT:FIN]

# Les commentaires expliquent souvent ce qu'on a refusé de faire — « pas de
# série, pas de score ». Les chercher dans le code sans les retirer d'abord
# ferait échouer un test sur la phrase qui dit précisément qu'on s'en abstient.
CODE_NU = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", CODE, flags=re.S))


def test_l_ecran_existe_avec_ses_sections():
    for identifiant in ("ecran-espace", "liste-agenda", "liste-reviennent",
                        "liste-mes-fiches", "liste-mes-controles", "frise-regularite",
                        "champ-prenom", "embleme", "carte-chiffres"):
        assert f'id="{identifiant}"' in PAGE, f"« {identifiant} » manque dans la page"


def test_la_carte_d_eleve_ne_quitte_jamais_l_appareil():
    """Un prénom, même local, ne doit atteindre aucune requête."""
    assert "CLE_CARTE" in SCRIPT and "localStorage" in CODE_NU
    for envoi in re.findall(r"(api|envoyerJson)\([^)]*\)", SCRIPT):
        assert "prenom" not in envoi, f"le prénom part dans une requête : {envoi}"
        assert "CLE_CARTE" not in envoi, f"la carte part dans une requête : {envoi}"
    assert "champ-prenom" not in re.sub(r"\s+", " ", " ".join(
        re.findall(r"envoyerJson\([^;]*;", SCRIPT)))


def test_aucun_compte_n_apparait():
    """Pas d'inscription, pas de connexion, pas de public : c'est la raison
    pour laquelle le produit peut être testé par des mineurs."""
    interdits = ("s'inscrire", "inscription", "connexion", "se connecter",
                 "mot de passe", "abonné", "abonnement", "follow", "partager mon profil")
    minuscules = PAGE.lower()
    espace = minuscules[minuscules.index('id="ecran-espace"') : minuscules.index('id="ecran-contexte"')]
    for mot in interdits:
        assert mot not in espace, f"« {mot} » apparaît dans Mon année"


def test_rien_qui_ressemble_a_une_note_ni_a_un_classement():
    """Le compteur autorisé, c'est « combien de fois cette notion est revenue ».
    Jamais un score, jamais un pourcentage, jamais une série à ne pas casser."""
    espace = PAGE[PAGE.index('id="ecran-espace"') : PAGE.index('id="ecran-contexte"')]
    for motif in (r"/20", r"\bscore\b", r"\bnote\b", r"%", r"\bclassement\b",
                  r"\bpoints\b", r"\bniveau \d", r"\bbadge\b", r"\bsérie\b"):
        assert not re.search(motif, espace, re.I), f"« {motif} » apparaît dans Mon année"
    # Une série, ce sont des jours consécutifs comptés puis remis à zéro : c'est
    # la mécanique qui punit un jour manqué. On vérifie qu'elle n'existe pas.
    for mecanique in ("serie", "streak", "affilée", "affilee", "consecutif", "consécutif"):
        assert mecanique not in CODE_NU.lower(), f"« {mecanique} » : mécanique de série dans le code"


def test_l_historique_se_relit_sans_index_separe():
    """Un index parallèle se désynchronise : une séance supprimée y laisserait
    une ligne fantôme. La source de vérité reste les sessions elles-mêmes."""
    assert "Object.keys(localStorage)" in CODE_NU
    assert "cle.indexOf(CLE_ETAT)" in CODE_NU


def test_une_notion_qui_revient_est_comptee_et_signalee():
    """C'est la seule chose que ce produit sait dire qu'un cahier ne dit pas."""
    assert "function notionsQuiReviennent" in CODE_NU
    assert "deja.fois += 1" in CODE_NU
    assert 'data-insistante="oui"' in STYLE or "[data-insistante=\"oui\"]" in STYLE
