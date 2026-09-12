"""La fiche sur papier : deux A4 au plus, le recto-verso d'une feuille.

La contrainte vient du classeur de l'élève, pas d'une préférence : au-delà, une
fiche cesse d'être une fiche. Elle est vérifiable, et elle l'a été — trois
calibres passés en vrai PDF A4 par un navigateur, mesurés avec pypdf :

    fiche de démonstration (3 parties, 11 points) ....... 1 page
    6 parties × 6 points, phrases ordinaires ............ 2 pages
    6 parties × 6 points, phrases longues ............... 2 pages

Six parties de six points est le maximum que la consigne autorise au modèle
(FICHE_GENERALE_CONSIGNE) : c'est donc le pire cas réel, pas une hypothèse.

La mise en pages est faite PAR LE SCRIPT et non par le navigateur. C'est le
fruit d'un bogue signalé depuis un iPhone : en confiant les colonnes au moteur
(« column-count » plus les sauts automatiques), les lignes sortaient tranchées
d'une page à l'autre et débordaient à droite. On ne demande donc plus au
navigateur de fragmenter quoi que ce soit — seulement de sauter une page là où
on le lui dit. Les tests ci-dessous gardent les trois conditions qui font tenir
ce choix ; chacune a été violée au moins une fois, et chacune a coûté un PDF.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = (RACINE / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RACINE / "web" / "app.js").read_text(encoding="utf-8")
STYLE = (RACINE / "web" / "styles.css").read_text(encoding="utf-8")

IMPRESSION = STYLE[STYLE.index("@media print {"):]
ECRAN = STYLE[: STYLE.index("@media print {")]


def regle(feuille: str, selecteur: str) -> str:
    """Le corps d'une règle CSS, accolades exclues — pas le commentaire au-dessus."""
    debut = feuille.index(selecteur + " {") + len(selecteur) + 2
    return feuille[debut: feuille.index("}", debut)]


def fonction(nom: str) -> str:
    """Le corps d'une fonction du script, de sa signature à son accolade seule."""
    debut = SCRIPT.index("function " + nom + "(")
    return SCRIPT[debut: SCRIPT.index("\n}\n", debut)]


def sans_commentaires_css(feuille: str) -> str:
    """Une feuille de style sans ses commentaires : un test qui interdit un mot
    ne doit pas se déclencher sur la phrase qui explique pourquoi il l'est."""
    return re.sub(r"/\*.*?\*/", "", feuille, flags=re.S)


def sans_commentaires(code: str) -> str:
    """Le code seul. Sans ça, un test sur un mot interdit se déclenche sur la
    phrase qui explique pourquoi il l'est — c'est déjà arrivé deux fois."""
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    return re.sub(r"//.*", "", code)


def test_la_feuille_est_hors_de_l_application():
    """L'impression cache tout ce qui n'est pas elle, « main » compris. Posée
    dedans, elle disparaissait avec le reste : le PDF sortait blanc."""
    assert PAGE.index("</main>") < PAGE.index('id="fiche-papier"')
    assert "body > *:not(#fiche-papier) { display: none !important; }" in IMPRESSION


def test_elle_est_mesurable_a_l_ecran_sans_s_y_voir():
    """Elle ne peut pas être « display: none » : il faut qu'elle soit mise en
    page pour qu'on puisse mesurer ses blocs avant de les répartir. On la sort
    donc du champ au lieu de la masquer."""
    corps = regle(ECRAN, "#fiche-papier")
    assert "display: none" not in corps
    assert "position: absolute" in corps and "left: -99999px" in corps


def test_la_largeur_imprimee_est_celle_qui_a_ete_mesuree():
    """Le bogue le plus coûteux de cette feuille. « width: auto » à l'impression
    donnait à la feuille la largeur de la FENÊTRE (390 px sur un téléphone) au
    lieu des 188 mm auxquels on venait de mesurer : chaque colonne moitié trop
    étroite, chaque bloc 60 % trop haut, et le contenu débordait la page.
    188 mm est la boîte de contenu d'une A4 avec les marges ci-dessous."""
    assert "@page { size: A4; margin: 10mm 11mm; }" in IMPRESSION
    a_l_ecran = regle(ECRAN, "#fiche-papier")
    a_l_impression = regle(IMPRESSION, "#fiche-papier")
    assert "width: 188mm" in a_l_ecran
    assert "width: 188mm" in a_l_impression
    assert "width: auto" not in a_l_impression


def test_la_regle_se_mesure_dans_la_feuille_jamais_dans_le_corps():
    """Deuxième moitié du même bogue. À l'impression, la feuille est le seul
    enfant du corps qui reste affiché. Une règle en millimètres posée dans le
    corps y mesurait donc zéro : la colonne recevait une hauteur nulle, plus
    aucun bloc ne changeait jamais de colonne, et la fiche entière s'empilait
    sur une colonne de 3 673 pixels que l'imprimante découpait où elle
    pouvait — les lignes tranchées que le testeur a vues."""
    corps = fonction("mmEnPixels")
    assert "document.body.appendChild" not in corps
    assert "feuille.appendChild(regle)" in corps


def test_elle_est_batie_a_part_pas_deguisee_du_paquet():
    """Les cartes de l'écran coupent une partie en deux quand la liste est
    longue, répètent leur titre à chaque morceau, cachent la phrase à retenir
    derrière un « Tu te souviens ? » et finissent par une carte de bilan. Rien
    de tout ça ne veut dire quoi que ce soit sur du papier."""
    bloc = sans_commentaires(fonction("blocsDeLaFiche") + fonction("dessinerFichePapier"))
    assert "fiche.sections" in bloc, "la feuille doit repartir des données"
    assert "carte" not in bloc.replace("écarte", ""), "elle ne doit pas relire le paquet"
    for morceau in ("a_retenir", "definitions", "pieges"):
        assert morceau in bloc, f"« {morceau} » manque à la feuille"


def test_le_bouton_est_sur_l_ecran_de_la_fiche():
    fiche = PAGE[PAGE.index('id="ecran-fiche"'):]
    fiche = fiche[: fiche.index("</section>")]
    assert 'id="bouton-imprimer"' in fiche
    assert "$('bouton-imprimer').onclick" in SCRIPT
    assert "window.print()" in SCRIPT


def test_le_navigateur_ne_fragmente_rien():
    """Le seul saut de page du document est celui qu'on pose. Aucun bloc
    multi-colonnes : c'est ce que les moteurs font le plus mal, et c'est ce qui
    coupait les lignes en deux sur le téléphone du testeur."""
    assert "column-count" not in IMPRESSION and "column-fill" not in IMPRESSION
    assert ".papier-page { break-after: page; break-inside: avoid; }" in IMPRESSION
    assert ".papier-page:last-child { break-after: auto; }" in IMPRESSION
    # Les deux colonnes sont des boîtes réelles, remplies une à une.
    assert "display: flex" in regle(ECRAN, ".papier-colonnes")
    assert "colonnes[ici.colonne].appendChild(bloc)" in fonction("rangerEnPages")


def test_le_titre_rogne_le_budget_des_deux_colonnes():
    """Le titre coiffe la page entière. Ne le déduire que de la première colonne
    laissait la seconde croire à une page vierge et la faisait déborder."""
    corps = fonction("rangerEnPages")
    assert "hauteur - (pages.length ? 0 : hautDe(enTete))" in corps


def test_on_mesure_la_colonne_et_pas_la_somme_des_blocs():
    """Les cartes portent une marge basse que le rectangle d'un bloc ne compte
    pas. Sur six parties, cela faisait un centimètre et demi d'écart — de quoi
    déborder sans le voir."""
    corps = fonction("rangerEnPages")
    assert "hautDe(ici.colonnes[ici.colonne]) > ici.plafond" in corps


def test_la_derniere_page_est_equilibree():
    """Remplie gloutonnement, elle donnait une colonne pleine à ras bord et une
    colonne presque vide : une demi-feuille blanche que l'élève a pourtant
    imprimée."""
    corps = fonction("equilibrerLaDerniere")
    assert "Math.max(gauche, droite)" in corps
    assert "if (gauche > derniere.plafond) break;" in corps, \
        "équilibrer ne doit jamais faire déborder la page"
    assert "equilibrerLaDerniere(pages[pages.length - 1])" in fonction("rangerEnPages")


def test_le_pied_signe_le_bas_de_la_derniere_page():
    """Posé dans une colonne, il atterrissait au milieu de la feuille, sous un
    bloc court, avec la moitié de la page blanche en dessous."""
    corps = fonction("rangerEnPages")
    assert "pages[pages.length - 1].page.appendChild(pied)" in corps


def test_la_typographie_passe_avant_la_mesure():
    """Les espaces insécables posés devant « ; : ! ? » suppriment des points de
    césure : une ligne peut alors passer à la suivante. Soigner la feuille une
    fois rangée, c'était la faire grandir dans le dos de la mise en pages et
    déborder la colonne qu'on venait de calculer juste."""
    assert "blocs.forEach(soignerTypographie);" in fonction("blocsDeLaFiche")
    dessin = fonction("dessinerFichePapier")
    assert "soignerTypographie(enTete);" in dessin and "soignerTypographie(pied);" in dessin
    assert "soignerTypographie(feuille)" not in dessin, \
        "soigner après le rangement rouvre le bogue"


def test_le_corps_reste_lisible():
    """Tenir en deux pages ne sert à rien si personne ne les lit. On essaie la
    taille la plus confortable d'abord et on ne resserre que si la fiche
    déborde ; 9 pt est le plancher sous lequel un élève de troisième renonce."""
    tailles = re.search(r"corps:\s*\[([\d.,\s]+)\]", SCRIPT)
    assert tailles, "les tailles de corps ont disparu de PAPIER"
    essais = [float(t) for t in tailles.group(1).split(",")]
    assert essais == sorted(essais, reverse=True), "on doit essayer la plus grande d'abord"
    assert essais[0] >= 10, "la fiche confortable doit partir de 10 pt"
    assert essais[-1] >= 9, "le corps est descendu sous 9 pt"
    assert "if (pages <= PAPIER.pagesVoulues) break;" in fonction("dessinerFichePapier")


def test_aucune_transparence_dans_les_fonds_de_la_feuille():
    """Signalé depuis un iPhone : des bandes NOIRES par-dessus chaque phrase à
    retenir, sur l'aperçu PDF. Le surligneur était un dégradé dont la moitié
    haute valait « transparent » — c'est-à-dire rgba(0, 0, 0, 0), du noir que
    seul l'alpha rend invisible. Le moteur d'impression jette l'alpha : il ne
    restait que le noir, sur exactement les 58 % que la borne découpait.

    Les couleurs de TEXTE et de FILET en rgba, elles, sortent correctement — on
    l'a vu sur la même capture. Ce test ne garde donc que les fonds."""
    feuille = sans_commentaires_css(ECRAN[ECRAN.index("#fiche-papier {"):]
                                    + IMPRESSION)
    for fond in re.findall(r"background[\w-]*:[^;]+;", feuille):
        assert "transparent" not in fond, f"fond transparent sur le papier : {fond}"
        assert not re.search(r"rgba\([^)]*,\s*0?\.\d+\s*\)", fond), \
            f"fond semi-transparent sur le papier : {fond}"

    # Et le surligneur est toujours là, en aplat plein, sur le bas de la ligne.
    surligneur = regle(ECRAN, ".papier-retenir-texte")
    assert "linear-gradient(#ffdc8a, #ffdc8a)" in surligneur, "le surligneur a disparu"
    assert "background-size: 100% 42%" in surligneur
    assert "box-decoration-break: clone" in surligneur, \
        "sans ça, la bande ne suit pas les lignes d'une phrase qui se replie"


def test_elle_porte_les_couleurs_de_l_application():
    """Demandé explicitement : « est-ce que le pdf pourrait ressembler à la fiche
    au niveau des couleurs et de la police ». Les six teintes sont écrites en
    dur et non en « var(--tN) » : la feuille ne doit pas suivre le mode sombre,
    un élève qui imprime la nuit veut la même fiche que le jour. Le test garde
    donc la correspondance, qu'une retouche de la palette casserait en
    silence."""
    racine = regle(ECRAN, ":root")
    palette = [re.search(rf"--t{n}:\s*(#[0-9a-f]{{6}})", racine).group(1) for n in range(6)]

    feuille = ECRAN[ECRAN.index(".papier-partie {"): ECRAN.index(".papier-partie-titre")]
    assert palette[0] in feuille, "la première teinte de la feuille a quitté la palette"
    for n in range(1, 6):
        attendu = regle(feuille, f'.papier-partie[data-teinte="{n}"]')
        assert palette[n] in attendu, f"la teinte {n} de la feuille a quitté la palette"

    # Sans ça, les navigateurs suppriment les fonds : la fiche sortirait grise.
    assert "print-color-adjust: exact" in IMPRESSION
    # Les trois familles de l'application, jamais une police du système seule.
    for police in ("var(--titre)", "var(--texte)", "var(--mono)"):
        assert police in feuille or police in ECRAN[ECRAN.index("#fiche-papier {"):], \
            f"{police} manque à la feuille"


def test_l_impression_est_comptee():
    """Savoir combien d'élèves impriment dit si la feuille sert."""
    from app import store
    assert "impression" in store.TYPES_EVENEMENTS
    assert "tracer('impression'" in SCRIPT
