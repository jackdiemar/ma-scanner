#!/usr/bin/env python3
"""
exception_queue_builder.py

Build an exception-first review queue for the next batch of acquired biotech cases.

For each case in scope, the script assigns a priority tier based on what pre-announcement
filing evidence exists:

  P1  — Explicit process language (unsolicited/superior/acquisition proposals, competing bids)
  P2  — Strategic-process indicators (strategic alternatives, advisor retention language)
  P3  — SC 13D filing with potential acquisition pressure
  P4  — ROFR/ROFN language (scope check required before promoting)
  P5  — Case adjudicated PRIVATE_BACKGROUND_ONLY (filing evidence is post-announcement only)
  P6  — Filing collection ran; no relevant hits found
  PENDING_FILING_COLLECTION — Date confirmed but filing collector has not yet run
  BLOCKED — No HIGH/MEDIUM announcement date; cannot run filing collector

This script does not collect filings, does not adjudicate cases, and does not classify
any new case as TRUE_PUBLIC_PRIOR_SIGNAL.

Usage:
    python3 src/historical_case_tools/exception_queue_builder.py
    python3 src/historical_case_tools/exception_queue_builder.py --start 51 --limit 20
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

DEFAULT_CANDIDATES    = HISTORICAL_DIR / "resolved_case_candidates.csv"
DEFAULT_DATES         = HISTORICAL_DIR / "acquisition_announcement_dates.csv"
DEFAULT_BATCH_RESULTS = HISTORICAL_DIR / "acquisition_prior_signal_batch_results.csv"
DEFAULT_SIGNAL_HITS   = HISTORICAL_DIR / "pre_announcement_signal_hits.csv"
DEFAULT_ADJ_QUEUE     = HISTORICAL_DIR / "prior_signal_adjudication_queue.csv"
DEFAULT_OUTPUT_CSV    = HISTORICAL_DIR / "batch_51_70_exception_queue.csv"
DEFAULT_OUTPUT_REPORT = HISTORICAL_DIR / "batch_51_70_exception_queue_report.md"

RUN_DATE = str(date.today())

# Phrase sets used to assign priority tier from signal hits
P1_SIGNAL_TYPES = {
    "unsolicited_proposal",
    "superior_proposal",
    "acquisition_proposal",
    "competing_proposal",
    "competing_bid",
    "public_competing_bid_or_process",
    "public_competing_bid_or_proposal",
}
P2_SIGNAL_TYPES = {
    "strategic_alternatives",
    "advisor_retained",
    "exploring_strategic",
}
P4_SIGNAL_TYPES = {
    "rofr",
    "rofn",
    "rights_language",
}

# SC 13D filing types that warrant P3 review
P3_FILING_TYPES = {"SC 13D", "SC 13D/A", "SC13D", "SC13D/A"}

OUTPUT_FIELDS = [
    "case_id",
    "ticker",
    "company",
    "likely_outcome_year",
    "announcement_date",
    "date_confidence",
    "needs_date_backfill",
    "filings_collected",
    "priority_tier",
    "priority_reason",
    "signal_phrase_types",
    "signal_hit_count",
    "adjudication_status",
    "next_action",
    "edgar_company_search_url",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def edgar_company_search(ticker: str) -> str:
    return (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?company=&CIK={quote(ticker)}&type=8-K&dateb=&owner=include"
        f"&count=40&search_text=&action=getcompany"
    )


def _assign_priority(
    case_id: str,
    has_date: bool,
    hits: list[dict[str, str]],
    adj_status: str,
) -> tuple[str, str]:
    """Return (priority_tier, priority_reason)."""

    if adj_status == "PRIVATE_BACKGROUND_ONLY":
        return "P5", "Adjudicated PRIVATE_BACKGROUND_ONLY — process not public before announcement."

    if not has_date:
        return "BLOCKED", "No HIGH/MEDIUM announcement date — run merger_date_prefiller first."

    if not hits:
        return "PENDING_FILING_COLLECTION", "Date confirmed; filing collector has not yet run for this case."

    # Classify highest-priority signal type found
    types_found: set[str] = set()
    for h in hits:
        for sig_type in h.get("possible_signal_type", "").split("|"):
            types_found.add(sig_type.strip())
        # Also check collector_signal_type if coming from adjudication queue
        for sig_type in h.get("collector_signal_type", "").split("|"):
            types_found.add(sig_type.strip())

    has_p1 = bool(types_found & P1_SIGNAL_TYPES)
    has_p3 = any(h.get("filing_type", "").strip() in P3_FILING_TYPES for h in hits)
    has_p2 = bool(types_found & P2_SIGNAL_TYPES)
    has_p4 = bool(types_found & P4_SIGNAL_TYPES)

    if has_p1:
        examples = sorted(types_found & P1_SIGNAL_TYPES)
        return "P1", f"Explicit process language: {', '.join(examples)}."
    if has_p3:
        return "P3", "SC 13D filing found — verify Item 4 for acquisition-pressure language."
    if has_p2:
        examples = sorted(types_found & P2_SIGNAL_TYPES)
        return "P2", f"Strategic-process indicator language: {', '.join(examples)}."
    if has_p4:
        examples = sorted(types_found & P4_SIGNAL_TYPES)
        return "P4", f"ROFR/ROFN language found — verify scope before promoting: {', '.join(examples)}."

    return "P6", "Filing collection ran; no relevant signal phrases found."


def _next_action(tier: str) -> str:
    actions = {
        "P1": "Open filing links. Verify phrase context. Adjudicate case_level_true_signal.",
        "P2": "Verify strategic alternatives language is process-specific, not boilerplate. Adjudicate.",
        "P3": "Read SC 13D Item 4. Classify as acquisition pressure or governance. Adjudicate.",
        "P4": "Confirm ROFR/ROFN scope is company-level, not asset-specific. Adjudicate.",
        "P5": "No further action — private process confirmed. Mark final in adjudication queue.",
        "P6": "No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed.",
        "PENDING_FILING_COLLECTION": "Run pre_announcement_filing_collector.py for this case.",
        "BLOCKED": "Add announcement date (HIGH or MEDIUM confidence) via date backfiller.",
    }
    return actions.get(tier, "Review case manually.")


def build_rows(
    *,
    candidates: list[dict[str, str]],
    processed_tickers: set[str],
    dates_by_case: dict[str, dict[str, str]],
    hits_by_case: dict[str, list[dict[str, str]]],
    adj_by_case: dict[str, list[dict[str, str]]],
    start: int,
    limit: int,
) -> list[dict[str, str]]:
    acquired = [
        r for r in candidates
        if r.get("likely_outcome_type", "").upper() == "ACQUIRED"
        and r.get("ticker", "").upper() not in processed_tickers
    ]

    def case_num(row: dict[str, str]) -> int:
        parts = row.get("candidate_id", "").split("-")
        return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 9999

    acquired.sort(key=case_num)

    idx_start = start - 51
    idx_start = max(idx_start, 0)
    batch = acquired[idx_start: idx_start + limit]

    rows: list[dict[str, str]] = []
    for candidate in batch:
        case_id = candidate.get("candidate_id", "").strip()
        ticker  = candidate.get("ticker", "").strip()
        company = candidate.get("company_name", "").strip()
        year    = candidate.get("likely_outcome_year", "").strip()

        date_row     = dates_by_case.get(case_id, {})
        ann_date     = date_row.get("acquisition_announcement_date", "").strip()
        confidence   = date_row.get("confidence", "").strip().upper()
        has_date     = confidence in {"HIGH", "MEDIUM"}
        needs_backfill = "TRUE" if not has_date else "FALSE"

        case_hits    = hits_by_case.get(case_id, [])
        case_adjs    = adj_by_case.get(case_id, [])

        # Determine adjudication status from adjudication queue (most recent first)
        adj_status = ""
        if case_adjs:
            statuses = [r.get("adjudication_classification", "").strip()
                        for r in case_adjs if r.get("adjudication_classification")]
            if statuses:
                adj_status = statuses[0]

        # Build combined hit list for priority analysis
        all_hits = list(case_hits) + list(case_adjs)

        tier, reason = _assign_priority(case_id, has_date, all_hits, adj_status)

        phrase_types = set()
        for h in all_hits:
            for sig_type in h.get("possible_signal_type", "").split("|"):
                t = sig_type.strip()
                if t:
                    phrase_types.add(t)
            for sig_type in h.get("collector_signal_type", "").split("|"):
                t = sig_type.strip()
                if t:
                    phrase_types.add(t)

        filings_collected = "TRUE" if case_hits or case_adjs else "FALSE"

        rows.append({
            "case_id":               case_id,
            "ticker":                ticker,
            "company":               company,
            "likely_outcome_year":   year,
            "announcement_date":     ann_date,
            "date_confidence":       confidence,
            "needs_date_backfill":   needs_backfill,
            "filings_collected":     filings_collected,
            "priority_tier":         tier,
            "priority_reason":       reason,
            "signal_phrase_types":   "|".join(sorted(phrase_types)) if phrase_types else "",
            "signal_hit_count":      str(len(case_hits)),
            "adjudication_status":   adj_status,
            "next_action":           _next_action(tier),
            "edgar_company_search_url": edgar_company_search(ticker),
            "notes":                 "",
        })

    return rows


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    tier_order = ["P1", "P2", "P3", "P4", "P5", "P6",
                  "PENDING_FILING_COLLECTION", "BLOCKED"]
    by_tier: dict[str, list[dict[str, str]]] = {t: [] for t in tier_order}
    for r in rows:
        tier = r["priority_tier"]
        by_tier.setdefault(tier, []).append(r)

    lines = [
        "# Batch 51–70 Exception Queue",
        "",
        f"Generated: {RUN_DATE}",
        "",
        "Work queue only. No cases adjudicated. Do not classify any case as TRUE_PUBLIC_PRIOR_SIGNAL.",
        "Resolve BLOCKED cases first (date backfill), then run filing collector, then review P1–P4.",
        "",
        "## Summary",
        "",
        f"- Cases in scope: {len(rows)}",
    ]

    for t in tier_order:
        count = len(by_tier.get(t, []))
        if count:
            lines.append(f"- {t}: {count}")

    lines += ["", "## Priority Queue", ""]

    for t in tier_order:
        tier_rows = by_tier.get(t, [])
        if not tier_rows:
            continue
        lines.append(f"### {t} ({len(tier_rows)} cases)")
        lines.append("")
        lines.append("| case_id | ticker | company | year | reason |")
        lines.append("|---|---|---|---|---|")
        for r in tier_rows:
            lines.append(
                f"| {r['case_id']} | {r['ticker']} | {r['company'][:35]} "
                f"| {r['likely_outcome_year']} | {r['priority_reason'][:70]} |"
            )
        lines.append("")

    lines += [
        "## Next Steps",
        "",
        "1. Resolve all BLOCKED cases: add HIGH/MEDIUM announcement dates via merger_date_prefiller queue.",
        "2. Run pre_announcement_filing_collector.py for PENDING_FILING_COLLECTION cases.",
        "3. Re-run this script after filing collection — PENDING cases will be re-classified P1–P6.",
        "4. Review P1 cases first: open filing links, read phrase context, adjudicate case_level_true_signal.",
        "5. Review P2, P3, P4 in order. P5 and P6 require minimal review.",
        "6. Add source evidence rows to acquisition_announcement_dates.csv for confirmed dates.",
        "7. Add adjudication rows to prior_signal_adjudication_queue.csv for all reviewed cases.",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    candidates    = read_csv(args.candidates)
    dates_raw     = read_csv(args.dates)
    batch_results = read_csv(args.batch_results)
    signal_hits   = read_csv(args.signal_hits)
    adj_queue     = read_csv(args.adj_queue)

    processed_tickers = {r["ticker"].upper() for r in batch_results if r.get("ticker")}
    dates_by_case     = {r["case_id"].strip(): r for r in dates_raw if r.get("case_id")}

    hits_by_case: dict[str, list[dict[str, str]]] = {}
    for h in signal_hits:
        cid = h.get("case_id", "").strip()
        if cid:
            hits_by_case.setdefault(cid, []).append(h)

    adj_by_case: dict[str, list[dict[str, str]]] = {}
    for h in adj_queue:
        cid = h.get("case_id", "").strip()
        if cid:
            adj_by_case.setdefault(cid, []).append(h)

    rows = build_rows(
        candidates=candidates,
        processed_tickers=processed_tickers,
        dates_by_case=dates_by_case,
        hits_by_case=hits_by_case,
        adj_by_case=adj_by_case,
        start=args.start,
        limit=args.limit,
    )

    write_csv(args.output, rows, OUTPUT_FIELDS)
    write_report(args.report, rows)

    tier_counts: dict[str, int] = {}
    for r in rows:
        tier_counts[r["priority_tier"]] = tier_counts.get(r["priority_tier"], 0) + 1

    print(f"Cases in scope: {len(rows)}")
    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count}")
    print(f"Queue  -> {args.output}")
    print(f"Report -> {args.report}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start",         type=int, default=51)
    parser.add_argument("--limit",         type=int, default=20)
    parser.add_argument("--candidates",    type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--dates",         type=Path, default=DEFAULT_DATES)
    parser.add_argument("--batch-results", type=Path, default=DEFAULT_BATCH_RESULTS)
    parser.add_argument("--signal-hits",   type=Path, default=DEFAULT_SIGNAL_HITS)
    parser.add_argument("--adj-queue",     type=Path, default=DEFAULT_ADJ_QUEUE)
    parser.add_argument("--output",        type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--report",        type=Path, default=DEFAULT_OUTPUT_REPORT)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
