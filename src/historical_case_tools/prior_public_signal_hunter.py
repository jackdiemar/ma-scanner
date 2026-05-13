#!/usr/bin/env python3
"""
prior_public_signal_hunter.py

Build a conservative prior-public-signal review queue for acquired historical
cases. The hunter uses local source-backed findings first, then creates
deterministic EDGAR search targets for cases where no prior public signal has
been found yet.

It does not mark any case VERIFIED. Private proxy background negotiations are
not treated as public pre-announcement signals unless the local evidence says
the event was publicly announced or disclosed before the final deal.

Usage:
    python3 src/historical_case_tools/prior_public_signal_hunter.py
    python3 src/historical_case_tools/prior_public_signal_hunter.py --limit 50
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote_plus


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'

DEFAULT_RESOLVED = HISTORICAL_DIR / 'resolved_case_candidates.csv'
DEFAULT_QUEUE = HISTORICAL_DIR / 'acquisition_verification_queue.csv'
DEFAULT_SOURCE_EVIDENCE = HISTORICAL_DIR / 'source_evidence.csv'
DEFAULT_BACKGROUND = HISTORICAL_DIR / 'acquisition_background_findings.csv'
DEFAULT_OBSERVATIONS = HISTORICAL_DIR / 'observation_date_candidates.csv'
DEFAULT_HISTORICAL_QUERIES = HISTORICAL_DIR / 'historical_source_queries.md'
DEFAULT_OUTPUT = HISTORICAL_DIR / 'prior_public_signal_candidates.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'prior_public_signal_report.md'

OUTPUT_FIELDS = [
    'case_id',
    'ticker',
    'company_name',
    'acquisition_announcement_date',
    'possible_prior_signal',
    'prior_signal_type',
    'prior_signal_date',
    'source_url_if_found',
    'source_query_if_not_found',
    'confidence',
    'recommended_next_action',
    'notes',
]

SIGNAL_TYPE_QUERY_TERMS = [
    (
        'strategic alternatives 8-K',
        '"strategic alternatives" OR "review of strategic alternatives"',
        '8-K,10-Q,10-K',
    ),
    (
        'retained banker/advisor',
        '"retained" "financial advisor" OR "engaged" "financial advisor"',
        '8-K,10-Q,10-K',
    ),
    (
        'SC 13D / 13D/A Item 4 sale pressure',
        '"Item 4" OR "maximize shareholder value" OR "sale of the company"',
        'SC 13D,SC 13D/A',
    ),
    (
        'public competing bid / outreach',
        '"publicly announced" "proposal" OR "unsolicited proposal" OR "competing bid"',
        '8-K,SC 13D,SC 13D/A,DEFM14A,DEF 14A,SC TO-T,SC TO-I',
    ),
    (
        'ROFR / ROFN / option rights',
        '"right of first refusal" OR "right of first negotiation" OR "option to acquire"',
        '8-K,10-K,10-Q,EX-10',
    ),
    (
        'public review process language',
        '"announced" "strategic review" OR "publicly disclosed" "strategic alternatives"',
        '8-K,10-Q,10-K',
    ),
    (
        'prior failed process',
        '"terminated" "strategic alternatives" OR "concluded" "strategic review"',
        '8-K,10-Q,10-K',
    ),
]

FOUND_PUBLIC_VALUES = {'FOUND_PUBLIC', 'POSSIBLE_FOUND_PUBLIC'}
NO_HIT_VALUES = {'NONE_FOUND', 'NO_LOCAL_PRIOR_SIGNAL_FOUND'}
PRIORITY_RANK = {'HIGH': 0, 'MED': 1, 'MEDIUM': 1, 'LOW': 2}
CONFIDENCE_RANK = {'HIGH': 0, 'MEDIUM': 1, 'MED': 1, 'LOW': 2, '': 3}
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def compact(text: str, max_chars: int = 320) -> str:
    cleaned = re.sub(r'\s+', ' ', text or '').strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(' ', 1)[0].rstrip(' ,.;') + '...'


def year_from(value: str) -> int | None:
    match = re.search(r'\d{4}', value or '')
    if not match:
        return None
    return int(match.group(0))


def case_number(case_id: str) -> int:
    match = re.search(r'RHC-(\d+)', case_id or '')
    if not match:
        return 999999
    return int(match.group(1))


def prior_bounds(year: str) -> tuple[str, str]:
    event_year = year_from(year)
    if event_year is None:
        return '2015-01-01', '2024-12-31'
    return f'{max(2015, event_year - 3)}-01-01', f'{event_year}-12-31'


def edgar_query(ticker: str, company: str, phrase: str, forms: str, start: str, end: str) -> str:
    query = f'{ticker} "{company}" {phrase}'
    return (
        'https://efts.sec.gov/LATEST/search-index?'
        f'q={quote_plus(query)}&forms={quote_plus(forms)}&dateRange=custom&startdt={start}&enddt={end}'
    )


def generated_queries(row: dict[str, str]) -> str:
    ticker = row.get('ticker', '').strip()
    company = row.get('company_name', '').strip()
    start, end = prior_bounds(row.get('likely_outcome_year', ''))
    targets = []
    for label, phrase, forms in SIGNAL_TYPE_QUERY_TERMS:
        targets.append(f'{label}: {edgar_query(ticker, company, phrase, forms, start, end)}')
    return ' || '.join(targets)


def query_fallback(row: dict[str, str]) -> str:
    existing = [
        row.get('prior_process_signal_query', ''),
        row.get('prior_13d_query', ''),
        row.get('prior_rofr_exhibit_query', ''),
    ]
    present = [value for value in existing if value]
    if present:
        labels = ['prior_process', 'prior_13d', 'prior_rofr']
        return ' || '.join(f'{label}: {value}' for label, value in zip(labels, present) if value)
    return generated_queries(row)


def index_one(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row.get(key, '').strip()
        if value and value not in indexed:
            indexed[value] = row
    return indexed


def source_rows_by_case(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        case_id = row.get('case_id', '').strip()
        if case_id:
            grouped.setdefault(case_id, []).append(row)
    return grouped


def acquisition_date(case_id: str, background: dict[str, dict[str, str]], sources: dict[str, list[dict[str, str]]]) -> str:
    for row in sources.get(case_id, []):
        if row.get('evidence_type') == '8K_MERGER' and row.get('source_url') != 'VERIFY_REQUIRED':
            filing_date = row.get('filing_date', '').strip()
            if DATE_RE.match(filing_date):
                return filing_date
    bg_row = background.get(case_id, {})
    return bg_row.get('first_public_acquisition_announcement_date', '').strip()


def background_signal(case_id: str, background: dict[str, dict[str, str]], observations: dict[str, dict[str, str]]) -> dict[str, str] | None:
    obs = observations.get(case_id)
    bg = background.get(case_id)
    row = obs or bg
    if not row:
        return None
    status = (row.get('prior_process_signal') or '').strip().upper()
    if status in FOUND_PUBLIC_VALUES:
        return {
            'possible_prior_signal': 'POSSIBLE_FOUND_PUBLIC',
            'prior_signal_type': row.get('prior_process_signal_type', ''),
            'prior_signal_date': row.get('prior_process_signal_date', ''),
            'source_url_if_found': row.get('source_url') or row.get('proxy_source_url', ''),
            'confidence': row.get('confidence', '') or 'MEDIUM',
            'notes': compact(row.get('source_excerpt') or row.get('relevant_excerpt') or row.get('observation_date_reasoning', '')),
        }
    if status in NO_HIT_VALUES:
        return {
            'possible_prior_signal': 'NO_LOCAL_PRIOR_SIGNAL_FOUND',
            'prior_signal_type': row.get('prior_process_signal_type', 'none found'),
            'prior_signal_date': '',
            'source_url_if_found': '',
            'confidence': row.get('confidence', '') or 'LOW',
            'notes': compact(row.get('observation_date_reasoning') or row.get('remaining_gaps') or ''),
        }
    return None


def source_signal(case_id: str, sources: dict[str, list[dict[str, str]]]) -> dict[str, str] | None:
    for row in sources.get(case_id, []):
        notes = f"{row.get('notes', '')} {row.get('excerpt', '')}".lower()
        public_marker = any(term in notes for term in ['publicly announcing', 'publicly announced', 'issued a press release'])
        found_marker = 'prior_process_signal=found_public' in notes
        if public_marker and found_marker and row.get('source_url') != 'VERIFY_REQUIRED':
            return {
                'possible_prior_signal': 'POSSIBLE_FOUND_PUBLIC',
                'prior_signal_type': 'public competing bid / outreach',
                'prior_signal_date': '',
                'source_url_if_found': row.get('source_url', ''),
                'confidence': row.get('confidence', '') or 'MEDIUM',
                'notes': compact(row.get('excerpt', '')),
            }
    return None


def recommended_next_action(signal_status: str, has_background: bool) -> str:
    if signal_status == 'POSSIBLE_FOUND_PUBLIC':
        return 'Open contemporaneous public source for the prior signal, confirm date and excerpt, then keep label below VERIFIED until independently checked.'
    if signal_status == 'NO_LOCAL_PRIOR_SIGNAL_FOUND':
        return 'Run targeted pre-announcement EDGAR searches and record manual no-hit evidence before treating acquisition announcement as first public signal.'
    if has_background:
        return 'Review background section plus targeted pre-announcement EDGAR searches for public signal categories.'
    return 'Start with merger proxy or Schedule 14D-9 background, then run targeted pre-announcement EDGAR searches.'


def candidate_sort_key(row: dict[str, str]) -> tuple[int, int, int, str]:
    return (
        PRIORITY_RANK.get(row.get('priority', '').upper(), 9),
        year_from(row.get('likely_outcome_year', '')) or 9999,
        case_number(row.get('candidate_id', '')),
        row.get('ticker', ''),
    )


def top_acquired(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    acquired = [row for row in rows if row.get('likely_outcome_type') == 'ACQUIRED']
    return sorted(acquired, key=candidate_sort_key)[:limit]


def report_rank_key(row: dict[str, str]) -> tuple[int, int, int, str]:
    status_rank = {
        'POSSIBLE_FOUND_PUBLIC': 0,
        'SEARCH_TARGET_ONLY': 1,
        'NO_LOCAL_PRIOR_SIGNAL_FOUND': 2,
    }
    return (
        status_rank.get(row.get('possible_prior_signal', ''), 9),
        CONFIDENCE_RANK.get(row.get('confidence', '').upper(), 3),
        case_number(row.get('case_id', '')),
        row.get('ticker', ''),
    )


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    lines = [
        '| ' + ' | '.join(columns) + ' |',
        '| ' + ' | '.join(['---'] * len(columns)) + ' |',
    ]
    for row in rows:
        values = [str(row.get(column, '')).replace('|', '/') for column in columns]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)


def write_report(path: Path, rows: list[dict[str, str]], checked_count: int, historical_queries_loaded: bool) -> None:
    counts = Counter(row['possible_prior_signal'] for row in rows)
    found = [row for row in rows if row['possible_prior_signal'] == 'POSSIBLE_FOUND_PUBLIC']
    top_targets = sorted(rows, key=report_rank_key)[:15]
    blockers = []
    if counts.get('SEARCH_TARGET_ONLY', 0):
        blockers.append('Most rows still require manual EDGAR no-hit or hit confirmation.')
    if any(not row.get('acquisition_announcement_date') for row in rows):
        blockers.append('Some acquisition announcement dates are only known by year from resolved_case_candidates.csv.')
    if not historical_queries_loaded:
        blockers.append('historical_source_queries.md was not available; script used company-specific query generation only.')
    if not blockers:
        blockers.append('None from local file generation; source confirmation remains required before any VERIFIED label.')

    count_rows = [
        {'possible_prior_signal': key, 'count': counts.get(key, 0)}
        for key in ['POSSIBLE_FOUND_PUBLIC', 'SEARCH_TARGET_ONLY', 'NO_LOCAL_PRIOR_SIGNAL_FOUND']
    ]

    path.write_text(f"""# Prior Public Signal Hunter Report

Generated by `src/historical_case_tools/prior_public_signal_hunter.py`.

## Summary

- Cases checked: {checked_count}
- Possible prior-public-signal cases found from local evidence: {len(found)}
- No rows were marked `VERIFIED`.
- Private proxy background negotiations are excluded unless the local evidence says the signal was public before the final acquisition announcement.

## Count By Conservative Label

{markdown_table(count_rows, ['possible_prior_signal', 'count'])}

## Possible Found Cases

{markdown_table(found, ['case_id', 'ticker', 'company_name', 'acquisition_announcement_date', 'prior_signal_type', 'prior_signal_date', 'confidence', 'recommended_next_action'])}

## Top 15 MDVN-Like Targets

{markdown_table(top_targets, ['case_id', 'ticker', 'company_name', 'acquisition_announcement_date', 'possible_prior_signal', 'prior_signal_type', 'prior_signal_date', 'confidence', 'recommended_next_action'])}

## Blockers

{chr(10).join(f'- {blocker}' for blocker in blockers)}

## Method

- Reviewed `acquisition_verification_queue.csv`, `resolved_case_candidates.csv`, `source_evidence.csv`, `acquisition_background_findings.csv`, `observation_date_candidates.csv`, and `historical_source_queries.md`.
- Used source-backed background findings first.
- Generated targeted EDGAR search strings for strategic alternatives 8-Ks, retained advisors, SC 13D Item 4 sale pressure, public bids, ROFR/ROFN or option rights, public review-process language, and prior failed processes.
""")


def build_rows(args: argparse.Namespace) -> tuple[list[dict[str, str]], int, bool]:
    resolved = read_csv(Path(args.resolved_input))
    queue = index_one(read_csv(Path(args.queue_input)), 'candidate_id')
    source_rows = source_rows_by_case(read_csv(Path(args.source_evidence_input)))
    background = index_one(read_csv(Path(args.background_input)), 'case_id')
    observations = index_one(read_csv(Path(args.observation_input)), 'case_id')
    historical_queries_loaded = Path(args.historical_queries_input).exists()

    candidates = top_acquired(resolved, args.limit)
    rows = []
    for candidate in candidates:
        case_id = candidate.get('candidate_id', '').strip()
        queue_row = queue.get(case_id, {})
        merged_candidate = {**candidate, **{k: v for k, v in queue_row.items() if v}}
        bg_result = background_signal(case_id, background, observations)
        source_result = source_signal(case_id, source_rows)
        result = bg_result or source_result
        if result is None:
            result = {
                'possible_prior_signal': 'SEARCH_TARGET_ONLY',
                'prior_signal_type': 'targeted public pre-announcement signal search',
                'prior_signal_date': '',
                'source_url_if_found': '',
                'confidence': 'LOW',
                'notes': 'No local source-backed prior public signal found yet. Search target generated only.',
            }

        has_background = case_id in background or any(
            row.get('evidence_type') == 'PROXY_SA_LANGUAGE'
            for row in source_rows.get(case_id, [])
        )
        rows.append({
            'case_id': case_id,
            'ticker': candidate.get('ticker', ''),
            'company_name': candidate.get('company_name', ''),
            'acquisition_announcement_date': acquisition_date(case_id, background, source_rows),
            'possible_prior_signal': result['possible_prior_signal'],
            'prior_signal_type': result['prior_signal_type'],
            'prior_signal_date': result['prior_signal_date'],
            'source_url_if_found': result['source_url_if_found'],
            'source_query_if_not_found': '' if result['source_url_if_found'] else query_fallback(merged_candidate),
            'confidence': result['confidence'],
            'recommended_next_action': recommended_next_action(result['possible_prior_signal'], has_background),
            'notes': compact(result['notes'] or candidate.get('notes', '')),
        })
    return rows, len(candidates), historical_queries_loaded


def main() -> int:
    parser = argparse.ArgumentParser(description='Build prior-public-signal hunter outputs for acquired historical cases.')
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--resolved-input', default=str(DEFAULT_RESOLVED))
    parser.add_argument('--queue-input', default=str(DEFAULT_QUEUE))
    parser.add_argument('--source-evidence-input', default=str(DEFAULT_SOURCE_EVIDENCE))
    parser.add_argument('--background-input', default=str(DEFAULT_BACKGROUND))
    parser.add_argument('--observation-input', default=str(DEFAULT_OBSERVATIONS))
    parser.add_argument('--historical-queries-input', default=str(DEFAULT_HISTORICAL_QUERIES))
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--report-output', default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    rows, checked_count, historical_queries_loaded = build_rows(args)
    write_csv(Path(args.output), rows, OUTPUT_FIELDS)
    write_report(Path(args.report_output), rows, checked_count, historical_queries_loaded)

    counts = Counter(row['possible_prior_signal'] for row in rows)
    print(f'Cases checked: {checked_count}')
    print(f'Possible prior-public-signal cases found: {counts.get("POSSIBLE_FOUND_PUBLIC", 0)}')
    print(f'Candidates -> {args.output}')
    print(f'Report -> {args.report_output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
