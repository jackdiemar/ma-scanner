#!/usr/bin/env python3
"""
fmp_candidate_discovery_stub.py

Read-only scaffold for future FMP-backed acquisition candidate discovery.

FMP is intended for universe discovery and market context. EDGAR and other
source-backed evidence remain the source of truth for acquisition confirmation
and prior-signal classification.

Usage:
    python3 src/historical_case_tools/fmp_candidate_discovery_stub.py --lookback-years 5
"""

from __future__ import annotations

import argparse
import csv
import os
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

DEFAULT_UNIVERSE = HISTORICAL_DIR / "five_year_acquisition_universe_candidates.csv"
DEFAULT_RESOLVED = HISTORICAL_DIR / "resolved_case_candidates.csv"
DEFAULT_DATES = HISTORICAL_DIR / "acquisition_announcement_dates.csv"
DEFAULT_OUTPUT = HISTORICAL_DIR / "fmp_candidate_discovery_stub_candidates.csv"
DEFAULT_REPORT = HISTORICAL_DIR / "fmp_candidate_discovery_stub_report.md"

RUN_DATE = date.today().isoformat()

CANDIDATE_FIELDS = [
    "ticker",
    "company",
    "fmp_exchange",
    "fmp_sector",
    "fmp_industry",
    "delisted_date",
    "ipo_date",
    "last_price_date",
    "possible_acquisition_flag",
    "possible_biotech_flag",
    "needs_edgar_confirmation",
    "existing_case_id_if_any",
    "already_in_universe",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_candidates(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CANDIDATE_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def ticker_value(row: dict[str, str]) -> str:
    return row.get("ticker", "").strip().upper()


def build_local_coverage(
    universe_rows: list[dict[str, str]],
    resolved_rows: list[dict[str, str]],
    date_rows: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    coverage: dict[str, dict[str, str]] = {}

    for row in universe_rows:
        ticker = ticker_value(row)
        if not ticker:
            continue
        entry = coverage.setdefault(ticker, {})
        entry["already_in_universe"] = "TRUE"
        if row.get("existing_case_id_if_any", "").strip():
            entry["existing_case_id_if_any"] = row["existing_case_id_if_any"].strip()

    for row in resolved_rows:
        ticker = ticker_value(row)
        if not ticker:
            continue
        entry = coverage.setdefault(ticker, {})
        if row.get("candidate_id", "").strip():
            entry.setdefault("existing_case_id_if_any", row["candidate_id"].strip())
        entry["in_resolved_candidates"] = "TRUE"

    for row in date_rows:
        ticker = ticker_value(row)
        if not ticker:
            continue
        entry = coverage.setdefault(ticker, {})
        if row.get("case_id", "").strip():
            entry.setdefault("existing_case_id_if_any", row["case_id"].strip())
        entry["has_announcement_date"] = "TRUE"

    return coverage


def discover_with_fmp_live(*, lookback_years: int) -> tuple[list[dict[str, str]], str]:
    return [], (
        "Live FMP discovery is intentionally not implemented yet. "
        f"The requested lookback window was {lookback_years} years."
    )


def annotate_candidates(
    rows: list[dict[str, str]],
    coverage: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    annotated = []
    for row in rows:
        normalized = {field: row.get(field, "").strip() for field in CANDIDATE_FIELDS}
        ticker = normalized["ticker"].upper()
        local = coverage.get(ticker, {})
        normalized["ticker"] = ticker
        normalized["existing_case_id_if_any"] = local.get("existing_case_id_if_any", normalized["existing_case_id_if_any"])
        normalized["already_in_universe"] = local.get("already_in_universe", "FALSE")
        normalized["needs_edgar_confirmation"] = "TRUE"
        if normalized["notes"]:
            normalized["notes"] += " "
        normalized["notes"] += "FMP discovery candidate; requires EDGAR/source confirmation before inclusion."
        annotated.append(normalized)
    return annotated


def write_report(
    path: Path,
    *,
    lookback_years: int,
    fmp_key_found: bool,
    live_api_enabled: bool,
    live_note: str,
    candidate_count: int,
    universe_count: int,
    resolved_count: int,
    date_count: int,
    coverage_ticker_count: int,
) -> None:
    key_status = "FOUND" if fmp_key_found else "MISSING"
    live_status = "ENABLED" if live_api_enabled else "DISABLED"
    mode = "LIVE_STUB" if live_api_enabled and fmp_key_found else "OFFLINE_PLACEHOLDER"

    text = f"""# FMP Candidate Discovery Stub Report

Generated: {RUN_DATE}

Status: read-only design stub. No historical classifications were changed.

## Run Summary

- Mode: {mode}
- Lookback years requested: {lookback_years}
- FMP_API_KEY: {key_status}
- Live API flag: {live_status}
- Candidate rows written: {candidate_count}
- Live discovery note: {live_note}

## Local Coverage Loaded

| Local file | Rows loaded |
|---|---:|
| five_year_acquisition_universe_candidates.csv | {universe_count} |
| resolved_case_candidates.csv | {resolved_count} |
| acquisition_announcement_dates.csv | {date_count} |

Unique tickers available for future coverage matching: {coverage_ticker_count}

## Placeholder Result

This run does not pull FMP data by default. The candidate CSV is written with
the expected schema so future live discovery can append FMP-derived candidates
without mutating the five-year universe builder or any adjudication files.

If `FMP_API_KEY` is missing, this behavior is expected. If the key exists, the
script still avoids live calls unless `--enable-live-api` is passed.

## Intended Future Flow

1. Use FMP delisted/profile data to identify possible biotech or biopharma
   companies that disappeared during the lookback window.
2. Mark whether each ticker is already covered by the five-year universe,
   resolved candidate seeds, or announcement-date table.
3. Send new possible acquisitions into the five-year universe builder as
   review candidates.
4. Confirm every candidate with EDGAR, merger filings, tender-offer filings, or
   source-backed press releases before adding it to the acquisition denominator.

## Guardrails

- FMP is for discovery, ticker validation, delisting context, and market data.
- EDGAR/source evidence remains the source of truth for acquisition evidence.
- FMP must not classify prior process signals.
- FMP must not mark cases VERIFIED or CALIBRATION_ELIGIBLE.
- Missing FMP data should not fail the historical case factory.

## Risks

- Survivorship bias in active-company profile data.
- Stale ticker mappings after acquisitions, renamings, or delistings.
- Delisted biotech coverage gaps.
- Paid endpoint and rate-limit constraints.
- Historical market cap and price fields may need date-bound validation.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only FMP acquisition candidate discovery stub.")
    parser.add_argument("--lookback-years", type=int, default=5, help="Lookback window for future FMP discovery.")
    parser.add_argument("--enable-live-api", action="store_true", help="Allow future live FMP calls when FMP_API_KEY exists.")
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE, help="Existing five-year universe candidate CSV.")
    parser.add_argument("--resolved", type=Path, default=DEFAULT_RESOLVED, help="Existing resolved candidate seed CSV.")
    parser.add_argument("--dates", type=Path, default=DEFAULT_DATES, help="Existing acquisition announcement date CSV.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output candidate CSV.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Output markdown report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    universe_rows = read_csv(args.universe)
    resolved_rows = read_csv(args.resolved)
    date_rows = read_csv(args.dates)
    coverage = build_local_coverage(universe_rows, resolved_rows, date_rows)

    fmp_key_found = bool(os.environ.get("FMP_API_KEY"))
    live_api_enabled = bool(args.enable_live_api and fmp_key_found)

    if args.enable_live_api and not fmp_key_found:
        live_note = "FMP_API_KEY was not found, so live API calls were skipped."
        raw_candidates: list[dict[str, str]] = []
    elif live_api_enabled:
        raw_candidates, live_note = discover_with_fmp_live(lookback_years=args.lookback_years)
    else:
        if fmp_key_found:
            live_note = "FMP_API_KEY was found, but --enable-live-api was not passed."
        else:
            live_note = "FMP_API_KEY was not found; wrote placeholder outputs without live API calls."
        raw_candidates = []

    candidates = annotate_candidates(raw_candidates, coverage)
    write_candidates(args.output, candidates)
    write_report(
        args.report,
        lookback_years=args.lookback_years,
        fmp_key_found=fmp_key_found,
        live_api_enabled=live_api_enabled,
        live_note=live_note,
        candidate_count=len(candidates),
        universe_count=len(universe_rows),
        resolved_count=len(resolved_rows),
        date_count=len(date_rows),
        coverage_ticker_count=len(coverage),
    )

    if not fmp_key_found:
        print("FMP_API_KEY not found. Wrote placeholder outputs without live API calls.")
    elif not args.enable_live_api:
        print("FMP_API_KEY found. Live API calls skipped because --enable-live-api was not passed.")
    else:
        print("FMP_API_KEY found and --enable-live-api passed. Live discovery functions are still placeholders.")
    print(f"Wrote candidate CSV: {args.output}")
    print(f"Wrote report: {args.report}")
    print(f"Candidate rows written: {len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
