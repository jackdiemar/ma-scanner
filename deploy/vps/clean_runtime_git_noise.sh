#!/usr/bin/env bash
# clean_runtime_git_noise.sh — Untrack generated runtime files from the git index.
#
# Does NOT delete local files. Idempotent — safe to run multiple times.
# After running, commit the result:
#   git commit -m "chore: untrack runtime artifacts from git index"
#
# Usage:
#   bash deploy/vps/clean_runtime_git_noise.sh [INSTALL_DIR]

set -uo pipefail

INSTALL_DIR="${1:-/opt/ma-scanner}"

if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "ERROR: install directory not found: ${INSTALL_DIR}"; exit 1
fi

cd "${INSTALL_DIR}" || exit 1

SEP="────────────────────────────────────────────────────────"

echo "${SEP}"
echo "  MA Scanner — Git Index Cleanup"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Local files are NOT deleted — only git tracking is removed."
echo "${SEP}"

TOTAL=0

# Untrack a directory or file if currently tracked. Idempotent.
untrack() {
  local path="$1"
  local tracked
  tracked="$(git ls-files "${path}" 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "${tracked}" -gt 0 ]]; then
    git rm -r --cached --quiet "${path}"
    echo "  untracked ${tracked} file(s): ${path}"
    TOTAL=$((TOTAL + tracked))
  else
    echo "  clean (nothing to do): ${path}"
  fi
}

untrack_glob() {
  local pattern="$1"
  local files
  files="$(git ls-files "${pattern}" 2>/dev/null || true)"
  if [[ -n "${files}" ]]; then
    local count
    count="$(echo "${files}" | wc -l | tr -d ' ')"
    echo "${files}" | xargs git rm --cached --quiet 2>/dev/null || true
    echo "  untracked ${count} file(s): ${pattern}"
    TOTAL=$((TOTAL + count))
  else
    echo "  clean (nothing to do): ${pattern}"
  fi
}

echo ""
echo "  FMP / EDGAR response cache"
untrack "data/cache"

echo ""
echo "  AI research outputs"
untrack "data/ai_research"

echo ""
echo "  Live monitoring runtime files"
for f in data/live_monitoring/latest_alerts.json \
          data/live_monitoring/latest_review_memo.md \
          data/live_monitoring/live_alert_log.csv \
          data/live_monitoring/live_monitoring_log.csv \
          data/live_monitoring/live_scanner_state.json; do
  untrack "${f}"
done
untrack "data/live_monitoring/runs"

echo ""
echo "  Scan outputs"
untrack_glob "data/scans/scan_v12_*.json"
untrack "data/scans/legacy"

echo ""
echo "  Legacy / ancillary data"
untrack "data/legacy-scans"
untrack "data/predictions"
untrack "data/tracking"

echo ""
echo "  .DS_Store files"
DS_FILES="$(git ls-files | grep '\.DS_Store' || true)"
if [[ -n "${DS_FILES}" ]]; then
  DS_COUNT="$(echo "${DS_FILES}" | wc -l | tr -d ' ')"
  echo "${DS_FILES}" | xargs git rm --cached --quiet 2>/dev/null || true
  echo "  untracked ${DS_COUNT} .DS_Store file(s)"
  TOTAL=$((TOTAL + DS_COUNT))
else
  echo "  clean (no .DS_Store tracked)"
fi

echo ""
echo "${SEP}"
echo "  Done. ${TOTAL} file(s) removed from git index."
if [[ "${TOTAL}" -gt 0 ]]; then
  echo ""
  echo "  Commit the cleanup:"
  echo "    git add .gitignore"
  echo "    git commit -m 'chore: untrack runtime artifacts from git index'"
fi
echo "${SEP}"
