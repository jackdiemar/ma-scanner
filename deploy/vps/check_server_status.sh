#!/bin/bash
# check_server_status.sh — Show live scanner health on the VPS.
#
# Prints:
#   - systemd timer status (next fire time, last run)
#   - systemd service status (exit code, runtime)
#   - last 20 journal log lines
#   - Python health check output (if health_check.py exists)
#   - path and timestamp of latest review memo
#
# Usage: bash deploy/vps/check_server_status.sh
# No root required (journalctl may need systemd-journal group membership).

set -uo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/ma-scanner}"
VENV_PYTHON="$INSTALL_DIR/.venv/bin/python"
HEALTH_CHECK="$INSTALL_DIR/src/live_monitoring/health_check.py"
MEMO_PATH="$INSTALL_DIR/data/live_monitoring/latest_review_memo.md"
STATE_PATH="$INSTALL_DIR/data/live_monitoring/live_scanner_state.json"

SEP="──────────────────────────────────────────────────────"

echo "$SEP"
echo "MA Scanner — Server Status"
echo "$(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "$SEP"

# ── Timer status ──────────────────────────────────────────────────────────────
echo ""
echo "[TIMER]"
if systemctl list-timers ma-scanner-live.timer --no-pager 2>/dev/null | grep -q ma-scanner; then
  systemctl list-timers ma-scanner-live.timer --no-pager
else
  echo "  Timer not found — not installed. Run: sudo bash deploy/vps/install_systemd_service.sh"
fi

# ── Service status ────────────────────────────────────────────────────────────
echo ""
echo "[SERVICE]"
systemctl status ma-scanner-live.service --no-pager -l 2>/dev/null || \
  echo "  Service has not run yet or is not installed."

# ── Recent journal logs ───────────────────────────────────────────────────────
echo ""
echo "[LAST 20 LOG LINES]"
journalctl -u ma-scanner-live.service -n 20 --no-pager 2>/dev/null || \
  echo "  No journal logs found (run 'sudo journalctl ...' if permission denied)."

# ── State file ────────────────────────────────────────────────────────────────
echo ""
echo "[SCANNER STATE]"
if [[ -f "$STATE_PATH" ]]; then
  cat "$STATE_PATH"
else
  echo "  State file not found: $STATE_PATH"
  echo "  Scanner has not completed a run yet."
fi

# ── Python health check ───────────────────────────────────────────────────────
echo ""
echo "[HEALTH CHECK]"
if [[ -f "$HEALTH_CHECK" ]] && [[ -x "$VENV_PYTHON" ]]; then
  "$VENV_PYTHON" "$HEALTH_CHECK" 2>&1 || echo "  Health check returned non-zero exit."
elif [[ -f "$HEALTH_CHECK" ]]; then
  python3 "$HEALTH_CHECK" 2>&1 || echo "  Health check returned non-zero exit."
else
  echo "  health_check.py not found at $HEALTH_CHECK"
fi

# ── Latest review memo ────────────────────────────────────────────────────────
echo ""
echo "[LATEST REVIEW MEMO]"
if [[ -f "$MEMO_PATH" ]]; then
  echo "  Path: $MEMO_PATH"
  echo "  Modified: $(stat -c '%y' "$MEMO_PATH" 2>/dev/null || stat -f '%Sm' "$MEMO_PATH" 2>/dev/null)"
  echo ""
  echo "  --- Memo summary (first 40 lines) ---"
  head -40 "$MEMO_PATH"
else
  echo "  Memo not found: $MEMO_PATH"
  echo "  Scanner has not completed a run yet."
fi

echo ""
echo "$SEP"
