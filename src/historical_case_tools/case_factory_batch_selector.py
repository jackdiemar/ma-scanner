#!/usr/bin/env python3
"""
case_factory_batch_selector.py

Select the next batch of historical case candidates from the five-year acquisition
universe for the 200-case factory pipeline.

Reads:  data/historical_cases/five_year_acquisition_universe_candidates.csv
Writes: data/historical_cases/batch_{start}_{end}_candidate_queue.csv
        data/historical_cases/batch_{start}_{end}_candidate_queue_report.md

Candidate filters applied (all default ON):
  - Exclude already_in_first_50=TRUE
  - Exclude already_in_batch_51_70=TRUE
  - Exclude inclusion_status starting with EXCLUDE
  - Exclude known batch 51-70 tickers (guards against stale flags in universe CSV)
  - Prefer INCLUDE_STANDARD_PUBLIC_COMPANY_ACQUISITION over MAYBE_NEEDS_REVIEW
  - Prefer HIGH confidence over LOW confidence

Safety:
  - No adjudication.
  - No VERIFIED or CALIBRATION_ELIGIBLE marking.
  - No live API calls.

Usage:
  python3 src/historical_case_tools/case_factory_batch_selector.py
  python3 src/historical_case_tools/case_factory_batch_selector.py --start 71 --limit 30
  python3 src/historical_case_tools/case_factory_batch_selector.py --start 101 --limit 30
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

DEFAULT_UNIVERSE = HISTORICAL_DIR / "five_year_acquisition_universe_candidates.csv"
RUN_DATE = date.today().isoformat()

# Known batch 51-70 tickers not always flagged in universe CSV.
# Guards against stale already_in_batch_51_70=FALSE for cases adjudicated in that batch.
BATCH_51_70_TICKERS: frozenset[str] = frozenset({
    "EPZM", "FMTX", "GBT", "IMGO", "OYST", "SRRA", "TPTX",
    "BLU", "CINC", "CTIC", "DICE", "HARP", "ISEE", "RETA",
    "ZYNE", "ALPN", "AMAM", "CBAY", "CERE", "DCPH",
})

OUTPUT_FIELDS = [
    "queue_position",
    "candidate_id",
    "ticker",
    "company",
    "acquirer",
    "announcement_date",
    "announcement_year",
    "confidence",
    "inclusion_status",
    "needs_date_backfill",
    "needs_standard_deal_confirmation",
    "source_url",
    "edgar_company_search_url",
    "recommended_action",
    "notes",
]

_INCLUSION_RANK = {
    "INCLUDE_STANDARD_PUBLIC_COMPANY_ACQUISITION": 0,
    "MAYBE_NEEDS_REVIEW": 1,
}
_CONFIDENCE_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "": 3}


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _edgar_company_search(ticker: str) -> str:
    return (
        "https://www.sec.gov/cgi-bin/browse-edgar"
        f"?company=&CIK={quote(ticker)}&type=8-K&dateb=&owner=include"
        "&count=40&search_text=&action=getcompany"
    )


def _recommended_action(row: dict[str, str]) -> str:
    if row.get("needs_date_backfill", "").upper() == "TRUE":
        return "DATE_BACKFILL_REQUIRED: find merger 8-K on EDGAR before filing collection"
    if row.get("needs_standard_deal_confirmation", "").upper() == "TRUE":
        return "DEAL_CONFIRMATION_REQUIRED: verify standard public-company acquisition"
    conf = row.get("confidence", "").upper()
    if conf in ("HIGH", "MEDIUM"):
        return "DATE_CONFIRMED: ready for exception queue and filing collection (if enabled)"
    return "REVIEW_NEEDED: check date confidence and deal structure before filing collection"


# ---------------------------------------------------------------------------
# Selection logic
# ---------------------------------------------------------------------------

def batch_name(start: int, end: int) -> str:
    return f"batch_{start}_{end}"


def select_candidates(
    universe: list[dict[str, str]],
    start: int,
    limit: int,
    extra_exclude_tickers: set[str] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    Returns (selected, excluded).

    selected: up to `limit` candidates sorted by inclusion quality.
    excluded: all rows filtered out and why.
    """
    exclude_tickers = set(BATCH_51_70_TICKERS)
    if extra_exclude_tickers:
        exclude_tickers |= {t.upper() for t in extra_exclude_tickers}

    excluded: list[dict[str, str]] = []
    eligible: list[dict[str, str]] = []

    for row in universe:
        ticker = row.get("ticker", "").strip().upper()
        already_50 = row.get("already_in_first_50", "").strip().upper() == "TRUE"
        already_51_70 = row.get("already_in_batch_51_70", "").strip().upper() == "TRUE"
        status = row.get("inclusion_status", "").strip()
        is_excluded = status.startswith("EXCLUDE")
        in_known_batch = ticker in exclude_tickers

        if already_50 or already_51_70 or is_excluded or in_known_batch:
            excluded.append(row)
            continue
        eligible.append(row)

    # Sort: prefer INCLUDE_STANDARD, then HIGH confidence, then alphabetical ticker
    def sort_key(r: dict[str, str]) -> tuple[int, int, str]:
        return (
            _INCLUSION_RANK.get(r.get("inclusion_status", ""), 99),
            _CONFIDENCE_RANK.get(r.get("confidence", "").upper(), 3),
            r.get("ticker", ""),
        )

    eligible.sort(key=sort_key)
    selected = eligible[:limit]
    return selected, excluded


def build_queue_rows(selected: list[dict[str, str]], start_seq: int) -> list[dict[str, str]]:
    rows = []
    for i, row in enumerate(selected, 1):
        ticker = row.get("ticker", "").strip().upper()
        rows.append({
            "queue_position":                  str(start_seq + i - 1),
            "candidate_id":                    row.get("candidate_id", ""),
            "ticker":                          ticker,
            "company":                         row.get("company", ""),
            "acquirer":                        row.get("acquirer", ""),
            "announcement_date":               row.get("announcement_date", ""),
            "announcement_year":               row.get("announcement_year", ""),
            "confidence":                      row.get("confidence", ""),
            "inclusion_status":                row.get("inclusion_status", ""),
            "needs_date_backfill":             row.get("needs_date_backfill", ""),
            "needs_standard_deal_confirmation":row.get("needs_standard_deal_confirmation", ""),
            "source_url":                      row.get("source_url", ""),
            "edgar_company_search_url":        _edgar_company_search(ticker),
            "recommended_action":              _recommended_action(row),
            "notes":                           row.get("notes", ""),
        })
    return rows


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(
    path: Path,
    batch: str,
    selected: list[dict[str, str]],
    excluded_count: int,
    eligible_total: int,
    limit: int,
    start: int,
    end: int,
    target: int = 200,
    current: int = 70,
) -> None:
    need_more = max(0, limit - len(selected))
    cases_after_batch = current + len(selected)
    still_needed = target - cases_after_batch
    pct_complete = round(cases_after_batch / target * 100, 1)

    lines = [
        f"# {batch.replace('_', ' ').title()} Candidate Queue Report",
        "",
        f"Generated: {RUN_DATE}",
        "",
        "Candidate selection only. No cases adjudicated. No classifications changed.",
        "No cases marked VERIFIED or CALIBRATION_ELIGIBLE.",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Target case count | {target} |",
        f"| Current confirmed cases | {current} |",
        f"| Cases needed to reach {target} | {target - current} |",
        f"| This batch target | {limit} cases (cases {start}–{end}) |",
        f"| Candidates selected from local universe | {len(selected)} |",
        f"| Candidates excluded (already covered or filtered) | {excluded_count} |",
        f"| Gap — additional candidates needed from external discovery | {need_more} |",
        f"| Cases still needed after this batch completes | {still_needed} |",
        f"| Projected completion after batch | {cases_after_batch}/{target} ({pct_complete}%) |",
        "",
    ]

    if need_more > 0:
        lines += [
            "---",
            "",
            "## Discovery Gap",
            "",
            f"**Local universe provides {len(selected)} of {limit} candidates needed for this batch.**",
            f"{need_more} additional candidate(s) must come from one of:",
            "",
            "1. **EDGAR universe expansion** — add 2024–2025 acquisitions to `resolved_case_candidates.csv`",
            "2. **FMP live discovery** — set `allow_fmp_discovery: true` in `configs/case_factory.yaml`",
            "3. **Manual seed** — add confirmed public-company acquisitions from external M&A databases",
            "",
            "> **Do not enable FMP live discovery until EDGAR/source evidence confirms each candidate.**",
            "> **Do not add candidates that are asset transactions, SPAC mergers, or reverse mergers.**",
            "",
        ]

    lines += [
        "---",
        "",
        "## Selected Candidates",
        "",
        "| # | candidate_id | ticker | company | year | confidence | needs_backfill | action |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in selected:
        action_short = r.get("recommended_action", "").split(":")[0]
        co = r.get("company", "")[:35]
        lines.append(
            f"| {r['queue_position']} | {r['candidate_id']} | {r['ticker']} "
            f"| {co} | {r['announcement_year']} "
            f"| {r['confidence']} | {r['needs_date_backfill']} | {action_short} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Pre-Work Required Before Filing Collection",
        "",
        "All candidates in this queue require date backfill before filing collection can run.",
        "Filing collection is OFF by default (`collect_filings: false` in config).",
        "",
        "### Step sequence:",
        "",
        "```bash",
        "# Step 1 — Select candidates (already done by running this script)",
        f"python3 src/historical_case_tools/case_factory_orchestrator.py \\",
        f"  --config configs/case_factory.yaml --select-next-batch",
        "",
        "# Step 2 — Date prefill work queue",
        f"python3 src/historical_case_tools/case_factory_orchestrator.py \\",
        f"  --config configs/case_factory.yaml --run-step date-prefill --start {start} --limit {limit}",
        "",
        "# Step 3 — Exception queue (after dates are resolved in acquisition_announcement_dates.csv)",
        f"python3 src/historical_case_tools/case_factory_orchestrator.py \\",
        f"  --config configs/case_factory.yaml --run-step exception-queue --start {start} --limit {limit}",
        "",
        "# Step 4 — Review packet for manual adjudication",
        f"python3 src/historical_case_tools/case_factory_orchestrator.py \\",
        f"  --config configs/case_factory.yaml --write-review-packets --start {start} --limit {limit}",
        "```",
        "",
        "---",
        "",
        "## Safety Constraints",
        "",
        "- No automatic adjudication.",
        "- No VERIFIED flag.",
        "- No CALIBRATION_ELIGIBLE flag.",
        "- No alpha claims.",
        "- FMP live discovery is OFF unless explicitly enabled in `configs/case_factory.yaml`.",
        "- Filing collection is OFF unless `collect_filings: true` is set in config.",
        "- EDGAR/source-backed evidence remains the source of truth for all classifications.",
        "- FMP is context only — not classification.",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=71,
                        help="First case number in this batch (default: 71)")
    parser.add_argument("--limit", type=int, default=30,
                        help="Max candidates to select (default: 30)")
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE,
                        help="Universe candidates CSV")
    parser.add_argument("--output-dir", type=Path, default=HISTORICAL_DIR)
    parser.add_argument("--target", type=int, default=200,
                        help="Total target case count")
    parser.add_argument("--current", type=int, default=70,
                        help="Current confirmed case count")
    args = parser.parse_args()

    end = args.start + args.limit - 1
    bname = batch_name(args.start, end)
    output_csv = args.output_dir / f"{bname}_candidate_queue.csv"
    output_report = args.output_dir / f"{bname}_candidate_queue_report.md"

    universe = read_csv(args.universe)
    if not universe:
        print(f"ERROR: Universe CSV not found or empty: {args.universe}")
        return 1

    selected, excluded = select_candidates(universe, args.start, args.limit)
    queue_rows = build_queue_rows(selected, args.start)

    write_csv(output_csv, queue_rows, OUTPUT_FIELDS)
    write_report(
        output_report,
        bname,
        queue_rows,
        excluded_count=len(excluded),
        eligible_total=len(universe),
        limit=args.limit,
        start=args.start,
        end=end,
        target=args.target,
        current=args.current,
    )

    gap = max(0, args.limit - len(queue_rows))
    print(f"Batch:      {bname}")
    print(f"Selected:   {len(queue_rows)} of {args.limit} target")
    print(f"Excluded:   {len(excluded)} (already covered or filtered)")
    print(f"Gap:        {gap} candidates still needed from external discovery")
    print(f"Output CSV: {output_csv}")
    print(f"Report:     {output_report}")
    if gap > 0:
        print()
        print(f"To close gap: expand resolved_case_candidates.csv OR enable allow_fmp_discovery in config.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
