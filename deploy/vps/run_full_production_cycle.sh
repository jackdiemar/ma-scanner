#!/usr/bin/env bash
# run_full_production_cycle.sh — One-command VPS production operator cycle.
#
# Runs in order: git pull → permissions repair → syntax check →
# live scanner → evidence audit → AI research email → health check.
# Optionally installs timers at the end.
#
# Usage:
#   sudo bash deploy/vps/run_full_production_cycle.sh [OPTIONS]
#
# Options:
#   --skip-git-pull          Skip git pull (use if already on correct commit)
#   --skip-scanner           Skip scanner run (use existing alert data)
#   --skip-ai                Skip AI research + email (scanner only)
#   --install-ai-timer       Install/restart AI research systemd timer after run
#   --restart-scanner-timer  Start ma-scanner-live.timer after run
#   --limit N                Max alerts for AI (default: 10)
#   --timeout N              Scanner V12 timeout in seconds (default: 1800)
#   --depth DEPTH            AI depth: fast_gate|deep (default: fast_gate)
#   --branch BRANCH          Git branch to pull (default: ai-final)
#
# Logs: data/live_monitoring/operator_runs/operator_run_YYYY-MM-DD_HHMM.log

set -uo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
INSTALL_DIR="${INSTALL_DIR:-/opt/ma-scanner}"
BRANCH="ai-final"
LIMIT=10
TIMEOUT=1800
DEPTH="fast_gate"
SKIP_GIT=false
SKIP_SCANNER=false
SKIP_AI=false
INSTALL_AI_TIMER=false
RESTART_SCANNER_TIMER=false

# ── Arg parsing ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-git-pull)        SKIP_GIT=true ;;
    --skip-scanner)         SKIP_SCANNER=true ;;
    --skip-ai)              SKIP_AI=true ;;
    --install-ai-timer)     INSTALL_AI_TIMER=true ;;
    --restart-scanner-timer) RESTART_SCANNER_TIMER=true ;;
    --limit)                LIMIT="${2}"; shift ;;
    --timeout)              TIMEOUT="${2}"; shift ;;
    --depth)                DEPTH="${2}"; shift ;;
    --branch)               BRANCH="${2}"; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

# ── Paths ─────────────────────────────────────────────────────────────────────
PYTHON="${INSTALL_DIR}/.venv/bin/python"
SCANNER_RUNNER="${INSTALL_DIR}/src/live_monitoring/live_scanner_runner.py"
AI_RUNNER="${INSTALL_DIR}/src/ai_research/run_ai_research.py"
ENV_FILE="${INSTALL_DIR}/config/.env"
DATA_DIR="${INSTALL_DIR}/data"
LIVE_DIR="${DATA_DIR}/live_monitoring"
RUNS_DIR="${LIVE_DIR}/operator_runs"
AI_DIR="${DATA_DIR}/ai_research"
SOURCE_CACHE_DIR="${AI_DIR}/source_cache"
AI_CACHE_DIR="${AI_DIR}/cache"
SUMMARY_PATH="${AI_DIR}/latest_ai_research_summary.md"
ERROR_LOG="${LIVE_DIR}/live_scanner_errors.log"
LOCK_FILE="${INSTALL_DIR}/live_scanner.lock"

TS="$(date '+%Y-%m-%d_%H%M')"
LOG_FILE="${RUNS_DIR}/operator_run_${TS}.log"

SEP="════════════════════════════════════════════════════════"

# ── Logging setup ─────────────────────────────────────────────────────────────
mkdir -p "${RUNS_DIR}"
exec > >(tee -a "${LOG_FILE}") 2>&1

section() {
  echo ""
  echo "${SEP}"
  echo "  $1"
  echo "${SEP}"
}

ok()   { echo "  ✓ $1"; }
warn() { echo "  ⚠  $1"; }
fail() { echo "  ✗ $1"; }

# ── Header ────────────────────────────────────────────────────────────────────
echo "${SEP}"
echo "  MA Scanner — Full Production Cycle"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Install dir : ${INSTALL_DIR}"
echo "  Branch      : ${BRANCH}"
echo "  Limit       : ${LIMIT}"
echo "  Timeout     : ${TIMEOUT}s"
echo "  Depth       : ${DEPTH}"
echo "  Log         : ${LOG_FILE}"
echo "${SEP}"

if [[ ! -d "${INSTALL_DIR}" ]]; then
  fail "Install directory not found: ${INSTALL_DIR}"
  exit 1
fi

cd "${INSTALL_DIR}" || exit 1

# ── Detect service user ───────────────────────────────────────────────────────
SERVICE_USER="$(systemctl show ma-scanner-live.service -p User --value 2>/dev/null || echo '')"
if [[ -z "${SERVICE_USER}" ]]; then
  SERVICE_USER="root"
fi
echo "  Service user: ${SERVICE_USER}"

# ── [1] Git pull ──────────────────────────────────────────────────────────────
section "[1/9] Git pull"
if [[ "${SKIP_GIT}" == "true" ]]; then
  warn "Skipped (--skip-git-pull)"
else
  git fetch origin "${BRANCH}" 2>&1 || { warn "git fetch failed — continuing with local code"; }
  git checkout "${BRANCH}" 2>&1 || { fail "git checkout ${BRANCH} failed"; exit 1; }
  git pull origin "${BRANCH}" 2>&1 || { warn "git pull failed — continuing with local code"; }
  ok "Branch: $(git log --oneline -1)"
fi

# ── [2] Stop AI timer during run ──────────────────────────────────────────────
section "[2/9] Pause AI timer"
if systemctl is-active --quiet ma-scanner-ai-research.timer 2>/dev/null; then
  systemctl stop ma-scanner-ai-research.timer 2>/dev/null && ok "AI timer paused" || warn "Could not stop AI timer"
  _AI_TIMER_WAS_RUNNING=true
else
  ok "AI timer not running (nothing to pause)"
  _AI_TIMER_WAS_RUNNING=false
fi

# ── [3] Repair permissions ────────────────────────────────────────────────────
section "[3/9] Permissions repair"
mkdir -p "${LIVE_DIR}" \
         "${LIVE_DIR}/runs" \
         "${LIVE_DIR}/operator_runs" \
         "${DATA_DIR}/scans" \
         "${AI_DIR}" \
         "${AI_DIR}/cases" \
         "${AI_CACHE_DIR}" \
         "${SOURCE_CACHE_DIR}"
touch "${ERROR_LOG}"
if [[ "${SERVICE_USER}" != "root" ]]; then
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}"
  ok "chown ${DATA_DIR} → ${SERVICE_USER}"
fi
chmod -R u+rwX "${DATA_DIR}"
chmod 600 "${ERROR_LOG}"
ok "Directories and permissions ready"

# ── [4] Syntax check ──────────────────────────────────────────────────────────
section "[4/9] Python syntax check"
PY_MODULES=(
  "src/ai_research/run_ai_research.py"
  "src/ai_research/research_case_builder.py"
  "src/ai_research/investment_gate.py"
  "src/ai_research/quote_extractor.py"
  "src/ai_research/source_fetcher.py"
  "src/ai_research/ai_emailer.py"
  "src/live_monitoring/live_scanner_runner.py"
)
SYNTAX_FAIL=false
for mod in "${PY_MODULES[@]}"; do
  if "${PYTHON}" -m py_compile "${mod}" 2>&1; then
    ok "${mod}"
  else
    fail "Syntax error: ${mod}"
    SYNTAX_FAIL=true
  fi
done
if [[ "${SYNTAX_FAIL}" == "true" ]]; then
  fail "Syntax errors found — aborting"
  exit 1
fi
ok "All modules pass syntax check"

# ── [5] Live scanner run ──────────────────────────────────────────────────────
section "[5/9] Live scanner run"
if [[ "${SKIP_SCANNER}" == "true" ]]; then
  warn "Skipped (--skip-scanner)"
else
  if [[ ! -f "${PYTHON}" ]]; then
    fail ".venv not found: ${PYTHON}"
    exit 1
  fi
  # Clear stale lock
  if [[ -f "${LOCK_FILE}" ]]; then
    LOCK_PID="$(cat "${LOCK_FILE}" 2>/dev/null || echo '')"
    if [[ -n "${LOCK_PID}" ]] && kill -0 "${LOCK_PID}" 2>/dev/null; then
      fail "Scanner is already running (PID ${LOCK_PID}). Wait for it to finish."
      exit 1
    else
      rm -f "${LOCK_FILE}"
      warn "Removed stale lock (PID ${LOCK_PID:-unknown})"
    fi
  fi

  echo "  Running scanner (timeout ${TIMEOUT}s) — this will take several minutes..."
  echo "  Command: ${PYTHON} ${SCANNER_RUNNER} --once --v12-timeout-seconds ${TIMEOUT}"
  echo ""

  set +e
  "${PYTHON}" "${SCANNER_RUNNER}" \
    --once \
    --v12-timeout-seconds "${TIMEOUT}"
  SCANNER_RC=$?
  set -e

  if [[ "${SCANNER_RC}" -ne 0 ]]; then
    fail "Scanner exited with code ${SCANNER_RC}"
    echo ""
    echo "  Last 80 journal lines:"
    journalctl -u ma-scanner-live.service -n 80 --no-pager 2>/dev/null || true
    echo ""
    echo "  Error log tail:"
    tail -120 "${ERROR_LOG}" 2>/dev/null || true
    echo ""
    fail "Scanner failed. Fix the issue and re-run, or use --skip-scanner."
    exit 1
  fi
  ok "Scanner completed successfully (exit 0)"
fi

# ── [6] Source field inspection ───────────────────────────────────────────────
section "[6/9] Source field inspection"
"${PYTHON}" "${AI_RUNNER}" --inspect-source-fields --limit "${LIMIT}" || true

# ── [7] Evidence audit ────────────────────────────────────────────────────────
section "[7/9] Evidence audit"
set +e
AUDIT_OUT=$("${PYTHON}" "${AI_RUNNER}" \
  --latest --limit "${LIMIT}" --evidence-audit --fetch-text 2>&1)
AUDIT_RC=$?
set -e
echo "${AUDIT_OUT}"

# Check if all grades are D or F
if echo "${AUDIT_OUT}" | grep -qE 'Grade summary:.*[A-C]='; then
  ok "Some cases have adequate evidence (grade A/B/C)"
else
  warn "Evidence remains weak (all D/F). AI will be conservative — NEEDS_HUMAN_REVIEW enforced."
fi

# ── [8] AI research email ─────────────────────────────────────────────────────
section "[8/9] AI research + email"
if [[ "${SKIP_AI}" == "true" ]]; then
  warn "Skipped (--skip-ai)"
else
  set +e
  "${PYTHON}" "${AI_RUNNER}" \
    --latest \
    --limit "${LIMIT}" \
    --depth "${DEPTH}" \
    --email \
    --strategic-brief \
    --include-completed-analogues \
    --probability-analysis \
    --opportunity-mode
  AI_RC=$?
  set -e

  if [[ "${AI_RC}" -ne 0 ]]; then
    warn "AI runner exited ${AI_RC} — check config/.env for OPENAI_API_KEY and AI_RESEARCH_ENABLED"
  else
    ok "AI research complete"
  fi

  echo ""
  echo "  ── AI Summary ──────────────────────────────────────────"
  if [[ -f "${SUMMARY_PATH}" ]]; then
    cat "${SUMMARY_PATH}"
  else
    warn "Summary file not found: ${SUMMARY_PATH}"
  fi
fi

# ── [9] Health check + timers ─────────────────────────────────────────────────
section "[9/9] Health check + timers"
"${PYTHON}" src/live_monitoring/health_check.py 2>/dev/null || warn "Health check returned non-zero"

if [[ "${INSTALL_AI_TIMER}" == "true" ]]; then
  echo ""
  echo "  Installing AI research timer..."
  bash deploy/vps/install_ai_research_timer.sh "${INSTALL_DIR}" || warn "Timer install failed"
  systemctl list-timers | grep ma-scanner-ai || true
elif [[ "${_AI_TIMER_WAS_RUNNING}" == "true" ]]; then
  # Restore AI timer if it was running before
  systemctl start ma-scanner-ai-research.timer 2>/dev/null && ok "AI timer restored" || warn "Could not restore AI timer"
fi

if [[ "${RESTART_SCANNER_TIMER}" == "true" ]]; then
  echo ""
  echo "  Starting scanner timer..."
  systemctl start ma-scanner-live.timer && ok "Scanner timer started" || warn "Could not start scanner timer"
  systemctl list-timers | grep ma-scanner-live || true
fi

# ── Final status ──────────────────────────────────────────────────────────────
echo ""
echo "${SEP}"
echo "  Production cycle complete"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""
echo "  Log         : ${LOG_FILE}"
echo "  AI summary  : ${SUMMARY_PATH}"
echo ""
echo "  Key commands:"
echo "    AI email only     : sudo bash ${INSTALL_DIR}/deploy/vps/run_ai_email_now.sh"
echo "    Scanner only      : sudo bash ${INSTALL_DIR}/deploy/vps/run_scanner_once_safe.sh"
echo "    Full cycle again  : sudo bash ${INSTALL_DIR}/deploy/vps/run_full_production_cycle.sh"
echo "    Live journal      : journalctl -u ma-scanner-live.service -n 50 --no-pager"
echo "    AI timer status   : systemctl status ma-scanner-ai-research.timer"
echo "${SEP}"
