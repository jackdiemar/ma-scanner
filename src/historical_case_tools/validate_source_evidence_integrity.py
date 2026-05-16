#!/usr/bin/env python3
"""
Read-only source evidence integrity validator for the historical case factory.

Inputs:
  - data/historical_cases/source_evidence.csv
  - data/historical_cases/acquisition_announcement_dates.csv
  - data/historical_cases/resolved_case_candidates.csv

Writes only:
  - data/historical_cases/source_evidence_integrity_report.md

The script does not mutate CSVs, run the scanner, run package workflows, or mark
cases VERIFIED / CALIBRATION_ELIGIBLE.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from case_factory_schema import (
    detect_column,
    normalize_ticker as schema_normalize_ticker,
    parse_iso_date,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

SOURCE_EVIDENCE = HISTORICAL_DIR / "source_evidence.csv"
ANNOUNCEMENT_DATES = HISTORICAL_DIR / "acquisition_announcement_dates.csv"
RESOLVED_CANDIDATES = HISTORICAL_DIR / "resolved_case_candidates.csv"
REPORT_OUTPUT = HISTORICAL_DIR / "source_evidence_integrity_report.md"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)

DATE_FIELD_HINTS = (
    "date",
    "filing_date",
    "event_date",
    "announcement_date",
    "acquisition_announcement_date",
    "added_date",
)
CASE_FIELDS = ("case_id", "candidate_id", "target_case_id")
TICKER_FIELDS = ("ticker", "target_ticker", "company_ticker")
SOURCE_URL_FIELDS = ("source_url", "source_filing_url", "url", "outcome_source_url")
SOURCE_REF_FIELDS = ("source_url", "source_reference", "source_name", "source_evidence_type", "notes")
CONFIDENCE_FIELDS = ("confidence", "date_confidence", "source_confidence")
EVIDENCE_TYPE_FIELDS = ("evidence_type", "source_evidence_type", "source_type")
ANNOUNCEMENT_DATE_FIELDS = ("acquisition_announcement_date", "announcement_date", "event_date", "deal_date")

MISSING_URL_TOKENS = {"", "VERIFY_REQUIRED", "PLACEHOLDER_PENDING_REVIEW", "TBD", "N/A", "NA", "UNKNOWN"}
HIGH = "HIGH"
MEDIUM = "MEDIUM"


@dataclass(frozen=True)
class Row:
    number: int
    data: dict[str, str]


@dataclass(frozen=True)
class CsvData:
    path: Path
    rows: list[Row]
    fieldnames: list[str]
    parse_error: str = ""


@dataclass(frozen=True)
class Issue:
    severity: str
    check_id: str
    file_name: str
    row_number: int | str
    case_id: str
    ticker: str
    detail: str


def clean(value: object) -> str:
    return str(value or "").strip()


def upper(value: object) -> str:
    return clean(value).upper()


def read_csv_data(path: Path) -> CsvData:
    if not path.exists():
        return CsvData(path=path, rows=[], fieldnames=[], parse_error="file_missing")
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = [Row(number=i, data=row) for i, row in enumerate(reader, start=2)]
            return CsvData(path=path, rows=rows, fieldnames=list(reader.fieldnames or []))
    except Exception as exc:
        return CsvData(path=path, rows=[], fieldnames=[], parse_error=str(exc))


def first_field(fieldnames: Iterable[str], candidates: tuple[str, ...]) -> str:
    return detect_column({field: "" for field in fieldnames}, list(candidates)) or ""


def fields_with_hint(fieldnames: Iterable[str], hints: tuple[str, ...]) -> list[str]:
    result = []
    for field in fieldnames:
        lower = field.lower()
        if any(hint in lower for hint in hints):
            result.append(field)
    return result


def value(row: Row, fields: tuple[str, ...], fieldnames: Iterable[str]) -> str:
    field = first_field(fieldnames, fields)
    if not field:
        return ""
    return clean(row.data.get(field))


def case_id(row: Row, fieldnames: Iterable[str]) -> str:
    return value(row, CASE_FIELDS, fieldnames)


def ticker(row: Row, fieldnames: Iterable[str]) -> str:
    return schema_normalize_ticker(value(row, TICKER_FIELDS, fieldnames))


def source_url(row: Row, fieldnames: Iterable[str]) -> str:
    return value(row, SOURCE_URL_FIELDS, fieldnames)


def confidence(row: Row, fieldnames: Iterable[str]) -> str:
    return upper(value(row, CONFIDENCE_FIELDS, fieldnames))


def evidence_type(row: Row, fieldnames: Iterable[str]) -> str:
    return upper(value(row, EVIDENCE_TYPE_FIELDS, fieldnames))


def announcement_date(row: Row, fieldnames: Iterable[str]) -> str:
    return value(row, ANNOUNCEMENT_DATE_FIELDS, fieldnames)


def row_has_source_reference(row: Row, fieldnames: Iterable[str]) -> bool:
    for field_name in SOURCE_REF_FIELDS:
        field = first_field(fieldnames, (field_name,))
        if field and clean(row.data.get(field)) and upper(row.data.get(field)) not in MISSING_URL_TOKENS:
            return True
    return False


def valid_url(url: str) -> bool:
    return bool(url and upper(url) not in MISSING_URL_TOKENS and URL_RE.match(url))


def valid_date(value_: str) -> bool:
    if not value_:
        return True
    return bool(DATE_RE.match(value_) and parse_iso_date(value_))


def date_year(value_: str) -> int | None:
    if not valid_date(value_) or not value_:
        return None
    return int(value_[:4])


def issue(
    severity: str,
    check_id: str,
    csv_data: CsvData,
    row: Row | None,
    detail: str,
    case_value: str = "",
    ticker_value: str = "",
) -> Issue:
    return Issue(
        severity=severity,
        check_id=check_id,
        file_name=csv_data.path.name,
        row_number=row.number if row else "-",
        case_id=case_value or (case_id(row, csv_data.fieldnames) if row else ""),
        ticker=ticker_value or (ticker(row, csv_data.fieldnames) if row else ""),
        detail=detail,
    )


def is_announcement_evidence(row: Row, fieldnames: Iterable[str]) -> bool:
    supports_field = upper(row.data.get(first_field(fieldnames, ("supports_field",))))
    ev_type = evidence_type(row, fieldnames)
    notes = upper(row.data.get(first_field(fieldnames, ("notes",))))
    return any(
        token in f"{supports_field} {ev_type} {notes}"
        for token in (
            "ACQUISITION_ANNOUNCEMENT_DATE",
            "ANNOUNCEMENT_DATE",
            "DEAL_DATE",
            "8K_MERGER",
            "MERGER",
            "TENDER",
        )
    )


def evidence_date(row: Row, fieldnames: Iterable[str]) -> str:
    for field_name in ("acquisition_announcement_date", "announcement_date", "event_date", "deal_date", "filing_date"):
        field = first_field(fieldnames, (field_name,))
        if field and clean(row.data.get(field)):
            return clean(row.data.get(field))
    return ""


def explicit_announcement_evidence_date(row: Row, fieldnames: Iterable[str]) -> str:
    for field_name in ("acquisition_announcement_date", "announcement_date", "event_date", "deal_date"):
        field = first_field(fieldnames, (field_name,))
        if field and clean(row.data.get(field)):
            return clean(row.data.get(field))
    return ""


def filtered_rows(csv_data: CsvData, case_prefix: str, ticker_filter: str) -> list[Row]:
    rows = csv_data.rows
    if case_prefix:
        rows = [row for row in rows if case_id(row, csv_data.fieldnames).startswith(case_prefix)]
    if ticker_filter:
        rows = [row for row in rows if ticker(row, csv_data.fieldnames) == ticker_filter.upper()]
    return rows


def candidate_year_index(candidates: CsvData) -> dict[tuple[str, str], int]:
    year_field = first_field(candidates.fieldnames, ("likely_outcome_year", "outcome_year", "announcement_year"))
    result: dict[tuple[str, str], int] = {}
    if not year_field:
        return result
    for row in candidates.rows:
        year_value = clean(row.data.get(year_field))
        if not year_value.isdigit():
            continue
        year = int(year_value)
        c_id = case_id(row, candidates.fieldnames)
        tick = ticker(row, candidates.fieldnames)
        if c_id:
            result[(c_id, "")] = year
        if tick:
            result[("", tick)] = year
        if c_id and tick:
            result[(c_id, tick)] = year
    return result


def lookup_candidate_year(index: dict[tuple[str, str], int], c_id: str, tick: str) -> int | None:
    return index.get((c_id, tick)) or index.get((c_id, "")) or index.get(("", tick))


def validate_required_files(source: CsvData, dates: CsvData, candidates: CsvData) -> list[Issue]:
    issues: list[Issue] = []
    for csv_data in (source, dates, candidates):
        if csv_data.parse_error:
            issues.append(issue("FAIL", "csv_parse", csv_data, None, csv_data.parse_error))
    for csv_data, required_any in (
        (source, (CASE_FIELDS, TICKER_FIELDS, SOURCE_URL_FIELDS, CONFIDENCE_FIELDS)),
        (dates, (TICKER_FIELDS, ANNOUNCEMENT_DATE_FIELDS, CONFIDENCE_FIELDS)),
    ):
        for field_group in required_any:
            if not first_field(csv_data.fieldnames, field_group):
                issues.append(
                    issue(
                        "FAIL",
                        "missing_required_column",
                        csv_data,
                        None,
                        f"Missing one of: {', '.join(field_group)}",
                    )
                )
    return issues


def validate_dates(csv_data: CsvData, rows: list[Row]) -> list[Issue]:
    issues: list[Issue] = []
    date_fields = fields_with_hint(csv_data.fieldnames, DATE_FIELD_HINTS)
    for row in rows:
        for field in date_fields:
            raw = clean(row.data.get(field))
            if raw and not valid_date(raw):
                issues.append(issue("FAIL", "malformed_date", csv_data, row, f"{field}={raw}"))
    return issues


def validate_source_rows(source: CsvData, rows: list[Row], strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    for row in rows:
        if confidence(row, source.fieldnames) == MEDIUM:
            issues.append(issue("WARN", "medium_confidence_source_evidence", source, row, "MEDIUM confidence row"))
        url = source_url(row, source.fieldnames)
        if url and not valid_url(url):
            issues.append(issue("WARN", "missing_or_placeholder_source_url", source, row, f"source_url={url}"))
        if is_announcement_evidence(row, source.fieldnames):
            if not case_id(row, source.fieldnames) and not ticker(row, source.fieldnames):
                issues.append(issue("FAIL", "announcement_evidence_missing_case_or_ticker", source, row, "case_id or ticker required"))
            if not evidence_date(row, source.fieldnames):
                issues.append(issue("FAIL", "announcement_evidence_missing_date", source, row, "announcement/event/filing date required"))
            if first_field(source.fieldnames, SOURCE_URL_FIELDS) and not valid_url(url):
                severity = "FAIL" if strict else "WARN"
                issues.append(issue(severity, "announcement_evidence_missing_source_url", source, row, "source_url missing or placeholder"))
            if first_field(source.fieldnames, CONFIDENCE_FIELDS) and not confidence(row, source.fieldnames):
                severity = "FAIL" if strict else "WARN"
                issues.append(issue(severity, "announcement_evidence_missing_confidence", source, row, "confidence missing"))
    return issues


def validate_date_rows(dates: CsvData, rows: list[Row], strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    case_field_exists = bool(first_field(dates.fieldnames, CASE_FIELDS))
    for row in rows:
        if not ticker(row, dates.fieldnames):
            issues.append(issue("FAIL", "date_row_missing_ticker", dates, row, "ticker required"))
        if case_field_exists and not case_id(row, dates.fieldnames):
            issues.append(issue("WARN", "date_row_missing_case_id", dates, row, "case_id missing"))
        if not announcement_date(row, dates.fieldnames):
            issues.append(issue("FAIL", "date_row_missing_announcement_date", dates, row, "announcement date required"))
        if not row_has_source_reference(row, dates.fieldnames):
            severity = "FAIL" if strict else "WARN"
            issues.append(issue(severity, "date_row_missing_source_reference", dates, row, "source URL or source reference required"))
        if first_field(dates.fieldnames, SOURCE_URL_FIELDS):
            url = source_url(row, dates.fieldnames)
            if url and not valid_url(url):
                issues.append(issue("WARN", "date_row_missing_or_placeholder_source_url", dates, row, f"source_url={url}"))
        if first_field(dates.fieldnames, CONFIDENCE_FIELDS) and not confidence(row, dates.fieldnames):
            issues.append(issue("FAIL", "date_row_missing_confidence", dates, row, "confidence required"))
        if confidence(row, dates.fieldnames) == MEDIUM:
            issues.append(issue("WARN", "medium_confidence_acquisition_date", dates, row, "MEDIUM confidence row"))
    return issues


def validate_duplicate_evidence(source: CsvData, rows: list[Row]) -> list[Issue]:
    issues: list[Issue] = []
    keyed: defaultdict[tuple[str, str, str, str, str], list[Row]] = defaultdict(list)
    for row in rows:
        key = (
            case_id(row, source.fieldnames),
            ticker(row, source.fieldnames),
            source_url(row, source.fieldnames),
            evidence_date(row, source.fieldnames),
            evidence_type(row, source.fieldnames),
        )
        if any(key):
            keyed[key].append(row)
    for key, duplicates in keyed.items():
        if len(duplicates) <= 1:
            continue
        row_numbers = ", ".join(str(row.number) for row in duplicates)
        first = duplicates[0]
        issues.append(
            issue(
                "FAIL",
                "duplicate_exact_source_evidence",
                source,
                first,
                f"Rows {row_numbers} share case_id/ticker/source_url/date/evidence_type",
            )
        )
    return issues


def validate_duplicate_dates(dates: CsvData, rows: list[Row]) -> list[Issue]:
    issues: list[Issue] = []
    dates_by_ticker: defaultdict[str, set[str]] = defaultdict(set)
    rows_by_ticker: defaultdict[str, list[Row]] = defaultdict(list)
    high_dates_by_key: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    high_rows_by_key: defaultdict[tuple[str, str], list[Row]] = defaultdict(list)

    for row in rows:
        tick = ticker(row, dates.fieldnames)
        c_id = case_id(row, dates.fieldnames)
        ann_date = announcement_date(row, dates.fieldnames)
        if tick and ann_date:
            dates_by_ticker[tick].add(ann_date)
            rows_by_ticker[tick].append(row)
        if confidence(row, dates.fieldnames) == HIGH and ann_date:
            key = (c_id, tick)
            high_dates_by_key[key].add(ann_date)
            high_rows_by_key[key].append(row)

    for tick, date_values in dates_by_ticker.items():
        if len(date_values) > 1:
            row_numbers = ", ".join(str(row.number) for row in rows_by_ticker[tick])
            issues.append(
                issue(
                    "WARN",
                    "duplicate_ticker_different_dates",
                    dates,
                    rows_by_ticker[tick][0],
                    f"Ticker {tick} has dates {', '.join(sorted(date_values))}; rows {row_numbers}",
                    ticker_value=tick,
                )
            )
    for key, date_values in high_dates_by_key.items():
        if len(date_values) > 1:
            rows_for_key = high_rows_by_key[key]
            issues.append(
                issue(
                    "FAIL",
                    "conflicting_high_confidence_dates",
                    dates,
                    rows_for_key[0],
                    f"HIGH confidence dates conflict: {', '.join(sorted(date_values))}",
                    case_value=key[0],
                    ticker_value=key[1],
                )
            )
    return issues


def build_source_indexes(source: CsvData, rows: list[Row]) -> tuple[dict[str, list[Row]], dict[str, list[Row]]]:
    by_case: defaultdict[str, list[Row]] = defaultdict(list)
    by_ticker: defaultdict[str, list[Row]] = defaultdict(list)
    for row in rows:
        c_id = case_id(row, source.fieldnames)
        tick = ticker(row, source.fieldnames)
        if c_id:
            by_case[c_id].append(row)
        if tick:
            by_ticker[tick].append(row)
    return dict(by_case), dict(by_ticker)


def validate_cross_checks(source: CsvData, dates: CsvData, source_rows: list[Row], date_rows: list[Row], strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    source_by_case, source_by_ticker = build_source_indexes(source, source_rows)

    date_by_case: defaultdict[str, list[Row]] = defaultdict(list)
    date_by_ticker: defaultdict[str, list[Row]] = defaultdict(list)
    for row in date_rows:
        c_id = case_id(row, dates.fieldnames)
        tick = ticker(row, dates.fieldnames)
        if c_id:
            date_by_case[c_id].append(row)
        if tick:
            date_by_ticker[tick].append(row)

    for row in date_rows:
        c_id = case_id(row, dates.fieldnames)
        tick = ticker(row, dates.fieldnames)
        ann_date = announcement_date(row, dates.fieldnames)
        related_source = source_by_case.get(c_id, []) + source_by_ticker.get(tick, [])
        has_source_url_or_row = bool(related_source) or valid_url(source_url(row, dates.fieldnames))
        if confidence(row, dates.fieldnames) == HIGH and not has_source_url_or_row:
            severity = "FAIL" if strict else "WARN"
            issues.append(
                issue(
                    severity,
                    "high_confidence_date_missing_related_source",
                    dates,
                    row,
                    "HIGH confidence date has no related source_evidence row or source_url",
                )
            )
        source_announcement_dates = {
            explicit_announcement_evidence_date(source_row, source.fieldnames)
            for source_row in related_source
            if is_announcement_evidence(source_row, source.fieldnames)
            and explicit_announcement_evidence_date(source_row, source.fieldnames)
        }
        conflicts = sorted(date_value for date_value in source_announcement_dates if ann_date and date_value != ann_date)
        if conflicts and confidence(row, dates.fieldnames) == HIGH:
            issues.append(
                issue(
                    "FAIL",
                    "source_evidence_date_conflicts_with_high_date",
                    dates,
                    row,
                    f"Date table={ann_date}; source evidence={', '.join(conflicts)}",
                )
            )

    for row in source_rows:
        if not is_announcement_evidence(row, source.fieldnames):
            continue
        c_id = case_id(row, source.fieldnames)
        tick = ticker(row, source.fieldnames)
        src_date = explicit_announcement_evidence_date(row, source.fieldnames)
        if not src_date:
            continue
        related_dates = date_by_case.get(c_id, []) + date_by_ticker.get(tick, [])
        date_values = {
            announcement_date(date_row, dates.fieldnames)
            for date_row in related_dates
            if announcement_date(date_row, dates.fieldnames)
        }
        conflicts = sorted(date_value for date_value in date_values if src_date and date_value != src_date)
        if conflicts:
            issues.append(
                issue(
                    "WARN",
                    "announcement_source_date_differs_from_date_table",
                    source,
                    row,
                    f"source evidence date={src_date}; date table={', '.join(conflicts)}",
                )
            )
    return issues


def validate_candidate_years(dates: CsvData, date_rows: list[Row], year_index: dict[tuple[str, str], int]) -> list[Issue]:
    issues: list[Issue] = []
    for row in date_rows:
        c_id = case_id(row, dates.fieldnames)
        tick = ticker(row, dates.fieldnames)
        ann_date = announcement_date(row, dates.fieldnames)
        ann_year = date_year(ann_date)
        expected_year = lookup_candidate_year(year_index, c_id, tick)
        if ann_year is None or expected_year is None:
            continue
        if abs(ann_year - expected_year) > 1:
            issues.append(
                issue(
                    "WARN",
                    "date_outside_plausible_acquisition_year",
                    dates,
                    row,
                    f"announcement year {ann_year} differs from likely_outcome_year {expected_year}",
                )
            )
    return issues


def apply_strict(issues: list[Issue], strict: bool) -> list[Issue]:
    if not strict:
        return issues
    promoted = {
        "missing_or_placeholder_source_url",
        "date_row_missing_case_id",
        "medium_confidence_source_evidence",
        "medium_confidence_acquisition_date",
    }
    result = []
    for item in issues:
        if item.severity == "WARN" and item.check_id in promoted:
            result.append(
                Issue(
                    severity="FAIL",
                    check_id=item.check_id,
                    file_name=item.file_name,
                    row_number=item.row_number,
                    case_id=item.case_id,
                    ticker=item.ticker,
                    detail=f"[strict] {item.detail}",
                )
            )
        else:
            result.append(item)
    return result


def issue_counts(issues: list[Issue]) -> tuple[int, int]:
    warnings = sum(1 for item in issues if item.severity == "WARN")
    failures = sum(1 for item in issues if item.severity == "FAIL")
    return warnings, failures


def write_report(
    *,
    strict: bool,
    case_prefix: str,
    ticker_filter: str,
    source: CsvData,
    dates: CsvData,
    candidates: CsvData,
    issues: list[Issue],
) -> None:
    warnings, failures = issue_counts(issues)
    status = "PASS" if failures == 0 else "FAIL"
    lines = [
        "# Source Evidence Integrity Report",
        "",
        f"- Mode: {'strict' if strict else 'non-strict'}",
        f"- Case prefix filter: {case_prefix or 'none'}",
        f"- Ticker filter: {ticker_filter or 'none'}",
        f"- Overall status: {status}",
        f"- Warnings: {warnings}",
        f"- Failures: {failures}",
        "",
        "## Inputs",
        "",
        "| File | Rows | Columns | Parse status |",
        "|---|---:|---:|---|",
        f"| `{source.path.relative_to(REPO_ROOT)}` | {len(source.rows)} | {len(source.fieldnames)} | {source.parse_error or 'OK'} |",
        f"| `{dates.path.relative_to(REPO_ROOT)}` | {len(dates.rows)} | {len(dates.fieldnames)} | {dates.parse_error or 'OK'} |",
        f"| `{candidates.path.relative_to(REPO_ROOT)}` | {len(candidates.rows)} | {len(candidates.fieldnames)} | {candidates.parse_error or 'OK'} |",
        "",
        "## Issue Summary",
        "",
    ]

    counts = Counter((item.severity, item.check_id) for item in issues)
    if counts:
        lines.extend(["| Severity | Check | Count |", "|---|---|---:|"])
        for (severity, check_id), count in sorted(counts.items()):
            lines.append(f"| {severity} | {check_id} | {count} |")
    else:
        lines.append("No issues found.")

    lines.extend(["", "## Issues", ""])
    if issues:
        lines.extend(["| Severity | Check | File | Row | Case ID | Ticker | Detail |", "|---|---|---|---:|---|---|---|"])
        for item in sorted(issues, key=lambda i: (i.severity != "FAIL", i.check_id, str(i.row_number))):
            detail = item.detail.replace("|", "\\|")
            lines.append(
                f"| {item.severity} | {item.check_id} | `{item.file_name}` | {item.row_number} | "
                f"{item.case_id or ''} | {item.ticker or ''} | {detail} |"
            )
    else:
        lines.append("No warnings or failures.")

    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- Malformed dates, conflicting HIGH-confidence dates, duplicate exact evidence rows, and missing required columns are failures.",
            "- MEDIUM confidence rows, missing source URLs, duplicate tickers with different dates, and implausible year differences are warnings in non-strict mode.",
            "- The validator is read-only except for this report.",
        ]
    )
    REPORT_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def run(strict: bool, case_prefix: str, ticker_filter: str) -> tuple[str, int, int, list[Issue]]:
    source = read_csv_data(SOURCE_EVIDENCE)
    dates = read_csv_data(ANNOUNCEMENT_DATES)
    candidates = read_csv_data(RESOLVED_CANDIDATES)

    source_rows = filtered_rows(source, case_prefix, ticker_filter)
    date_rows = filtered_rows(dates, case_prefix, ticker_filter)
    year_index = candidate_year_index(candidates)

    issues: list[Issue] = []
    issues.extend(validate_required_files(source, dates, candidates))
    issues.extend(validate_dates(source, source_rows))
    issues.extend(validate_dates(dates, date_rows))
    issues.extend(validate_source_rows(source, source_rows, strict))
    issues.extend(validate_date_rows(dates, date_rows, strict))
    issues.extend(validate_duplicate_evidence(source, source_rows))
    issues.extend(validate_duplicate_dates(dates, date_rows))
    issues.extend(validate_cross_checks(source, dates, source_rows, date_rows, strict))
    issues.extend(validate_candidate_years(dates, date_rows, year_index))
    issues = apply_strict(issues, strict)

    write_report(
        strict=strict,
        case_prefix=case_prefix,
        ticker_filter=ticker_filter,
        source=source,
        dates=dates,
        candidates=candidates,
        issues=issues,
    )

    warnings, failures = issue_counts(issues)
    status = "PASS" if failures == 0 else "FAIL"
    return status, warnings, failures, issues


def print_summary(status: str, warnings: int, failures: int, issues: list[Issue]) -> None:
    print(f"Source evidence integrity: {status}")
    print(f"Warnings: {warnings}")
    print(f"Failures: {failures}")
    print(f"Report: {REPORT_OUTPUT.relative_to(REPO_ROOT)}")
    if issues:
        print()
        for item in sorted(issues, key=lambda i: (i.severity != "FAIL", i.check_id, str(i.row_number)))[:40]:
            location = f"{item.file_name}:{item.row_number}"
            identity = " ".join(part for part in (item.case_id, item.ticker) if part)
            print(f"[{item.severity}] {item.check_id} {location} {identity} - {item.detail}")
        if len(issues) > 40:
            print(f"... {len(issues) - 40} more issues in report")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate source evidence and acquisition date integrity.")
    parser.add_argument("--strict", action="store_true", help="Promote selected data-quality warnings to failures")
    parser.add_argument("--case-prefix", default="", help="Limit checks to case_ids beginning with this prefix")
    parser.add_argument("--ticker", default="", help="Limit checks to one ticker")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    status, warnings, failures, issues = run(args.strict, args.case_prefix, args.ticker)
    print_summary(status, warnings, failures, issues)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
