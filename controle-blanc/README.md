# Contrôle blanc

> Passe le contrôle avant le contrôle.

Un site web mobile où un élève photographie son cours, passe un **contrôle blanc au
format réel de la matière**, obtient une correction commentée qui renvoie à son propre
cours, puis des fiches ciblées sur ce qu'il a raté.

On ne vend pas des fiches de révision. On vend le fait de s'être déjà trompé une fois,
sur ses notions à lui, avant le jour J.

---

## Le parcours, tel qu'il est codé

| # | Étape | Où c'est |
|---|-------|----------|
| 1 | Photographier le cours (plusieurs pages, écriture manuscrite, ajout ultérieur possible) | `POST /api/analyse` |
| 2 | Confirmer le périmètre : « j'ai repéré N chapitres, c'est bien tout ? » | écran `ecran-perimetre` |
| 3 | Deux boutons de poids strictement égal : **je révise d'abord** / **je me teste tout de suite** | écran `ecran-carrefour` |
| 4 | Le contrôle blanc : format réel, chronomètre, pas de retour en arrière | `POST /api/controle` |
| 5 | La correction commentée : ce qui manquait, et **où c'est dans son cours à lui** | `POST /api/correction` |
| 6 | La fiche ciblée, uniquement sur les notions ratées | `POST /api/fiche/ciblee` |
| 7 | Second contrôle, questions différentes, mêmes notions | `POST /api/controle` avec `notions_ciblees` |

Les deux chemins de l'étape 3 mènent tous les deux au contrôle blanc. **L'ordre des deux
boutons est tiré au sort par session** : sans ça, on mesurerait la position du bouton,
pas la préférence de l'élève.

Deux types de fiches, à ne pas confondre :

* **fiche générale** (étape 3) — tout le chapitre, pour relire avant de se tester ;
* **fiche ciblée** (étape 6) — uniquement les notions ratées, cinq minutes de lecture.
  C'est celle qui a le plus de valeur.

---

## Les contraintes v1, et comment elles sont tenues

| Contrainte | Comment |
|---|---|
| Une seule page, mobile d'abord | `web/index.html` — écrans successifs, une seule colonne, cibles tactiles ≥ 48 px |
| Pas de compte, pas de mot de passe | Session = un identifiant aléatoire. Aucune donnée personnelle collectée |
| Stockage local | `localStorage` : cours, réponses, fiches. Le serveur ne stocke que des compteurs |
| Reprise de session | Lien `?s=…` mis en avant sur l'écran de session, avec bouton « copier » |
| Pas de note prédictive | Statuts qualitatifs (`acquis` / `partiel` / `à revoir`) + 3 notions fragiles. Aucun score, aucun `/20`, aucun pourcentage — vérifié par un test |
| « Cette question me semble fausse » | Sur chaque question, pendant le contrôle **et** dans la correction. Remonte au tableau de bord ; la question ne pénalise pas l'élève |
| Coût par usage | Quotas côté serveur, par jour et par session (`app/config.py`) |

### Les photos ne sont pas conservées

Elles transitent en mémoire jusqu'au modèle, puis disparaissent. Ce qui est gardé, c'est
la transcription du cours — dans le navigateur de l'élève, pas sur le serveur. Côté
serveur ne subsistent qu'un identifiant aléatoire, des compteurs d'usage, des événements
anonymes, et le corrigé du contrôle en cours (purgé au bout de 30 jours).

Le corrigé reste côté serveur pour une raison simple : envoyé avec les questions, il
serait lisible dans les outils de développement avant même que l'élève ait répondu.

---

## Démarrer

```bash
cd controle-blanc
pip install -r requirements.txt
./lancer.sh                      # http://localhost:8000
```

Sans `ANTHROPIC_API_KEY`, l'application démarre en **mode démonstration** : tout le
parcours est cliquable avec un chapitre d'histoire de 3e en dur, sans un seul appel
facturé. C'est le mode à utiliser pour montrer l'outil avant de dépenser.

En mode réel :

```bash
cp .env.example .env             # y mettre ANTHROPIC_API_KEY et CB_ADMIN_TOKEN
./lancer.sh
```

Les tests tournent hors ligne, sans clé :

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests -q
```

---

## Mettre en ligne pour le test

L'application est un serveur Python unique qui sert aussi la page. N'importe quel
hébergeur qui exécute un processus web convient (Railway, Render, Fly, Scalingo…) :

```
Commande : uvicorn app.main:app --host 0.0.0.0 --port $PORT
Racine    : controle-blanc/
```

Variables à définir : `ANTHROPIC_API_KEY`, `CB_ADMIN_TOKEN`, `CB_PUBLIC_BASE_URL`.
`CB_DB_PATH` doit pointer vers un disque persistant, sinon les quotas et les mesures
repartent de zéro à chaque redéploiement.

---

## Ce que ça coûte, et ce qui le borne

Un parcours complet, c'est quatre à cinq appels au modèle : analyse des photos, fiche,
contrôle, correction, fiche ciblée. Le poste le plus lourd est l'analyse des photos.

Trois choses réduisent la facture :

* les photos sont **redimensionnées dans le navigateur** à 1568 px avant l'envoi ;
* le cours de l'élève est mis en **cache de prompt** (1 h) : il est renvoyé à chaque
  appel de la séance, c'est le plus gros bloc et il ne bouge pas ;
* les **quotas** plafonnent par jour et par session.

Quotas par défaut, tous réglables par variable d'environnement :

| Action | Par jour | Par session |
|---|---|---|
| Analyse de photos | 4 | 20 |
| Fiche générale | 3 | 12 |
| Contrôle blanc | 3 | 12 |
| Fiche ciblée | 5 | 20 |

La correction n'est pas décomptée : elle fait partie du contrôle déjà compté. Faire
payer un contrôle sans résultat n'aurait pas de sens.

Quand un élève atteint la limite du jour, le message le renvoie à demain — ce qui sert
aussi la métrique qui compte.

---

## Mesurer le test

`GET /admin/metriques?token=…` (404 si `CB_ADMIN_TOKEN` n'est pas défini).

La page affiche, dans cet ordre :

1. combien ont ouvert le lien ;
2. combien ont généré une 2e fiche sans qu'on le leur demande ;
3. **combien sont revenus le lendemain** — mise en avant, c'est la seule qui décide ;

puis la répartition « je révise d'abord » / « je me teste tout de suite », **avec le taux
de retour de chacun des deux chemins**. C'est cette ligne qui dira s'il faut garder les
deux entrées ou n'en garder qu'une.

Le coût réel par session y figure aussi, ainsi que les questions signalées par les élèves
— à relire avant chaque itération sur les prompts.

---

## Hors périmètre, volontairement

Comptes utilisateurs, paiement, sections collège/lycée/fac séparées, intégration des
programmes officiels, rappels par notification. Le sélecteur de niveau existe dans le
code (`app/formats.py`) mais un seul niveau est testé.

L'intégration des programmes officiels (Bulletin officiel, Licence Ouverte d'Etalab) est
prévue plus tard, pour calibrer la difficulté et signaler les trous du cours photographié
— **formulé comme un doute, jamais comme une affirmation**. Rien n'est construit pour ça
aujourd'hui.

---

## À caler avant de lancer le test réel

Trois choses conditionnent la qualité des questions générées, et aucune ne se décide
depuis le code :

* le niveau exact des classes du professeur d'EPS ;
* la matière et la date d'un contrôle réel à venir ;
* **un ancien contrôle du même professeur, photographié** — c'est ce qui permettra de
  caler `app/formats.py` sur le vrai format plutôt que sur un format type.

Le catalogue de formats de `app/formats.py` est écrit pour être corrigé à la main : une
matière = une entrée, la description passe telle quelle dans le prompt.

---

## Organisation du code

```
controle-blanc/
├── app/
│   ├── main.py       routes ; le corrigé est retiré de ce qui part au navigateur
│   ├── llm.py        les appels au modèle, tous au même endroit
│   ├── prompts.py    les prompts en français et les schémas de sortie
│   ├── formats.py    le format réel d'un contrôle, par matière
│   ├── store.py      SQLite : compteurs, événements, corrigés
│   ├── demo.py       contenus d'exemple pour le mode démonstration
│   └── config.py     tout ce qui se règle par variable d'environnement
├── web/              la page unique : index.html, app.js, styles.css
└── tests/            le parcours complet, hors ligne
```
