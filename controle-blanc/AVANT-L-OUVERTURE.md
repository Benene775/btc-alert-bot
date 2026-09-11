# Ce qu'il faut reprendre avant d'ouvrir au public

Tout ce qui suit a été posé **exprès** pour le test fermé — une dizaine de
familles connues, un mois, gratuit. Chacune de ces décisions est raisonnable
dans ce cadre et devient fausse, voire malhonnête, dès qu'un inconnu s'inscrit.

Cette liste existe parce qu'aucune de ces choses ne casse toute seule : elles
continuent de fonctionner en mentant. Personne ne s'en apercevra sans la relire.

---

## 1. Le consentement parental n'est pas vérifié

**Aujourd'hui.** L'élève déclare son âge, et s'il a moins de 15 ans il coche
« j'ai demandé à mes parents ». C'est une déclaration : qui veut passer outre
coche la case.

**Pourquoi c'est acceptable maintenant.** Dix familles que tu connais, à qui tu
as donné le lien toi-même.

**Ce qu'il faut à la place.** Un mécanisme où le parent **agit** : l'élève donne
l'adresse d'un parent, le parent reçoit un message et clique, et le compte ne
s'ouvre qu'ensuite. L'article 8 du RGPD demande des « efforts raisonnables pour
vérifier » — une case cochée par l'enfant ne vérifie rien.

La machinerie existe déjà : `app/courrier.py` sait envoyer, et les routes
d'authentification gèrent les codes avec expiration, essais et cadence. Compte
une demi-journée.

*Au minimum, si tu gardes la déclaration : refuse que l'adresse du parent soit
celle de l'élève, demande le prénom du parent et écris-lui par son prénom, et
envoie-lui un résumé mensuel. Le dernier sert aussi à autre chose : c'est lui
qui décidera de payer.*

## 2. « C'est gratuit » est écrit dans le produit

`web/index.html`, dans le bloc que l'élève montre à ses parents, marqué
`À REPRENDRE À LA FIN DU TEST`. La ligne dit qu'il n'y a aucun paiement dans
l'application. Le jour où c'est faux, c'est un mensonge écrit à l'endroit exact
où un parent donne son accord.

Un test (`tests/test_age_et_accord.py`) vérifie qu'aucune **invitation** à payer
n'existe ailleurs. Il faudra le revoir en même temps.

## 3. Le mot juridique manque

Il n'y a ni politique de confidentialité, ni registre des traitements. Les
quatre lignes montrées aux parents disent l'essentiel et sont vraies, mais ce
n'est pas une politique de confidentialité.

À écrire avant d'ouvrir, avec le point 1.

## 4. L'adresse du site et l'expéditeur des mails

**Le domaine.** Les élèves installent l'application sur leur écran d'accueil, et
elle est attachée à l'adresse d'où elle a été installée. Passer de
`xxx.onrender.com` à un vrai domaine oblige chacun à désinstaller et
réinstaller. Pour dix, c'est une instruction de trente secondes ; à cent, non.

**L'expéditeur.** `CB_SMTP_EXPEDITEUR` porte une adresse personnelle. Ça marche
et ça rassure dix familles qui te connaissent ; ça fait amateur pour un inconnu.

Attention en changeant : l'expéditeur doit appartenir à un domaine que tu
contrôles et dont tu as réglé SPF et DKIM. Mettre un expéditeur à un domaine
qu'on ne possède pas envoie tous les mails en spam.

## 5. La branche

Tout est sur `claude/new-session-s00nfb`, rien sur `main`. À fusionner avant que
le déploiement dépende d'une branche de travail.

## 6. La garde ne couvre pas la lecture des photos

`outils/garde.py` part du corpus, donc d'un cours déjà transcrit : elle ne fait
jamais tourner `ANALYSE_SYSTEME`. Pose `CB_GARDE_PHOTOS` sur un dossier d'images
pour ajouter ce cas — avec des photos qui ne sont le cahier de personne, le
dépôt étant public.

## 7. Les plafonds

96 pages, 12 fiches, 12 contrôles par mois : ils donnent 1,20 €/mois en moyenne
et 3,61 € au maximum. C'est ce qui fixera le prix. Le tableau de bord mesure le
coût réel par compte pendant le test — regarde-le avant de décider.

---

## Et ce qui est déjà en ordre

Pour ne pas rouvrir ce qui n'a pas besoin de l'être : les photos ne sont pas
conservées, les mots de passe sont hachés par scrypt, effacer son compte efface
aussi le navigateur, aucune requête ne part vers un tiers, le corrigé reste hors
de portée du navigateur, aucune note n'est jamais affichée, et le mode
application est complet.
