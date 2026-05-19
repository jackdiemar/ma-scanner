#!/usr/bin/env bash
# push_and_deploy_to_vps.sh — Push local branch to origin and trigger VPS deploy.
#
# Usage:
#   bash deploy/local/push_and_deploy_to_vps.sh [OPTIONS]
#
# Environment (set in deploy/local/.env.deploy or shell):
#   MA_SCANNER_VPS_HOST     SSH target, e.g. root@137.184.133.182
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

set -euo pipefail

# Capture any env-passed values before loading .env.deploy (env vars take priority over file).
_HOST_FROM_ENV="${MA_SCANNER_VPS_HOST:-}"
_DIR_FROM_ENV="${MA_SCANNER_REMOTE_DIR:-}"
_BRANCH_FROM_ENV="${MA_SCANNER_BRANCH:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DEPLOY="${SCRIPT_DIR}/.env.deploy"
if [[ -f "${ENV_DEPLOY}" ]]; then
  # shellcheck source=/dev/null
  source "${ENV_DEPLOY}"
fi

# Env vars override .env.deploy
[[ -n "${_HOST_FROM_ENV}" ]]   && MA_SCANNER_VPS_HOST="${_HOST_FROM_ENV}"
[[ -n "${_DIR_FROM_ENV}" ]]    && MA_SCANNER_REMOTE_DIR="${_DIR_FROM_ENV}"
[[ -n "${_BRANCH_FROM_ENV}" ]] && MA_SCANNER_BRANCH="${_BRANCH_FROM_ENV}"

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
    *) echo "ERROR: Unknown option: $1"; exit 1 ;;
  esac
  shift
done

SEP="────────────────────────────────────────────────────────"

ok()   { echo "  ✓ $1"; }
warn() { echo "  ⚠  $1"; }
fail() { echo "  ✗ $1"; }

# ── Host validation ───────────────────────────────────────────────────────────
# Reject missing or placeholder hosts before doing anything.
_PLACEHOLDER_RE='(your_server|YOUR_SERVER|SERVER_IP|example\.com|placeholder|localhost$|127\.0\.0\.1$)'

if [[ -z "${VPS_HOST}" ]]; then
  echo ""
  echo "ERROR: MA_SCANNER_VPS_HOST is not set."
  echo ""
  echo "  Option 1 — set environment variable:"
  echo "    export MA_SCANNER_VPS_HOST=root@137.184.133.182"
  echo ""
  echo "  Option 2 — create deploy/local/.env.deploy:"
  echo "    cp deploy/local/.env.deploy.example deploy/local/.env.deploy"
  echo "    # .env.deploy already contains the correct host — no edit needed"
  echo ""
  exit 1
fi

if echo "${VPS_HOST}" | grep -qE "${_PLACEHOLDER_RE}"; then
  echo ""
  echo "ERROR: MA_SCANNER_VPS_HOST looks like a placeholder: ${VPS_HOST}"
  echo "  Set MA_SCANNER_VPS_HOST in deploy/local/.env.deploy or pass --host root@SERVER_IP"
  exit 1
fi

echo "${SEP}"
echo "  MA Scanner — Push + Deploy to VPS"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  VPS host    : ${VPS_HOST}"
echo "  Remote dir  : ${REMOTE_DIR}"
echo "  Branch      : ${BRANCH}"
echo "${SEP}"

# Wrapper: every SSH call is fatal on failure.
ssh_run() {
  ssh -T -o BatchMode=yes -o ConnectTimeout=30 "${VPS_HOST}" "$@"
}

# ── [1] Local pre-flight ──────────────────────────────────────────────────────
echo ""
echo "[1/5] Local pre-flight"

SOURCE_DIRTY="$(git status --short -- src/ deploy/ config/ scripts/ requirements.txt 2>/dev/null \
  | grep -v '^?' || true)"
if [[ -n "${SOURCE_DIRTY}" ]]; then
  fail "Uncommitted source changes — commit or stash before deploy:"
  echo "${SOURCE_DIRTY}" | sed 's/^/        /'
  exit 1
fi
ok "Local source tree is clean"
ok "Branch: $(git log --oneline -1)"

# ── [2] SSH preflight ─────────────────────────────────────────────────────────
echo ""
echo "[2/5] SSH preflight"
SSH_TEST_OUT="$(ssh -T -o BatchMode=yes -o ConnectTimeout=10 "${VPS_HOST}" "echo ok" 2>&1)" || {
  fail "SSH connection failed: ${VPS_HOST}"
  echo "  Output: ${SSH_TEST_OUT}"
  echo "  Test manually: ssh ${VPS_HOST}"
  exit 1
}
if [[ "${SSH_TEST_OUT}" != "ok" ]]; then
  fail "SSH preflight returned unexpected output: ${SSH_TEST_OUT}"
  echo "  Test manually: ssh ${VPS_HOST}"
  exit 1
fi
ok "SSH connection: ${VPS_HOST}"

# ── [3] Push to remote ────────────────────────────────────────────────────────
echo ""
echo "[3/5] Push to origin"
if [[ "${SKIP_PUSH}" == "true" ]]; then
  warn "Skipped (--skip-push)"
else
  git push origin "${BRANCH}"
  ok "Pushed ${BRANCH} to origin"
fi

# ── [4] VPS pull ──────────────────────────────────────────────────────────────
echo ""
echo "[4/5] VPS git pull"
if [[ "${SKIP_REMOTE_PULL}" == "true" ]]; then
  warn "Skipped (--skip-remote-pull)"
else
  # Check VPS for uncommitted source changes.
  # grep exits 1 on no matches — use || true so set -e doesn't fire on clean tree.
  VPS_STATUS_RAW="$(ssh_run "cd ${REMOTE_DIR} && git status --short -- src/ deploy/ config/ scripts/ requirements.txt 2>/dev/null")"
  VPS_DIRTY="$(echo "${VPS_STATUS_RAW}" | grep -v '^?' || true)"
  if [[ -n "${VPS_DIRTY}" ]]; then
    fail "VPS has uncommitted source changes — cannot pull without conflict risk:"
    echo "${VPS_DIRTY}" | sed 's/^/        /'
    echo ""
    echo "  Resolve on VPS:"
    echo "    ssh ${VPS_HOST}"
    echo "    cd ${REMOTE_DIR} && git status"
    exit 1
  fi
  ok "VPS source tree is clean"

  if [[ "${RUN_CLEANUP}" == "true" ]]; then
    echo "  Running full git index cleanup on VPS..."
    ssh_run "bash ${REMOTE_DIR}/deploy/vps/clean_runtime_git_noise.sh ${REMOTE_DIR}" || true
  fi

  # Runtime-safe VPS deploy — avoids ff-merge conflicts caused by commits that
  # removed large tracked data dirs (git rm --cached). Strategy:
  # 1. Fetch + checkout branch
  # 2. Checkout source files from remote into working tree + index
  # 3. git reset --mixed: advance HEAD + sync index to remote; working tree untouched
  # Runtime data (cache, live_monitoring, ai_research) stays on disk through all steps.
  echo "  Updating VPS..."
  ssh_run "$(cat <<SSHEOF
set -euo pipefail
cd ${REMOTE_DIR}
git fetch origin ${BRANCH}
git checkout ${BRANCH}

# Get list of source files in remote commit (excludes data/ since cleanup commits
# removed them from tracking, so ls-tree only returns source files now)
SOURCE_FILES=\$(git ls-tree -r --name-only "origin/${BRANCH}" 2>/dev/null | grep -v '^config/\.env')
if [[ -n "\${SOURCE_FILES}" ]]; then
  echo "\${SOURCE_FILES}" | xargs git checkout "origin/${BRANCH}" -- 2>/dev/null || true
fi

# Advance HEAD to remote commit + sync index to match (no working tree changes).
# This handles any remaining index/HEAD divergence from our checkout operations.
git reset --mixed "origin/${BRANCH}"
SSHEOF
)"
  VPS_HEAD="$(ssh_run "cd ${REMOTE_DIR} && git log --oneline -1")"
  ok "VPS updated: ${VPS_HEAD}"
fi

# ── [5] Post-deploy action ────────────────────────────────────────────────────
echo ""
echo "[5/5] Post-deploy action"
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
echo "    Health check: bash deploy/local/push_and_deploy_to_vps.sh --run-health-check"
echo "    AI email    : bash deploy/local/push_and_deploy_to_vps.sh --run-ai-email"
echo "    Full cycle  : bash deploy/local/push_and_deploy_to_vps.sh --run-full-cycle"
echo "${SEP}"
