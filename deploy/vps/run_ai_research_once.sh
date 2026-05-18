#!/usr/bin/env bash
# run_ai_research_once.sh — Manual one-shot AI research run.
# Usage: bash deploy/vps/run_ai_research_once.sh [LIMIT] [DEPTH] [INSTALL_DIR]
# Defaults: LIMIT=5, DEPTH=fast_gate, INSTALL_DIR=/opt/ma-scanner

set -uo pipefail

LIMIT="${1:-5}"
DEPTH="${2:-fast_gate}"
INSTALL_DIR="${3:-/opt/ma-scanner}"
ENV_FILE="${INSTALL_DIR}/config/.env"
PYTHON="${INSTALL_DIR}/.venv/bin/python"
RUNNER="${INSTALL_DIR}/src/ai_research/run_ai_research.py"

echo "=== One-shot AI Research Run ==="
echo "Install dir : ${INSTALL_DIR}"
echo "Limit       : ${LIMIT}"
echo "Depth       : ${DEPTH}"
echo ""

# Verify install dir and venv
if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "ERROR: install directory not found: ${INSTALL_DIR}"
  exit 1
fi

if [[ ! -f "${PYTHON}" ]]; then
  echo "ERROR: .venv not found at ${INSTALL_DIR}/.venv"
  echo "  Run: python3 -m venv ${INSTALL_DIR}/.venv && ${INSTALL_DIR}/.venv/bin/pip install -r requirements.txt"
  exit 1
fi

cd "${INSTALL_DIR}" || exit 1

# Source env
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  echo "config/.env sourced"
else
  echo "WARNING: config/.env not found at ${ENV_FILE}"
fi

echo "AI_RESEARCH_ENABLED  : ${AI_RESEARCH_ENABLED:-not set}"
echo "AI_RESEARCH_DRY_RUN  : ${AI_RESEARCH_DRY_RUN:-not set}"
echo "OPENAI_API_KEY set   : $([[ -n "${OPENAI_API_KEY:-}" ]] && echo true || echo false)"
echo ""

# [1/3] Status
echo "[1/3] Status"
"${PYTHON}" "${RUNNER}" --status
status_rc=$?
echo ""

# [2/3] Plan (no files written, no LLM calls)
echo "[2/3] Plan preview"
"${PYTHON}" "${RUNNER}" --latest --limit "${LIMIT}" --depth "${DEPTH}" --plan
plan_rc=$?
echo ""

if [[ "${status_rc}" -ne 0 || "${plan_rc}" -ne 0 ]]; then
  echo "Status or plan failed. Real run skipped."
  exit 1
fi

# [3/3] Live or dry-run
LIVE_OK=true
SKIP_REASON=""

if [[ "${AI_RESEARCH_ENABLED:-false}" != "true" ]]; then
  LIVE_OK=false
  SKIP_REASON="AI_RESEARCH_ENABLED is not true"
elif [[ -z "${OPENAI_API_KEY:-}" ]]; then
  LIVE_OK=false
  SKIP_REASON="OPENAI_API_KEY is not set"
elif [[ "${AI_RESEARCH_DRY_RUN:-true}" == "true" ]]; then
  LIVE_OK=false
  SKIP_REASON="AI_RESEARCH_DRY_RUN is true"
fi

if [[ "${LIVE_OK}" == "true" ]]; then
  echo "[3/3] Live AI research run (--email included)"
  "${PYTHON}" "${RUNNER}" --latest --limit "${LIMIT}" --depth "${DEPTH}" --email
else
  echo "[3/3] Dry-run (live skipped: ${SKIP_REASON})"
  "${PYTHON}" "${RUNNER}" --latest --limit "${LIMIT}" --depth "${DEPTH}" --dry-run
  echo ""
  echo "To run live, set in config/.env:"
  echo "  AI_RESEARCH_ENABLED=true"
  echo "  AI_RESEARCH_DRY_RUN=false"
  echo "  OPENAI_API_KEY=sk-..."
fi
