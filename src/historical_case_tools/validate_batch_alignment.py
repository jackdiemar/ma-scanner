#!/usr/bin/env python3
"""
Read-only batch file alignment validator for the historical case factory.

Compares batch-scoped CSV and JSON artifacts against the candidate queue as the
canonical source. The script writes only:
  - data/historical_cases/{batch_name}_alignment_validation_report.md

It does not mutate CSVs, source evidence, scanner outputs, or case factory state.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

TICKER_FIELDS = ("ticker", "target_ticker", "company_ticker")
CASE_ID_FIELDS = ("case_id", "candidate_id", "target_case_id")


@dataclass(frozen=True)
class FileSpec:
    label: str
    suffix: str
    expected: bool = True
    requires_full_batch: bool = False

    def path(self, batch_name: str) -> Path:
        return HISTORICAL_DIR / f"{batch_name}_{self.suffix}"


FILE_SPECS = [
    FileSpec("candidate_queue", "candidate_queue.csv", requires_full_batch=True),
    FileSpec("staging_candidates", "staging_candidates.csv", requires_full_batch=True),
    FileSpec("date_prefill_queue", "date_prefill_queue.csv", requires_full_batch=True),
    FileSpec("exception_queue", "exception_queue.csv", requires_full_batch=True),
    FileSpec("source_evidence_draft", "source_evidence_draft.csv"),
    FileSpec("pre_announcement_filing_targets", "pre_announcement_filing_targets.csv"),
    FileSpec("filing_targets", "filing_targets.csv", expected=False),
    FileSpec("run_manifest", "run_manifest.json"),
]


@dataclass
class ExtractedFile:
    spec: FileSpec
    path: Path
    found: bool
    row_count: int = 0
    ticker_values: list[str] | None = None
    case_id_values: list[str] | None = None
    ticker_field: str = ""
    case_id_field: str = ""
    read_error: str = ""
    rows: list[dict[str, str]] | None = None

    @property
    def tickers(self) -> set[str]:
        return set(self.ticker_values or [])

    @property
    def case_ids(self) -> set[str]:
        return set(self.case_id_values or [])

    @property
    def duplicate_tickers(self) -> list[str]:
        return sorted(value for value, count in Counter(self.ticker_values or []).items() if count > 1)

    @property
    def duplicate_case_ids(self) -> list[str]:
        return sorted(value for value, count in Counter(self.case_id_values or []).items() if count > 1)


@dataclass
class Comparison:
    file: ExtractedFile
    extra_tickers: list[str]
    missing_tickers: list[str]
    extra_case_ids: list[str]
    missing_case_ids: list[str]
    duplicated_tickers: list[str]
    duplicated_case_ids: list[str]
    wrong_old_index_tickers: list[str]
    failures: list[str]
    warnings: list[str]
    expected_source: str = "candidate_queue"


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalize_ticker(value: Any) -> str:
    return clean(value).upper()


def normalize_case_id(value: Any) -> str:
    return clean(value)


def first_present_field(fieldnames: Iterable[str] | None, candidates: tuple[str, ...]) -> str:
    if not fieldnames:
        return ""
    field_set = {field.strip(): field for field in fieldnames}
    for candidate in candidates:
        if candidate in field_set:
            return field_set[candidate]
    lower_map = {field.strip().lower(): field for field in fieldnames}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return ""


def read_csv_file(spec: FileSpec, path: Path) -> ExtractedFile:
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as exc:
        return ExtractedFile(spec=spec, path=path, found=True, read_error=str(exc))

    ticker_field = first_present_field(reader.fieldnames, TICKER_FIELDS)
    case_id_field = first_present_field(reader.fieldnames, CASE_ID_FIELDS)
    tickers = [normalize_ticker(row.get(ticker_field)) for row in rows if ticker_field and normalize_ticker(row.get(ticker_field))]
    case_ids = [normalize_case_id(row.get(case_id_field)) for row in rows if case_id_field and normalize_case_id(row.get(case_id_field))]
    return ExtractedFile(
        spec=spec,
        path=path,
        found=True,
        row_count=len(rows),
        ticker_values=tickers,
        case_id_values=case_ids,
        ticker_field=ticker_field,
        case_id_field=case_id_field,
        rows=rows,
    )


def collect_json_values(value: Any, keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    key_set = {key.lower() for key in keys}

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key.lower() in key_set and not isinstance(child, (dict, list)):
                    cleaned = clean(child)
                    if cleaned:
                        values.append(cleaned)
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    return values


def read_json_file(spec: FileSpec, path: Path) -> ExtractedFile:
    try:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:
        return ExtractedFile(spec=spec, path=path, found=True, read_error=str(exc))

    tickers = [normalize_ticker(value) for value in collect_json_values(payload, TICKER_FIELDS)]
    case_ids = [normalize_case_id(value) for value in collect_json_values(payload, CASE_ID_FIELDS)]
    row_count = len(tickers) or len(case_ids)
    return ExtractedFile(
        spec=spec,
        path=path,
        found=True,
        row_count=row_count,
        ticker_values=tickers,
        case_id_values=case_ids,
        ticker_field="recursive_json",
        case_id_field="recursive_json",
    )


def read_batch_file(spec: FileSpec, batch_name: str) -> ExtractedFile:
    path = spec.path(batch_name)
    if not path.exists():
        return ExtractedFile(spec=spec, path=path, found=False, ticker_values=[], case_id_values=[])
    if path.suffix.lower() == ".json":
        return read_json_file(spec, path)
    return read_csv_file(spec, path)


def upper(value: Any) -> str:
    return clean(value).upper()


def row_value(row: dict[str, str], candidates: tuple[str, ...]) -> str:
    field = first_present_field(row.keys(), candidates)
    if not field:
        return ""
    return clean(row.get(field))


def row_ticker(row: dict[str, str]) -> str:
    return normalize_ticker(row_value(row, TICKER_FIELDS))


def row_case_id(row: dict[str, str]) -> str:
    return normalize_case_id(row_value(row, CASE_ID_FIELDS))


def row_date(row: dict[str, str]) -> str:
    return row_value(
        row,
        (
            "announcement_date",
            "acquisition_announcement_date",
            "current_announcement_date",
            "event_date",
        ),
    )


def row_status_text(row: dict[str, str]) -> str:
    fields = (
        "priority_tier",
        "adjudication_status",
        "recommended_status",
        "hit_status",
        "next_action",
        "notes",
    )
    return " ".join(upper(row.get(field)) for field in fields if field in row)


def is_blocked_row(row: dict[str, str]) -> bool:
    status = row_status_text(row)
    if "DATE_OR_CIK_BLOCKED" in status or "BLOCKED" in status:
        return True
    needs_backfill = upper(row.get("needs_date_backfill"))
    return needs_backfill in {"TRUE", "YES", "1"}


def is_multirow_filing_target(file: ExtractedFile) -> bool:
    if "filing_targets" not in file.spec.label:
        return False
    unique_case_count = len(file.case_ids)
    if unique_case_count and file.row_count > unique_case_count:
        return True
    for row in file.rows or []:
        if clean(row.get("filing_date")) or clean(row.get("accession_number")):
            return True
    return False


@dataclass(frozen=True)
class ExpectedSet:
    tickers: set[str]
    case_ids: set[str]
    source: str
    warnings: tuple[str, ...] = ()


def expected_from_rows(rows: list[dict[str, str]], source: str) -> ExpectedSet:
    tickers = {row_ticker(row) for row in rows if row_ticker(row)}
    case_ids = {row_case_id(row) for row in rows if row_case_id(row)}
    return ExpectedSet(tickers=tickers, case_ids=case_ids, source=source)


def eligible_from_exception_queue(exception_file: ExtractedFile) -> ExpectedSet | None:
    if not exception_file.found or exception_file.read_error:
        return None

    eligible_rows = []
    for row in exception_file.rows or []:
        status = row_status_text(row)
        if is_blocked_row(row):
            continue
        has_date = bool(row_date(row))
        has_eligible_status = (
            "PENDING_FILING_COLLECTION" in status
            or "P1" in status
            or "P2" in status
            or "P3" in status
            or "P4" in status
            or "P5" in status
            or "P6" in status
            or "REVIEW" in status
        )
        if has_date and has_eligible_status:
            eligible_rows.append(row)

    return expected_from_rows(eligible_rows, "eligible_dated_cases_from_exception_queue")


def eligible_from_confirmation_staging(batch_name: str) -> ExpectedSet | None:
    path = HISTORICAL_DIR / f"{batch_name}_confirmation_results_staging.csv"
    if not path.exists():
        return None
    spec = FileSpec("confirmation_results_staging", "confirmation_results_staging.csv")
    staging = read_csv_file(spec, path)
    if staging.read_error:
        return None

    eligible_rows = []
    for row in staging.rows or []:
        if row_date(row) and not is_blocked_row(row):
            eligible_rows.append(row)
    return expected_from_rows(eligible_rows, "eligible_dated_cases_from_confirmation_results_staging")


def eligible_filing_targets(files_by_label: dict[str, ExtractedFile], batch_name: str) -> ExpectedSet:
    from_exception = eligible_from_exception_queue(files_by_label["exception_queue"])
    if from_exception and (from_exception.tickers or from_exception.case_ids):
        return from_exception

    from_staging = eligible_from_confirmation_staging(batch_name)
    if from_staging and (from_staging.tickers or from_staging.case_ids):
        return from_staging

    return ExpectedSet(
        tickers=set(),
        case_ids=set(),
        source="eligible_set_unavailable",
        warnings=("eligible_set_unavailable",),
    )


def case_number(case_id: str) -> int | None:
    match = re.match(r"^RHC-(\d+)-", case_id)
    if not match:
        return None
    return int(match.group(1))


def batch_range(batch_name: str) -> tuple[int | None, int | None]:
    match = re.match(r"^batch_(\d+)_(\d+)$", batch_name)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def wrong_old_index_tickers(file: ExtractedFile, canonical_case_ids: set[str], batch_name: str) -> list[str]:
    start, end = batch_range(batch_name)
    if start is None or end is None:
        return []

    wrong: list[str] = []
    case_to_ticker = {}
    for case_id, ticker in zip(file.case_id_values or [], file.ticker_values or []):
        case_to_ticker[case_id] = ticker

    for case_id, ticker in case_to_ticker.items():
        number = case_number(case_id)
        if number is None:
            continue
        if start <= number <= end and case_id not in canonical_case_ids:
            wrong.append(ticker or case_id)
    return sorted(set(wrong))


def compare_file(
    file: ExtractedFile,
    canonical: ExtractedFile,
    batch_name: str,
    expected: ExpectedSet | None = None,
) -> Comparison:
    failures: list[str] = []
    warnings: list[str] = []
    expected = expected or ExpectedSet(canonical.tickers, canonical.case_ids, "candidate_queue")
    multirow_filing_target = is_multirow_filing_target(file)

    has_identifier_values = bool(file.ticker_values or file.case_id_values)
    if not has_identifier_values and not file.read_error:
        warnings.append("no_ticker_or_case_id_values")
        return Comparison(
            file=file,
            extra_tickers=[],
            missing_tickers=[],
            extra_case_ids=[],
            missing_case_ids=[],
            duplicated_tickers=[],
            duplicated_case_ids=[],
            wrong_old_index_tickers=[],
            failures=failures,
            warnings=warnings,
            expected_source=expected.source,
        )

    extra_tickers = sorted(file.tickers - expected.tickers)
    missing_tickers = sorted(expected.tickers - file.tickers)
    extra_case_ids = sorted(file.case_ids - expected.case_ids)
    missing_case_ids = sorted(expected.case_ids - file.case_ids)
    outside_candidate_tickers = sorted(file.tickers - canonical.tickers)
    outside_candidate_case_ids = sorted(file.case_ids - canonical.case_ids)
    duplicated_tickers = [] if multirow_filing_target else file.duplicate_tickers
    duplicated_case_ids = [] if multirow_filing_target else file.duplicate_case_ids
    old_index_tickers = wrong_old_index_tickers(file, canonical.case_ids, batch_name)

    if file.read_error:
        failures.append(f"read_error: {file.read_error}")
    warnings.extend(expected.warnings)
    if duplicated_tickers:
        failures.append("duplicated_tickers")
    if duplicated_case_ids:
        failures.append("duplicated_case_ids")
    if outside_candidate_tickers:
        failures.append("outside_candidate_tickers")
    if outside_candidate_case_ids:
        failures.append("outside_candidate_case_ids")
    if extra_tickers:
        failures.append("extra_or_ineligible_tickers")
    if extra_case_ids:
        failures.append("extra_or_ineligible_case_ids")
    if old_index_tickers:
        failures.append("wrong_old_index_tickers")
    if multirow_filing_target and expected.source == "eligible_set_unavailable":
        warnings.append("filing_target_eligible_set_unavailable")
    elif multirow_filing_target and missing_tickers:
        failures.append("missing_eligible_tickers")
    elif file.spec.requires_full_batch and missing_tickers:
        failures.append("missing_tickers")
    elif missing_tickers:
        warnings.append("missing_tickers")
    if multirow_filing_target and expected.source == "eligible_set_unavailable":
        pass
    elif multirow_filing_target and missing_case_ids:
        failures.append("missing_eligible_case_ids")
    elif file.spec.requires_full_batch and missing_case_ids:
        failures.append("missing_case_ids")
    elif missing_case_ids:
        warnings.append("missing_case_ids")

    return Comparison(
        file=file,
        extra_tickers=extra_tickers,
        missing_tickers=missing_tickers,
        extra_case_ids=extra_case_ids,
        missing_case_ids=missing_case_ids,
        duplicated_tickers=duplicated_tickers,
        duplicated_case_ids=duplicated_case_ids,
        wrong_old_index_tickers=old_index_tickers,
        failures=failures,
        warnings=warnings,
        expected_source=expected.source,
    )


def fmt_list(values: list[str], limit: int = 20) -> str:
    if not values:
        return "None"
    shown = values[:limit]
    suffix = "" if len(values) <= limit else f" ... (+{len(values) - limit} more)"
    return ", ".join(shown) + suffix


def status_for(comparison: Comparison) -> str:
    if comparison.failures:
        return "FAIL"
    if comparison.warnings:
        return "WARN"
    return "PASS"


def write_report(
    *,
    batch_name: str,
    strict: bool,
    files: list[ExtractedFile],
    missing_files: list[ExtractedFile],
    comparisons: list[Comparison],
    overall_status: str,
    report_path: Path,
) -> None:
    found_files = [file for file in files if file.found]
    lines: list[str] = [
        f"# Batch Alignment Validation Report: {batch_name}",
        "",
        f"- Mode: {'strict' if strict else 'non-strict'}",
        f"- Overall status: {overall_status}",
        f"- Canonical source: `{batch_name}_candidate_queue.csv`",
        "",
        "## Files Found",
        "",
    ]

    if found_files:
        for file in found_files:
            lines.append(f"- `{file.path.relative_to(REPO_ROOT)}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Files Missing", ""])
    if missing_files:
        for file in missing_files:
            severity = "FAIL" if strict and file.spec.expected else "WARN"
            expected = "expected" if file.spec.expected else "optional"
            lines.append(f"- {severity}: `{file.path.relative_to(REPO_ROOT)}` ({expected})")
    else:
        lines.append("- None")

    lines.extend(["", "## Counts By File", ""])
    lines.append("| File | Rows | Ticker field | Unique ticker count | Case ID field | Unique case ID count | Repeated tickers | Repeated case_ids |")
    lines.append("|---|---:|---|---:|---|---:|---|---|")
    for file in found_files:
        repeated_tickers = "expected multi-row file" if is_multirow_filing_target(file) else fmt_list(file.duplicate_tickers)
        repeated_case_ids = "expected multi-row file" if is_multirow_filing_target(file) else fmt_list(file.duplicate_case_ids)
        lines.append(
            "| "
            f"{file.spec.label} | "
            f"{file.row_count} | "
            f"{file.ticker_field or 'not found'} | "
            f"{len(file.tickers)} | "
            f"{file.case_id_field or 'not found'} | "
            f"{len(file.case_ids)} | "
            f"{repeated_tickers} | "
            f"{repeated_case_ids} |"
        )

    lines.extend(["", "## Alignment Results", ""])
    lines.append("| File | Expected set | Status | Extra tickers | Missing tickers | Extra case_ids | Missing case_ids | Wrong old-index tickers | Notes |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for comparison in comparisons:
        notes = comparison.failures + comparison.warnings
        lines.append(
            "| "
            f"{comparison.file.spec.label} | "
            f"{comparison.expected_source} | "
            f"{status_for(comparison)} | "
            f"{fmt_list(comparison.extra_tickers)} | "
            f"{fmt_list(comparison.missing_tickers)} | "
            f"{fmt_list(comparison.extra_case_ids)} | "
            f"{fmt_list(comparison.missing_case_ids)} | "
            f"{fmt_list(comparison.wrong_old_index_tickers)} | "
            f"{fmt_list(notes)} |"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "- Full-batch files must contain every candidate queue ticker and case_id.",
        "- Multi-row filing target files are compared against eligible dated cases, not the full candidate queue.",
        "- Eligible dated cases come from the exception queue when available, excluding BLOCKED / DATE_OR_CIK_BLOCKED rows.",
        "- Repeated tickers and case_ids are expected in multi-row filing target files.",
        "- Partial downstream files may omit canonical candidates, but may not introduce extras.",
        "- Any extra ticker outside the expected set, outside-candidate ticker, duplicate in one-row-per-case files, read error, or wrong old-index detection is a failure.",
        "- In strict mode, missing expected downstream files are failures.",
        "",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")


def validate(batch_name: str, strict: bool) -> tuple[int, str, list[Comparison], list[ExtractedFile], Path]:
    files = [read_batch_file(spec, batch_name) for spec in FILE_SPECS]
    by_label = {file.spec.label: file for file in files}
    canonical = by_label["candidate_queue"]
    report_path = HISTORICAL_DIR / f"{batch_name}_alignment_validation_report.md"

    comparisons: list[Comparison] = []
    missing_files = [file for file in files if not file.found]
    failures: list[str] = []

    if not canonical.found:
        failures.append("candidate_queue_missing")
    elif canonical.read_error:
        failures.append("candidate_queue_read_error")
    elif not canonical.tickers and not canonical.case_ids:
        failures.append("candidate_queue_has_no_ticker_or_case_id_values")
    else:
        canonical_comparison = compare_file(canonical, canonical, batch_name)
        comparisons.append(canonical_comparison)
        eligible_for_filing_targets = eligible_filing_targets(by_label, batch_name)
        if eligible_for_filing_targets.source == "eligible_set_unavailable":
            eligible_for_filing_targets = ExpectedSet(
                tickers=canonical.tickers,
                case_ids=canonical.case_ids,
                source="eligible_set_unavailable",
                warnings=eligible_for_filing_targets.warnings,
            )
        for file in files:
            if not file.found or file.spec.label == "candidate_queue":
                continue
            expected = eligible_for_filing_targets if is_multirow_filing_target(file) else None
            comparisons.append(compare_file(file, canonical, batch_name, expected))

    if strict:
        failures.extend(f"missing_file:{file.spec.label}" for file in missing_files if file.spec.expected)
    failures.extend(
        f"{comparison.file.spec.label}:{failure}"
        for comparison in comparisons
        for failure in comparison.failures
    )

    overall_status = "FAIL" if failures else "PASS"
    write_report(
        batch_name=batch_name,
        strict=strict,
        files=files,
        missing_files=missing_files,
        comparisons=comparisons,
        overall_status=overall_status,
        report_path=report_path,
    )
    return (1 if failures else 0), overall_status, comparisons, missing_files, report_path


def print_summary(
    *,
    batch_name: str,
    strict: bool,
    status: str,
    comparisons: list[Comparison],
    missing_files: list[ExtractedFile],
    report_path: Path,
) -> None:
    print(f"Batch alignment validation: {status}")
    print(f"Batch: {batch_name}")
    print(f"Mode: {'strict' if strict else 'non-strict'}")
    print(f"Report: {report_path.relative_to(REPO_ROOT)}")
    print()

    found_count = len([comparison for comparison in comparisons])
    print(f"Files compared: {found_count}")
    if missing_files:
        print("Files missing:")
        for file in missing_files:
            severity = "FAIL" if strict and file.spec.expected else "WARN"
            expected = "expected" if file.spec.expected else "optional"
            print(f"  [{severity}] {file.path.relative_to(REPO_ROOT)} ({expected})")
    else:
        print("Files missing: None")
    print()

    for comparison in comparisons:
        comp_status = status_for(comparison)
        print(
            f"[{comp_status}] {comparison.file.spec.label}: "
            f"tickers={len(comparison.file.tickers)} "
            f"case_ids={len(comparison.file.case_ids)}"
        )
        if comparison.extra_tickers:
            print(f"  extra tickers: {fmt_list(comparison.extra_tickers)}")
        if comparison.missing_tickers:
            print(f"  missing tickers: {fmt_list(comparison.missing_tickers)}")
        if comparison.extra_case_ids:
            print(f"  extra case_ids: {fmt_list(comparison.extra_case_ids)}")
        if comparison.missing_case_ids:
            print(f"  missing case_ids: {fmt_list(comparison.missing_case_ids)}")
        if comparison.duplicated_tickers:
            print(f"  duplicated tickers: {fmt_list(comparison.duplicated_tickers)}")
        if comparison.duplicated_case_ids:
            print(f"  duplicated case_ids: {fmt_list(comparison.duplicated_case_ids)}")
        if comparison.wrong_old_index_tickers:
            print(f"  wrong old-index tickers: {fmt_list(comparison.wrong_old_index_tickers)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that case factory batch files align with the candidate queue."
    )
    parser.add_argument("--batch-name", required=True, help="Batch name such as batch_71_100")
    parser.add_argument("--strict", action="store_true", help="Fail if expected downstream files are missing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    rc, status, comparisons, missing_files, report_path = validate(args.batch_name, args.strict)
    print_summary(
        batch_name=args.batch_name,
        strict=args.strict,
        status=status,
        comparisons=comparisons,
        missing_files=missing_files,
        report_path=report_path,
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
