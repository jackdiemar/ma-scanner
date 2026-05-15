#!/usr/bin/env python3
"""
merger_date_prefiller.py

Build a date-prefill work queue for the next batch of acquired biotech cases.

For each case in scope the script checks whether an announcement date is already
present in acquisition_announcement_dates.csv.  Cases without a HIGH or MEDIUM
confidence date are flagged needs_date_backfill=TRUE and get pre-built EDGAR
search URLs so the researcher can quickly find the merger 8-K.

This script is a WORK QUEUE generator.  It does not fetch dates from EDGAR and
does not insert unverified dates anywhere.

Usage:
    python3 src/historical_case_tools/merger_date_prefiller.py
    python3 src/historical_case_tools/merger_date_prefiller.py --start 51 --limit 20
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

DEFAULT_CANDIDATES  = HISTORICAL_DIR / "resolved_case_candidates.csv"
DEFAULT_DATES       = HISTORICAL_DIR / "acquisition_announcement_dates.csv"
DEFAULT_BATCH_RESULTS = HISTORICAL_DIR / "acquisition_prior_signal_batch_results.csv"
DEFAULT_OUTPUT_CSV  = HISTORICAL_DIR / "batch_51_70_date_prefill_queue.csv"
DEFAULT_OUTPUT_REPORT = HISTORICAL_DIR / "batch_51_70_date_prefill_report.md"

RUN_DATE = str(date.today())

OUTPUT_FIELDS = [
    "case_id",
    "ticker",
    "company",
    "likely_outcome_year",
    "current_announcement_date",
    "date_confidence",
    "needs_date_backfill",
    "edgar_company_search_url",
    "edgar_merger_8k_query_url",
    "edgar_sc14d9_query_url",
    "suggested_query_terms",
    "notes",
]


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


def edgar_company_search(ticker: str) -> str:
    return (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?company=&CIK={quote(ticker)}&type=8-K&dateb=&owner=include"
        f"&count=40&search_text=&action=getcompany"
    )


def edgar_merger_8k_url(ticker: str, company: str, year: str) -> str:
    start = f"{int(year) - 1}-01-01" if year and year.isdigit() else "2015-01-01"
    end   = f"{int(year) + 1}-12-31" if year and year.isdigit() else "2025-12-31"
    q = quote(f'"{company}" "agreement and plan of merger" "per share"')
    return (
        f"https://efts.sec.gov/LATEST/search-index?q={q}"
        f"&forms=8-K,SC+TO-T,SC+TO-I"
        f"&dateRange=custom&startdt={start}&enddt={end}"
    )


def edgar_sc14d9_url(ticker: str, company: str, year: str) -> str:
    start = f"{int(year) - 1}-01-01" if year and year.isdigit() else "2015-01-01"
    end   = f"{int(year) + 1}-12-31" if year and year.isdigit() else "2025-12-31"
    q = quote(f'"{company}" "background of the offer"')
    return (
        f"https://efts.sec.gov/LATEST/search-index?q={q}"
        f"&forms=SC+14D9,SC+14D-9"
        f"&dateRange=custom&startdt={start}&enddt={end}"
    )


def build_rows(
    *,
    candidates: list[dict[str, str]],
    processed_tickers: set[str],
    dates_by_case: dict[str, dict[str, str]],
    start: int,
    limit: int,
) -> list[dict[str, str]]:
    acquired = [
        r for r in candidates
        if r.get("likely_outcome_type", "").upper() == "ACQUIRED"
        and r.get("ticker", "").upper() not in processed_tickers
    ]

    # Sort by case_id numeric part so RHC-0051 comes before RHC-0052 etc.
    def case_num(row: dict[str, str]) -> int:
        parts = row.get("candidate_id", "").split("-")
        return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 9999

    acquired.sort(key=case_num)

    # Slice to the requested window (start is 1-indexed batch number)
    # start=51, limit=20 → indices [50:70] of the full acquired-not-processed list
    idx_start = start - 51          # offset relative to first unprocessed case
    idx_start = max(idx_start, 0)
    batch = acquired[idx_start: idx_start + limit]

    rows: list[dict[str, str]] = []
    for candidate in batch:
        case_id = candidate.get("candidate_id", "").strip()
        ticker  = candidate.get("ticker", "").strip()
        company = candidate.get("company_name", "").strip()
        year    = candidate.get("likely_outcome_year", "").strip()

        date_row = dates_by_case.get(case_id, {})
        current_date = date_row.get("acquisition_announcement_date", "").strip()
        confidence   = date_row.get("confidence", "").strip().upper()

        needs_backfill = "TRUE" if confidence not in {"HIGH", "MEDIUM"} else "FALSE"

        notes_parts = []
        if not current_date:
            notes_parts.append("No announcement date in dates file.")
        elif confidence == "LOW":
            notes_parts.append(f"Date present ({current_date}) but LOW confidence — verify before filing collection.")
        elif confidence in {"HIGH", "MEDIUM"}:
            notes_parts.append(f"Date confirmed ({current_date}, {confidence}). Run filing collector.")
        notes = " ".join(notes_parts) or "Check EDGAR merger 8-K."

        rows.append({
            "case_id":                   case_id,
            "ticker":                    ticker,
            "company":                   company,
            "likely_outcome_year":       year,
            "current_announcement_date": current_date,
            "date_confidence":           confidence,
            "needs_date_backfill":       needs_backfill,
            "edgar_company_search_url":  edgar_company_search(ticker),
            "edgar_merger_8k_query_url": edgar_merger_8k_url(ticker, company, year),
            "edgar_sc14d9_query_url":    edgar_sc14d9_url(ticker, company, year),
            "suggested_query_terms":     f'"{company}" "agreement and plan of merger"',
            "notes":                     notes,
        })

    return rows


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    needs_backfill  = [r for r in rows if r["needs_date_backfill"] == "TRUE"]
    already_present = [r for r in rows if r["needs_date_backfill"] == "FALSE"]

    lines = [
        "# Batch 51–70 Date Prefill Queue",
        "",
        f"Generated: {RUN_DATE}",
        "",
        "Work queue only. Dates in this report are not inserted into any canonical file.",
        "Resolve each NEEDS_DATE_BACKFILL=TRUE case before running the filing collector.",
        "",
        "## Summary",
        "",
        f"- Cases in scope: {len(rows)}",
        f"- Needs date backfill: {len(needs_backfill)}",
        f"- Date already present: {len(already_present)}",
        "",
        "## Cases Needing Date Backfill",
        "",
    ]

    if needs_backfill:
        lines.append("| case_id | ticker | company | year | edgar_merger_8k_query_url |")
        lines.append("|---|---|---|---|---|")
        for r in needs_backfill:
            lines.append(
                f"| {r['case_id']} | {r['ticker']} | {r['company'][:35]} "
                f"| {r['likely_outcome_year']} | {r['edgar_merger_8k_query_url'][:80]}... |"
            )
    else:
        lines.append("None — all cases in scope have a date.")

    lines += [
        "",
        "## Cases With Date Present",
        "",
    ]

    if already_present:
        lines.append("| case_id | ticker | date | confidence |")
        lines.append("|---|---|---|---|")
        for r in already_present:
            lines.append(
                f"| {r['case_id']} | {r['ticker']} "
                f"| {r['current_announcement_date']} | {r['date_confidence']} |"
            )
    else:
        lines.append("None.")

    lines += [
        "",
        "## Next Steps",
        "",
        "1. For each NEEDS_DATE_BACKFILL=TRUE case:",
        "   - Open the edgar_merger_8k_query_url.",
        "   - Find the earliest 8-K with 'agreement and plan of merger' in the filing.",
        "   - Note the filing date and add a CURATED_DATE_EVIDENCE entry to",
        "     src/historical_case_tools/acquisition_announcement_date_backfiller.py.",
        "   - Or add a source_evidence row with evidence_type=8K_MERGER.",
        "2. Re-run acquisition_announcement_date_backfiller.py.",
        "3. Confirm all 20 cases have HIGH or MEDIUM confidence.",
        "4. Run pre_announcement_filing_collector.py.",
        "5. Then run exception_queue_builder.py to build the review queue.",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    candidates   = read_csv(args.candidates)
    dates_raw    = read_csv(args.dates)
    batch_results = read_csv(args.batch_results)

    processed_tickers = {r["ticker"].upper() for r in batch_results if r.get("ticker")}
    dates_by_case     = {r["case_id"].strip(): r for r in dates_raw if r.get("case_id")}

    rows = build_rows(
        candidates=candidates,
        processed_tickers=processed_tickers,
        dates_by_case=dates_by_case,
        start=args.start,
        limit=args.limit,
    )

    write_csv(args.output, rows, OUTPUT_FIELDS)
    write_report(args.report, rows)

    needs = sum(1 for r in rows if r["needs_date_backfill"] == "TRUE")
    print(f"Cases in scope:        {len(rows)}")
    print(f"Needs date backfill:   {needs}")
    print(f"Date already present:  {len(rows) - needs}")
    print(f"Queue  -> {args.output}")
    print(f"Report -> {args.report}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start",         type=int, default=51,
                        help="First batch number (1-indexed, default 51)")
    parser.add_argument("--limit",         type=int, default=20,
                        help="Number of cases to include (default 20)")
    parser.add_argument("--candidates",    type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--dates",         type=Path, default=DEFAULT_DATES)
    parser.add_argument("--batch-results", type=Path, default=DEFAULT_BATCH_RESULTS)
    parser.add_argument("--output",        type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--report",        type=Path, default=DEFAULT_OUTPUT_REPORT)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
