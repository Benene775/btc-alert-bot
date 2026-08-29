"""L'écran de connexion et d'inscription, côté navigateur.

Le serveur est testé ailleurs (`test_entree.py`). Ici on tient quatre choses que
seule la page peut casser :

  1. ni le jeton ni le mot de passe ne doivent être rangés par le script — le
     premier vit dans un cookie que `document.cookie` ne voit pas, le second ne
     fait qu'un aller ;
  2. le classeur d'un élève ne doit pas s'ouvrir pour le suivant sur la même
     tablette : les clés du navigateur portent l'identifiant du compte ;
  3. la page d'accueil ne doit plus promettre « sans compte », puisqu'il y en a
     un maintenant. Une promesse fausse est pire qu'une promesse absente ;
  4. les formulaires doivent être de vrais formulaires : sans ça, pas de touche
     Entrée, pas de clavier adapté, et aucun gestionnaire de mots de passe.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
WEB = RACINE / "web"
PAGE = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPT = (WEB / "app.js").read_text(encoding="utf-8")
STYLE = (WEB / "styles.css").read_text(encoding="utf-8")


def test_l_ecran_porte_la_connexion_l_inscription_et_l_oubli():
    assert 'id="ecran-connexion"' in PAGE
    for identifiant in (
        # connexion
        "onglet-connexion", "volet-connexion", "champ-email", "champ-mdp",
        "bouton-connexion", "bouton-oubli",
        # inscription
        "onglet-inscription", "volet-inscription", "champ-prenom-inscription",
        "champ-classe-inscription", "champ-email-inscription",
        "champ-mdp-inscription", "champ-mdp-confirmation", "bouton-inscription",
        # mot de passe oublié
        "volet-oubli", "champ-email-oubli", "bouton-envoyer-code",
        "volet-code", "champ-code", "champ-mdp-nouveau", "bouton-reinitialiser",
        "bouton-renvoyer", "bouton-changer-adresse",
    ):
        assert f'id="{identifiant}"' in PAGE, f"« {identifiant} » manque"


def test_l_inscription_demande_le_minimum_et_pas_un_champ_de_plus():
    """Prénom et classe servent (l'un nomme sa page, l'autre règle le niveau).
    Un nom de famille, une date de naissance ou un établissement seraient de la
    donnée personnelle collectée sans usage — donc de la donnée à protéger,
    à justifier et à effacer pour rien."""
    volet = PAGE.split('id="volet-inscription"')[1].split("</form>")[0]
    champs = set(re.findall(r'id="(champ-[a-z-]+)"', volet))
    assert champs == {"champ-prenom-inscription", "champ-classe-inscription",
                      "champ-email-inscription", "champ-mdp-inscription",
                      "champ-mdp-confirmation"}, f"champs inattendus : {champs}"
    # On regarde les champs, pas le texte : « restent dans ce téléphone » est une
    # promesse, pas une demande de numéro.
    demandes = " ".join(re.findall(r"<label[^>]*>(.*?)</label>", volet, re.S)).lower()
    for interdit in ("naissance", "nom de famille", "établissement", "téléphone", "adresse postale"):
        assert interdit not in demandes, f"l'inscription demande « {interdit} »"


def test_le_mot_de_passe_peut_se_relire():
    """Sur un clavier de téléphone, un mot de passe qu'on ne peut pas relire est
    un mot de passe qu'on retape trois fois — puis qu'on écrit sur un cahier."""
    for bouton in ("voir-mdp", "voir-mdp-inscription", "voir-mdp-nouveau"):
        assert f'id="{bouton}"' in PAGE, f"« {bouton} » manque"
    assert 'aria-pressed="false"' in PAGE, "l'état doit être annoncé, pas seulement peint"
    assert ".voir-mdp" in STYLE


def test_la_marque_y_est_beaucoup_plus_grande_qu_ailleurs():
    """C'est le seul écran où l'élève confie quelque chose : il doit voir à qui.
    Le premier jet réutilisait le logo de 32 px du bandeau — invisible."""
    assert 'class="logo-geant"' in PAGE
    bloc = STYLE[STYLE.index(".logo-geant {"):]
    bloc = bloc[: bloc.index("}")]
    taille = int(re.search(r"width:\s*(\d+)px", bloc).group(1))
    normal = STYLE[STYLE.index(".logo-marque {"):]
    normal = int(re.search(r"width:\s*(\d+)px", normal[: normal.index("}")]).group(1))
    assert taille >= normal * 2, f"le logo d'entrée fait {taille}px contre {normal}px ailleurs"
    assert 'href="#glyphe-repere"' in PAGE.split('id="ecran-connexion"')[1][:1200], \
        "l'écran d'entrée doit reprendre le glyphe, pas un second dessin"


def test_les_volets_sont_de_vrais_formulaires():
    """Un <div> avec un onclick n'accepte pas la touche Entrée, n'affiche pas
    « envoyer » sur le clavier d'un téléphone, et ne dit rien aux gestionnaires
    de mots de passe. Trois pertes pour rien."""
    entree = PAGE.split('id="ecran-connexion"')[1].split("</section>")[0]
    assert entree.count("<form") == 4, "connexion, inscription, oubli, code"
    assert entree.count('type="submit"') == 4
    assert 'autocomplete="email"' in entree
    assert 'autocomplete="current-password"' in entree, "le gestionnaire doit savoir remplir"
    assert entree.count('autocomplete="new-password"') >= 2, "et savoir proposer"
    assert 'autocomplete="one-time-code"' in entree, "le code reçu doit se remplir tout seul"
    assert 'inputmode="numeric"' in entree, "un pavé numérique pour six chiffres"


def test_les_onglets_sont_annonces_comme_des_onglets():
    """Un lecteur d'écran doit dire « onglet 1 sur 2, sélectionné », pas
    « bouton ». C'est trois attributs, et sans eux la moitié du sens est peinte
    au lieu d'être dite."""
    assert 'role="tablist"' in PAGE
    assert PAGE.count('role="tab"') == 2
    assert PAGE.count('role="tabpanel"') == 2
    assert 'aria-controls="volet-connexion"' in PAGE


def test_ni_le_jeton_ni_le_mot_de_passe_ne_sont_gardes_par_le_script():
    """Le cookie est HttpOnly. Un script qui essaie de le lire, ou qui range le
    mot de passe « pour la prochaine fois », annulerait la protection sans que
    rien ne casse — donc sans que personne ne s'en aperçoive."""
    assert "document.cookie" not in SCRIPT, "le script touche au cookie"
    rangements = re.findall(r"(?:localStorage|sessionStorage)\.setItem\(\s*([^,]+)", SCRIPT)
    suspects = [r for r in rangements
                if re.search(r"jeton|token|auth|cookie|mdp|passe|password", r, re.I)]
    assert not suspects, f"un secret est rangé dans le navigateur : {suspects}"
    # Ce qu'on fait à la place : « suis-je connecté ? » est une question au serveur.
    assert "'/api/auth/moi'" in SCRIPT
    # Et le champ est vidé dès que la requête est partie.
    for champ in ("champ-mdp", "champ-mdp-inscription", "champ-mdp-nouveau"):
        assert f"$('{champ}').value = ''" in SCRIPT, f"« {champ} » n'est jamais vidé"


def test_le_classeur_est_range_sous_le_compte():
    """Deux élèves qui se prêtent une tablette ne doivent pas voir le travail
    l'un de l'autre. Leur classeur est dans CE navigateur, et rien d'autre ne
    l'y sépare."""
    assert "function attacherAuCompte" in SCRIPT
    bloc = SCRIPT[SCRIPT.index("function attacherAuCompte"):]
    bloc = bloc[: bloc.index("\n}\n")]
    for cle in ("CLE_ETAT", "CLE_DERNIERE", "CLE_CARTE", "CLE_AGENDA", "BASE_PAGES"):
        assert cle in bloc, f"« {cle} » n'est pas rattachée au compte"
    # Et rien ne doit rester en « const » : le préfixe se pose après l'entrée.
    for cle in ("CLE_ETAT", "CLE_CARTE", "CLE_AGENDA", "BASE_PAGES"):
        assert f"const {cle} =" not in SCRIPT, f"« {cle} » est figée avant qu'on sache qui entre"


def test_on_attache_le_compte_avant_de_lire_quoi_que_ce_soit():
    """Lire d'abord et attacher ensuite ferait lire le classeur de personne — ou
    celui du dernier élève passé sur ce navigateur."""
    debut = SCRIPT.index("async function initialiser")
    corps = SCRIPT[debut: SCRIPT.index("\n}\n", debut)]
    assert corps.index("await qui()") < corps.index("menageSessions()")
    assert corps.index("attacherAuCompte") < corps.index("menageSessions()")


def test_les_deux_portes_du_produit_demandent_d_entrer():
    for fonction in ("async function demarrerSession", "function ouvrirEspace"):
        bloc = SCRIPT[SCRIPT.index(fonction):]
        bloc = bloc[: bloc.index("\n}\n")]
        assert "exigerEntree" in bloc, f"« {fonction} » ne demande pas d'entrer"


def test_un_401_ramene_a_la_porte_sans_dire_erreur():
    """Un jeton qui expire au bout de trente jours n'est pas une panne : c'est
    la vie normale du produit. Le message rouge ferait croire l'inverse."""
    bloc = SCRIPT[SCRIPT.index("function gererErreur"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "'entree'" in bloc and "exigerEntree" in bloc


def test_la_page_d_accueil_ne_promet_plus_ce_qui_n_est_plus_vrai():
    """Il y a un compte maintenant. « Sans compte » sur la page d'accueil serait
    un mensonge — et le premier que l'élève découvrirait en cliquant."""
    accueil = PAGE.split('id="ecran-accueil"')[1].split('id="ecran-connexion"')[0]
    for mensonge in ("Sans compte", "sans compte", "Aucune donnée"):
        assert mensonge not in accueil, f"« {mensonge} » n'est plus vrai"
    # Ce qui reste vrai, et qu'on doit continuer à dire.
    assert "téléphone" in accueil


def test_effacer_son_compte_efface_aussi_ce_navigateur():
    """Effacer côté serveur seulement laisserait tout le travail lisible au
    prochain qui entre avec la même adresse sur ce téléphone."""
    bloc = SCRIPT[SCRIPT.index("function effacerLeNavigateur"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "localStorage.removeItem" in bloc
    assert "indexedDB.deleteDatabase" in bloc
    assert 'id="bouton-effacer-compte"' in PAGE


def test_sortir_ne_jette_pas_le_travail():
    """Se déconnecter sur un ordinateur partagé ne doit pas effacer le classeur :
    il est rangé sous le préfixe du compte, et il attend le retour de l'élève."""
    bloc = SCRIPT[SCRIPT.index("function oublierLeCompte"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "removeItem" not in bloc and "clear()" not in bloc


def test_la_page_ne_promet_pas_une_synchronisation_qui_n_existe_pas():
    """Avec un compte, l'élève s'attend à retrouver ses fiches sur un autre
    appareil. Ce n'est pas ce que fait le produit : elles vivent dans le
    navigateur. Tant que ce n'est pas vrai, la page ne doit pas le dire."""
    accueil = PAGE.split('id="ecran-accueil"')[1].split('id="ecran-connexion"')[0]
    entree = PAGE.split('id="ecran-connexion"')[1].split("</section>")[0]
    for promesse in ("n’importe quel appareil", "tous tes appareils", "synchronis",
                     "partout", "d’un appareil à l’autre"):
        for endroit, nom in ((accueil, "l'accueil"), (entree, "l'entrée")):
            assert promesse not in endroit.lower(), f"« {promesse} » promis sur {nom}"
