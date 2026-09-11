"""Ce que le navigateur a le droit de garder, et pendant combien de temps.

Sans en-tête « Cache-Control », un navigateur invente sa propre règle : il garde
le fichier une fraction du temps écoulé depuis sa dernière modification. Ça ne
se voit pas en développement, où l'on recharge de force, et très mal en ligne.

Rencontré pour de vrai : un « app.js » corrigé, déployé, vérifié dans les
journaux — et toujours l'ancien dans le navigateur, qui affichait donc l'ancien
comportement. Pendant le test, où le code change plusieurs fois par jour, ça
transforme chaque correctif en « ça ne marche pas chez moi » impossible à
instruire à distance.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

CLIENT = TestClient(app)


@pytest.mark.parametrize("chemin", [
    "/", "/index.html", "/app.js", "/styles.css", "/polices.css",
    "/manifeste.json", "/agent.js",
])
def test_le_code_est_toujours_reverifie(chemin):
    """« no-cache » : le navigateur garde le fichier mais redemande s'il a
    changé. Un 304 vide, pas un téléchargement."""
    reponse = CLIENT.get(chemin)
    assert reponse.status_code == 200, chemin
    assert reponse.headers.get("Cache-Control") == "no-cache", chemin


def test_l_agent_de_service_surtout():
    """S'il périme, plus rien ne se met à jour : c'est lui qui décide comment
    tout le reste est servi."""
    assert CLIENT.get("/agent.js").headers.get("Cache-Control") == "no-cache"


def test_les_icones_sont_gardees_longtemps():
    """Elles ne changent pas. Les redemander à chaque démarrage, c'est payer un
    aller-retour pour rien sur une connexion de collège."""
    reponse = CLIENT.get("/icones/icone-192.png")
    if reponse.status_code == 404:
        pytest.skip("pas d'icône à cette taille")
    entete = reponse.headers.get("Cache-Control", "")
    assert "immutable" in entete
    assert "max-age=31536000" in entete


def test_l_api_n_est_jamais_gardee():
    """Un classeur ou un quota servis depuis le cache feraient réapparaître du
    travail effacé, ou rouvriraient une porte que le serveur a fermée."""
    reponse = CLIENT.get("/api/config")
    assert reponse.status_code == 200
    assert reponse.headers.get("Cache-Control") == "no-store"


def test_le_tableau_de_bord_non_plus():
    reponse = CLIENT.get("/admin/metriques?token=jeton-de-test")
    assert reponse.headers.get("Cache-Control") == "no-store"


def test_la_coque_du_serveur_et_celle_de_l_agent_disent_la_meme_chose():
    """Deux listes qui décrivent le même ensemble de fichiers finissent par
    diverger. Si l'une oublie un fichier que l'autre connaît, ce fichier est
    servi selon une règle que personne n'a choisie."""
    from pathlib import Path

    from app.main import duree_de_cache

    agent = (Path(__file__).resolve().parent.parent / "web" / "agent.js").read_text(encoding="utf-8")
    bloc = agent[agent.index("const COQUE"):agent.index("];", agent.index("const COQUE"))]
    dans_l_agent = {m.strip().strip("'\",") for m in bloc.split("[")[1].split(",")}
    dans_l_agent = {c for c in dans_l_agent if c.startswith("/")}
    assert dans_l_agent, "la coque de l'agent n'a pas été relue correctement"
    sans_regle = [c for c in sorted(dans_l_agent) if duree_de_cache(c) is None]
    assert not sans_regle, f"servis sans règle de cache : {sans_regle}"
