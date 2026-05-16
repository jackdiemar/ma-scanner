#!/usr/bin/env python3
"""
Dependency-free schema contracts for historical case factory CSV rows.

This module is intentionally lightweight. It normalizes common identifiers,
checks common required fields, and returns warnings/failures instead of
raising for ordinary row-quality problems.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar


MISSING_TOKENS = {"", "VERIFY_REQUIRED", "PLACEHOLDER_PENDING_REVIEW", "TBD", "N/A", "NA", "UNKNOWN", "NONE"}


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalize_ticker(value: str) -> str:
    return clean(value).upper()


def parse_iso_date(value: str) -> str | None:
    raw = clean(value)
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def detect_column(row: dict, candidates: list[str]) -> str | None:
    if not isinstance(row, dict):
        return None
    exact = {clean(key): key for key in row.keys()}
    lower = {clean(key).lower(): key for key in row.keys()}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
        lowered = candidate.lower()
        if lowered in lower:
            return lower[lowered]
    return None


def value_for(row: dict, candidates: list[str]) -> str:
    column = detect_column(row, candidates)
    if not column:
        return ""
    return clean(row.get(column))


def is_missing(value: str) -> bool:
    return clean(value).upper() in MISSING_TOKENS


def looks_like_url(value: str) -> bool:
    return clean(value).lower().startswith(("http://", "https://"))


@dataclass
class CaseFactoryRow:
    raw: dict[str, Any]
    row_number: int | None = None
    warnings: list[str] = field(default_factory=list, init=False)
    failures: list[str] = field(default_factory=list, init=False)

    row_type: ClassVar[str] = "base"
    required_groups: ClassVar[tuple[tuple[str, list[str]], ...]] = ()
    date_fields: ClassVar[tuple[list[str], ...]] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.raw, dict):
            self.raw = {}
            self.failures.append("row_unreadable")
            return
        self.validate_required_fields()
        self.validate_dates()
        self.validate_specific()

    def get(self, candidates: list[str]) -> str:
        return value_for(self.raw, candidates)

    @property
    def ticker(self) -> str:
        return normalize_ticker(self.get(["ticker", "target_ticker", "company_ticker"]))

    @property
    def case_id(self) -> str:
        return self.get(["case_id", "candidate_id", "target_case_id"])

    @property
    def status(self) -> str:
        return self.get([
            "status",
            "verification_status",
            "adjudication_status",
            "recommended_status",
            "priority_tier",
            "hit_status",
            "inclusion_status",
        ]).upper()

    @property
    def form_type(self) -> str:
        return self.get(["filing_type", "form_type", "source_filing_type"])

    @property
    def filing_date(self) -> str:
        raw = self.get(["filing_date", "source_filing_date"])
        return parse_iso_date(raw) or raw

    @property
    def source_url(self) -> str:
        return self.get(["source_url", "source_filing_url", "best_source_url", "url", "outcome_source_url"])

    def validate_required_fields(self) -> None:
        for label, candidates in self.required_groups:
            if not self.get(candidates):
                self.failures.append(f"missing_required:{label}")

    def validate_dates(self) -> None:
        for candidates in self.date_fields:
            column = detect_column(self.raw, candidates)
            if not column:
                continue
            raw = clean(self.raw.get(column))
            if raw and parse_iso_date(raw) is None:
                self.failures.append(f"malformed_date:{column}={raw}")

    def validate_specific(self) -> None:
        return None

    def duplicate_key(self) -> tuple[str, ...]:
        return (self.case_id, self.ticker)


@dataclass
class CandidateRow(CaseFactoryRow):
    row_type: ClassVar[str] = "candidate"
    required_groups: ClassVar[tuple[tuple[str, list[str]], ...]] = (
        ("candidate_id", ["candidate_id", "case_id"]),
        ("ticker", ["ticker"]),
    )
    date_fields: ClassVar[tuple[list[str], ...]] = (["announcement_date", "acquisition_announcement_date"],)

    @property
    def case_id(self) -> str:
        return self.get(["candidate_id", "case_id"])

    @property
    def status(self) -> str:
        return self.get(["inclusion_status", "recommended_status", "verification_status"]).upper()


@dataclass
class DatePrefillRow(CaseFactoryRow):
    row_type: ClassVar[str] = "date_prefill"
    required_groups: ClassVar[tuple[tuple[str, list[str]], ...]] = (
        ("case_id", ["case_id", "candidate_id"]),
        ("ticker", ["ticker"]),
    )
    date_fields: ClassVar[tuple[list[str], ...]] = (["announcement_date", "acquisition_announcement_date"],)

    @property
    def status(self) -> str:
        return self.get(["date_confidence", "confidence", "needs_date_backfill", "next_action"]).upper()


@dataclass
class ExceptionQueueRow(CaseFactoryRow):
    row_type: ClassVar[str] = "exception_queue"
    required_groups: ClassVar[tuple[tuple[str, list[str]], ...]] = (
        ("case_id", ["case_id", "candidate_id"]),
        ("ticker", ["ticker"]),
        ("priority_tier", ["priority_tier"]),
    )
    date_fields: ClassVar[tuple[list[str], ...]] = (["announcement_date", "acquisition_announcement_date"],)

    @property
    def status(self) -> str:
        return self.get(["priority_tier", "adjudication_status", "next_action"]).upper()


@dataclass
class FilingTargetRow(CaseFactoryRow):
    row_type: ClassVar[str] = "filing_target"
    required_groups: ClassVar[tuple[tuple[str, list[str]], ...]] = (
        ("case_id", ["case_id", "candidate_id"]),
        ("ticker", ["ticker"]),
        ("announcement_date", ["announcement_date", "acquisition_announcement_date"]),
    )
    date_fields: ClassVar[tuple[list[str], ...]] = (
        ["announcement_date", "acquisition_announcement_date"],
        ["filing_date"],
    )

    def validate_specific(self) -> None:
        if self.source_url and not looks_like_url(self.source_url):
            self.warnings.append(f"source_url_not_url:{self.source_url}")

    def duplicate_key(self) -> tuple[str, ...]:
        return (
            self.case_id,
            self.ticker,
            self.get(["filing_date"]),
            self.get(["accession_number"]),
            self.source_url,
        )


@dataclass
class SignalHitRow(FilingTargetRow):
    row_type: ClassVar[str] = "signal_hit"
    required_groups: ClassVar[tuple[tuple[str, list[str]], ...]] = (
        ("case_id", ["case_id", "candidate_id"]),
        ("ticker", ["ticker"]),
        ("announcement_date", ["announcement_date", "acquisition_announcement_date"]),
        ("possible_signal_type", ["possible_signal_type", "signal_type"]),
    )


@dataclass
class SourceEvidenceRow(CaseFactoryRow):
    row_type: ClassVar[str] = "source_evidence"
    required_groups: ClassVar[tuple[tuple[str, list[str]], ...]] = (
        ("evidence_id", ["evidence_id"]),
        ("case_id", ["case_id"]),
        ("ticker", ["ticker"]),
        ("evidence_type", ["evidence_type"]),
        ("confidence", ["confidence"]),
        ("verification_status", ["verification_status"]),
        ("added_date", ["added_date"]),
    )
    date_fields: ClassVar[tuple[list[str], ...]] = (
        ["filing_date", "source_filing_date"],
        ["added_date"],
    )

    @property
    def status(self) -> str:
        return self.get(["verification_status"]).upper()

    def validate_specific(self) -> None:
        if not self.source_url or is_missing(self.source_url):
            self.warnings.append("missing_or_placeholder_source_url")
        elif not looks_like_url(self.source_url):
            self.warnings.append(f"source_url_not_url:{self.source_url}")

        if self.status == "VERIFIED" and (not self.source_url or is_missing(self.source_url)):
            self.failures.append("verified_evidence_missing_source_url")

        confidence = self.get(["confidence"]).upper()
        if confidence and confidence not in {"HIGH", "MEDIUM", "LOW"}:
            self.failures.append(f"invalid_confidence:{confidence}")

    def duplicate_key(self) -> tuple[str, ...]:
        return (self.get(["evidence_id"]),)


@dataclass
class AdjudicationResultRow(CaseFactoryRow):
    row_type: ClassVar[str] = "adjudication_result"
    required_groups: ClassVar[tuple[tuple[str, list[str]], ...]] = (
        ("case_id", ["case_id", "candidate_id"]),
        ("ticker", ["ticker"]),
        ("adjudication_classification", ["adjudication_classification", "adjudication_status"]),
    )
    date_fields: ClassVar[tuple[list[str], ...]] = (
        ["announcement_date", "acquisition_announcement_date"],
        ["filing_date"],
    )

    @property
    def status(self) -> str:
        return self.get(["adjudication_classification", "adjudication_status"]).upper()


ROW_TYPES: dict[str, type[CaseFactoryRow]] = {
    "candidate": CandidateRow,
    "candidate_row": CandidateRow,
    "date_prefill": DatePrefillRow,
    "date_prefill_row": DatePrefillRow,
    "exception_queue": ExceptionQueueRow,
    "exception_queue_row": ExceptionQueueRow,
    "filing_target": FilingTargetRow,
    "filing_target_row": FilingTargetRow,
    "signal_hit": SignalHitRow,
    "signal_hit_row": SignalHitRow,
    "source_evidence": SourceEvidenceRow,
    "source_evidence_row": SourceEvidenceRow,
    "adjudication_result": AdjudicationResultRow,
    "adjudication_result_row": AdjudicationResultRow,
}


def row_class_for(row_type: str) -> type[CaseFactoryRow]:
    key = clean(row_type).lower()
    if key not in ROW_TYPES:
        raise ValueError(f"Unknown row_type: {row_type}")
    return ROW_TYPES[key]


def validate_rows(rows: list[dict], row_type: str) -> dict:
    cls = row_class_for(row_type)
    parsed = [cls(row, index) for index, row in enumerate(rows, start=2)]
    warnings = [
        {"row": item.row_number, "case_id": item.case_id, "ticker": item.ticker, "issue": warning}
        for item in parsed
        for warning in item.warnings
    ]
    failures = [
        {"row": item.row_number, "case_id": item.case_id, "ticker": item.ticker, "issue": failure}
        for item in parsed
        for failure in item.failures
    ]
    duplicate_keys = [
        key for key, count in Counter(item.duplicate_key() for item in parsed if any(item.duplicate_key())).items()
        if count > 1
    ]
    for key in duplicate_keys:
        warnings.append({
            "row": None,
            "case_id": key[0] if key else "",
            "ticker": key[1] if len(key) > 1 else "",
            "issue": "duplicate_row_identity",
        })

    return {
        "row_type": cls.row_type,
        "row_count": len(parsed),
        "warnings": warnings,
        "failures": failures,
        "warning_count": len(warnings),
        "failure_count": len(failures),
        "status": "FAIL" if failures else "WARN" if warnings else "PASS",
    }


def summarize_schema_validation(results: dict) -> str:
    if "files" in results:
        lines = [
            f"Files checked: {len(results.get('files', []))}",
            f"Rows checked: {results.get('row_count', 0)}",
            f"Warnings: {results.get('warning_count', 0)}",
            f"Failures: {results.get('failure_count', 0)}",
            f"Status: {results.get('status', 'UNKNOWN')}",
        ]
        return "\n".join(lines)
    return (
        f"{results.get('row_type', 'unknown')}: "
        f"rows={results.get('row_count', 0)} "
        f"warnings={results.get('warning_count', 0)} "
        f"failures={results.get('failure_count', 0)} "
        f"status={results.get('status', 'UNKNOWN')}"
    )


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def validate_csv_file(path: Path, row_type: str) -> dict:
    try:
        rows = read_csv_rows(path)
    except Exception as exc:
        return {
            "path": str(path),
            "row_type": row_type,
            "row_count": 0,
            "warnings": [],
            "failures": [{"row": None, "case_id": "", "ticker": "", "issue": f"read_error:{exc}"}],
            "warning_count": 0,
            "failure_count": 1,
            "status": "FAIL",
        }
    result = validate_rows(rows, row_type)
    result["path"] = str(path)
    return result
