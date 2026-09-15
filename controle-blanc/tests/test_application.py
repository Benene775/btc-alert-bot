"""Repère comme application installable.

Les élèves sont sur leur téléphone. Une icône sur l'écran d'accueil, qui ouvre
en plein écran et démarre sans réseau, c'est ce qui sépare « un site qu'on
retrouve dans ses onglets » d'un outil qu'on ouvre en sortant du cours.

Ce n'est pas une application de magasin : c'est la page elle-même, que le
téléphone accepte de garder. Pour six testeurs, ça évite un compte développeur,
une revue de plusieurs semaines et une seconde base de code, pour le même
résultat à l'usage.
"""

from __future__ import annotations

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
WEB = RACINE / "web"
PAGE = (WEB / "index.html").read_text(encoding="utf-8")
SCRIPT = (WEB / "app.js").read_text(encoding="utf-8")
AGENT = (WEB / "agent.js").read_text(encoding="utf-8")
MANIFESTE = json.loads((WEB / "manifeste.json").read_text(encoding="utf-8"))


def test_le_manifeste_dit_ce_qu_il_faut():
    assert MANIFESTE["display"] == "standalone", "l'app s'ouvrirait dans un onglet"
    assert MANIFESTE["start_url"] == "/"
    assert MANIFESTE["lang"] == "fr"
    assert MANIFESTE["short_name"], "sans nom court, l'icône porte une étiquette tronquée"


def test_une_icone_supporte_le_recadrage_d_android():
    """Android recadre les icônes en cercle. Sans version « maskable », le
    dessin est rogné — c'est la marque qui y passe."""
    formes = {i.get("purpose") for i in MANIFESTE["icons"]}
    assert "maskable" in formes
    assert "any" in formes


def test_les_icones_existent_vraiment():
    """Un manifeste qui pointe vers une icône absente s'installe quand même —
    avec une icône grise par défaut, et personne ne comprend pourquoi."""
    for icone in MANIFESTE["icons"]:
        chemin = WEB / icone["src"].lstrip("/")
        assert chemin.exists(), icone["src"]
        assert chemin.stat().st_size > 500, f"{icone['src']} est vide ou presque"
    assert (WEB / "icones" / "icone-apple-180.png").exists(), "iOS n'aura pas d'icône"


def test_ios_est_declare_a_part():
    """iOS ne lit pas le manifeste pour l'écran d'accueil : sans ces balises,
    l'app s'installe avec une capture d'écran en guise d'icône."""
    assert 'rel="manifest"' in PAGE
    assert 'name="apple-mobile-web-app-capable"' in PAGE
    assert 'rel="apple-touch-icon"' in PAGE


def test_l_api_ne_passe_jamais_par_le_cache():
    """La règle qui compte. Servir un classeur ou un quota depuis le cache
    ferait réapparaître du travail effacé et mentir les compteurs — exactement
    le genre de panne qu'on ne remarque qu'après."""
    assert "url.pathname.startsWith('/api/')" in AGENT
    bloc = AGENT[AGENT.index("if (url.pathname.startsWith('/api/')"):]
    bloc = bloc[: bloc.index("\n\n")]
    assert "return;" in bloc, "l'agent intercepte quand même les appels d'API"


def test_la_coque_va_chercher_le_reseau_d_abord():
    """Pendant la phase de test le code change souvent. Un cache d'abord
    bloquerait les élèves sur une version périmée, ce qui coûte plus cher qu'un
    chargement une seconde plus lent."""
    bloc = AGENT[AGENT.index("evenement.respondWith(\n    fetch(requete)"):]
    assert "fetch(requete)" in bloc
    assert ".catch(() => caches.match(requete)" in bloc, "aucun secours hors ligne"


def test_seules_les_reponses_valables_sont_gardees():
    """Mettre une page d'erreur en cache la rejouerait à chaque démarrage hors
    ligne, et l'élève croirait l'application cassée."""
    assert "if (reponse && reponse.ok)" in AGENT


def test_une_version_perimee_du_cache_est_effacee():
    assert "caches.keys()" in AGENT and "caches.delete(n)" in AGENT
    assert "self.clients.claim()" in AGENT


def test_le_bandeau_revient_tant_que_ce_n_est_pas_installe():
    """Règle inversée après les premiers élèves. L'invitation se fermait pour de
    bon au premier « non merci » : ils l'ont fermée, puis n'ont pas su installer,
    et plus rien ne le leur reproposait. « Plus tard » veut maintenant dire
    demain, et seule l'installation fait taire le bandeau."""
    assert "SILENCE_INSTALL" in SCRIPT
    bloc = SCRIPT[SCRIPT.index("function installationRepoussee()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "> Date.now()" in bloc, "le silence doit expirer, pas être définitif"
    assert "'non'" not in bloc, "plus de « non » qui vaut pour toujours"

    pose = SCRIPT[SCRIPT.index("$('bouton-installer-plus-tard').onclick"):][:400]
    assert "Date.now() + SILENCE_INSTALL" in pose


def test_le_bandeau_ne_parait_pas_dans_l_application_installee():
    bloc = SCRIPT[SCRIPT.index("function rafraichirBandeauInstall()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "dejaInstallee()" in bloc


def test_le_bandeau_est_au_dessus_des_ecrans_et_pas_dans_l_un_d_eux():
    """L'ancienne invitation vivait au bas de la page de l'élève : il fallait
    faire défiler jusqu'en bas pour la trouver. Les élèves ne l'ont jamais vue."""
    assert PAGE.index('id="bandeau-install"') < PAGE.index('<main id="scene">')
    assert 'id="ecran-espace"' not in PAGE[: PAGE.index('id="bandeau-install"')]


def test_ios_recoit_ses_propres_instructions():
    """iOS n'émet jamais beforeinstallprompt. Sans ce cas explicite, la marche à
    suivre ne paraîtrait que sur Android, là où elle est le moins utile puisque
    le navigateur la propose déjà."""
    assert "function surIOS()" in SCRIPT
    assert "Sur l’écran d’accueil" in SCRIPT, "aucune marche à suivre pour iOS"


def test_les_trois_pieges_d_ios_sont_nommes():
    """Trois choses ont fait échouer les premiers élèves, et aucune ne se devine :
    le bouton « Partager » n'a pas de nom écrit, il est en bas de l'écran, et
    l'entrée cherchée est loin dans une liste qu'il faut faire défiler."""
    bloc = SCRIPT[SCRIPT.index("if (surIOS()) {", SCRIPT.index("function marcheASuivre()")):]
    bloc = bloc[: bloc.index("if (inviteInstallation)")]
    assert "en bas de l’écran" in bloc, "où se trouve le bouton"
    assert "vers le haut" in bloc, "la liste se fait défiler"
    assert "SIGNE_PARTAGE" in bloc, "le bouton est dessiné, pas seulement nommé"


def test_un_navigateur_embarque_est_reconnu_et_nomme():
    """Un lien ouvert depuis Instagram ou Snapchat ouvre une fenêtre interne qui
    n'a pas l'entrée « Sur l'écran d'accueil ». Lui répéter la marche à suivre de
    Safari, c'est donner tort à un élève qui a tout bien fait."""
    assert "function navigateurEmbarque()" in SCRIPT
    for application in ("Instagram", "Snapchat", "FBAN", "TikTok"):
        assert application in SCRIPT, application
    bloc = SCRIPT[SCRIPT.index("function marcheASuivre()"):]
    assert "Ouvrir dans " in bloc[: bloc.index("if (surIOS() && !surSafariIOS())")]


def test_sur_ios_un_autre_navigateur_renvoie_vers_safari():
    """Sur iPhone, seule une application posée depuis Safari reçoit les
    notifications. Installer depuis Chrome donne une icône qui ne préviendra
    jamais de rien — et c'est justement pour ça qu'on installe."""
    assert "function surSafariIOS()" in SCRIPT
    for autre in ("CriOS", "FxiOS", "EdgiOS"):
        assert autre in SCRIPT, autre
    bloc = SCRIPT[SCRIPT.index("if (surIOS() && !surSafariIOS())"):]
    bloc = bloc[: bloc.index("if (surIOS()) {")]
    assert "Safari" in bloc
    assert "rappel" in bloc or "prévenu" in bloc, "dire ce qu'on perd sans Safari"


def test_le_bandeau_se_tait_pendant_un_controle():
    """On ne distrait pas quelqu'un qui compose."""
    assert ':root[data-ecran="controle"] .bandeau-install' in \
        (WEB / "styles.css").read_text(encoding="utf-8")
