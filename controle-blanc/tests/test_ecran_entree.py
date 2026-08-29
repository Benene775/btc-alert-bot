"""L'écran d'entrée, côté navigateur, et ce que la page promet à l'élève.

Le serveur est testé ailleurs (`test_entree.py`). Ici on tient trois choses que
seule la page peut casser :

  1. le jeton ne doit jamais passer par le script — il vit dans un cookie que
     `document.cookie` ne voit pas ;
  2. le classeur d'un élève ne doit pas s'ouvrir pour le suivant sur la même
     tablette : les clés du navigateur portent l'identifiant du compte ;
  3. la page d'accueil ne doit plus promettre « sans compte », puisqu'il y en a
     un maintenant. Une promesse fausse est pire qu'une promesse absente.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
WEB = RACINE / "web"
PAGE = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPT = (WEB / "app.js").read_text(encoding="utf-8")
STYLE = (WEB / "styles.css").read_text(encoding="utf-8")


def test_l_ecran_d_entree_existe_avec_ses_deux_volets():
    assert 'id="ecran-connexion"' in PAGE
    for identifiant in ("volet-adresse", "champ-email", "bouton-envoyer-code",
                        "volet-code", "champ-code", "bouton-entrer",
                        "bouton-renvoyer", "bouton-changer-adresse"):
        assert f'id="{identifiant}"' in PAGE, f"« {identifiant} » manque"


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


def test_les_deux_formulaires_sont_de_vrais_formulaires():
    """Un <div> avec un onclick n'accepte pas la touche Entrée, n'affiche pas
    « envoyer » sur le clavier d'un téléphone, et ne dit rien aux gestionnaires
    de mots de passe. Trois pertes pour rien."""
    entree = PAGE.split('id="ecran-connexion"')[1].split("</section>")[0]
    assert entree.count("<form") == 2
    assert 'type="submit"' in entree
    assert 'autocomplete="email"' in entree
    assert 'autocomplete="one-time-code"' in entree, "le code reçu doit se remplir tout seul"
    assert 'inputmode="numeric"' in entree, "un pavé numérique pour six chiffres"


def test_le_jeton_ne_passe_jamais_par_le_script():
    """Le cookie est HttpOnly. Un script qui essaie de le lire ou de le ranger
    dans localStorage annulerait la protection sans que rien ne casse."""
    assert "document.cookie" not in SCRIPT, "le script touche au cookie"
    # Rien qui ressemble à ranger un secret d'authentification côté navigateur.
    rangements = re.findall(r"(?:localStorage|sessionStorage)\.setItem\(\s*([^,]+)", SCRIPT)
    suspects = [r for r in rangements if re.search(r"jeton|token|auth|cookie", r, re.I)]
    assert not suspects, f"un secret d'entrée est rangé dans le navigateur : {suspects}"
    # Ce qu'on fait à la place : « suis-je entré ? » est une question au serveur.
    assert "'/api/auth/moi'" in SCRIPT


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
    assert "pas de mot de passe" in accueil.lower()
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
