#!/usr/bin/env bash
# install_ai_research_timer.sh — Install AI research systemd service and timer.
# Usage: sudo bash deploy/vps/install_ai_research_timer.sh [INSTALL_DIR] [--run-now]
#
# INSTALL_DIR defaults to /opt/ma-scanner.
# --run-now triggers an immediate one-shot run after the timer is enabled.

set -euo pipefail

INSTALL_DIR="${1:-/opt/ma-scanner}"
RUN_NOW=false
for arg in "$@"; do
  if [[ "${arg}" == "--run-now" ]]; then
    RUN_NOW=true
  fi
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_SRC="${SCRIPT_DIR}/ma-scanner-ai-research.service"
TIMER_SRC="${SCRIPT_DIR}/ma-scanner-ai-research.timer"
SERVICE_DEST="/etc/systemd/system/ma-scanner-ai-research.service"
TIMER_DEST="/etc/systemd/system/ma-scanner-ai-research.timer"

echo "=== Install AI Research Timer ==="
echo "Install dir : ${INSTALL_DIR}"
echo "Run now     : ${RUN_NOW}"
echo ""

if [[ ! -f "${SERVICE_SRC}" ]]; then
  echo "ERROR: service file not found: ${SERVICE_SRC}"
  exit 1
fi
if [[ ! -f "${TIMER_SRC}" ]]; then
  echo "ERROR: timer file not found: ${TIMER_SRC}"
  exit 1
fi

echo "[1/5] Copying unit files to /etc/systemd/system/"
cp "${SERVICE_SRC}" "${SERVICE_DEST}"
cp "${TIMER_SRC}"   "${TIMER_DEST}"

# Update WorkingDirectory and ExecStart paths if INSTALL_DIR differs from /opt/ma-scanner
if [[ "${INSTALL_DIR}" != "/opt/ma-scanner" ]]; then
  echo "  Patching install paths in service file..."
  sed -i "s|/opt/ma-scanner|${INSTALL_DIR}|g" "${SERVICE_DEST}"
fi

echo "[2/5] Reloading systemd daemon"
systemctl daemon-reload

echo "[3/5] Enabling timer (auto-start on boot)"
systemctl enable ma-scanner-ai-research.timer

echo "[4/5] Starting timer"
systemctl start ma-scanner-ai-research.timer

if [[ "${RUN_NOW}" == "true" ]]; then
  echo "[5/5] Running service now (one-shot)"
  systemctl start ma-scanner-ai-research.service
  echo "  Service started. Check logs with:"
  echo "    journalctl -u ma-scanner-ai-research.service -n 80 --no-pager"
else
  echo "[5/5] Skipped immediate run (no --run-now flag)"
fi

echo ""
echo "Next scheduled runs:"
systemctl list-timers | grep ma-scanner-ai || echo "  (timer list not available)"

echo ""
echo "Useful commands:"
echo "  Check timer     : systemctl status ma-scanner-ai-research.timer"
echo "  Check service   : systemctl status ma-scanner-ai-research.service"
echo "  Logs            : journalctl -u ma-scanner-ai-research.service -n 80 --no-pager"
echo "  Run now         : systemctl start ma-scanner-ai-research.service"
echo "  Uninstall       : sudo bash deploy/vps/uninstall_ai_research_timer.sh"
echo ""
echo "AI research timer installed successfully."
