"""Le carré « un nouveau cours » mène à l'appareil photo, pas à un formulaire.

Il ouvrait l'écran de contexte : « C'est quoi, ce contrôle ? », la classe, la
matière, la date, et un bouton « Continuer ». Les trois champs arrivaient DÉJÀ
REMPLIS — la classe vient du compte, la matière et la date ont leur valeur par
défaut. C'était donc une porte à pousser entre « je veux photographier mon
cours » et l'appareil photo, qui ne demandait rien que le produit ne sache
déjà. Signalé en usage réel, capture à l'appui.

Le raccourci a un prix, et c'est lui que ce fichier surveille : la matière
décide du CLASSEMENT du cours et du FORMAT du contrôle blanc. Sautée sans rien
dire, elle rangerait un cours de maths sous « Histoire-Géographie » sans que
personne ne le voie. Elle est donc écrite là où l'élève agit, et s'y change.

Ce qui doit tenir :

1. Tous les chemins vers l'appareil photo y arrivent directement.
2. Le contexte part quand même au serveur : le raccourci ne perd rien.
3. Ce qui est enregistré est visible sur l'écran des photos, avant d'appuyer.
4. Et ça se change d'un doigt — sinon la ligne n'est qu'un reproche.
5. Les étapes se renumérotent : photographier est la première, sur quatre.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

CODE_NU = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", SCRIPT, flags=re.S))
PHOTOS = PAGE[PAGE.index('id="ecran-photos"') : PAGE.index('id="ecran-perimetre"')]


def bloc(nom: str) -> str:
    debut = CODE_NU.index("function " + nom + "(")
    return CODE_NU[debut : CODE_NU.index("\n}\n", debut)]


def test_ouvrir_un_nouveau_cours_ouvre_l_appareil_photo():
    """Le carré de la page perso appelle demarrerSession, qui ne doit plus
    s'arrêter en route."""
    assert "$('porte-photo').onclick = () => demarrerSession();" in SCRIPT
    corps = bloc("demarrerSession")
    assert "return validerContexte();" in corps
    assert "montrer('ecran-contexte')" not in corps


def test_le_contexte_part_quand_meme_au_serveur():
    """Aller plus vite ne veut pas dire en dire moins : la classe calibre la
    fiche et le contrôle, la matière donne le format, la date rythme l'agenda.
    validerContexte reste le seul passage, c'est ce qui garantit qu'on n'a rien
    perdu en supprimant l'écran."""
    corps = bloc("validerContexte")
    for champ in ("champ-niveau", "champ-matiere", "champ-date"):
        assert champ in corps
    assert "/api/session/contexte" in corps
    assert "montrer('ecran-photos')" in corps


def test_ce_qui_est_enregistre_se_lit_avant_d_appuyer():
    """Une matière invisible est une matière fausse un jour sur cinq."""
    assert 'id="resume-contexte"' in PHOTOS
    # Au-dessus de la zone qui ajoute : on vérifie avant de photographier, pas après.
    assert PHOTOS.index('id="resume-contexte"') < PHOTOS.index('id="zone-photos"')
    corps = bloc("dessinerResumeContexte")
    assert "etat.niveau" in corps and "etat.matiere" in corps and "etat.dateControle" in corps
    # Repeinte à chaque arrivée sur l'écran : la matière a pu changer entre-temps.
    entree = CODE_NU[CODE_NU.index("if (id === 'ecran-photos') {"):][:220]
    assert "dessinerResumeContexte();" in entree


def test_elle_se_change_d_un_doigt():
    """Sinon ce n'est pas un réglage, c'est un constat."""
    assert "$('resume-contexte').onclick = () => montrer('ecran-contexte');" in SCRIPT
    assert "<button" in PHOTOS[PHOTOS.index('id="resume-contexte"') - 120:
                               PHOTOS.index('id="resume-contexte"')]
    assert "contexte-changer" in PHOTOS
    # La matière se lit au-dessus du reste : c'est elle qu'on vient corriger.
    assert PHOTOS.index('id="contexte-matiere"') < PHOTOS.index('id="contexte-detail"')
    # Visible : un gris de note se fait ignorer, et c'est le classement qui trinque.
    assert re.search(r"\.contexte-changer \{[^}]*color: var\(--accent\)", STYLE, re.S)


def test_les_etapes_sont_renumerotees():
    """« Étape 2 sur 5 » sur le premier écran du parcours se lit comme un pas
    manqué. Il y en a trois depuis que le carrefour a disparu — la fiche vient
    avec le cours au lieu de se choisir — et photographier est la première."""
    assert "Étape 1 sur 3" in PHOTOS
    for reste in ("Étape 2 sur 3", "Étape 3 sur 3"):
        assert reste in PAGE, reste
    # « Question 1 sur 5 » compte les questions d'un contrôle, pas les étapes.
    assert not re.search(r"Étape \d+ sur [45]", PAGE), "une étape annonce encore l'ancien parcours"
    # L'écran de contexte n'est plus une marche : c'est un réglage qu'on rouvre.
    contexte = PAGE[PAGE.index('id="ecran-contexte"') : PAGE.index('id="ecran-photos"')]
    assert "Étape" not in contexte
