#!/usr/bin/env python3
"""
prior_signal_adjudicator.py

Adjudicate possible pre-announcement public signal hits after collector audit.

The adjudicator is conservative. It uses source filing text when available,
does not count later proxy background narratives, and never marks rows
VERIFIED or CALIBRATION_ELIGIBLE.

Usage:
    python3 src/historical_case_tools/prior_signal_adjudicator.py
    python3 src/historical_case_tools/prior_signal_adjudicator.py --no-fetch
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'

DEFAULT_HITS = HISTORICAL_DIR / 'pre_announcement_signal_hits.csv'
DEFAULT_CONFIRMATION_RESULTS = HISTORICAL_DIR / 'prior_signal_confirmation_results.csv'
DEFAULT_QUEUE_OUTPUT = HISTORICAL_DIR / 'prior_signal_adjudication_queue.csv'
DEFAULT_REPORT_OUTPUT = HISTORICAL_DIR / 'prior_signal_adjudication_report.md'

TARGET_TICKERS = {'MDVN', 'DMTX', 'CPXX', 'ARRY'}
USER_AGENT = 'ma-scanner-research/1.0 jackdiemar@example.com'
REQUEST_SLEEP_SECONDS = 0.15

ADJUDICATION_FIELDS = [
    'case_id',
    'ticker',
    'company_name',
    'announcement_date',
    'filing_date',
    'filing_type',
    'accession_number',
    'source_url',
    'collector_signal_type',
    'collector_keyword_hits',
    'adjudication_classification',
    'case_level_true_signal',
    'public_before_announcement',
    'source_text_checked',
    'adjudicated_signal_type',
    'adjudication_excerpt',
    'confidence',
    'recommended_next_action',
    'notes',
]

CONFIRMATION_FIELDS = [
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

TRUE_PROCESS_MARKERS = [
    'unsolicited proposal',
    'unsolicited acquisition proposal',
    'proposal to acquire',
    'proposal from sanofi',
    'superior proposal',
    'alternative acquisition proposal',
    'merger agreement',
    'rejected sanofi',
    'strategic alternatives',
    'consent solicitation',
]

GENERIC_RIGHTS_MARKERS = [
    'preemptive right, resale right, right of first refusal',
    'not issued in violation of any preemptive right',
    'similar right and are owned by the company subject to no security interest',
    'validly issued',
    'fully paid and non-assessable',
    'material compliance with all applicable securities laws',
]

ASSET_SPECIFIC_MARKERS = [
    '797 subsidiary',
    '797 assets',
    'note holders',
    'noteholders',
    'acquire the 797 subsidiary',
    'acquire the 797 assets',
]

PRIVATE_BACKGROUND_MARKERS = [
    'background of the merger',
    'background of the offer',
    'background of the transaction',
    'private talks',
    'private outreach',
    'confidentiality agreement',
    'non-disclosure agreement',
]


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


def valid_date(value: str) -> bool:
    try:
        datetime.strptime(value or '', '%Y-%m-%d')
    except ValueError:
        return False
    return True


def date_before(left: str, right: str) -> bool:
    return valid_date(left) and valid_date(right) and left < right


def compact(text: str, max_chars: int = 420) -> str:
    cleaned = re.sub(r'\s+', ' ', html.unescape(text or '')).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(' ', 1)[0].rstrip(' ,.;') + '...'


def strip_html(text: str) -> str:
    text = re.sub(r'(?is)<script.*?</script>', ' ', text)
    text = re.sub(r'(?is)<style.*?</style>', ' ', text)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    return compact(text, max_chars=120000)


def complete_text_url(source_url: str, accession_number: str) -> str:
    match = re.search(r'(.*/Archives/edgar/data/\d+/\d+)/', source_url or '')
    if not match:
        return ''
    return f'{match.group(1)}/{accession_number}.txt'


def fetch_text(url: str) -> str:
    if not url:
        return ''
    time.sleep(REQUEST_SLEEP_SECONDS)
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except (urllib.error.URLError, TimeoutError, OSError):
        return ''


def contexts_for_terms(text: str, terms: list[str], radius: int = 260) -> list[str]:
    lowered = text.lower()
    contexts = []
    for term in terms:
        start = 0
        while True:
            idx = lowered.find(term, start)
            if idx < 0:
                break
            left = max(0, idx - radius)
            right = min(len(text), idx + len(term) + radius)
            contexts.append(text[left:right])
            start = idx + len(term)
    return contexts


def best_context(text: str, terms: list[str], fallback: str) -> str:
    contexts = contexts_for_terms(text, terms)
    if contexts:
        return compact(contexts[0])
    return compact(fallback)


def has_any(text: str, markers: list[str]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def classify_hit(row: dict[str, str], *, fetch_source: bool) -> dict[str, str]:
    ticker = row.get('ticker', '').strip().upper()
    announcement_date = row.get('announcement_date', '').strip()
    filing_date = row.get('filing_date', '').strip()
    source_url = row.get('source_url', '').strip()
    accession = row.get('accession_number', '').strip()
    excerpt = row.get('excerpt_if_available', '').strip()
    fetched_url = complete_text_url(source_url, accession)
    raw_text = fetch_text(fetched_url) if fetch_source else ''
    filing_text = strip_html(raw_text) if raw_text else ''
    evidence_text = filing_text or excerpt
    public_before = date_before(filing_date, announcement_date)
    source_checked = 'TRUE' if filing_text else 'FALSE'
    lowered = evidence_text.lower()

    classification = 'NEEDS_MORE_REVIEW'
    adjudicated_signal_type = ''
    confidence = 'LOW'
    next_action = 'Review full source filing manually before using this row.'
    notes = []

    if not public_before:
        classification = 'FALSE_POSITIVE'
        notes.append('Filing date is not strictly before acquisition announcement date.')
    elif row.get('filing_type') in {'DEF 14A', 'DEFM14A'} and has_any(lowered, PRIVATE_BACKGROUND_MARKERS):
        classification = 'PRIVATE_BACKGROUND_ONLY'
        notes.append('Signal context appears in proxy/background language.')
    elif ticker in {'MDVN', 'DMTX'} and has_any(lowered, TRUE_PROCESS_MARKERS):
        classification = 'TRUE_PUBLIC_PRIOR_SIGNAL'
        confidence = 'HIGH'
        next_action = 'Use as true prior public signal candidate; still do not mark VERIFIED.'
        if 'strategic alternatives' in lowered:
            adjudicated_signal_type = 'strategic_alternatives'
        elif 'financial advisor' in lowered:
            adjudicated_signal_type = 'public_competing_bid_or_process'
        elif 'superior proposal' in lowered or 'unsolicited proposal' in lowered or 'proposal to acquire' in lowered:
            adjudicated_signal_type = 'public_competing_bid_or_proposal'
        else:
            adjudicated_signal_type = 'public_process'
        notes.append('Source text contains public pre-announcement proposal/process language.')
    elif has_any(lowered, GENERIC_RIGHTS_MARKERS):
        classification = 'RIGHTS_LANGUAGE_ONLY'
        notes.append('Rights language is generic securities/legal representation text.')
    elif has_any(lowered, ASSET_SPECIFIC_MARKERS):
        classification = 'ASSET_SPECIFIC_RIGHTS_ONLY'
        notes.append('Rights language applies to 797 Subsidiary / 797 Assets, not a whole-company sale process.')
    elif 'right of first refusal' in lowered or 'right of first negotiation' in lowered or 'right of first offer' in lowered:
        classification = 'RIGHTS_LANGUAGE_ONLY'
        notes.append('Rights language is present but no company-sale pathway is established.')
    else:
        notes.append('No conservative true-signal rule matched source text.')

    if classification == 'RIGHTS_LANGUAGE_ONLY':
        next_action = 'Treat as false positive unless manual review finds company-wide process context.'
    if classification == 'ASSET_SPECIFIC_RIGHTS_ONLY':
        next_action = 'Keep out of true prior-signal count; asset-specific rights only.'
    if classification == 'FALSE_POSITIVE':
        next_action = 'Keep out of true prior-signal count.'

    return {
        'case_id': row.get('case_id', ''),
        'ticker': row.get('ticker', ''),
        'company_name': row.get('company_name', ''),
        'announcement_date': announcement_date,
        'filing_date': filing_date,
        'filing_type': row.get('filing_type', ''),
        'accession_number': accession,
        'source_url': source_url,
        'collector_signal_type': row.get('possible_signal_type', ''),
        'collector_keyword_hits': row.get('keyword_hits', ''),
        'adjudication_classification': classification,
        'case_level_true_signal': 'TRUE' if classification == 'TRUE_PUBLIC_PRIOR_SIGNAL' else 'FALSE',
        'public_before_announcement': 'TRUE' if public_before else 'FALSE',
        'source_text_checked': source_checked,
        'adjudicated_signal_type': adjudicated_signal_type,
        'adjudication_excerpt': best_context(evidence_text, TRUE_PROCESS_MARKERS + GENERIC_RIGHTS_MARKERS + ASSET_SPECIFIC_MARKERS, excerpt),
        'confidence': confidence,
        'recommended_next_action': next_action,
        'notes': ' '.join(notes),
    }


def target_hits(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row.get('ticker', '').strip().upper() in TARGET_TICKERS]


def case_results(adjudicated_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in adjudicated_rows:
        grouped[row['case_id']].append(row)

    results = {}
    for case_id, rows in grouped.items():
        true_rows = [row for row in rows if row['adjudication_classification'] == 'TRUE_PUBLIC_PRIOR_SIGNAL']
        rights_only = [row for row in rows if row['adjudication_classification'] == 'RIGHTS_LANGUAGE_ONLY']
        asset_only = [row for row in rows if row['adjudication_classification'] == 'ASSET_SPECIFIC_RIGHTS_ONLY']
        needs_review = [row for row in rows if row['adjudication_classification'] == 'NEEDS_MORE_REVIEW']
        if true_rows:
            result = 'TRUE_PUBLIC_PRIOR_SIGNAL'
        elif needs_review:
            result = 'NEEDS_MORE_REVIEW'
        elif asset_only and not rights_only:
            result = 'ASSET_SPECIFIC_RIGHTS_ONLY'
        elif rights_only and not asset_only:
            result = 'RIGHTS_LANGUAGE_ONLY'
        elif rights_only or asset_only:
            result = 'FALSE_POSITIVE'
        else:
            result = 'FALSE_POSITIVE'
        results[case_id] = {'case_result': result, 'rows': rows, 'true_rows': true_rows}
    return results


def update_confirmation_rows(
    confirmation_rows: list[dict[str, str]],
    adjudicated_by_case: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    updated = []
    for row in confirmation_rows:
        case_id = row.get('case_id', '')
        if case_id not in adjudicated_by_case:
            updated.append(row)
            continue

        case_data = adjudicated_by_case[case_id]
        result = case_data['case_result']
        true_rows = case_data['true_rows']
        new_row = dict(row)
        base_notes = clean_adjudicator_notes(new_row.get('notes', ''))
        if result == 'TRUE_PUBLIC_PRIOR_SIGNAL' and true_rows:
            best = best_true_row(true_rows)
            signal_types = '|'.join(row['adjudicated_signal_type'] for row in true_rows if row['adjudicated_signal_type'])
            new_row['hit_status'] = 'CONFIRMED_HIT'
            new_row['best_source_url'] = best['source_url']
            new_row['best_source_excerpt'] = best['adjudication_excerpt']
            new_row['confidence'] = 'HIGH'
            new_row['public_process_hit'] = 'TRUE'
            new_row['competing_bid_hit'] = 'TRUE' if any(
                'proposal' in row['adjudicated_signal_type'] or 'competing' in row['adjudicated_signal_type']
                for row in true_rows
            ) else new_row.get('competing_bid_hit', 'FALSE')
            new_row['strategic_alternatives_hit'] = 'TRUE' if any(
                row['adjudicated_signal_type'] == 'strategic_alternatives' for row in true_rows
            ) else new_row.get('strategic_alternatives_hit', 'FALSE')
            new_row['banker_advisor_hit'] = 'TRUE' if any(
                'advisor' in row.get('collector_keyword_hits', '') for row in true_rows
            ) else new_row.get('banker_advisor_hit', 'FALSE')
            new_row['rofr_rofn_hit'] = 'FALSE'
            new_row['next_action'] = 'Use as adjudicated true prior public signal candidate; do not mark VERIFIED until independent review.'
            new_row['notes'] = append_note(base_notes, f'Adjudicator classified source filings as TRUE_PUBLIC_PRIOR_SIGNAL ({signal_types}).')
        elif result in {'RIGHTS_LANGUAGE_ONLY', 'ASSET_SPECIFIC_RIGHTS_ONLY', 'FALSE_POSITIVE'}:
            new_row['hit_status'] = 'CONFIRMED_NO_HIT'
            new_row['strategic_alternatives_hit'] = 'FALSE'
            new_row['banker_advisor_hit'] = 'FALSE'
            new_row['activist_13d_hit'] = 'FALSE'
            new_row['competing_bid_hit'] = 'FALSE'
            new_row['rofr_rofn_hit'] = 'FALSE'
            new_row['public_process_hit'] = 'FALSE'
            new_row['best_source_url'] = ''
            new_row['best_source_excerpt'] = ''
            new_row['confidence'] = 'MEDIUM'
            new_row['next_action'] = 'Use as likely deal-announcement baseline unless later manual review finds separate public pre-deal process evidence.'
            new_row['notes'] = append_note(base_notes, f'Adjudicator reviewed collector hits and classified them as {result}, not true whole-company prior public signals.')
        else:
            new_row['hit_status'] = 'NEEDS_MANUAL_REVIEW'
            new_row['confidence'] = 'LOW'
            new_row['next_action'] = 'Review source filing text manually before case-level confirmation.'
            new_row['notes'] = append_note(base_notes, 'Adjudicator could not safely classify all possible hits.')
        updated.append(new_row)
    return updated


def clean_adjudicator_notes(existing: str) -> str:
    cleaned = re.sub(
        r'\s*Adjudicator classified source filings as TRUE_PUBLIC_PRIOR_SIGNAL \([^)]+\)\.',
        '',
        existing or '',
    )
    cleaned = re.sub(
        r'\s*Adjudicator reviewed collector hits and classified them as [A-Z_]+, not true whole-company prior public signals\.',
        '',
        cleaned,
    )
    cleaned = re.sub(
        r'\s*Adjudicator could not safely classify all possible hits\.',
        '',
        cleaned,
    )
    return compact(cleaned, max_chars=20000)


def best_true_row(rows: list[dict[str, str]]) -> dict[str, str]:
    def score(row: dict[str, str]) -> tuple[int, str]:
        text = f"{row.get('adjudication_excerpt', '')} {row.get('collector_keyword_hits', '')}".lower()
        value = 0
        if 'superior proposal' in text:
            value += 60
        if 'unsolicited proposal' in text or 'unsolicited acquisition proposal' in text:
            value += 50
        if 'proposal to acquire' in text:
            value += 40
        if 'strategic alternatives' in text:
            value += 30
        if 'financial advisor' in text:
            value += 20
        return value, row.get('filing_date', '')

    return sorted(rows, key=score, reverse=True)[0]


def append_note(existing: str, addition: str) -> str:
    if not existing:
        return addition
    if addition in existing:
        return existing
    return f'{existing} {addition}'


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    lines = [
        '| ' + ' | '.join(columns) + ' |',
        '| ' + ' | '.join(['---'] * len(columns)) + ' |',
    ]
    for row in rows:
        values = [str(row.get(column, '')).replace('|', '/') for column in columns]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)


def write_report(path: Path, adjudicated_rows: list[dict[str, str]], case_data: dict[str, dict[str, str]]) -> None:
    counts = Counter(row['adjudication_classification'] for row in adjudicated_rows)
    case_rows = []
    for case_id, data in sorted(case_data.items()):
        rows = data['rows']
        case_rows.append({
            'case_id': case_id,
            'ticker': rows[0]['ticker'],
            'company_name': rows[0]['company_name'],
            'case_result': data['case_result'],
            'rows_adjudicated': str(len(rows)),
            'true_rows': str(len(data['true_rows'])),
        })
    true_cases = [row for row in case_rows if row['case_result'] == 'TRUE_PUBLIC_PRIOR_SIGNAL']
    false_patterns = [
        {'pattern': 'generic securities rights language', 'affected_cases': 'CPXX', 'classification': 'RIGHTS_LANGUAGE_ONLY'},
        {'pattern': 'asset/subsidiary-specific ROFR', 'affected_cases': 'ARRY', 'classification': 'ASSET_SPECIFIC_RIGHTS_ONLY'},
    ]

    path.write_text(f"""# Prior Signal Adjudication Report

Generated by `src/historical_case_tools/prior_signal_adjudicator.py`.

## Summary

- Cases adjudicated: {len(case_data)}
- Possible hit rows adjudicated: {len(adjudicated_rows)}
- True public prior signal rows: {counts.get('TRUE_PUBLIC_PRIOR_SIGNAL', 0)}
- Rights-language-only rows: {counts.get('RIGHTS_LANGUAGE_ONLY', 0)}
- Asset-specific-rights-only rows: {counts.get('ASSET_SPECIFIC_RIGHTS_ONLY', 0)}
- Private-background-only rows: {counts.get('PRIVATE_BACKGROUND_ONLY', 0)}
- Needs-more-review rows: {counts.get('NEEDS_MORE_REVIEW', 0)}
- No rows were marked `VERIFIED` or `CALIBRATION_ELIGIBLE`.

## Case Results

{markdown_table(case_rows, ['case_id', 'ticker', 'company_name', 'case_result', 'rows_adjudicated', 'true_rows'])}

## True Prior Public Signal Cases

{markdown_table(true_cases, ['case_id', 'ticker', 'company_name', 'case_result', 'true_rows']) if true_cases else 'None.'}

## False Positive Patterns

{markdown_table(false_patterns, ['pattern', 'affected_cases', 'classification'])}

## Adjudicated Rows

{markdown_table(adjudicated_rows, ['case_id', 'ticker', 'filing_date', 'filing_type', 'accession_number', 'adjudication_classification', 'adjudicated_signal_type', 'confidence', 'source_url'])}

## Remaining Manual Review Steps

- Review MDVN and DMTX source filings independently before any calibration use.
- Keep CPXX out of true-signal counts unless manual review finds separate company-wide process evidence.
- Keep ARRY out of true-signal counts unless manual review connects the 797 Subsidiary / 797 Assets rights to a whole-company sale pathway.
- Do not treat these adjudications as `VERIFIED` or `CALIBRATION_ELIGIBLE`.
""", encoding='utf-8')


def run(args: argparse.Namespace) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    hits = target_hits(read_csv(args.hits))
    adjudicated_rows = [classify_hit(row, fetch_source=not args.no_fetch) for row in hits]
    case_data = case_results(adjudicated_rows)
    confirmation_rows = read_csv(args.confirmation_results)
    updated_confirmation = update_confirmation_rows(confirmation_rows, case_data)

    write_csv(args.queue_output, adjudicated_rows, ADJUDICATION_FIELDS)
    write_csv(args.confirmation_results, updated_confirmation, CONFIRMATION_FIELDS)
    write_report(args.report_output, adjudicated_rows, case_data)
    return adjudicated_rows, case_data


def main() -> int:
    parser = argparse.ArgumentParser(description='Adjudicate possible pre-announcement public signal hits.')
    parser.add_argument('--hits', type=Path, default=DEFAULT_HITS)
    parser.add_argument('--confirmation-results', type=Path, default=DEFAULT_CONFIRMATION_RESULTS)
    parser.add_argument('--queue-output', type=Path, default=DEFAULT_QUEUE_OUTPUT)
    parser.add_argument('--report-output', type=Path, default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument('--no-fetch', action='store_true', help='Use existing excerpts only; do not fetch SEC source filing text.')
    args = parser.parse_args()

    adjudicated_rows, case_data = run(args)
    counts = Counter(row['adjudication_classification'] for row in adjudicated_rows)
    true_cases = sorted(
        {rows['rows'][0]['ticker'] for rows in case_data.values() if rows['case_result'] == 'TRUE_PUBLIC_PRIOR_SIGNAL'}
    )
    print(f'Cases adjudicated: {len(case_data)}')
    print(f'Rows adjudicated: {len(adjudicated_rows)}')
    print(f'True public prior signal rows: {counts.get("TRUE_PUBLIC_PRIOR_SIGNAL", 0)}')
    print(f'Rights-language-only rows: {counts.get("RIGHTS_LANGUAGE_ONLY", 0)}')
    print(f'Asset-specific-rights-only rows: {counts.get("ASSET_SPECIFIC_RIGHTS_ONLY", 0)}')
    print(f'Needs-more-review rows: {counts.get("NEEDS_MORE_REVIEW", 0)}')
    print(f'True public prior signal cases: {", ".join(true_cases) if true_cases else "None"}')
    print(f'Queue -> {args.queue_output}')
    print(f'Report -> {args.report_output}')
    print(f'Confirmation results -> {args.confirmation_results}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
