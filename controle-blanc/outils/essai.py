#!/usr/bin/env python3
"""Banc d’essai : la chaîne complète sur de vraies photos, en une commande.

À quoi ça sert : juger ce que l’outil produit réellement — la lecture d’une
écriture manuscrite, la fiche, les questions, la correction — et voir ce que ça
coûte, avant de le mettre entre les mains d’élèves.

    python3 outils/essai.py photos/*.jpg --niveau 3e --matiere histoire-geographie

Sans photos sous la main, on part d’un chapitre du corpus, qui tient lieu de
transcription — c’est ce qui permet de travailler la qualité des fiches et des
questions en attendant de vraies photos d’élèves :

    python3 outils/essai.py --corpus liste
    python3 outils/essai.py --corpus revolution-neolithique --niveau 6e \
        --matiere histoire-geographie

Sans ANTHROPIC_API_KEY, la commande refuse de partir plutôt que de produire
silencieusement les contenus d’exemple : un banc d’essai qui ne teste rien est
pire que pas de banc d’essai.

Ce qui sort :
  - le déroulé à l’écran, étape par étape, avec le coût de chacune ;
  - un rapport HTML relisible et partageable ;
  - les réponses brutes du modèle en JSON, pour inspecter ce qui a été produit.

Les réponses de l’élève : saisies au clavier par défaut, ou lues dans un fichier
(--reponses), ou laissées vides (--vide) pour voir la correction la plus sévère.
"""

from __future__ import annotations

import argparse
import html
import io
import json
import mimetypes
import os
import sys
import time
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

COTE_MAX = 1568  # au-delà, le modèle redimensionne de toute façon


# --- Affichage --------------------------------------------------------------

class Terminal:
    GRAS = "\033[1m"
    BLEU = "\033[34m"
    ROUGE = "\033[31m"
    VERT = "\033[32m"
    GRIS = "\033[90m"
    FIN = "\033[0m"

    def __init__(self) -> None:
        self.couleur = sys.stdout.isatty()

    def _c(self, code: str, texte: str) -> str:
        return f"{code}{texte}{self.FIN}" if self.couleur else texte

    def titre(self, texte: str) -> None:
        print(f"\n{self._c(self.GRAS, texte)}")
        print(self._c(self.GRIS, "─" * min(len(texte), 64)))

    def info(self, texte: str) -> None:
        print(self._c(self.GRIS, texte))

    def bien(self, texte: str) -> None:
        print(self._c(self.VERT, texte))

    def alerte(self, texte: str) -> None:
        print(self._c(self.ROUGE, texte))

    def cle(self, cle: str, valeur: str) -> None:
        print(f"  {self._c(self.BLEU, cle)} {valeur}")


T = Terminal()


# --- Images -----------------------------------------------------------------

def charger_images(chemins: list[str]) -> list[tuple[str, bytes]]:
    """Lit et réduit les photos, comme le fait le navigateur avant l’envoi."""
    from PIL import Image

    images: list[tuple[str, bytes]] = []
    for chemin in chemins:
        fichier = Path(chemin)
        if not fichier.is_file():
            raise SystemExit(f"introuvable : {fichier}")

        image = Image.open(fichier)
        image = image.convert("RGB")
        avant = image.size
        echelle = min(1.0, COTE_MAX / max(image.size))
        if echelle < 1.0:
            image = image.resize(
                (round(image.width * echelle), round(image.height * echelle)),
                Image.LANCZOS,
            )
        tampon = io.BytesIO()
        image.save(tampon, format="JPEG", quality=82)
        octets = tampon.getvalue()
        images.append(("image/jpeg", octets))
        T.info(f"  {fichier.name} — {avant[0]}×{avant[1]} → {image.width}×{image.height}, "
               f"{len(octets) // 1024} Ko")
    return images


# --- Réponses de l’élève ----------------------------------------------------

def lire_reponses(questions: list[dict], source: str | None, vide: bool) -> dict[int, str]:
    if vide:
        return {q["numero"]: "" for q in questions}

    if source:
        # Format attendu : « 1: ma réponse », une question par bloc.
        texte = Path(source).read_text(encoding="utf-8")
        reponses: dict[int, str] = {}
        courante = None
        for ligne in texte.splitlines():
            debut = ligne.split(":", 1)
            if len(debut) == 2 and debut[0].strip().isdigit():
                courante = int(debut[0].strip())
                reponses[courante] = debut[1].strip()
            elif courante is not None:
                reponses[courante] = (reponses[courante] + "\n" + ligne).strip()
        return {q["numero"]: reponses.get(q["numero"], "") for q in questions}

    if not sys.stdin.isatty():
        T.info("  (entrée non interactive : réponses laissées vides)")
        return {q["numero"]: "" for q in questions}

    reponses = {}
    print()
    T.info("Réponds comme un élève. Ligne vide seule pour passer à la suivante.")
    for question in questions:
        print()
        T.cle(f"Question {question['numero']}", question["partie"])
        if question.get("document"):
            print(f"  {T._c(T.GRIS, question['document'][:400])}")
        print(f"  {question['enonce']}")
        lignes = []
        while True:
            try:
                ligne = input("  > ")
            except EOFError:
                break
            if not ligne.strip():
                break
            lignes.append(ligne)
        reponses[question["numero"]] = "\n".join(lignes)
    return reponses


# --- Rapport ----------------------------------------------------------------

def rapport_html(essai: dict, chemin: Path) -> None:
    e = html.escape

    def liste(elements: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{e(x)}</li>" for x in elements) + "</ul>"

    chapitres = "".join(
        f"<div class='c'><h3>{e(c['titre'])}</h3>{liste(c.get('notions', []))}"
        f"<details><summary>Transcription ({len(c.get('transcription', ''))} caractères)</summary>"
        f"<pre>{e(c.get('transcription', ''))}</pre></details></div>"
        for c in essai["analyse"]["chapitres"]
    )

    photos = "".join(
        f"<li class='{'ko' if not p['lisible'] else 'ok'}'>Photo {p['index'] + 1} — "
        f"{'illisible : ' + e(p['remarque']) if not p['lisible'] else 'lisible'}"
        f"{' · ' + e(p['remarque']) if p['lisible'] and p.get('remarque') else ''}</li>"
        for p in essai["analyse"]["photos"]
    )

    def bloc_fiche(fiche: dict) -> str:
        sections = "".join(
            f"<div class='c'><h3>{e(s['titre'])}</h3>{liste(s.get('points', []))}"
            f"<p class='r'>{e(s.get('a_retenir', ''))}</p></div>"
            for s in fiche.get("sections", [])
        )
        defs = "".join(
            f"<p><b>{e(d['terme'])}</b> — {e(d['definition'])}</p>"
            for d in fiche.get("definitions", [])
        )
        return f"<h2>{e(fiche.get('titre', ''))}</h2>{sections}<div class='c'>{defs}" \
               f"{liste(fiche.get('pieges', []))}</div>"

    def bloc_controle(controle: dict) -> str:
        questions = "".join(
            f"<div class='c'><p class='p'>{e(q.get('partie', ''))} · {e(q.get('notion', ''))}"
            f" · {q.get('duree_minutes', 0)} min</p>"
            + (f"<blockquote>{e(q['document'])}</blockquote>" if q.get("document") else "")
            + f"<p><b>{q['numero']}. {e(q['enonce'])}</b></p>"
            + f"<details><summary>Corrigé attendu</summary>{liste(q.get('points_attendus', []))}"
            + f"<p class='r'>Renvoi au cours : {e(q.get('ou_dans_le_cours', ''))}</p></details></div>"
            for q in controle["questions"]
        )
        return f"<h2>{e(controle.get('titre', ''))}</h2>" \
               f"<p class='n'>{e(controle.get('consigne_generale', ''))}</p>{questions}"

    def bloc_correction(correction: dict, reponses: dict) -> str:
        lignes = "".join(
            f"<div class='c s-{r['statut']}'><p class='p'>{r['statut'].replace('_', ' ')}</p>"
            f"<p><b>{r['numero']}.</b> {e(r.get('enonce', ''))}</p>"
            f"<p class='rep'>Réponse donnée : {e(reponses.get(r['numero'], '') or '(vide)')}</p>"
            + (f"<p>{e(r['ce_qui_va'])}</p>" if r.get("ce_qui_va") else "")
            + (liste(r["ce_qui_manquait"]) if r.get("ce_qui_manquait") else "")
            + f"<p class='r'>Où le relire : {e(r.get('ou_dans_ton_cours', ''))}</p></div>"
            for r in correction["reponses"]
        )
        fragiles = "".join(
            f"<li><b>{e(n['notion'])}</b> — {e(n.get('pourquoi', ''))}</li>"
            for n in correction.get("notions_fragiles", [])
        )
        return (f"<h2>Correction</h2><p class='n'>{e(correction.get('mot_de_fin', ''))}</p>"
                f"<div class='c'><h3>Notions fragiles</h3><ol>{fragiles}</ol></div>{lignes}")

    couts = "".join(
        f"<tr><td>{e(c['etape'])}</td><td>{c['secondes']:.1f} s</td>"
        f"<td>{c['tokens_entree']:,}</td><td>{c['tokens_sortie']:,}</td>"
        f"<td>{c['cout_usd']:.4f} $</td></tr>".replace(",", " ")
        for c in essai["couts"]
    )

    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Essai — {e(essai['matiere'])} {e(essai['niveau'])}</title>
<style>
 :root {{ --encre:#16203a; --doux:#5b6480; --papier:#f6f7fa; --carte:#fff;
          --trait:#dde2ec; --bleu:#2f4fd8; --bleu-doux:#e9edff; --rouge:#cf3a2c;
          --vert:#1c7a58; --ambre:#9c6410; }}
 @media (prefers-color-scheme: dark) {{ :root {{
   --encre:#e9edf8; --doux:#949db8; --papier:#0e1220; --carte:#171d2f;
   --trait:#262f48; --bleu:#8aa0ff; --bleu-doux:#1a2244; --rouge:#f0796a;
   --vert:#55bd90; --ambre:#d7a548; }} }}
 body {{ font:16px/1.6 ui-sans-serif,system-ui,sans-serif; margin:0;
         padding:32px 20px 80px; background:var(--papier); color:var(--encre); }}
 main {{ max-width:760px; margin:0 auto; }}
 h1 {{ font-size:1.7rem; margin:0 0 6px; }}
 h2 {{ font-size:1.15rem; margin:44px 0 14px; padding-bottom:8px;
       border-bottom:1px solid var(--trait); }}
 h3 {{ font-size:1rem; margin:0 0 8px; }}
 .c {{ background:var(--carte); border:1px solid var(--trait); border-radius:10px;
       padding:16px; margin-bottom:10px; }}
 .c.s-acquis {{ border-left:3px solid var(--vert); }}
 .c.s-partiel {{ border-left:3px solid var(--ambre); }}
 .c.s-a_revoir {{ border-left:3px solid var(--rouge); }}
 .p {{ font-size:.72rem; letter-spacing:.1em; text-transform:uppercase;
       color:var(--bleu); margin:0 0 8px; font-weight:600; }}
 .n {{ color:var(--doux); }}
 .r {{ background:var(--bleu-doux); border-radius:6px; padding:9px 11px;
       font-size:.9rem; margin:10px 0 0; }}
 .rep {{ font-style:italic; color:var(--doux); white-space:pre-wrap; }}
 .ok {{ color:var(--vert); }} .ko {{ color:var(--rouge); }}
 ul,ol {{ margin:0; padding-left:20px; }} li {{ margin-bottom:5px; }}
 pre {{ white-space:pre-wrap; font-size:.85rem; background:var(--papier);
        padding:12px; border-radius:6px; overflow-x:auto; }}
 blockquote {{ margin:0 0 10px; padding:12px; background:var(--papier);
               border-left:3px solid var(--trait); white-space:pre-wrap;
               font-size:.92rem; }}
 summary {{ cursor:pointer; color:var(--bleu); font-size:.88rem; padding:6px 0; }}
 table {{ width:100%; border-collapse:collapse; font-size:.9rem; }}
 th,td {{ text-align:right; padding:8px; border-bottom:1px solid var(--trait);
          font-variant-numeric:tabular-nums; }}
 th:first-child,td:first-child {{ text-align:left; }}
</style></head><body><main>
<h1>Essai de la chaîne complète</h1>
<p class="n">{e(essai['matiere'])} · {e(essai['niveau'])} · {e(essai['horodatage'])}
 · modèle {e(essai['modele'])}</p>

<h2>Lecture des photos</h2>
<ul>{photos}</ul>
<p class="n">Matière détectée : {e(essai['analyse'].get('matiere_detectee') or '—')}</p>
{chapitres}

{bloc_fiche(essai['fiche_generale'])}
{bloc_controle(essai['controle'])}
{bloc_correction(essai['correction'], essai['reponses'])}
{bloc_fiche(essai['fiche_ciblee']) if essai.get('fiche_ciblee') else ''}
{bloc_controle(essai['second_controle']) if essai.get('second_controle') else ''}

<h2>Coût</h2>
<table><tr><th>Étape</th><th>Durée</th><th>Entrée</th><th>Sortie</th><th>Coût</th></tr>
{couts}
<tr><td><b>Total</b></td><td><b>{essai['secondes_total']:.1f} s</b></td><td></td><td></td>
<td><b>{essai['cout_total']:.4f} $</b></td></tr></table>
<p class="n">C’est le coût d’un élève qui va au bout du parcours une fois.</p>
</main></body></html>"""
    chemin.write_text(page, encoding="utf-8")


# --- Programme --------------------------------------------------------------

def corpus_disponible() -> list[dict]:
    """Le programme d’histoire de 6e, qui tient lieu de photos tant qu’on n’en a pas."""
    import importlib.util

    chemin = RACINE / "outils" / "corpus" / "histoire-6e.py"
    spec = importlib.util.spec_from_file_location("corpus_histoire_6e", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CHAPITRES


def chapitre_du_corpus(identifiant: str) -> dict:
    for chapitre in corpus_disponible():
        if chapitre["id"] == identifiant:
            return {
                "titre": chapitre["titre"],
                "notions": chapitre["notions"],
                "transcription": chapitre["transcription"],
                "photos": [],
            }
    connus = ", ".join(c["id"] for c in corpus_disponible())
    raise SystemExit(f"chapitre inconnu : {identifiant}\nDisponibles : {connus}")


def main() -> int:
    analyseur = argparse.ArgumentParser(
        description="Passe de vraies photos de cours dans toute la chaîne."
    )
    analyseur.add_argument("photos", nargs="*", help="les photos du cours")
    analyseur.add_argument("--corpus", metavar="CHAPITRE",
                           help="partir d’un chapitre du corpus au lieu de photos "
                                "(« liste » pour voir les chapitres disponibles)")
    analyseur.add_argument("--niveau", default="3e")
    analyseur.add_argument("--matiere", default="autre")
    analyseur.add_argument("--reponses", help="fichier de réponses (« 1: … » par bloc)")
    analyseur.add_argument("--vide", action="store_true",
                           help="laisser toutes les réponses vides")
    analyseur.add_argument("--sortie", default=None,
                           help="dossier des résultats (défaut : essais/AAAA-MM-JJ-hhmm)")
    analyseur.add_argument("--sans-second-tour", action="store_true",
                           help="s’arrêter après la correction")
    arguments = analyseur.parse_args()

    if arguments.corpus == "liste":
        for chapitre in corpus_disponible():
            print(f"  {chapitre['id']:28} thème {chapitre['theme']} — {chapitre['titre']}")
        return 0

    if bool(arguments.photos) == bool(arguments.corpus):
        analyseur.error("donne soit des photos, soit --corpus, pas les deux ni aucun")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        T.alerte("ANTHROPIC_API_KEY n’est pas définie.")
        T.info("Ce banc d’essai appelle le vrai modèle : sans clé il ne testerait rien.")
        T.info("  export ANTHROPIC_API_KEY=sk-ant-…")
        return 2
    os.environ["CB_DEMO_MODE"] = "0"

    # Importé seulement maintenant : app.config lit l’environnement à l’import,
    # et CB_DEMO_MODE vient d’être fixé.
    sys.path.insert(0, str(RACINE))
    from app import config, formats, llm

    dossier = Path(arguments.sortie) if arguments.sortie else (
        RACINE / "essais" / datetime.now().strftime("%Y-%m-%d-%H%M")
    )
    dossier.mkdir(parents=True, exist_ok=True)

    fmt = formats.format_matiere(arguments.matiere)
    niveau = formats.nom_niveau(arguments.niveau)
    couts: list[dict] = []
    depart = time.monotonic()

    def etape(nom: str, fonction):
        T.titre(nom)
        debut = time.monotonic()
        resultat, usage = fonction()
        secondes = time.monotonic() - debut
        p = config.PRIX_USD_PAR_MTOK
        cout = (
            usage.get("tokens_entree", 0) * p["entree"]
            + usage.get("tokens_sortie", 0) * p["sortie"]
            + usage.get("cache_ecriture", 0) * p["cache_ecriture"]
            + usage.get("cache_lecture", 0) * p["cache_lecture"]
        ) / 1_000_000
        couts.append({
            "etape": nom, "secondes": secondes, "cout_usd": cout,
            "tokens_entree": usage.get("tokens_entree", 0),
            "tokens_sortie": usage.get("tokens_sortie", 0),
            "cache_lecture": usage.get("cache_lecture", 0),
        })
        T.info(f"  {secondes:.1f} s · {usage.get('tokens_entree', 0)} tokens entrée "
               f"(dont {usage.get('cache_lecture', 0)} en cache) · "
               f"{usage.get('tokens_sortie', 0)} sortie · {cout:.4f} $")
        return resultat

    # 1. Le cours : des photos à lire, ou un chapitre du corpus déjà transcrit.
    if arguments.corpus:
        T.titre("Corpus")
        chapitre = chapitre_du_corpus(arguments.corpus)
        T.info(f"  {chapitre['titre']} — {len(chapitre['transcription'])} caractères, "
               f"pas d’appel au modèle pour cette étape")
        analyse = {"photos": [], "matiere_detectee": "", "chapitres": [chapitre]}
    else:
        T.titre("Photos")
        images = charger_images(arguments.photos)
        analyse = etape("Lecture du cours",
                        lambda: llm.analyser_photos(images, niveau, fmt["nom"]))

    for photo in analyse["photos"]:
        if photo["lisible"]:
            T.bien(f"  photo {photo['index'] + 1} : lisible"
                   + (f" — {photo['remarque']}" if photo.get("remarque") else ""))
        else:
            T.alerte(f"  photo {photo['index'] + 1} : ILLISIBLE — {photo['remarque']}")

    chapitres = analyse["chapitres"]
    if not chapitres:
        T.alerte("Aucun chapitre lisible. On s’arrête là.")
        return 1
    for chapitre in chapitres:
        T.cle(chapitre["titre"], f"{len(chapitre.get('notions', []))} notions, "
                                 f"{len(chapitre.get('transcription', ''))} caractères")
        for notion in chapitre.get("notions", []):
            print(f"      · {notion}")

    # 2. La fiche générale
    fiche = etape("Fiche générale", lambda: llm.fiche_generale(chapitres, niveau))
    for section in fiche.get("sections", []):
        T.cle(section["titre"], section.get("a_retenir", ""))

    # 3. Le contrôle blanc
    controle = etape("Contrôle blanc", lambda: llm.generer_controle(
        chapitres, niveau, fmt["nom"], fmt["structure"], fmt["duree_minutes"]))
    for question in controle["questions"]:
        T.cle(f"Q{question['numero']}",
              f"{question['enonce'][:96]}… ({question['duree_minutes']} min, {question['notion']})")

    # 4. Les réponses, puis la correction
    reponses = lire_reponses(controle["questions"], arguments.reponses, arguments.vide)
    correction = etape("Correction", lambda: llm.corriger(
        chapitres, niveau, controle["questions"], reponses, set()))
    for ligne in correction["reponses"]:
        marque = {"acquis": T.bien, "partiel": T.info, "a_revoir": T.alerte}[ligne["statut"]]
        marque(f"  Q{ligne['numero']} — {ligne['statut']} — {ligne['ou_dans_ton_cours'][:80]}")
    T.titre("Notions fragiles")
    for notion in correction.get("notions_fragiles", []):
        T.cle(notion["notion"], notion.get("pourquoi", ""))

    fiche_ciblee = second = None
    if not arguments.sans_second_tour and correction.get("notions_fragiles"):
        fiche_ciblee = etape("Fiche ciblée", lambda: llm.fiche_ciblee(
            chapitres, niveau, correction["notions_fragiles"]))
        second = etape("Second contrôle", lambda: llm.generer_controle(
            chapitres, niveau, fmt["nom"], fmt["structure"], fmt["duree_minutes"],
            notions_ciblees=[n["notion"] for n in correction["notions_fragiles"]],
            enonces_deja_poses=[q["enonce"] for q in controle["questions"]]))
        repetes = ({q["enonce"] for q in second["questions"]}
                   & {q["enonce"] for q in controle["questions"]})
        if repetes:
            T.alerte(f"  {len(repetes)} question(s) reposée(s) à l’identique")
        else:
            T.bien("  aucune question reposée à l’identique")

    essai = {
        "horodatage": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "modele": config.MODEL,
        "niveau": formats.nom_niveau(arguments.niveau),
        "matiere": fmt["nom"],
        "analyse": analyse,
        "source": f"corpus : {arguments.corpus}" if arguments.corpus else
                  f"{len(arguments.photos)} photo(s)",
        "fiche_generale": fiche,
        "controle": controle,
        "reponses": reponses,
        "correction": correction,
        "fiche_ciblee": fiche_ciblee,
        "second_controle": second,
        "couts": couts,
        "cout_total": sum(c["cout_usd"] for c in couts),
        "secondes_total": time.monotonic() - depart,
    }

    (dossier / "essai.json").write_text(
        json.dumps(essai, ensure_ascii=False, indent=2), encoding="utf-8")
    rapport_html(essai, dossier / "rapport.html")

    T.titre("Résultat")
    T.cle("Rapport", str(dossier / "rapport.html"))
    T.cle("Données brutes", str(dossier / "essai.json"))
    T.cle("Coût du parcours", f"{essai['cout_total']:.4f} $ pour un élève")
    T.cle("Durée", f"{essai['secondes_total']:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
