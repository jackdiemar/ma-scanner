#!/usr/bin/env python3
"""
source_evidence_autofill.py

Generate draft ADJUDICATION_NOTE placeholder rows for Batch 51–70 cases.

Reads the exception queue (batch_51_70_exception_queue.csv) and creates a draft
source_evidence CSV with one ADJUDICATION_NOTE row per case.  Only cases in tiers
P1, P2, P3, P4, and BLOCKED get draft rows — P5, P6, and PENDING_FILING_COLLECTION
cases do not need pre-populated draft evidence because they either have nothing to
adjudicate yet or are already closed.

OUTPUT IS A DRAFT FILE ONLY.  It does NOT write to source_evidence.csv.
Every row is marked verification_status=DRAFT_PENDING_REVIEW.
A researcher must review, fill in PLACEHOLDER fields, and manually append to
source_evidence.csv after verification.

Usage:
    python3 src/historical_case_tools/source_evidence_autofill.py
    python3 src/historical_case_tools/source_evidence_autofill.py --start 51 --limit 20
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

DEFAULT_EXCEPTION_QUEUE = HISTORICAL_DIR / "batch_51_70_exception_queue.csv"
DEFAULT_OUTPUT_CSV      = HISTORICAL_DIR / "batch_51_70_source_evidence_draft.csv"
DEFAULT_OUTPUT_REPORT   = HISTORICAL_DIR / "batch_51_70_source_evidence_draft_report.md"

RUN_DATE = str(date.today())

# Tiers that warrant a draft placeholder row
DRAFT_TIERS = {"P1", "P2", "P3", "P4", "BLOCKED"}

OUTPUT_FIELDS = [
    "evidence_id",
    "case_id",
    "ticker",
    "evidence_type",
    "source_name",
    "source_url",
    "filing_type",
    "filing_date",
    "accession_number",
    "exhibit_number",
    "excerpt",
    "supports_field",
    "confidence",
    "verification_status",
    "added_by",
    "added_date",
    "notes",
]

PLACEHOLDER = "PLACEHOLDER_PENDING_REVIEW"


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


def _draft_note(tier: str, reason: str) -> str:
    return (
        f"[DRAFT] Review before adding to source_evidence.csv. "
        f"Priority tier: {tier}. Reason: {reason} "
        f"Fill all PLACEHOLDER fields from the actual filing before promoting."
    )


def build_rows(queue_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for q in queue_rows:
        tier   = q.get("priority_tier", "").strip()
        if tier not in DRAFT_TIERS:
            continue

        case_id = q.get("case_id", "").strip()
        ticker  = q.get("ticker", "").strip()
        reason  = q.get("priority_reason", "").strip()

        rows.append({
            "evidence_id":         f"{case_id}-ADJ-DRAFT-001",
            "case_id":             case_id,
            "ticker":              ticker,
            "evidence_type":       "ADJUDICATION_NOTE",
            "source_name":         PLACEHOLDER,
            "source_url":          PLACEHOLDER,
            "filing_type":         PLACEHOLDER,
            "filing_date":         PLACEHOLDER,
            "accession_number":    PLACEHOLDER,
            "exhibit_number":      "",
            "excerpt":             PLACEHOLDER,
            "supports_field":      "had_prior_process_signal",
            "confidence":          "LOW",
            "verification_status": "DRAFT_PENDING_REVIEW",
            "added_by":            "source_evidence_autofill",
            "added_date":          RUN_DATE,
            "notes":               _draft_note(tier, reason),
        })

    return rows


def write_report(path: Path, draft_rows: list[dict[str, str]],
                 queue_rows: list[dict[str, str]]) -> None:
    skipped = [
        q for q in queue_rows
        if q.get("priority_tier", "") not in DRAFT_TIERS
    ]

    lines = [
        "# Batch 51–70 Source Evidence Draft",
        "",
        f"Generated: {RUN_DATE}",
        "",
        "Draft file only. Do NOT copy these rows to source_evidence.csv without verification.",
        "All PLACEHOLDER fields must be filled from the actual filing before promoting.",
        "",
        "## Summary",
        "",
        f"- Draft rows generated: {len(draft_rows)}",
        f"- Cases skipped (P5/P6/PENDING_FILING_COLLECTION): {len(skipped)}",
        "",
        "## Draft Rows",
        "",
    ]

    if draft_rows:
        lines.append("| evidence_id | ticker | tier | reason |")
        lines.append("|---|---|---|---|")
        for r in draft_rows:
            case_id = r["case_id"]
            # Pull tier/reason back from the original queue row
            matching = next(
                (q for q in queue_rows if q.get("case_id", "") == case_id), {}
            )
            tier   = matching.get("priority_tier", "")
            reason = matching.get("priority_reason", "")[:60]
            lines.append(
                f"| {r['evidence_id']} | {r['ticker']} | {tier} | {reason} |"
            )
    else:
        lines.append("No draft rows generated — all cases are P5/P6/PENDING_FILING_COLLECTION.")

    lines += [
        "",
        "## Skipped Cases",
        "",
    ]

    if skipped:
        lines.append("| case_id | ticker | tier | reason |")
        lines.append("|---|---|---|---|")
        for q in skipped:
            lines.append(
                f"| {q['case_id']} | {q['ticker']} "
                f"| {q['priority_tier']} | {q.get('priority_reason', '')[:60]} |"
            )
    else:
        lines.append("None.")

    lines += [
        "",
        "## Workflow",
        "",
        "1. Open each PLACEHOLDER row.",
        "2. Find the actual filing in EDGAR using the edgar_company_search_url from the exception queue.",
        "3. Fill: source_name, source_url, filing_type, filing_date, accession_number, excerpt.",
        "4. Change verification_status from DRAFT_PENDING_REVIEW to a real status.",
        "5. Change confidence from LOW to HIGH/MEDIUM/LOW based on verified evidence.",
        "6. Append to data/historical_cases/source_evidence.csv manually.",
        "7. Do not mark any case VERIFIED or CALIBRATION_ELIGIBLE.",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    queue_rows = read_csv(args.exception_queue)
    draft_rows = build_rows(queue_rows)

    write_csv(args.output, draft_rows, OUTPUT_FIELDS)
    write_report(args.report, draft_rows, queue_rows)

    print(f"Draft rows generated: {len(draft_rows)}")
    print(f"Cases skipped:        {len(queue_rows) - len(draft_rows)}")
    print(f"Draft CSV  -> {args.output}")
    print(f"Draft report -> {args.report}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exception-queue", type=Path, default=DEFAULT_EXCEPTION_QUEUE)
    parser.add_argument("--output",          type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--report",          type=Path, default=DEFAULT_OUTPUT_REPORT)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
