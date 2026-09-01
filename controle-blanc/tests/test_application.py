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


def test_l_invitation_se_referme_pour_de_bon():
    """Un bandeau qu'on ne peut pas faire taire finit par se lire comme de la
    publicité — sur la page d'un élève, c'est le pire endroit pour ça."""
    assert "CLE_INVITE_APP" in SCRIPT
    bloc = SCRIPT[SCRIPT.index("function fermerInviteApp()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "localStorage.setItem(CLE_INVITE_APP, 'non')" in bloc


def test_l_invitation_ne_parait_pas_dans_l_application_installee():
    bloc = SCRIPT[SCRIPT.index("function montrerInviteApp()"):]
    bloc = bloc[: bloc.index("\n}\n")]
    assert "dejaInstallee()" in bloc


def test_ios_recoit_ses_propres_instructions():
    """iOS n'émet jamais beforeinstallprompt. Sans ce cas explicite,
    l'invitation ne paraîtrait que sur Android, là où elle est le moins utile
    puisque le navigateur la propose déjà."""
    assert "function surIOS()" in SCRIPT
    assert "Sur l’écran d’accueil" in SCRIPT, "aucune marche à suivre pour iOS"
