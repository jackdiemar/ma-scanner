#!/usr/bin/env python3
"""
acquisition_case_verifier.py

Build a first-wave verification workflow for resolved historical acquisition
candidates. This tool creates deterministic EDGAR search targets and source
evidence target rows. It does not mark any case VERIFIED, PARTIAL, or
calibration-ready.

Usage:
    python src/historical_case_tools/acquisition_case_verifier.py
    python src/historical_case_tools/acquisition_case_verifier.py --limit 25
"""

import argparse
import csv
from collections import Counter
from pathlib import Path
from urllib.parse import quote_plus


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'
DEFAULT_INPUT = HISTORICAL_DIR / 'resolved_case_candidates.csv'
DEFAULT_QUEUE = HISTORICAL_DIR / 'acquisition_verification_queue.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'acquisition_verification_report.md'
DEFAULT_EVIDENCE_TARGETS = HISTORICAL_DIR / 'acquisition_source_evidence_targets.csv'

QUEUE_FIELDS = [
    'candidate_id',
    'ticker',
    'company_name',
    'likely_outcome_year',
    'merger_8k_query',
    'proxy_query',
    'background_section_needed',
    'prior_process_signal_query',
    'deal_terms_needed',
    'price_window_needed',
    'recommended_status',
    'next_best_action',
    'notes',
]

EVIDENCE_TARGET_FIELDS = [
    'evidence_target_id',
    'candidate_id',
    'ticker',
    'company_name',
    'target_type',
    'filing_type',
    'query_url',
    'supports_field',
    'required_for_partial',
    'expected_evidence',
    'verification_status',
    'notes',
]

VERIFYING_TARGETS = [
    (
        'MERGER_8K',
        '8-K',
        '"agreement and plan of merger" "per share"',
        'deal_announcement_date|acquirer|deal_price_or_consideration|deal_terms',
        'TRUE',
        'Merger agreement 8-K with Item 1.01 and deal consideration language.',
    ),
    (
        'MERGER_PROXY',
        'DEFM14A,DEF 14A',
        '"background of the merger" OR "reasons for the merger"',
        'proxy_background|deal_premium_pct|process_timeline',
        'TRUE',
        'Proxy background section with board process, outreach, competing bids, and premium if disclosed.',
    ),
    (
        'PRIOR_PROCESS_8K',
        '8-K,10-Q,10-K',
        '"strategic alternatives" OR "financial advisor" OR "review of strategic alternatives"',
        'prior_process_signal|observation_date|had_prior_process_signal',
        'FALSE',
        'Pre-announcement process language, banker/advisor language, or no-hit confirmation.',
    ),
    (
        'PRIOR_13D',
        'SC 13D,SC 13D/A',
        '"Item 4" OR "maximize shareholder value" OR "strategic alternatives"',
        'activist_involvement|item4_intent',
        'FALSE',
        'Any pre-deal Item 4 activist pressure or sale-process language.',
    ),
    (
        'ROFR_ROFN_EXHIBIT',
        '8-K,10-K,10-Q,EX-10',
        '"right of first refusal" OR "right of first negotiation" OR "option to acquire"',
        'rofr_scope|transaction_rights',
        'FALSE',
        'Prior collaboration/license exhibit with ROFR, ROFN, ROFO, or option rights.',
    ),
    (
        'PRICE_WINDOW',
        'PRICE_DATA',
        '',
        'price_before_signal|price_30d_after|price_90d_after|max_drawdown_after_signal',
        'TRUE',
        'Adjusted-close price window after the verified observation date.',
    ),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def year_bounds(year: str) -> tuple[str, str]:
    clean = ''.join(ch for ch in str(year or '') if ch.isdigit())
    if len(clean) >= 4:
        return f'{clean[:4]}-01-01', f'{clean[:4]}-12-31'
    return '2015-01-01', '2024-12-31'


def prior_bounds(year: str) -> tuple[str, str]:
    clean = ''.join(ch for ch in str(year or '') if ch.isdigit())
    if len(clean) < 4:
        return '2015-01-01', '2024-12-31'
    event_year = int(clean[:4])
    return f'{max(2015, event_year - 3)}-01-01', f'{event_year}-12-31'


def edgar_query(ticker: str, company: str, phrase: str, forms: str, start: str, end: str) -> str:
    query = f'{ticker} "{company}" {phrase}'
    return (
        'https://efts.sec.gov/LATEST/search-index?'
        f'q={quote_plus(query)}&forms={quote_plus(forms)}&dateRange=custom&startdt={start}&enddt={end}'
    )


def manual_research_reason(row: dict[str, str]) -> str:
    text = f"{row.get('company_name', '')} {row.get('outcome_source_hint', '')} {row.get('notes', '')}".lower()
    if any(term in text for term in {'plc', 'foreign', '6-k', 'circular'}):
        return 'Foreign issuer or circular/6-K path may not have a standard DEFM14A background section.'
    if 'tender offer' in text:
        return 'Tender-offer path may require SC TO-T/SC TO-I plus Schedule 14D-9 rather than a standard merger proxy.'
    if 'check' in text:
        return 'Source hint includes unresolved detail that should be checked before field extraction.'
    return ''


def recommended_status(row: dict[str, str]) -> str:
    year = row.get('likely_outcome_year', '').strip()
    ticker = row.get('ticker', '').strip()
    company = row.get('company_name', '').strip()
    if not year.isdigit() or not ticker or not company:
        return 'BAD_TARGET'
    if manual_research_reason(row):
        return 'NEEDS_MANUAL_RESEARCH'
    return 'PARTIAL_READY'


def next_action(status: str) -> str:
    if status == 'PARTIAL_READY':
        return 'Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section.'
    if status == 'NEEDS_MANUAL_RESEARCH':
        return 'Check EDGAR manually for tender-offer, 6-K, proxy, or foreign-issuer transaction filings before extracting fields.'
    if status == 'BAD_TARGET':
        return 'Confirm ticker, company, and acquisition year before doing source work.'
    return 'Keep as CANDIDATE until primary filing evidence is opened and excerpted.'


def queue_row(row: dict[str, str]) -> dict[str, str]:
    start, end = year_bounds(row['likely_outcome_year'])
    prior_start, prior_end = prior_bounds(row['likely_outcome_year'])
    status = recommended_status(row)
    ticker = row['ticker']
    company = row['company_name']
    merger_8k = edgar_query(
        ticker,
        company,
        '"agreement and plan of merger" "per share"',
        '8-K,SC TO-T,SC TO-I',
        start,
        end,
    )
    proxy = edgar_query(
        ticker,
        company,
        '"background of the merger" OR "reasons for the merger" OR "premium"',
        'DEFM14A,DEF 14A,SC TO-T,SC TO-I',
        start,
        end,
    )
    prior_process = edgar_query(
        ticker,
        company,
        '"strategic alternatives" OR "financial advisor" OR "prior outreach" OR "competing bids" OR "Item 4" OR "right of first refusal" OR "right of first negotiation"',
        '8-K,10-Q,10-K,SC 13D,SC 13D/A,DEFM14A,DEF 14A',
        prior_start,
        prior_end,
    )
    manual_reason = manual_research_reason(row)
    notes = manual_reason or row.get('notes') or 'Candidate only. No source-backed fields populated by this factory run.'
    return {
        'candidate_id': row['candidate_id'],
        'ticker': ticker,
        'company_name': company,
        'likely_outcome_year': row['likely_outcome_year'],
        'merger_8k_query': merger_8k,
        'proxy_query': proxy,
        'background_section_needed': 'TRUE',
        'prior_process_signal_query': prior_process,
        'deal_terms_needed': 'deal_announcement_date|acquirer|deal_price_or_consideration|premium_if_available|consideration_type',
        'price_window_needed': 'TRUE',
        'recommended_status': status,
        'next_best_action': next_action(status),
        'notes': notes,
    }


def evidence_targets_for(row: dict[str, str]) -> list[dict[str, str]]:
    ticker = row['ticker']
    company = row['company_name']
    start, end = year_bounds(row['likely_outcome_year'])
    prior_start, prior_end = prior_bounds(row['likely_outcome_year'])
    rows = []
    for index, (target_type, filing_type, phrase, supports, required, expected) in enumerate(VERIFYING_TARGETS, start=1):
        if target_type == 'PRICE_WINDOW':
            query = f'https://finance.yahoo.com/quote/{ticker}/history/'
            notes = 'Use price_window_fetcher.py after observation_date is verified; use fallback source for delisted ticker if yfinance has no data.'
        elif target_type in {'PRIOR_PROCESS_8K', 'PRIOR_13D', 'ROFR_ROFN_EXHIBIT'}:
            query = edgar_query(ticker, company, phrase, filing_type, prior_start, prior_end)
            notes = 'Backward-looking process-signal search. A no-hit result must be recorded before classifying as no prior signal.'
        else:
            query = edgar_query(ticker, company, phrase, filing_type, start, end)
            notes = 'Outcome-first verification target. Do not promote without primary filing URL, date, accession, and excerpt.'
        rows.append({
            'evidence_target_id': f'{row["candidate_id"]}-EVT-{index:03d}',
            'candidate_id': row['candidate_id'],
            'ticker': ticker,
            'company_name': company,
            'target_type': target_type,
            'filing_type': filing_type,
            'query_url': query,
            'supports_field': supports,
            'required_for_partial': required,
            'expected_evidence': expected,
            'verification_status': 'VERIFY_REQUIRED',
            'notes': notes,
        })
    return rows


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    lines = [
        '| ' + ' | '.join(columns) + ' |',
        '| ' + ' | '.join(['---'] * len(columns)) + ' |',
    ]
    for row in rows:
        lines.append('| ' + ' | '.join(str(row.get(column, '')) for column in columns) + ' |')
    return '\n'.join(lines)


def write_report(path: Path, queue_rows: list[dict[str, str]]) -> None:
    status_counts = Counter(row['recommended_status'] for row in queue_rows)
    top_rows = [
        {
            'candidate_id': row['candidate_id'],
            'ticker': row['ticker'],
            'company_name': row['company_name'],
            'year': row['likely_outcome_year'],
            'recommended_status': row['recommended_status'],
            'first_action': row['next_best_action'],
        }
        for row in queue_rows
    ]
    easy_rows = [
        {
            'ticker': row['ticker'],
            'company_name': row['company_name'],
            'year': row['likely_outcome_year'],
            'why': 'Clear year and standard domestic merger/proxy verification path.',
        }
        for row in queue_rows
        if row['recommended_status'] == 'PARTIAL_READY'
    ]
    manual_rows = [
        {
            'ticker': row['ticker'],
            'company_name': row['company_name'],
            'year': row['likely_outcome_year'],
            'reason': row['notes'],
        }
        for row in queue_rows
        if row['recommended_status'] == 'NEEDS_MANUAL_RESEARCH'
    ]
    count_rows = [{'recommended_status': status, 'count': status_counts.get(status, 0)}
                  for status in ['PARTIAL_READY', 'NEEDS_MANUAL_RESEARCH', 'CANDIDATE', 'BAD_TARGET']]

    path.write_text(f"""# Acquisition Verification Report

Generated by `src/historical_case_tools/acquisition_case_verifier.py`.

## Summary

- Acquisition candidates queued: {len(queue_rows)}
- No rows were marked `VERIFIED`, `PARTIAL`, or `CALIBRATION_ELIGIBLE`.
- `PARTIAL_READY` is a workflow recommendation only. It means the case looks clean enough to start primary-source verification.
- `source_evidence.csv` was not updated because this run generated targets rather than opened and excerpted primary filings.

## Count By Recommended Status

{markdown_table(count_rows, ['recommended_status', 'count'])}

## Top 25 Acquisition Verification Queue

{markdown_table(top_rows, ['candidate_id', 'ticker', 'company_name', 'year', 'recommended_status', 'first_action'])}

## Easiest To Move Toward PARTIAL

{markdown_table(easy_rows, ['ticker', 'company_name', 'year', 'why'])}

## Needs Manual Research

{markdown_table(manual_rows, ['ticker', 'company_name', 'year', 'reason'])}

## Evidence Gaps

- Merger 8-K accession number, filing URL, filing date, acquirer, and consideration.
- DEFM14A / DEF 14A or tender-offer filing with background section.
- Proxy background review for prior outreach, competing bids, banker/advisor involvement, activist pressure, and ROFR/ROFN or option rights.
- Premium, if disclosed.
- Price window after the verified observation date.
""")


def main() -> int:
    parser = argparse.ArgumentParser(description='Build acquisition verification workflow targets.')
    parser.add_argument('--input', default=str(DEFAULT_INPUT))
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--queue-output', default=str(DEFAULT_QUEUE))
    parser.add_argument('--report-output', default=str(DEFAULT_REPORT))
    parser.add_argument('--evidence-targets-output', default=str(DEFAULT_EVIDENCE_TARGETS))
    args = parser.parse_args()

    candidates = [
        row for row in read_csv(Path(args.input))
        if row.get('likely_outcome_type') == 'ACQUIRED'
    ][:args.limit]

    queue_rows = [queue_row(row) for row in candidates]
    evidence_rows = []
    for row in candidates:
        evidence_rows.extend(evidence_targets_for(row))

    write_csv(Path(args.queue_output), queue_rows, QUEUE_FIELDS)
    write_csv(Path(args.evidence_targets_output), evidence_rows, EVIDENCE_TARGET_FIELDS)
    write_report(Path(args.report_output), queue_rows)

    counts = Counter(row['recommended_status'] for row in queue_rows)
    print(f'Queued {len(queue_rows)} acquisition candidates -> {args.queue_output}')
    for status in ['PARTIAL_READY', 'NEEDS_MANUAL_RESEARCH', 'CANDIDATE', 'BAD_TARGET']:
        print(f'{status}: {counts.get(status, 0)}')
    print(f'Evidence targets: {len(evidence_rows)} -> {args.evidence_targets_output}')
    print(f'Report -> {args.report_output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
