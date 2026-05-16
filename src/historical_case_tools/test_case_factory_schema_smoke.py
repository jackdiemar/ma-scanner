#!/usr/bin/env python3
"""
Smoke tests for dependency-free case factory schema contracts.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from historical_case_tools.case_factory_schema import (  # noqa: E402
    CandidateRow,
    SourceEvidenceRow,
    parse_iso_date,
    validate_rows,
)


def expect(condition: bool, label: str, failures: list[str]) -> None:
    if not condition:
        failures.append(label)


def main() -> int:
    failures: list[str] = []

    candidate = CandidateRow({"candidate_id": "RHC-TEST-001", "ticker": "albo"})
    expect(candidate.ticker == "ALBO", "lowercase ticker normalized", failures)
    expect(not candidate.failures, f"candidate valid: {candidate.failures}", failures)

    date_result = validate_rows(
        [{"case_id": "RHC-TEST-002", "ticker": "GNCA", "announcement_date": "2022-99-99"}],
        "date_prefill",
    )
    expect(date_result["failure_count"] == 1, "malformed date flagged", failures)
    expect(parse_iso_date("2022-04-28") == "2022-04-28", "valid ISO date parsed", failures)
    expect(parse_iso_date("2022-99-99") is None, "invalid ISO date rejected", failures)

    rows_by_type = {
        "candidate": [{"candidate_id": "RHC-TEST-003", "ticker": "SRRA"}],
        "date_prefill": [{"case_id": "RHC-TEST-004", "ticker": "FLXN", "announcement_date": "2021-10-11"}],
        "exception_queue": [{"case_id": "RHC-TEST-005", "ticker": "PTGX", "priority_tier": "BLOCKED"}],
        "filing_target": [{
            "case_id": "RHC-TEST-006",
            "ticker": "HARP",
            "announcement_date": "2020-11-01",
            "filing_date": "2020-10-01",
            "source_url": "https://www.sec.gov/Archives/test-index.htm",
        }],
        "signal_hit": [{
            "case_id": "RHC-TEST-007",
            "ticker": "MGTA",
            "announcement_date": "2023-02-02",
            "possible_signal_type": "strategic_alternatives",
        }],
        "source_evidence": [{
            "evidence_id": "RHC-TEST-008-SRC-001",
            "case_id": "RHC-TEST-008",
            "ticker": "DOVA",
            "evidence_type": "8K_MERGER",
            "source_name": "SEC EDGAR",
            "source_url": "https://www.sec.gov/Archives/test.htm",
            "confidence": "HIGH",
            "verification_status": "VERIFIED",
            "added_date": "2026-05-16",
        }],
        "adjudication_result": [{
            "case_id": "RHC-TEST-009",
            "ticker": "RIGL",
            "adjudication_classification": "DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE",
        }],
    }
    for row_type, rows in rows_by_type.items():
        result = validate_rows(rows, row_type)
        expect(result["failure_count"] == 0, f"{row_type} synthetic row valid: {result}", failures)

    missing_url = SourceEvidenceRow({
        "evidence_id": "RHC-TEST-010-SRC-001",
        "case_id": "RHC-TEST-010",
        "ticker": "CRBP",
        "evidence_type": "RESEARCH_TARGET",
        "source_name": "SEC EDGAR",
        "confidence": "LOW",
        "verification_status": "VERIFY_REQUIRED",
        "added_date": "2026-05-16",
    })
    expect("missing_or_placeholder_source_url" in missing_url.warnings, "missing source_url warns", failures)
    expect(not missing_url.failures, f"missing source_url did not crash/fail low-confidence row: {missing_url.failures}", failures)

    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
