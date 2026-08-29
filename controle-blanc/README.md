# Repère

> Passe le contrôle avant le contrôle.

Un site web mobile où un élève photographie son cours, passe un **contrôle blanc au
format réel de la matière**, obtient une correction commentée qui renvoie à son propre
cours, puis des fiches ciblées sur ce qu'il a raté.

On ne vend pas des fiches de révision. On vend le fait de s'être déjà trompé une fois,
sur ses notions à lui, avant le jour J.

**Le nom.** Un repère, c'est ce que la correction rend : pas une note — le cahier des
charges les interdit — mais l'endroit de son propre cours où aller relire. Le logo le
dessine : un filet de marge, trois lignes, et celle qu'on est venu retrouver. « Contrôle
blanc » reste le nom de l'épreuve, pas celui du site.

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
| Compte par adresse mail et mot de passe | Mot de passe haché par scrypt ; code de réinitialisation et jeton de connexion hachés eux aussi (`app/store.py`) |
| Stockage local | `localStorage` : cours, réponses, fiches. Le serveur ne stocke que des compteurs |
| Reprise de session | Lien `?s=…` mis en avant sur l'écran de session, avec bouton « copier » |
| Pas de note prédictive | Statuts qualitatifs (`acquis` / `partiel` / `à revoir`) + 3 notions fragiles. Aucun score, aucun `/20`, aucun pourcentage — vérifié par un test |
| « Cette question me semble fausse » | Sur chaque question, pendant le contrôle **et** dans la correction. Remonte au tableau de bord ; la question ne pénalise pas l'élève |
| Coût par usage | Quotas côté serveur, par jour et par session (`app/config.py`) |

### Le compte : adresse mail et mot de passe

Deux onglets sur le même écran — connexion et inscription — plus « mot de passe oublié »,
qui envoie un code à six chiffres par courrier.

L'inscription demande **le prénom, la classe, l'adresse et un mot de passe**, et rien de
plus. Le prénom nomme la page de l'élève, la classe règle le niveau des contrôles : ni
l'un ni l'autre n'est de la curiosité. Ni nom de famille, ni date de naissance, ni
établissement — ce qu'on ne collecte pas ne peut ni fuiter, ni être réclamé, ni être
effacé pour rien.

**Le mot de passe** passe par `hashlib.scrypt` (n = 2¹⁴, r = 8, p = 1, sel aléatoire par
compte) : dans la bibliothèque standard, donc aucune dépendance à tenir à jour, et coûteux
en mémoire, ce qui rend une carte graphique bien moins efficace pour l'attaquer qu'avec un
SHA nu. Environ 45 ms par vérification. Les paramètres voyagent avec l'empreinte, pour
pouvoir les durcir sans invalider les anciennes.

Pas de règle de composition (« une majuscule, un chiffre, un caractère spécial ») : elles
poussent à `Motdepasse1!`, que tout dictionnaire connaît, et à écrire le mot de passe sur
un cahier. On exige **8 caractères**, et on refuse les évidences — la liste des plus
courants, son propre prénom, sa propre adresse.

Ce qui est tenu côté serveur (`app/store.py`, `app/main.py`, testé dans
`tests/test_entree.py`) :

| Risque | Ce qui l'arrête |
|---|---|
| Essayer mille mots de passe | 10 essais ratés par quart d'heure, par adresse **et** par machine ; une connexion réussie efface l'ardoise |
| Lire les mots de passe d'une base volée | scrypt avec un sel par compte : jamais de clair, et pas de table pré-calculée |
| Savoir qui est inscrit | Adresse inconnue et mauvais mot de passe donnent la même réponse, au même temps de calcul (hachage à vide) |
| Deviner le code de réinitialisation | Cinq essais, puis il est brûlé ; comparaison à temps constant |
| Rejouer un code | Effacé dès qu'il a servi, expire en 10 minutes |
| Remettre `12345678` par la porte de service | Le nouveau mot de passe passe les mêmes règles |
| Garder la main sur un compte volé | Changer de mot de passe ferme **toutes** les connexions ouvertes |
| Inonder la boîte mail d'un camarade | Un code par minute et 15 par heure par adresse, 50 par heure par machine |
| Arroser mille adresses depuis une machine | Même limite par machine (`X-Forwarded-For` lu seulement si `CB_PROXY_DE_CONFIANCE=1`) |
| Voler le jeton depuis la page | Cookie `HttpOnly`, `SameSite=Lax`, `Secure` en HTTPS. Le script ne le lit jamais |
| Ouvrir le cours d'un camarade avec son lien `?s=…` | Une séance appartient à un compte ; les autres reçoivent un 404 |
| Deux élèves sur la même tablette | Les clés du navigateur portent l'identifiant du compte (`cb.<compte>.…`) |

Toutes les routes `/api` sauf `/api/config` et `/api/auth/*` exigent d'être connecté — un
test énumère l'application pour attraper celle qu'on ajouterait sans le garde-fou.

**Le droit à l'effacement est un bouton**, en bas de sa page : l'adresse et les séances
partent du serveur, et le classeur de ce navigateur part avec.

### Ce que le compte ne fait pas encore : tout garder

**Décidé : le classeur ira sur le serveur.** Aujourd'hui les cours, les fiches et les
contrôles vivent dans le navigateur où ils ont été faits ; se connecter sur un autre
appareil donne un classeur vide. Avec un compte, l'élève s'attend à l'inverse, et il a
raison. Tant que ce n'est pas fait, aucune page ne le promet — un test l'empêche.

Ce que ça demande, dans l'ordre où ça se construit.

**1. Ce qui monte.** Le texte ne pèse rien : une séance complète (transcription du cours,
fiches, contrôles et corrections) tient dans quelques dizaines de kilo-octets, soit moins
d'un mégaoctet pour une année entière. Le stocker est gratuit à l'échelle d'un test.

Les **photos du cahier** montent aussi — décidé. Au format que le produit fabrique
(1568 px de côté, JPEG qualité 0.82), une page tourne autour de 200 à 400 Ko, cent fois le
reste : quatre pages par cours, dix cours par trimestre, ~10 Mo par élève et par
trimestre. Le coût n'est pas le sujet ; ce que ça engage l'est (point 4).

C'est aussi ce qui rend la promesse tenable : sans les photos, un élève qui change de
téléphone retrouve ses fiches mais plus le fragment de cahier qui les justifie — or c'est
exactement ce qui distingue ce produit d'un générateur de fiches.

**2. Le modèle de synchronisation.** Une séance entière, écrasée par la plus récente
(`maj_le` en UTC). Pas de fusion champ par champ : c'est un élève, sur un ou deux
appareils, qui travaille rarement sur les deux en même temps. Une vraie fusion coûterait
des semaines pour un cas qui arrive deux fois par an, et le prix se paierait en bugs
silencieux — la pire monnaie quand ce qu'on perd est le travail de quelqu'un.

Concrètement : `GET /api/classeur?depuis=<horodatage>` rend les séances modifiées depuis,
`PUT /api/classeur/<seance>` en pousse une. Le navigateur garde tout en local et reste
utilisable hors ligne ; le serveur est la copie de référence quand les deux divergent.

**3. La reprise de l'existant.** À la première connexion après la bascule, ce qui est dans
le navigateur monte tel quel. Un élève qui a travaillé avant ne doit rien perdre — et ne
doit pas avoir à comprendre qu'il s'est passé quelque chose.

**4. Ce que ça change côté données personnelles — le vrai sujet.** Aujourd'hui le serveur
détient une adresse, un prénom, une classe. Après, il détiendra **le cours d'un enfant,
ses réponses, et les photos de son cahier** — parfois avec son nom écrit dessus, et
l'écriture d'un mineur identifiable. Ce n'est pas la même ligne au registre des
traitements.

Ce qui devient obligatoire, et non plus recommandé :

- le **consentement d'un titulaire de l'autorité parentale** avant l'ouverture du compte,
  et non plus « à prévoir un jour » ;
- un **contrat de sous-traitance** avec l'hébergeur (article 28 du RGPD), et un hébergement
  dans l'Union ;
- le **chiffrement au repos** des photos, et un accès qui passe par le compte — pas une URL
  devinable ;
- une **durée de conservation écrite** : l'année scolaire, puis effacement automatique ;
- l'**export** de son classeur par l'élève, en plus de l'effacement qui existe déjà.

Aucun de ces cinq points n'est du code compliqué. Ils sont simplement plus difficiles à
ajouter après coup qu'à poser en même temps que le stockage — d'où cette liste ici, avant
la première ligne.

**5. Ce qui ne change pas.** Les quotas restent côté serveur, le corrigé du contrôle en
cours reste hors de portée du navigateur, et il n'y a toujours aucune note.

### Envoyer les codes de réinitialisation

Sans `CB_SMTP_HOTE`, les codes partent dans les journaux — c'est fait pour le
développement. `CB_AUTH_CODE_EN_CLAIR` les renvoie en plus dans la réponse HTTP pour
cliquer dans le parcours sans serveur de courrier : **c'est la porte grande ouverte**, et
le réglage se désactive tout seul dès qu'un SMTP est configuré.

```
CB_SMTP_HOTE=smtp.exemple.fr
CB_SMTP_PORT=587
CB_SMTP_UTILISATEUR=…
CB_SMTP_MOT_DE_PASSE=…
CB_SMTP_EXPEDITEUR="Repère <ne-pas-repondre@exemple.fr>"
```

### Ce qui reste à faire avant d'ouvrir à des mineurs

Collecter l'adresse mail et le prénom d'un collégien est un traitement de données
personnelles. En France, le consentement du seul mineur ne vaut qu'à partir de 15 ans
(article 8 du RGPD, article 45 de la loi Informatique et Libertés) ; en dessous, il faut
aussi celui d'un titulaire de l'autorité parentale. Le code tient la partie technique —
minimisation, effacement en un clic, mots de passe hachés, rien de transmis à un tiers.
Restent à écrire : une politique de confidentialité, le recueil du consentement parental,
et le registre des traitements.

### Aucune requête vers un tiers

Les polices sont découpées et embarquées dans `web/polices.css` plutôt que chargées
depuis Google : une requête vers `fonts.gstatic.com` transmettrait l’adresse IP de
chaque élève à un tiers, ce que tout le reste du produit s’applique à éviter.
`outils/polices.py` les refabrique (626 Ko de polices complètes réduits à 64 Ko), et
refuse de produire un fichier à qui il manquerait des caractères.

### Les photos ne sont pas conservées

Elles transitent en mémoire jusqu'au modèle, puis disparaissent. Ce qui est gardé, c'est
la transcription du cours — dans le navigateur de l'élève, pas sur le serveur. Côté
serveur ne subsistent que l'adresse mail du compte, un identifiant de séance aléatoire,
des compteurs d'usage, des événements anonymes, et le corrigé du contrôle en cours
(purgé au bout de 30 jours).

Le corrigé reste côté serveur pour une raison simple : envoyé avec les questions, il
serait lisible dans les outils de développement avant même que l'élève ait répondu.

---

## Démarrer

```bash
cd controle-blanc
pip install -r requirements.txt
./lancer.sh                      # http://localhost:8000
```

Sans `ANTHROPIC_API_KEY`, l’application démarre en **mode démonstration** : tout le
parcours est cliquable avec un chapitre d’histoire de 3e en dur, sans un seul appel
facturé. C’est le mode à utiliser pour montrer l’outil avant de dépenser.

Pour envoyer la démonstration à quelqu’un sans rien héberger :

```bash
python3 outils/artefact.py demo.html                      # histoire, 3e
python3 outils/artefact.py demo-es.html --contenu espagnol  # espagnol, lycée
```

Un seul fichier, aucune requête sortante. Le jeu de contenus se choisit avec
`--contenu` : chaque fichier de `outils/demonstration/` fournit le cours, la fiche et
les questions, sans qu’aucune ligne de logique change. En ajouter un permet de montrer
l’outil dans une autre matière.

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

## Essayer la chaîne sur de vraies photos

C’est la commande qui sert à juger le produit avant de le donner à des élèves :
lecture des photos, fiche, contrôle, correction, fiche ciblée, second contrôle.

```bash
export ANTHROPIC_API_KEY=sk-ant-…
python3 outils/essai.py photos/*.jpg --niveau 3e --matiere histoire-geographie
```

Elle affiche chaque étape avec sa durée et son coût, puis écrit dans
`essais/AAAA-MM-JJ-hhmm/` un rapport HTML relisible et le JSON brut du modèle.

Les réponses de l’élève se saisissent au clavier, ou viennent d’un fichier
(`--reponses copie.txt`, un bloc `1: …` par question), ou restent vides
(`--vide`) pour voir la correction la plus sévère.

Sans photos sous la main, on part d’un chapitre du corpus — les programmes de 6e en
histoire et en maths, écrits comme des transcriptions de cahier. Ça permet de travailler la qualité des
fiches et des questions en attendant de vraies photos d’élèves :

```bash
python3 outils/essai.py --corpus liste
python3 outils/essai.py --corpus cites-grecques --niveau 6e --matiere histoire-geographie
```

Le corpus est un banc d’essai, pas du contenu à servir : le produit tient sur le fait
que c’est le cours de *ce prof-là* qui tombe au contrôle.

Chaque fichier de `outils/corpus/` déclare le programme qu’il suit, parce qu’ils ne
changent pas au même moment : les maths ont basculé sur l’arrêté du 17 avril 2025, en
vigueur depuis la rentrée 2025 ; l’histoire suit encore l’arrêté de 2015 modifié, et ne
basculera qu’à la rentrée 2027. Ajouter une matière ne demande qu’un fichier de plus,
de la même forme.

Sans clé API la commande refuse de partir : un banc d’essai qui produirait les
contenus d’exemple ne testerait rien.

Ce qu’il faut regarder dans le rapport, dans cet ordre :

1. **la transcription** — est-ce bien ce que dit le cours ? c’est elle qui
   conditionne tout le reste ;
2. **les photos signalées illisibles** — le signal est-il juste, et le conseil
   utile ?
3. **les questions** — un professeur de la matière les poserait-il ?
4. **la correction** — le renvoi au cours tombe-t-il au bon endroit ?
5. **le coût total**, affiché en bas : c’est le prix d’un élève qui va au bout.

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
├── web/              la page unique : index.html, app.js, styles.css, polices.css
├── outils/
│   ├── polices.py    refabrique polices.css (découpe et embarque les polices)
│   ├── artefact.py   fabrique la démonstration autonome, en un seul fichier
│   ├── essai.py      passe de vraies photos, ou un chapitre du corpus, dans la chaîne
│   ├── corpus/       les programmes de 6e, qui tiennent lieu de photos
│   └── demonstration/  le faux serveur et les jeux de contenus (histoire, espagnol)
└── tests/            le parcours complet, hors ligne
```
