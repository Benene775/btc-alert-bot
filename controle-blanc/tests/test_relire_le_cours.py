"""Relire le cours de l'élève, et dire ce qui semble faux — sans le corriger.

Un cours est recopié à la main, en classe, vite, sous la dictée. Il arrive
qu'une ligne soit fausse, et c'est la pire chose qui puisse arriver à une
révision : l'élève apprend l'erreur par cœur et la ressort le jour du contrôle.
Personne ne relit son cahier entre le jour où il l'écrit et le jour du contrôle.

Mesuré avant d'y croire, sur une page fabriquée avec deux erreurs volontaires
et une ligne juste. Les deux erreurs trouvées, la ligne juste laissée
tranquille, zéro fausse alerte, et un contre-exemple pour expliquer :

    « Cette règle est fausse : 14 a pour chiffre des unités 4 mais n'est pas
      divisible par 4, alors que 12 l'est avec un chiffre des unités 2. »

Trois canaux à ne jamais confondre :

  photos[].remarque   ce qui ne va pas avec la PHOTO
  doutes              ce qu'on n'a pas su LIRE, et qu'on demande à l'élève
  a_verifier          ce qu'on a bien lu, mais qui paraît FAUX

Les mélanger, c'est apprendre à l'élève à tout ignorer.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")


def bloc(nom: str) -> str:
    debut = SCRIPT.index("function " + nom)
    return SCRIPT[debut:][: SCRIPT[debut:].index("\n}\n")]


def test_le_canal_existe_et_est_distinct_des_deux_autres():
    from app import prompts

    champs = prompts.SCHEMA_ANALYSE["properties"]
    assert "a_verifier" in champs and "doutes" in champs and "photos" in champs
    assert "a_verifier" in prompts.SCHEMA_ANALYSE["required"]
    item = champs["a_verifier"]["items"]
    assert set(item["required"]) == {"page", "ecrit", "probleme", "plutot"}


def test_la_consigne_interdit_de_corriger_en_silence():
    """Réécrire le cahier ferait réviser à l'élève une version que personne n'a
    enseignée — et il n'aurait aucun moyen de s'en apercevoir."""
    from app import prompts

    consigne = prompts.ANALYSE_SYSTEME
    assert "jamais ce que ça devrait être" in consigne
    assert "Tu n'as pas le dernier mot" in consigne
    # Le signalement doit rester rare, sinon il devient du bruit qu'on apprend
    # à ignorer — la même faute que sept doutes posés pour rien.
    assert "Vide dans l'immense majorité des cas." in consigne
    # Une hésitation n'est pas une accusation.
    assert "c'est un doute, pas un signalement" in consigne


def test_l_ecran_le_montre_avant_les_doutes():
    """Un mot mal lu, l'élève le rectifie en deux secondes. Une ligne fausse
    dans son cours, il l'apprend par cœur."""
    assert 'id="a-verifier"' in PAGE
    assert PAGE.index('id="a-verifier"') < PAGE.index('id="doutes"')
    assert "dessinerAVerifier()" in bloc("dessinerPerimetre")
    corps = bloc("dessinerPerimetre")
    assert corps.index("dessinerAVerifier()") < corps.index("dessinerDoutes()")


def test_la_ligne_fautive_est_barree_pas_remplacee():
    """On montre ce qui est écrit dans le cahier ; on ne le remplace pas."""
    assert ".verif-ecrit" in STYLE and "line-through" in STYLE
    corps = bloc("dessinerAVerifier")
    assert "textContent = v.ecrit" in corps, "la ligne du cahier n'est pas citée telle quelle"
    assert "innerHTML = ''" in corps and "innerHTML =" not in corps.replace("innerHTML = ''", ""), (
        "le texte du modèle doit passer par textContent, jamais par innerHTML"
    )


def test_ajouter_des_pages_n_efface_pas_un_signalement():
    corps = SCRIPT[SCRIPT.index("etat.aVerifier = (etat.aVerifier"):][:400]
    assert "concat(" in corps


def test_la_page_d_accueil_l_annonce_avec_un_exemple_de_maths():
    accueil = PAGE[PAGE.index('id="ecran-accueil"') : PAGE.index('id="ecran-connexion"')]
    assert "On relit ton cours, aussi" in accueil
    assert "225 = 9 × 45" in accueil, "l'exemple annoncé n'est pas là"
    assert "9 × 45 = 405" in accueil, "l'exemple ne montre pas pourquoi c'est faux"
    # Et la promesse ne doit pas dépasser ce que le produit fait.
    assert "On ne réécrit rien" in accueil


def test_les_deux_demonstrations_le_montrent():
    """Une page d'accueil qui promet et une démonstration qui ne montre rien,
    c'est la promesse qui perd."""
    for contenu in ("histoire.js", "espagnol.js"):
        source = (RACINE / "outils" / "demonstration" / contenu).read_text(encoding="utf-8")
        assert "const A_VERIFIER" in source, contenu
    faux = (RACINE / "outils" / "demonstration" / "faux-serveur.js").read_text(encoding="utf-8")
    assert "a_verifier: A_VERIFIER" in faux
    from app import demo
    assert demo.analyse(2)["a_verifier"], "la démonstration servie par le serveur n'en a pas"
