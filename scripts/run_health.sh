#!/usr/bin/env bash
set -euo pipefail

# Pick the exact Python you want launchd to use:
#  - Apple Silicon (brew): /opt/homebrew/bin/python3
#  - Intel (brew):         /usr/local/bin/python3
#  - Or your venv python:  /FULL/PATH/TO/venv/bin/python
PY="/Users/dmitry_v/dev/optionsTrader/venv/bin/python"

# Make sure PATH includes brew bins (not strictly required when PY is absolute)
#export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

exec "$PY" "/Users/dmitry_v/dev/optionsTrader/ibkr/check_ibkr_health.py"
