#!/usr/bin/env python3
"""
Read-only evidence/source coverage audit for the historical case factory.

Inputs are read from data/historical_cases. The script writes only:
  - data/historical_cases/evidence_coverage_audit_issues.csv
  - data/historical_cases/evidence_coverage_audit_report.md

It does not change classifications, statuses, packets, batch outputs, or
mini-study files.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

SOURCE_EVIDENCE = HISTORICAL_DIR / "source_evidence.csv"
ANNOUNCEMENT_DATES = HISTORICAL_DIR / "acquisition_announcement_dates.csv"
RESOLVED_CANDIDATES = HISTORICAL_DIR / "resolved_case_candidates.csv"
ACQUISITION_QUEUE = HISTORICAL_DIR / "acquisition_verification_queue.csv"
FILING_TARGETS = HISTORICAL_DIR / "pre_announcement_filing_targets.csv"
SIGNAL_HITS = HISTORICAL_DIR / "pre_announcement_signal_hits.csv"

ISSUES_OUTPUT = HISTORICAL_DIR / "evidence_coverage_audit_issues.csv"
REPORT_OUTPUT = HISTORICAL_DIR / "evidence_coverage_audit_report.md"

RUN_DATE = "2026-05-14"

ISSUE_FIELDS = [
    "priority",
    "priority_rank",
    "check_id",
    "case_id",
    "ticker",
    "source_file",
    "row_number",
    "field_name",
    "issue",
    "cleanup_action",
    "blocks_50_case_study",
    "detail",
]

PRIORITY_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
SEC_FORM_PREFIXES = (
    "8-K",
    "10-K",
    "10-Q",
    "S-1",
    "S-3",
    "S-4",
    "F-1",
    "F-3",
    "F-4",
    "20-F",
    "6-K",
    "SC ",
    "SC_",
    "DEF",
    "DEFM",
    "PREM",
    "PREC",
    "424B",
    "13D",
    "13G",
)
MISSING_URL_TOKENS = {"", "VERIFY_REQUIRED", "TBD", "N/A", "NA", "UNKNOWN"}
NON_SEC_ALLOWED_TYPES = {"PRICE_DATA"}
NON_SEC_ALLOWED_SOURCES = {"YAHOO FINANCE", "YFINANCE", "STOOQ", "BLOOMBERG"}


@dataclass(frozen=True)
class Row:
    number: int
    data: dict[str, str]


def read_csv(path: Path) -> list[Row]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [Row(i, row) for i, row in enumerate(reader, start=2)]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def group_by(rows: Iterable[Row], field: str) -> dict[str, list[Row]]:
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        key = clean(row.data.get(field))
        if key:
            grouped[key].append(row)
    return dict(grouped)


def index_by(rows: Iterable[Row], field: str) -> dict[str, Row]:
    indexed = {}
    for row in rows:
        key = clean(row.data.get(field))
        if key and key not in indexed:
            indexed[key] = row
    return indexed


def clean(value: str | None) -> str:
    return str(value or "").strip()


def upper(value: str | None) -> str:
    return clean(value).upper()


def source_type(row: dict[str, str]) -> str:
    return clean(row.get("source_type")) or clean(row.get("evidence_type")) or "UNKNOWN"


def source_url(row: dict[str, str]) -> str:
    return clean(row.get("source_url"))


def is_missing_url(value: str | None) -> bool:
    return upper(value) in MISSING_URL_TOKENS


def is_valid_http_url(value: str | None) -> bool:
    url = clean(value)
    if is_missing_url(url):
        return False
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_sec_url(value: str | None) -> bool:
    if not is_valid_http_url(value):
        return False
    host = urlparse(clean(value)).netloc.lower()
    return host == "sec.gov" or host.endswith(".sec.gov")


def is_sec_related(row: dict[str, str]) -> bool:
    filing_type = upper(row.get("filing_type"))
    source_name = upper(row.get("source_name"))
    url = upper(row.get("source_url"))
    evidence_type = upper(row.get("evidence_type"))
    if filing_type and filing_type.startswith(SEC_FORM_PREFIXES):
        return True
    if "SEC" in source_name or "EDGAR" in source_name:
        return True
    if "SEC.GOV" in url:
        return True
    return bool(filing_type and evidence_type != "PRICE_DATA")


def is_non_sec_allowed(row: dict[str, str]) -> bool:
    evidence_type = upper(row.get("evidence_type"))
    source_name = upper(row.get("source_name"))
    if evidence_type in NON_SEC_ALLOWED_TYPES:
        return True
    return any(token in source_name for token in NON_SEC_ALLOWED_SOURCES)


def acquired_candidates(rows: list[Row]) -> list[Row]:
    return [
        row
        for row in rows
        if upper(row.data.get("likely_outcome_type")) == "ACQUIRED"
        and clean(row.data.get("candidate_id"))
    ]


def queue_case_id(row: Row) -> str:
    return clean(row.data.get("candidate_id"))


def candidate_case_id(row: Row) -> str:
    return clean(row.data.get("candidate_id"))


def ticker_for(case_id: str, indexes: list[dict[str, Row]]) -> str:
    for indexed in indexes:
        row = indexed.get(case_id)
        if row:
            return clean(row.data.get("ticker"))
    return ""


def selected_first_50(queue_rows: list[Row], candidate_rows: list[Row]) -> list[Row]:
    selected = []
    seen: set[str] = set()
    for row in queue_rows:
        case_id = queue_case_id(row)
        if not case_id or case_id in seen:
            continue
        selected.append(row)
        seen.add(case_id)
        if len(selected) >= 50:
            return selected
    for row in acquired_candidates(candidate_rows):
        case_id = candidate_case_id(row)
        if case_id in seen:
            continue
        selected.append(row)
        seen.add(case_id)
        if len(selected) >= 50:
            return selected
    return selected


def add_issue(
    issues: list[dict[str, str]],
    *,
    priority: str,
    check_id: str,
    case_id: str,
    ticker: str,
    source_file: str,
    row_number: int | str,
    field_name: str,
    issue: str,
    cleanup_action: str,
    first_50_case_ids: set[str],
    detail: str = "",
) -> None:
    priority = priority.upper()
    issues.append(
        {
            "priority": priority,
            "priority_rank": str(PRIORITY_RANK[priority]),
            "check_id": check_id,
            "case_id": case_id,
            "ticker": ticker,
            "source_file": source_file,
            "row_number": str(row_number),
            "field_name": field_name,
            "issue": issue,
            "cleanup_action": cleanup_action,
            "blocks_50_case_study": "TRUE"
            if priority == "HIGH" and case_id in first_50_case_ids
            else "FALSE",
            "detail": detail,
        }
    )


def build_report(
    *,
    evidence_rows: list[Row],
    source_type_counts: Counter[str],
    evidence_by_case_counts: Counter[str],
    first_50_rows: list[Row],
    first_50_case_ids: set[str],
    evidence_by_case: dict[str, list[Row]],
    dates_by_case: dict[str, Row],
    targets_by_case: dict[str, list[Row]],
    hits_by_case: dict[str, list[Row]],
    issues: list[dict[str, str]],
) -> str:
    priority_counts = Counter(issue["priority"] for issue in issues)
    check_counts = Counter(issue["check_id"] for issue in issues)
    high_issues = [issue for issue in issues if issue["priority"] == "HIGH"]
    study_blockers = [issue for issue in issues if issue["blocks_50_case_study"] == "TRUE"]

    first_50_with_evidence = sum(1 for case_id in first_50_case_ids if evidence_by_case.get(case_id))
    first_50_with_dates = sum(1 for case_id in first_50_case_ids if case_id in dates_by_case)
    first_50_with_targets = sum(1 for case_id in first_50_case_ids if targets_by_case.get(case_id))
    first_50_with_hits = sum(1 for case_id in first_50_case_ids if hits_by_case.get(case_id))

    lines = [
        "# Evidence Coverage Audit",
        "",
        f"Run date: {RUN_DATE}",
        "",
        "Read-only audit of historical case source coverage. This report does not change classifications, case packets, batch results, mini-study files, statuses, or scanner/dashboard logic.",
        "",
        "## Summary",
        "",
        f"- Total evidence rows: {len(evidence_rows)}",
        f"- Cases with source evidence: {len(evidence_by_case_counts)}",
        f"- Total coverage gaps found: {len(issues)}",
        f"- High-priority issues: {len(high_issues)}",
        f"- Blocks the 50-case study: {'YES' if study_blockers else 'NO'}",
        "",
        "## Evidence Rows by Source Type",
        "",
        "| Source type | Rows |",
        "|---|---:|",
    ]
    for key, count in source_type_counts.most_common():
        lines.append(f"| {key} | {count} |")

    lines.extend(
        [
            "",
            "## Evidence Rows by Case",
            "",
            "| Case ID | Rows |",
            "|---|---:|",
        ]
    )
    for key, count in evidence_by_case_counts.most_common():
        lines.append(f"| {key} | {count} |")

    lines.extend(
        [
            "",
            "## First 50 Acquisition Cases",
            "",
            f"- Cases reviewed: {len(first_50_rows)}",
            f"- With source evidence: {first_50_with_evidence}",
            f"- With announcement date rows: {first_50_with_dates}",
            f"- With pre-announcement filing targets: {first_50_with_targets}",
            f"- With pre-announcement signal hits: {first_50_with_hits}",
            "",
            "| Case ID | Ticker | Evidence rows | Announcement date row | Filing targets | Signal hits |",
            "|---|---|---:|---|---:|---:|",
        ]
    )
    for row in first_50_rows:
        case_id = queue_case_id(row) or candidate_case_id(row)
        ticker = clean(row.data.get("ticker"))
        lines.append(
            "| "
            + " | ".join(
                [
                    case_id,
                    ticker,
                    str(len(evidence_by_case.get(case_id, []))),
                    "YES" if case_id in dates_by_case else "NO",
                    str(len(targets_by_case.get(case_id, []))),
                    str(len(hits_by_case.get(case_id, []))),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Issue Counts",
            "",
            "| Priority | Count |",
            "|---|---:|",
        ]
    )
    for priority in ("HIGH", "MEDIUM", "LOW"):
        lines.append(f"| {priority} | {priority_counts.get(priority, 0)} |")

    lines.extend(
        [
            "",
            "| Check | Count |",
            "|---|---:|",
        ]
    )
    for key, count in check_counts.most_common():
        lines.append(f"| {key} | {count} |")

    lines.extend(
        [
            "",
            "## Ranked Cleanup List",
            "",
        ]
    )
    for index, issue in enumerate(issues[:50], start=1):
        lines.extend(
            [
                f"{index}. **[{issue['priority']}]** `{issue['check_id']}` - {issue['issue']}",
                f"   - Case: `{issue['case_id'] or 'aggregate'}` ticker `{issue['ticker']}`",
                f"   - File: `{issue['source_file']}` row {issue['row_number']} field `{issue['field_name']}`",
                f"   - Cleanup: {issue['cleanup_action']}",
            ]
        )
        if issue["detail"]:
            lines.append(f"   - Detail: {issue['detail']}")

    if len(issues) > 50:
        lines.append("")
        lines.append(f"Only the top 50 ranked issues are shown here. Full list: `{ISSUES_OUTPUT.relative_to(REPO_ROOT)}`.")

    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- `{ISSUES_OUTPUT.relative_to(REPO_ROOT)}`",
            f"- `{REPORT_OUTPUT.relative_to(REPO_ROOT)}`",
        ]
    )
    return "\n".join(lines) + "\n"


def collect_issues(
    *,
    evidence_rows: list[Row],
    announcement_rows: list[Row],
    candidate_rows: list[Row],
    queue_rows: list[Row],
    target_rows: list[Row],
    hit_rows: list[Row],
    first_50_case_ids: set[str],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    evidence_by_case = group_by(evidence_rows, "case_id")
    dates_by_case = index_by(announcement_rows, "case_id")
    queue_by_case = index_by(queue_rows, "candidate_id")
    candidates_by_case = index_by(candidate_rows, "candidate_id")
    targets_by_case = group_by(target_rows, "case_id")
    hits_by_case = group_by(hit_rows, "case_id")
    candidate_indexes = [candidates_by_case, queue_by_case, dates_by_case]

    for candidate in acquired_candidates(candidate_rows):
        case_id = candidate_case_id(candidate)
        ticker = clean(candidate.data.get("ticker"))
        if case_id not in evidence_by_case:
            add_issue(
                issues,
                priority="HIGH",
                check_id="ACQUIRED_NO_SOURCE_EVIDENCE",
                case_id=case_id,
                ticker=ticker,
                source_file="resolved_case_candidates.csv",
                row_number=candidate.number,
                field_name="candidate_id",
                issue="Acquired candidate has no source_evidence rows.",
                cleanup_action="Add or verify primary source evidence before relying on the case for verification.",
                first_50_case_ids=first_50_case_ids,
            )
        if case_id not in dates_by_case:
            add_issue(
                issues,
                priority="HIGH",
                check_id="ACQUIRED_NO_ANNOUNCEMENT_DATE",
                case_id=case_id,
                ticker=ticker,
                source_file="resolved_case_candidates.csv",
                row_number=candidate.number,
                field_name="candidate_id",
                issue="Acquired candidate has no acquisition announcement date row.",
                cleanup_action="Backfill announcement date with source URL before using the case as a dated baseline.",
                first_50_case_ids=first_50_case_ids,
            )

    for row in announcement_rows:
        case_id = clean(row.data.get("case_id"))
        url = source_url(row.data)
        if case_id and is_missing_url(url):
            add_issue(
                issues,
                priority="HIGH",
                check_id="ANNOUNCEMENT_DATE_NO_SOURCE_URL",
                case_id=case_id,
                ticker=clean(row.data.get("ticker")) or ticker_for(case_id, candidate_indexes),
                source_file="acquisition_announcement_dates.csv",
                row_number=row.number,
                field_name="source_url",
                issue="Announcement date row has no source URL.",
                cleanup_action="Attach the SEC-filed press release, 8-K, tender-offer filing, or equivalent primary URL.",
                first_50_case_ids=first_50_case_ids,
            )

    for case_id, rows in evidence_by_case.items():
        if case_id.startswith("RHC-") and "-ACQUIRED-" in case_id and case_id not in queue_by_case:
            add_issue(
                issues,
                priority="MEDIUM",
                check_id="SOURCE_EVIDENCE_NO_QUEUE_ROW",
                case_id=case_id,
                ticker=ticker_for(case_id, candidate_indexes),
                source_file="source_evidence.csv",
                row_number="aggregate",
                field_name="case_id",
                issue="Source evidence exists for an acquired case with no acquisition verification queue row.",
                cleanup_action="Confirm whether the case should be added to the acquisition queue or documented as out of scope.",
                first_50_case_ids=first_50_case_ids,
                detail=f"{len(rows)} evidence rows",
            )

    for case_id, rows in targets_by_case.items():
        if not hits_by_case.get(case_id):
            add_issue(
                issues,
                priority="MEDIUM",
                check_id="FILING_TARGETS_NO_HITS",
                case_id=case_id,
                ticker=ticker_for(case_id, candidate_indexes) or clean(rows[0].data.get("ticker")),
                source_file="pre_announcement_filing_targets.csv",
                row_number="aggregate",
                field_name="case_id",
                issue="Pre-announcement filing targets exist but no signal hits were recorded.",
                cleanup_action="Run or review the signal-hit collection result before treating prior-signal coverage as complete.",
                first_50_case_ids=first_50_case_ids,
                detail=f"{len(rows)} filing target rows",
            )

    for row in hit_rows:
        case_id = clean(row.data.get("case_id"))
        if is_missing_url(row.data.get("source_url")):
            add_issue(
                issues,
                priority="HIGH",
                check_id="SIGNAL_HIT_NO_SOURCE_URL",
                case_id=case_id,
                ticker=clean(row.data.get("ticker")) or ticker_for(case_id, candidate_indexes),
                source_file="pre_announcement_signal_hits.csv",
                row_number=row.number,
                field_name="source_url",
                issue="Pre-announcement signal hit has no source URL.",
                cleanup_action="Attach the filing URL before using the hit as public prior-signal evidence.",
                first_50_case_ids=first_50_case_ids,
            )

    urls: dict[str, list[Row]] = defaultdict(list)
    for row in evidence_rows:
        url = source_url(row.data)
        if not is_missing_url(url):
            urls[url].append(row)
    for url, rows in urls.items():
        case_ids = sorted({clean(row.data.get("case_id")) for row in rows if clean(row.data.get("case_id"))})
        if len(rows) > 1:
            add_issue(
                issues,
                priority="MEDIUM",
                check_id="DUPLICATE_SOURCE_URL",
                case_id=";".join(case_ids[:5]),
                ticker="",
                source_file="source_evidence.csv",
                row_number="aggregate",
                field_name="source_url",
                issue="Source URL appears on multiple evidence rows across cases.",
                cleanup_action="Confirm whether the duplicate URL is a shared source, copied placeholder, or case-linking error.",
                first_50_case_ids=first_50_case_ids,
                detail=f"{len(rows)} rows across {len(case_ids)} case(s): {url}",
            )

    for row in evidence_rows:
        case_id = clean(row.data.get("case_id"))
        ticker = clean(row.data.get("ticker")) or ticker_for(case_id, candidate_indexes)
        if is_sec_related(row.data) and not clean(row.data.get("accession_number")):
            add_issue(
                issues,
                priority="MEDIUM",
                check_id="SEC_ROW_MISSING_ACCESSION",
                case_id=case_id,
                ticker=ticker,
                source_file="source_evidence.csv",
                row_number=row.number,
                field_name="accession_number",
                issue="SEC-related evidence row is missing accession_number.",
                cleanup_action="Backfill the SEC accession number to make the filing auditable.",
                first_50_case_ids=first_50_case_ids,
            )

        url = source_url(row.data)
        if is_missing_url(url):
            add_issue(
                issues,
                priority="HIGH" if is_sec_related(row.data) else "MEDIUM",
                check_id="SUSPICIOUS_SOURCE_URL_MISSING",
                case_id=case_id,
                ticker=ticker,
                source_file="source_evidence.csv",
                row_number=row.number,
                field_name="source_url",
                issue="Evidence row has a blank or placeholder source_url.",
                cleanup_action="Replace placeholder with a primary source URL or move the row to a research-target workflow.",
                first_50_case_ids=first_50_case_ids,
            )
        elif not is_valid_http_url(url):
            add_issue(
                issues,
                priority="HIGH",
                check_id="SUSPICIOUS_SOURCE_URL_MALFORMED",
                case_id=case_id,
                ticker=ticker,
                source_file="source_evidence.csv",
                row_number=row.number,
                field_name="source_url",
                issue="Evidence row has a malformed source_url.",
                cleanup_action="Correct the URL so the evidence can be opened and verified.",
                first_50_case_ids=first_50_case_ids,
                detail=url,
            )
        elif is_sec_related(row.data) and not is_sec_url(url):
            add_issue(
                issues,
                priority="MEDIUM",
                check_id="SUSPICIOUS_SOURCE_URL_NON_SEC",
                case_id=case_id,
                ticker=ticker,
                source_file="source_evidence.csv",
                row_number=row.number,
                field_name="source_url",
                issue="SEC-related evidence row points to a non-SEC URL.",
                cleanup_action="Confirm whether the row should use an SEC archive URL or be reclassified as non-SEC evidence.",
                first_50_case_ids=first_50_case_ids,
                detail=url,
            )
        elif not is_sec_url(url) and not is_non_sec_allowed(row.data):
            add_issue(
                issues,
                priority="LOW",
                check_id="SUSPICIOUS_SOURCE_URL_NON_SEC",
                case_id=case_id,
                ticker=ticker,
                source_file="source_evidence.csv",
                row_number=row.number,
                field_name="source_url",
                issue="Evidence row points to a non-SEC URL.",
                cleanup_action="Confirm source type and keep only if non-SEC support is intentional.",
                first_50_case_ids=first_50_case_ids,
                detail=url,
            )

    issues.sort(
        key=lambda issue: (
            -int(issue["priority_rank"]),
            issue["check_id"],
            issue["case_id"],
            issue["source_file"],
            int(issue["row_number"]) if re.fullmatch(r"\d+", issue["row_number"]) else 999999,
        )
    )
    return issues


def main() -> None:
    evidence_rows = read_csv(SOURCE_EVIDENCE)
    announcement_rows = read_csv(ANNOUNCEMENT_DATES)
    candidate_rows = read_csv(RESOLVED_CANDIDATES)
    queue_rows = read_csv(ACQUISITION_QUEUE)
    target_rows = read_csv(FILING_TARGETS)
    hit_rows = read_csv(SIGNAL_HITS)

    first_50_rows = selected_first_50(queue_rows, candidate_rows)
    first_50_case_ids = {
        queue_case_id(row) or candidate_case_id(row)
        for row in first_50_rows
        if queue_case_id(row) or candidate_case_id(row)
    }

    evidence_by_case = group_by(evidence_rows, "case_id")
    dates_by_case = index_by(announcement_rows, "case_id")
    targets_by_case = group_by(target_rows, "case_id")
    hits_by_case = group_by(hit_rows, "case_id")

    source_type_counts = Counter(source_type(row.data) for row in evidence_rows)
    evidence_by_case_counts = Counter(
        {case_id: len(rows) for case_id, rows in evidence_by_case.items()}
    )

    issues = collect_issues(
        evidence_rows=evidence_rows,
        announcement_rows=announcement_rows,
        candidate_rows=candidate_rows,
        queue_rows=queue_rows,
        target_rows=target_rows,
        hit_rows=hit_rows,
        first_50_case_ids=first_50_case_ids,
    )

    write_csv(ISSUES_OUTPUT, issues, ISSUE_FIELDS)
    REPORT_OUTPUT.write_text(
        build_report(
            evidence_rows=evidence_rows,
            source_type_counts=source_type_counts,
            evidence_by_case_counts=evidence_by_case_counts,
            first_50_rows=first_50_rows,
            first_50_case_ids=first_50_case_ids,
            evidence_by_case=evidence_by_case,
            dates_by_case=dates_by_case,
            targets_by_case=targets_by_case,
            hits_by_case=hits_by_case,
            issues=issues,
        ),
        encoding="utf-8",
    )

    high_count = sum(1 for issue in issues if issue["priority"] == "HIGH")
    blockers = sum(1 for issue in issues if issue["blocks_50_case_study"] == "TRUE")
    print(f"Wrote {ISSUES_OUTPUT.relative_to(REPO_ROOT)}")
    print(f"Wrote {REPORT_OUTPUT.relative_to(REPO_ROOT)}")
    print(f"Total evidence rows: {len(evidence_rows)}")
    print(f"Coverage gaps found: {len(issues)}")
    print(f"High-priority issues: {high_count}")
    print(f"Blocks 50-case study: {'YES' if blockers else 'NO'}")


if __name__ == "__main__":
    main()
