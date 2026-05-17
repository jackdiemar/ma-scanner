#!/bin/bash
# post_deploy_check.sh — Read-only post-bootstrap status report.
#
# Usage:
#   bash /opt/ma-scanner/deploy/vps/post_deploy_check.sh

set -uo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/ma-scanner}"
VENV_PYTHON="$INSTALL_DIR/.venv/bin/python"
HEALTH_CHECK="$INSTALL_DIR/src/live_monitoring/health_check.py"
ENV_FILE="$INSTALL_DIR/config/.env"
MEMO_DIR="$INSTALL_DIR/data/live_monitoring"
MEMO_PATH="$MEMO_DIR/latest_review_memo.md"
ALERT_LOG="$MEMO_DIR/live_alert_log.csv"
STATE_PATH="$MEMO_DIR/live_scanner_state.json"

SEP="──────────────────────────────────────────────────────"

section() {
  echo ""
  echo "$SEP"
  echo "$1"
  echo "$SEP"
}

echo "$SEP"
echo "MA Scanner — Post Deploy Check"
echo "$(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Install dir: $INSTALL_DIR"
echo "$SEP"

section "Git Commit"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" log --oneline -1
  echo "Branch: $(git -C "$INSTALL_DIR" branch --show-current 2>/dev/null || echo unknown)"
else
  echo "Repo metadata not found at $INSTALL_DIR/.git"
fi

section "Config"
if [[ -f "$ENV_FILE" ]]; then
  echo "config/.env: present"
  perms="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE" 2>/dev/null || echo unknown)"
  echo "config/.env permissions: $perms"
  if grep -q '^FMP_API_KEY=.\+' "$ENV_FILE"; then
    echo "FMP_API_KEY: set (value hidden)"
  else
    echo "FMP_API_KEY: missing or blank"
  fi
else
  echo "config/.env: missing"
  echo "FMP_API_KEY: missing"
fi

section "Systemd Timer"
systemctl list-timers ma-scanner-live.timer --no-pager 2>/dev/null || echo "Timer not installed or systemd unavailable."
echo ""
systemctl status ma-scanner-live.timer --no-pager -l 2>/dev/null || echo "Timer status unavailable."

section "Last Service Status"
systemctl status ma-scanner-live.service --no-pager -l 2>/dev/null || echo "Service has not run yet or is not installed."

section "Last 30 Journal Lines"
journalctl -u ma-scanner-live.service -n 30 --no-pager 2>/dev/null || echo "No journal logs found or permission denied."

section "Health Check"
if [[ -x "$VENV_PYTHON" ]] && [[ -f "$HEALTH_CHECK" ]]; then
  "$VENV_PYTHON" "$HEALTH_CHECK" || echo "Health check returned non-zero."
elif [[ -f "$HEALTH_CHECK" ]]; then
  python3 "$HEALTH_CHECK" || echo "Health check returned non-zero."
else
  echo "health_check.py not found at $HEALTH_CHECK"
fi

section "Latest Outputs"
if [[ -f "$MEMO_PATH" ]]; then
  echo "Latest memo path: $MEMO_PATH"
  echo "Latest memo modified: $(stat -c '%y' "$MEMO_PATH" 2>/dev/null || stat -f '%Sm' "$MEMO_PATH" 2>/dev/null)"
else
  echo "Latest memo path: not found ($MEMO_PATH)"
fi

if [[ -f "$ALERT_LOG" ]]; then
  echo "Latest alert log path: $ALERT_LOG"
  echo "Alert log modified: $(stat -c '%y' "$ALERT_LOG" 2>/dev/null || stat -f '%Sm' "$ALERT_LOG" 2>/dev/null)"
else
  echo "Latest alert log path: not found ($ALERT_LOG)"
fi

if [[ -f "$STATE_PATH" ]]; then
  echo "State path: $STATE_PATH"
else
  echo "State path: not found ($STATE_PATH)"
fi

section "Useful Commands"
echo "View logs:"
echo "  journalctl -u ma-scanner-live.service -n 50 --no-pager"
echo "Follow logs:"
echo "  journalctl -u ma-scanner-live.service -f"
echo "Check timer:"
echo "  systemctl list-timers ma-scanner-live.timer"
echo "Pause timer:"
echo "  sudo systemctl stop ma-scanner-live.timer"
echo "Uninstall:"
echo "  sudo bash $INSTALL_DIR/deploy/vps/uninstall_systemd_service.sh"
