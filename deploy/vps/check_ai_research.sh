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
PYTHON="${INSTALL_DIR}/.venv/bin/python"

AI_MODULES=(
  "src/ai_research/research_case_builder.py"
  "src/ai_research/llm_client.py"
  "src/ai_research/investment_gate.py"
  "src/ai_research/prompts.py"
  "src/ai_research/watchlist_manager.py"
  "src/ai_research/run_ai_research.py"
  "src/ai_research/ai_emailer.py"
)

echo "=== AI Research Layer VPS Check ==="
echo "Install dir : ${INSTALL_DIR}"
echo ""

if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "ERROR: install directory not found: ${INSTALL_DIR}"
  exit 1
fi

cd "${INSTALL_DIR}" || exit 1

# ─── [1] Config ───────────────────────────────────────────────────────────────
echo "[1/7] Configuration"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  echo "  config/.env found and sourced"
else
  echo "  WARNING: config/.env not found"
fi

echo "  AI_RESEARCH_ENABLED             : ${AI_RESEARCH_ENABLED:-not set}"
echo "  AI_RESEARCH_DRY_RUN             : ${AI_RESEARCH_DRY_RUN:-not set}"
echo "  OPENAI_API_KEY set              : $([[ -n "${OPENAI_API_KEY:-}" ]] && echo true || echo false)"
echo "  AI_MODEL                        : ${AI_MODEL:-not set}"
echo "  AI_RESEARCH_MAX_CASES_PER_RUN   : ${AI_RESEARCH_MAX_CASES_PER_RUN:-not set}"
echo "  AI_RESEARCH_DEFAULT_DEPTH       : ${AI_RESEARCH_DEFAULT_DEPTH:-not set}"
echo "  AI_EMAILS_ENABLED               : ${AI_EMAILS_ENABLED:-not set}"
echo "  AI_EMAIL_ON_EVERY_RUN           : ${AI_EMAIL_ON_EVERY_RUN:-not set}"
echo "  AI_EMAIL_SUBJECT_PREFIX         : ${AI_EMAIL_SUBJECT_PREFIX:-not set}"
echo ""

# ─── [2] Latest scanner alerts ────────────────────────────────────────────────
echo "[2/7] Scanner alert data"
LATEST_ALERTS="${INSTALL_DIR}/data/live_monitoring/latest_alerts.json"
ALERT_LOG="${INSTALL_DIR}/data/live_monitoring/live_alert_log.csv"
if [[ -f "${LATEST_ALERTS}" ]]; then
  alert_count=$(python3 -c "import json; d=json.load(open('${LATEST_ALERTS}')); print(len(d))" 2>/dev/null || echo "?")
  echo "  latest_alerts.json : found (${alert_count} alerts)"
elif [[ -f "${ALERT_LOG}" ]]; then
  row_count=$(tail -n +2 "${ALERT_LOG}" | wc -l | tr -d ' ')
  echo "  latest_alerts.json : missing — fallback to live_alert_log.csv (${row_count} rows)"
else
  echo "  WARNING: No scanner alert data found at ${LATEST_ALERTS}"
fi
echo ""

# ─── [3] Latest AI summary ────────────────────────────────────────────────────
echo "[3/7] Latest AI summary"
SUMMARY="${INSTALL_DIR}/data/ai_research/latest_ai_research_summary.md"
if [[ -f "${SUMMARY}" ]]; then
  mtime=$(stat -c '%y' "${SUMMARY}" 2>/dev/null || stat -f '%Sm' "${SUMMARY}" 2>/dev/null || echo "unknown")
  echo "  Found: ${SUMMARY}"
  echo "  Modified: ${mtime}"
else
  echo "  Not found: ${SUMMARY} (run --latest first)"
fi
echo ""

# ─── [4] AI timer status ──────────────────────────────────────────────────────
echo "[4/7] AI research timer (systemd)"
systemctl status ma-scanner-ai-research.timer 2>/dev/null || echo "  not installed"
echo ""

echo "  Next scheduled runs:"
systemctl list-timers 2>/dev/null | grep ma-scanner-ai || echo "  timer not installed"
echo ""

# ─── [5] Python compile checks ────────────────────────────────────────────────
echo "[5/7] Python compile check"
compile_failed=0
for module in "${AI_MODULES[@]}"; do
  if "${PYTHON}" -m py_compile "${module}" 2>/dev/null; then
    echo "  PASS ${module}"
  else
    echo "  FAIL ${module}"
    compile_failed=1
  fi
done
echo ""

# ─── [6] Status + plan ────────────────────────────────────────────────────────
echo "[6/7] AI status"
"${PYTHON}" src/ai_research/run_ai_research.py --status
status_rc=$?
echo ""

echo "[7/7] Dry-run + plan (limit 3)"
"${PYTHON}" src/ai_research/run_ai_research.py --latest --limit 3 --dry-run
dry_run_rc=$?
echo ""

"${PYTHON}" src/ai_research/run_ai_research.py --latest --limit 3 --plan
plan_rc=$?
echo ""

# ─── Summary ──────────────────────────────────────────────────────────────────
echo "=== Config to enable live AI research in config/.env ==="
echo "  AI_RESEARCH_ENABLED=true"
echo "  AI_RESEARCH_DRY_RUN=false"
echo "  AI_MODEL=gpt-4.1-mini"
echo "  AI_RESEARCH_MAX_CASES_PER_RUN=10"
echo "  AI_RESEARCH_DEFAULT_DEPTH=fast_gate"
echo "  AI_EMAILS_ENABLED=true"
echo "  AI_EMAIL_ON_EVERY_RUN=false"
echo "  AI_EMAIL_SUBJECT_PREFIX=MA Scanner AI Research Brief"
echo ""

echo "=== First real AI command ==="
echo "  cd ${INSTALL_DIR}"
echo "  ${PYTHON} src/ai_research/run_ai_research.py --latest --limit 5 --depth fast_gate --email"
echo ""

echo "=== Install timer ==="
echo "  sudo bash deploy/vps/install_ai_research_timer.sh ${INSTALL_DIR}"
echo "  sudo bash deploy/vps/install_ai_research_timer.sh ${INSTALL_DIR} --run-now"
echo ""

if [[ "${compile_failed}" -ne 0 || "${status_rc}" -ne 0 || "${dry_run_rc}" -ne 0 || "${plan_rc}" -ne 0 ]]; then
  echo "AI research check completed with failures."
  exit 1
fi

echo "AI research check completed successfully."
