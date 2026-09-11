# Mettre Repère en ligne, étape par étape

Pour le test fermé : une dizaine d'élèves, un mois. Compte une demi-journée en
tout, dont l'essentiel est de l'attente.

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
effacée à chaque redéploiement. Compte quelques euros par mois pour un disque.

Render, Railway, Fly.io ou une petite machine virtuelle font l'affaire. La
suite décrit Render, qui lit le `Procfile` tout seul ; l'idée est la même
ailleurs.

1. Nouveau **Web Service**, à partir du dépôt GitHub.
2. Branche : `claude/new-session-s00nfb`.
3. **Root directory : `controle-blanc`.** Le dépôt en contient d'autres choses ;
   sans ça rien ne se construit.
4. Build : `pip install -r requirements.txt`. Démarrage : laisse-le lire le
   `Procfile`.
5. **Ajoute un disque** (Disks), point de montage `/var/donnees`, 1 Go suffit.

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

Tout le reste a des valeurs par défaut mesurées : ne les touche pas pour le
test. Elles sont dans `.env.example`, avec leur raison.

---

## 3. Vérifier avant d'envoyer le lien (15 min)

Dans l'ordre, sur ton téléphone :

1. **La page s'ouvre.** Pas de bandeau « Mode démonstration » sur l'accueil : s'il
   est là, `ANTHROPIC_API_KEY` n'est pas lue et rien ne sera analysé pour de vrai.
2. **Crée-toi un compte**, réponds à la question de l'âge.
3. **Photographie deux pages d'un vrai cours** et va jusqu'à la fiche. C'est le
   seul test qui compte : il vérifie la clé, le modèle, les quotas et le disque
   d'un coup. Coûte environ 0,25 $.
4. **Redéploie** (n'importe quelle modification), puis reconnecte-toi. Si ton
   compte a disparu, `CB_DB_PATH` n'est pas dans le disque monté — reviens à
   l'étape 1.5.
5. **Regarde les journaux.** S'il y a une ligne `COOKIE SANS « Secure »`, c'est
   `CB_IPS_PROXY` qui manque.
6. **Mot de passe oublié** : demande un code, vérifie qu'il arrive par mail.
7. **Installe l'application** : le navigateur te le propose, ou « Partager → Sur
   l'écran d'accueil » sur iPhone. Vérifie qu'elle s'ouvre sans barre d'adresse.
8. **`/admin/metriques?token=…`** répond.

---

## 4. Les dix familles

Envoie le lien aux **parents**, pas aux élèves : c'est eux qui doivent savoir, et
c'est eux qui décideront un jour de payer. Dis ce que c'est en trois lignes, et
préviens que l'enfant devra cocher qu'il a leur accord s'il a moins de 15 ans.

Note la date du premier compte : le compteur du mois repart le 1er.

---

## Pendant le mois

`/admin/metriques?token=…` montre ce qui se passe. Regarde surtout **qui revient
une deuxième fois** : c'est la seule question à laquelle ce test doit répondre.
Une fiche lue une fois par curiosité ne prouve rien.

Repasse `python3 outils/garde.py` avant tout changement de consigne pendant le
test — 0,30 $, et ça évite de casser le produit sous les pieds de dix élèves.
