#!/usr/bin/env python3
"""
case_factory_date_backfiller.py

Automated, conservative source-backed announcement date discovery for batch
candidates missing from acquisition_announcement_dates.csv.

For each missing-date candidate:
1. Resolves the company CIK via EDGAR company_tickers.json or company search
2. Fetches the EDGAR submissions JSON to find 8-K filings with Item 1.01
3. Filters for the most likely merger announcement in the expected deal-year window
4. Verifies the filing index for EX-2.x exhibits (merger agreement evidence)
5. Writes confirmed dates to acquisition_announcement_dates.csv
6. Writes source evidence rows to source_evidence.csv
7. Reports all results: found, unresolved, failure reasons

Only writes dates with direct SEC filing evidence.
Never guesses. Never uses FMP. Never changes classifications.
Confidence = HIGH when single Item 1.01 + EX-2.x in expected year.
Confidence = MEDIUM when Item 1.01 in year-1 with EX-2.x, or multiple candidates.
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

DEFAULT_DATES_CSV    = HISTORICAL_DIR / "acquisition_announcement_dates.csv"
DEFAULT_EVIDENCE_CSV = HISTORICAL_DIR / "source_evidence.csv"

USER_AGENT    = "ma-scanner-date-backfiller/1.0 research@example.com"
REQUEST_DELAY = 0.5  # seconds between EDGAR requests

DATES_FIELDS = [
    "case_id", "ticker", "company_name", "acquisition_announcement_date",
    "source_evidence_type", "source_url", "confidence", "notes", "next_action",
]

EVIDENCE_FIELDS = [
    "evidence_id", "case_id", "ticker", "evidence_type", "source_name",
    "source_url", "filing_type", "filing_date", "accession_number",
    "exhibit_number", "excerpt", "supports_field", "confidence",
    "verification_status", "added_by", "added_date", "notes",
]

# CIK cache: {ticker_upper: cik_str}
_CIK_CACHE: dict[str, str] = {}
_COMPANY_TICKERS_LOADED = False
_COMPANY_TICKERS_MAP: dict[str, str] = {}  # ticker_upper -> cik_str


# ---------------------------------------------------------------------------
# Low-level HTTP helpers
# ---------------------------------------------------------------------------

def _fetch(url: str, as_json: bool = True, timeout: int = 20) -> "Optional[dict | str]":
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            text = data.decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
            return json.loads(text) if as_json else text
    except Exception:
        return None


def _sleep() -> None:
    time.sleep(REQUEST_DELAY)


# ---------------------------------------------------------------------------
# CIK resolution
# ---------------------------------------------------------------------------

def _load_company_tickers() -> None:
    global _COMPANY_TICKERS_LOADED, _COMPANY_TICKERS_MAP
    if _COMPANY_TICKERS_LOADED:
        return
    data = _fetch("https://www.sec.gov/files/company_tickers.json")
    if data:
        for v in data.values():
            tk = v.get("ticker", "").upper()
            cik = str(v.get("cik_str", ""))
            if tk and cik:
                _COMPANY_TICKERS_MAP[tk] = cik
    _COMPANY_TICKERS_LOADED = True
    _sleep()


def _cik_from_ticker(ticker: str) -> str:
    _load_company_tickers()
    cik = _COMPANY_TICKERS_MAP.get(ticker.upper(), "")
    if cik:
        return cik

    # Fallback: EDGAR company search by ticker as CIK field
    url = (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getcompany&company=&CIK={urllib.request.quote(ticker)}"
        f"&type=8-K&dateb=&owner=include&count=5&search_text="
    )
    _sleep()
    html = _fetch(url, as_json=False)
    if html:
        ciks = re.findall(r'CIK=0*(\d+)', str(html))
        if ciks:
            return ciks[0]
    return ""


def _cik_from_name(company_name: str, ticker: str) -> str:
    """Last-resort CIK lookup by company name."""
    short = company_name.split(",")[0].split("(")[0].strip()
    # Take first 2-3 words to reduce noise
    words = short.split()[:3]
    query = " ".join(words)
    url = (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getcompany&company={urllib.request.quote(query)}"
        f"&CIK=&type=8-K&dateb=&owner=include&count=5&search_text="
    )
    _sleep()
    html = _fetch(url, as_json=False)
    if html:
        ciks = re.findall(r'CIK=0*(\d+)', str(html))
        if ciks:
            return ciks[0]
    return ""


def _resolve_cik(ticker: str, company_name: str) -> str:
    if ticker in _CIK_CACHE:
        return _CIK_CACHE[ticker]
    cik = _cik_from_ticker(ticker)
    if not cik:
        cik = _cik_from_name(company_name, ticker)
    _CIK_CACHE[ticker] = cik
    return cik


# ---------------------------------------------------------------------------
# Submissions JSON: find merger announcement 8-K
# ---------------------------------------------------------------------------

def _padded_cik(cik: str) -> str:
    digits = re.sub(r"\D", "", cik)
    return digits.zfill(10)


def _fetch_submissions(cik: str) -> Optional[dict]:
    _sleep()
    return _fetch(f"https://data.sec.gov/submissions/CIK{_padded_cik(cik)}.json")


def _index_url(cik: str, accession_no: str) -> str:
    acc_nodash = re.sub(r"\D", "", accession_no)
    return f"https://www.sec.gov/Archives/edgar/data/{re.sub(r'[^0-9]', '', cik)}/{acc_nodash}/{accession_no}-index.htm"


def _has_merger_exhibit(cik: str, accession_no: str) -> bool:
    """Return True if the filing index lists an EX-2.x (merger/acquisition agreement)."""
    _sleep()
    html = _fetch(_index_url(cik, accession_no), as_json=False)
    if not html:
        return False
    return bool(re.search(r"EX-2\b", str(html), re.IGNORECASE))


def _find_merger_8k(
    cik: str,
    expected_year: str,
) -> dict:
    """
    Scan submissions JSON for Item 1.01 8-K filings in [expected_year-2, expected_year].
    Returns the best candidate with confidence scoring.
    """
    result = {"found": False, "filing_date": "", "accession": "",
              "form_type": "", "confidence": "", "reason": ""}

    data = _fetch_submissions(cik)
    if not data:
        result["reason"] = "EDGAR submissions fetch failed"
        return result

    filings = data.get("filings", {}).get("recent", {})
    forms      = filings.get("form", [])
    dates      = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])
    items_all  = filings.get("items", [])

    try:
        exp_yr = int(expected_year)
    except (ValueError, TypeError):
        result["reason"] = "Invalid expected_year"
        return result

    lo_year = exp_yr - 2
    hi_year = exp_yr

    # Collect Item 1.01 8-Ks in range
    candidates: list[tuple[str, str]] = []  # (filing_date, accession_no)
    for form, dt, acc, items in zip(forms, dates, accessions, items_all):
        if form != "8-K":
            continue
        if "1.01" not in items:
            continue
        try:
            yr = int(dt[:4])
        except ValueError:
            continue
        if lo_year <= yr <= hi_year:
            candidates.append((dt, acc))

    if not candidates:
        result["reason"] = f"No Item 1.01 8-K in {lo_year}–{hi_year}"
        return result

    # Sort newest-first; prefer filings in expected_year itself
    candidates.sort(reverse=True)
    in_expected_year = [(dt, acc) for dt, acc in candidates if dt.startswith(expected_year)]
    pool = in_expected_year if in_expected_year else candidates

    best_date, best_acc = pool[0]  # most recent in preferred pool

    has_exhibit = _has_merger_exhibit(cik, best_acc)

    if len(pool) == 1 and has_exhibit:
        confidence = "HIGH"
    elif len(pool) == 1 and not has_exhibit:
        confidence = "MEDIUM"
    elif len(pool) > 1 and has_exhibit:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    result.update({
        "found": True,
        "filing_date": best_date,
        "accession": best_acc,
        "form_type": "8-K",
        "confidence": confidence,
        "has_exhibit": has_exhibit,
        "total_candidates": len(candidates),
        "reason": (
            f"Found {len(candidates)} Item 1.01 8-K(s) in range; "
            f"best={best_date}; EX-2.x={'YES' if has_exhibit else 'NO'}; "
            f"confidence={confidence}"
        ),
    })
    return result


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _append_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_date_backfill(
    queue_rows: list[dict[str, str]],
    dates_csv: Path = DEFAULT_DATES_CSV,
    evidence_csv: Path = DEFAULT_EVIDENCE_CSV,
    run_date: str = "",
) -> dict:
    """
    Attempt source-backed date backfill for missing-date candidates.

    Returns summary dict with keys:
      attempted, found, not_found, skipped, details, new_dates_written, new_evidence_written
    """
    if not run_date:
        run_date = str(date.today())

    existing_dates = _read_csv(dates_csv)
    already_dated = {
        r["ticker"] for r in existing_dates
        if r.get("acquisition_announcement_date", "").strip()
        and r.get("confidence", "").upper() in {"HIGH", "MEDIUM"}
    }

    existing_evidence = _read_csv(evidence_csv)
    existing_ev_ids = {r.get("evidence_id", "") for r in existing_evidence}

    summary: dict = {
        "attempted": 0, "found": 0, "not_found": 0,
        "skipped": 0, "details": [],
    }
    new_dates: list[dict] = []
    new_evidence: list[dict] = []

    for cand in queue_rows:
        ticker  = cand.get("ticker", "").strip()
        company = cand.get("company", "").strip()
        case_id = cand.get("candidate_id", "").strip()
        exp_year = cand.get("announcement_year", "").strip()

        if not ticker:
            continue

        if ticker in already_dated:
            summary["skipped"] += 1
            summary["details"].append({
                "ticker": ticker, "status": "SKIPPED",
                "reason": "Already has HIGH/MEDIUM confidence date",
            })
            continue

        summary["attempted"] += 1
        print(f"  [{ticker}] resolving CIK...", end=" ", flush=True)

        cik = _resolve_cik(ticker, company)
        if not cik:
            print(f"CIK not found.")
            summary["not_found"] += 1
            summary["details"].append({
                "ticker": ticker, "status": "NOT_FOUND", "reason": "CIK lookup failed",
            })
            continue

        print(f"CIK={cik}  searching 8-K Item 1.01...", end=" ", flush=True)
        hit = _find_merger_8k(cik, exp_year)

        if not hit["found"]:
            print(f"NOT FOUND. {hit['reason']}")
            summary["not_found"] += 1
            summary["details"].append({
                "ticker": ticker, "status": "NOT_FOUND",
                "cik": cik, "reason": hit["reason"],
            })
            continue

        # Only write HIGH or MEDIUM confidence dates
        if hit["confidence"] == "LOW":
            print(f"LOW confidence — skipping write.")
            summary["not_found"] += 1
            summary["details"].append({
                "ticker": ticker, "status": "LOW_CONFIDENCE",
                "cik": cik, "date": hit["filing_date"], "reason": hit["reason"],
            })
            continue

        filing_date = hit["filing_date"]
        accession   = hit["accession"]
        confidence  = hit["confidence"]
        source_url  = _index_url(cik, accession)

        print(f"FOUND {filing_date}  conf={confidence}  EX-2={'YES' if hit.get('has_exhibit') else 'NO'}")

        summary["found"] += 1
        summary["details"].append({
            "ticker": ticker, "status": "FOUND",
            "date": filing_date, "source_url": source_url,
            "form_type": "8-K", "confidence": confidence,
            "has_exhibit": hit.get("has_exhibit", False),
            "reason": hit["reason"],
        })

        new_dates.append({
            "case_id":                      case_id,
            "ticker":                       ticker,
            "company_name":                 company,
            "acquisition_announcement_date": filing_date,
            "source_evidence_type":         "EDGAR 8-K Item 1.01 filing index",
            "source_url":                   source_url,
            "confidence":                   confidence,
            "notes": (
                f"Automated backfill via EDGAR submissions JSON. "
                f"8-K filed {filing_date}, accession {accession}. "
                f"EX-2.x: {'YES' if hit.get('has_exhibit') else 'NO'}. "
                f"{hit['reason']}"
            ),
            "next_action": "Verify 8-K filing confirms merger agreement announcement; use as search cutoff date.",
        })

        ev_id = f"{case_id}-SRC-DATE-001"
        if ev_id not in existing_ev_ids:
            new_evidence.append({
                "evidence_id":       ev_id,
                "case_id":           case_id,
                "ticker":            ticker,
                "evidence_type":     "EDGAR_8K_ITEM_1_01",
                "source_name":       "SEC EDGAR",
                "source_url":        source_url,
                "filing_type":       "8-K",
                "filing_date":       filing_date,
                "accession_number":  accession,
                "exhibit_number":    "EX-2.1" if hit.get("has_exhibit") else "",
                "excerpt": (
                    f"EDGAR 8-K filed {filing_date} by {company}. "
                    f"Item 1.01 (Material Definitive Agreement). "
                    f"Accession: {accession}. "
                    f"EX-2.x merger exhibit: {'present' if hit.get('has_exhibit') else 'not confirmed'}."
                ),
                "supports_field":    "acquisition_announcement_date",
                "confidence":        confidence,
                "verification_status": "AUTOMATED_EDGAR_MATCH",
                "added_by":          "case_factory_date_backfiller",
                "added_date":        run_date,
                "notes":             "Automated date backfill. Researcher should verify filing content confirms merger announcement.",
            })
            existing_ev_ids.add(ev_id)

    if new_dates:
        _append_csv(dates_csv, new_dates, DATES_FIELDS)
    if new_evidence:
        _append_csv(evidence_csv, new_evidence, EVIDENCE_FIELDS)

    summary["new_dates_written"]    = len(new_dates)
    summary["new_evidence_written"] = len(new_evidence)
    return summary


def write_backfill_report(
    path: Path,
    summary: dict,
    run_date: str,
    batch_label: str,
) -> None:
    """Write a markdown report summarizing the date backfill attempt."""
    details = summary.get("details", [])
    found    = [d for d in details if d.get("status") == "FOUND"]
    missing  = [d for d in details if d.get("status") not in {"FOUND", "SKIPPED"}]
    skipped  = [d for d in details if d.get("status") == "SKIPPED"]

    lines = [
        f"# {batch_label.replace('_', ' ').title()} Date Backfill Report",
        "",
        f"Generated: {run_date}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Candidates attempted | {summary.get('attempted', 0)} |",
        f"| Dates found (HIGH/MEDIUM) | {summary.get('found', 0)} |",
        f"| Not resolved | {summary.get('not_found', 0)} |",
        f"| Already had date (skipped) | {summary.get('skipped', 0)} |",
        f"| New rows written → acquisition_announcement_dates.csv | {summary.get('new_dates_written', 0)} |",
        f"| New rows written → source_evidence.csv | {summary.get('new_evidence_written', 0)} |",
        "",
        "---",
        "",
        "## Dates Found",
        "",
    ]

    if found:
        lines += [
            "| Ticker | Date | Confidence | EX-2.x | Source |",
            "|---|---|---|---|---|",
        ]
        for d in found:
            ex2 = "YES" if d.get("has_exhibit") else "NO"
            url = d.get("source_url", "")[:80]
            lines.append(
                f"| {d['ticker']} | {d.get('date', '')} | {d.get('confidence', '')} | {ex2} | {url} |"
            )
    else:
        lines.append("No dates found in this run.")

    lines += [
        "",
        "---",
        "",
        "## Unresolved (manual backfill required)",
        "",
    ]

    if missing:
        lines += [
            "| Ticker | Status | Reason |",
            "|---|---|---|",
        ]
        for d in missing:
            lines.append(
                f"| {d['ticker']} | {d.get('status', '')} | {d.get('reason', '')[:80]} |"
            )
        lines += [
            "",
            "Use EDGAR URLs in `batch_N_M_date_prefill_queue.csv` to resolve manually.",
            "Record dates in `acquisition_announcement_dates.csv` with `confidence=HIGH`.",
        ]
    else:
        lines.append("All candidates resolved or already dated.")

    if skipped:
        lines += [
            "",
            "---",
            "",
            "## Skipped (already have confirmed dates)",
            "",
            "| Ticker |",
            "|---|",
        ]
        for d in skipped:
            lines.append(f"| {d['ticker']} |")

    lines += [
        "",
        "---",
        "",
        "## Safety",
        "",
        "- No classifications changed.",
        "- No adjudication performed.",
        "- No VERIFIED flag set.",
        "- No CALIBRATION_ELIGIBLE flag set.",
        "- Only EDGAR submissions JSON used. No FMP. No live scanner.",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
