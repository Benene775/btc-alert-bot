"""« Contrôle d'espagnol demain, pense à réviser. »

La seule notification que Repère envoie. Elle lit l'agenda que l'élève a rempli
lui-même et qui monte déjà au serveur : rien n'est deviné, et rien n'est
fabriqué pour faire revenir quelqu'un — un produit qui écrit à des collégiens
le soir doit pouvoir dire exactement pourquoi, à chaque fois.

Ce qui doit tenir :

1. Le français. « Contrôle de Espagnol » n'est pas une phrase, et une
   notification se lit en entier ou pas du tout.
2. La veille, une fois, et jamais deux — même si le serveur redémarre.
3. Jamais la nuit : l'heure est bornée, parce que ce sont des mineurs.
4. Sans clés VAPID, la fonction n'existe pas : pas de route, pas de réglage,
   pas de tâche de fond. Un dépôt public ne doit pas porter de secret, et un
   déploiement qui n'en veut pas ne doit rien avoir à dire.
5. Le message arrive vraiment, et il arrive lisible. Le reste de ce fichier
   peut passer sur du code qui n'envoie rien : le dernier test monte donc un
   faux service de push, capture l'envoi, et le DÉCHIFFRE.
"""

from __future__ import annotations

import base64
import json
import os
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app import config, rappels, store
from tests.conftest import inscrire


# --- Ce qu'on dit, et comment on l'écrit ------------------------------------

def test_toutes_les_matieres_ont_un_nom_de_phrase():
    """Une matière ajoutée sans nom court donnerait « Contrôle  demain »."""
    from app import formats

    for m in formats.liste_matieres():
        assert m["cle"] in rappels.COURT, f"{m['cle']} n'a pas de nom court"


@pytest.mark.parametrize("matieres, attendu", [
    (["espagnol"], "Contrôle d'espagnol demain"),
    (["anglais"], "Contrôle d'anglais demain"),
    (["histoire-geographie"], "Contrôle d'histoire-géo demain"),
    (["mathematiques"], "Contrôle de maths demain"),
    # Un sigle commence par une voyelle à l'oreille et ne s'élide pas à l'écrit.
    (["svt"], "Contrôle de SVT demain"),
    (["ses"], "Contrôle de SES demain"),
    # « Autre matière » n'a pas de nom qu'on puisse mettre dans une phrase.
    (["autre"], "Contrôle demain"),
    (["espagnol", "mathematiques"], "Deux contrôles demain : espagnol et maths"),
    (["espagnol", "mathematiques", "svt"], "Trois contrôles demain"),
])
def test_le_titre_est_du_francais(matieres, attendu):
    assert rappels.texte_du_rappel(matieres)["titre"] == attendu


def test_au_dela_de_deux_le_detail_passe_dans_le_corps():
    """Le titre d'une notification est coupé vers quarante signes."""
    texte = rappels.texte_du_rappel(["espagnol", "mathematiques", "svt"])
    assert "espagnol, maths et SVT" in texte["corps"]


def test_le_message_n_accuse_personne():
    """Elle arrive chez quelqu'un qui n'a peut-être rien révisé. Lui rappeler ce
    qu'il sait déjà ne l'aide pas, et le produit ne compte pas les absences."""
    texte = rappels.texte_du_rappel(["espagnol"])
    entier = (texte["titre"] + " " + texte["corps"]).lower()
    for reproche in ("tu n'as pas", "tu n’as pas", "toujours pas", "aucune", "retard"):
        assert reproche not in entier


# --- L'agenda, lu avec méfiance ---------------------------------------------

def test_l_agenda_est_lu_sans_faire_confiance():
    """C'est un blob JSON écrit par le navigateur. Une entrée abîmée ne doit pas
    faire tomber la tournée des autres comptes."""
    assert rappels.rendez_vous_le("pas du json", "2026-01-01") == []
    assert rappels.rendez_vous_le('{"pas": "une liste"}', "2026-01-01") == []
    assert rappels.rendez_vous_le('[1, 2, "trois"]', "2026-01-01") == []
    bon = '[{"date": "2026-01-01", "matiere": "espagnol", "note": "chapitre 3"}]'
    assert rappels.rendez_vous_le(bon, "2026-01-01") == [
        {"matiere": "espagnol", "note": "chapitre 3"}
    ]
    assert rappels.rendez_vous_le(bon, "2026-01-02") == []


def test_on_annonce_la_veille():
    assert rappels.jour_vise(date(2026, 3, 10)) == "2026-03-11"


# --- L'heure, parce que ce sont des mineurs ---------------------------------

def test_l_heure_ne_peut_pas_tomber_la_nuit(monkeypatch):
    """Un réglage fautif ne doit pas pouvoir réveiller un collégien. La borne
    est dans config, au moment de la lecture, et pas dans un commentaire."""
    import importlib

    for demande, attendu in (("3", 7), ("23", 21), ("18", 18), ("pas un nombre", 18)):
        monkeypatch.setenv("CB_RAPPEL_HEURE", demande)
        recharge = importlib.reload(config)
        assert recharge.RAPPEL_HEURE == attendu
    monkeypatch.delenv("CB_RAPPEL_HEURE", raising=False)
    importlib.reload(config)


# --- Sans clés, rien n'existe -----------------------------------------------

def test_sans_cles_la_fonction_est_absente(client):
    """Le dépôt est public : la clé privée vit dans l'environnement, et un
    déploiement qui n'en pose pas ne doit voir aucune trace de tout ça."""
    assert not config.RAPPELS_ACTIFS, "les tests tournent sans clés, c'est voulu"
    assert client.get("/api/config").json()["vapid_publique"] == ""
    refus = client.post("/api/rappels/activer", json={
        "endpoint": "https://push.exemple.test/abc123",
        "p256dh": "x" * 40, "auth": "y" * 20})
    assert refus.status_code == 503


def test_la_cle_privee_n_est_nulle_part_dans_le_depot():
    """La faute qui ne se rattrape pas : un secret poussé sur un dépôt public.

    On cherche une VALEUR, pas le nom de la variable — ce fichier-ci le contient
    forcément, et un test qui s'attrape lui-même n'attrape plus rien d'autre.
    Une clé privée VAPID fait 43 signes de base64url.
    """
    import re
    from pathlib import Path

    racine = Path(__file__).resolve().parent.parent
    # Assemblé à l'exécution : écrit en un seul morceau, le motif se trouverait
    # lui-même à la première relecture du dossier des tests.
    motif = re.compile("CB_VAPID_CLE_PRIV" + r"EE\s*=\s*[A-Za-z0-9_-]{20,}")
    for fichier in racine.rglob("*"):
        if fichier.is_dir() or fichier.suffix not in {".py", ".js", ".md", ".json",
                                                      ".txt", ".html", ".css", ".example"}:
            continue
        if "__pycache__" in str(fichier) or "/donnees/" in str(fichier):
            continue
        texte = fichier.read_text(encoding="utf-8", errors="ignore")
        assert not motif.search(texte), f"une clé privée semble écrite dans {fichier}"


# --- Une fois, et pas deux --------------------------------------------------

def test_un_rappel_ne_part_qu_une_fois(client):
    """Le serveur redémarre ; la tournée repasse. Sans trace, l'élève reçoit
    deux fois la même chose, ce qui est la meilleure façon de se faire couper."""
    email = inscrire(client)
    compte_id = client.get("/api/auth/moi").json()["compte"]
    demain = "2026-05-12"
    client.put("/api/agenda", json={
        "contenu": json.dumps([{"date": demain, "matiere": "espagnol", "note": ""}]),
        "maj_le": "2026-05-11T10:00:00Z"})
    store.abonner_push(compte_id, "https://push.exemple.test/" + email,
                       "p" * 40, "a" * 20)

    premier = rappels.a_prevenir(demain)
    assert [c["matieres"] for c in premier] == [["espagnol"]]

    store.noter_rappel(compte_id, demain, "espagnol")
    assert rappels.a_prevenir(demain) == [], "le même rappel repart une seconde fois"


def test_on_ne_lit_pas_l_agenda_de_qui_n_a_pas_demande(client):
    """La tournée part des abonnés, pas des agendas : un élève qui n'a rien
    activé ne doit même pas être lu."""
    inscrire(client)
    client.put("/api/agenda", json={
        "contenu": json.dumps([{"date": "2026-05-12", "matiere": "svt", "note": ""}]),
        "maj_le": "2026-05-11T10:00:00Z"})
    assert rappels.a_prevenir("2026-05-12") == []


# --- Et pour de vrai : un envoi capturé, déchiffré, relu ---------------------

class _FauxPush(BaseHTTPRequestHandler):
    recu: list = []

    def do_POST(self):  # noqa: N802
        taille = int(self.headers.get("Content-Length", "0"))
        _FauxPush.recu.append({
            "chemin": self.path,
            "corps": self.rfile.read(taille),
            # Les noms d'en-tête HTTP sont insensibles à la casse, et la
            # bibliothèque d'envoi les écrit en minuscules : on compare
            # sur une forme normalisée plutôt que sur celle qu'on espère.
            "entetes": {k.lower(): v for k, v in self.headers.items()},
        })
        self.send_response(201)
        self.end_headers()

    def log_message(self, *_a):  # silence
        pass


def test_le_message_part_signe_chiffre_et_lisible(client, monkeypatch):
    """Le seul test qui prouve que ça marche.

    Tout le reste passerait sur un code qui n'envoie rien. Ici on monte un faux
    service de push, on fabrique un abonnement comme le ferait un navigateur, on
    lance la tournée, puis on DÉCHIFFRE ce qui est arrivé. Si ce test passe, un
    téléphone affiche la phrase.
    """
    pytest.importorskip("pywebpush")
    http_ece = pytest.importorskip("http_ece")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    import asyncio

    # Les clés du serveur (VAPID), comme « python -m outils.cles_vapid ».
    from outils.cles_vapid import fabriquer
    publique, privee = fabriquer()
    monkeypatch.setattr(config, "VAPID_CLE_PUBLIQUE", publique)
    monkeypatch.setattr(config, "VAPID_CLE_PRIVEE", privee)
    monkeypatch.setattr(config, "VAPID_CONTACT", "mailto:essai@exemple.test")

    # Les clés du navigateur, comme « pushManager.subscribe ».
    navigateur = ec.generate_private_key(ec.SECP256R1())
    p256dh = base64.urlsafe_b64encode(navigateur.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )).rstrip(b"=").decode()
    secret = os.urandom(16)
    auth = base64.urlsafe_b64encode(secret).rstrip(b"=").decode()

    _FauxPush.recu.clear()
    serveur = HTTPServer(("127.0.0.1", 0), _FauxPush)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    port = serveur.server_address[1]

    try:
        inscrire(client)
        compte_id = client.get("/api/auth/moi").json()["compte"]
        demain = "2026-05-12"
        client.put("/api/agenda", json={
            "contenu": json.dumps([{"date": demain, "matiere": "espagnol", "note": ""}]),
            "maj_le": "2026-05-11T10:00:00Z"})
        store.abonner_push(compte_id, f"http://127.0.0.1:{port}/envoi", p256dh, auth)

        bilan = asyncio.run(rappels.tournee(demain))
    finally:
        serveur.shutdown()

    assert bilan == {"envoyes": 1, "morts": 0, "rates": 0}, bilan
    assert len(_FauxPush.recu) == 1
    envoi = _FauxPush.recu[0]

    # Signé (VAPID) : sans cet en-tête, Apple et Google refusent l'envoi.
    assert "authorization" in envoi["entetes"]
    assert envoi["entetes"].get("content-encoding") == "aes128gcm"

    # Chiffré pour CE navigateur, et déchiffrable par lui seul.
    clair = http_ece.decrypt(envoi["corps"], private_key=navigateur,
                             auth_secret=secret, version="aes128gcm")
    charge = json.loads(clair)
    assert charge["titre"] == "Contrôle d'espagnol demain"
    assert charge["corps"] == "Pense à réviser — tu as encore ce soir."
    assert charge["jour"] == demain

    # Et la tournée a noté son passage : elle ne renverra rien demain matin.
    assert rappels.a_prevenir(demain) == []


# --- L'outil de vérification, qui doit désigner le BON coupable --------------

@pytest.mark.parametrize("contact, cle_juste, attendu", [
    # Le cas rencontré en configurant le service : un contact auquel il manque
    # « https:// ». py_vapid refuse un « sub » mal formé avec la même exception
    # qu'une clé illisible — l'outil accusait donc une clé parfaitement bonne,
    # et envoyait régénérer une paire qui n'avait rien. Un diagnostic qui
    # désigne le mauvais coupable coûte plus cher que pas de diagnostic.
    ("repere.example.test", True, ["CB_VAPID_CONTACT"]),
    ("https://repere.example.test", True, []),
    ("mailto:contact@example.test", True, []),
    # Et une clé vraiment abîmée doit rester détectée, elle.
    ("https://repere.example.test", False, ["CB_VAPID_CLE_PRIVEE"]),
])
def test_le_verificateur_ne_se_trompe_pas_de_coupable(monkeypatch, contact, cle_juste,
                                                      attendu):
    pytest.importorskip("py_vapid")
    from outils.cles_vapid import fabriquer
    from outils.verifier_rappels import verifier

    publique, privee = fabriquer()
    monkeypatch.setattr(config, "VAPID_CLE_PUBLIQUE", publique)
    monkeypatch.setattr(config, "VAPID_CLE_PRIVEE", privee if cle_juste else privee[:20])
    monkeypatch.setattr(config, "VAPID_CONTACT", contact)

    fautes = verifier()
    assert len(fautes) == len(attendu), fautes
    for variable, faute in zip(attendu, fautes):
        assert variable in faute, faute
    # Et quand c'est le contact, l'outil montre la valeur lue et la correction :
    # « il lui manque https:// » se répare sans rien comprendre au reste.
    if attendu == ["CB_VAPID_CONTACT"]:
        assert contact in fautes[0] and "https://" + contact in fautes[0]


def test_le_verificateur_n_affiche_aucun_secret(monkeypatch):
    """Il tourne dans un shell dont on envoie parfois des captures."""
    pytest.importorskip("py_vapid")
    from outils.cles_vapid import fabriquer
    from outils.verifier_rappels import verifier

    publique, privee = fabriquer()
    monkeypatch.setattr(config, "VAPID_CLE_PUBLIQUE", publique)
    monkeypatch.setattr(config, "VAPID_CLE_PRIVEE", privee[:20])  # abîmée : il va se plaindre
    monkeypatch.setattr(config, "VAPID_CONTACT", "https://repere.example.test")

    tout = " ".join(verifier())
    assert privee[:20] not in tout, "la clé privée se retrouve dans un message d'erreur"


# --- L'invitation, et ce qu'elle devient une fois acceptée ------------------

def _script() -> str:
    from pathlib import Path

    racine = Path(__file__).resolve().parent.parent
    return (racine / "web" / "app.js").read_text(encoding="utf-8")


def _bloc(nom: str) -> str:
    import re

    nu = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", _script(), flags=re.S))
    debut = nu.index("function " + nom + "(")
    return nu[debut : nu.index("\n}\n", debut)]


def test_l_invitation_disparait_une_fois_les_rappels_actifs():
    """« Ça sert à rien de le garder. » Une carte qui ne fait que confirmer ce
    qu'on sait déjà se lit à chaque ouverture de l'agenda et ne dit jamais rien
    de neuf — or l'agenda s'ouvre pour noter un contrôle, pas pour relire ses
    réglages."""
    corps = _bloc("dessinerRappels")
    assert "bloc.hidden = pose;" in corps
    assert "if (pose) return;" in corps


def test_mais_on_peut_encore_les_couper():
    """Retirer l'invitation ne doit pas enfermer l'élève : sans interrupteur,
    couper les rappels demanderait de passer par les réglages du téléphone, que
    l'application ne contrôle pas et où l'abonnement resterait vivant."""
    from pathlib import Path

    racine = Path(__file__).resolve().parent.parent
    page = (racine / "web" / "index.html").read_text(encoding="utf-8")
    # Au pied du compte, là où l'on cherche à couper quelque chose.
    pied = page[page.index('class="pied-compte"') : page.index("</section>",
                                                              page.index('class="pied-compte"'))]
    assert 'id="bouton-stopper-rappels"' in pied
    assert 'id="bouton-sortir"' in pied, "le repère de l'endroit a changé"
    corps = _bloc("dessinerRappels")
    assert "arret.hidden = !pose;" in corps
    assert "function arreterLesRappels" in _script()
    # Et il coupe vraiment des deux côtés : serveur et navigateur.
    arret = _bloc("arreterLesRappels")
    assert "/api/rappels/arreter" in arret and "deja.unsubscribe()" in arret


def test_l_etat_est_redessine_avec_la_page_perso():
    """Le pied du compte vit sur la page perso, pas dans l'agenda : sans ce
    dessin-là, l'interrupteur n'apparaîtrait qu'après avoir ouvert l'agenda."""
    assert "dessinerRappels();" in _bloc("dessinerEspace")
