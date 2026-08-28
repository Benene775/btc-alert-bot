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


def test_l_agenda_est_un_agenda_que_l_eleve_remplit():
    """Une date de contrôle se connaît des semaines avant qu'on photographie le
    cours : l'agenda doit exister avant la séance, pas en être un sous-produit."""
    assert "CLE_AGENDA" in SCRIPT, "aucun stockage de dates saisies"
    assert "function ajouterRendezVous" in CODE_NU
    assert "function retirerRendezVous" in CODE_NU
    assert 'id="mois-grille"' in PAGE, "pas de calendrier"
    assert "function formulaireRendezVous" in CODE_NU, "rien pour ajouter une date"
    # Une date posée sans cours mène à l'appareil photo, pas à une séance vide.
    assert "demarrerSession({ matiere:" in CODE_NU


def test_le_calendrier_ne_decale_pas_les_jours():
    """toISOString bascule en UTC : le soir, en France, il rend la veille."""
    assert "toISOString" not in CODE_NU.split("function cleJour")[1].split("}")[0]
    assert "function cleJour" in CODE_NU


def test_l_ecran_existe_avec_ses_sections():
    for identifiant in ("ecran-espace", "mois-grille", "jour-detail", "liste-reviennent",
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


def test_le_classeur_n_ouvre_qu_une_pile_a_la_fois():
    """Tout empilé, la page dépassait trois écrans et grandissait à chaque
    contrôle passé. Les intercalaires la rendent indépendante de l'historique."""
    espace = PAGE[PAGE.index('id="ecran-espace"') : PAGE.index('id="ecran-contexte"')]
    panneaux = re.findall(r'id="(panneau-[a-z]+)"[^>]*>', espace)
    assert len(panneaux) == 4, f"quatre piles attendues, trouvé {panneaux}"

    # Un seul panneau part visible ; les autres portent « hidden » dans le HTML,
    # pour que rien ne s'empile avant même que le script tourne.
    ouverts = [p for p in panneaux if f'id="{p}" role="tabpanel" aria-labelledby="onglet-{p[8:]}" tabindex="0">' in espace]
    assert len(ouverts) == 1, f"une seule pile doit être ouverte au départ, trouvé {ouverts}"

    assert 'role="tablist"' in espace, "la barre d'intercalaires n'est pas un tablist"
    for attendu in ('role="tabpanel"', "aria-labelledby="):
        assert attendu in espace, f"« {attendu} » manque"


def test_les_onglets_se_parcourent_au_clavier():
    """Une barre d'onglets où la tabulation traverse les quatre boutons est une
    barre d'onglets ratée : on y entre une fois, puis on circule aux flèches."""
    assert "ArrowLeft" in CODE_NU and "ArrowRight" in CODE_NU
    assert "bouton.tabIndex = actif ? 0 : -1" in CODE_NU
    assert 'setAttribute(\'aria-selected\'' in CODE_NU


def test_le_dos_de_la_carte_sort_de_l_arbre_d_accessibilite():
    """Une face retournée reste dans le document : sans « aria-hidden », un
    lecteur d'écran lit les deux faces à la suite et la tabulation entre dans
    ce qui est physiquement derrière."""
    assert "function retournerCarte" in CODE_NU
    assert "aria-hidden" in CODE_NU
