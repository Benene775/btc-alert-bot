# Repère

> Révise ce qui te manque, pas le reste.

Un site web mobile où un élève photographie son cours, passe un **contrôle blanc au
format réel de la matière**, obtient une correction commentée qui renvoie à son propre
cours, puis des fiches ciblées sur ce qu'il a raté.

On ne vend pas des fiches de révision, et surtout pas une révision de plus : on vend
le temps qu'un élève cesse de perdre sur ce qu'il sait déjà. Le contrôle blanc ne
s'ajoute pas à la séance de révision, il la remplace — se tester au lieu de relire —
et ce qu'il révèle réduit le chapitre à trois notions. L'élève en difficulté y gagne
un point de départ au lieu d'un mur ; celui qui s'en sort déjà y gagne les heures
qu'il passait à tout revoir par sécurité.

**Le nom.** Un repère, c'est ce que la correction rend : pas une note — le cahier des
charges les interdit — mais l'endroit de son propre cours où aller relire. Le logo le
dessine : un filet de marge, trois lignes, et celle qu'on est venu retrouver. « Contrôle
blanc » reste le nom de l'épreuve, pas celui du site.

---

## Mettre en ligne

Deux choses très différentes, à ne pas confondre.

### Les démonstrations : oui, tout de suite

`python3 outils/site.py _site` fabrique trois fichiers HTML autonomes — une page de
choix et les deux démonstrations. Aucun serveur, aucune clé d'API, aucune donnée
d'élève, aucune requête sortante. Ça se pose n'importe où.

* **GitHub Pages** — `.github/workflows/demos.yml` s'en charge. À activer une fois :
  *Settings → Pages → Source : GitHub Actions*. Le site sort ensuite sur
  `https://<compte>.github.io/<dépôt>/` à chaque poussée sur `main`.
* **Netlify** — `netlify.toml` à la racine. *Add new site → Import an existing project*,
  choisir le dépôt : Netlify lit le fichier, il n'y a rien à régler.

Le workflow fait tourner les tests avant de publier : on ne met pas en ligne une
démonstration fabriquée à partir d'un code cassé.

### Le produit : ni sur Pages, ni sur Netlify

Repère a un serveur Python qui garde les comptes, appelle le modèle, tient les quotas
et garde le corrigé hors de portée du navigateur. GitHub Pages ne sert que des
fichiers. Netlify ne fait tourner que des fonctions courtes, sans disque persistant —
donc sans SQLite.

Il lui faut un hébergement qui exécute du Python avec un disque : Railway, Render,
Fly.io, Scaleway, ou une petite machine virtuelle. Et, avant d'ouvrir à de vrais
élèves :

| | |
|---|---|
| `ANTHROPIC_API_KEY` | Sans elle, `CB_DEMO_MODE` reste à 1 et rien n'est analysé pour de bon |
| Le coût réel par élève | Jamais mesuré : `outils/essai.py` n'a pas pu tourner faute de clé |
| `CB_SMTP_HOTE` | Sinon « mot de passe oublié » ne fonctionne pas |
| Un vrai domaine en HTTPS | Le cookie de connexion ne passe en `Secure` qu'en HTTPS |
| Le consentement parental | Voir plus haut : ce n'est pas une option pour des collégiens |


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
| Coût par usage | Quotas côté serveur : par jour, par séance, et par mois et par compte (`app/config.py`) |

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

### Le classeur suit l'élève

Le texte du classeur — cours transcrits, fiches, contrôles, corrections, agenda —
monte sur le serveur, parce qu'un compte promet qu'on retrouve ses affaires
ailleurs. Avant, tout vivait dans le seul navigateur où le travail avait été
fait : changer d'appareil ou vider ses données perdait le classeur entier, sans
message, sans rien. Pour un élève ce n'est pas un bug, c'est un produit qui a
perdu son travail.

**Le modèle est volontairement pauvre.** Une séance entière, la plus récente
gagne. Pas de fusion champ par champ : c'est un élève sur un ou deux appareils,
qui travaille rarement sur les deux en même temps, et une vraie fusion coûterait
des semaines pour un cas qui arrive deux fois par an — le prix se paierait en
pertes silencieuses, la pire monnaie quand ce qu'on perd est le travail de
quelqu'un.

| | |
|---|---|
| `GET /api/classeur?depuis=…` | les séances rangées depuis, plus l'agenda |
| `PUT /api/classeur/<seance>` | en pousse une ; `{"range": false}` si le serveur en a une plus récente |
| `DELETE /api/classeur/<seance>` | effacée sur le téléphone, effacée ici — sinon elle revient |
| `PUT /api/agenda` | l'agenda entier, quelques centaines d'octets |

**Deux horodatages, et ils ne servent pas à la même chose.** `maj_le` vient du
navigateur et départage deux appareils ; `range_le` vient du serveur et répond à
« qu'est-ce qui a bougé depuis ma dernière visite ». Les confondre paraît marcher
tant que les horloges sont d'accord, puis fait sauter des séances chez l'élève
dont le téléphone retarde — et personne ne s'en aperçoit. Un test le vérifie.

Le navigateur reste la copie de travail : tout marche hors ligne, la montée se
fait quand elle peut, et la descente a lieu aux deux endroits où un compte
arrive — au démarrage si le cookie était là, et juste après avoir tapé son mot de
passe, qui est précisément le cas de l'appareil neuf.

**Ce qui ne monte pas encore : les photos du cahier.** Elles vivent dans
IndexedDB, sur l'appareil. Un élève qui change de téléphone retrouve donc ses
fiches et ses contrôles, mais plus le fragment de cahier qui les justifie. C'est
un choix, pas un oubli : stocker l'écriture manuscrite d'un mineur identifiable
n'est pas la même ligne au registre des traitements que du texte, et cette
décision se prend avec la politique de confidentialité, pas dans un commit. Ce
qui monte aujourd'hui pèse quelques dizaines de kilo-octets par élève ; les
photos, ce serait ~10 Mo par trimestre.

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

**Le démarrage refuse deux configurations**, dès que `CB_PUBLIC_BASE_URL` est définie
— c'est le signal qu'on déploie, et rien ne gêne en local :

* le **mode démonstration**, qui s'active tout seul quand `ANTHROPIC_API_KEY` manque.
  Une variable oubliée suffirait à servir des contenus factices à de vrais élèves, et
  la seule mention à l'écran est sur l'accueil — qu'un élève connecté ne voit jamais.
  Il photographierait son cours de maths pour recevoir une fiche sur la Première
  Guerre mondiale ;
* `CB_AUTH_CODE_EN_CLAIR`, qui renvoie le code de réinitialisation dans la réponse
  HTTP : n'importe qui prendrait n'importe quel compte.

`CB_DEMO_ASSUMEE=1` lève les deux — pour mettre la démonstration en ligne exprès. Les
deux ensemble, parce qu'ils décrivent la même situation.

Un avertissement de plus dans les journaux n'aurait servi à rien : personne ne les lit
au moment où ça compte. Mieux vaut un déploiement qui échoue bruyamment qu'un site qui
ment poliment.

---

## Ce que ça coûte, et ce qui le borne

Un parcours complet, c'est quatre à cinq appels au modèle : analyse des photos, fiche,
contrôle, correction, fiche ciblée. Le poste le plus lourd est l'analyse des photos.

Trois choses réduisent la facture :

* les photos sont **redimensionnées dans le navigateur** à 1568 px avant l'envoi ;
* le cours de l'élève est mis en **cache de prompt** (1 h) : il est renvoyé à chaque
  appel de la séance, c'est le plus gros bloc et il ne bouge pas ;
* les **quotas** plafonnent par jour, par séance, et surtout par mois et par compte.

Quotas par défaut, tous réglables par variable d'environnement :

| Action | Par jour | Par séance | Par mois et par compte |
|---|---|---|---|
| Analyse de photos **(en pages)** | 48 | 96 | 96 |
| Fiche générale | 3 | 12 | 8 |
| Contrôle blanc | 3 | 12 | 8 |
| Fiche ciblée | 5 | 20 | 8 |

**L'analyse se compte en pages, pas en envois.** Une page photographiée vaut
~2 350 tokens d'entrée (le navigateur la réduit à 1568 px, le modèle la découpe en
carreaux de 28×28 px), et les photos font 55 à 79 % du coût d'un parcours complet
— mesuré sur les prompts réels. Compter les envois revenait donc à facturer pareil
quatre pages et cinquante. C'est aussi l'unité qu'un élève comprend sans qu'on la
lui explique : il voit ses feuilles. L'écran des photos affiche ce qu'il lui reste
dès qu'il approche de la limite, et un envoi qui dépasserait est refusé **avant**
l'appel, pas constaté après.

Le plafond du mois est le seul qui tienne l'abonnement. Les deux autres se comptent
par séance : en ouvrir une nouvelle les remet à zéro, ce qui est gratuit et se fait
en un clic. Le mensuel, lui, passe par `sessions.compte_id`, donc il suit l'élève.

Il est calibré sur un abonnement à 7,99 € TTC (~6,20 € net de TVA et de frais de
paiement). Ce n'est pas le **pire cas** qu'on budgète : saturer les quatre compteurs
le même mois demande un acharnement que presque personne n'a, et dimensionner dessus
revient à priver tout le monde pour un élève sur vingt. C'est le **coût moyen par
compte** qui décide.

**Ces plafonds reposent sur une estimation, pas sur une mesure** — elle vient de la
taille des prompts, aucun appel n'a jamais été passé à l'API. Voir « Chiffrer le coût »
ci-dessous pour les remplacer par de vrais chiffres.

La correction n'est pas décomptée : elle fait partie du contrôle déjà compté. Faire
payer un contrôle sans résultat n'aurait pas de sens.

Quand un élève atteint la limite du jour, le message le renvoie à demain — ce qui sert
aussi la métrique qui compte. Le mois se dit autrement : demain n'y changera rien, donc
le message annonce le 1er, et rappelle que les fiches et les corrections déjà produites
restent consultables. Le mois est vérifié **avant** le jour, pour ne pas promettre un
lendemain qui refusera pareil.

Ce qu'il reste du mois s'affiche sous chaque outil de la page perso
(`GET /api/compte/quotas`). La tuile reste cliquable même à zéro : ce compteur peut
être en retard, et c'est le serveur qui refuse, avec la vraie raison.

---

## L'application

Repère s'installe sur l'écran d'accueil d'un téléphone : icône, ouverture en
plein écran sans barre d'adresse, démarrage même sans réseau. Ce n'est pas une
application de magasin — c'est la page elle-même, que le téléphone accepte de
garder (`web/manifeste.json` et `web/agent.js`).

Ce choix vaut d'être explicite. Passer par l'App Store et le Play Store
demanderait un compte développeur (99 $/an chez Apple), une revue de plusieurs
semaines, et une seconde base de code ou un emballage natif — pour le même
résultat à l'usage : une icône qu'on touche. Pour six testeurs sur deux mois,
c'est disproportionné. Le jour où la distribution en magasin devient un vrai
besoin, le même code peut être emballé sans être réécrit.

**Comment l'élève l'installe** : sur Android le navigateur le propose, et la
page perso porte un bouton ; sur iOS il faut Partager → « Sur l'écran
d'accueil », ce que la même invitation explique. Elle se referme
définitivement — un bandeau qu'on ne peut pas faire taire se lit comme de la
publicité.

### L'essayer sur son propre téléphone

**Il faut du HTTPS.** Un agent de service ne s'enregistre que sur une origine
sûre : `https://…` ou `localhost`. Ouvrir `http://192.168.1.x:8000` depuis son
téléphone, sur le réseau de la maison, donne la page mais **jamais** le mode
application — pas d'icône, pas de plein écran, pas de démarrage hors ligne. Le
fichier autonome de `outils/artefact.py` ne le donne pas non plus : il n'a ni
manifeste ni agent, seulement la page.

Deux chemins, du plus rapide au plus durable :

1. **Un tunnel**, en cinq minutes et sans rien héberger. On lance le serveur en
   local (`./lancer.sh`), puis `cloudflared tunnel --url http://localhost:8000`
   ou `ngrok http 8000` : les deux rendent une adresse en `https://…` qu'on
   ouvre sur son téléphone. Le tunnel meurt avec la fenêtre — c'est fait pour
   regarder, pas pour faire tester.

2. **Un vrai hébergement**, qu'il faudra de toute façon pour la phase de test.
   Le `Procfile` à la racine suffit à Railway, Render et Scalingo ; l'HTTPS est
   fourni. Racine du projet : `controle-blanc/`.

**Sans clé API**, le site tourne en mode démonstration — ce qui suffit largement
pour juger l'installation et le plein écran. Attention : si on définit
`CB_PUBLIC_BASE_URL`, le garde-fou de démarrage refuse justement cette
combinaison (voir plus haut). Pour un essai assumé, laisser cette variable vide,
ou poser `CB_DEMO_ASSUMEE=1`.

**Ce que l'agent met en cache, et ce qu'il ne met surtout pas :**

| | |
|---|---|
| `/api/*` | **jamais.** Servir un vieux classeur ou un vieux quota ferait réapparaître du travail effacé et mentir les compteurs. Hors ligne l'appel échoue, et l'application sait le dire |
| la coque (page, script, styles, polices) | réseau d'abord, cache en secours. Pendant le test le code change souvent : un cache d'abord bloquerait les élèves sur une version périmée |
| les icônes | cache d'abord — elles ne changent pas |

Seules les réponses valables sont gardées : mettre une page d'erreur en cache
la rejouerait à chaque démarrage hors ligne. `VERSION` dans `agent.js` se
change à la main pour purger les caches d'une version précédente.

---

## Quel modèle sert quel appel

Deux réglages larges, plus un par appel, parce que les cinq appels n'ont pas le
même risque.

| Variable | Appels concernés | Défaut |
|---|---|---|
| `CB_MODEL` | l'analyse : le seul appel qui regarde les **photos** | `claude-sonnet-5` |
| `CB_MODEL_TEXTE` | fiche, fiche ciblée, contrôle, correction | `claude-sonnet-5` |
| `CB_MODEL_<APPEL>` | cet appel-là seulement, quel qu'il soit | vide = suit les deux ci-dessus |

Les noms d'appel sont `ANALYSE`, `FICHE_GENERALE`, `FICHE_CIBLEE`, `CONTROLE`,
`CORRECTION`. Le réglage fin sert à un cas précis : les quatre appels de texte ne
demandent pas la même chose. Rédiger une fiche, c'est résumer un texte qu'on a
sous les yeux ; corriger la copie d'un élève de 13 ans, c'est juger une phrase à
moitié formée et décider ce qui est acquis. `CB_MODEL_CORRECTION=claude-opus-5`
met la gamme haute là et nulle part ailleurs, pour +31 % sur le parcours.

**Un modèle à part n'écrit plus de cache.** Un cache appartient à un modèle : les
appels qui n'en partagent pas ne se relisent pas. Comme l'écriture d'un cache
d'une heure coûte 2× l'entrée contre 0,2× la lecture, il faut au moins trois
appels sur le même modèle pour rentrer dans ses frais — `doit_cacher_le_cours()`
compte, et se tait quand ça n'en vaut plus la peine. Sans ça, sortir la seule
correction du lot lui ferait écrire un cache que personne ne relit.

Un seul appel lit de l'écriture manuscrite, et tout le reste est bâti sur ce
qu'il en tire : la fiche, le contrôle et la correction lisent la transcription,
jamais les images. Une ligne mal lue ne reste donc pas locale — elle se propage
jusque dans la copie corrigée, et un modèle qui lit de travers ne le signale pas
(contrairement à un modèle qui n'arrive pas à lire, qui met `lisible = false`).

C'est pourquoi l'écran de périmètre montre la transcription sous chaque chapitre
— « Voir ce que j'ai lu », replié par défaut — avec un bouton « Ce n'est pas ce
que dit mon cours ». C'est le seul contrôle qui existe sur cette étape, et
pendant la phase de test c'est le signal qui dira si le modèle choisi lit assez
bien : chaque clic enregistre un événement `transcription_signalee`.

Les deux défauts sont au tarif bas, et c'est un choix de **phase de test** : les
testeurs sont des élèves qu'on connaît, à qui rien n'est facturé et qu'on a
prévenus. Faire l'essai sur le modèle cher n'apprendrait rien sur ce qu'on peut
se permettre ensuite.

Le jour où c'est payant, `CB_MODEL=claude-opus-5` remonte la lecture des photos
en gamme haute **sans toucher aux quatre autres appels** — on garde donc
l'essentiel de l'économie. Ce découpage ne coûte aucune lecture de cache : le
bloc de cours mis en cache ne sert qu'aux appels « texte », l'analyse tournant
avant que le cours existe.

---

## Ce que le navigateur peut renvoyer

Le navigateur garde le cours et le renvoie à chaque appel ; ce texte part au
modèle en entrée. Sans plafond, un appel coûterait ce que le navigateur décide,
et le quota compterait quand même « une fiche ». `app/schemas.py` borne donc les
trois choses qui font la taille d'une requête : la transcription d'un chapitre
(60 000 caractères), le nombre de chapitres (40), et surtout **le total de
transcription d'un appel** (200 000 caractères, ≈ 54 000 tokens). La copie de
l'élève, qui repart au modèle pour la correction, est bornée de même.

Ces valeurs gênent l'absurde, pas l'usage : un trimestre entier de cours dense
passe largement en dessous. Un test le vérifie dans les deux sens.

---

## Chiffrer le coût

Rien à estimer : **chaque appel enregistre déjà les compteurs que l'API renvoie
elle-même** (`llm._usage` lit `input_tokens`, `output_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`, plus le modèle qui a
réellement servi), et `store.enregistrer_usage` les range dans `usages`. Il manque
seulement d'avoir tourné avec une vraie clé.

La marche à suivre :

1. Poser `ANTHROPIC_API_KEY` (ce qui sort du mode démonstration tout seul) et un
   `CB_DB_PATH` persistant.
2. Vérifier `PRIX_USD_PAR_MTOK_PAR_MODELE` dans `app/config.py` contre la page de
   tarifs. Ces nombres sont écrits à la main et rien ne les met à jour. La table
   connaît Opus (5 / 25 $ par million de tokens) et Sonnet 5 (2 / 10 $) ; tout
   autre modèle est chiffré au tarif par défaut, et le tableau de bord le signale
   en rouge plutôt que d'afficher un chiffre faux en silence. Les clés sont
   volontairement précises — `sonnet-5`, pas `sonnet`, qui attraperait Sonnet 4.6
   et son tarif différent.
3. Faire passer un lot de cours réels — une vingtaine suffit à sortir du bruit.
4. Lire `GET /admin/metriques?token=…` :
   * **coût par appel**, ventilé par action *et par modèle* (indispensable pour
     comparer deux modèles : sans ça tout finirait au même tarif) ;
   * **coût par compte et par mois** — moyenne, médiane, maximum. C'est la seule
     unité qui se compare au prix de l'abonnement ; le coût par séance n'en dit
     rien, puisqu'un élève ouvre autant de séances qu'il veut.
5. Recouper le total avec la facturation de la console Anthropic. Si les deux
   divergent, c'est la table de tarifs qui a vieilli.

Ce que ça ne mesure pas : la **qualité**. Un modèle deux fois moins cher qui
transcrit mal un cours coûte bien plus qu'il n'économise, puisque la fiche, le
contrôle et la correction sont tous bâtis sur la transcription, pas sur les photos.
Comparer deux modèles demande de relire les transcriptions à la main sur le même
lot de cours.

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
