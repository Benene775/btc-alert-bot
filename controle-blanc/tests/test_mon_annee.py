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


def test_rien_n_est_cache_derriere_un_mecanisme():
    """La carte se retournait pour montrer la frise.

    Un retournement, c'est une face que les lecteurs d'écran lisent quand même,
    une tabulation qui entre dans ce qui est derrière, et surtout la plus belle
    chose de la page rendue invisible par défaut. Tout tient sur une face.
    """
    assert "function retournerCarte" not in SCRIPT, "le retournement est revenu"
    assert 'id="carte-annee"' in PAGE
    # La frise est devant, dans la carte elle-même.
    carte = PAGE[PAGE.index('id="carte-annee"') : PAGE.index('id="prochain"')]
    assert 'id="frise-regularite"' in carte, "la frise n'est pas sur la carte"
    assert 'id="carte-chiffres"' in carte, "les chiffres ne sont pas sur la carte"


def test_les_notions_se_rangent_par_matiere():
    """Sept notions à la file, c'est une liste qu'on ne lit pas.

    Elles se rangent en tiroirs par matière — sauf celles qui sont revenues
    plusieurs fois : les enfermer reviendrait à cacher la seule chose que cette
    section avait à dire.
    """
    assert "const recurrentes = notions.filter((n) => n.fois > 1)" in CODE_NU
    assert "parMatiere" in CODE_NU, "aucun regroupement par matière"
    assert "'groupe'" in CODE_NU and ".groupe {" in STYLE, "le tiroir n'existe pas"
    # Celles qui reviennent sont posées en tête, avant les tiroirs — mais en
    # nombre borné : au-delà de quelques-unes, une liste d'alertes n'alerte plus.
    assert CODE_NU.index("enTete.forEach") < CODE_NU.index("parMatiere.forEach")
    assert "const TETE_MAX" in CODE_NU, "les notions en tête ne sont pas bornées"


def test_l_archive_est_faite_pour_une_annee_entiere():
    """Une année, ce n'est pas quatre fiches : c'est trente, sur six matières.

    En rangée qui défile, la trentième était à 3800 px du bord — quinze
    glissements pour l'atteindre, et rien pour la chercher.
    """
    assert "function dessinerArchive" in CODE_NU, "fiches et contrôles ne partagent pas leur liste"
    assert "const PAR_PAGE" in CODE_NU, "la liste n'est pas bornée"
    assert "function dessinerFiltres" in CODE_NU, "aucun filtre par matière"
    assert 'id="recherche-fiches"' in PAGE and 'id="recherche-controles"' in PAGE
    # Chercher « theoreme » doit trouver « théorème » : un élève ne tape pas les accents.
    assert "normalize('NFD')" in CODE_NU, "la recherche est sensible aux accents"
    # La couleur d'une matière est son code : elle ne doit pas dépendre du hasard.
    assert "function teinteMatiere" in CODE_NU
    assert "findIndex" in CODE_NU.split("function teinteMatiere")[1][:300]


def test_rien_dans_l_espace_ne_grandit_sans_fin():
    """Chaque liste est bornée, sinon la page s'allonge avec l'année."""
    assert ".slice(0, PAR_PAGE)" in CODE_NU, "l'archive n'est pas coupée"
    assert "const TETE_MAX" in CODE_NU, "les notions récurrentes ne sont pas bornées"
    assert "SEMAINES_FRISE" in CODE_NU, "la frise n'est pas bornée"


def test_une_fiche_remplace_celle_qu_elle_refait():
    """Repasser par « je révise » sur le même chapitre empilait une fiche
    identique à chaque fois : dix lignes « Turismo y Madrid · 28 août » dans
    l'archive, impossibles à distinguer, et un stockage qui gonflait pour rien.

    Un contrôle blanc, lui, se garde à chaque fois : le repasser est un nouvel
    essai, et comparer les deux est justement l'intérêt.
    """
    assert "function garderFiche" in SCRIPT, "les fiches s'ajoutent sans se remplacer"
    # Le seul empilement autorisé est celui de garderFiche, après avoir cherché
    # un doublon. Ailleurs, c'est le bogue qui revient.
    corps = SCRIPT[SCRIPT.index("function garderFiche") :]
    corps = corps[: corps.index("\n}\n")]
    assert "etat.fiches.push" in corps
    assert SCRIPT.count("etat.fiches.push") == 1, "une fiche est encore empilée hors de garderFiche"
    assert "etat.controles.push" in SCRIPT, "les contrôles ne doivent PAS être dédoublonnés"


def test_l_archive_ne_montre_pas_de_titres_indistincts():
    """Trois « Ce qui ne tenait pas encore » à la suite ne se distinguent pas :
    dans une liste, une fiche ciblée prend le nom de son chapitre."""
    assert "fiche.type === 'ciblee'" in CODE_NU
    assert "codeMatiere" in CODE_NU, "les lignes n'ont pas de pastille de matière"
    assert "CODES_MATIERE" in SCRIPT
