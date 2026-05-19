#!/usr/bin/env bash
# push_and_deploy_to_vps.sh — Push local branch to origin and trigger VPS deploy.
#
# Usage:
#   bash deploy/local/push_and_deploy_to_vps.sh [OPTIONS]
#
# Environment (set in deploy/local/.env.deploy or shell):
#   MA_SCANNER_VPS_HOST     SSH target, e.g. root@12.34.56.78
#   MA_SCANNER_REMOTE_DIR   Install dir on VPS (default: /opt/ma-scanner)
#   MA_SCANNER_BRANCH       Git branch (default: ai-final)
#
# Options:
#   --host HOST             Override MA_SCANNER_VPS_HOST
#   --remote-dir DIR        Override MA_SCANNER_REMOTE_DIR
#   --branch BRANCH         Override MA_SCANNER_BRANCH
#   --run-full-cycle        Run full production cycle on VPS after pull
#   --run-ai-email          Run AI email only on VPS after pull
#   --run-scanner           Run scanner only on VPS after pull
#   --run-cleanup           Run clean_runtime_git_noise.sh on VPS before pull
#   --run-health-check      Run health check on VPS after deploy
#   --skip-push             Skip git push (VPS pull only)
#   --skip-remote-pull      Skip VPS pull (push only)

set -uo pipefail

# Load local .env.deploy if it exists next to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DEPLOY="${SCRIPT_DIR}/.env.deploy"
if [[ -f "${ENV_DEPLOY}" ]]; then
  # shellcheck source=/dev/null
  source "${ENV_DEPLOY}"
fi

VPS_HOST="${MA_SCANNER_VPS_HOST:-}"
REMOTE_DIR="${MA_SCANNER_REMOTE_DIR:-/opt/ma-scanner}"
BRANCH="${MA_SCANNER_BRANCH:-ai-final}"
RUN_FULL_CYCLE=false
RUN_AI_EMAIL=false
RUN_SCANNER=false
RUN_CLEANUP=false
RUN_HEALTH_CHECK=false
SKIP_PUSH=false
SKIP_REMOTE_PULL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)             VPS_HOST="${2}"; shift ;;
    --remote-dir)       REMOTE_DIR="${2}"; shift ;;
    --branch)           BRANCH="${2}"; shift ;;
    --run-full-cycle)   RUN_FULL_CYCLE=true ;;
    --run-ai-email)     RUN_AI_EMAIL=true ;;
    --run-scanner)      RUN_SCANNER=true ;;
    --run-cleanup)      RUN_CLEANUP=true ;;
    --run-health-check) RUN_HEALTH_CHECK=true ;;
    --skip-push)        SKIP_PUSH=true ;;
    --skip-remote-pull) SKIP_REMOTE_PULL=true ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

SEP="────────────────────────────────────────────────────────"

echo "${SEP}"
echo "  MA Scanner — Push + Deploy to VPS"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  VPS host    : ${VPS_HOST:-[NOT SET]}"
echo "  Remote dir  : ${REMOTE_DIR}"
echo "  Branch      : ${BRANCH}"
echo "${SEP}"

if [[ -z "${VPS_HOST}" ]]; then
  echo ""
  echo "ERROR: VPS host not set."
  echo ""
  echo "  Option 1 — set environment variable:"
  echo "    export MA_SCANNER_VPS_HOST=root@your_server_ip"
  echo ""
  echo "  Option 2 — create deploy/local/.env.deploy:"
  echo "    cp deploy/local/.env.deploy.example deploy/local/.env.deploy"
  echo "    # edit .env.deploy with your VPS host"
  echo ""
  exit 1
fi

ok()   { echo "  ✓ $1"; }
warn() { echo "  ⚠  $1"; }
fail() { echo "  ✗ $1"; }

ssh_run() {
  ssh -T "${VPS_HOST}" "$@"
}

# ── [1] Local pre-flight ──────────────────────────────────────────────────────
echo ""
echo "[1/4] Local pre-flight"

SOURCE_DIRTY="$(git status --short -- src/ deploy/ config/ scripts/ requirements.txt 2>/dev/null \
  | grep -v '^?' || true)"
if [[ -n "${SOURCE_DIRTY}" ]]; then
  fail "Uncommitted source changes — commit or stash before deploy:"
  echo "${SOURCE_DIRTY}" | sed 's/^/        /'
  exit 1
fi
ok "Local source tree is clean"
ok "Branch: $(git log --oneline -1)"

# ── [2] Push to remote ────────────────────────────────────────────────────────
echo ""
echo "[2/4] Push to origin"
if [[ "${SKIP_PUSH}" == "true" ]]; then
  warn "Skipped (--skip-push)"
else
  git push origin "${BRANCH}"
  ok "Pushed ${BRANCH} to origin"
fi

# ── [3] VPS pull ──────────────────────────────────────────────────────────────
echo ""
echo "[3/4] VPS git pull"
if [[ "${SKIP_REMOTE_PULL}" == "true" ]]; then
  warn "Skipped (--skip-remote-pull)"
else
  # Check VPS for uncommitted source changes
  VPS_DIRTY="$(ssh_run "cd ${REMOTE_DIR} && git status --short -- src/ deploy/ config/ scripts/ requirements.txt 2>/dev/null | grep -v '^?'" || true)"
  if [[ -n "${VPS_DIRTY}" ]]; then
    fail "VPS has uncommitted source changes — cannot pull without risk of conflict:"
    echo "${VPS_DIRTY}" | sed 's/^/        /'
    echo ""
    echo "  Resolve on VPS:"
    echo "    ssh ${VPS_HOST}"
    echo "    cd ${REMOTE_DIR}"
    echo "    git status"
    exit 1
  fi
  ok "VPS source tree is clean"

  if [[ "${RUN_CLEANUP}" == "true" ]]; then
    echo "  Running git index cleanup on VPS..."
    ssh_run "bash ${REMOTE_DIR}/deploy/vps/clean_runtime_git_noise.sh ${REMOTE_DIR}" || true
  fi

  ssh_run "cd ${REMOTE_DIR} && git fetch origin ${BRANCH} && git checkout ${BRANCH} && git pull --ff-only origin ${BRANCH}"
  VPS_HEAD="$(ssh_run "cd ${REMOTE_DIR} && git log --oneline -1")"
  ok "VPS updated: ${VPS_HEAD}"
fi

# ── [4] Post-deploy action ────────────────────────────────────────────────────
echo ""
echo "[4/4] Post-deploy action"
if [[ "${RUN_FULL_CYCLE}" == "true" ]]; then
  echo "  Running full production cycle (--skip-scanner) on VPS..."
  ssh_run "sudo bash ${REMOTE_DIR}/deploy/vps/run_full_production_cycle.sh --skip-scanner"
elif [[ "${RUN_AI_EMAIL}" == "true" ]]; then
  echo "  Running AI email on VPS..."
  ssh_run "bash ${REMOTE_DIR}/deploy/vps/run_ai_email_now.sh ${REMOTE_DIR}"
elif [[ "${RUN_SCANNER}" == "true" ]]; then
  echo "  Running scanner on VPS..."
  ssh_run "sudo bash ${REMOTE_DIR}/deploy/vps/run_scanner_once_safe.sh ${REMOTE_DIR}"
elif [[ "${RUN_HEALTH_CHECK}" == "true" ]]; then
  echo "  Running health check on VPS..."
  ssh_run "${REMOTE_DIR}/.venv/bin/python ${REMOTE_DIR}/src/live_monitoring/health_check.py"
else
  warn "No post-deploy action selected"
  echo "        Add --run-full-cycle, --run-ai-email, --run-scanner, or --run-health-check"
fi

echo ""
echo "${SEP}"
echo "  Deploy complete. $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""
echo "  Common next steps:"
echo "    Full cycle  : --run-full-cycle"
echo "    AI email    : --run-ai-email"
echo "    Health check: --run-health-check"
echo "${SEP}"
