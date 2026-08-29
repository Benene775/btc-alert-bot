# Repère

> Passe le contrôle avant le contrôle.

Un site web mobile où un élève de collège photographie son cours, passe un **contrôle
blanc au format réel de la matière**, obtient une correction commentée qui renvoie à son
propre cours, puis des fiches ciblées sur ce qu'il a raté.

**Tout le projet est dans [`controle-blanc/`](controle-blanc/)** — commencer par
[son README](controle-blanc/README.md) : le parcours, les contraintes, l'architecture,
la mise en ligne.

```
controle-blanc/
├── web/        la page (une seule) : HTML, CSS, JavaScript
├── app/        le serveur : comptes, appels au modèle, quotas, corrigés
├── outils/     démonstrations autonomes, site statique, banc d'essai
└── tests/      143 tests
```

---

## Sur le nom du dépôt

Il s'appelle encore `btc-alert-bot` : c'était à l'origine un petit bot Telegram qui
surveillait le cours du Bitcoin, sans aucun rapport avec Repère. Ce bot a été supprimé,
et son code avec — il portait son jeton d'accès en clair dans un dépôt public, ce qui a
fini par lui coûter son compte. Ce qui reste ici est entièrement Repère.
