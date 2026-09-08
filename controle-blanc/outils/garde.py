# -*- coding: utf-8 -*-
"""La garde : trois cas figés, vérifiés à chaque changement de consigne.

À quoi ça sert. Les tests de « pytest » vérifient le code ; ils ne peuvent rien
dire de ce que le modèle produit. Un mot changé dans un prompt peut faire
disparaître les pièges d'une fiche, transformer un contrôle en QCM ou faire
apparaître une note chiffrée, sans casser une seule ligne de Python. La garde
lance la chaîne sur trois cours toujours identiques et vérifie ce qui doit
rester vrai quoi qu'il arrive.

Ce que ce n'est pas. Ce n'est pas un banc d'essai : la garde ne note pas la
qualité et ne compare pas deux réglages. Elle attrape les cassures franches,
pas les dérives. Un cas peut passer avec une fiche médiocre — elle dit
seulement que rien n'est cassé.

Ce qu'elle coûte. Environ 0,35 $ le passage, une minute et demie.

    python3 outils/garde.py                        # avant de pousser une consigne
    python3 outils/garde.py --effort low           # « est-ce que low casse quelque chose ? »
    python3 outils/garde.py --modele claude-opus-5

Le code de sortie vaut 0 si tout tient, 1 sinon : la garde s'enchaîne donc dans
un script ou un workflow.

La lecture des photos n'est pas couverte par défaut — le corpus part d'un cours
déjà transcrit, et on ne met pas le cahier d'un élève dans un dépôt public. Pose
CB_GARDE_PHOTOS sur un dossier d'images pour ajouter ce cas-là.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

sys.path.insert(0, str(RACINE / "outils"))


# --- Les cas ----------------------------------------------------------------
# Trois, pas dix : la garde doit coûter assez peu pour qu'on la lance vraiment.
# Deux matières, parce que le format d'un contrôle d'histoire et celui d'un
# contrôle de maths n'ont rien à voir et ne cassent pas pour les mêmes raisons.

CAS = [
    # « corriger » n'est vrai qu'une fois : c'est l'étape la plus chère, et une
    # seule suffit à vérifier que la correction corrige.
    {"id": "histoire-neolithique", "corpus": "revolution-neolithique", "corriger": True},
    {"id": "histoire-cites-grecques", "corpus": "cites-grecques", "corriger": False},
    {"id": "maths-proportionnalite", "corpus": "proportionnalite", "corriger": False},
]

# Un plafond par étape et un pour le passage entier. Ils ne sont pas serrés :
# ils attrapent l'emballement (une consigne qui fait écrire trois fois plus),
# pas les variations d'un appel à l'autre.
PLAFOND_ETAPE = 0.15
PLAFOND_PASSAGE = 0.70


class Manque(Exception):
    """Un invariant rompu. Le message dit lequel, en français, sans jargon."""


def exige(condition: bool, message: str) -> None:
    if not condition:
        raise Manque(message)


def texte_de(objet) -> str:
    """Tout le texte d'une structure, à plat, pour y chercher un mot."""
    if isinstance(objet, str):
        return objet
    if isinstance(objet, dict):
        return " ".join(texte_de(v) for v in objet.values())
    if isinstance(objet, (list, tuple)):
        return " ".join(texte_de(v) for v in objet)
    return ""


def sans_accent(texte: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", texte)
                   if unicodedata.category(c) != "Mn").lower()


# Cinq lettres au moins : en dessous, un mot français est presque toujours un
# mot-outil. Le reste de la liste enlève les quelques longs qui le sont aussi.
MOTS_VIDES = {"leurs", "cette", "celui", "celle", "comme", "aussi", "alors",
              "ainsi", "entre", "depuis", "pendant", "avant", "apres", "selon",
              "chaque", "toute", "toutes", "autre", "autres", "meme", "memes",
              "dont", "quand", "parce", "cependant", "toutefois", "lorsque"}


def mots_utiles(texte: str) -> set[str]:
    return {m for m in re.findall(r"[a-z]+", sans_accent(texte))
            if len(m) >= 5 and m not in MOTS_VIDES}


def couverture(notions: list[str], texte) -> tuple[int, int]:
    """Combien des notions du cours se retrouvent dans ce qui a été produit.

    Une notion compte dès que la moitié de ses mots pleins réapparaissent : on
    cherche à savoir si le sujet a été traité, pas s'il a été recopié.
    """
    plat = mots_utiles(texte_de(texte))
    trouvees = 0
    for notion in notions:
        mots = mots_utiles(notion)
        if mots and len(mots & plat) >= max(1, len(mots) // 2):
            trouvees += 1
    return trouvees, len(notions)


# --- Les invariants ---------------------------------------------------------

def verifier_fiche(fiche: dict, notions: list[str]) -> None:
    exige(bool(fiche.get("titre", "").strip()), "la fiche n'a pas de titre")
    duree = fiche.get("duree_lecture_minutes", 0)
    exige(2 <= duree <= 12, f"la fiche annonce {duree} min de lecture (attendu entre 2 et 12)")

    sections = fiche.get("sections") or []
    exige(len(sections) >= 3, f"{len(sections)} section(s) dans la fiche, il en faut au moins 3")
    for i, s in enumerate(sections, 1):
        exige(bool(s.get("titre", "").strip()), f"la section {i} n'a pas de titre")
        exige(len(s.get("points") or []) >= 2, f"la section {i} a moins de 2 points")
        # Le « à retenir » surligné est la promesse de la fiche : sans lui, on
        # rend un résumé de plus.
        exige(bool((s.get("a_retenir") or "").strip()), f"la section {i} n'a pas d'« à retenir »")

    definitions = fiche.get("definitions") or []
    exige(len(definitions) >= 3, f"{len(definitions)} définition(s), il en faut au moins 3")
    for d in definitions:
        exige(bool(d.get("terme")) and bool(d.get("definition")), "une définition est incomplète")

    # Les pièges sont ce qui distingue la fiche d'un résumé : ils nomment la
    # confusion que l'élève va faire.
    pieges = fiche.get("pieges") or []
    exige(len(pieges) >= 2, f"{len(pieges)} piège(s), il en faut au moins 2")

    # La fiche résume tout le chapitre : elle doit en couvrir l'essentiel. Le
    # seuil est lâche exprès — il attrape l'effondrement, pas la variation.
    trouvees, total = couverture(notions, fiche)
    exige(trouvees >= total * 0.5,
          f"la fiche ne couvre que {trouvees} notions du cours sur {total}")


# Le cahier des charges interdit le QCM. Ce motif a été faux deux fois avant
# d'être juste, et les deux erreurs se ressemblent : un signe de QCM pris isolé
# ne veut rien dire.
#
#   « a) … b) … »              la numérotation normale des sous-questions
#   « Entoure sur la carte… »  une consigne de cartographie, pas un choix
#
# Il faut donc les deux moitiés : un verbe qui fait choisir ET la chose parmi
# laquelle on choisit, dans la même phrase.
QCM = re.compile(
    r"\b(coch(e|er|ez)|entoure(z)?|choisi(s|ssez)|s[ée]lectionne(z)?)\b"
    r"[^.?!]{0,60}"
    r"\b(bonnes?\s+r[ée]ponses?|r[ée]ponses?\s+(exacte|juste|correcte)|propositions?|affirmations?)\b"
    r"|\bparmi\s+(les|ces)\s+(propositions|r[ée]ponses|affirmations)\b"
    r"|\bune\s+seule\s+r[ée]ponse\b",
    re.I)


def verifier_controle(controle: dict, notions: list[str], duree_format: int) -> None:
    questions = controle.get("questions") or []
    exige(4 <= len(questions) <= 12, f"{len(questions)} question(s) (attendu entre 4 et 12)")

    numeros = [q.get("numero") for q in questions]
    exige(numeros == sorted(numeros), "les questions ne sont pas dans l'ordre")

    for q in questions:
        n = q.get("numero")
        exige(bool((q.get("enonce") or "").strip()), f"Q{n} n'a pas d'énoncé")
        exige(bool((q.get("notion") or "").strip()), f"Q{n} ne dit pas sur quelle notion elle porte")
        # Sans ça, la correction ne peut renvoyer nulle part, et c'est toute la
        # thèse du produit qui tombe.
        exige(bool((q.get("ou_dans_le_cours") or "").strip()),
              f"Q{n} ne renvoie à aucun endroit du cours")
        exige((q.get("duree_minutes") or 0) > 0, f"Q{n} n'a pas de durée")

    # Le schéma impose maintenant deux critères de correction — « essentiel » et
    # « second », deux champs obligatoires plutôt qu'un tableau sans minimum. La
    # garde tolérait un écart tant que rien ne l'imposait ; elle n'a plus de
    # raison de le faire. Il reste un cas possible : « required » impose la
    # présence d'un champ, pas son contenu, et un « second » vide est retiré à
    # la mise à plat.
    maigres = [q["numero"] for q in questions if len(q.get("points_attendus") or []) < 2]
    exige(not maigres,
          "moins de 2 points attendus, donc pas corrigeable : Q"
          + ", Q".join(str(m) for m in maigres))

    total = sum(q.get("duree_minutes", 0) for q in questions)
    bas, haut = duree_format * 0.5, duree_format * 1.5
    exige(bas <= total <= haut,
          f"le contrôle dure {total} min pour un format de {duree_format} min")

    # Un contrôle de cinquante minutes ne peut pas tout couvrir, et ne doit pas :
    # on vérifie seulement qu'il pioche vraiment dans le cours.
    trouvees, total = couverture(notions, questions)
    exige(trouvees >= 3,
          f"le contrôle ne touche que {trouvees} notions du cours sur {total}")

    # « Le contrôle ne peut pas être un QCM. Quelques questions fermées sont
    # admises en partie 1 […] mais l'essentiel doit être rédigé » dit la
    # consigne. Interdire toute question fermée était donc plus sévère que le
    # produit lui-même : un « coche la bonne réponse » en ouverture d'un
    # contrôle d'histoire de 6e est légitime. Deux ne le sont plus.
    qcm = [(q["numero"], QCM.search(q.get("enonce") or "")) for q in questions]
    qcm = [(n, m) for n, m in qcm if m]
    if len(qcm) > 1:
        preuves = " / ".join(f"Q{n} « …{m.group(0)[:50]}… »" for n, m in qcm)
        raise Manque(f"{len(qcm)} questions à choisir au lieu de rédiger : {preuves}")

    # Ce qui sépare un contrôle d'un quiz : on y rédige. La moitié des questions
    # au moins doit demander autre chose qu'un mot.
    developpees = [q for q in questions
                   if q.get("duree_minutes", 0) >= 5 or len(q.get("points_attendus") or []) >= 3]
    exige(len(developpees) * 2 >= len(questions),
          f"{len(developpees)} question(s) à rédiger sur {len(questions)} : "
          "le contrôle est devenu un quiz")


# Une note chiffrée est le seul interdit absolu du produit.
NOTE = re.compile(r"/\s*20\b|\btu aurais\b|\bnote\s*:\s*\d|\b\d{1,2}\s*/\s*20\b", re.I)


def verifier_correction(correction: dict, questions: list[dict], fausses: set[int]) -> None:
    lignes = correction.get("reponses") or []
    exige(len(lignes) == len(questions),
          f"{len(lignes)} réponse(s) corrigée(s) pour {len(questions)} question(s)")

    for ligne in lignes:
        n = ligne.get("numero")
        exige(ligne.get("statut") in ("acquis", "partiel", "a_revoir"),
              f"Q{n} n'a pas de statut lisible")
        if ligne.get("statut") != "acquis":
            exige(bool((ligne.get("ou_dans_ton_cours") or "").strip()),
                  f"Q{n} est à revoir mais ne dit pas où relire")

    # On a répondu n'importe quoi à ces questions-là : si elles ressortent
    # « acquis », la correction ne corrige rien.
    for ligne in lignes:
        if ligne.get("numero") in fausses:
            exige(ligne.get("statut") != "acquis",
                  f"Q{ligne['numero']} : réponse absurde jugée acquise")

    fragiles = correction.get("notions_fragiles") or []
    exige(len(fragiles) >= 1, "aucune notion fragile alors que des réponses sont fausses")
    for f in fragiles:
        exige(bool((f.get("pourquoi") or "").strip()),
              f"la notion « {f.get('notion', '?')} » ne dit pas pourquoi elle est fragile")

    trouve = NOTE.search(texte_de(correction))
    exige(not trouve, f"la correction met une note : « {trouve.group(0) if trouve else ''} »")


def verifier_analyse(analyse: dict, max_doutes: int) -> None:
    photos = analyse.get("photos") or []
    exige(bool(photos), "aucune photo jugée")
    chapitres = [c for c in (analyse.get("chapitres") or []) if c.get("transcription")]
    exige(bool(chapitres), "aucun chapitre transcrit")
    exige(sum(len(c.get("notions") or []) for c in chapitres) >= 3,
          "moins de 3 notions dégagées de tout le cours")
    doutes = analyse.get("doutes") or []
    exige(len(doutes) <= max_doutes,
          f"{len(doutes)} doutes pour un plafond de {max_doutes}")
    for d in doutes:
        exige(bool(d.get("lu")) and bool(d.get("pourquoi")), "un doute est incomplet")


# --- Le passage -------------------------------------------------------------

def main() -> int:
    analyseur = argparse.ArgumentParser(
        description="Vérifie que rien n'est cassé dans ce que le modèle produit.")
    analyseur.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"],
                           help="l'effort de tous les appels, pour répondre à "
                                "« est-ce que ce réglage casse quelque chose ? »")
    analyseur.add_argument("--modele", metavar="NOM", help="le modèle de tous les appels")
    analyseur.add_argument("--cas", metavar="ID", action="append", default=[],
                           help="ne lancer que ce cas ; répétable")
    arguments = analyseur.parse_args()

    # Posé avant l'import : config lit l'environnement au chargement.
    # Il n'y a pas de variable globale pour l'effort : « EFFORT_PAR_DEFAUT » est
    # une constante, et seul « CB_EFFORT_<ACTION> » se pose par l'environnement.
    if arguments.effort:
        for action in ("ANALYSE", "FICHE_GENERALE", "FICHE_CIBLEE", "CONTROLE", "CORRECTION"):
            os.environ[f"CB_EFFORT_{action}"] = arguments.effort
    if arguments.modele:
        os.environ["CB_MODEL"] = arguments.modele
        os.environ["CB_MODEL_TEXTE"] = arguments.modele

    from app import config, formats, llm
    from essai import chapitre_du_corpus

    if config.DEMO_MODE:
        print("ANTHROPIC_API_KEY n'est pas posée : la garde n'aurait rien à juger.")
        return 2

    cas = [c for c in CAS if not arguments.cas or c["id"] in arguments.cas]
    if not cas:
        print(f"aucun cas ne correspond. Connus : {', '.join(c['id'] for c in CAS)}")
        return 2

    total = 0.0
    echecs: list[tuple[str, str]] = []
    depart = time.time()

    print(f"La garde · {len(cas)} cas · "
          f"effort {arguments.effort or config.EFFORT_PAR_DEFAUT} · "
          f"modèle {arguments.modele or config.MODELE_TEXTE}\n")

    for c in cas:
        chapitre = chapitre_du_corpus(c["corpus"])
        niveau = formats.nom_niveau(chapitre["niveau"])
        fmt = formats.format_matiere(chapitre["matiere"])
        chapitres = [chapitre]
        cout_cas = 0.0

        def appel(nom, fonction):
            nonlocal cout_cas
            donnees, usage = fonction()
            prix, _ = config.prix_du_modele(usage.get("modele", ""))
            cout = (usage.get("tokens_entree", 0) * prix["entree"]
                    + usage.get("tokens_sortie", 0) * prix["sortie"]
                    + usage.get("cache_ecriture", 0) * prix["cache_ecriture"]
                    + usage.get("cache_lecture", 0) * prix["cache_lecture"]) / 1_000_000
            cout_cas += cout
            if cout > PLAFOND_ETAPE:
                echecs.append((c["id"], f"{nom} coûte {cout:.4f} $ "
                                        f"(plafond {PLAFOND_ETAPE:.2f} $)"))
            return donnees

        def tenir(quoi, verification):
            try:
                verification()
                print(f"  ✓ {quoi}")
            except Manque as manque:
                print(f"  ✗ {quoi} — {manque}")
                echecs.append((c["id"], f"{quoi} : {manque}"))

        print(f"{c['id']} · {chapitre['titre']}")

        fiche = appel("la fiche", lambda: llm.fiche_generale(chapitres, niveau))
        tenir("fiche", lambda: verifier_fiche(fiche, chapitre["notions"]))

        controle = appel("le contrôle", lambda: llm.generer_controle(
            chapitres, niveau, fmt["nom"], fmt["structure"], fmt["duree_minutes"]))
        tenir("contrôle blanc",
              lambda: verifier_controle(controle, chapitre["notions"], fmt["duree_minutes"]))

        if c["corriger"] and (controle.get("questions") or []):
            questions = controle["questions"]
            # Une copie mi-juste mi-absurde : la correction doit voir les deux.
            # Répondre à côté est le seul moyen de vérifier qu'elle corrige
            # vraiment au lieu de valider tout ce qu'on lui donne.
            fausses = {q["numero"] for q in questions[:2]}
            reponses = {q["numero"]: ("Le poisson rouge de la Renaissance."
                                      if q["numero"] in fausses
                                      else (q.get("points_attendus") or [""])[0])
                        for q in questions}
            correction = appel("la correction", lambda: llm.corriger(
                chapitres, niveau, questions, reponses, set()))
            tenir("correction",
                  lambda: verifier_correction(correction, questions, fausses))

        total += cout_cas
        print(f"  {cout_cas:.4f} $\n")

    # La lecture des photos, si on lui en a donné.
    dossier = os.environ.get("CB_GARDE_PHOTOS", "")
    if dossier and Path(dossier).is_dir():
        images = []
        for chemin in sorted(Path(dossier).iterdir()):
            if chemin.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                mime = "image/png" if chemin.suffix.lower() == ".png" else "image/jpeg"
                images.append((mime, chemin.read_bytes()))
        if images:
            print(f"photos · {len(images)} image(s) de {dossier}")
            analyse, usage = llm.analyser_photos(images, "3e", "")
            prix, _ = config.prix_du_modele(usage.get("modele", ""))
            cout = (usage.get("tokens_entree", 0) * prix["entree"]
                    + usage.get("tokens_sortie", 0) * prix["sortie"]) / 1_000_000
            total += cout
            try:
                verifier_analyse(analyse, config.MAX_DOUTES)
                print("  ✓ lecture des photos")
            except Manque as manque:
                print(f"  ✗ lecture des photos — {manque}")
                echecs.append(("photos", str(manque)))
            print(f"  {cout:.4f} $\n")
    else:
        print("photos · pas de cas (pose CB_GARDE_PHOTOS sur un dossier d'images)\n")

    if total > PLAFOND_PASSAGE:
        echecs.append(("passage", f"{total:.4f} $ pour un plafond de {PLAFOND_PASSAGE:.2f} $"))

    print(f"{total:.4f} $ · {time.time() - depart:.0f} s")
    if echecs:
        print(f"\nÉCHEC — {len(echecs)} chose(s) cassée(s) :")
        for cas_id, quoi in echecs:
            print(f"  · {cas_id} : {quoi}")
        return 1
    print("\nRien n'est cassé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
