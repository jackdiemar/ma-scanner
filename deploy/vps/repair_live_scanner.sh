#!/usr/bin/env bash
# repair_live_scanner.sh — Fix permissions, clear stale lock, restart service.
# Run as root or with sudo on the VPS when the scanner is stuck or hitting
# PermissionError on data dirs.
#
# Usage:
#   sudo bash deploy/vps/repair_live_scanner.sh [INSTALL_DIR]
#
# INSTALL_DIR defaults to /opt/ma-scanner.

set -euo pipefail

INSTALL_DIR="${1:-/opt/ma-scanner}"
SERVICE="ma-scanner-live.service"
LOCK_FILE="${INSTALL_DIR}/live_scanner.lock"
DATA_DIR="${INSTALL_DIR}/data/live_monitoring"
RUNS_DIR="${DATA_DIR}/runs"
SCANS_DIR="${INSTALL_DIR}/data/scans"

echo "=== MA Scanner Repair ==="
echo "  Install dir : ${INSTALL_DIR}"
echo "  Service     : ${SERVICE}"
echo ""

# 1. Stop the service before touching anything
echo "[1/5] Stopping ${SERVICE} ..."
systemctl stop "${SERVICE}" 2>/dev/null && echo "      stopped" || echo "      (service not running or not installed)"

# 2. Create data dirs if missing
echo "[2/5] Ensuring data dirs exist ..."
mkdir -p "${DATA_DIR}" "${RUNS_DIR}" "${SCANS_DIR}"

# 3. Fix ownership (service runs as the user who installed it; default: root)
OWNER="${SUDO_USER:-root}"
echo "[3/5] Setting ownership to ${OWNER} on ${INSTALL_DIR}/data ..."
chown -R "${OWNER}:${OWNER}" "${INSTALL_DIR}/data"
chmod -R 755 "${INSTALL_DIR}/data"

# 4. Clear stale lock file
if [[ -f "${LOCK_FILE}" ]]; then
    LOCK_PID=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")
    if [[ -n "${LOCK_PID}" ]] && kill -0 "${LOCK_PID}" 2>/dev/null; then
        echo "[4/5] WARNING: Scanner process IS running (PID ${LOCK_PID}). Lock NOT removed."
        echo "      Stop the process manually before running this script."
        exit 1
    else
        rm -f "${LOCK_FILE}"
        echo "[4/5] Stale lock removed (was PID ${LOCK_PID:-unknown})."
    fi
else
    echo "[4/5] No lock file present."
fi

# 5. Restart the service
echo "[5/5] Starting ${SERVICE} ..."
systemctl start "${SERVICE}" 2>/dev/null && echo "      started" || echo "      (service not installed — start manually)"

echo ""
echo "Repair complete. Check status:"
echo "  python3 ${INSTALL_DIR}/src/live_monitoring/live_scanner_runner.py --status"
echo "  journalctl -u ${SERVICE} -n 40 --no-pager"
