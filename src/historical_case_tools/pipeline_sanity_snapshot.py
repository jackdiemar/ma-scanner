#!/usr/bin/env python3
"""
Fast read-only sanity snapshot for the historical case factory.

Reads only the core historical-case pipeline CSVs and writes:
  - data/historical_cases/pipeline_sanity_snapshot.csv
  - data/historical_cases/pipeline_sanity_snapshot.md

This script does not change statuses, classifications, packets, batch outputs,
evidence audit outputs, scanner logic, or dashboard logic.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

ACQUISITION_QUEUE = HISTORICAL_DIR / "acquisition_verification_queue.csv"
ANNOUNCEMENT_DATES = HISTORICAL_DIR / "acquisition_announcement_dates.csv"
SOURCE_EVIDENCE = HISTORICAL_DIR / "source_evidence.csv"
FILING_TARGETS = HISTORICAL_DIR / "pre_announcement_filing_targets.csv"
SIGNAL_HITS = HISTORICAL_DIR / "pre_announcement_signal_hits.csv"
RESOLVED_CANDIDATES = HISTORICAL_DIR / "resolved_case_candidates.csv"

SNAPSHOT_CSV = HISTORICAL_DIR / "pipeline_sanity_snapshot.csv"
SNAPSHOT_REPORT = HISTORICAL_DIR / "pipeline_sanity_snapshot.md"

RUN_DATE = "2026-05-14"

CSV_FIELDS = [
    "case_id",
    "ticker",
    "in_acquisition_candidates",
    "in_acquisition_queue",
    "has_announcement_date",
    "announcement_confidence",
    "source_evidence_rows",
    "filing_target_rows",
    "possible_hit_rows",
    "alignment_status",
    "alignment_risks",
    "threatens_50_case_study",
]

RISK_RANK = {
    "hits_without_filing_targets": 5,
    "filing_targets_without_announcement_date": 4,
    "duplicate_case_id_ticker": 4,
    "evidence_without_announcement_date": 3,
    "announcement_date_without_evidence": 2,
}


@dataclass(frozen=True)
class Row:
    number: int
    data: dict[str, str]


def read_csv(path: Path) -> list[Row]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [Row(number, row) for number, row in enumerate(reader, start=2)]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def clean(value: str | None) -> str:
    return str(value or "").strip()


def upper(value: str | None) -> str:
    return clean(value).upper()


def group_by(rows: Iterable[Row], field: str) -> dict[str, list[Row]]:
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        key = clean(row.data.get(field))
        if key:
            grouped[key].append(row)
    return dict(grouped)


def first_by(rows: Iterable[Row], field: str) -> dict[str, Row]:
    indexed = {}
    for row in rows:
        key = clean(row.data.get(field))
        if key and key not in indexed:
            indexed[key] = row
    return indexed


def acquired_candidates(rows: list[Row]) -> list[Row]:
    return [
        row
        for row in rows
        if upper(row.data.get("likely_outcome_type")) == "ACQUIRED"
        and clean(row.data.get("candidate_id"))
    ]


def acquisition_queue_case_id(row: Row) -> str:
    return clean(row.data.get("candidate_id"))


def candidate_case_id(row: Row) -> str:
    return clean(row.data.get("candidate_id"))


def selected_first_50(queue_rows: list[Row], candidate_rows: list[Row]) -> set[str]:
    selected: list[str] = []
    seen: set[str] = set()

    for row in queue_rows:
        case_id = acquisition_queue_case_id(row)
        if not case_id or case_id in seen:
            continue
        selected.append(case_id)
        seen.add(case_id)
        if len(selected) >= 50:
            return set(selected)

    for row in acquired_candidates(candidate_rows):
        case_id = candidate_case_id(row)
        if not case_id or case_id in seen:
            continue
        selected.append(case_id)
        seen.add(case_id)
        if len(selected) >= 50:
            return set(selected)

    return set(selected)


def possible_hit_rows(rows: list[Row]) -> list[Row]:
    hits = []
    for row in rows:
        status = upper(row.data.get("recommended_status"))
        signal = clean(row.data.get("possible_signal_type"))
        keywords = clean(row.data.get("keyword_hits"))
        if status in {"POSSIBLE_HIT", "LIKELY_HIT", "CONFIRMED_HIT"} or signal or keywords:
            hits.append(row)
    return hits


def duplicate_case_ticker_keys(rows: Iterable[Row], case_field: str) -> set[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for row in rows:
        case_id = clean(row.data.get(case_field))
        ticker = upper(row.data.get("ticker"))
        if case_id or ticker:
            counts[(case_id, ticker)] += 1
    return {key for key, count in counts.items() if count > 1}


def status_from_risks(risks: list[str]) -> str:
    if any(risk in risks for risk in ("hits_without_filing_targets", "filing_targets_without_announcement_date", "duplicate_case_id_ticker")):
        return "FAIL"
    if risks:
        return "WARN"
    return "PASS"


def overall_status(case_rows: list[dict[str, str]], duplicate_keys: set[tuple[str, str]]) -> str:
    if duplicate_keys:
        return "FAIL"
    if any(row["alignment_status"] == "FAIL" for row in case_rows):
        return "FAIL"
    if any(row["alignment_status"] == "WARN" for row in case_rows):
        return "WARN"
    return "PASS"


def risk_summary(case_rows: list[dict[str, str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in case_rows:
        for risk in row["alignment_risks"].split("|"):
            if risk:
                counts[risk] += 1
    return counts


def build_case_rows(
    *,
    candidate_rows: list[Row],
    queue_rows: list[Row],
    announcement_by_case: dict[str, Row],
    evidence_by_case: dict[str, list[Row]],
    targets_by_case: dict[str, list[Row]],
    hits_by_case: dict[str, list[Row]],
    first_50_case_ids: set[str],
    duplicate_keys: set[tuple[str, str]],
) -> list[dict[str, str]]:
    candidates_by_case = first_by(acquired_candidates(candidate_rows), "candidate_id")
    queue_by_case = first_by(queue_rows, "candidate_id")
    all_case_ids = sorted(
        set(candidates_by_case)
        | set(queue_by_case)
        | set(announcement_by_case)
        | set(evidence_by_case)
        | set(targets_by_case)
        | set(hits_by_case)
    )

    rows = []
    for case_id in all_case_ids:
        candidate = candidates_by_case.get(case_id)
        queue = queue_by_case.get(case_id)
        announcement = announcement_by_case.get(case_id)
        ticker = ""
        for source in (candidate, queue, announcement):
            if source and clean(source.data.get("ticker")):
                ticker = clean(source.data.get("ticker"))
                break

        risks = []
        has_announcement = announcement is not None
        evidence_count = len(evidence_by_case.get(case_id, []))
        target_count = len(targets_by_case.get(case_id, []))
        hit_count = len(hits_by_case.get(case_id, []))

        if has_announcement and evidence_count == 0:
            risks.append("announcement_date_without_evidence")
        if evidence_count > 0 and not has_announcement and case_id.startswith("RHC-"):
            risks.append("evidence_without_announcement_date")
        if target_count > 0 and not has_announcement:
            risks.append("filing_targets_without_announcement_date")
        if hit_count > 0 and target_count == 0:
            risks.append("hits_without_filing_targets")
        if (case_id, upper(ticker)) in duplicate_keys:
            risks.append("duplicate_case_id_ticker")

        rows.append(
            {
                "case_id": case_id,
                "ticker": ticker,
                "in_acquisition_candidates": "TRUE" if candidate else "FALSE",
                "in_acquisition_queue": "TRUE" if queue else "FALSE",
                "has_announcement_date": "TRUE" if has_announcement else "FALSE",
                "announcement_confidence": upper(announcement.data.get("confidence")) if announcement else "MISSING",
                "source_evidence_rows": str(evidence_count),
                "filing_target_rows": str(target_count),
                "possible_hit_rows": str(hit_count),
                "alignment_status": status_from_risks(risks),
                "alignment_risks": "|".join(sorted(risks, key=lambda risk: (-RISK_RANK.get(risk, 0), risk))),
                "threatens_50_case_study": "TRUE"
                if case_id in first_50_case_ids
                and any(
                    risk in risks
                    for risk in (
                        "hits_without_filing_targets",
                        "filing_targets_without_announcement_date",
                        "duplicate_case_id_ticker",
                    )
                )
                else "FALSE",
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            {"FAIL": 0, "WARN": 1, "PASS": 2}.get(row["alignment_status"], 3),
            row["case_id"],
        ),
    )


def build_report(
    *,
    case_rows: list[dict[str, str]],
    sanity_status: str,
    candidate_count: int,
    announcement_by_case: dict[str, Row],
    evidence_by_case: dict[str, list[Row]],
    targets_by_case: dict[str, list[Row]],
    hits_by_case: dict[str, list[Row]],
    confidence_counts: Counter[str],
    duplicate_keys: set[tuple[str, str]],
) -> str:
    risk_counts = risk_summary(case_rows)
    threats = [row for row in case_rows if row["threatens_50_case_study"] == "TRUE"]
    cases_with_announcement = sum(1 for row in case_rows if row["has_announcement_date"] == "TRUE")
    cases_with_evidence = sum(1 for row in case_rows if int(row["source_evidence_rows"]) > 0)
    cases_with_targets = sum(1 for row in case_rows if int(row["filing_target_rows"]) > 0)
    cases_with_hits = sum(1 for row in case_rows if int(row["possible_hit_rows"]) > 0)

    coherent = not any(
        risk_counts.get(risk, 0)
        for risk in (
            "hits_without_filing_targets",
            "filing_targets_without_announcement_date",
            "duplicate_case_id_ticker",
        )
    )

    lines = [
        "# Pipeline Sanity Snapshot",
        "",
        f"Run date: {RUN_DATE}",
        "",
        "Fast read-only snapshot of whether the historical case factory pieces line up logically. Adjudication files are intentionally not read because Claude is working that queue.",
        "",
        "## Status",
        "",
        f"- Sanity status: **{sanity_status}**",
        f"- Anything appears to threaten the 50-case study: {'YES' if threats else 'NO'}",
        f"- Pipeline order coherent through hits stage: {'YES' if coherent else 'NO'}",
        "",
        "## Core Counts",
        "",
        f"- Acquisition candidates: {candidate_count}",
        f"- Cases with announcement dates: {len(announcement_by_case)}",
        f"- Cases with source evidence: {len(evidence_by_case)}",
        f"- Cases with pre-announcement filing targets: {len(targets_by_case)}",
        f"- Cases with possible pre-announcement hits: {len(hits_by_case)}",
        "",
        "## Announcement Confidence",
        "",
        "| Confidence | Cases |",
        "|---|---:|",
    ]
    for confidence in ("HIGH", "MEDIUM", "MISSING"):
        lines.append(f"| {confidence} | {confidence_counts.get(confidence, 0)} |")
    for confidence, count in sorted(confidence_counts.items()):
        if confidence not in {"HIGH", "MEDIUM", "MISSING"}:
            lines.append(f"| {confidence} | {count} |")

    lines.extend(
        [
            "",
            "## Alignment Risks",
            "",
            "| Risk | Cases |",
            "|---|---:|",
        ]
    )
    if risk_counts:
        for risk, count in risk_counts.most_common():
            lines.append(f"| {risk} | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Pipeline Order",
            "",
            "| Stage | Case count | Note |",
            "|---|---:|---|",
            f"| candidate | {candidate_count} | Acquired rows in resolved_case_candidates.csv |",
            f"| announcement date | {cases_with_announcement} | Cases with date rows |",
            f"| filing targets | {cases_with_targets} | Cases with pre-announcement filing target rows |",
            f"| hits | {cases_with_hits} | Cases with possible signal-hit rows |",
            "| adjudication | not inspected | Protected while Claude adjudicates NEEDS_MANUAL_REVIEW cases |",
            "",
            "## Biggest Alignment Risks",
            "",
        ]
    )

    if risk_counts:
        for risk, count in risk_counts.most_common(5):
            lines.append(f"- {risk}: {count}")
    else:
        lines.append("- None detected.")

    if duplicate_keys:
        lines.extend(["", "## Duplicate Case/Ticker Keys", ""])
        for case_id, ticker in sorted(duplicate_keys):
            lines.append(f"- `{case_id}` / `{ticker}`")

    lines.extend(
        [
            "",
            "## Cases Needing Attention",
            "",
            "| Case ID | Ticker | Status | Risks | Threatens 50-case study |",
            "|---|---|---|---|---|",
        ]
    )
    attention_rows = [row for row in case_rows if row["alignment_status"] != "PASS"]
    for row in attention_rows[:50]:
        lines.append(
            f"| {row['case_id']} | {row['ticker']} | {row['alignment_status']} | {row['alignment_risks']} | {row['threatens_50_case_study']} |"
        )
    if len(attention_rows) > 50:
        lines.append(f"| ... | ... | ... | {len(attention_rows) - 50} additional rows in CSV | ... |")

    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- `{SNAPSHOT_CSV.relative_to(REPO_ROOT)}`",
            f"- `{SNAPSHOT_REPORT.relative_to(REPO_ROOT)}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    queue_rows = read_csv(ACQUISITION_QUEUE)
    announcement_rows = read_csv(ANNOUNCEMENT_DATES)
    evidence_rows = read_csv(SOURCE_EVIDENCE)
    target_rows = read_csv(FILING_TARGETS)
    hit_rows = possible_hit_rows(read_csv(SIGNAL_HITS))
    candidate_rows = read_csv(RESOLVED_CANDIDATES)

    acquired = acquired_candidates(candidate_rows)
    first_50_case_ids = selected_first_50(queue_rows, candidate_rows)

    announcement_by_case = first_by(announcement_rows, "case_id")
    evidence_by_case = group_by(evidence_rows, "case_id")
    targets_by_case = group_by(target_rows, "case_id")
    hits_by_case = group_by(hit_rows, "case_id")

    duplicate_keys = (
        duplicate_case_ticker_keys(acquired, "candidate_id")
        | duplicate_case_ticker_keys(queue_rows, "candidate_id")
        | duplicate_case_ticker_keys(announcement_rows, "case_id")
    )

    case_rows = build_case_rows(
        candidate_rows=candidate_rows,
        queue_rows=queue_rows,
        announcement_by_case=announcement_by_case,
        evidence_by_case=evidence_by_case,
        targets_by_case=targets_by_case,
        hits_by_case=hits_by_case,
        first_50_case_ids=first_50_case_ids,
        duplicate_keys=duplicate_keys,
    )

    candidate_case_ids = {candidate_case_id(row) for row in acquired}
    confidence_counts: Counter[str] = Counter()
    for case_id in candidate_case_ids:
        row = announcement_by_case.get(case_id)
        confidence = upper(row.data.get("confidence")) if row else "MISSING"
        confidence_counts[confidence or "MISSING"] += 1

    sanity_status = overall_status(case_rows, duplicate_keys)
    write_csv(SNAPSHOT_CSV, case_rows, CSV_FIELDS)
    SNAPSHOT_REPORT.write_text(
        build_report(
            case_rows=case_rows,
            sanity_status=sanity_status,
            candidate_count=len(acquired),
            announcement_by_case=announcement_by_case,
            evidence_by_case=evidence_by_case,
            targets_by_case=targets_by_case,
            hits_by_case=hits_by_case,
            confidence_counts=confidence_counts,
            duplicate_keys=duplicate_keys,
        ),
        encoding="utf-8",
    )

    threats = sum(1 for row in case_rows if row["threatens_50_case_study"] == "TRUE")
    risks = risk_summary(case_rows)
    print(f"Wrote {SNAPSHOT_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {SNAPSHOT_REPORT.relative_to(REPO_ROOT)}")
    print(f"Sanity status: {sanity_status}")
    print(f"Biggest alignment risks: {', '.join(risk for risk, _ in risks.most_common(3)) or 'none'}")
    print(f"Threatens 50-case study: {'YES' if threats else 'NO'}")


if __name__ == "__main__":
    main()
