#!/usr/bin/env bash
# check_repo_clean.sh — Verify the repo is free of runtime artifacts.
#
# Exits non-zero if:
#   1. config/.env is tracked by git
#   2. Generated data files are still tracked
#   3. Uncommitted source changes are present
#
# Usage:
#   bash deploy/vps/check_repo_clean.sh [INSTALL_DIR]

set -uo pipefail

INSTALL_DIR="${1:-/opt/ma-scanner}"

if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "ERROR: install directory not found: ${INSTALL_DIR}"; exit 1
fi

cd "${INSTALL_DIR}" || exit 1

FAIL=false

echo "Repo hygiene check: ${INSTALL_DIR}"
echo ""

# [1] config/.env must not be tracked
if git ls-files --error-unmatch config/.env >/dev/null 2>&1; then
  echo "  FAIL  config/.env is tracked by git"
  echo "        Fix: git rm --cached config/.env"
  FAIL=true
else
  echo "  OK    config/.env is not tracked"
fi

# [2] Runtime data must not be tracked
RUNTIME_TRACKED="$(git ls-files \
  data/cache \
  data/ai_research \
  data/live_monitoring/latest_alerts.json \
  data/live_monitoring/live_scanner_state.json \
  data/live_monitoring/live_alert_log.csv \
  data/live_monitoring/live_monitoring_log.csv \
  data/live_monitoring/latest_review_memo.md \
  data/predictions \
  data/tracking \
  data/legacy-scans \
  2>/dev/null || true)"

# Also catch timestamped scan files
RUNTIME_TRACKED+="$(git ls-files 'data/scans/scan_v12_*.json' 'data/scans/legacy' 2>/dev/null || true)"

if [[ -n "${RUNTIME_TRACKED}" ]]; then
  TRACKED_COUNT="$(echo "${RUNTIME_TRACKED}" | wc -l | tr -d ' ')"
  echo "  FAIL  ${TRACKED_COUNT} runtime file(s) tracked by git"
  echo "${RUNTIME_TRACKED}" | head -10 | sed 's/^/        /'
  if [[ "${TRACKED_COUNT}" -gt 10 ]]; then
    echo "        ... and $((TRACKED_COUNT - 10)) more"
  fi
  echo "        Fix: bash ${INSTALL_DIR}/deploy/vps/clean_runtime_git_noise.sh"
  FAIL=true
else
  echo "  OK    no runtime files tracked"
fi

# [3] Source changes must be committed
SOURCE_DIRTY="$(git status --short -- src/ deploy/ config/ scripts/ requirements.txt 2>/dev/null \
  | grep -v '^?' || true)"
if [[ -n "${SOURCE_DIRTY}" ]]; then
  echo "  FAIL  uncommitted source changes:"
  echo "${SOURCE_DIRTY}" | sed 's/^/        /'
  FAIL=true
else
  echo "  OK    source tree is clean"
fi

echo ""
if [[ "${FAIL}" == "true" ]]; then
  echo "RESULT: hygiene check FAILED"
  exit 1
fi

echo "RESULT: repo is clean"
