# Mettre Repère en ligne, étape par étape

Pour le test fermé : une dizaine d'élèves, un mois. Compte une demi-journée en
tout, dont l'essentiel est de l'attente.

**Ce que coûte un mois de test**, en deux factures qui n'ont rien à voir :

| Quoi | Chez qui | Combien |
|---|---|---|
| Le serveur qui fait tourner le site | l'hébergeur | ~7 $/mois |
| Le disque qui garde les comptes | l'hébergeur | ~0,25 $/mois (1 Go) |
| La lecture des cours | Anthropic | 12 € en moyenne, 36 € si les dix saturent |

Soit une cinquantaine d'euros au pire, dont sept d'hébergement. Les élèves ne
paient rien et rien ne le leur demande : c'est toi qui portes les deux
factures. L'hébergement se facture au prorata — on supprime le service à la fin
du test et ça s'arrête.

Ce qui est déjà fait et dont tu n'as pas à t'occuper : le mode application
(manifeste, icônes, agent de service, invitation à installer), les quotas, la
question de l'âge à l'inscription, le tableau de bord.

---

## 0. Avant de toucher à un hébergeur (10 min)

**Recharge la clé.** `console.anthropic.com` → Billing. Pour dix élèves sur un
mois : compte 12 € en moyenne, 36 € si tous saturent leurs quotas. Mets 40 €.

**Pose une limite de dépense** dans la même section. C'est le seul garde-fou
qui te protège de ce que personne n'a prévu. Mets-la à 50 €.

**Fabrique un jeton d'administration.** Une valeur longue et aléatoire :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Garde-la : c'est elle qui ouvrira `/admin/metriques`. Sans elle, cette page
renvoie 404 — pour tout le monde, toi compris.

---

## 1. L'hébergeur (30 min)

Il faut **du Python avec un disque qui survit aux redémarrages**. C'est le seul
critère, et c'est là qu'on se trompe : sur les offres gratuites de Render ou de
Fly, le disque est éphémère, et la base SQLite — donc tous les comptes — est
effacée à chaque redéploiement. Concrètement : un élève s'inscrit le mardi, tu
corriges un défaut le mercredi, et jeudi son compte n'existe plus. C'est ce que
la première offre payante achète, et c'est la seule raison de la prendre.

Render, Railway, Fly.io ou une petite machine virtuelle font l'affaire. La
suite décrit Render ; l'idée est la même ailleurs.

1. Nouveau **Web Service**, à partir du dépôt GitHub.
2. **Le nom devient l'adresse** (`https://<nom>.onrender.com`) : c'est lui que
   tu enverras aux familles et qui restera dans le raccourci posé sur l'écran
   d'accueil. `repere-revisions`, pas le nom du dépôt.
3. **Région : Frankfurt.** Par défaut c'est l'Oregon, et chaque photo d'élève
   traverse l'Atlantique deux fois. Une région ne se change pas après coup : il
   faut recréer le service.
4. Branche : `claude/new-session-s00nfb`. Render propose `main`, où il n'y a
   rien.
5. **Root directory : `controle-blanc`.** Le dépôt contient aussi un `_site` et
   un `netlify.toml` à la racine ; sans ce champ, Render cherche
   `requirements.txt` là où il n'y en a pas.
6. Build : `pip install -r requirements.txt`.
7. Démarrage : recopie la ligne du `Procfile`, plutôt que de compter sur Render
   pour la lire :

   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT --forwarded-allow-ips "${CB_IPS_PROXY:-127.0.0.1}"
   ```

8. **L'offre payante la moins chère**, pas la gratuite : c'est la première qui
   accepte un disque.
9. **Ajoute un disque** (Disks), point de montage `/var/donnees`, 1 Go suffit.

Le premier déploiement peut se faire avant les réglages de l'étape 2 : sans
`ANTHROPIC_API_KEY` le site démarre en mode démonstration, ce qui prouve déjà
que la construction passe.

---

## 2. Les réglages (15 min)

Dans *Environment*. Les six premiers sont indispensables, les quatre suivants
concernent le courrier.

| Nom | Valeur | Pourquoi |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-…` | sans elle le site démarre en mode démonstration et refuse de se lancer sur une adresse publique |
| `CB_DB_PATH` | `/var/donnees/repere.sqlite3` | **dans le disque monté**, sinon les comptes disparaissent au premier redéploiement |
| `CB_PUBLIC_BASE_URL` | `https://…` (l'adresse que Render te donne) | sert aux liens de reprise, et signale au démarrage que le site est en ligne |
| `CB_ADMIN_TOKEN` | le jeton de l'étape 0 | ouvre `/admin/metriques` |
| `CB_TAUX_EUR_USD` | `0.92` | convertit les dollars du tableau de bord en euros |
| `CB_PRIX_ABONNEMENT` | `7.99` | le prix affiché, pour dire ce qu'il reste une fois le modèle payé |
| `CB_IPS_PROXY` | `*` | **le piège** : sans ça uvicorn voit du `http` derrière le proxy, et le cookie de connexion part sans `Secure`. Sûr ici, où rien n'atteint l'application autrement que par le proxy de la plateforme |
| `CB_PROXY_DE_CONFIANCE` | `1` | pour que les limites de cadence comptent la vraie machine, pas le proxy |

Le courrier, pour « mot de passe oublié ». Sur dix élèves, au moins un oubliera
son mot de passe ; sans ces quatre-là, il est bloqué pour de bon et le code
part dans les journaux du serveur.

| Nom | Valeur |
|---|---|
| `CB_SMTP_HOTE` | `smtp-relay.brevo.com`, `smtp.resend.com`, ou ton fournisseur |
| `CB_SMTP_PORT` | `587` |
| `CB_SMTP_UTILISATEUR` / `CB_SMTP_MOT_DE_PASSE` | ce que le fournisseur te donne |
| `CB_SMTP_EXPEDITEUR` | `Repère <ne-pas-repondre@ton-domaine>` |

Les rappels de contrôle, si tu les veux. **Facultatif** : sans ces trois
lignes, la fonction n'existe pas — aucun réglage n'apparaît chez l'élève, et
aucune tâche de fond ne démarre. Le reste du produit marche exactement pareil.

Sur ta machine, une fois :

```
python -m outils.cles_vapid
```

Il affiche trois lignes à coller dans *Environment*. **La clé privée ne doit
jamais entrer dans le dépôt**, qui est public — c'est elle qui autorise à
écrire aux téléphones de tes élèves.

| Nom | Valeur |
|---|---|
| `CB_VAPID_CLE_PUBLIQUE` | ce que l'outil affiche |
| `CB_VAPID_CLE_PRIVEE` | ce que l'outil affiche — **secret** |
| `CB_VAPID_CONTACT` | `https://ton-site.onrender.com` — par où Apple et Google te joindraient si tes envois posaient problème. L'adresse du site suffit ; `mailto:une-adresse` marche aussi, mais une adresse personnelle n'apporte rien ici |

Puis, dans le Shell, une fois le service redémarré :

```
python -m outils.verifier_rappels
```

Il dit en une ligne si c'est bon. Le journal de démarrage, lui, annonce
seulement que les trois variables **existent** : une clé tronquée au
copier-coller, ou une publique et une privée venues de deux exécutions
différentes, passent ce contrôle-là et ne se voient qu'à l'envoi, le soir, chez
l'élève. Cet outil attrape les trois fautes, sans rien afficher de secret.

Deux choses à savoir avant de le proposer aux familles :

* **Sur iPhone, ça ne marche que depuis l'écran d'accueil.** Partager → « Sur
  l'écran d'accueil ». Dans l'onglet Safari, aucune notification n'arrive, et
  c'est Apple qui le décide. L'application le dit avant de proposer le réglage.
* **Les régénérer coupe les rappels de tout le monde** : les navigateurs déjà
  inscrits l'ont été avec l'ancienne clé publique. On ne le fait que si la
  privée a fuité — et alors il faut le faire tout de suite.

Tout le reste a des valeurs par défaut mesurées : ne les touche pas pour le
test. Elles sont dans `.env.example`, avec leur raison.

---

## 3. Vérifier avant d'envoyer le lien (15 min)

Dans l'ordre, sur ton téléphone :

1. **La page s'ouvre.** Pas de bandeau « Mode démonstration » sur l'accueil : s'il
   est là, `ANTHROPIC_API_KEY` n'est pas lue et rien ne sera analysé pour de vrai.

   L'absence du bandeau ne suffisait pas : au premier déploiement, la clé était
   posée, non vide, et refusée — le bandeau avait bien disparu, et seule
   l'analyse échouait. Le démarrage vérifie donc maintenant que la clé ouvre
   vraiment la porte (un appel gratuit) et **refuse de démarrer** sinon. Si le
   déploiement échoue sur `ANTHROPIC_API_KEY refusée par le fournisseur`, c'est
   un copier-coller à reprendre : retape la valeur à la main dans *Environment*
   plutôt que de réimporter un `.env`.
2. **Crée-toi un compte**, réponds à la question de l'âge.
3. **Photographie deux pages d'un vrai cours** et va jusqu'à la fiche. C'est le
   seul test qui compte : il vérifie la clé, le modèle, les quotas et le disque
   d'un coup. Coûte environ 0,25 $.
4. **Redéploie** (n'importe quelle modification), puis reconnecte-toi. Si ton
   compte a disparu, `CB_DB_PATH` n'est pas dans le disque monté — reviens à
   l'étape 1.9.
5. **Regarde les journaux.** S'il y a une ligne `COOKIE SANS « Secure »`, c'est
   `CB_IPS_PROXY` qui manque.
6. **Mot de passe oublié** : demande un code, vérifie qu'il arrive par mail.
7. **Installe l'application** : le navigateur te le propose, ou « Partager → Sur
   l'écran d'accueil » sur iPhone. Vérifie qu'elle s'ouvre sans barre d'adresse.
8. **`/admin/metriques?token=…`** répond.

### Quand le tableau de bord ne bouge pas

Des élèves travaillent, et la page ne montre rien de neuf. Trois pannes très
différentes se ressemblent vues d'ici. Dans l'ordre, du plus rapide au plus sûr :

1. **Ouvrir `/api/config`** dans un navigateur — pas besoin du jeton. Si
   `"mode_demonstration": true`, tout est dit : sans `ANTHROPIC_API_KEY`, le
   produit continue de marcher mais **sert des contenus inventés** et enregistre
   des appels à zéro token. Les volumes montent, le coût reste à zéro.
2. **Dans le Shell Render**, taper `python outils/etat_base.py`. Il dit le mode,
   l'état de la base, ce qui est arrivé les dix derniers jours poste par poste,
   et ce qui est rattaché à chaque élève. Il n'écrit rien et n'appelle rien.
3. **Regarder « Plus ancien compte »** dans sa sortie. Si cette date colle avec
   le dernier déploiement, `CB_DB_PATH` ne pointe pas sur le disque persistant
   et la base repart de zéro à chaque mise en ligne.

Et un cas qui n'est pas une panne : **« Séances sans compte »**. Ces appels-là
comptent dans « Dépensé en tout » et dans aucune ligne d'élève — c'est ce que
fait un élève qui travaille déconnecté.

---

## 4. Les dix familles

Envoie le lien aux **parents**, pas aux élèves : c'est eux qui doivent savoir, et
c'est eux qui décideront un jour de payer. Dis ce que c'est en trois lignes, et
préviens que l'enfant devra cocher qu'il a leur accord s'il a moins de 15 ans.

Note la date du premier compte : le compteur du mois repart le 1er.

---

## Quand le test sera fini

Tout ce qui a été posé pour ce test et qui devient faux en s'ouvrant au public
est listé dans **AVANT-L-OUVERTURE.md** — le consentement parental qui n'est pas
vérifié, la ligne « c'est gratuit » écrite dans le produit, l'expéditeur
personnel, le domaine, la branche. Aucune de ces choses ne casse toute seule :
elles continuent de fonctionner en mentant. Relis ce fichier avant d'envoyer le
lien à quelqu'un que tu ne connais pas.

## Pendant le mois

`/admin/metriques?token=…` montre ce qui se passe. Regarde surtout **qui revient
une deuxième fois** : c'est la seule question à laquelle ce test doit répondre.
Une fiche lue une fois par curiosité ne prouve rien.

Repasse `python3 outils/garde.py` avant tout changement de consigne pendant le
test — 0,30 $, et ça évite de casser le produit sous les pieds de dix élèves.
