#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/dev/optionsTrader"

if [ -f "$APP_DIR/.optionsTrader_env" ]; then
  # shellcheck disable=SC1090
  . "$APP_DIR/.optionsTrader_env"
fi

RUN="$APP_DIR/scripts/sync_both.sh"
NOTIFY="$APP_DIR/scripts/notify_email.py"
PY="$APP_DIR/venv/bin/python"

WHEN="${1:-manual}"         # scheduled-morning | scheduled-evening | manual
TARGET="${2:-both}"         # live | paper | both

LOG_DIR="$APP_DIR/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/mirror_$(date +%Y%m%d_%H%M%S)_${TARGET}.log"

LIVE_HOST=127.0.0.1; LIVE_PORT=4001; LIVE_LABEL="LIVE GW (4001)"
PAPER_HOST=127.0.0.1; PAPER_PORT=4002; PAPER_LABEL="PAPER GW (4002)"

check_port() {
  if command -v nc >/dev/null 2>&1; then nc -z -G 3 "$1" "$2" >/dev/null 2>&1
  else (echo > /dev/tcp/"$1"/"$2") >/dev/null 2>&1; fi
}

fail_and_email() {
  local subject="$1" body="$2"
  echo "ERROR: $subject" | tee -a "$LOG"
  echo -e "$body" | tee -a "$LOG"
  "$PY" "$NOTIFY" "[optionsTrader] Mirror PRECHECK FAILED (${TARGET})" "$subject"$'\n\n'"$body"
  exit 1
}

# --------- Precheck ----------
{
  echo "=== Precheck start $(date -u)Z [$WHEN][$TARGET] ==="
  ok_live=1; ok_paper=1
  if [[ "$TARGET" == "live" || "$TARGET" == "both" ]]; then
    if check_port "$LIVE_HOST" "$LIVE_PORT"; then echo "[OK] $LIVE_LABEL"; else echo "[FAIL] $LIVE_LABEL"; ok_live=0; fi
  fi
  if [[ "$TARGET" == "paper" || "$TARGET" == "both" ]]; then
    if check_port "$PAPER_HOST" "$PAPER_PORT"; then echo "[OK] $PAPER_LABEL"; else echo "[FAIL] $PAPER_LABEL"; ok_paper=0; fi
  fi
  if [[ ( "$TARGET" == "live"  && $ok_live  -ne 1 ) || \
        ( "$TARGET" == "paper" && $ok_paper -ne 1 ) || \
        ( "$TARGET" == "both"  && ( $ok_live -ne 1 || $ok_paper -ne 1 ) ) ]]; then
    msg="Connectivity failed at $(date -u)Z\n\nResults:\n- $LIVE_LABEL: $([[ $ok_live -eq 1 ]] && echo OK || echo FAIL)\n- $PAPER_LABEL: $([[ $ok_paper -eq 1 ]] && echo OK || echo FAIL)"
    fail_and_email "IB API connectivity issue ($TARGET)" "$msg"
  fi
  echo "=== Precheck OK $(date -u)Z ==="
} >>"$LOG" 2>&1

# --------- Run ----------
{
  echo "=== Mirror start $(date -u)Z [$WHEN][$TARGET] ==="
  if "$RUN" "$WHEN" "$TARGET"; then
    echo "=== Mirror OK $(date -u)Z ==="
  else
    echo "=== Mirror FAILED $(date -u)Z ==="
    exit 1
  fi
  #"$RUN" "$WHEN" "$TARGET"
  #echo "=== Mirror OK $(date -u)Z ==="
} >>"$LOG" 2>&1 || {
  TAIL=$(tail -n 200 "$LOG")
  "$PY" "$NOTIFY" "[optionsTrader] Mirror FAILED [$WHEN][$TARGET]" "Failed at $(date -u)Z\n\nLast log:\n\n$TAIL"
  exit 1
}

