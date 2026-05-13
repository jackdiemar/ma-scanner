#!/usr/bin/env python3
"""
prior_signal_confirmation_runner.py

Confirm, deny, or route manual review for prior-public-signal candidates.

The runner is conservative by design. It only counts public signals dated before
the acquisition announcement. Later proxy background descriptions of private
talks do not count as prior public signals.

Usage:
    python3 src/historical_case_tools/prior_signal_confirmation_runner.py
    python3 src/historical_case_tools/prior_signal_confirmation_runner.py --no-edgar
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'

DEFAULT_CANDIDATES = HISTORICAL_DIR / 'prior_public_signal_candidates.csv'
DEFAULT_QUEUE = HISTORICAL_DIR / 'acquisition_verification_queue.csv'
DEFAULT_SOURCE_EVIDENCE = HISTORICAL_DIR / 'source_evidence.csv'
DEFAULT_HISTORICAL_QUERIES = HISTORICAL_DIR / 'historical_source_queries.md'
DEFAULT_ACQUISITION_DATES = HISTORICAL_DIR / 'acquisition_announcement_dates.csv'
DEFAULT_RESULTS = HISTORICAL_DIR / 'prior_signal_confirmation_results.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'prior_signal_confirmation_report.md'
DEFAULT_PRIOR_REPORT = HISTORICAL_DIR / 'prior_public_signal_report.md'

TARGET_TICKERS = [
    'MDVN',
    'CPXX',
    'RLYP',
    'VTAE',
    'CLCD',
    'DMTX',
    'AVXS',
    'CASC',
    'RXDX',
    'ALDR',
    'ARRY',
    'CMTA',
    'LOXO',
    'NITE',
    'ONCE',
]

RESULT_FIELDS = [
    'case_id',
    'ticker',
    'company_name',
    'acquisition_announcement_date',
    'search_window_start',
    'search_window_end',
    'searched_signal_types',
    'strategic_alternatives_hit',
    'banker_advisor_hit',
    'activist_13d_hit',
    'competing_bid_hit',
    'rofr_rofn_hit',
    'public_process_hit',
    'hit_status',
    'best_source_url',
    'best_source_excerpt',
    'confidence',
    'next_action',
    'notes',
]

SEARCH_TYPES = [
    'strategic_alternatives',
    'banker_advisor',
    'activist_13d',
    'competing_bid',
    'rofr_rofn',
    'public_process',
]

SEARCH_DEFS = {
    'strategic_alternatives': {
        'hit_field': 'strategic_alternatives_hit',
        'forms': '8-K,10-Q,10-K',
        'query': '"strategic alternatives" OR "review of strategic alternatives" OR "maximize shareholder value"',
        'required_terms': ['strategic alternatives', 'review of strategic alternatives', 'maximize shareholder value'],
    },
    'banker_advisor': {
        'hit_field': 'banker_advisor_hit',
        'forms': '8-K,10-Q,10-K',
        'query': '"financial advisor" OR "retained" OR "engaged"',
        'required_terms': ['financial advisor', 'retained', 'engaged'],
    },
    'activist_13d': {
        'hit_field': 'activist_13d_hit',
        'forms': 'SC 13D,SC 13D/A',
        'query': '"Item 4" OR "maximize shareholder value" OR "sale of the company" OR "strategic alternatives"',
        'required_terms': ['item 4', 'maximize shareholder value', 'sale of the company', 'strategic alternatives'],
    },
    'competing_bid': {
        'hit_field': 'competing_bid_hit',
        'forms': '8-K,SC 13D,SC 13D/A,SC TO-T,SC TO-I',
        'query': '"publicly announced" "proposal" OR "unsolicited proposal" OR "competing bid"',
        'required_terms': ['publicly announced', 'proposal', 'unsolicited proposal', 'competing bid'],
    },
    'rofr_rofn': {
        'hit_field': 'rofr_rofn_hit',
        'forms': '8-K,10-K,10-Q,EX-10',
        'query': '"right of first refusal" OR "right of first negotiation" OR "right of first offer" OR "option to acquire"',
        'required_terms': ['right of first refusal', 'right of first negotiation', 'right of first offer', 'option to acquire'],
    },
    'public_process': {
        'hit_field': 'public_process_hit',
        'forms': '8-K,10-Q,10-K,SC 13D,SC 13D/A',
        'query': '"announced" "strategic review" OR "publicly disclosed" "strategic alternatives" OR "prior failed process"',
        'required_terms': ['announced', 'strategic review', 'publicly disclosed', 'prior failed process'],
    },
}

PUBLIC_MARKERS = [
    'publicly announced',
    'publicly disclosed',
    'issued a press release',
    'press release',
    'announced',
]

PRIVATE_ONLY_MARKERS = [
    'private outreach',
    'private talks',
    'confidentiality agreement',
    'non-disclosure agreement',
    'due diligence',
    'later proxy background',
]

EDGAR_SEARCH_URL = 'https://efts.sec.gov/LATEST/search-index'
USER_AGENT = 'ma-scanner-research/1.0 jackdiemar@example.com'
REQUEST_SLEEP_SECONDS = 0.15
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


@dataclass(frozen=True)
class EdgarHit:
    signal_type: str
    filing_date: str
    source_url: str
    excerpt: str


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def compact(text: str, max_chars: int = 360) -> str:
    cleaned = re.sub(r'\s+', ' ', text or '').strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(' ', 1)[0].rstrip(' ,.;') + '...'


def valid_date(value: str) -> bool:
    if not DATE_RE.match(value or ''):
        return False
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def year_from_date(value: str) -> int | None:
    if not value:
        return None
    match = re.search(r'\d{4}', value)
    return int(match.group(0)) if match else None


def prior_start(acquisition_date: str, queue_year: str = '') -> str:
    year = year_from_date(acquisition_date) or year_from_date(queue_year)
    if year is None:
        return ''
    return f'{max(2015, year - 3)}-01-01'


def manual_window_end(acquisition_date: str, queue_year: str = '') -> str:
    if valid_date(acquisition_date):
        return acquisition_date
    year = year_from_date(queue_year)
    return f'{year}-12-31' if year else ''


def date_before(left: str, right: str) -> bool:
    return valid_date(left) and valid_date(right) and left < right


def index_by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    indexed = {}
    for row in rows:
        value = row.get(key, '').strip()
        if value and value not in indexed:
            indexed[value] = row
    return indexed


def group_by(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        value = row.get(key, '').strip()
        if value:
            grouped.setdefault(value, []).append(row)
    return grouped


def target_rows(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    by_ticker = {row.get('ticker', '').strip().upper(): row for row in candidates}
    return [by_ticker[ticker] for ticker in TARGET_TICKERS if ticker in by_ticker]


def apply_acquisition_date_backfills(
    candidates: list[dict[str, str]],
    date_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    dates_by_id = index_by(date_rows, 'case_id')
    updated = []
    for row in candidates:
        case_id = row.get('case_id', '').strip()
        date_row = dates_by_id.get(case_id, {})
        backfilled_date = date_row.get('acquisition_announcement_date', '').strip()
        if not row.get('acquisition_announcement_date', '').strip() and valid_date(backfilled_date):
            row = dict(row)
            row['acquisition_announcement_date'] = backfilled_date
            row['notes'] = ' '.join([
                row.get('notes', ''),
                f"Acquisition announcement date backfilled from acquisition_announcement_dates.csv ({date_row.get('confidence', '')} confidence).",
            ]).strip()
        updated.append(row)
    return updated


def hit_fields() -> dict[str, str]:
    return {definition['hit_field']: 'FALSE' for definition in SEARCH_DEFS.values()}


def classify_local_candidate(row: dict[str, str]) -> tuple[dict[str, str], str, str, str]:
    hits = hit_fields()
    possible = row.get('possible_prior_signal', '').strip()
    signal_type = row.get('prior_signal_type', '').lower()
    notes = f"{row.get('notes', '')} {row.get('best_source_excerpt', '')}".lower()
    source_url = row.get('source_url_if_found', '').strip()
    signal_date = row.get('prior_signal_date', '').strip()

    if possible != 'POSSIBLE_FOUND_PUBLIC' or not source_url:
        return hits, '', '', ''
    if not any(marker in notes for marker in PUBLIC_MARKERS):
        return hits, '', '', ''
    if any(marker in notes for marker in PRIVATE_ONLY_MARKERS):
        return hits, '', '', ''

    if 'strategic' in signal_type:
        hits['strategic_alternatives_hit'] = 'TRUE'
    if 'advisor' in signal_type or 'banker' in signal_type:
        hits['banker_advisor_hit'] = 'TRUE'
    if '13d' in signal_type or 'activist' in signal_type:
        hits['activist_13d_hit'] = 'TRUE'
    if 'bid' in signal_type or 'outreach' in signal_type or 'proposal' in notes:
        hits['competing_bid_hit'] = 'TRUE'
    if 'rofr' in signal_type or 'rofn' in signal_type or 'option' in signal_type:
        hits['rofr_rofn_hit'] = 'TRUE'
    hits['public_process_hit'] = 'TRUE'
    return hits, source_url, row.get('notes', ''), signal_date


def manual_query(ticker: str, company: str, signal_type: str, start: str, end: str) -> str:
    definition = SEARCH_DEFS[signal_type]
    query = f'{ticker} "{company}" {definition["query"]}'
    return (
        f'{signal_type}: {EDGAR_SEARCH_URL}?'
        + urlencode({
            'q': query,
            'forms': definition['forms'],
            'dateRange': 'custom',
            'startdt': start,
            'enddt': end,
        })
    )


def manual_queries(ticker: str, company: str, start: str, end: str) -> str:
    if not start or not end:
        return 'Exact acquisition announcement date required before hit/no-hit search window can be locked.'
    return ' || '.join(manual_query(ticker, company, signal_type, start, end) for signal_type in SEARCH_TYPES)


def extract_edgar_hits(payload: dict, signal_type: str, acquisition_date: str) -> list[EdgarHit]:
    hits = []
    candidates = payload.get('hits', {}).get('hits', [])
    for item in candidates:
        source = item.get('_source', {}) if isinstance(item, dict) else {}
        filing_date = (
            source.get('file_date')
            or source.get('filing_date')
            or source.get('filedAt')
            or source.get('period_ending')
            or ''
        )
        filing_date = str(filing_date)[:10]
        if not date_before(filing_date, acquisition_date):
            continue

        excerpt = compact(
            source.get('summary')
            or source.get('text')
            or source.get('display_names')
            or item.get('highlight', {})
            or ''
        )
        source_url = source.get('url') or source.get('adsh') or source.get('accession') or ''
        if source_url and source_url.startswith('/'):
            source_url = f'https://www.sec.gov{source_url}'
        if not source_url:
            source_url = EDGAR_SEARCH_URL
        if excerpt and not contains_signal_terms(excerpt, signal_type):
            continue
        hits.append(EdgarHit(signal_type=signal_type, filing_date=filing_date, source_url=source_url, excerpt=excerpt))
    return hits


def contains_signal_terms(text: str, signal_type: str) -> bool:
    lowered = text.lower()
    terms = SEARCH_DEFS[signal_type]['required_terms']
    return any(term in lowered for term in terms)


def edgar_search(ticker: str, company: str, signal_type: str, start: str, end: str) -> tuple[list[EdgarHit], str]:
    definition = SEARCH_DEFS[signal_type]
    query = f'{ticker} "{company}" {definition["query"]}'
    params = {
        'q': query,
        'forms': definition['forms'],
        'dateRange': 'custom',
        'startdt': start,
        'enddt': end,
    }
    url = f'{EDGAR_SEARCH_URL}?{urlencode(params)}'
    time.sleep(REQUEST_SLEEP_SECONDS)
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=12) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
    return extract_edgar_hits(payload, signal_type, end), url


def attempt_edgar_searches(row: dict[str, str], start: str, end: str, *, enabled: bool) -> tuple[dict[str, str], EdgarHit | None, list[str], str]:
    hits = hit_fields()
    if not enabled:
        return hits, None, [], 'EDGAR search disabled by --no-edgar.'

    ticker = row.get('ticker', '').strip()
    company = row.get('company_name', '').strip()
    queries = []
    errors = []
    best_hit = None
    for signal_type in SEARCH_TYPES:
        try:
            found, url = edgar_search(ticker, company, signal_type, start, end)
            queries.append(f'{signal_type}: {url}')
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            errors.append(f'{signal_type}: {exc}')
            continue
        if found:
            hits[SEARCH_DEFS[signal_type]['hit_field']] = 'TRUE'
            if best_hit is None:
                best_hit = found[0]
    if errors and not queries:
        return hits, best_hit, queries, 'EDGAR unavailable; generated manual review queries instead.'
    if errors:
        return hits, best_hit, queries, 'Partial EDGAR search completed; some signal searches failed.'
    return hits, best_hit, queries, 'EDGAR search completed.'


def any_hit(hits: dict[str, str]) -> bool:
    return any(value == 'TRUE' for value in hits.values())


def merge_hits(base: dict[str, str], extra: dict[str, str]) -> dict[str, str]:
    merged = dict(base)
    for key, value in extra.items():
        if value == 'TRUE':
            merged[key] = 'TRUE'
    return merged


def row_status(date_missing: bool, hits: dict[str, str], edgar_attempt_note: str, edgar_enabled: bool) -> str:
    if any_hit(hits):
        return 'CONFIRMED_HIT'
    if date_missing:
        return 'DATE_MISSING'
    if edgar_enabled and edgar_attempt_note == 'EDGAR search completed.':
        return 'CONFIRMED_NO_HIT'
    return 'NEEDS_MANUAL_REVIEW'


def next_action(status: str) -> str:
    if status == 'CONFIRMED_HIT':
        return 'Open source, extract contemporaneous public excerpt, and keep below VERIFIED until independent review.'
    if status == 'CONFIRMED_NO_HIT':
        return 'Use as likely deal-announcement baseline unless later manual proxy review finds a public pre-deal source.'
    if status == 'DATE_MISSING':
        return 'Confirm exact acquisition announcement date from merger 8-K or tender-offer filing before hit/no-hit search.'
    return 'Run the generated SEC queries manually and record hit/no-hit evidence with source URL and excerpt.'


def build_result(
    row: dict[str, str],
    queue: dict[str, dict[str, str]],
    source_rows: dict[str, list[dict[str, str]]],
    historical_queries_loaded: bool,
    *,
    edgar_enabled: bool,
) -> dict[str, str]:
    case_id = row.get('case_id', '')
    queue_row = queue.get(case_id, {})
    acquisition_date = row.get('acquisition_announcement_date', '').strip()
    start = prior_start(acquisition_date, queue_row.get('likely_outcome_year', ''))
    end = manual_window_end(acquisition_date, queue_row.get('likely_outcome_year', ''))
    date_missing = not valid_date(acquisition_date)

    local_hits, local_url, local_excerpt, local_signal_date = classify_local_candidate(row)
    if local_signal_date and valid_date(acquisition_date) and not date_before(local_signal_date, acquisition_date):
        local_hits = hit_fields()
        local_url = ''
        local_excerpt = ''

    edgar_hits = hit_fields()
    edgar_best = None
    edgar_queries: list[str] = []
    edgar_note = 'EDGAR not attempted because acquisition date is missing.'
    if not date_missing and not any_hit(local_hits):
        edgar_hits, edgar_best, edgar_queries, edgar_note = attempt_edgar_searches(row, start, end, enabled=edgar_enabled)
    elif not date_missing and any_hit(local_hits):
        edgar_note = 'EDGAR not attempted because local source-backed public hit already exists.'

    hits = merge_hits(local_hits, edgar_hits)
    status = row_status(date_missing, hits, edgar_note, edgar_enabled)
    query_text = ' || '.join(edgar_queries) if edgar_queries else manual_queries(row.get('ticker', ''), row.get('company_name', ''), start, end)
    best_url = local_url or (edgar_best.source_url if edgar_best else '')
    best_excerpt = local_excerpt or (edgar_best.excerpt if edgar_best else '')

    notes = []
    if query_text:
        notes.append(f'Manual/EDGAR queries: {query_text}')
    if source_rows.get(case_id):
        notes.append(f'Local source_evidence rows: {len(source_rows[case_id])}')
    if not historical_queries_loaded:
        notes.append('historical_source_queries.md missing.')
    notes.append(edgar_note)
    if row.get('notes'):
        notes.append(row['notes'])

    confidence = 'MEDIUM' if status == 'CONFIRMED_HIT' and local_url else 'LOW'
    if status == 'CONFIRMED_NO_HIT':
        confidence = 'LOW'
    if status == 'DATE_MISSING':
        confidence = 'LOW'

    return {
        'case_id': case_id,
        'ticker': row.get('ticker', ''),
        'company_name': row.get('company_name', ''),
        'acquisition_announcement_date': acquisition_date,
        'search_window_start': start,
        'search_window_end': acquisition_date if valid_date(acquisition_date) else end,
        'searched_signal_types': '|'.join(SEARCH_TYPES),
        'hit_status': status,
        'best_source_url': best_url,
        'best_source_excerpt': compact(best_excerpt),
        'confidence': confidence,
        'next_action': next_action(status),
        'notes': ' '.join(notes),
        **hits,
    }


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    lines = [
        '| ' + ' | '.join(columns) + ' |',
        '| ' + ' | '.join(['---'] * len(columns)) + ' |',
    ]
    for row in rows:
        values = [str(row.get(column, '')).replace('|', '/') for column in columns]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)


def best_candidates(rows: list[dict[str, str]], limit: int = 5) -> list[dict[str, str]]:
    ranked = []
    for row in rows:
        score = 0
        if row['hit_status'] == 'CONFIRMED_HIT':
            score += 100
        if row['competing_bid_hit'] == 'TRUE':
            score += 20
        if row['strategic_alternatives_hit'] == 'TRUE':
            score += 15
        if row['banker_advisor_hit'] == 'TRUE':
            score += 12
        if row['activist_13d_hit'] == 'TRUE':
            score += 12
        if row['rofr_rofn_hit'] == 'TRUE':
            score += 8
        ranked.append((score, row['ticker'], row))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [row for score, _, row in ranked if score > 0][:limit]


def baseline_cases(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row['hit_status'] == 'CONFIRMED_NO_HIT']


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row['hit_status'] for row in rows)
    best = best_candidates(rows)
    baselines = baseline_cases(rows)
    manual = [row for row in rows if row['hit_status'] in {'DATE_MISSING', 'NEEDS_MANUAL_REVIEW'}]
    baseline_empty_note = (
        'None confirmed as no-hit yet because some targets lack exact acquisition dates or require manual EDGAR review.'
        if counts.get('DATE_MISSING', 0)
        else 'None confirmed as no-hit yet because live EDGAR hit/no-hit searches require manual review.'
    )

    path.write_text(f"""# Prior Signal Confirmation Report

Generated by `src/historical_case_tools/prior_signal_confirmation_runner.py`.

## Summary

- Cases checked: {len(rows)}
- Confirmed hits: {counts.get('CONFIRMED_HIT', 0)}
- Confirmed no-hits: {counts.get('CONFIRMED_NO_HIT', 0)}
- Needs manual review: {counts.get('NEEDS_MANUAL_REVIEW', 0)}
- Date missing: {counts.get('DATE_MISSING', 0)}
- No rows were marked `VERIFIED`.

## Best 5 True Pre-Deal Signal Candidates

{markdown_table(best, ['case_id', 'ticker', 'company_name', 'acquisition_announcement_date', 'hit_status', 'best_source_url', 'best_source_excerpt', 'confidence']) if best else 'None confirmed from available local evidence and EDGAR attempts.'}

## Likely Deal-Announcement Baselines

{markdown_table(baselines, ['case_id', 'ticker', 'company_name', 'acquisition_announcement_date', 'hit_status', 'confidence']) if baselines else baseline_empty_note}

## Manual Review Queue

{markdown_table(manual, ['case_id', 'ticker', 'company_name', 'acquisition_announcement_date', 'search_window_start', 'search_window_end', 'hit_status', 'next_action'])}

## All Results

{markdown_table(rows, ['case_id', 'ticker', 'company_name', 'hit_status', 'strategic_alternatives_hit', 'banker_advisor_hit', 'activist_13d_hit', 'competing_bid_hit', 'rofr_rofn_hit', 'public_process_hit', 'confidence'])}

## Rules Applied

- Counted only public signals before the acquisition announcement date.
- Excluded private talks disclosed later in proxy background sections.
- Did not invent sources or infer hits from generated search targets.
- Used `DATE_MISSING` when exact announcement date was not available, because no-hit confirmation requires a locked cutoff.
""")


def update_prior_report(path: Path, rows: list[dict[str, str]]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding='utf-8')
    marker = '\n## Confirmation Runner Addendum\n'
    text = text.split(marker, 1)[0].rstrip()
    counts = Counter(row['hit_status'] for row in rows)
    best = best_candidates(rows)
    baselines = baseline_cases(rows)
    baseline_empty_note = (
        'None confirmed as no-hit yet because some targets lack exact acquisition dates or require manual EDGAR review.'
        if counts.get('DATE_MISSING', 0)
        else 'None confirmed as no-hit yet because live EDGAR hit/no-hit searches require manual review.'
    )
    addendum = f"""

## Confirmation Runner Addendum

Updated by `src/historical_case_tools/prior_signal_confirmation_runner.py`.

- Cases checked: {len(rows)}
- Confirmed hits: {counts.get('CONFIRMED_HIT', 0)}
- Confirmed no-hits: {counts.get('CONFIRMED_NO_HIT', 0)}
- Needs manual review: {counts.get('NEEDS_MANUAL_REVIEW', 0)}
- Date missing: {counts.get('DATE_MISSING', 0)}

### Best 5 True Pre-Deal Signal Candidates

{markdown_table(best, ['case_id', 'ticker', 'company_name', 'acquisition_announcement_date', 'hit_status', 'confidence']) if best else 'None confirmed from available local evidence and EDGAR attempts.'}

### Likely Deal-Announcement Baselines

{markdown_table(baselines, ['case_id', 'ticker', 'company_name', 'acquisition_announcement_date', 'hit_status', 'confidence']) if baselines else baseline_empty_note}
"""
    path.write_text(text + addendum, encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description='Confirm prior public signal hits/no-hits for top acquired historical targets.')
    parser.add_argument('--candidates-input', default=str(DEFAULT_CANDIDATES))
    parser.add_argument('--queue-input', default=str(DEFAULT_QUEUE))
    parser.add_argument('--source-evidence-input', default=str(DEFAULT_SOURCE_EVIDENCE))
    parser.add_argument('--historical-queries-input', default=str(DEFAULT_HISTORICAL_QUERIES))
    parser.add_argument('--acquisition-dates-input', default=str(DEFAULT_ACQUISITION_DATES))
    parser.add_argument('--output', default=str(DEFAULT_RESULTS))
    parser.add_argument('--report-output', default=str(DEFAULT_REPORT))
    parser.add_argument('--prior-report', default=str(DEFAULT_PRIOR_REPORT))
    parser.add_argument('--no-edgar', action='store_true', help='Skip live EDGAR search attempts and write manual queries only.')
    args = parser.parse_args()

    candidates = target_rows(read_csv(Path(args.candidates_input)))
    candidates = apply_acquisition_date_backfills(candidates, read_csv(Path(args.acquisition_dates_input)))
    queue = index_by(read_csv(Path(args.queue_input)), 'candidate_id')
    source_rows = group_by(read_csv(Path(args.source_evidence_input)), 'case_id')
    historical_queries_loaded = Path(args.historical_queries_input).exists()
    rows = [
        build_result(
            row,
            queue,
            source_rows,
            historical_queries_loaded,
            edgar_enabled=not args.no_edgar,
        )
        for row in candidates
    ]

    write_csv(Path(args.output), rows, RESULT_FIELDS)
    write_report(Path(args.report_output), rows)
    update_prior_report(Path(args.prior_report), rows)

    counts = Counter(row['hit_status'] for row in rows)
    print(f'Cases checked: {len(rows)}')
    print(f'Confirmed hits: {counts.get("CONFIRMED_HIT", 0)}')
    print(f'Confirmed no-hits: {counts.get("CONFIRMED_NO_HIT", 0)}')
    print(f'Needs manual review: {counts.get("NEEDS_MANUAL_REVIEW", 0)}')
    print(f'Date missing: {counts.get("DATE_MISSING", 0)}')
    print(f'Results -> {args.output}')
    print(f'Report -> {args.report_output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
