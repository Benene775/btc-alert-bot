"""« Ma page » : le classeur de l'élève, et ce qu'il ne doit jamais devenir.

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

DEBUT = SCRIPT.index("/* ------------------------------------------------------------- ma page --- */")
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
        assert mot not in espace, f"« {mot} » apparaît dans Ma page"


def test_rien_qui_ressemble_a_une_note_ni_a_un_classement():
    """Le compteur autorisé, c'est « combien de fois cette notion est revenue ».
    Jamais un score, jamais un pourcentage, jamais une série à ne pas casser."""
    espace = PAGE[PAGE.index('id="ecran-espace"') : PAGE.index('id="ecran-contexte"')]
    for motif in (r"/20", r"\bscore\b", r"\bnote\b", r"%", r"\bclassement\b",
                  r"\bpoints\b", r"\bniveau \d", r"\bbadge\b", r"\bsérie\b"):
        assert not re.search(motif, espace, re.I), f"« {motif} » apparaît dans Ma page"
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
    assert ".slice(0, parPage())" in CODE_NU, "l'archive n'est pas coupée"
    assert ".slice(0, 3)" in CODE_NU, "les notions montrées en tête ne sont pas bornées"
    assert "SEMAINES_MAX" in CODE_NU, "la frise n'est pas bornée"
    # L'étagère est bornée par le nombre de matières du programme, pas par le
    # travail de l'élève : elle ne grandit pas avec l'année.
    assert "function matieres" in CODE_NU


def test_la_matiere_est_la_structure_de_la_page():
    """Tout ce que l'élève possède appartient à une matière : ses cours, ses
    fiches, ses contrôles, ses notions fragiles.

    Elle n'était qu'une puce de filtre, et tout le reste vivait derrière quatre
    onglets — en arrivant, on voyait son prénom et une échéance, jamais son
    année. Une tuile par matière la montre d'un coup, et l'ouvre.
    """
    assert 'id="etagere"' in PAGE, "pas d'étagère de matières"
    assert 'id="ecran-matiere"' in PAGE, "une matière ne s'ouvre nulle part"
    assert "function dessinerEtagere" in CODE_NU
    assert "function ouvrirMatiere" in CODE_NU
    assert "intercalaire" not in PAGE, "les onglets sont revenus"
    # Une tuile dit ce qu'elle contient : sans compte ni échéance, elle n'est
    # qu'un bouton de plus.
    tuile = CODE_NU[CODE_NU.index("function dessinerEtagere") :][:2600]
    for attendu in ("tuile-chiffres", "tuile-echeance", "tuile-revoir"):
        assert attendu in tuile, f"la tuile ne montre pas « {attendu} »"


def test_l_agenda_s_ouvre_depuis_la_frise():
    """L'agenda avait son panneau pliant en bas de page, après l'étagère. Il
    vit maintenant dans la carte : la frise EST sa porte. Les deux objets
    disent la même chose à deux échelles — une grille de semaines, une grille
    de jours — et l'un se déplie depuis l'autre."""
    assert 'id="pan-agenda"' not in PAGE, "le panneau pliant du bas est revenu"

    # La porte est un vrai bouton : au clavier comme au doigt.
    porte = PAGE[PAGE.index('id="bouton-agenda"') - 80 : PAGE.index('id="agenda-deplie"')]
    assert "<button" in porte, "la frise n'est pas un bouton"
    assert 'aria-expanded="false"' in porte
    assert 'aria-controls="agenda-deplie"' in porte
    assert 'id="frise-regularite"' in porte, "la frise n'est pas dans la porte"

    # L'agenda est bien dans la carte, pas ailleurs sur la page.
    carte = PAGE[PAGE.index('id="carte-annee"') : PAGE.index('espace-haut-droite')]
    assert 'id="agenda-deplie"' in carte
    assert 'id="mois-grille"' in carte


def test_l_invite_de_l_agenda_se_lit_sans_survol():
    """Une frise reste un dessin : personne ne pense à cliquer dessus. Le
    survol le dit — mais au doigt il n'y a pas de survol, donc l'invite est
    écrite en clair sous la frise, à tout moment."""
    porte = PAGE[PAGE.index('id="bouton-agenda"') : PAGE.index('id="agenda-deplie"')]
    assert 'id="frise-invite-mot"' in porte
    assert "Ouvrir l’agenda" in porte, "l'invite n'est pas écrite dans la page"

    # Et le survol ajoute son signal, sur trois plans à la fois.
    for regle in (".frise-porte:hover",
                  ".frise-porte:hover .frise-invite",
                  '.frise-porte:hover .case-frise[data-travaille="oui"]'):
        assert regle in STYLE, f"« {regle} » manque : le survol ne dit rien"


def test_la_porte_de_l_agenda_survit_a_une_frise_vide():
    """Un compte neuf n'a rien à mettre dans la frise — et c'est précisément
    quand on vient poser la date de son premier contrôle. Cacher tout le bloc,
    comme on le faisait pour éviter le papier réglé vide, emporterait la porte
    avec lui."""
    bloc = SCRIPT[SCRIPT.index("function dessinerRegularite"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "frise.hidden = !jours.size;" in bloc, "la grille vide s'affiche encore"
    assert "$('bloc-frise').hidden" not in bloc, \
        "cacher le bloc entier emporte la porte de l'agenda"


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


def test_deux_seances_du_meme_cours_se_reunissent():
    """Repartir de l'accueil crée une séance neuve.

    Photographier deux fois le même cours donnait donc deux séances jumelles, et
    l'archive affichait la même fiche autant de fois qu'on avait recommencé —
    neuf lignes « Turismo y Madrid » identiques. Dédoublonner à l'intérieur
    d'une séance ne suffisait pas : le double était entre séances.
    """
    assert "function menageSessions" in CODE_NU
    assert "function signatureCours" in CODE_NU, "rien ne reconnaît deux fois le même cours"
    # La signature tient à la matière ET aux chapitres : deux chapitres
    # différents de la même matière restent deux cours.
    signature = CODE_NU[CODE_NU.index("function signatureCours") :][:400]
    assert "matiere" in signature and "chapitres" in signature

    # Un contrôle repassé est un essai distinct : il ne doit jamais fusionner.
    fusion = CODE_NU[CODE_NU.index("function fusionner") :]
    fusion = fusion[: fusion.index("\n}\n")]
    assert "controle_id" in fusion, "les contrôles ne sont pas conservés un par un"


def test_le_menage_tourne_avant_qu_on_lise_l_historique():
    """Sinon la page affiche les doublons une fois avant de les ranger."""
    debut = SCRIPT.index("async function initialiser")
    entete = SCRIPT[debut : SCRIPT.index("const derniere = localStorage.getItem(CLE_DERNIERE)", debut)]
    assert "menageSessions()" in entete, "le ménage passe après la lecture de l'historique"


def test_les_pages_d_une_seance_disparue_sont_effacees():
    """Ce sont les objets les plus lourds du stockage : les laisser derrière une
    séance supprimée remplit le téléphone pour rien."""
    assert "function oublierPages" in SCRIPT
    oublier = SCRIPT[SCRIPT.index("function oublierSession") :]
    oublier = oublier[: oublier.index("\n}\n")]
    assert "oublierPages" in oublier
