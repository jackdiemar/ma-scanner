#!/usr/bin/env bash
# run_ai_research_once.sh — Run one manual AI research pass on the VPS.
#
# Usage:
#   bash deploy/vps/run_ai_research_once.sh [LIMIT] [DEPTH]
#
# Defaults:
#   LIMIT=5
#   DEPTH=fast_gate

set -uo pipefail

INSTALL_DIR="/opt/ma-scanner"
ENV_FILE="${INSTALL_DIR}/config/.env"
LIMIT="${1:-5}"
DEPTH="${2:-fast_gate}"

echo "=== One-shot AI Research Run ==="
echo "Install dir: ${INSTALL_DIR}"
echo "Limit: ${LIMIT}"
echo "Depth: ${DEPTH}"
echo ""

cd "${INSTALL_DIR}" || exit 1

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  echo "config/.env found and sourced"
else
  echo "ERROR: config/.env missing at ${ENV_FILE}"
  exit 1
fi

echo "OPENAI_API_KEY set=$([[ -n "${OPENAI_API_KEY:-}" ]] && echo true || echo false)"
echo "AI_RESEARCH_ENABLED=${AI_RESEARCH_ENABLED:-not set}"
echo "AI_RESEARCH_DRY_RUN=${AI_RESEARCH_DRY_RUN:-not set}"
echo ""

echo "[1/3] Status"
python3 src/ai_research/run_ai_research.py --status
status_rc=$?
echo ""

echo "[2/3] Plan"
python3 src/ai_research/run_ai_research.py --latest --limit "${LIMIT}" --depth "${DEPTH}" --plan
plan_rc=$?
echo ""

if [[ "${status_rc}" -ne 0 || "${plan_rc}" -ne 0 ]]; then
  echo "Status or plan failed. Real run skipped."
  exit 1
fi

if [[ "${AI_RESEARCH_ENABLED:-false}" != "true" ]]; then
  echo "Real run skipped: AI_RESEARCH_ENABLED is not true."
  exit 0
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Real run skipped: OPENAI_API_KEY is not set."
  exit 0
fi

if [[ "${AI_RESEARCH_DRY_RUN:-true}" == "true" ]]; then
  echo "Real run skipped: AI_RESEARCH_DRY_RUN is true."
  exit 0
fi

echo "[3/3] Real one-shot AI research run"
python3 src/ai_research/run_ai_research.py --latest --limit "${LIMIT}" --depth "${DEPTH}"
