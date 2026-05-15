#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_FILE="$ROOT_DIR/data/historical_cases/project_status_snapshot.md"
SNAPSHOT_DATE="$(date '+%Y-%m-%d %H:%M:%S %Z')"

cd "$ROOT_DIR" || exit 1

BRANCH_NAME="$(git branch --show-current 2>/dev/null || echo "UNKNOWN")"
GIT_STATUS_OUTPUT="$(git status --short)"
LATEST_COMMITS_OUTPUT="$(git log --oneline -12)"

branch_name() {
  echo "$BRANCH_NAME"
}

git_status_short() {
  if [[ -z "$GIT_STATUS_OUTPUT" ]]; then
    echo "Clean"
  else
    echo "$GIT_STATUS_OUTPUT"
  fi
}

file_status_line() {
  local path="$1"
  if [[ -f "$ROOT_DIR/$path" ]]; then
    printf -- "- PRESENT: \`%s\`\n" "$path"
  else
    printf -- "- MISSING: \`%s\`\n" "$path"
  fi
}

print_file_group() {
  local title="$1"
  shift
  echo "## $title"
  echo
  local path
  for path in "$@"; do
    file_status_line "$path"
  done
  echo
}

queue_summary_excerpt() {
  local queue_summary="$ROOT_DIR/data/historical_cases/batch_51_70_queue_summary.md"
  if [[ ! -f "$queue_summary" ]]; then
    echo "_Batch 51-70 queue summary not found._"
    return
  fi
  awk '
    /^## Summary/ {printing=1}
    /^## P1\/P3 Case List/ {printing=0}
    printing {print}
  ' "$queue_summary"
}

latest_commits() {
  echo "$LATEST_COMMITS_OUTPUT"
}

write_snapshot() {
  mkdir -p "$(dirname "$OUT_FILE")"
  {
    echo "# Project Status Snapshot"
    echo
    echo "Generated: $SNAPSHOT_DATE"
    echo
    echo "## Git"
    echo
    echo "- Branch: $(branch_name)"
    echo
    echo "### git status --short"
    echo
    echo '```text'
    git_status_short
    echo '```'
    echo
    echo "### Latest 12 Commits"
    echo
    echo '```text'
    latest_commits
    echo '```'
    echo
    print_file_group "Batch 51-70 File Check" \
      "data/historical_cases/batch_51_70_exception_queue.csv" \
      "data/historical_cases/batch_51_70_queue_summary.md" \
      "data/historical_cases/batch_51_70_filing_collection_report.md" \
      "data/historical_cases/batch_51_70_source_evidence_draft.csv" \
      "data/historical_cases/batch_51_70_high_priority_adjudication_report.md" \
      "data/historical_cases/batch_51_70_p6_adjudication_report.md"
    print_file_group "FMP And Universe File Check" \
      "docs/fmp_integration_opportunities.md" \
      "docs/fmp_candidate_discovery_stub.md" \
      "src/historical_case_tools/five_year_acquisition_universe_builder.py" \
      "data/historical_cases/five_year_acquisition_universe_candidates.csv" \
      "src/historical_case_tools/fmp_candidate_discovery_stub.py" \
      "data/historical_cases/fmp_candidate_discovery_stub_report.md"
    echo "## Current Research Status"
    echo
    echo "- First 50-case prior-signal study: complete."
    echo "- First 50 final distribution: TRUE_PUBLIC_PRIOR_SIGNAL 3, DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE 35, PRIVATE_BACKGROUND_ONLY 9, ASSET_SPECIFIC_RIGHTS_ONLY 2, RIGHTS_LANGUAGE_ONLY 1, DATE_MISSING 0."
    echo "- Batch 51-70 announcement dates: complete."
    echo "- Batch 51-70 filing collection: complete."
    echo "- Batch 51-70 high-priority review: complete."
    echo "- High-priority review result: 0 TRUE_PUBLIC_PRIOR_SIGNAL."
    echo "- Remaining Batch 51-70 work: P6 possible-hit adjudication, no-hit baseline finalization, final batch report."
    echo "- FMP integration plan: exists."
    echo "- Five-year acquisition universe builder: exists."
    echo "- FMP candidate discovery stub: exists, but live API is not enabled."
    echo
    echo "## Batch 51-70 Queue Summary"
    echo
    queue_summary_excerpt
    echo
    echo "## Remaining Known Work"
    echo
    echo "1. Finish Batch 51-70 P6 possible-hit adjudication."
    echo "2. Finalize true no-hit P6 baseline cases after coverage check."
    echo "3. Build final Batch 51-70 distribution/report."
    echo "4. Decide whether the historical factory is fast enough to scale toward 100 cases."
    echo "5. Keep FMP as discovery/context only until EDGAR/source-backed evidence confirms candidates."
    echo
    echo "## Do Not Touch Without Explicit Direction"
    echo
    echo "- Do not edit \`source_evidence.csv\` while adjudication is active."
    echo "- Do not edit active Batch 51-70 adjudication outputs."
    echo "- Do not mark \`VERIFIED\`."
    echo "- Do not mark \`CALIBRATION_ELIGIBLE\`."
    echo "- Do not claim alpha."
    echo "- Do not pitch this as M&A prediction."
    echo "- Do not touch dashboard/frontend."
    echo "- Do not run the full scanner for this snapshot."
    echo
    echo "## Next Recommended Command Sequence"
    echo
    echo '```bash'
    echo "git status --short"
    echo "python3 src/historical_case_tools/batch_51_70_queue_summary.py"
    echo "sed -n '1,220p' data/historical_cases/batch_51_70_queue_summary.md"
    echo "# After Claude finishes P6 adjudication, review the P6 report and then build the final Batch 51-70 report."
    echo '```'
  } > "$OUT_FILE"
}

print_terminal_summary() {
  echo "Project status snapshot"
  echo "Generated: $SNAPSHOT_DATE"
  echo "Branch: $(branch_name)"
  echo
  echo "git status --short"
  git_status_short
  echo
  echo "Latest 12 commits"
  latest_commits
  echo
  echo "Key Batch 51-70 files"
  file_status_line "data/historical_cases/batch_51_70_exception_queue.csv"
  file_status_line "data/historical_cases/batch_51_70_queue_summary.md"
  file_status_line "data/historical_cases/batch_51_70_filing_collection_report.md"
  file_status_line "data/historical_cases/batch_51_70_high_priority_adjudication_report.md"
  file_status_line "data/historical_cases/batch_51_70_p6_adjudication_report.md"
  echo
  echo "Key FMP/universe files"
  file_status_line "docs/fmp_integration_opportunities.md"
  file_status_line "src/historical_case_tools/five_year_acquisition_universe_builder.py"
  file_status_line "src/historical_case_tools/fmp_candidate_discovery_stub.py"
  echo
  echo "Batch 51-70 queue summary"
  queue_summary_excerpt
  echo
  echo "Wrote: $OUT_FILE"
}

write_snapshot
print_terminal_summary
