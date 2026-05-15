#!/usr/bin/env python3
"""
batch_51_70_queue_summary.py

Read-only summary helper for the Batch 51-70 exception queue.

This script does not adjudicate cases, mutate CSVs, edit source evidence, or
mark any case VERIFIED or CALIBRATION_ELIGIBLE.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

EXCEPTION_QUEUE = HISTORICAL_DIR / "batch_51_70_exception_queue.csv"
SOURCE_EVIDENCE_DRAFT = HISTORICAL_DIR / "batch_51_70_source_evidence_draft.csv"
FILING_TARGETS = HISTORICAL_DIR / "batch_51_70_pre_announcement_filing_targets.csv"
OUTPUT_REPORT = HISTORICAL_DIR / "batch_51_70_queue_summary.md"

RUN_DATE = date.today().isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def clean(value: str | None) -> str:
    return (value or "").strip()


def int_value(value: str | None) -> int:
    try:
        return int(clean(value))
    except ValueError:
        return 0


def is_possible_hit(row: dict[str, str]) -> bool:
    status = clean(row.get("recommended_status")).upper()
    if status and status not in {"LIKELY_NO_HIT", "NO_HIT", "CLEAN_BASELINE"}:
        return True
    if clean(row.get("possible_signal_type")):
        return True
    if clean(row.get("keyword_hits")):
        return True
    return False


def case_label(row: dict[str, str]) -> str:
    ticker = clean(row.get("ticker"))
    case_id = clean(row.get("case_id"))
    company = clean(row.get("company")) or clean(row.get("company_name"))
    if company:
        return f"{ticker} ({case_id}) - {company}"
    return f"{ticker} ({case_id})"


def markdown_table(rows: list[dict[str, str]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "_None._"

    header = "| " + " | ".join(label for label, _ in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        values = []
        for _, key in columns:
            values.append(clean(row.get(key)).replace("|", "/").replace("—", "-"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def summarize() -> tuple[str, str]:
    queue_rows = read_csv(EXCEPTION_QUEUE)
    draft_rows = read_csv(SOURCE_EVIDENCE_DRAFT)
    target_rows = read_csv(FILING_TARGETS)

    tier_counts = Counter(clean(row.get("priority_tier")) or "MISSING" for row in queue_rows)
    possible_hit_rows = [row for row in target_rows if is_possible_hit(row)]
    total_queue_hits = sum(int_value(row.get("signal_hit_count")) for row in queue_rows)

    possible_hits_by_case: dict[str, int] = defaultdict(int)
    targets_by_case: dict[str, int] = defaultdict(int)
    for row in target_rows:
        case_id = clean(row.get("case_id"))
        if not case_id:
            continue
        targets_by_case[case_id] += 1
        if is_possible_hit(row):
            possible_hits_by_case[case_id] += 1

    p1_p3_rows = sorted([
        row for row in queue_rows
        if clean(row.get("priority_tier")) in {"P1", "P3"}
    ], key=lambda row: (
        {"P1": 1, "P3": 3}.get(clean(row.get("priority_tier")), 99),
        clean(row.get("ticker")),
    ))
    p6_rows = [
        row for row in queue_rows
        if clean(row.get("priority_tier")) == "P6"
    ]
    p6_with_hits = [
        row for row in p6_rows
        if int_value(row.get("signal_hit_count")) > 0 or possible_hits_by_case.get(clean(row.get("case_id")), 0) > 0
    ]
    p6_true_no_hits = [
        row for row in p6_rows
        if int_value(row.get("signal_hit_count")) == 0 and possible_hits_by_case.get(clean(row.get("case_id")), 0) == 0
    ]

    recommended_review = sorted(
        queue_rows,
        key=lambda row: (
            {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "BLOCKED": 5, "P5": 6, "P6": 7}.get(clean(row.get("priority_tier")), 99),
            clean(row.get("ticker")),
        ),
    )

    for row in recommended_review:
        case_id = clean(row.get("case_id"))
        row["filing_target_count"] = str(targets_by_case.get(case_id, 0))
        row["possible_hit_rows"] = str(possible_hits_by_case.get(case_id, 0))

    tier_lines = []
    for tier in sorted(tier_counts, key=lambda value: ({"P1": 1, "P2": 2, "P3": 3, "P4": 4, "BLOCKED": 5, "P5": 6, "P6": 7}.get(value, 99), value)):
        tier_lines.append(f"- {tier}: {tier_counts[tier]}")
    tier_block = "\n".join(tier_lines) if tier_lines else "- None"

    report = f"""# Batch 51-70 Queue Summary

Generated: {RUN_DATE}

Status: read-only workload summary. This script does not adjudicate cases, edit `source_evidence.csv`, or change classifications.

## Summary

- Total cases: {len(queue_rows)}
- Total filing targets: {len(target_rows)}
- Total possible hits from queue: {total_queue_hits}
- Possible-hit filing rows needing context checks: {len(possible_hit_rows)}
- Draft source-evidence rows pending review: {len(draft_rows)}

## Tier Distribution

{tier_block}

## P1/P3 Case List

{markdown_table(p1_p3_rows, [
    ("tier", "priority_tier"),
    ("case_id", "case_id"),
    ("ticker", "ticker"),
    ("company", "company"),
    ("signal_hit_count", "signal_hit_count"),
    ("reason", "priority_reason"),
])}

## P6 Cases With Hits

These are still P6 cases. The hit count indicates low-value or non-adjudicated phrase workload, not a true prior signal.

{markdown_table(p6_with_hits, [
    ("case_id", "case_id"),
    ("ticker", "ticker"),
    ("company", "company"),
    ("signal_phrase_types", "signal_phrase_types"),
    ("signal_hit_count", "signal_hit_count"),
    ("next_action", "next_action"),
])}

## P6 True No-Hit Cases

{markdown_table(p6_true_no_hits, [
    ("case_id", "case_id"),
    ("ticker", "ticker"),
    ("company", "company"),
    ("next_action", "next_action"),
])}

## Recommended Review Order

{markdown_table(recommended_review, [
    ("tier", "priority_tier"),
    ("ticker", "ticker"),
    ("case_id", "case_id"),
    ("filing_targets", "filing_target_count"),
    ("possible_hit_rows", "possible_hit_rows"),
    ("next_action", "next_action"),
])}

## Warning

This summary is a workload view only. It does not classify cases, does not promote draft evidence into `source_evidence.csv`, and does not determine whether any case is `TRUE_PUBLIC_PRIOR_SIGNAL`.
"""

    terminal = "\n".join([
        "Batch 51-70 queue summary",
        f"Total cases: {len(queue_rows)}",
        f"Total filing targets: {len(target_rows)}",
        f"Total possible hits from queue: {total_queue_hits}",
        f"Possible-hit filing rows needing context checks: {len(possible_hit_rows)}",
        "Tier distribution: " + ", ".join(f"{tier}={count}" for tier, count in sorted(tier_counts.items())),
        "P1/P3 cases: " + ", ".join(clean(row.get("ticker")) for row in p1_p3_rows),
        "P6 cases with hits: " + str(len(p6_with_hits)),
        "P6 true no-hit cases: " + str(len(p6_true_no_hits)),
        f"Wrote: {OUTPUT_REPORT}",
    ])
    return report, terminal


def main() -> int:
    report, terminal = summarize()
    OUTPUT_REPORT.write_text(report, encoding="utf-8")
    print(terminal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
