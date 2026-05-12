#!/usr/bin/env python3
"""
Lightweight data-quality audit for historical case pipeline CSVs.

Read-only: does not modify source data or statuses.
Outputs:
  - data/historical_cases/historical_data_quality_issues.csv
  - data/historical_cases/historical_data_quality_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# --- Constants ----------------------------------------------------------------

PLACEHOLDER_DATES = frozenset(
    {
        "2020-01-01",
        "2021-01-01",
        "2022-01-01",
        "2023-01-01",
        "2024-01-01",
    }
)
VERIFY_TOKEN = "VERIFY_REQUIRED"

SOURCE_EVIDENCE_STATUS_OK = frozenset({"VERIFIED", "PARTIAL"})
CASES_DATA_QUALITY_OK_EVIDENCE = frozenset({"PARTIAL", "VERIFIED"})

RESOLVED_UNRESOLVED_HINTS = re.compile(
    r"check current status|as of 2025|still trading|may still be|not yet resolved|"
    r"verify whether an actual|outcome is not known|remains in the active universe",
    re.I,
)

DATE_LIKE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(order=True)
class Issue:
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    priority_score: int
    check_id: str
    source_file: str
    row_number: str  # 1-based or "aggregate"
    entity_id: str
    field_name: str
    message: str
    raw_detail: str = ""

    def as_csv_row(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "priority_score": str(self.priority_score),
            "check_id": self.check_id,
            "source_file": self.source_file,
            "row_number": self.row_number,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "message": self.message,
            "detail": self.raw_detail,
        }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        return [], []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []
    return list(fields), rows


def _is_blank(v: str | None) -> bool:
    return v is None or str(v).strip() == ""


def _norm_ticker(t: str) -> str:
    return str(t or "").strip().upper()


def _norm_company(s: str) -> str:
    """Normalize legal-entity suffix noise so cross-file comparisons are meaningful."""
    s = str(s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r",\s*$", "", s)
    for pat in (
        r"\binc\.?$",
        r"\bincorporated$",
        r"\bcorp\.?$",
        r"\bcorporation$",
        r"\bltd\.?$",
        r"\blimited$",
        r"\bplc$",
        r"\bn\.?v\.?$",
        r"\bs\.?a\.?$",
        r"\bholdings$",
        r"\bholding company$",
    ):
        s = re.sub(pat + r"$", "", s).strip()
    s = re.sub(r"\s+", " ", s).strip().strip(",").strip()
    return s


def _severity_rank(sev: str) -> int:
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}.get(sev, 0)


def _issue(
    check_id: str,
    severity: str,
    source_file: str,
    row_number: int | str,
    entity_id: str,
    field_name: str,
    message: str,
    detail: str = "",
) -> Issue:
    base = _severity_rank(severity) * 25
    bonus = 0
    if "case_id" in field_name or check_id in {"CROSS_CASE_ID", "EVIDENCE_GAP"}:
        bonus += 10
    if severity == "CRITICAL":
        bonus += 15
    score = min(100, base + bonus)
    return Issue(
        severity=severity,
        priority_score=score,
        check_id=check_id,
        source_file=source_file,
        row_number=str(row_number),
        entity_id=entity_id,
        field_name=field_name,
        message=message,
        raw_detail=detail,
    )


def _load_schema_required_cases(schema_path: Path) -> list[str]:
    if not schema_path.is_file():
        return []
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    fields = data.get("fields") or {}
    required = []
    for name, spec in fields.items():
        if isinstance(spec, dict) and spec.get("required") is True:
            required.append(name)
    return sorted(required)


def _parse_year_token(val: str) -> bool:
    """True if value looks like a concrete calendar year (4 digits), not a range."""
    v = str(val or "").strip()
    if not v or v == VERIFY_TOKEN:
        return False
    if re.fullmatch(r"\d{4}", v):
        return True
    return False


def _row_has_placeholder_date(row: Mapping[str, str], date_columns: Iterable[str]) -> list[tuple[str, str]]:
    hits = []
    for col in date_columns:
        if col not in row:
            continue
        val = str(row.get(col) or "").strip()
        if val in PLACEHOLDER_DATES:
            hits.append((col, val))
        if VERIFY_TOKEN in val and col.lower().endswith("date"):
            hits.append((col, val))
    return hits


def _collect_issues(
    data_dir: Path,
    schema_path: Path,
) -> list[Issue]:
    issues: list[Issue] = []

    files_map = {
        "cases_seed.csv": data_dir / "cases_seed.csv",
        "resolved_case_candidates.csv": data_dir / "resolved_case_candidates.csv",
        "candidate_case_universe.csv": data_dir / "candidate_case_universe.csv",
        "candidate_case_universe_triaged.csv": data_dir / "candidate_case_universe_triaged.csv",
        "verification_working_queue.csv": data_dir / "verification_working_queue.csv",
        "source_evidence.csv": data_dir / "source_evidence.csv",
        "price_windows.csv": data_dir / "price_windows.csv",
    }

    loaded: dict[str, tuple[list[str], list[dict[str, str]]]] = {}
    for name, p in files_map.items():
        loaded[name] = _read_csv(p)

    # --- Evidence index by case_id ---
    se_fields, se_rows = loaded["source_evidence.csv"]
    evidence_by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in se_rows:
        cid = str(r.get("case_id") or "").strip()
        if cid:
            evidence_by_case[cid].append(r)

    def has_substantive_evidence(case_id: str) -> bool:
        for er in evidence_by_case.get(case_id, []):
            st = str(er.get("verification_status") or "").strip().upper()
            et = str(er.get("evidence_type") or "").strip().upper()
            if st in SOURCE_EVIDENCE_STATUS_OK and et != "RESEARCH_TARGET":
                return True
        return False

    # --- Check 1 & 2 & 3 & 4: cases_seed ---
    cases_required = _load_schema_required_cases(schema_path)
    cs_fields, cs_rows = loaded["cases_seed.csv"]
    if cs_rows:
        case_ids = [str(r.get("case_id") or "").strip() for r in cs_rows]
        dup_case = {k for k, v in Counter(case_ids).items() if k and v > 1}
        if dup_case:
            issues.append(
                _issue(
                    "DUP_CASE_ID",
                    "CRITICAL",
                    "cases_seed.csv",
                    "aggregate",
                    ";".join(sorted(dup_case)),
                    "case_id",
                    "Duplicate case_id values in cases_seed.csv",
                )
            )
        tickers = [_norm_ticker(r.get("ticker")) for r in cs_rows]
        dup_ticker = {t for t, c in Counter(tickers).items() if t and c > 1}
        if dup_ticker:
            issues.append(
                _issue(
                    "DUP_TICKER",
                    "INFO",
                    "cases_seed.csv",
                    "aggregate",
                    ",".join(sorted(dup_ticker)),
                    "ticker",
                    "Ticker appears on multiple rows (may be multiple legitimate cases)",
                )
            )

        date_cols_cases = [
            c
            for c in cs_fields
            if "date" in c.lower() or c in ("observation_date", "deal_date", "source_filing_date", "added_date")
        ]
        valid_data_quality = frozenset(
            {"CALIBRATION_ELIGIBLE", "VERIFIED", "PARTIAL", "STUB", "VERIFY_REQUIRED"}
        )
        valid_signal_quality = frozenset(
            {"AFFIRM", "PROCESS", "ROFR", "BOILERPLATE", "SCORE_ONLY", "MERGER"}
        )

        for i, r in enumerate(cs_rows, start=2):
            cid = str(r.get("case_id") or "").strip()
            for req in cases_required:
                if req not in r or _is_blank(r.get(req)):
                    issues.append(
                        _issue(
                            "MISSING_REQUIRED",
                            "HIGH",
                            "cases_seed.csv",
                            i,
                            cid,
                            req,
                            f"Missing or empty required field per schema.json: {req}",
                        )
                    )
            dq = str(r.get("data_quality") or "").strip().upper()
            if dq and dq not in valid_data_quality:
                issues.append(
                    _issue(
                        "INVALID_ENUM",
                        "MEDIUM",
                        "cases_seed.csv",
                        i,
                        cid,
                        "data_quality",
                        f"Invalid data_quality: {dq}",
                    )
                )
            sq = str(r.get("signal_quality") or "").strip().upper()
            if sq and sq not in valid_signal_quality and sq != VERIFY_TOKEN:
                issues.append(
                    _issue(
                        "INVALID_ENUM",
                        "MEDIUM",
                        "cases_seed.csv",
                        i,
                        cid,
                        "signal_quality",
                        f"Invalid signal_quality: {sq}",
                    )
                )
            for col, val in _row_has_placeholder_date(r, date_cols_cases):
                issues.append(
                    _issue(
                        "PLACEHOLDER_DATE",
                        "MEDIUM",
                        "cases_seed.csv",
                        i,
                        cid,
                        col,
                        f"Placeholder or VERIFY_REQUIRED in date-like field: {val}",
                    )
                )
            for k, v in r.items():
                if v and VERIFY_TOKEN in str(v) and k not in ("notes", "excerpt_text", "failure_reason"):
                    if k.lower().endswith("date") or k in ("observation_date", "deal_date", "source_filing_date"):
                        pass  # already covered
                    elif k in ("source_filing_url", "price_at_signal", "mcap_at_signal_M"):
                        issues.append(
                            _issue(
                                "PLACEHOLDER_TOKEN",
                                "LOW",
                                "cases_seed.csv",
                                i,
                                cid,
                                k,
                                "VERIFY_REQUIRED token in field that should eventually be concrete",
                            )
                        )

            # Check 5: PARTIAL/VERIFIED without substantive evidence
            if dq in CASES_DATA_QUALITY_OK_EVIDENCE:
                if not has_substantive_evidence(cid):
                    issues.append(
                        _issue(
                            "EVIDENCE_GAP",
                            "HIGH",
                            "cases_seed.csv",
                            i,
                            cid,
                            "data_quality",
                            f"data_quality={dq} but no VERIFIED/PARTIAL non-RESEARCH_TARGET evidence rows",
                        )
                    )

            # Check 6: outcome / event with no timing
            outcome = str(r.get("outcome") or "").strip().upper()
            event_type = str(r.get("event_type") or "").strip().upper()
            deal_announced = str(r.get("deal_announced") or "").strip().upper()
            deal_date = str(r.get("deal_date") or "").strip()
            if outcome and outcome not in ("ONGOING", ""):
                if event_type == "COMPLETED_DEAL" or deal_announced == "TRUE":
                    if _is_blank(deal_date) or deal_date == VERIFY_TOKEN:
                        issues.append(
                            _issue(
                                "OUTCOME_WITHOUT_DATE",
                                "MEDIUM",
                                "cases_seed.csv",
                                i,
                                cid,
                                "deal_date",
                                "Resolved deal-style outcome but deal_date missing or placeholder",
                            )
                        )
            # corporate_outcome / process_event_type heuristics
            corp = str(r.get("corporate_outcome") or "").strip().upper()
            if corp and corp not in ("ONGOING", "UNKNOWN", "", "NOT_APPLICABLE"):
                if not _parse_year_token(str(r.get("days_signal_to_outcome") or "")) and _is_blank(
                    r.get("deal_date")
                ):
                    # If we have no deal_date and no numeric days, flag if observation_date is placeholder
                    od = str(r.get("observation_date") or "").strip()
                    if od in PLACEHOLDER_DATES or od == VERIFY_TOKEN:
                        issues.append(
                            _issue(
                                "OUTCOME_WITHOUT_DATE",
                                "MEDIUM",
                                "cases_seed.csv",
                                i,
                                cid,
                                "observation_date",
                                "Corporate outcome set but observation_date/deal_date timing unclear",
                            )
                        )

            # Check 7: price fields populated but observation_date bad
            price_keys = ("price_at_signal", "price_30d_after", "price_90d_after", "price_180d_after")
            has_price = any(not _is_blank(r.get(pk)) and str(r.get(pk)) != VERIFY_TOKEN for pk in price_keys)
            od = str(r.get("observation_date") or "").strip()
            if has_price and (not DATE_LIKE.match(od) or od in PLACEHOLDER_DATES):
                issues.append(
                    _issue(
                        "PRICE_WITHOUT_OBS_DATE",
                        "HIGH",
                        "cases_seed.csv",
                        i,
                        cid,
                        "observation_date",
                        "Price fields present but observation_date missing, placeholder, or non-ISO",
                    )
                )

    # --- source_evidence.csv ---
    se_valid_status = frozenset({"VERIFIED", "PARTIAL", "VERIFY_REQUIRED"})
    se_valid_evidence = frozenset(
        {
            "8K_SA",
            "8K_MERGER",
            "8K_WINDDOWN",
            "8K_BANKRUPTCY",
            "8K_ASSET_SALE",
            "8K_CAPITAL_RAISE",
            "8K_OTHER",
            "13D_INITIAL",
            "13D_AMENDMENT",
            "EXHIBIT_AGREEMENT",
            "PROXY_SA_LANGUAGE",
            "EARNINGS_SA_LANGUAGE",
            "PRICE_DATA",
            "PACER_DOCKET",
            "PRESS_RELEASE",
            "RESEARCH_TARGET",
            "OTHER",
        }
    )
    if se_rows:
        eids = [str(r.get("evidence_id") or "").strip() for r in se_rows]
        dup_eid = {k for k, v in Counter(eids).items() if k and v > 1}
        if dup_eid:
            issues.append(
                _issue(
                    "DUP_EVIDENCE_ID",
                    "CRITICAL",
                    "source_evidence.csv",
                    "aggregate",
                    ";".join(sorted(dup_eid)),
                    "evidence_id",
                    "Duplicate evidence_id",
                )
            )
        se_req = (
            "evidence_id",
            "case_id",
            "ticker",
            "evidence_type",
            "source_name",
            "supports_field",
            "confidence",
            "verification_status",
            "added_date",
        )
        for i, r in enumerate(se_rows, start=2):
            eid = str(r.get("evidence_id") or "").strip()
            for req in se_req:
                if req not in r or _is_blank(r.get(req)):
                    issues.append(
                        _issue(
                            "MISSING_REQUIRED",
                            "HIGH",
                            "source_evidence.csv",
                            i,
                            eid,
                            req,
                            "Missing required source_evidence field",
                        )
                    )
            vst = str(r.get("verification_status") or "").strip().upper()
            if vst and vst not in se_valid_status:
                issues.append(
                    _issue(
                        "INVALID_ENUM",
                        "MEDIUM",
                        "source_evidence.csv",
                        i,
                        eid,
                        "verification_status",
                        f"Invalid verification_status: {vst}",
                    )
                )
            et = str(r.get("evidence_type") or "").strip().upper()
            if et and et not in se_valid_evidence:
                issues.append(
                    _issue(
                        "INVALID_ENUM",
                        "LOW",
                        "source_evidence.csv",
                        i,
                        eid,
                        "evidence_type",
                        f"Unexpected evidence_type: {et}",
                    )
                )
            for col in ("filing_date", "added_date"):
                if col in r:
                    val = str(r.get(col) or "").strip()
                    if val and val not in PLACEHOLDER_DATES and VERIFY_TOKEN in val:
                        issues.append(
                            _issue(
                                "PLACEHOLDER_DATE",
                                "LOW",
                                "source_evidence.csv",
                                i,
                                eid,
                                col,
                                "VERIFY_REQUIRED mixed into date field",
                            )
                        )
            if str(r.get("source_url") or "").strip() == VERIFY_TOKEN and vst == "VERIFIED":
                issues.append(
                    _issue(
                        "VERIFIED_NO_URL",
                        "HIGH",
                        "source_evidence.csv",
                        i,
                        eid,
                        "source_url",
                        "verification_status=VERIFIED but source_url is VERIFY_REQUIRED",
                    )
                )

    # --- resolved_case_candidates ---
    rc_fields, rc_rows = loaded["resolved_case_candidates.csv"]
    if rc_rows:
        cids = [str(r.get("candidate_id") or "").strip() for r in rc_rows]
        dup_c = {k for k, v in Counter(cids).items() if k and v > 1}
        if dup_c:
            issues.append(
                _issue(
                    "DUP_CANDIDATE_ID",
                    "CRITICAL",
                    "resolved_case_candidates.csv",
                    "aggregate",
                    ";".join(sorted(dup_c)),
                    "candidate_id",
                    "Duplicate candidate_id",
                )
            )
        pair_counts = Counter()
        for r in rc_rows:
            pair = (_norm_ticker(r.get("ticker")), str(r.get("likely_outcome_type") or "").strip().upper())
            if pair[0]:
                pair_counts[pair] += 1
        for (t, ot), c in pair_counts.items():
            if c > 1:
                issues.append(
                    _issue(
                        "DUP_TICKER_OUTCOME",
                        "MEDIUM",
                        "resolved_case_candidates.csv",
                        "aggregate",
                        f"{t}|{ot}",
                        "ticker+likely_outcome_type",
                        f"Duplicate rows for same ticker+outcome ({c} rows)",
                    )
                )
        rc_req = (
            "candidate_id",
            "ticker",
            "company_name",
            "likely_outcome_type",
            "likely_outcome_year",
            "verification_status",
        )
        for i, r in enumerate(rc_rows, start=2):
            cid = str(r.get("candidate_id") or "").strip()
            for req in rc_req:
                if req not in r or _is_blank(r.get(req)):
                    issues.append(
                        _issue(
                            "MISSING_REQUIRED",
                            "MEDIUM",
                            "resolved_case_candidates.csv",
                            i,
                            cid,
                            req,
                            "Missing core field for resolved candidate row",
                        )
                    )
            vst = str(r.get("verification_status") or "").strip().upper()
            if vst and vst != "CANDIDATE":
                issues.append(
                    _issue(
                        "INVALID_VERIFICATION",
                        "LOW",
                        "resolved_case_candidates.csv",
                        i,
                        cid,
                        "verification_status",
                        f"Expected CANDIDATE in resolved pipeline file, got {vst}",
                    )
                )
            lot = str(r.get("likely_outcome_type") or "").strip().upper()
            loy = str(r.get("likely_outcome_year") or "").strip()
            if lot and lot not in ("ONGOING", "UNKNOWN") and not _parse_year_token(loy):
                issues.append(
                    _issue(
                        "OUTCOME_YEAR_MISSING",
                        "MEDIUM",
                        "resolved_case_candidates.csv",
                        i,
                        cid,
                        "likely_outcome_year",
                        "likely_outcome_type set but likely_outcome_year not a 4-digit year",
                    )
                )
            hint = f"{r.get('outcome_source_hint') or ''} {r.get('notes') or ''}"
            if RESOLVED_UNRESOLVED_HINTS.search(hint):
                issues.append(
                    _issue(
                        "UNRESOLVED_IN_RESOLVED_FILE",
                        "MEDIUM",
                        "resolved_case_candidates.csv",
                        i,
                        cid,
                        "notes/hint",
                        "Language suggests live or not-yet-resolved outcome in resolved_case_candidates",
                    )
                )
            if lot == "ONGOING":
                issues.append(
                    _issue(
                        "UNRESOLVED_IN_RESOLVED_FILE",
                        "HIGH",
                        "resolved_case_candidates.csv",
                        i,
                        cid,
                        "likely_outcome_type",
                        "likely_outcome_type=ONGOING in resolved_case_candidates",
                    )
                )

    # --- candidate_case_universe & triaged ---
    for fname in ("candidate_case_universe.csv", "candidate_case_universe_triaged.csv"):
        _, cu_rows = loaded[fname]  # type: ignore[index]
        if not cu_rows:
            continue
        ids = [str(r.get("candidate_id") or "").strip() for r in cu_rows]
        dup_ids = {k for k, v in Counter(ids).items() if k and v > 1}
        if dup_ids:
            issues.append(
                _issue(
                    "DUP_CANDIDATE_ID",
                    "CRITICAL",
                    fname,
                    "aggregate",
                    ";".join(sorted(dup_ids)),
                    "candidate_id",
                    "Duplicate candidate_id",
                )
            )
        req = ("candidate_id", "ticker", "company_name", "category", "verification_status")
        for i, r in enumerate(cu_rows, start=2):
            cid = str(r.get("candidate_id") or "").strip()
            for f in req:
                if f not in r or _is_blank(r.get(f)):
                    issues.append(
                        _issue(
                            "MISSING_REQUIRED",
                            "MEDIUM",
                            fname,
                            i,
                            cid,
                            f,
                            "Missing core candidate universe field",
                        )
                    )
            vst = str(r.get("verification_status") or "").strip().upper()
            if vst and vst != "CANDIDATE":
                issues.append(
                    _issue(
                        "INVALID_VERIFICATION",
                        "LOW",
                        fname,
                        i,
                        cid,
                        "verification_status",
                        f"Expected CANDIDATE, got {vst}",
                    )
                )
        if fname == "candidate_case_universe_triaged.csv":
            for i, r in enumerate(cu_rows, start=2):
                cid = str(r.get("candidate_id") or "").strip()
                lr = str(r.get("likely_resolved_historical") or "").strip().upper()
                ll = str(r.get("likely_live_unresolved") or "").strip().upper()
                if lr == "TRUE" and ll == "TRUE":
                    issues.append(
                        _issue(
                            "TRIAGE_CONTRADICTION",
                            "MEDIUM",
                            fname,
                            i,
                            cid,
                            "likely_resolved_historical/likely_live_unresolved",
                            "Both likely_resolved_historical and likely_live_unresolved are TRUE",
                        )
                    )

    # --- verification_working_queue ---
    vq_fields, vq_rows = loaded["verification_working_queue.csv"]
    if vq_rows:
        seen_pairs = Counter()
        for r in vq_rows:
            t = _norm_ticker(r.get("ticker"))
            c = str(r.get("case_id_current") or "").strip()
            if t:
                seen_pairs[(t, c)] += 1
        for (t, c), n in seen_pairs.items():
            if n > 1:
                issues.append(
                    _issue(
                        "DUP_QUEUE_ROW",
                        "MEDIUM",
                        "verification_working_queue.csv",
                        "aggregate",
                        f"{t}|{c}",
                        "ticker+case_id_current",
                        "Duplicate ticker/case_id_current combination",
                    )
                )
        vstat_ok = frozenset({"STUB", "PARTIAL", "VERIFIED", "CANDIDATE"})
        for i, r in enumerate(vq_rows, start=2):
            t = _norm_ticker(r.get("ticker"))
            ccid = str(r.get("case_id_current") or "").strip()
            st = str(r.get("current_status") or "").strip().upper()
            if st and st not in vstat_ok:
                issues.append(
                    _issue(
                        "INVALID_ENUM",
                        "LOW",
                        "verification_working_queue.csv",
                        i,
                        ccid,
                        "current_status",
                        f"Unexpected current_status: {st}",
                    )
                )
            if st in CASES_DATA_QUALITY_OK_EVIDENCE and not has_substantive_evidence(ccid):
                issues.append(
                    _issue(
                        "EVIDENCE_GAP",
                        "HIGH",
                        "verification_working_queue.csv",
                        i,
                        ccid,
                        "current_status",
                        f"Queue status {st} but no substantive source_evidence for case_id",
                    )
                )

    # --- price_windows ---
    pw_fields, pw_rows = loaded["price_windows.csv"]
    price_cols_pw = [
        c
        for c in (pw_fields or [])
        if "price" in c.lower() or c in ("max_drawdown_after_signal",)
    ]
    if pw_rows:
        for i, r in enumerate(pw_rows, start=2):
            cid = str(r.get("case_id") or "").strip()
            od = str(r.get("observation_date") or "").strip()
            any_price = False
            for pc in price_cols_pw:
                v = str(r.get(pc) or "").strip()
                if v and v not in ("", "0", "0.0"):
                    try:
                        float(v)
                        any_price = True
                    except ValueError:
                        pass
            if any_price and (not DATE_LIKE.match(od) or od == VERIFY_TOKEN):
                issues.append(
                    _issue(
                        "PRICE_WITHOUT_OBS_DATE",
                        "HIGH",
                        "price_windows.csv",
                        i,
                        cid,
                        "observation_date",
                        "Numeric price data present but observation_date invalid",
                    )
                )
            if od in PLACEHOLDER_DATES or od == VERIFY_TOKEN:
                issues.append(
                    _issue(
                        "PLACEHOLDER_DATE",
                        "MEDIUM",
                        "price_windows.csv",
                        i,
                        cid,
                        "observation_date",
                        f"observation_date is placeholder or VERIFY_REQUIRED: {od}",
                    )
                )

    # --- Check 8: cross-file ticker / company ---
    ticker_to_names: dict[str, set[str]] = defaultdict(set)
    sources_for_names = [
        ("cases_seed.csv", "ticker", "company"),
        ("resolved_case_candidates.csv", "ticker", "company_name"),
        ("candidate_case_universe.csv", "ticker", "company_name"),
        ("candidate_case_universe_triaged.csv", "ticker", "company_name"),
        ("verification_working_queue.csv", "ticker", "ticker"),  # no company column
        ("source_evidence.csv", "ticker", "ticker"),
    ]
    for fname, tk, ck in sources_for_names:
        _, rows = loaded[fname]  # type: ignore[index]
        if ck == "ticker":
            continue
        for r in rows:
            t = _norm_ticker(r.get(tk))
            name = str(r.get(ck) or "").strip()
            if t and name:
                ticker_to_names[t].add(_norm_company(name))

    for t, names in ticker_to_names.items():
        # Ignore trivial variants: Inc vs Incorporated already normalized weakly
        if len(names) <= 1:
            continue
        # If one name is substring of another, downgrade
        slist = sorted(names)
        issues.append(
            _issue(
                "NAME_MISMATCH",
                "MEDIUM",
                "cross_file",
                "aggregate",
                t,
                "company",
                "Multiple normalized company strings for same ticker across pipeline files",
                detail=" | ".join(slist[:5]),
            )
        )

    # Cross-check cases_seed case_id vs queue case_id_current per ticker
    _, cs_r2 = loaded["cases_seed.csv"]
    seed_by_ticker = {_norm_ticker(r.get("ticker")): str(r.get("case_id") or "").strip() for r in cs_r2}
    for r in vq_rows:
        t = _norm_ticker(r.get("ticker"))
        qid = str(r.get("case_id_current") or "").strip()
        sid = seed_by_ticker.get(t)
        if sid and qid and sid != qid:
            issues.append(
                _issue(
                    "CROSS_CASE_ID",
                    "HIGH",
                    "cross_file",
                    "aggregate",
                    t,
                    "case_id",
                    f"cases_seed case_id {sid} != verification_working_queue case_id_current {qid}",
                )
            )

    # --- Check 10: category representation ---
    if rc_rows:
        counts = Counter(str(r.get("likely_outcome_type") or "").strip().upper() for r in rc_rows)
        total = sum(counts.values()) or 1
        # flag categories with <2% of rows (and at least one row elsewhere) as underrepresented tail
        for cat, cnt in counts.most_common():
            if not cat:
                continue
            pct = cnt / total
            if pct < 0.02 and cnt < max(3, int(0.02 * total)):
                issues.append(
                    _issue(
                        "UNDERREPRESENTED_CATEGORY",
                        "INFO",
                        "resolved_case_candidates.csv",
                        "aggregate",
                        cat,
                        "likely_outcome_type",
                        f"Outcome category {cat} is {pct*100:.1f}% of file ({cnt} rows) — possible sampling gap",
                    )
                )
    _, cu_all = loaded["candidate_case_universe.csv"]
    if cu_all:
        ccounts = Counter(str(r.get("category") or "").strip() for r in cu_all)
        total2 = sum(ccounts.values()) or 1
        rare = [(c, n) for c, n in ccounts.items() if c and n / total2 < 0.01]
        for c, n in sorted(rare, key=lambda x: x[1])[:15]:
            issues.append(
                _issue(
                    "UNDERREPRESENTED_CATEGORY",
                    "INFO",
                    "candidate_case_universe.csv",
                    "aggregate",
                    c,
                    "category",
                    f"Category {c} is {n/total2*100:.2f}% of universe ({n} rows)",
                )
            )

    return issues


def _write_issues_csv(path: Path, issues: Sequence[Issue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "severity",
        "priority_score",
        "check_id",
        "source_file",
        "row_number",
        "entity_id",
        "field_name",
        "message",
        "detail",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for iss in sorted(issues, key=lambda x: (-x.priority_score, -_severity_rank(x.severity), x.check_id)):
            w.writerow(iss.as_csv_row())


def _write_report_md(path: Path, issues: Sequence[Issue], data_dir: Path) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    counts = Counter(i.severity for i in issues)
    top = sorted(issues, key=lambda x: (-x.priority_score, -_severity_rank(x.severity), x.check_id))[:20]

    lines = [
        "# Historical pipeline data quality audit",
        "",
        f"- Generated (UTC): `{now}`",
        f"- Data directory: `{data_dir}`",
        "",
        "## Severity counts",
        "",
        "| Severity | Count |",
        "|----------|-------|",
    ]
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        lines.append(f"| {sev} | {counts.get(sev, 0)} |")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `historical_data_quality_issues.csv` — one row per finding",
            "- This report — summary and top priorities",
            "",
            "## Top 20 priority issues",
            "",
        ]
    )
    for j, iss in enumerate(top, start=1):
        lines.append(f"{j}. **[{iss.severity}]** `{iss.check_id}` — {iss.message}")
        lines.append(
            f"   - File: `{iss.source_file}` row {iss.row_number} entity `{iss.entity_id}` field `{iss.field_name}`"
        )
        if iss.raw_detail:
            lines.append(f"   - Detail: {iss.raw_detail}")
        lines.append("")

    lines.extend(
        [
            "## Suggested next cleanup task",
            "",
            "Reconcile **CROSS_CASE_ID** (queue vs `cases_seed`) and backfill schema-required fields such as **deal_type** where rows are otherwise structured, then clear **PLACEHOLDER_DATE** / **PRICE_WITHOUT_OBS_DATE** so evidence, prices, and case IDs line up.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit historical case pipeline CSVs (read-only).")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory containing pipeline CSVs (default: <repo>/data/historical_cases)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="schema.json path (default: <data-dir>/schema.json)",
    )
    parser.add_argument(
        "--issues-out",
        type=Path,
        default=None,
        help="Output CSV for issues",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help="Output Markdown report",
    )
    args = parser.parse_args()

    root = _repo_root()
    data_dir = (args.data_dir or (root / "data" / "historical_cases")).resolve()
    schema_path = (args.schema or (data_dir / "schema.json")).resolve()
    issues_out = (args.issues_out or (data_dir / "historical_data_quality_issues.csv")).resolve()
    report_out = (args.report_out or (data_dir / "historical_data_quality_report.md")).resolve()

    issues = _collect_issues(data_dir, schema_path)
    _write_issues_csv(issues_out, issues)
    _write_report_md(report_out, issues, data_dir)

    sev_counts = Counter(i.severity for i in issues)
    print(f"Wrote {issues_out} ({len(issues)} issues)")
    print(f"Wrote {report_out}")
    print("By severity:", dict(sev_counts))


if __name__ == "__main__":
    main()
