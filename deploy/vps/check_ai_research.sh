#!/usr/bin/env bash
# check_ai_research.sh — Verify AI research readiness on the VPS.
#
# Usage:
#   bash deploy/vps/check_ai_research.sh [INSTALL_DIR]
#
# INSTALL_DIR defaults to /opt/ma-scanner.

set -uo pipefail

INSTALL_DIR="${1:-/opt/ma-scanner}"
ENV_FILE="${INSTALL_DIR}/config/.env"

AI_MODULES=(
  "src/ai_research/research_case_builder.py"
  "src/ai_research/llm_client.py"
  "src/ai_research/investment_gate.py"
  "src/ai_research/prompts.py"
  "src/ai_research/watchlist_manager.py"
  "src/ai_research/run_ai_research.py"
)

echo "=== AI Research Layer VPS Check ==="
echo "Install dir: ${INSTALL_DIR}"
echo ""

if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "ERROR: install directory not found: ${INSTALL_DIR}"
  exit 1
fi

cd "${INSTALL_DIR}" || exit 1

echo "[1/5] Loading config"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  echo "  config/.env found and sourced"
else
  echo "  config/.env missing"
fi
echo "  AI_RESEARCH_ENABLED=${AI_RESEARCH_ENABLED:-not set}"
echo "  AI_RESEARCH_DRY_RUN=${AI_RESEARCH_DRY_RUN:-not set}"
echo "  OPENAI_API_KEY set=$([[ -n "${OPENAI_API_KEY:-}" ]] && echo true || echo false)"
echo "  AI_MODEL=${AI_MODEL:-not set}"
echo "  AI_RESEARCH_MAX_CASES_PER_RUN=${AI_RESEARCH_MAX_CASES_PER_RUN:-not set}"
echo "  AI_RESEARCH_DEFAULT_DEPTH=${AI_RESEARCH_DEFAULT_DEPTH:-not set}"
echo ""

echo "[2/5] Python compile check"
compile_failed=0
for module in "${AI_MODULES[@]}"; do
  if python3 -m py_compile "${module}"; then
    echo "  PASS ${module}"
  else
    echo "  FAIL ${module}"
    compile_failed=1
  fi
done
echo ""

echo "[3/5] AI status"
python3 src/ai_research/run_ai_research.py --status
status_rc=$?
echo ""

echo "[4/5] AI dry-run"
python3 src/ai_research/run_ai_research.py --latest --limit 5 --dry-run
dry_run_rc=$?
echo ""

echo "[5/5] AI plan"
python3 src/ai_research/run_ai_research.py --latest --limit 5 --plan
plan_rc=$?
echo ""

echo "Config lines to enable live AI research in config/.env:"
echo "AI_RESEARCH_ENABLED=true"
echo "AI_RESEARCH_DRY_RUN=false"
echo "AI_MODEL=gpt-4.1-mini"
echo "AI_RESEARCH_MAX_CASES_PER_RUN=10"
echo "AI_RESEARCH_DEFAULT_DEPTH=fast_gate"
echo ""
echo "First real manual AI command:"
echo "cd ${INSTALL_DIR}"
echo "python3 src/ai_research/run_ai_research.py --latest --limit 5 --depth fast_gate"
echo ""
echo "This script does not schedule AI research."

if [[ "${compile_failed}" -ne 0 || "${status_rc}" -ne 0 || "${dry_run_rc}" -ne 0 || "${plan_rc}" -ne 0 ]]; then
  echo ""
  echo "AI research check completed with failures."
  exit 1
fi

echo ""
echo "AI research check completed successfully."
