"""L'outil de diagnostic doit marcher le jour où on en a besoin.

Il ne sert qu'en panne — donc il n'est jamais lancé, donc il pourrit sans
bruit. Une requête qui ne passe plus, et on l'apprend le soir où le tableau de
bord ne bouge pas et où un élève attend.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import store

RACINE = Path(__file__).resolve().parent.parent


def _outil():
    chemin = RACINE / "outils" / "etat_base.py"
    spec = importlib.util.spec_from_file_location("etat_base", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sortie(module) -> str:
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        module.le_mode()
        module.la_base()
        module.l_activite()
        module.les_eleves()
    return tampon.getvalue()


def test_il_tourne_sur_une_base_vide(client):
    """Une base neuve est le cas où on le lance le plus tôt — et celui où une
    requête sur une table vide casse le plus facilement."""
    with store.curseur() as cur:
        cur.execute("DELETE FROM usages")
    texte = _sortie(_outil())
    assert "LE MODE" in texte
    assert "Aucun appel enregistré" in texte


def test_il_nomme_le_mode_demonstration(client):
    """C'est la panne la plus grave et la moins visible : l'élève reçoit une
    fiche inventée, et rien ne le dit."""
    texte = _sortie(_outil())
    assert "Mode démonstration" in texte
    assert "CONTENUS FACTICES" in texte, "le mode démonstration doit crier"


def test_il_compte_les_seances_sans_compte(client, session):
    """« Ce que coûte chaque élève » ne lit que les séances rattachées à un
    compte : une séance orpheline dépense dans le total et dans aucune ligne.

    Le nombre attendu se relit dans la base plutôt que de s'écrire en dur : la
    base est partagée par la suite, et un test voisin qui ouvre une séance
    ferait échouer celui-ci sans rien dire du vrai sujet.
    """
    with store.curseur() as cur:
        cur.execute("UPDATE sessions SET compte_id = NULL")
        combien = cur.execute(
            "SELECT COUNT(*) AS n FROM sessions WHERE compte_id IS NULL").fetchone()["n"]
    assert combien >= 1, "le test ne prouverait rien sans séance orpheline"

    texte = _sortie(_outil())
    assert f"Séances sans compte : {combien}" in texte
    assert "AUCUNE" in texte, "le cas doit être expliqué, pas seulement compté"


def test_il_ne_montre_aucune_adresse_ni_aucune_cle(client, session):
    """Il s'affiche dans un terminal partagé et se copie dans une conversation."""
    texte = _sortie(_outil())
    assert "@" not in texte
    with store.curseur() as cur:
        adresse = cur.execute("SELECT email FROM comptes LIMIT 1").fetchone()
    if adresse:
        assert adresse["email"] not in texte


def test_il_dit_quand_la_base_a_vraiment_ete_ecrite(tmp_path):
    """La base tourne en WAL : les écritures atterrissent dans un fichier
    « -wal » à côté, et la date du fichier principal ne bouge qu'au point de
    reprise. Lue seule, elle annonçait « modifié il y a cinq jours » sur une
    base écrite la veille — un faux indice, servi au moment précis où l'on
    cherche une panne."""
    base = tmp_path / "repere.sqlite3"
    base.write_bytes(b"x" * 2048)
    journal = tmp_path / "repere.sqlite3-wal"
    journal.write_bytes(b"y" * 1024)

    # Le fichier principal date d'une semaine, le journal d'il y a une minute.
    vieux = time.time() - 7 * 86400
    os.utime(base, (vieux, vieux))

    quand, taille = _outil().derniere_ecriture(base)
    ecart = datetime.now(timezone.utc) - datetime.fromisoformat(quand)
    assert ecart < timedelta(minutes=5), f"la date du journal est ignorée : {quand}"
    assert taille == 3072, "le journal doit compter dans la taille"


def test_une_base_absente_ne_fait_pas_tomber_l_outil(tmp_path):
    """C'est un cas réel : mauvais CB_DB_PATH, disque non monté. L'outil doit le
    dire, pas s'écrouler dessus."""
    quand, taille = _outil().derniere_ecriture(tmp_path / "nulle-part.sqlite3")
    assert taille == 0
    assert quand


def test_il_nomme_ceux_qui_ne_peuvent_pas_revenir(client):
    """Sans serveur de courrier, un élève qui oublie son mot de passe est
    dehors pour de bon : son code part dans les journaux de la plateforme. Il ne
    signale pas une panne, il arrête — et rien dans les mesures ne le dit."""
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        _outil().les_portes_fermees()
    texte = tampon.getvalue()
    assert "Serveur de courrier configuré" in texte
    assert "NE PEUT PAS REVENIR" in texte, "l'absence de SMTP doit crier"
