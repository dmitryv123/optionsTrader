#!/usr/bin/env bash
set -euo pipefail

# --- CONFIG ---
USER_HOME="${HOME}"
LA_AGENTS_DIR="${USER_HOME}/Library/LaunchAgents"
LOG_DIR="${USER_HOME}/Library/Logs"

LIVE_PLIST="com.ibkr.gateway.live.plist"
PAPER_PLIST="com.ibkr.gateway.paper.plist"
HEALTH_PLIST="com.ibkr.gateway.health.plist"

HEALTH_LOG="${LOG_DIR}/ibkr_health.log"

AGENTS=(
  "${LA_AGENTS_DIR}/${LIVE_PLIST}"
  "${LA_AGENTS_DIR}/${PAPER_PLIST}"
  "${LA_AGENTS_DIR}/${HEALTH_PLIST}"
)

# --- FUNCTIONS ---
unload_agent() {
  local plist="$1"
  if [[ -f "${plist}" ]]; then
    # unload may error if not loaded — ignore errors
    launchctl unload "${plist}" 2>/dev/null || true
    echo "Unloaded: $(basename "${plist}")"
  else
    echo "WARNING: Missing plist: ${plist}"
  fi
}


load_agent() {
  local plist="$1"
  if [[ -f "${plist}" ]]; then
    launchctl load "${plist}"
    echo "Loaded:    $(basename "${plist}")"
  else
    echo "ERROR: Missing plist: ${plist}"
  fi
}

# --- MAIN ---
mkdir -p "${LOG_DIR}"

echo "== Unloading any existing agents =="
for a in "${AGENTS[@]}"; do
  unload_agent "${a}"
done


echo  "== Loading agents =="
for a in "${AGENTS[@]}"; do
  load_agent "${a}"
done

echo "== Active IBKR agents =="
launchctl list | grep -E "com\.ibkr\.gateway|com\.ibkr\.health" || echo "No agents found in launchctl list yet."

echo "== Tailing health log =="
echo "Log: ${HEALTH_LOG}"
touch "${HEALTH_LOG}"

# Clean exit on Ctrl+C
trap 'echo; echo "[manage_ibkr_agents] exiting..."; exit 0' INT TERM

# Show last 50 lines and follow
tail -n 50 -f "${HEALTH_LOG}"
