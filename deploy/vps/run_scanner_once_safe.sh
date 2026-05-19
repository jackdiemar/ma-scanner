#!/usr/bin/env bash
# run_scanner_once_safe.sh — Repair permissions, run live scanner once, health check.
#
# Usage:
#   sudo bash deploy/vps/run_scanner_once_safe.sh [INSTALL_DIR] [TIMEOUT]
#
# Defaults: INSTALL_DIR=/opt/ma-scanner, TIMEOUT=1800

set -uo pipefail

INSTALL_DIR="${1:-/opt/ma-scanner}"
TIMEOUT="${2:-1800}"

PYTHON="${INSTALL_DIR}/.venv/bin/python"
SCANNER_RUNNER="${INSTALL_DIR}/src/live_monitoring/live_scanner_runner.py"
DATA_DIR="${INSTALL_DIR}/data"
LIVE_DIR="${DATA_DIR}/live_monitoring"
ERROR_LOG="${LIVE_DIR}/live_scanner_errors.log"
LOCK_FILE="${INSTALL_DIR}/live_scanner.lock"

SEP="────────────────────────────────────────────────────────"

echo "${SEP}"
echo "  MA Scanner — Safe Single Run"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Install dir : ${INSTALL_DIR}"
echo "  Timeout     : ${TIMEOUT}s"
echo "${SEP}"

if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "ERROR: install directory not found: ${INSTALL_DIR}"; exit 1
fi
if [[ ! -f "${PYTHON}" ]]; then
  echo "ERROR: .venv not found: ${PYTHON}"; exit 1
fi

cd "${INSTALL_DIR}" || exit 1

# Detect service user
SERVICE_USER="$(systemctl show ma-scanner-live.service -p User --value 2>/dev/null || echo '')"
if [[ -z "${SERVICE_USER}" ]]; then SERVICE_USER="root"; fi

# [1] Permissions repair
echo ""
echo "[1/3] Permissions repair"
mkdir -p "${LIVE_DIR}" "${LIVE_DIR}/runs" "${DATA_DIR}/scans"
touch "${ERROR_LOG}"
if [[ "${SERVICE_USER}" != "root" ]]; then
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}"
fi
chmod -R u+rwX "${DATA_DIR}"
chmod 600 "${ERROR_LOG}"
echo "  ✓ Permissions set (user=${SERVICE_USER})"

# Clear stale lock
if [[ -f "${LOCK_FILE}" ]]; then
  LOCK_PID="$(cat "${LOCK_FILE}" 2>/dev/null || echo '')"
  if [[ -n "${LOCK_PID}" ]] && kill -0 "${LOCK_PID}" 2>/dev/null; then
    echo "  ✗ Scanner already running (PID ${LOCK_PID}). Exiting."
    exit 1
  else
    rm -f "${LOCK_FILE}"
    echo "  ✓ Removed stale lock (PID ${LOCK_PID:-unknown})"
  fi
fi

# [2] Run scanner
echo ""
echo "[2/3] Live scanner run"
echo "  Command: ${PYTHON} ${SCANNER_RUNNER} --once --v12-timeout-seconds ${TIMEOUT}"
echo "  (This typically takes 5–20 minutes)"
echo ""

set +e
"${PYTHON}" "${SCANNER_RUNNER}" \
  --once \
  --v12-timeout-seconds "${TIMEOUT}"
SCANNER_RC=$?
set -e

if [[ "${SCANNER_RC}" -ne 0 ]]; then
  echo ""
  echo "  ✗ Scanner failed (exit ${SCANNER_RC})"
  echo ""
  echo "  Journal tail:"
  journalctl -u ma-scanner-live.service -n 80 --no-pager 2>/dev/null || true
  echo ""
  echo "  Error log:"
  tail -120 "${ERROR_LOG}" 2>/dev/null || true
  echo ""
  echo "  Next steps:"
  echo "    sudo bash ${INSTALL_DIR}/deploy/vps/repair_live_scanner.sh"
  echo "    sudo bash ${INSTALL_DIR}/deploy/vps/run_scanner_once_safe.sh"
  exit 1
fi
echo "  ✓ Scanner completed (exit 0)"

# [3] Health check
echo ""
echo "[3/3] Health check"
"${PYTHON}" src/live_monitoring/health_check.py 2>/dev/null || echo "  ⚠  Health check returned non-zero"

echo ""
echo "${SEP}"
echo "  Scanner run complete. $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Next: run AI email:"
echo "    bash ${INSTALL_DIR}/deploy/vps/run_ai_email_now.sh"
echo "  Or full cycle:"
echo "    sudo bash ${INSTALL_DIR}/deploy/vps/run_full_production_cycle.sh --skip-scanner"
echo "${SEP}"
