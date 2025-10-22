#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/dev/optionsTrader"
PY="$APP_DIR/venv/bin/python"
MANAGE="$APP_DIR/manage.py"

WHEN="${1:-manual}"        # scheduled-morning | scheduled-evening | manual
TARGET="${2:-both}"        # live | paper | both

cd "$APP_DIR"

if [[ "$TARGET" == "live" || "$TARGET" == "both" ]]; then
echo  "$PY" "$MANAGE" sync_ibkr --host 127.0.0.1 --port 4001 --client-id 51 \
    --skip-orders --readonly --source "$WHEN"

"$PY" "$MANAGE" sync_ibkr --host 127.0.0.1 --port 4001 --client-id 51 --skip-orders --readonly --source "$WHEN"
fi

if [[ "$TARGET" == "paper" || "$TARGET" == "both" ]]; then
  "$PY" "$MANAGE" sync_ibkr --host 127.0.0.1 --port 4002 --client-id 402 --skip-orders --readonly --source "$WHEN"
fi

