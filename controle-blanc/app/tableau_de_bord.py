"""La page /admin/metriques : ce que le produit coûte, et si ça tient.

Elle ne s'adresse qu'à une personne, et cette personne a trois questions dans
cet ordre :

1. Est-ce qu'un abonnement paie l'élève qui le consomme ?
2. Qui coûte cher, et à cause de quoi ?
3. Est-ce que les élèves reviennent ?

La version précédente répondait aux trois, mais en huit tableaux de même poids :
le chiffre qui décide de tout avait exactement la même taille que le nombre de
questions signalées. Ici la hiérarchie est celle des questions ci-dessus, et un
chiffre important a le droit d'être gros.

Deux règles qui ne se voient pas :

- Les tarifs du fournisseur sont en dollars hors taxes, l'abonnement est en
  euros. Les deux monnaies cohabitent : les euros pour décider, les dollars pour
  vérifier contre la facture. Jamais un euro sans son dollar à côté.
- Tout ce qui vient d'un élève — prénom, énoncé, motif de signalement — passe
  par `txt()` avant d'entrer dans la page.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from . import config, store

# Les teintes suivent le POSTE, jamais son rang du jour : deux captures prises à
# une semaine d'écart doivent se comparer, et une couleur attribuée par rang
# repeindrait tout dès qu'un élève change de place. Validées pour le daltonisme
# sur ce fond — contraste faible pour trois d'entre elles, d'où la règle : tout
# chiffre est écrit en toutes lettres à côté, la couleur ne fait que résumer.
TEINTES = {
    "analyse": "#2a78d6",
    "controle": "#eb6834",
    "correction": "#1baf7a",
    "fiche_generale": "#eda100",
    "fiche_ciblee": "#e87ba4",
}

MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre")


# --- Écrire des nombres qu'on lit sans les déchiffrer ------------------------

def txt(valeur: Any) -> str:
    return html.escape(str(valeur), quote=True)


def _monnaie(valeur: float, symbole: str) -> str:
    """Trois décimales sous l'unité, parce qu'une page coûte 0,018 $ et que
    « 0,02 $ » en perdrait le dixième. Mais zéro s'écrit « 0 » : « 0,000 $ » se
    lit comme une précision, alors que c'est l'absence de mesure."""
    if not valeur:
        return f"0 {symbole}"
    ecrit = f"{valeur:.3f}" if abs(valeur) < 1 else f"{valeur:.2f}"
    return ecrit.replace(".", ",") + " " + symbole


def sous(valeur: float) -> str:
    return _monnaie(valeur, "$")


def euros(valeur_usd: float) -> str:
    return _monnaie(config.en_euros(valeur_usd), "€")


def euros_directs(montant: float) -> str:
    """Un prix d'abonnement, lui, garde ses deux décimales : « 7,99 € » est le
    prix affiché, pas une mesure — et « 8 € » ne serait plus ce prix-là."""
    return f"{montant:.2f}".replace(".", ",") + " €"


def nombre(valeur: Any) -> str:
    """Un entier avec son espace fine : 1 248 se lit, 1248 se compte."""
    try:
        return f"{int(valeur):,}".replace(",", " ")
    except (TypeError, ValueError):
        return txt(valeur)


def pluriel(combien: int, singulier: str, pluriels: str) -> str:
    """« 1 question signalée », « 3 questions signalées ». Un tableau qui écrit
    « 1 question(s) » se lit comme un tableau négligé, et on croit alors moins
    ses chiffres."""
    return f"{nombre(combien)} {singulier if combien == 1 else pluriels}"


def part(combien: float, sur: float) -> str:
    return f"{combien / sur * 100:.0f} %" if sur else "—"


# --- Les briques de la page --------------------------------------------------

def tableau_large(contenu: str) -> str:
    """Un tableau trop large pour un téléphone défile latéralement. Rien ne le
    dit à l'oeil : la dernière colonne est simplement coupée, et on croit l'avoir
    vue en entier. La mention n'apparaît que sur petit écran, où elle sert."""
    return (f"<div class='large'><table>{contenu}</table></div>"
            "<p class='defile'>Le tableau défile vers la droite →</p>")


def carte(titre: str, valeur: str, dessous: str = "", note: str = "",
          ton: str = "", large: bool = False) -> str:
    """Un chiffre, son titre, et ce qu'il faut savoir pour ne pas le mal lire."""
    classes = " ".join(filter(None, ("carte", ton, "large" if large else "")))
    return (
        f"<div class='{classes}'>"
        f"<p class='titre-carte'>{titre}</p>"
        f"<p class='chiffre'>{valeur}</p>"
        + (f"<p class='dessous'>{dessous}</p>" if dessous else "")
        + (f"<p class='note'>{note}</p>" if note else "")
        + "</div>"
    )


def ligne(titre: str, valeur: Any, note: str = "", fort: bool = False) -> str:
    classe = " class='fort'" if fort else ""
    return (f"<tr{classe}><th>{titre}</th><td class='v'>{valeur}</td>"
            f"<td class='n'>{note}</td></tr>")


def barre_composition(postes: dict[str, Any], total: float, hauteur: str = "") -> str:
    """D'où vient une dépense, en une barre. Elle ne porte aucun chiffre : ils
    sont tous écrits à côté. Le filet de 2 px empêche deux teintes voisines de
    se souder pour un oeil qui ne les distingue pas."""
    if total <= 0:
        return ""
    morceaux = []
    for poste in store.POSTES:
        proportion = postes[poste]["cout_usd"] / total * 100
        if proportion <= 0:
            continue
        morceaux.append(
            f"<span style='width:{proportion:.2f}%;background:{TEINTES[poste]}'"
            f" title='{txt(store.NOM_DU_POSTE[poste])} — {proportion:.0f} %'></span>"
        )
    style = f" style='height:{hauteur}'" if hauteur else ""
    return f"<span class='barre'{style}>" + "".join(morceaux) + "</span>"


def legende() -> str:
    return "<div class='legende'>" + "".join(
        f"<span class='cle-couleur'><i style='background:{TEINTES[poste]}'></i>"
        f"{txt(store.NOM_DU_POSTE[poste])}</span>"
        for poste in store.POSTES
    ) + "</div>"


# --- Le bandeau qui répond avant qu'on ait cherché ---------------------------

def verdict(m: dict[str, Any], plafond: dict[str, Any]) -> str:
    """La question qui décide de tout, et sa réponse en toutes lettres.

    Le coût retenu est la MOYENNE d'un compte sur un mois — pas le cumul de tous
    les élèves, pas le coût d'une séance. C'est la seule grandeur comparable à
    un abonnement, qui se paie par personne et par mois.
    """
    prix = config.PRIX_ABONNEMENT_EUR
    if not m["comptes_mois_mesures"]:
        return (
            "<section class='verdict attente'>"
            "<p class='question'>Est-ce qu'un abonnement paie l'élève qui le consomme ?</p>"
            "<p class='reponse'>Pas encore de réponse : aucun élève n'a consommé "
            "assez pour qu'un mois se chiffre.</p>"
            "<p class='source'>Le chiffre apparaîtra tout seul dès les premiers appels facturés.</p>"
            "</section>"
        )

    cout = config.en_euros(m["cout_usd_moyen_compte_mois"])
    reste = prix - cout
    proportion = min(100.0, cout / prix * 100) if prix else 100.0
    ton = "bon" if proportion < 40 else ("moyen" if proportion < 70 else "mauvais")

    if reste > 0:
        reponse = (
            f"Sur les <b>{euros_directs(prix)}</b> d'un abonnement, le modèle en prend "
            f"<b class='gros'>{euros_directs(cout)}</b>.<br>"
            f"Il te reste <b class='gros'>{euros_directs(reste)}</b> pour l'hébergement, "
            "les impôts et toi."
        )
    else:
        ton = "mauvais"
        reponse = (
            f"Non : un élève coûte <b class='gros'>{euros_directs(cout)}</b> par mois, "
            f"l'abonnement en encaisse {euros_directs(prix)}.<br>"
            f"Chaque abonné te fait perdre <b class='gros'>{euros_directs(-reste)}</b>."
        )

    pire = config.en_euros(m["cout_usd_max_compte_mois"])
    au_pire = (
        f" Le plus gourmand a coûté {euros_directs(pire)} sur son mois"
        + (f", et le plafond autorise {euros(plafond['cout_usd'])}."
           if plafond["cout_usd"] else ".")
    )

    # La barre sature à 100 % — elle ne peut pas déborder de son cadre. Écrire
    # « 137 % » sous une barre pleine ferait douter des deux ; au-delà du prix,
    # c'est une seule phrase qui dit de combien on dépasse.
    if reste > 0:
        mots = (f"<span>Ce que prend le modèle · {part(cout, prix)}</span>"
                f"<span>Ce qu'il te reste · {part(reste, prix)}</span>")
    else:
        mots = (f"<span>Le modèle prend {part(cout, prix)} de l'abonnement</span>"
                "<span>Il ne reste rien</span>")

    return (
        f"<section class='verdict {ton}'>"
        "<p class='question'>Est-ce qu'un abonnement paie l'élève qui le consomme ?</p>"
        f"<p class='reponse'>{reponse}</p>"
        "<div class='jauge'>"
        f"<span class='pris' style='width:{proportion:.1f}%'></span></div>"
        f"<div class='jauge-mots'>{mots}</div>"
        f"<p class='source'>Moyenne mesurée sur {nombre(m['comptes_mois_mesures'])} "
        f"couples compte × mois, soit {sous(m['cout_usd_moyen_compte_mois'])} hors taxes."
        f"{au_pire}</p>"
        "</section>"
    )


# --- Les sections ------------------------------------------------------------

def section_eleves(par_eleve: dict[str, Any]) -> str:
    def cellule(nom_poste: str, poste: dict[str, Any]) -> str:
        if not poste["quantite"] and not poste["cout_usd"]:
            return "<td class='v vide'>—</td>"
        combien = poste["quantite"]
        return (f"<td class='v'>{sous(poste['cout_usd'])}"
                f"<small>{combien} {txt(store.unite(nom_poste, combien))}</small></td>")

    entetes = "".join(f"<th class='v'>{txt(store.NOM_DU_POSTE[p])}</th>" for p in store.POSTES)

    corps = "".join(
        "<tr><th class='qui'>"
        f"<span class='prenom'>{txt(e['prenom'])}</span>"
        + (f"<span class='niveau'>{txt(e['niveau'])}</span>" if e["niveau"] else "")
        + barre_composition(e["postes"], e["cout_usd"])
        + "</th>"
        + f"<td class='v total'>{sous(e['cout_usd'])}<small>{euros(e['cout_usd'])}</small></td>"
        + "".join(cellule(p, e["postes"][p]) for p in store.POSTES)
        + "</tr>"
        for e in par_eleve["eleves"]
    ) or ("<tr><td colspan='7' class='n'>Aucun appel facturé pour l’instant : "
          "aucun élève n’a encore rentré de cours.</td></tr>")

    return f"""
<h2>Ce que coûte chaque élève</h2>
<p class='chapo'>Du plus cher au moins cher. Chaque case donne ce que le poste a coûté,
et en dessous ce qu'il a consommé. La barre sous le prénom résume d'où vient la dépense.
<b>Ces montants sont cumulés depuis le début</b>, pas sur le mois en cours.</p>
{legende()}
{tableau_large(f'''
 <thead><tr><th>Élève</th><th class='v'>Total</th>{entetes}</tr></thead>
 <tbody>{corps}</tbody>''')}"""


def section_argent(par_eleve: dict[str, Any]) -> str:
    total = par_eleve["cout_usd_total"]
    combien_d_eleves = len(par_eleve["eleves"]) or 1
    proportion = (lambda c: c / total * 100) if total > 0 else (lambda c: 0.0)

    lignes = "".join(
        f"<tr><th><i class='pastille' style='background:{TEINTES[poste]}'></i>"
        f"{txt(store.NOM_DU_POSTE[poste])}</th>"
        f"<td class='v'>{sous(t['cout_usd'])}<small>{proportion(t['cout_usd']):.0f} % du total</small></td>"
        f"<td class='v'>{nombre(t['quantite'])}<small>{txt(store.unite(poste, t['quantite']))}</small></td>"
        f"<td class='v cle'>{sous(t['cout_usd'] / t['quantite']) if t['quantite'] else '—'}"
        f"<small>l’unité</small></td>"
        f"<td class='v'>{sous(t['cout_usd'] / combien_d_eleves)}<small>par élève</small></td></tr>"
        for poste, t in ((p, par_eleve["totaux"][p]) for p in store.POSTES)
        if t["cout_usd"] or t["quantite"]
    ) or "<tr><td colspan='5' class='n'>Rien à répartir pour l’instant.</td></tr>"

    grande_barre = barre_composition(par_eleve["totaux"], total, hauteur="26px")
    mots = "".join(
        f"<span class='cle-couleur'><i style='background:{TEINTES[poste]}'></i>"
        f"{txt(store.NOM_DU_POSTE[poste])} <b>{proportion(par_eleve['totaux'][poste]['cout_usd']):.0f} %</b></span>"
        for poste in store.POSTES if par_eleve["totaux"][poste]["cout_usd"] > 0
    )

    return f"""
<h2>Où va l’argent</h2>
<p class='chapo'>Tout ce qui a été dépensé depuis le début, réparti par poste.
La colonne <b>à l’unité</b> est celle qui sert à décider : c'est le prix d'UNE page
photographiée, d'UN contrôle blanc, d'UNE fiche. Les plafonds du mois se règlent là-dessus.</p>
<div class='panneau'>
 <p class='titre-carte'>Dépensé en tout · {sous(total)} <span class='sec'>soit {euros(total)}</span></p>
 {grande_barre or "<p class='n'>Aucun appel facturé.</p>"}
 <div class='legende grosse'>{mots}</div>
</div>
{tableau_large(f'''
 <thead><tr><th>Poste</th><th class='v'>Coût</th><th class='v'>Volume</th>
 <th class='v'>À l’unité</th><th class='v'>Par élève</th></tr></thead>
 <tbody>{lignes}</tbody>''')}"""


def section_plafond(plafond: dict[str, Any]) -> str:
    lignes = "".join(
        f"<tr><th><i class='pastille' style='background:{TEINTES[l['poste']]}'></i>"
        f"{txt(store.NOM_DU_POSTE[l['poste']])}</th>"
        f"<td class='v'>{nombre(l['droits'])}<small>{txt(store.unite(l['poste'], l['droits']))}</small></td>"
        f"<td class='v'>{sous(l['unitaire_usd']) if l['mesure'] else '—'}<small>l’unité</small></td>"
        f"<td class='v total'>{sous(l['cout_usd']) if l['mesure'] else '—'}"
        f"<small>{euros(l['cout_usd']) if l['mesure'] else 'jamais appelé'}</small></td></tr>"
        for l in plafond["lignes"]
    )
    manque = (
        "<p class='alerte'>Jamais appelé, donc jamais chiffré : "
        + txt(", ".join(store.NOM_DU_POSTE[p].lower() for p in plafond["sans_mesure"]))
        + ". Le total ci-dessous est donc un plancher, pas le vrai plafond.</p>"
    ) if plafond["sans_mesure"] else ""

    return f"""
<h2>Si un élève consomme tout son mois</h2>
<p class='chapo'>Le pire cas, calculé sur les prix du tableau précédent : un élève qui
irait au bout de chacun de ses droits. C'est ce chiffre-là qui dit si l'abonnement
tient, pas la moyenne — une moyenne basse ne veut dire qu'une chose tant que
personne ne se sert vraiment du produit.</p>
{manque}
{tableau_large(f'''
 <thead><tr><th>Poste</th><th class='v'>Droits du mois</th>
 <th class='v'>Prix mesuré</th><th class='v'>Au plafond</th></tr></thead>
 <tbody>{lignes}
 <tr class='somme'><th>Un élève au maximum</th><td class='v'></td><td class='v'></td>
 <td class='v total'>{sous(plafond['cout_usd'])}<small>{euros(plafond['cout_usd'])} par mois</small></td></tr>
 </tbody>''')}"""


def section_usage(m: dict[str, Any]) -> str:
    actifs = m["eleves_actifs"] or 1
    chemins = "".join(
        f"<tr><th>{txt(cle)}</th><td class='v'>{nombre(v['sessions'])}</td>"
        f"<td class='n'>{nombre(v['revenus'])} revenus un autre jour</td></tr>"
        for cle, v in sorted(m["par_chemin"].items())
    ) or "<tr><td colspan='3' class='n'>Aucun choix enregistré pour l'instant.</td></tr>"

    cartes = (
        carte("Élèves actifs", nombre(m["eleves_actifs"]), "ont fait au moins une chose")
        + carte("Revenus un autre jour", nombre(m["eleves_revenus_un_autre_jour"]),
                f"{part(m['eleves_revenus_un_autre_jour'], actifs)} des actifs")
        + carte("Revenus une semaine après", nombre(m["eleves_revenus_une_semaine_apres"]),
                f"{part(m['eleves_revenus_une_semaine_apres'], actifs)} des actifs",
                "le seul signe d'un usage qui tient", ton="phare")
        + carte("Ont rentré 2 cours ou plus", nombre(m["eleves_deux_cours_ou_plus"]),
                "un seul cours, c'est un essai")
        + carte("Jours actifs", nombre(m["jours_actifs_median_par_eleve"]),
                "médiane, par élève")
    )

    return f"""
<h2>Est-ce que ça sert vraiment</h2>
<p class='chapo'>Par élève d'abord : tout ce qui se compte par séance compte des cours,
et un élève qui en ouvre six apparaîtrait comme six visiteurs venus une fois chacun.
La question est « est-ce qu'un élève revient », pas « est-ce qu'un cours est rouvert ».</p>
<h3>Par élève</h3>
<div class='grille'>{cartes}</div>
<h3>Par cours</h3>
<div class='deux'>
<table>
 <thead><tr><th>Ce que font les cours</th><th class='v'>Combien</th><th></th></tr></thead>
 {ligne("Liens ouverts", nombre(m["ouvertures"]), "séances distinctes")}
 {ligne("2 fiches ou plus", nombre(m["deux_fiches_ou_plus"]), "sans qu'on le demande")}
 {ligne("Cours rouverts le lendemain", nombre(m["revenus_le_lendemain"]), "un cours, pas un élève")}
 {ligne("Sessions créées", nombre(m["sessions_creees"]))}
 {ligne("Contrôles terminés", nombre(m["controles_termines"]))}
</table>
<table>
 <thead><tr><th>Chemin choisi à l’étape 3</th><th class='v'>Cours</th><th></th></tr></thead>
 {chemins}</table>
</div>"""


def section_alertes(m: dict[str, Any], signalees: list[dict[str, Any]]) -> str:
    tarifs = (
        "<p class='alerte'>Tarif inconnu pour "
        + txt(", ".join(m["tarifs_inconnus"]))
        + " — ces lignes sont chiffrées au tarif par défaut, donc fausses. "
        + "Ajouter le modèle dans <code>PRIX_USD_PAR_MTOK_PAR_MODELE</code>.</p>"
    ) if m["tarifs_inconnus"] else ""

    liste = "".join(
        f"<li><b>Q{txt(signal.get('numero', '?'))}</b> — {txt(signal.get('enonce', '')[:160])}"
        + (f"<br><i>{txt(signal.get('motif'))}</i>" if signal.get("motif") else "")
        + "</li>"
        for signal in signalees
    ) or "<li class='n'>Aucune question signalée. C'est la bonne nouvelle.</li>"

    return f"""
<h2>Ce qui cloche</h2>
{tarifs}
<p class='chapo'>{pluriel(m["questions_signalees"], "question signalée", "questions signalées")}
« me semble fausse » depuis le début. Les trente dernières :</p>
<ul class='signalements'>{liste}</ul>"""


# --- La feuille de style -----------------------------------------------------
#
# Écrite à part, en texte brut : dans une f-string, chaque accolade CSS devrait
# être doublée, et une seule oubliée casse la page entière sans rien dire.

STYLE = """
 *, *::before, *::after { box-sizing: border-box; }
 body { font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0;
        background: #f2efea; color: #1c1a17;
        -webkit-font-smoothing: antialiased; }
 .dedans { max-width: 1060px; margin: 0 auto; padding: 0 20px; }

 /* Le bandeau de tête : on sait où on est avant d'avoir lu quoi que ce soit. */
 .tete { background: #1c1a17; color: #f2efea; padding: 14px 0; margin-bottom: 28px; }
 .tete .dedans { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
 .marque { font-weight: 700; letter-spacing: -.01em; font-size: 1.05rem; }
 .ou { color: #a9a29a; font-size: .9rem; }
 .quand { margin-left: auto; color: #a9a29a; font-size: .82rem; }

 h1 { font-size: 1.05rem; margin: 0; }
 h2 { font-size: 1.35rem; letter-spacing: -.015em; margin: 44px 0 6px; }
 h3 { font-size: .78rem; text-transform: uppercase; letter-spacing: .08em;
      color: #7d766e; margin: 26px 0 10px; font-weight: 700; }
 .chapo { color: #5d564f; font-size: .92rem; max-width: 62ch; margin: 0 0 18px; }
 .n { color: #7d766e; font-size: .85rem; }
 code { font-size: .85em; background: #e7e2da; padding: 1px 4px; border-radius: 4px; }

 /* --- Le verdict. C'est la seule chose qu'on doit pouvoir lire de loin. --- */
 .verdict { background: #fff; border-radius: 16px; padding: 26px 28px;
            border: 1px solid #e3ded6; border-top: 4px solid #b4530a;
            box-shadow: 0 10px 30px -22px rgba(28,26,23,.5); }
 .verdict.bon { border-top-color: #1baf7a; }
 .verdict.moyen { border-top-color: #eda100; }
 .verdict.mauvais { border-top-color: #d4351c; }
 .verdict.attente { border-top-color: #b8b1a8; }
 .question { margin: 0 0 10px; font-size: .78rem; text-transform: uppercase;
             letter-spacing: .08em; color: #7d766e; font-weight: 700; }
 .reponse { margin: 0; font-size: 1.32rem; line-height: 1.45; letter-spacing: -.01em; }
 .reponse .gros { font-size: 1.9rem; font-weight: 700; letter-spacing: -.02em;
                  font-variant-numeric: tabular-nums; }
 .bon .gros { color: #12855c; } .moyen .gros { color: #9c6b00; }
 .mauvais .gros { color: #b52a14; }
 .source { margin: 16px 0 0; color: #7d766e; font-size: .84rem; }
 .jauge { display: flex; height: 14px; border-radius: 7px; overflow: hidden;
          background: #1baf7a; margin-top: 20px; }
 .jauge .pris { background: #eb6834; display: block; }
 .mauvais .jauge { background: #d4351c; } .mauvais .jauge .pris { background: #d4351c; }
 .jauge-mots { display: flex; justify-content: space-between; gap: 12px;
               font-size: .78rem; color: #5d564f; margin-top: 7px; }

 /* --- Les cartes à chiffre. --- */
 .grille { display: grid; gap: 12px; margin: 14px 0 4px;
           grid-template-columns: repeat(auto-fit, minmax(178px, 1fr)); }
 .carte { background: #fff; border: 1px solid #e3ded6; border-radius: 14px;
          padding: 16px 18px; }
 .carte.phare { background: #1c1a17; border-color: #1c1a17; }
 .carte.phare .titre-carte, .carte.phare .dessous { color: #a9a29a; }
 .carte.phare .chiffre { color: #fff; }
 .carte.phare .note { color: #eda100; }
 .titre-carte { margin: 0; font-size: .74rem; text-transform: uppercase;
                letter-spacing: .07em; color: #7d766e; font-weight: 700; }
 .chiffre { margin: 8px 0 0; font-size: 2.1rem; font-weight: 700; line-height: 1.05;
            letter-spacing: -.03em; font-variant-numeric: tabular-nums; color: #1c1a17; }
 .carte .dessous { margin: 6px 0 0; font-size: .85rem; color: #5d564f; }
 .carte .note { margin: 8px 0 0; font-size: .78rem; color: #b4530a; font-weight: 600; }
 .sec { font-weight: 400; color: #7d766e; text-transform: none; letter-spacing: 0; }

 .panneau { background: #fff; border: 1px solid #e3ded6; border-radius: 14px;
            padding: 18px 20px; margin-bottom: 16px; }
 .panneau .titre-carte { margin-bottom: 12px; font-size: .84rem; color: #1c1a17; }

 /* --- Les tableaux. --- */
 table { width: 100%; border-collapse: collapse; background: #fff; }
 .large, .deux table { border: 1px solid #e3ded6; border-radius: 14px; overflow: hidden; }
 .large { overflow-x: auto; }
 .large table { min-width: 660px; }
 .large th, .large td { white-space: nowrap; }
 thead th { font-size: .72rem; text-transform: uppercase; letter-spacing: .05em;
            color: #7d766e; font-weight: 700; background: #faf8f5; }
 th { text-align: left; font-weight: 600; padding: 13px 16px;
      border-bottom: 1px solid #ece7e0; }
 td { padding: 13px 16px; border-bottom: 1px solid #ece7e0; }
 tr:last-child th, tr:last-child td { border-bottom: 0; }
 td.v, thead th.v { text-align: right; font-variant-numeric: tabular-nums;
                    font-weight: 600; }
 td.v small, th small { display: block; font-weight: 400; font-size: .73rem;
                        color: #7d766e; letter-spacing: 0; margin-top: 2px; }
 td.vide { color: #c7c1b8; font-weight: 400; }
 td.total { color: #b4530a; }
 td.v.cle { color: #1c1a17; background: #fdf6ee; }
 tr.fort td.v { color: #b4530a; font-size: 1.25rem; }
 tr.somme th, tr.somme td { background: #faf8f5; border-top: 2px solid #e3ded6; }
 tr.somme td.total { font-size: 1.2rem; }
 .deux { display: grid; gap: 12px; align-items: start;
         grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
 .deux td.v { width: 70px; }

 /* --- Le nom de l'élève, et la composition de sa dépense. --- */
 th.qui { min-width: 172px; }
 .prenom { font-size: 1.02rem; }
 .niveau { display: inline-block; margin-left: 7px; padding: 1px 7px; border-radius: 20px;
           background: #ece7e0; color: #5d564f; font-size: .7rem; font-weight: 600;
           vertical-align: 1px; }
 .barre { display: flex; gap: 2px; height: 9px; border-radius: 5px; margin-top: 9px;
          overflow: hidden; background: #ece7e0; }
 .barre span { display: block; height: 100%; }
 .legende { display: flex; flex-wrap: wrap; gap: 8px 16px; margin: 0 0 14px;
            font-size: .8rem; color: #5d564f; }
 .legende.grosse { margin: 12px 0 0; font-size: .85rem; }
 .cle-couleur { display: inline-flex; align-items: center; gap: 6px; }
 .cle-couleur i, .pastille { width: 10px; height: 10px; border-radius: 3px;
                             display: inline-block; flex: 0 0 auto; }
 .pastille { margin-right: 9px; vertical-align: baseline; }

 .defile { display: none; }
 .alerte { background: #fdf1e3; border-left: 3px solid #b4530a; padding: 12px 16px;
           border-radius: 0 8px 8px 0; font-size: .87rem; margin: 0 0 16px; }
 .signalements { background: #fff; border: 1px solid #e3ded6; border-radius: 14px;
                 padding: 16px 16px 16px 34px; margin: 0; }
 .signalements li { margin-bottom: 11px; font-size: .9rem; }
 .signalements li:last-child { margin-bottom: 0; }
 .pied { color: #7d766e; font-size: .8rem; margin: 40px 0 48px; max-width: 62ch; }

 /* Un téléphone : une seule colonne, des marges qui ne mangent pas l'écran,
    et un chiffre qui reste lisible sans être écrit en travers. */
 @media (max-width: 560px) {
   .dedans { padding: 0 14px; }
   .verdict { padding: 20px 18px; border-radius: 14px; }
   .reponse { font-size: 1.12rem; }
   .reponse .gros { font-size: 1.55rem; }
   h2 { font-size: 1.18rem; margin-top: 34px; }
   .large { margin: 0 -14px; padding: 0 14px; border: 0; border-radius: 0; }
   .large table { border: 1px solid #e3ded6; border-radius: 14px; }
   .defile { display: block; margin: 7px 0 0; font-size: .76rem; color: #7d766e; }
 }
"""


def rendre(m: dict[str, Any], par_eleve: dict[str, Any],
           plafond: dict[str, Any], signalees: list[dict[str, Any]]) -> str:
    aujourdhui = datetime.now()
    jour = f"{aujourdhui.day} {MOIS[aujourdhui.month - 1]} {aujourdhui.year}"

    cartes_cout = (
        carte("L’élève moyen", euros(m["cout_usd_moyen_compte_mois"]),
              f"{sous(m['cout_usd_moyen_compte_mois'])} par mois",
              "c'est lui qu'un abonnement doit payer", ton="phare")
        + carte("L’élève médian", euros(m["cout_usd_median_compte_mois"]),
                f"{sous(m['cout_usd_median_compte_mois'])} par mois",
                "la moitié coûte moins que ça")
        + carte("Le plus gourmand", euros(m["cout_usd_max_compte_mois"]),
                f"{sous(m['cout_usd_max_compte_mois'])} sur un mois",
                "déjà arrivé, pas une hypothèse")
        + carte("Au plafond", euros(plafond["cout_usd"]),
                f"{sous(plafond['cout_usd'])} par mois",
                "si un élève consommait tous ses droits")
    )

    return f"""<!doctype html><html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Repère — tableau de bord</title>
<style>{STYLE}</style>
<header class="tete"><div class="dedans">
 <span class="marque">Repère</span>
 <h1 class="ou">Tableau de bord</h1>
 <span class="quand">{txt(jour)}</span>
</div></header>
<main class="dedans">

{verdict(m, plafond)}

<h2>Le chiffre qui décide de l’abonnement</h2>
<p class='chapo'>Quatre façons de regarder le même mois. La <b>moyenne</b> dit ce que
coûtent les élèves d'aujourd'hui ; le <b>plafond</b> dit ce que coûterait le pire d'entre
eux. Un prix fixé sur la moyenne tient tant que personne ne se sert vraiment du produit.</p>
<div class='grille'>{cartes_cout}</div>

{section_eleves(par_eleve)}

{section_argent(par_eleve)}

{section_plafond(plafond)}

{section_usage(m)}

{section_alertes(m, signalees)}

<p class='pied'>Les dollars sont ceux du fournisseur, <b>hors taxes</b> : ce sont ses tarifs
affichés. Les euros sont convertis à un taux fixe de {txt(f'{config.TAUX_EURO_POUR_UN_DOLLAR:.2f}'.replace('.', ','))} €
pour 1 $, réglé dans <code>CB_TAUX_EUR_USD</code> — ils servent à décider d'un ordre de
grandeur, pas à tenir une comptabilité. Selon ton statut, la facture peut porter 20 % de
TVA en plus : c'est elle qui fait foi, pas cette page.</p>
</main></html>"""
