"""La palette : une seule identité, et elle doit rester lisible.

L'application entière porte désormais le papier chaud de la fiche. Deux choses
peuvent casser sans que rien ne plante : un jeton qu'on retire mais qui reste
utilisé quelque part, et un couple couleur/fond qui descend sous le seuil de
lisibilité. Les deux se vérifient ici, pas à l'oeil.
"""

from __future__ import annotations

import re
from pathlib import Path

STYLE = (Path(__file__).resolve().parent.parent / "web" / "styles.css").read_text(encoding="utf-8")


def _jetons(bloc: str) -> dict[str, str]:
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", bloc))


def _bloc(entete: str) -> str:
    debut = STYLE.index(entete) + len(entete)
    return STYLE[debut : STYLE.index("}", debut)]


CLAIR = _jetons(_bloc(":root {"))
SOMBRE = _jetons(_bloc(':root[data-theme="dark"] {'))
# Le produit sert DEUX jeux de couleurs de matières : le lavis sobre, par
# défaut, et le pastel, que l'élève peut choisir. Les deux sont livrés, donc les
# deux doivent tenir le contraste — un jeu qu'on ne teste pas est un jeu qu'on
# n'a pas vérifié, et c'est celui que l'élève aura choisi.
PASTEL_CLAIR = dict(CLAIR, **_jetons(_bloc(':root[data-teintes="pastel"] {')))
PASTEL_SOMBRE = dict(SOMBRE, **_jetons(_bloc(':root[data-theme="dark"][data-teintes="pastel"] {')))


def _luminance(hexa: str) -> float:
    hexa = hexa.strip().lstrip("#")
    canaux = [int(hexa[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lineaire = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
    return 0.2126 * lineaire[0] + 0.7152 * lineaire[1] + 0.0722 * lineaire[2]


def _contraste(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# Les couples qui portent du texte. Le bouton principal en fait partie : c'est
# lui qui a révélé le problème — du blanc sur l'ambre clair du mode sombre
# tombait à 2,2:1, illisible, et personne ne l'aurait vu sur une capture claire.
COUPLES = [
    ("--encre", "--papier"),
    ("--encre", "--carte"),
    ("--encre-douce", "--papier"),
    ("--accent", "--papier"),
    ("--sur-accent", "--accent"),
    ("--stylo-eleve", "--papier"),
    ("--rouge", "--papier"),
    ("--acquis", "--papier"),
    ("--partiel", "--papier"),
    ("--encre", "--t0"),
    ("--encre", "--t1"),
    ("--encre", "--t2"),
    ("--encre", "--t3"),
    ("--encre", "--t4"),
    ("--encre", "--t5"),
    ("--encre", "--stylo-eleve-doux"),
    # Une matière est désormais une ENCRE sur son lavis, pas un aplat pastel :
    # c'est ce couple-là qui porte le code « H-G », « MATH », et lui seul dit
    # de quelle matière il s'agit.
    ("--m0", "--t0"),
    ("--m1", "--t1"),
    ("--m2", "--t2"),
    ("--m3", "--t3"),
    ("--m4", "--t4"),
    ("--m5", "--t5"),
]


def test_tout_ce_qui_porte_du_texte_reste_lisible():
    faibles = []
    for nom, jetons in (("clair", CLAIR), ("sombre", SOMBRE),
                        ("pastel clair", PASTEL_CLAIR), ("pastel sombre", PASTEL_SOMBRE)):
        for devant, derriere in COUPLES:
            rapport = _contraste(jetons[devant], jetons[derriere])
            if rapport < 4.5:
                faibles.append(f"{nom} : {devant} sur {derriere} = {rapport:.2f}")
    assert not faibles, "contraste insuffisant — " + " ; ".join(faibles)


def _est_couleur(valeur: str) -> bool:
    return valeur.strip().startswith(("#", "rgb", "hsl", "color-mix"))


def test_les_deux_themes_definissent_les_memes_couleurs():
    """Une couleur définie en clair mais oubliée en sombre disparaît sans erreur.

    Le tri se fait sur la valeur, pas sur une liste de noms à tenir à jour :
    une longueur ou une famille typographique n'a rien à faire dans un thème.
    """
    couleurs = {j for j, v in CLAIR.items() if _est_couleur(v)}
    manquantes = sorted(couleurs - set(SOMBRE))
    assert not manquantes, f"absentes du thème sombre : {manquantes}"


def test_aucun_jeton_utilise_n_est_indefini():
    """« --alerte-fiche » a vécu dans la surcouche de la fiche ; en la retirant
    on aurait pu laisser derrière soi des « var() » qui ne valent plus rien.

    Les définitions sont relevées dans toute la feuille, pas seulement dans
    « :root » : « --reglure » est défini sur « .seyes », là où il sert.

    Un « var() » muni d'une valeur de repli est en revanche légitime, même sans
    définition : c'est ainsi qu'on lit une variable posée par le script — la
    position du curseur, par exemple — sans que la page casse s'il ne tourne pas.
    """
    definis = set(re.findall(r"(--[a-z0-9-]+)\s*:", STYLE))
    sans_repli = set(re.findall(r"var\((--[a-z0-9-]+)\s*\)", STYLE))
    orphelins = sorted(sans_repli - definis)
    assert not orphelins, f"jetons utilisés sans définition ni valeur de repli : {orphelins}"


def test_une_seule_palette_pour_toute_l_application():
    """Elle a vécu derrière « [data-ecran=\"fiche\"] » : le reste était bleu et froid."""
    assert ':root[data-ecran="fiche"] {' not in STYLE, "la palette est de nouveau réservée à un écran"
    assert "--t0" in CLAIR and "--t5" in CLAIR, "les teintes des matières ne sont pas globales"


def test_les_trois_couleurs_ont_chacune_leur_role():
    """Bleu, on peut agir. Bordeaux, ça presse. Vert, c'est acquis. Trois rôles
    distincts, donc trois teintes qui ne doivent pas se confondre — une pastille
    « acquis » qu'on prend pour un bouton est pire qu'une pastille grise."""
    roles = {"--accent": "bleu", "--rouge": "bordeaux", "--acquis": "vert"}
    valeurs = {CLAIR[jeton].strip().lower() for jeton in roles}
    assert len(valeurs) == 3, f"deux rôles partagent la même couleur : {valeurs}"
    for jeton in roles:
        assert jeton in SOMBRE, f"{jeton} n'existe pas en sombre"


def test_le_papier_n_est_plus_creme():
    """Le fond beige chaud avec un accent ambre est la signature visuelle des
    interfaces engendrées par une machine. Le commanditaire l'a nommée, et la
    direction retenue s'en éloigne exprès."""
    assert CLAIR["--papier"].strip().lower() not in ("#fbf7f2", "#faf9f7", "#f4f1ea")
    assert CLAIR["--accent"].strip().lower() != "#9a6410", "l'ambre est revenu"


def test_les_cartes_sont_devenues_des_blocs_a_filet():
    """« Tout est une carte arrondie » était le premier grief. Une ombre portée
    sur dix-neuf blocs dit « objet séparé » dix-neuf fois, et aplatit la
    hiérarchie : il ne reste rien d'important."""
    assert "--ombre-carte: 0 0 0 1px var(--trait)" in STYLE
    assert CLAIR["--rayon"].strip() == "4px", "les grands rayons sont revenus"


def test_une_matiere_n_emprunte_aucun_des_trois_roles():
    """Bleu vif, bordeaux et vert ont chacun un rôle — on peut agir, ça presse,
    c'est acquis. Une matière qui emprunterait l'un des trois se lirait comme
    une consigne : « MATH » en bleu d'accent, c'est un bouton."""
    roles = {CLAIR[j].strip().lower() for j in ("--accent", "--rouge", "--acquis")}
    for n in range(6):
        encre = CLAIR[f"--m{n}"].strip().lower()
        assert encre not in roles, f"--m{n} porte la couleur d'un rôle"


def test_le_pastel_est_parti():
    """Abricot, rose, sauge, ciel, lilas : cinq aplats saturés sous des blocs de
    170 px, la dernière pièce de la signature « fait par IA ». Le fond d'une
    matière est maintenant un lavis, le même pour toutes à l'oeil."""
    anciens = {"#f7e9de", "#f7e6e8", "#e6efe7", "#e4ebf5", "#eae6f1", "#f4efdd"}
    for n in range(6):
        assert CLAIR[f"--t{n}"].strip().lower() not in anciens, f"--t{n} est resté pastel"
    # Un lavis, c'est-à-dire presque le papier : au-delà, c'est un aplat.
    for n in range(6):
        assert _contraste(CLAIR[f"--t{n}"], CLAIR["--papier"]) < 1.25, \
            f"--t{n} se détache trop du papier pour un lavis"


def test_la_feuille_imprimee_suit_la_palette():
    """Elle dit recopier les teintes de l'écran « pour qu'une partie garde sa
    couleur du téléphone au papier ». Elle ne pouvait pas les lire — un élève en
    mode nuit sortirait une fiche à l'encre blanche — donc elle les recopie, et
    la recopie avait silencieusement divergé : le papier portait encore l'encre
    crème et l'ambre d'une identité abandonnée depuis.
    """
    base = re.search(r"\.papier-partie \{[^}]*background:\s*(#[0-9a-fA-F]{6})", STYLE)
    assert base, "la feuille imprimée n'a plus de fond de partie"
    recopiees = [base.group(1).lower()]
    for n in range(1, 6):
        trouve = re.search(
            r'\.papier-partie\[data-teinte="%d"\] \{ background: (#[0-9a-fA-F]{6}); \}' % n, STYLE)
        assert trouve, f"la teinte {n} manque à la feuille imprimée"
        recopiees.append(trouve.group(1).lower())
    attendues = [CLAIR[f"--t{n}"].strip().lower() for n in range(6)]
    assert recopiees == attendues, (
        f"le papier dit {recopiees}, la feuille de style {attendues}")


def test_plus_une_seule_trace_d_ambre():
    """« --accent: #9a6410 » a été retiré du thème il y a deux étapes. Il avait
    survécu dans la feuille imprimée, qui n'est lue par aucun thème : la
    rubrique, le numéro d'une partie et les puces des listes étaient encore
    ambre sur un produit qui n'en a plus."""
    assert "#9a6410" not in STYLE
    assert "#241e17" not in STYLE, "l'encre crème de l'ancienne identité est restée"


def test_le_pastel_definit_les_memes_teintes_que_le_sobre():
    """Un jeu qui oublie « --t3 » laisse la sauge sobre au milieu de cinq
    pastels : personne ne le voit tant qu'on ne regarde pas cet écran-là."""
    attendus = {f"--t{n}" for n in range(6)} | {f"--m{n}" for n in range(6)}
    for nom, bloc in (("clair", ':root[data-teintes="pastel"] {'),
                      ("sombre", ':root[data-theme="dark"][data-teintes="pastel"] {')):
        poses = set(_jetons(_bloc(bloc)))
        assert attendus <= poses, f"pastel {nom} : absents — {sorted(attendus - poses)}"


def test_une_matiere_pastel_n_emprunte_aucun_des_trois_roles():
    """Même règle que pour le jeu sobre : « MATH » en bleu d'accent se lit
    comme un bouton, quelle que soit la palette choisie."""
    roles = {CLAIR[j].strip().lower() for j in ("--accent", "--rouge", "--acquis")}
    for n in range(6):
        assert PASTEL_CLAIR[f"--m{n}"].strip().lower() not in roles, f"pastel --m{n}"
