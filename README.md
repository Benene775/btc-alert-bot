# btc-alert-bot

Petit bot Telegram qui surveille le cours du Bitcoin et alerte au-delà de 2 % de
variation (`bot.py`).

## Configuration

Le jeton du bot et l'identifiant de conversation se posent dans l'environnement,
jamais dans le code — voir `.env.example` :

```
cp .env.example .env      # puis remplir
set -a && . ./.env && set +a
python3 bot.py
```

> **Le jeton présent dans `bot.py` jusqu'au 29 août 2026 doit être considéré comme
> compromis** : il était en clair dans un dépôt public. Le révoquer via @BotFather
> (`/mybots` → le bot → *API Token* → *Revoke current token*). Le retirer du code ne
> suffit pas : l'historique git le garde.

## Autre projet dans ce dépôt

`controle-blanc/` — outil de révision par contrôle blanc : un élève photographie son
cours, passe un contrôle au format réel de la matière, obtient une correction commentée
puis des fiches ciblées. Voir [controle-blanc/README.md](controle-blanc/README.md).
