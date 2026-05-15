#!/usr/bin/env python3
"""
Read-only pattern-prep analysis for the acquisition prior-signal study.

This script summarizes emerging prior-signal patterns from existing historical
case artifacts. It writes only:
  - data/historical_cases/prior_signal_pattern_prep.csv
  - data/historical_cases/prior_signal_pattern_prep_report.md

It does not change classifications, case data, packets, batch outputs, scanner
logic, or dashboard logic.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

BATCH_RESULTS = HISTORICAL_DIR / "acquisition_prior_signal_batch_results.csv"
SIGNAL_HITS = HISTORICAL_DIR / "pre_announcement_signal_hits.csv"
FILING_TARGETS = HISTORICAL_DIR / "pre_announcement_filing_targets.csv"
ADJUDICATION_QUEUE = HISTORICAL_DIR / "prior_signal_adjudication_queue.csv"
ANNOUNCEMENT_DATES = HISTORICAL_DIR / "acquisition_announcement_dates.csv"
SOURCE_EVIDENCE = HISTORICAL_DIR / "source_evidence.csv"

OUTPUT_CSV = HISTORICAL_DIR / "prior_signal_pattern_prep.csv"
OUTPUT_REPORT = HISTORICAL_DIR / "prior_signal_pattern_prep_report.md"

RUN_DATE = "2026-05-14"

CSV_FIELDS = [
    "case_id",
    "ticker",
    "company_name",
    "adjudication_status",
    "announcement_date",
    "earliest_possible_signal_date",
    "days_signal_before_announcement",
    "filing_types_in_lookback",
    "possible_signal_keywords",
    "likely_signal_category",
    "likely_edge_value",
    "reason",
]

TRUE_STATUSES = {"TRUE_PUBLIC_PRIOR_SIGNAL"}
BASELINE_STATUSES = {"DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE", "BASELINE"}
FALSE_POSITIVE_STATUSES = {
    "RIGHTS_LANGUAGE_ONLY",
    "ASSET_SPECIFIC_RIGHTS_ONLY",
    "PRIVATE_BACKGROUND_ONLY",
    "FALSE_POSITIVE",
}
POSSIBLE_STATUSES = {"POSSIBLE_SIGNAL_NEEDS_REVIEW", "NEEDS_MANUAL_REVIEW"}


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


def parse_date(value: str | None) -> date | None:
    text = clean(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def join_unique(values: Iterable[str]) -> str:
    seen = []
    for value in values:
        text = clean(value)
        if text and text not in seen:
            seen.append(text)
    return "|".join(seen)


def text_blob(*parts: str | None) -> str:
    return " ".join(clean(part).lower() for part in parts if clean(part))


def is_sec_row(row: dict[str, str]) -> bool:
    url = clean(row.get("source_url")).lower()
    filing_type = upper(row.get("filing_type"))
    return filing_type != "NEWS" and ("sec.gov" in url or filing_type not in {"", "NEWS"})


def category_from_text(status: str, rows: list[Row], evidence_rows: list[Row]) -> str:
    combined = " ".join(
        text_blob(
            row.data.get("possible_signal_type"),
            row.data.get("collector_signal_type"),
            row.data.get("keyword_hits"),
            row.data.get("collector_keyword_hits"),
            row.data.get("adjudicated_signal_type"),
            row.data.get("adjudication_excerpt"),
            row.data.get("excerpt_if_available"),
            row.data.get("notes"),
        )
        for row in rows
    )
    combined += " " + " ".join(
        text_blob(
            row.data.get("evidence_type"),
            row.data.get("filing_type"),
            row.data.get("excerpt"),
            row.data.get("supports_field"),
            row.data.get("notes"),
            row.data.get("source_name"),
        )
        for row in evidence_rows
    )

    if status == "RIGHTS_LANGUAGE_ONLY":
        return "rights_language"
    if status == "ASSET_SPECIFIC_RIGHTS_ONLY":
        return "asset_specific_rights"
    if status == "PRIVATE_BACKGROUND_ONLY":
        return "private_background_only"
    if status in BASELINE_STATUSES:
        return "no_public_prior_signal"
    if "superior proposal" in combined:
        return "superior_proposal"
    if "explore potential sale" in combined or "sale process" in combined or "public_sale_process_report" in combined:
        return "sale_process_media_report"
    if "news" in combined or "bloomberg" in combined or "reuters" in combined or "cnbc" in combined:
        return "sale_process_media_report"
    if "unsolicited proposal" in combined or "proposal to acquire" in combined or "proposal from" in combined:
        return "unsolicited_proposal"
    if "13d" in combined or "activist" in combined or "consent solicitation" in combined:
        return "activist_or_13d_pressure"
    if "right of first refusal" in combined or "rofr" in combined or "right of first negotiation" in combined:
        return "rights_language"
    if "private" in combined or "background" in combined:
        return "private_background_only"
    return "unclear"


def edge_value(status: str, category: str) -> str:
    if status in BASELINE_STATUSES:
        return "NONE"
    if category in {"unsolicited_proposal", "sale_process_media_report", "superior_proposal"}:
        return "HIGH" if status in TRUE_STATUSES or status in POSSIBLE_STATUSES else "MEDIUM"
    if category == "activist_or_13d_pressure":
        return "MEDIUM"
    if category in {"rights_language", "asset_specific_rights"}:
        return "LOW" if status in POSSIBLE_STATUSES else "NONE"
    if category == "private_background_only":
        return "NONE"
    if status in POSSIBLE_STATUSES:
        return "MEDIUM"
    return "LOW" if status in TRUE_STATUSES else "NONE"


def reason_for(status: str, category: str, rows: list[Row], days: str) -> str:
    if status in BASELINE_STATUSES:
        return "No public prior signal currently identified in batch result."
    if status == "TRUE_PUBLIC_PRIOR_SIGNAL":
        timing = f" Earliest signal was {days} days before announcement." if days else ""
        return f"Adjudicated as public prior signal; category inferred as {category}.{timing}"
    if status == "RIGHTS_LANGUAGE_ONLY":
        return "Rights-language hit appears legal or generic rather than whole-company process evidence."
    if status == "ASSET_SPECIFIC_RIGHTS_ONLY":
        return "Rights signal appears limited to an asset or program, not a company-level sale process."
    if status == "PRIVATE_BACKGROUND_ONLY":
        return "Signal appears in transaction-background narrative but was not public before announcement."
    if status in POSSIBLE_STATUSES:
        keywords = join_unique(
            row.data.get("collector_keyword_hits") or row.data.get("keyword_hits") or ""
            for row in rows
        )
        return f"Still needs manual review; current keyword basis: {keywords or 'unclear'}."
    if status == "DATE_MISSING":
        return "Announcement date missing; timing and prior-signal interpretation are incomplete."
    return "Conservative category inferred from available hit/adjudication/source rows."


def rows_before_announcement(rows: list[Row], announcement: date | None) -> list[Row]:
    if not announcement:
        return rows
    filtered = []
    for row in rows:
        filing = parse_date(row.data.get("filing_date"))
        if filing and filing < announcement:
            filtered.append(row)
    return filtered


def earliest_signal_date(rows: list[Row], announcement: date | None) -> date | None:
    dates = []
    for row in rows_before_announcement(rows, announcement):
        filing = parse_date(row.data.get("filing_date"))
        if filing:
            dates.append(filing)
    return min(dates) if dates else None


def build_case_rows(
    batch_rows: list[Row],
    hits_by_case: dict[str, list[Row]],
    targets_by_case: dict[str, list[Row]],
    adjudication_by_case: dict[str, list[Row]],
    evidence_by_case: dict[str, list[Row]],
) -> list[dict[str, str]]:
    case_rows = []
    for row in batch_rows:
        batch = row.data
        case_id = clean(batch.get("case_id"))
        status = upper(batch.get("adjudication_status"))
        announcement_text = clean(batch.get("announcement_date"))
        announcement = parse_date(announcement_text)

        signal_rows = adjudication_by_case.get(case_id, []) or hits_by_case.get(case_id, [])
        target_rows = targets_by_case.get(case_id, [])
        evidence_rows = evidence_by_case.get(case_id, [])
        earliest = earliest_signal_date(signal_rows, announcement)
        days = ""
        if earliest and announcement:
            days = str((announcement - earliest).days)

        lookback_filing_types = join_unique(
            [row.data.get("filing_type", "") for row in target_rows]
            + [row.data.get("filing_type", "") for row in signal_rows]
            + [row.data.get("filing_type", "") for row in evidence_rows]
        )
        keywords = join_unique(
            row.data.get("collector_keyword_hits") or row.data.get("keyword_hits") or row.data.get("possible_signal_type") or row.data.get("collector_signal_type") or ""
            for row in signal_rows
        )
        category = category_from_text(status, signal_rows, evidence_rows)
        edge = edge_value(status, category)
        reason = reason_for(status, category, signal_rows, days)

        case_rows.append(
            {
                "case_id": case_id,
                "ticker": clean(batch.get("ticker")),
                "company_name": clean(batch.get("company_name")),
                "adjudication_status": status,
                "announcement_date": announcement_text,
                "earliest_possible_signal_date": earliest.isoformat() if earliest else "",
                "days_signal_before_announcement": days,
                "filing_types_in_lookback": lookback_filing_types,
                "possible_signal_keywords": keywords,
                "likely_signal_category": category,
                "likely_edge_value": edge,
                "reason": reason,
            }
        )
    return case_rows


def filing_usefulness(
    adjudication_rows: list[Row],
    hit_rows: list[Row],
    target_rows: list[Row],
) -> list[dict[str, str]]:
    stats: dict[str, Counter[str]] = defaultdict(Counter)
    for row in target_rows:
        filing_type = clean(row.data.get("filing_type")) or "UNKNOWN"
        stats[filing_type]["lookback_rows"] += 1
    for row in hit_rows:
        filing_type = clean(row.data.get("filing_type")) or "UNKNOWN"
        stats[filing_type]["possible_hits"] += 1
    for row in adjudication_rows:
        filing_type = clean(row.data.get("filing_type")) or "UNKNOWN"
        classification = upper(row.data.get("adjudication_classification"))
        if classification == "TRUE_PUBLIC_PRIOR_SIGNAL":
            stats[filing_type]["true_rows"] += 1
        elif classification:
            stats[filing_type]["false_or_nontrue_rows"] += 1

    rows = []
    for filing_type, counts in stats.items():
        true_rows = counts["true_rows"]
        possible_hits = counts["possible_hits"]
        lookback_rows = counts["lookback_rows"]
        score = true_rows * 5 + possible_hits - counts["false_or_nontrue_rows"]
        rows.append(
            {
                "filing_type": filing_type,
                "lookback_rows": str(lookback_rows),
                "possible_hits": str(possible_hits),
                "true_rows": str(true_rows),
                "false_or_nontrue_rows": str(counts["false_or_nontrue_rows"]),
                "usefulness_score": str(score),
            }
        )
    return sorted(rows, key=lambda row: (-int(row["usefulness_score"]), row["filing_type"]))


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        output.append("| " + " | ".join(cell.replace("\n", " ") for cell in row) + " |")
    return output


def public_media_cases(case_rows: list[dict[str, str]], evidence_by_case: dict[str, list[Row]], adjudication_by_case: dict[str, list[Row]]) -> list[dict[str, str]]:
    selected = []
    for row in case_rows:
        case_id = row["case_id"]
        evidence_media = any(
            upper(evidence.data.get("evidence_type")) == "PUBLIC_MEDIA_REPORT"
            or upper(evidence.data.get("filing_type")) == "NEWS"
            or any(source in upper(evidence.data.get("source_name")) for source in ("BLOOMBERG", "REUTERS", "CNBC"))
            for evidence in evidence_by_case.get(case_id, [])
        )
        adjudication_media = any(
            upper(adj.data.get("filing_type")) == "NEWS"
            or "public_sale_process_report" in clean(adj.data.get("adjudicated_signal_type")).lower()
            for adj in adjudication_by_case.get(case_id, [])
        )
        if evidence_media or adjudication_media:
            selected.append(row)
    return selected


def sec_signal_cases(case_rows: list[dict[str, str]], adjudication_by_case: dict[str, list[Row]], hits_by_case: dict[str, list[Row]]) -> list[dict[str, str]]:
    selected = []
    for row in case_rows:
        case_id = row["case_id"]
        rows = adjudication_by_case.get(case_id, []) or hits_by_case.get(case_id, [])
        if any(is_sec_row(hit.data) for hit in rows):
            selected.append(row)
    return selected


def build_report(
    case_rows: list[dict[str, str]],
    adjudication_rows: list[Row],
    hit_rows: list[Row],
    target_rows: list[Row],
    evidence_by_case: dict[str, list[Row]],
    adjudication_by_case: dict[str, list[Row]],
    hits_by_case: dict[str, list[Row]],
) -> str:
    status_counts = Counter(row["adjudication_status"] for row in case_rows)
    category_counts = Counter(row["likely_signal_category"] for row in case_rows)
    true_rows = [row for row in case_rows if row["adjudication_status"] in TRUE_STATUSES]
    false_rows = [row for row in case_rows if row["adjudication_status"] in FALSE_POSITIVE_STATUSES]
    possible_rows = [row for row in case_rows if row["adjudication_status"] in POSSIBLE_STATUSES]
    timing_rows = [row for row in case_rows if row["earliest_possible_signal_date"]]
    media_rows = public_media_cases(case_rows, evidence_by_case, adjudication_by_case)
    sec_rows = sec_signal_cases(case_rows, adjudication_by_case, hits_by_case)
    usefulness = filing_usefulness(adjudication_rows, hit_rows, target_rows)

    high_edge_possible = [
        row for row in possible_rows if row["likely_edge_value"] in {"HIGH", "MEDIUM"}
    ]

    lines = [
        "# Prior Signal Pattern Prep",
        "",
        f"Run date: {RUN_DATE}",
        "",
        "Read-only analysis prep for the 50-case acquisition prior-signal study. This does not change classifications, case data, packets, scanner logic, or dashboard logic.",
        "",
        "## Executive Summary",
        "",
        f"- Current distribution: {', '.join(f'{status}={count}' for status, count in status_counts.most_common())}.",
        f"- True public prior signals currently cluster around explicit public acquisition pressure: unsolicited proposals, competing/superior proposals, and public sale-process media reports.",
        f"- The clearest false-positive families are generic rights language, asset-specific rights, and private transaction-background narratives.",
        f"- Cases still most likely to change the study conclusion: {', '.join(row['ticker'] for row in high_edge_possible) or 'none currently flagged as medium/high edge from available rows'}.",
        "- Treat all findings as prep for human/Claude review, not final adjudication.",
        "",
        "## Current 50-Case Distribution by Status",
        "",
    ]
    lines.extend(table(["Status", "Cases"], [[status, str(count)] for status, count in status_counts.most_common()]))

    lines.extend(["", "## True-Signal Pattern Table", ""])
    true_table_rows = [
        [
            row["ticker"],
            row["likely_signal_category"],
            row["earliest_possible_signal_date"] or "",
            row["days_signal_before_announcement"] or "",
            row["filing_types_in_lookback"],
            row["reason"],
        ]
        for row in true_rows
    ]
    lines.extend(table(["Ticker", "Category", "Earliest signal", "Days before", "Filing types", "Reason"], true_table_rows or [["None", "", "", "", "", ""]]))

    lines.extend(["", "## False-Positive Pattern Table", ""])
    false_table_rows = [
        [row["ticker"], row["adjudication_status"], row["likely_signal_category"], row["possible_signal_keywords"], row["reason"]]
        for row in false_rows
    ]
    lines.extend(table(["Ticker", "Status", "Category", "Keywords", "Reason"], false_table_rows or [["None", "", "", "", ""]]))

    lines.extend(["", "## Possible-Signal Review Priority Table", ""])
    possible_sorted = sorted(possible_rows, key=lambda row: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 3}.get(row["likely_edge_value"], 4), row["ticker"]))
    lines.extend(
        table(
            ["Ticker", "Category", "Edge value", "Earliest signal", "Days before", "Why review"],
            [
                [
                    row["ticker"],
                    row["likely_signal_category"],
                    row["likely_edge_value"],
                    row["earliest_possible_signal_date"],
                    row["days_signal_before_announcement"],
                    row["reason"],
                ]
                for row in possible_sorted
            ]
            or [["None", "", "", "", "", ""]],
        )
    )

    lines.extend(["", "## Signal Timing Table", ""])
    timing_sorted = sorted(timing_rows, key=lambda row: int(row["days_signal_before_announcement"] or "999999"), reverse=True)
    lines.extend(
        table(
            ["Ticker", "Status", "Category", "Signal date", "Announcement", "Days before"],
            [
                [
                    row["ticker"],
                    row["adjudication_status"],
                    row["likely_signal_category"],
                    row["earliest_possible_signal_date"],
                    row["announcement_date"],
                    row["days_signal_before_announcement"],
                ]
                for row in timing_sorted
            ]
            or [["None", "", "", "", "", ""]],
        )
    )

    lines.extend(["", "## Filing / Source Type Usefulness Ranking", ""])
    lines.extend(
        table(
            ["Filing type", "Lookback rows", "Possible hits", "True rows", "Non-true rows", "Score"],
            [
                [
                    row["filing_type"],
                    row["lookback_rows"],
                    row["possible_hits"],
                    row["true_rows"],
                    row["false_or_nontrue_rows"],
                    row["usefulness_score"],
                ]
                for row in usefulness
            ],
        )
    )

    lines.extend(["", "## Public Media Reports Before Announcement", ""])
    lines.extend(
        table(
            ["Ticker", "Status", "Category", "Reason"],
            [[row["ticker"], row["adjudication_status"], row["likely_signal_category"], row["reason"]] for row in media_rows]
            or [["None identified", "", "", ""]],
        )
    )

    lines.extend(["", "## SEC-Filed Signals Before Announcement", ""])
    lines.extend(
        table(
            ["Ticker", "Status", "Category", "Earliest signal", "Filing types"],
            [
                [
                    row["ticker"],
                    row["adjudication_status"],
                    row["likely_signal_category"],
                    row["earliest_possible_signal_date"],
                    row["filing_types_in_lookback"],
                ]
                for row in sec_rows
            ]
            or [["None identified", "", "", "", ""]],
        )
    )

    lines.extend(
        [
            "",
            "## Early Live-Scanner Rule Recommendations",
            "",
            "1. Elevate explicit public unsolicited proposal language when it appears before a signed merger announcement, especially in 8-Ks, 10-Qs, and public communications filed with SEC.",
            "2. Treat superior-proposal language as high-value only when the filing date precedes the final acquisition announcement and source text confirms public availability.",
            "3. Separate generic rights language from company-level transaction rights. Generic legal representations should not count as prior process evidence.",
            "4. Separate asset-specific rights from whole-company acquisition rights. Asset or subsidiary rights should not clear the company-level process gate.",
            "5. Do not count private background-only negotiations as public prior signals unless the pre-announcement source itself was public.",
            "6. Keep media reports in a distinct category from SEC filings. Public sale-process reports can matter, but source availability and date must be verified.",
            "7. Require Item 4 / exact-source context before treating activist or 13D pressure as sale-process evidence.",
            "",
            "## Five Most Important Open Research Questions",
            "",
            "1. Among the six possible-signal cases, how many are genuinely public before announcement versus private background-only?",
            "2. Do media-reported sale processes produce materially different timing and reliability than SEC-filed acquisition proposals?",
            "3. Are rights-language false positives mostly generic legal representations, or are any company-level ROFR/ROFN rights being missed?",
            "4. Which filing types create the best precision: 8-K, 10-Q, Schedule 14D-9, proxy/tender filings, or news reports?",
            "5. Does signal age matter enough to create freshness thresholds for the live scanner?",
            "",
            "## Suggested Prompt for Claude After the 6-Case Adjudication Finishes",
            "",
            "```text",
            "Using the finalized 50-case acquisition prior-signal batch, review prior_signal_pattern_prep_report.md and prior_signal_pattern_prep.csv. Confirm which pattern claims are still valid after the six POSSIBLE_SIGNAL_NEEDS_REVIEW cases were adjudicated. Update the interpretation of true public prior signals versus false positives, identify any live-scanner rule changes that are now evidence-backed, and separate findings that are statistically suggestive from findings that are only anecdotal. Do not mark any cases VERIFIED or CALIBRATION_ELIGIBLE.",
            "```",
            "",
            "## Outputs",
            "",
            f"- `{OUTPUT_CSV.relative_to(REPO_ROOT)}`",
            f"- `{OUTPUT_REPORT.relative_to(REPO_ROOT)}`",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    batch_rows = read_csv(BATCH_RESULTS)
    hit_rows = read_csv(SIGNAL_HITS)
    target_rows = read_csv(FILING_TARGETS)
    adjudication_rows = read_csv(ADJUDICATION_QUEUE)
    read_csv(ANNOUNCEMENT_DATES)
    evidence_rows = read_csv(SOURCE_EVIDENCE)

    active_batch = batch_rows[:50]
    hits_by_case = group_by(hit_rows, "case_id")
    targets_by_case = group_by(target_rows, "case_id")
    adjudication_by_case = group_by(adjudication_rows, "case_id")
    evidence_by_case = group_by(evidence_rows, "case_id")

    case_rows = build_case_rows(
        active_batch,
        hits_by_case,
        targets_by_case,
        adjudication_by_case,
        evidence_by_case,
    )
    write_csv(OUTPUT_CSV, case_rows, CSV_FIELDS)
    OUTPUT_REPORT.write_text(
        build_report(
            case_rows,
            adjudication_rows,
            hit_rows,
            target_rows,
            evidence_by_case,
            adjudication_by_case,
            hits_by_case,
        ),
        encoding="utf-8",
    )

    status_counts = Counter(row["adjudication_status"] for row in case_rows)
    possible = [row["ticker"] for row in case_rows if row["adjudication_status"] in POSSIBLE_STATUSES]
    true_categories = Counter(
        row["likely_signal_category"]
        for row in case_rows
        if row["adjudication_status"] in TRUE_STATUSES
    )
    print(f"Wrote {OUTPUT_CSV.relative_to(REPO_ROOT)}")
    print(f"Wrote {OUTPUT_REPORT.relative_to(REPO_ROOT)}")
    print("Status distribution: " + ", ".join(f"{k}={v}" for k, v in status_counts.most_common()))
    print("Possible-signal review cases: " + (", ".join(possible) or "none"))
    print("True-signal categories: " + (", ".join(f"{k}={v}" for k, v in true_categories.most_common()) or "none"))


if __name__ == "__main__":
    main()
