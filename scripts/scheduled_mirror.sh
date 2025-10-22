#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/dev/optionsTrader"
RUN="$APP_DIR/scripts/sync_both.sh"         # not backend/scripts unless you really keep it there
NOTIFY="$APP_DIR/scripts/notify_email.py"
PY="$APP_DIR/venv/bin/python"
LOG_DIR="$APP_DIR/logs"


# Load env (SMTP, etc.)
[ -f "$HOME/.optionsTrader_env" ] && . "$HOME/.optionsTrader_env"

# ---- paths (adjust if your files truly live under backend/) ----
RUN="$APP_DIR/scripts/sync_both.sh"
NOTIFY="$APP_DIR/scripts/notify_email.py"
PY="$APP_DIR/venv/bin/python"

WHEN="${1:-manual}"         # scheduled-morning | scheduled-evening | manual
TARGET="${2:-both}"         # live | paper | both

# Logs (pick one place; I recommend inside the app)
LOG_DIR="$APP_DIR/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/mirror_$(date +%Y%m%d_%H%M%S)_${TARGET}.log"

# Optional: per-target run lock to avoid overlap
LOCK_DIR="/tmp/ot_mirror_${TARGET}.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Another ${TARGET} mirror is running (lock at $LOCK_DIR). Exiting." | tee -a "$LOG"
  exit 0
fi
trap 'r=$?; rm -rf "$LOCK_DIR"; exit $r' EXIT

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

# --------- TCP precheck (non-API) ----------
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
    fail_and_email "IB API TCP connectivity issue ($TARGET)" "$msg"
  fi
  echo "=== Precheck OK $(date -u)Z ==="
} >>"$LOG" 2>&1

# Small cushion before opening API session (prevents back-to-back connect flakiness)
sleep 2

# --------- Single mirror run ----------
{
  echo "=== Mirror start $(date -u)Z [$WHEN][$TARGET] ==="
  if "$RUN" "$WHEN" "$TARGET"; then
    echo "=== Mirror OK $(date -u)Z ==="
  else
    echo "=== Mirror FAILED $(date -u)Z ==="
    exit 1
  fi
} >>"$LOG" 2>&1 || {
  TAIL=$(tail -n 200 "$LOG")
  "$PY" "$NOTIFY" "[optionsTrader] Mirror FAILED [$WHEN][$TARGET]" \
    "Failed at $(date -u)Z\n\nLast log:\n\n$TAIL"
  exit 1
}









#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/dev/optionsTrader"

if [ -f "$HOME/.optionsTrader_env" ]; then
  # shellcheck disable=SC1090
  . "$HOME/.optionsTrader_env"
fi

RUN="$APP_DIR/backend/scripts/sync_both.sh"
NOTIFY="$APP_DIR/backend/scripts/notify_email.py"
PY="$APP_DIR/venv/bin/python"

WHEN="${1:-manual}"         # scheduled-morning | scheduled-evening | manual
TARGET="${2:-both}"         # live | paper | both

#LOG_DIR="$APP_DIR/logs"; mkdir -p "$LOG_DIR"
LOG_DIR="$HOME/logs"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/mirror_$(date +%Y%m%d_%H%M%S)_${TARGET}.log"

LIVE_HOST=127.0.0.1; LIVE_PORT=4001; LIVE_LABEL="LIVE GW (4001)"

# echo "$RUN" "$WHEN" "$TARGET"
# "$RUN" "$WHEN" "$TARGET"

# exit

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

