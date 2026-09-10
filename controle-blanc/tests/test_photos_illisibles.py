"""Quand aucune page ne passe : dire ce qui a bloqué, pas « recommence ».

Mesuré sur deux vraies photos ratées — un cahier photographié de loin, de
travers, dans l'ombre. Le modèle a refusé les deux en seize secondes et deux
centimes, avec un conseil précis par page :

    « Ta photo est trop sombre et floue pour que je puisse lire le texte avec
      certitude : reprends-la avec plus de lumière, en évitant que ton ombre ou
      celle de l'appareil ne couvre la page, et stabilise bien l'appareil. »

Et le produit jetait ce conseil. « etat.remarquesPhotos » n'était rendu que sur
l'écran du périmètre, qu'on n'atteint jamais quand rien n'a été lu : l'élève
recevait un message générique de huit secondes qui lui disait de se rapprocher,
alors que le problème était son ombre. C'est le moment précis où il décide de
recommencer ou de laisser tomber.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")

ECRAN_PHOTOS = PAGE[PAGE.index('id="ecran-photos"') : PAGE.index('id="ecran-perimetre"')]


def bloc(nom: str) -> str:
    debut = SCRIPT.index("function " + nom)
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_l_ecran_des_photos_a_de_quoi_afficher_le_refus():
    """Sur l'écran du périmètre, la boîte existait déjà. Ici, non — et c'est le
    seul écran que voit l'élève quand rien n'a été lu."""
    assert 'id="alerte-relecture"' in ECRAN_PHOTOS


def test_le_conseil_du_modele_est_affiche_quand_rien_n_a_ete_lu():
    corps = SCRIPT[SCRIPT.index("const nouveaux = resultat.chapitres"):][:1400]
    assert "dessinerRemarquesPhotos('alerte-relecture'" in corps, (
        "le conseil page par page est encore jeté quand aucune page ne passe"
    )
    # Le message générique reste, mais en filet : il ne sert que si le modèle
    # n'a rien dit de précis.
    avis = corps.index("dessinerRemarquesPhotos('alerte-relecture'")
    filet = corps.index("Aucune page n’était lisible")
    assert avis < filet, "le message générique passe avant le conseil précis"
    assert "if (!dit)" in corps, "le message générique n'est pas conditionnel"


def test_les_deux_ecrans_partagent_le_meme_rendu():
    """Deux copies auraient divergé à la première retouche — et c'est déjà ce
    qui s'était passé : l'écran du périmètre affichait, l'autre pas."""
    assert SCRIPT.count("function dessinerRemarquesPhotos") == 1
    assert "dessinerRemarquesPhotos('alerte-photos'" in bloc("dessinerPerimetre")


def test_la_remarque_du_modele_est_echappee():
    """Elle est écrite par le modèle à partir d'une photo fournie par l'élève :
    elle ne s'exécute pas dans le navigateur."""
    corps = bloc("dessinerRemarquesPhotos")
    assert "innerHTML" in corps
    assert corps.count("echapper(") == 2, (
        "l'en-tête et la remarque doivent être échappés tous les deux"
    )


def test_une_reprise_qui_marche_efface_l_avis():
    corps = SCRIPT[SCRIPT.index("const nouveaux = resultat.chapitres"):][:1400]
    assert "$('alerte-relecture').hidden = true" in corps
