#!/usr/bin/env bash
# run_ai_email_now.sh — Run AI research and send email, no scanner.
#
# Use when you already have fresh scanner output and want to re-run
# the AI gate and send the research email immediately.
#
# Usage:
#   bash deploy/vps/run_ai_email_now.sh [INSTALL_DIR] [LIMIT] [DEPTH]
#
# Defaults: INSTALL_DIR=/opt/ma-scanner, LIMIT=10, DEPTH=fast_gate

set -uo pipefail

INSTALL_DIR="${1:-/opt/ma-scanner}"
LIMIT="${2:-10}"
DEPTH="${3:-fast_gate}"

PYTHON="${INSTALL_DIR}/.venv/bin/python"
AI_RUNNER="${INSTALL_DIR}/src/ai_research/run_ai_research.py"
SUMMARY_PATH="${INSTALL_DIR}/data/ai_research/latest_ai_research_summary.md"

SEP="────────────────────────────────────────────────────────"

echo "${SEP}"
echo "  MA Scanner — AI Email Now"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Install dir : ${INSTALL_DIR}"
echo "  Limit       : ${LIMIT}"
echo "  Depth       : ${DEPTH}"
echo "${SEP}"

if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "ERROR: install directory not found: ${INSTALL_DIR}"; exit 1
fi
if [[ ! -f "${PYTHON}" ]]; then
  echo "ERROR: .venv not found: ${PYTHON}"; exit 1
fi

cd "${INSTALL_DIR}" || exit 1

# [1] Status check
echo ""
echo "[1/4] AI layer status"
"${PYTHON}" "${AI_RUNNER}" --status

# [2] Evidence audit with source fetch
echo ""
echo "[2/4] Evidence audit (with EDGAR fetch)"
set +e
AUDIT_OUT=$("${PYTHON}" "${AI_RUNNER}" \
  --latest --limit "${LIMIT}" --evidence-audit --fetch-text 2>&1)
AUDIT_RC=$?
set -e
echo "${AUDIT_OUT}"
if ! echo "${AUDIT_OUT}" | grep -qE 'Grade summary:.*[A-C]='; then
  echo ""
  echo "  ⚠  Evidence weak (all D/F). AI will enforce NEEDS_HUMAN_REVIEW on ESCALATE cases."
fi

# [3] AI research + email
echo ""
echo "[3/4] Running AI research gate + email"
set +e
"${PYTHON}" "${AI_RUNNER}" \
  --latest \
  --limit "${LIMIT}" \
  --depth "${DEPTH}" \
  --email \
  --strategic-brief \
  --include-completed-analogues \
  --probability-analysis
AI_RC=$?
set -e

if [[ "${AI_RC}" -ne 0 ]]; then
  echo "  ⚠  AI runner exited ${AI_RC}. Check config/.env for OPENAI_API_KEY / AI_RESEARCH_ENABLED."
fi

# [4] Print summary
echo ""
echo "[4/4] AI research summary"
echo "${SEP}"
if [[ -f "${SUMMARY_PATH}" ]]; then
  cat "${SUMMARY_PATH}"
else
  echo "  Summary not found: ${SUMMARY_PATH}"
fi

echo ""
echo "${SEP}"
echo "  Done. $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  For full cycle: sudo bash ${INSTALL_DIR}/deploy/vps/run_full_production_cycle.sh"
echo "${SEP}"
