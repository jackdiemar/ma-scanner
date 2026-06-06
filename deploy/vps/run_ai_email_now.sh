#!/usr/bin/env bash
# run_ai_email_now.sh — Run AI research at diligence_memo depth and send email.
#
# Does NOT re-run the live scanner. Uses existing scanner output.
# Runs at diligence_memo depth: fetches filing text, produces full research memo.
#
# Usage:
#   bash deploy/vps/run_ai_email_now.sh [INSTALL_DIR] [LIMIT] [DEPTH]
#
# Defaults: INSTALL_DIR=/opt/ma-scanner, LIMIT=10, DEPTH=diligence_memo

set -uo pipefail

INSTALL_DIR="${1:-/opt/ma-scanner}"
LIMIT="${2:-10}"
DEPTH="${3:-diligence_memo}"

PYTHON="${INSTALL_DIR}/.venv/bin/python"
AI_RUNNER="${INSTALL_DIR}/src/ai_research/run_ai_research.py"
SUMMARY_PATH="${INSTALL_DIR}/data/ai_research/latest_ai_research_summary.md"
QUEUE_PATH="${INSTALL_DIR}/data/ai_research/latest_opportunity_queue.json"
QUEUE_MD_PATH="${INSTALL_DIR}/data/ai_research/latest_opportunity_queue.md"

SEP="────────────────────────────────────────────────────────"

echo "${SEP}"
echo "  MA Scanner — AI Email Now (diligence_memo depth)"
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
echo "[1/5] AI layer status"
"${PYTHON}" "${AI_RUNNER}" --status

# [2] Opportunity plan (no LLM, no files)
echo ""
echo "[2/5] Opportunity plan (pre-run preview)"
set +e
"${PYTHON}" "${AI_RUNNER}" \
  --latest --limit "${LIMIT}" --opportunity-plan 2>&1
set -e

# [3] Evidence audit with source fetch
echo ""
echo "[3/5] Evidence audit (with EDGAR fetch)"
set +e
AUDIT_OUT=$("${PYTHON}" "${AI_RUNNER}" \
  --latest --limit "${LIMIT}" --evidence-audit --fetch-text 2>&1)
AUDIT_RC=$?
set -e
echo "${AUDIT_OUT}"
if ! echo "${AUDIT_OUT}" | grep -qE 'Grade summary:.*[A-C]='; then
  echo ""
  echo "  ⚠  Evidence weak (all D/F). AI will enforce NEEDS_HUMAN_REVIEW on ESCALATE cases."
  echo "  ⚠  diligence_memo depth will attempt to fetch filing text to improve evidence grade."
fi

# [4] AI research + email (diligence_memo depth, force-refresh for active cases)
echo ""
echo "[4/5] Running AI research gate (${DEPTH} depth) + email"
echo "       Note: --force-refresh ensures fresh diligence analysis (bypasses LLM cache)"
set +e
"${PYTHON}" "${AI_RUNNER}" \
  --latest \
  --limit "${LIMIT}" \
  --depth "${DEPTH}" \
  --email \
  --strategic-brief \
  --include-completed-analogues \
  --probability-analysis \
  --opportunity-mode \
  --force-refresh
AI_RC=$?
set -e

if [[ "${AI_RC}" -ne 0 ]]; then
  echo "  ⚠  AI runner exited ${AI_RC}. Check config/.env for OPENAI_API_KEY / AI_RESEARCH_ENABLED."
fi

# [5] Print summary and paths
echo ""
echo "[5/5] Results"
echo "${SEP}"

if [[ -f "${SUMMARY_PATH}" ]]; then
  echo "  Summary:"
  cat "${SUMMARY_PATH}"
else
  echo "  Summary not found: ${SUMMARY_PATH}"
fi

echo ""
echo "  Key output paths:"
echo "    AI summary     : ${SUMMARY_PATH}"
echo "    Opportunity Q  : ${QUEUE_PATH}"
echo "    Queue markdown : ${QUEUE_MD_PATH}"

if [[ "${AI_RC}" -eq 0 ]]; then
  echo "    Email sent     : YES (check inbox)"
else
  echo "    Email sent     : NO (AI runner failed — check OPENAI_API_KEY and AI_EMAILS_ENABLED)"
fi

echo ""
echo "${SEP}"
echo "  Done. $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  For full cycle: sudo bash ${INSTALL_DIR}/deploy/vps/run_full_production_cycle.sh"
echo "  For preview only (no send): ${PYTHON} ${AI_RUNNER} --email-preview --latest --limit ${LIMIT} --depth ${DEPTH} --strategic-brief --opportunity-mode"
echo "${SEP}"
