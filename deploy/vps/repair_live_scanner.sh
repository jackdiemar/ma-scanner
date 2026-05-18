#!/usr/bin/env bash
# repair_live_scanner.sh — Fix permissions, clear stale lock, restart service.
# Run as root or with sudo on the VPS when the scanner is stuck or hitting
# PermissionError on data dirs or the error log file.
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
ERROR_LOG="${DATA_DIR}/live_scanner_errors.log"
RUNNER="${INSTALL_DIR}/src/live_monitoring/live_scanner_runner.py"

echo "=== MA Scanner Repair ==="
echo "  Install dir : ${INSTALL_DIR}"
echo "  Service     : ${SERVICE}"
echo ""

# 1. Stop the service before touching anything
echo "[1/6] Stopping ${SERVICE} ..."
systemctl stop "${SERVICE}" 2>/dev/null && echo "      stopped" || echo "      (service not running or not installed)"

# 2. Create data dirs if missing
echo "[2/6] Ensuring data dirs exist ..."
mkdir -p "${DATA_DIR}" "${RUNS_DIR}" "${SCANS_DIR}"

# 3. Create/touch the error log file so FileHandler can open it
echo "[3/6] Creating/touching error log: ${ERROR_LOG} ..."
touch "${ERROR_LOG}"

# 4. Fix ownership and permissions
#    Service runs as root on most VPS setups; SUDO_USER is the original caller.
OWNER="${SUDO_USER:-root}"
echo "[4/6] Setting ownership to ${OWNER} on ${INSTALL_DIR}/data ..."
chown -R "${OWNER}:${OWNER}" "${INSTALL_DIR}/data"
chmod -R u+rwX "${INSTALL_DIR}/data"
chmod 600 "${ERROR_LOG}"

# 5. Clear stale lock file
echo "[5/6] Checking lock file ..."
if [[ -f "${LOCK_FILE}" ]]; then
    LOCK_PID=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")
    if [[ -n "${LOCK_PID}" ]] && kill -0 "${LOCK_PID}" 2>/dev/null; then
        echo "      WARNING: Scanner process IS running (PID ${LOCK_PID}). Lock NOT removed."
        echo "      Stop the process manually before running this script."
        exit 1
    else
        rm -f "${LOCK_FILE}"
        echo "      Stale lock removed (was PID ${LOCK_PID:-unknown})."
    fi
else
    echo "      No lock file present."
fi

# 6. Restart the service
echo "[6/6] Starting ${SERVICE} ..."
systemctl start "${SERVICE}" 2>/dev/null && echo "      started" || echo "      (service not installed — start manually)"

echo ""
echo "=== Post-Repair Validation ==="
echo ""

# Status check
echo "-- Status --"
python3 "${RUNNER}" --status 2>&1 || true

echo ""

# Dry run
echo "-- Dry run --"
python3 "${RUNNER}" --once --dry-run 2>&1 || true

echo ""
echo "=== Repair complete ==="
echo "  journalctl -u ${SERVICE} -n 40 --no-pager"
