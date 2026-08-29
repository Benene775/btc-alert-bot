#!/usr/bin/env bash
# Démarrage local. Sans ANTHROPIC_API_KEY, l'application bascule en mode
# démonstration et le parcours reste entièrement cliquable.
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] && { set -a; . ./.env; set +a; }
exec python3 -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" "$@"
