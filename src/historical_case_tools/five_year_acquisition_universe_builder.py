#!/usr/bin/env python3
"""
five_year_acquisition_universe_builder.py

Build a conservative, review-first candidate universe of US-listed biotech
acquisitions from the last five years using local historical case files.

This is candidate generation only. It does not adjudicate prior signals, mutate
source evidence, mark cases VERIFIED, or call live APIs.

Usage:
    python3 src/historical_case_tools/five_year_acquisition_universe_builder.py
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

DEFAULT_CANDIDATES = HISTORICAL_DIR / "resolved_case_candidates.csv"
DEFAULT_DATES = HISTORICAL_DIR / "acquisition_announcement_dates.csv"
DEFAULT_SOURCE_EVIDENCE = HISTORICAL_DIR / "source_evidence.csv"
DEFAULT_OUTPUT = HISTORICAL_DIR / "five_year_acquisition_universe_candidates.csv"
DEFAULT_REPORT = HISTORICAL_DIR / "five_year_acquisition_universe_report.md"

RUN_DATE = date.today().isoformat()
DEFAULT_START_YEAR = date.today().year - 5

OUTPUT_FIELDS = [
    "candidate_id",
    "ticker",
    "company",
    "acquirer",
    "announcement_date",
    "announcement_year",
    "source_url",
    "source_type",
    "filing_type",
    "accession_number",
    "deal_type_guess",
    "inclusion_status",
    "inclusion_reason",
    "exclusion_reason",
    "confidence",
    "existing_case_id_if_any",
    "already_in_first_50",
    "already_in_batch_51_70",
    "needs_date_backfill",
    "needs_standard_deal_confirmation",
    "fmp_profile_status",
    "notes",
]


EXCLUDE_PATTERNS = [
    ("EXCLUDE_ASSET_TRANSACTION", re.compile(r"\b(asset sale|asset purchase|asset-only|divestiture)\b", re.I)),
    ("EXCLUDE_LICENSE_ONLY", re.compile(r"\b(license|licensing|collaboration-only|royalty)\b", re.I)),
    ("EXCLUDE_REVERSE_MERGER_OR_SPAC", re.compile(r"\b(reverse merger|spac|de-spac|business combination)\b", re.I)),
    ("EXCLUDE_BANKRUPTCY_OR_LIQUIDATION", re.compile(r"\b(bankrupt|bankruptcy|liquidation|wind[- ]?down|chapter 11|chapter 7)\b", re.I)),
]

STANDARD_DEAL_PATTERN = re.compile(
    r"\b(acquisition|acquire|acquired|merger|tender offer|agreement and plan of merger|buyout)\b",
    re.I,
)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def group_by(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        value = row.get(key, "").strip()
        if value:
            grouped.setdefault(value, []).append(row)
    return grouped


def index_by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    indexed = {}
    for row in rows:
        value = row.get(key, "").strip()
        if value and value not in indexed:
            indexed[value] = row
    return indexed


def case_number(case_id: str) -> int:
    parts = case_id.split("-")
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    return 999999


def normalize_company(value: str) -> str:
    text = value.lower()
    text = re.sub(r"\b(inc|inc\.|corp|corp\.|corporation|pharmaceuticals|therapeutics|holdings|plc|ltd|limited|company|co)\b", "", text)
    return re.sub(r"[^a-z0-9]+", "", text)


def infer_acquirer(candidate: dict[str, str]) -> str:
    hint = candidate.get("outcome_source_hint", "").strip()
    patterns = [
        r"^([A-Z][A-Za-z&.\- ]{1,45}) acquisition",
        r"^([A-Z][A-Za-z&.\- ]{1,45}) deal",
        r"^EDGAR 8-K ([A-Z][A-Za-z&.\- ]{1,45}) deal",
        r"^([A-Z][A-Za-z&.\- ]{1,45}) merger",
        r"by ([A-Z][A-Za-z&.\- ]{1,45})",
    ]
    for pattern in patterns:
        match = re.search(pattern, hint)
        if match:
            value = match.group(1).strip(" ;,.")
            if value.upper() not in {"EDGAR"}:
                return value
    return ""


def deal_type_guess(text: str) -> str:
    lowered = text.lower()
    if "tender offer" in lowered:
        return "TENDER_OFFER"
    if "agreement and plan of merger" in lowered or "merger" in lowered:
        return "MERGER"
    if "acquisition" in lowered or "acquire" in lowered or "acquired" in lowered:
        return "ACQUISITION"
    if "asset purchase" in lowered or "asset sale" in lowered:
        return "ASSET_TRANSACTION"
    if "license" in lowered or "collaboration" in lowered:
        return "LICENSE_OR_COLLABORATION"
    return "UNKNOWN"


def classify_inclusion(candidate: dict[str, str], *, has_date: bool, has_source: bool) -> tuple[str, str, str, str]:
    text = " ".join([
        candidate.get("outcome_source_hint", ""),
        candidate.get("reason_for_inclusion", ""),
        candidate.get("notes", ""),
    ])
    for status, pattern in EXCLUDE_PATTERNS:
        if pattern.search(text):
            return status, "", f"Local candidate text contains exclusion pattern for {status}.", "MEDIUM"
    if STANDARD_DEAL_PATTERN.search(text):
        if has_date and has_source:
            return (
                "INCLUDE_STANDARD_PUBLIC_COMPANY_ACQUISITION",
                "Local candidate has standard acquisition/merger language plus existing date/source coverage.",
                "",
                "HIGH",
            )
        if has_date:
            return (
                "INCLUDE_STANDARD_PUBLIC_COMPANY_ACQUISITION",
                "Local candidate has standard acquisition/merger language and existing announcement date; source evidence still should be checked.",
                "",
                "MEDIUM",
            )
        return (
            "MAYBE_NEEDS_REVIEW",
            "Local candidate has standard acquisition/merger language but needs announcement-date/source confirmation.",
            "",
            "LOW",
        )
    return "MAYBE_NEEDS_REVIEW", "Candidate is acquired in local seed data but deal structure needs source-backed confirmation.", "", "LOW"


def duplicate_group_key(row: dict[str, str]) -> tuple[str, str]:
    return row.get("ticker", "").upper(), normalize_company(row.get("company", ""))


def duplicate_rank(row: dict[str, str]) -> tuple[int, int, int]:
    has_date = 1 if row.get("needs_date_backfill") == "FALSE" else 0
    has_source = 1 if row.get("needs_standard_deal_confirmation") == "FALSE" else 0
    lower_case_num = -case_number(row.get("candidate_id", ""))
    return has_source, has_date, lower_case_num


def apply_duplicate_flags(rows: list[dict[str, str]]) -> None:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = duplicate_group_key(row)
        if key[0] or key[1]:
            grouped.setdefault(key, []).append(row)

    for group in grouped.values():
        if len(group) < 2:
            continue
        keeper = sorted(group, key=duplicate_rank, reverse=True)[0]
        for row in group:
            if row is keeper:
                continue
            row["inclusion_status"] = "EXCLUDE_DUPLICATE"
            row["inclusion_reason"] = ""
            row["exclusion_reason"] = f"Duplicate ticker/company candidate; retained {keeper['candidate_id']} as the stronger source/date row."
            row["confidence"] = "LOW"
            row["needs_standard_deal_confirmation"] = "TRUE"
            row["notes"] = (row.get("notes", "") + f" Duplicate of {keeper['candidate_id']}.").strip()


def best_source(
    case_id: str,
    date_row: dict[str, str],
    evidence_rows: list[dict[str, str]],
    candidate: dict[str, str],
) -> dict[str, str]:
    if date_row.get("source_url", "").strip():
        return {
            "source_url": date_row.get("source_url", "").strip(),
            "source_type": date_row.get("source_evidence_type", "").strip() or "ACQUISITION_DATE_TABLE",
            "filing_type": "",
            "accession_number": "",
        }

    preferred = []
    for row in evidence_rows:
        evidence_type = row.get("evidence_type", "").upper()
        supports = row.get("supports_field", "").upper()
        if "MERGER" in evidence_type or "DEAL_ANNOUNCEMENT_DATE" in supports or "OUTCOME" in supports:
            preferred.append(row)
    if not preferred:
        preferred = [row for row in evidence_rows if row.get("source_url", "").strip()]

    if preferred:
        row = preferred[0]
        return {
            "source_url": row.get("source_url", "").strip(),
            "source_type": row.get("evidence_type", "").strip() or row.get("source_name", "").strip(),
            "filing_type": row.get("filing_type", "").strip(),
            "accession_number": row.get("accession_number", "").strip(),
        }

    return {
        "source_url": candidate.get("outcome_edgar_query", "").strip(),
        "source_type": "LOCAL_CANDIDATE_QUERY",
        "filing_type": "",
        "accession_number": "",
    }


def build_rows(
    *,
    candidates: list[dict[str, str]],
    dates_by_case: dict[str, dict[str, str]],
    evidence_by_case: dict[str, list[dict[str, str]]],
    start_year: int,
) -> list[dict[str, str]]:
    acquired = []
    for row in candidates:
        if row.get("likely_outcome_type", "").strip().upper() != "ACQUIRED":
            continue
        year = row.get("likely_outcome_year", "").strip()
        if not year.isdigit() or int(year) < start_year:
            continue
        acquired.append(row)
    acquired.sort(key=lambda row: (row.get("likely_outcome_year", ""), case_number(row.get("candidate_id", "")), row.get("ticker", "")))

    rows: list[dict[str, str]] = []
    for candidate in acquired:
        case_id = candidate.get("candidate_id", "").strip()
        ticker = candidate.get("ticker", "").strip().upper()
        date_row = dates_by_case.get(case_id, {})
        evidence_rows = evidence_by_case.get(case_id, [])
        announcement_date = date_row.get("acquisition_announcement_date", "").strip()
        announcement_year = announcement_date[:4] if announcement_date else candidate.get("likely_outcome_year", "").strip()
        acquirer = infer_acquirer(candidate)
        has_date = bool(announcement_date and date_row.get("confidence", "").strip().upper() in {"HIGH", "MEDIUM"})
        has_source = bool(evidence_rows or date_row.get("source_url", "").strip())
        inclusion_status, inclusion_reason, exclusion_reason, confidence = classify_inclusion(
            candidate,
            has_date=has_date,
            has_source=has_source,
        )
        source = best_source(case_id, date_row, evidence_rows, candidate)
        notes = []
        if has_date:
            notes.append(f"Date table coverage: {date_row.get('confidence', '').strip().upper()}.")
        else:
            notes.append("No HIGH/MEDIUM date table coverage.")
        if evidence_rows:
            notes.append(f"Source evidence rows: {len(evidence_rows)}.")
        else:
            notes.append("No source_evidence rows found.")
        if case_number(case_id) <= 50:
            notes.append("Already part of first 50-case study.")
        elif 51 <= case_number(case_id) <= 70:
            notes.append("Already part of Batch 51-70 workflow.")

        rows.append({
            "candidate_id": case_id,
            "ticker": ticker,
            "company": candidate.get("company_name", "").strip(),
            "acquirer": acquirer,
            "announcement_date": announcement_date,
            "announcement_year": announcement_year,
            "source_url": source["source_url"],
            "source_type": source["source_type"],
            "filing_type": source["filing_type"],
            "accession_number": source["accession_number"],
            "deal_type_guess": deal_type_guess(" ".join([candidate.get("outcome_source_hint", ""), source["source_type"]])),
            "inclusion_status": inclusion_status,
            "inclusion_reason": inclusion_reason,
            "exclusion_reason": exclusion_reason,
            "confidence": confidence,
            "existing_case_id_if_any": case_id,
            "already_in_first_50": "TRUE" if case_number(case_id) <= 50 else "FALSE",
            "already_in_batch_51_70": "TRUE" if 51 <= case_number(case_id) <= 70 else "FALSE",
            "needs_date_backfill": "FALSE" if has_date else "TRUE",
            "needs_standard_deal_confirmation": "FALSE" if inclusion_status == "INCLUDE_STANDARD_PUBLIC_COMPANY_ACQUISITION" and has_source else "TRUE",
            "fmp_profile_status": "NOT_CHECKED_OFFLINE_BUILDER",
            "notes": " ".join(notes),
        })
    apply_duplicate_flags(rows)
    return rows


def markdown_table(rows: list[dict[str, str]], columns: list[str], limit: int = 20) -> str:
    shown = rows[:limit]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in shown:
        values = [str(row.get(column, "")).replace("|", "/") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    if len(rows) > limit:
        lines.append(f"| ... | {len(rows) - limit} more rows |  | | |")
    return "\n".join(lines)


def write_report(path: Path, rows: list[dict[str, str]], *, start_year: int) -> None:
    status_counts = Counter(row["inclusion_status"] for row in rows)
    covered = [r for r in rows if r["already_in_first_50"] == "TRUE" or r["already_in_batch_51_70"] == "TRUE"]
    new_eligible = [
        r for r in rows
        if r["inclusion_status"] == "INCLUDE_STANDARD_PUBLIC_COMPANY_ACQUISITION"
        and r["already_in_first_50"] == "FALSE"
        and r["already_in_batch_51_70"] == "FALSE"
    ]
    needs_review = [r for r in rows if r["inclusion_status"] == "MAYBE_NEEDS_REVIEW"]
    missing_source = [r for r in rows if r["needs_standard_deal_confirmation"] == "TRUE" or r["needs_date_backfill"] == "TRUE"]
    excluded = [r for r in rows if r["inclusion_status"].startswith("EXCLUDE_")]

    lines = [
        "# Five-Year Acquisition Universe Candidate Report",
        "",
        f"Generated: {RUN_DATE}",
        "",
        "Candidate-generation layer only. No classifications changed. No cases marked VERIFIED or CALIBRATION_ELIGIBLE.",
        "",
        "## Scope",
        "",
        f"- Start year: {start_year}",
        "- Source basis: local historical case files only.",
        "- Target universe: US-listed biotech / biopharma / life sciences public-company acquisitions.",
        "- External hooks: FMP, EDGAR submissions, SEC form search, and press-release exhibits are planned but not called by this first version.",
        "",
        "## Summary",
        "",
        f"- Total candidates found: {len(rows)}",
        f"- Already covered by first 50 or Batch 51-70: {len(covered)}",
        f"- New likely eligible candidates: {len(new_eligible)}",
        f"- Candidates needing review: {len(needs_review)}",
        f"- Excluded candidates: {len(excluded)}",
        f"- Missing source/date confirmation gaps: {len(missing_source)}",
        "",
        "## Candidates By Inclusion Status",
        "",
    ]
    lines.extend(f"- {status}: {count}" for status, count in status_counts.most_common())
    lines.extend([
        "",
        "## New Likely Eligible Candidates",
        "",
        markdown_table(new_eligible, ["candidate_id", "ticker", "company", "announcement_year", "acquirer"], limit=30) if new_eligible else "None.",
        "",
        "## Candidates Needing Review",
        "",
        markdown_table(needs_review, ["candidate_id", "ticker", "company", "announcement_year", "needs_date_backfill"], limit=30) if needs_review else "None.",
        "",
        "## Excluded Candidates By Reason",
        "",
    ])
    if excluded:
        excluded_counts = Counter(row["inclusion_status"] for row in excluded)
        lines.extend(f"- {status}: {count}" for status, count in excluded_counts.most_common())
    else:
        lines.append("None.")
    lines.extend([
        "",
        "## Missing Source Gaps",
        "",
        markdown_table(missing_source, ["candidate_id", "ticker", "company", "announcement_year", "needs_date_backfill", "needs_standard_deal_confirmation"], limit=30) if missing_source else "None.",
        "",
        "## Recommended Next Batch Construction",
        "",
        "1. Use `INCLUDE_STANDARD_PUBLIC_COMPANY_ACQUISITION` rows not already in the first 50 or Batch 51-70.",
        "2. Prioritize rows with HIGH confidence and existing date/source coverage.",
        "3. Move MAYBE rows into a date/source confirmation queue before filing collection.",
        "4. Exclude duplicate, asset-only, license-only, reverse merger/SPAC, and bankruptcy/liquidation rows unless primary evidence proves standard public-company acquisition treatment.",
        "5. Add FMP context later for market cap, liquidity, and tradability, but keep EDGAR/source evidence as the classification source of truth.",
        "",
        "## Risks And Caveats",
        "",
        "- Local seed data is not complete enough to claim every US-listed biotech acquisition from the last five years.",
        "- Current output can organize the known candidate universe, but cannot fully replace external discovery yet.",
        "- Some candidates may have stale ticker mappings, delisted-company coverage gaps, or incorrect seed acquirer/year hints.",
        "- FMP profile and delisting hooks are placeholders in this version.",
        "- Candidate inclusion is not prior-signal adjudication.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> list[dict[str, str]]:
    candidates = read_csv(args.candidates)
    dates = read_csv(args.dates)
    evidence = read_csv(args.source_evidence)
    rows = build_rows(
        candidates=candidates,
        dates_by_case=index_by(dates, "case_id"),
        evidence_by_case=group_by(evidence, "case_id"),
        start_year=args.start_year,
    )
    write_csv(args.output, rows)
    write_report(args.report, rows, start_year=args.start_year)

    covered = sum(1 for row in rows if row["already_in_first_50"] == "TRUE" or row["already_in_batch_51_70"] == "TRUE")
    new_eligible = sum(
        1 for row in rows
        if row["inclusion_status"] == "INCLUDE_STANDARD_PUBLIC_COMPANY_ACQUISITION"
        and row["already_in_first_50"] == "FALSE"
        and row["already_in_batch_51_70"] == "FALSE"
    )
    print(f"Total candidates found:      {len(rows)}")
    print(f"Already covered:             {covered}")
    print(f"New likely eligible:         {new_eligible}")
    print(f"Candidate CSV -> {args.output}")
    print(f"Report        -> {args.report}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--dates", type=Path, default=DEFAULT_DATES)
    parser.add_argument("--source-evidence", type=Path, default=DEFAULT_SOURCE_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
