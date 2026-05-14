#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="$ROOT/reports/repo_hygiene_audit.md"

cd "$ROOT"
mkdir -p reports

count_tracked_under() {
  local path="$1"
  git ls-files "$path" | wc -l | tr -d ' '
}

tracked_file_size_rows() {
  git ls-files -z |
    xargs -0 du -k 2>/dev/null |
    sort -nr |
    awk 'NR <= 30 {
      size_kb=$1
      $1=""
      sub(/^ /, "")
      size_mb=sprintf("%.2f", size_kb / 1024)
      printf("| %s | %s MB |\n", $0, size_mb)
    }'
}

tracked_ignored_files() {
  git ls-files -ci --exclude-standard
}

timestamped_scan_files() {
  git ls-files 'data/scans/scan_v12_*.json'
}

cache_files() {
  git ls-files 'data/cache/*'
}

tracked_or_not() {
  local path="$1"
  if git ls-files --error-unmatch "$path" >/dev/null 2>&1; then
    printf "tracked"
  else
    printf "not tracked"
  fi
}

ignored_or_not() {
  local path="$1"
  if git check-ignore -q "$path"; then
    printf "ignored"
  else
    printf "not ignored"
  fi
}

emit_file_list() {
  local title="$1"
  local content="$2"
  local limit="${3:-50}"

  {
    printf "### %s\\n\\n" "$title"
    if [[ -z "$content" ]]; then
      printf "None.\\n\\n"
      return
    fi
    printf '```text\n'
    printf "%s\\n" "$content" | awk -v limit="$limit" 'NR <= limit { print }'
    local total
    total="$(printf "%s\\n" "$content" | sed '/^$/d' | wc -l | tr -d ' ')"
    if [[ "$total" -gt "$limit" ]]; then
      printf "... %s additional files omitted\\n" "$((total - limit))"
    fi
    printf '```\n\n'
  }
}

tracked_ignored="$(tracked_ignored_files)"
timestamped_scans="$(timestamped_scan_files)"
tracked_cache="$(cache_files)"

tracked_ignored_count="$(printf "%s\\n" "$tracked_ignored" | sed '/^$/d' | wc -l | tr -d ' ')"
timestamped_scan_count="$(printf "%s\\n" "$timestamped_scans" | sed '/^$/d' | wc -l | tr -d ' ')"
tracked_cache_count="$(printf "%s\\n" "$tracked_cache" | sed '/^$/d' | wc -l | tr -d ' ')"

cache_count="$(count_tracked_under 'data/cache')"
scan_count="$(count_tracked_under 'data/scans')"
packet_count="$(count_tracked_under 'data/historical_cases/case_packets')"

scan_latest_state="$(tracked_or_not 'data/scans/scan_latest.json') / $(ignored_or_not 'data/scans/scan_latest.json')"
scan_partial_state="$(tracked_or_not 'data/scans/scan_partial.json') / $(ignored_or_not 'data/scans/scan_partial.json')"

cleanup_safe="YES"
if [[ "$scan_latest_state" != "tracked / not ignored" || "$scan_partial_state" != "tracked / not ignored" ]]; then
  cleanup_safe="REVIEW"
fi

{
  printf "# Repo Hygiene Audit\\n\\n"
  printf "Read-only audit of tracked bloat and generated/local files. No files were deleted or untracked.\\n\\n"

  printf "## Summary\\n\\n"
  printf "%s\\n" "- Tracked files under data/cache/: $cache_count"
  printf "%s\\n" "- Tracked files under data/scans/: $scan_count"
  printf "%s\\n" "- Tracked files under data/historical_cases/case_packets/: $packet_count"
  printf "%s\\n" "- Tracked files now ignored by .gitignore: $tracked_ignored_count"
  printf "%s\\n" "- Tracked timestamped scan outputs: $timestamped_scan_count"
  printf "%s\\n" "- Tracked cache files: $tracked_cache_count"
  printf "%s\\n" "- data/scans/scan_latest.json: $scan_latest_state"
  printf "%s\\n" "- data/scans/scan_partial.json: $scan_partial_state"
  printf "%s\\n\\n" "- Cleanup safe to run later: $cleanup_safe"

  printf "## Largest Tracked Files\\n\\n"
  printf "| Path | Size |\\n"
  printf "|---|---:|\\n"
  tracked_file_size_rows
  printf "\\n"

  printf "## Tracked Directory Counts\\n\\n"
  printf "| Path | Tracked files |\\n"
  printf "|---|---:|\\n"
  printf "| data/cache/ | %s |\\n" "$cache_count"
  printf "| data/scans/ | %s |\\n" "$scan_count"
  printf "| data/historical_cases/case_packets/ | %s |\\n\\n" "$packet_count"

  emit_file_list "Tracked Files Now Ignored" "$tracked_ignored" 80
  emit_file_list "Tracked Timestamped Scan Outputs" "$timestamped_scans" 80
  emit_file_list "Tracked Cache Files" "$tracked_cache" 80

  printf "## Recommended Cleanup Commands\\n\\n"
  printf "Do not run these during this audit. They are recommendations for a later cleanup commit.\\n\\n"
  printf '```bash\n'
  if [[ "$tracked_cache_count" -gt 0 ]]; then
    printf "git rm -r --cached data/cache\\n"
  fi
  if [[ "$timestamped_scan_count" -gt 0 ]]; then
    printf "git rm --cached data/scans/scan_v12_*.json\\n"
  fi
  if [[ "$tracked_ignored_count" -gt 0 ]]; then
    printf "# For any remaining ignored tracked files not covered above:\\n"
    printf "git ls-files -ci --exclude-standard -z | xargs -0 git rm --cached --\\n"
  fi
  if [[ "$tracked_cache_count" -eq 0 && "$timestamped_scan_count" -eq 0 && "$tracked_ignored_count" -eq 0 ]]; then
    printf "# No tracked ignored/cache/timestamped scan cleanup needed.\\n"
  fi
  printf '```\n\n'

  printf "## Notes\\n\\n"
  printf "%s\\n" "- scan_latest.json and scan_partial.json remain trackable because .gitignore explicitly unignores them."
  printf "%s\\n" "- Case packets are counted only for visibility. This audit does not recommend untracking them without a separate historical-case policy decision."
  printf "%s\\n" "- Cleanup is safe to run later if reviewed as a separate commit because the recommended commands only untrack generated/cache files; they do not delete local files."
} > "$REPORT"

printf "Wrote %s\\n" "${REPORT#$ROOT/}"
