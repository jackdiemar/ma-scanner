#!/usr/bin/env python3
"""
pre_announcement_filing_collector.py

Collect and screen SEC filings before acquisition announcements for historical
acquired cases.

The collector is conservative. It screens only filings dated before the
announcement cutoff, avoids later proxy background narratives as public prior
signals, and never marks rows VERIFIED, CALIBRATION_ELIGIBLE, or confirmed
no-hit.

Usage:
    python3 src/historical_case_tools/pre_announcement_filing_collector.py
    python3 src/historical_case_tools/pre_announcement_filing_collector.py --no-api
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'

DEFAULT_ACQUISITION_DATES = HISTORICAL_DIR / 'acquisition_announcement_dates.csv'
DEFAULT_CONFIRMATION_RESULTS = HISTORICAL_DIR / 'prior_signal_confirmation_results.csv'
DEFAULT_QUEUE = HISTORICAL_DIR / 'acquisition_verification_queue.csv'
DEFAULT_SOURCE_EVIDENCE = HISTORICAL_DIR / 'source_evidence.csv'
DEFAULT_TARGETS_OUTPUT = HISTORICAL_DIR / 'pre_announcement_filing_targets.csv'
DEFAULT_HITS_OUTPUT = HISTORICAL_DIR / 'pre_announcement_signal_hits.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'pre_announcement_filing_report.md'
DEFAULT_CONFIRMATION_REPORT = HISTORICAL_DIR / 'prior_signal_confirmation_report.md'

EDGAR_TICKERS_JSON = 'https://www.sec.gov/files/company_tickers.json'
EDGAR_SUBMISSIONS = 'https://data.sec.gov/submissions'
EDGAR_ARCHIVE = 'https://www.sec.gov/Archives/edgar/data'
USER_AGENT = 'ma-scanner-research/1.0 jackdiemar@example.com'
REQUEST_SLEEP_SECONDS = 0.15
WINDOW_DAYS = 548

TARGET_FORMS = {
    '8-K',
    'SC 13D',
    'SC 13D/A',
    'DEF 14A',
    'DEFM14A',
    'S-4',
    '424B3',
    '10-K',
    '10-Q',
}

ROW_FIELDS = [
    'case_id',
    'ticker',
    'company_name',
    'announcement_date',
    'filing_date',
    'filing_type',
    'accession_number',
    'source_url',
    'possible_signal_type',
    'keyword_hits',
    'excerpt_if_available',
    'confidence',
    'recommended_status',
]

# Delisted tickers are not consistently available in current SEC ticker JSON.
# These CIKs are source-backed from local SEC archive evidence or SEC filing
# history already used in the historical-case workflow.
CIK_OVERRIDES = {
    'MDVN': '0001011835',
    'CPXX': '0001327467',
    'RLYP': '0001416792',
    'VTAE': '0001426800',
    'CLCD': '0001556263',
    'DMTX': '0001592288',
    'AVXS': '0001652923',
    'CASC': '0001060736',
    'RXDX': '0001557421',
    'ALDR': '0001423824',
    'ARRY': '0001100412',
    'CMTA': '0001647320',
    'LOXO': '0001581720',
    'NITE': '0001711675',
    'ONCE': '0001609351',
}

SIGNAL_KEYWORDS = {
    'strategic_alternatives': [
        'strategic alternatives',
        'review of strategic alternatives',
    ],
    'retained_advisor': [
        'retained advisor',
        'retained a financial advisor',
        'engaged a financial advisor',
        'financial advisor',
    ],
    'sale_process': [
        'sale process',
        'sale of the company',
        'formal sale process',
    ],
    'acquisition_proposal': [
        'acquisition proposal',
        'proposal to acquire',
        'proposal from',
    ],
    'unsolicited_proposal': [
        'unsolicited proposal',
        'unsolicited acquisition proposal',
    ],
    'competing_bid': [
        'competing bid',
        'competing proposal',
        'superior proposal',
    ],
    'rofr_rofn': [
        'right of first refusal',
        'right of first negotiation',
        'right of first offer',
        'rofr',
        'rofn',
    ],
    'option_to_acquire': [
        'option to acquire',
        'purchase option',
    ],
    'activist_13d': [
        'activist',
    ],
}

PRIVATE_BACKGROUND_MARKERS = [
    'background of the merger',
    'background of the offer',
    'background of the transaction',
    'past contacts',
    'private outreach',
    'confidentiality agreement',
    'non-disclosure agreement',
    'due diligence',
]

FALSE_POSITIVE_MARKERS = [
    'stock option to acquire',
    'stock options to acquire',
    'stock option grants',
    'option awards',
    'restricted stock units',
    'lease',
    'lease-to-own',
    'customer',
    'merchandise',
    'premises',
    'office space',
    'future issuances of equity securities',
    'previously served',
    'prior to joining',
    'financial advisors and arthur andersen',
    'investment banking',
    'underwriting',
    'underwriter',
    'underwriters',
    'representatives',
    'firm shares',
    'option shares',
    'optional shares',
    'optional securities',
    'over-allotment',
    'prospectus',
    'free and clear of any lien',
    'encumbrance, right of first refusal',
    'not issued in violation of any preemptive right',
    'preemptive right, resale right',
    'has the meaning set forth',
    'shall have the following meanings',
    'may prevent or discourage unsolicited acquisition proposals',
    'license agreement',
    'clazakizumab',
    'vitaeris',
    'csl limited',
    'therapeutic option',
    'strategic collaboration and purchase option agreement',
]

PROCESS_CONTEXT_MARKERS = [
    'all outstanding shares',
    'board of directors',
    'special committee',
    'strategic alternatives',
    'sale process',
    'sale of the company',
    'sell the company',
    'merger',
    'business combination',
    'acquisition proposal',
    'proposal to acquire',
    'unsolicited proposal',
    'unsolicited acquisition proposal',
    'competing proposal',
    'superior proposal',
    'maximize shareholder value',
]

ACTIVIST_PROCESS_MARKERS = [
    'strategic alternatives',
    'sale process',
    'sale of the company',
    'sell the company',
    'merger',
    'business combination',
    'acquisition proposal',
    'proposal to acquire',
    'unsolicited proposal',
    'unsolicited acquisition proposal',
    'competing proposal',
    'superior proposal',
    'maximize shareholder value',
    'board review',
]

_TICKERS_CACHE: dict[str, dict[str, str]] | None = None


@dataclass(frozen=True)
class Filing:
    filing_date: str
    filing_type: str
    accession_number: str
    source_url: str
    primary_url: str
    complete_text_url: str


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
    cleaned = re.sub(r'\s+', ' ', html.unescape(text or '')).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(' ', 1)[0].rstrip(' ,.;') + '...'


def valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        return False
    return True


def window_start(announcement_date: str) -> str:
    dt = datetime.strptime(announcement_date, '%Y-%m-%d')
    return (dt - timedelta(days=WINDOW_DAYS)).strftime('%Y-%m-%d')


def date_before(left: str, right: str) -> bool:
    return valid_date(left) and valid_date(right) and left < right


def index_by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    indexed = {}
    for row in rows:
        value = row.get(key, '').strip()
        if value and value not in indexed:
            indexed[value] = row
    return indexed


def _get_bytes(url: str, timeout: int = 12) -> bytes | None:
    time.sleep(REQUEST_SLEEP_SECONDS)
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _get_json(url: str) -> dict | None:
    raw = _get_bytes(url)
    if not raw:
        return None
    try:
        return json.loads(raw.decode('utf-8'))
    except json.JSONDecodeError:
        return None


def _get_text(url: str) -> str:
    raw = _get_bytes(url)
    if not raw:
        return ''
    return raw.decode('utf-8', errors='ignore')


def edgar_tickers() -> dict[str, dict[str, str]]:
    global _TICKERS_CACHE
    if _TICKERS_CACHE is None:
        raw = _get_json(EDGAR_TICKERS_JSON) or {}
        _TICKERS_CACHE = {
            row['ticker'].upper(): {
                'cik': str(row['cik_str']).zfill(10),
                'title': row.get('title', ''),
            }
            for row in raw.values()
            if row.get('ticker') and row.get('cik_str')
        }
    return _TICKERS_CACHE


def cik_from_sec_url(url: str) -> str:
    match = re.search(r'/Archives/edgar/data/(\d+)/', url or '')
    return match.group(1).zfill(10) if match else ''


def lookup_cik(row: dict[str, str], date_rows: dict[str, dict[str, str]], source_rows: list[dict[str, str]], use_api: bool) -> str:
    ticker = row.get('ticker', '').strip().upper()
    if ticker in CIK_OVERRIDES:
        return CIK_OVERRIDES[ticker]

    for source_row in source_rows:
        cik = cik_from_sec_url(source_row.get('source_url', ''))
        if cik:
            return cik

    date_row = date_rows.get(row.get('case_id', '').strip(), {})
    cik = cik_from_sec_url(date_row.get('source_url', ''))
    if cik:
        return cik

    if use_api:
        entry = edgar_tickers().get(ticker)
        if entry:
            return entry['cik']
    return ''


def filing_urls(cik: str, accession_number: str, primary_doc: str) -> tuple[str, str, str]:
    cik_raw = str(int(cik))
    accession_clean = accession_number.replace('-', '')
    base = f'{EDGAR_ARCHIVE}/{cik_raw}/{accession_clean}'
    return f'{base}/{accession_number}-index.htm', f'{base}/{primary_doc}', f'{base}/{accession_number}.txt'


def collect_filings(cik: str, start: str, end: str, use_api: bool) -> tuple[list[Filing], str]:
    if not use_api:
        return [], 'EDGAR API disabled by --no-api.'
    data = _get_json(f'{EDGAR_SUBMISSIONS}/CIK{cik}.json')
    if not data:
        return [], 'EDGAR submissions unavailable or CIK blocked.'

    recent = data.get('filings', {}).get('recent', {})
    forms = recent.get('form', [])
    dates = recent.get('filingDate', [])
    accns = recent.get('accessionNumber', [])
    primary_docs = recent.get('primaryDocument', [])
    filings = []
    for form, filing_date, accession, primary_doc in zip(forms, dates, accns, primary_docs):
        if form not in TARGET_FORMS:
            continue
        if not (start <= filing_date < end):
            continue
        source_url, primary_url, complete_text_url = filing_urls(cik, accession, primary_doc)
        filings.append(Filing(
            filing_date=filing_date,
            filing_type=form,
            accession_number=accession,
            source_url=source_url,
            primary_url=primary_url,
            complete_text_url=complete_text_url,
        ))
    filings.sort(key=lambda item: (item.filing_date, item.filing_type, item.accession_number))
    return filings, 'EDGAR submissions search completed.'


def strip_html(text: str) -> str:
    text = re.sub(r'(?is)<script.*?</script>', ' ', text)
    text = re.sub(r'(?is)<style.*?</style>', ' ', text)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    return compact(text, max_chars=100000)


def contexts_for_phrase(text: str, phrase: str, radius: int = 260) -> list[str]:
    lowered = text.lower()
    contexts = []
    start = 0
    while True:
        idx = lowered.find(phrase, start)
        if idx < 0:
            break
        left = max(0, idx - radius)
        right = min(len(lowered), idx + len(phrase) + radius)
        contexts.append(lowered[left:right])
        start = idx + len(phrase)
    return contexts


def has_process_context(value: str) -> bool:
    return any(marker in value for marker in PROCESS_CONTEXT_MARKERS)


def item4_section(text: str) -> str:
    lowered = text.lower()
    start_match = re.search(r'item\s+4\.?\s+purpose of (?:the )?transaction', lowered)
    if not start_match:
        start_match = re.search(r'item\s+4\.', lowered)
    if not start_match:
        return ''
    start = start_match.start()
    end_match = re.search(r'item\s+5\.', lowered[start_match.end():])
    if not end_match:
        return lowered[start:start + 4000]
    return lowered[start:start_match.end() + end_match.start()]


def has_activist_process_context(full_text: str) -> bool:
    section = item4_section(full_text)
    if not section:
        return False
    if any(marker in section for marker in [
        'for investment purposes',
        'not applicable',
        'did not involve any transactions',
        'ordinary course of business',
    ]) and not any(marker in section for marker in ACTIVIST_PROCESS_MARKERS):
        return False
    return any(marker in section for marker in ACTIVIST_PROCESS_MARKERS)


def phrase_is_signal(signal_type: str, phrase: str, context: str, full_text: str, filing_type: str) -> bool:
    if signal_type == 'activist_13d':
        if filing_type not in {'SC 13D', 'SC 13D/A'}:
            return False
        return has_activist_process_context(full_text)

    if signal_type == 'retained_advisor':
        if phrase == 'financial advisor' and not has_process_context(context):
            return False
        return not any(marker in context for marker in FALSE_POSITIVE_MARKERS)

    if signal_type == 'option_to_acquire':
        if any(marker in context for marker in FALSE_POSITIVE_MARKERS):
            return False
        return any(marker in context for marker in [
            'all outstanding shares',
            'company',
            'business combination',
            'merger',
            'acquisition proposal',
            'proposal to acquire',
        ])

    if signal_type == 'rofr_rofn':
        if any(marker in context for marker in FALSE_POSITIVE_MARKERS):
            return False
        return True

    if signal_type == 'sale_process' and phrase == 'sale of the company':
        if any(marker in context for marker in ['previously served', 'led the company', 'through the sale of the company']):
            return False
        return True

    if signal_type == 'acquisition_proposal' and phrase == 'proposal from':
        if any(marker in context for marker in FALSE_POSITIVE_MARKERS):
            return False
        return any(marker in context for marker in [
            'acquisition',
            'acquire',
            'merger',
            'unsolicited',
            'superior proposal',
            'competing proposal',
        ])

    return not any(marker in context for marker in FALSE_POSITIVE_MARKERS)


def signal_matches(text: str, filing_type: str) -> tuple[list[str], list[str]]:
    lowered = text.lower()
    signal_types = []
    keywords = []
    for signal_type, phrases in SIGNAL_KEYWORDS.items():
        matched = []
        for phrase in phrases:
            for context in contexts_for_phrase(text, phrase):
                if phrase_is_signal(signal_type, phrase, context, lowered, filing_type):
                    matched.append(phrase)
                    break
        if matched:
            signal_types.append(signal_type)
            keywords.extend(matched)
    return sorted(set(signal_types)), sorted(set(keywords))


def excerpt_for_keywords(text: str, keywords: list[str]) -> str:
    lowered = text.lower()
    for keyword in keywords:
        idx = lowered.find(keyword.lower())
        if idx >= 0:
            start = max(0, idx - 170)
            end = min(len(text), idx + len(keyword) + 220)
            return compact(text[start:end], 420)
    return ''


def is_private_background_only(text: str, filing_type: str) -> bool:
    if filing_type not in {'DEF 14A', 'DEFM14A', 'SC 14D9', 'SC TO-T'}:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in PRIVATE_BACKGROUND_MARKERS)


def classify_filing(filing: Filing, text: str, fetch_note: str) -> dict[str, str]:
    signal_types, keywords = signal_matches(text, filing.filing_type)
    private_background_only = bool(signal_types) and is_private_background_only(text, filing.filing_type)
    if signal_types and not private_background_only:
        recommended_status = 'POSSIBLE_HIT'
        confidence = 'LOW'
    elif not text:
        recommended_status = 'NEEDS_MANUAL_REVIEW'
        confidence = 'LOW'
    else:
        recommended_status = 'LIKELY_NO_HIT'
        confidence = 'LOW'

    if private_background_only:
        recommended_status = 'NEEDS_MANUAL_REVIEW'
        confidence = 'LOW'
        signal_types = []
        keywords = []
        fetch_note = f'{fetch_note} Keyword context appears in later proxy/background text; not counted as prior public signal.'

    return {
        'filing_date': filing.filing_date,
        'filing_type': filing.filing_type,
        'accession_number': filing.accession_number,
        'source_url': filing.source_url,
        'possible_signal_type': '|'.join(signal_types),
        'keyword_hits': '|'.join(keywords),
        'excerpt_if_available': excerpt_for_keywords(text, keywords) or fetch_note,
        'confidence': confidence,
        'recommended_status': recommended_status,
    }


def manual_url(ticker: str, company: str, start: str, end: str) -> str:
    query = f'{ticker} "{company}" ("strategic alternatives" OR "financial advisor" OR "sale process" OR "acquisition proposal" OR "unsolicited proposal" OR "competing bid" OR ROFR OR ROFN OR "option to acquire" OR activist OR "Item 4")'
    from urllib.parse import urlencode
    return 'https://efts.sec.gov/LATEST/search-index?' + urlencode({
        'q': query,
        'forms': ','.join(sorted(TARGET_FORMS)),
        'dateRange': 'custom',
        'startdt': start,
        'enddt': end,
    })


def build_targets(
    confirmation_rows: list[dict[str, str]],
    date_rows: dict[str, dict[str, str]],
    source_rows_by_case: dict[str, list[dict[str, str]]],
    *,
    use_api: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]]:
    targets = []
    hits = []
    case_status = {}
    for row in confirmation_rows:
        case_id = row.get('case_id', '').strip()
        ticker = row.get('ticker', '').strip()
        company = row.get('company_name', '').strip()
        announcement_date = row.get('acquisition_announcement_date', '').strip()
        if not valid_date(announcement_date):
            date_row = date_rows.get(case_id, {})
            announcement_date = date_row.get('acquisition_announcement_date', '').strip()

        base = {
            'case_id': case_id,
            'ticker': ticker,
            'company_name': company,
            'announcement_date': announcement_date,
        }
        if not valid_date(announcement_date):
            blocked = {
                **base,
                'filing_date': '',
                'filing_type': '',
                'accession_number': '',
                'source_url': '',
                'possible_signal_type': '',
                'keyword_hits': '',
                'excerpt_if_available': 'Announcement date missing; cannot lock pre-announcement cutoff.',
                'confidence': 'LOW',
                'recommended_status': 'DATE_OR_CIK_BLOCKED',
            }
            targets.append(blocked)
            case_status[case_id] = 'DATE_OR_CIK_BLOCKED'
            continue

        start = window_start(announcement_date)
        cik = lookup_cik(row, date_rows, source_rows_by_case.get(case_id, []), use_api=use_api)
        if not cik:
            blocked = {
                **base,
                'filing_date': '',
                'filing_type': '',
                'accession_number': '',
                'source_url': manual_url(ticker, company, start, announcement_date),
                'possible_signal_type': '',
                'keyword_hits': '',
                'excerpt_if_available': 'CIK lookup blocked; manual SEC search URL generated.',
                'confidence': 'LOW',
                'recommended_status': 'DATE_OR_CIK_BLOCKED',
            }
            targets.append(blocked)
            case_status[case_id] = 'DATE_OR_CIK_BLOCKED'
            continue

        filings, collect_note = collect_filings(cik, start, announcement_date, use_api=use_api)
        if not filings:
            status = 'NEEDS_MANUAL_REVIEW' if 'unavailable' in collect_note.lower() or 'disabled' in collect_note.lower() else 'LIKELY_NO_HIT'
            no_filing_row = {
                **base,
                'filing_date': '',
                'filing_type': '',
                'accession_number': '',
                'source_url': manual_url(ticker, company, start, announcement_date),
                'possible_signal_type': '',
                'keyword_hits': '',
                'excerpt_if_available': f'{collect_note} No target-form filings collected in the 18-month pre-announcement window.',
                'confidence': 'LOW',
                'recommended_status': status,
            }
            targets.append(no_filing_row)
            case_status[case_id] = status
            continue

        case_rows = []
        for filing in filings:
            raw_parts = []
            if use_api:
                primary_text = _get_text(filing.primary_url)
                complete_text = _get_text(filing.complete_text_url)
                raw_parts = [part for part in [primary_text, complete_text] if part]
            raw_text = '\n'.join(raw_parts)
            filing_text = strip_html(raw_text) if raw_text else ''
            fetch_note = 'Primary and complete submission text fetched.' if filing_text else 'Filing text unavailable; manual review needed.'
            screened = classify_filing(filing, filing_text, fetch_note)
            target_row = {**base, **screened}
            case_rows.append(target_row)
            targets.append(target_row)
            if target_row['recommended_status'] == 'POSSIBLE_HIT':
                hits.append(target_row)

        statuses = {case_row['recommended_status'] for case_row in case_rows}
        if 'POSSIBLE_HIT' in statuses:
            case_status[case_id] = 'POSSIBLE_HIT'
        elif 'NEEDS_MANUAL_REVIEW' in statuses:
            case_status[case_id] = 'NEEDS_MANUAL_REVIEW'
        elif statuses == {'LIKELY_NO_HIT'}:
            case_status[case_id] = 'LIKELY_NO_HIT'
        else:
            case_status[case_id] = 'NEEDS_MANUAL_REVIEW'
    return targets, hits, case_status


def group_by(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        value = row.get(key, '').strip()
        if value:
            grouped.setdefault(value, []).append(row)
    return grouped


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    lines = [
        '| ' + ' | '.join(columns) + ' |',
        '| ' + ' | '.join(['---'] * len(columns)) + ' |',
    ]
    for row in rows:
        values = [str(row.get(column, '')).replace('|', '/') for column in columns]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)


def representative_case_rows(rows: list[dict[str, str]], statuses: set[str]) -> list[dict[str, str]]:
    out = []
    seen = set()
    for row in rows:
        case_id = row.get('case_id', '')
        if case_id in seen or row.get('recommended_status') not in statuses:
            continue
        out.append(row)
        seen.add(case_id)
    return out


def write_report(
    path: Path,
    targets: list[dict[str, str]],
    hits: list[dict[str, str]],
    case_status: dict[str, str],
) -> None:
    status_counts = Counter(case_status.values())
    manual = representative_case_rows(targets, {'POSSIBLE_HIT', 'NEEDS_MANUAL_REVIEW', 'DATE_OR_CIK_BLOCKED'})
    best_beyond_mdvn = [
        row for row in hits
        if row.get('ticker') != 'MDVN'
    ][:10]
    likely_no_hit_cases = [
        {'case_id': case_id, 'recommended_status': status}
        for case_id, status in sorted(case_status.items())
        if status == 'LIKELY_NO_HIT'
    ]
    path.write_text(f"""# Pre-Announcement Filing Collector Report

Generated by `src/historical_case_tools/pre_announcement_filing_collector.py`.

## Summary

- Cases checked: {len(case_status)}
- Filing target rows collected: {len(targets)}
- Possible signal hit rows: {len(hits)}
- Possible-hit cases: {status_counts.get('POSSIBLE_HIT', 0)}
- Likely no-hit cases: {status_counts.get('LIKELY_NO_HIT', 0)}
- Needs manual review cases: {status_counts.get('NEEDS_MANUAL_REVIEW', 0)}
- Date or CIK blocked cases: {status_counts.get('DATE_OR_CIK_BLOCKED', 0)}
- No rows were marked `VERIFIED`, `CALIBRATION_ELIGIBLE`, or `CONFIRMED_NO_HIT`.

## Possible Signal Hits

{markdown_table(hits[:25], ['case_id', 'ticker', 'announcement_date', 'filing_date', 'filing_type', 'possible_signal_type', 'keyword_hits', 'source_url']) if hits else 'None found from collected pre-announcement filing text.'}

## Best Possible MDVN-Like Candidates Beyond MDVN

{markdown_table(best_beyond_mdvn, ['case_id', 'ticker', 'announcement_date', 'filing_date', 'filing_type', 'possible_signal_type', 'keyword_hits', 'source_url']) if best_beyond_mdvn else 'None found beyond MDVN from collected pre-announcement filing text.'}

## Likely No-Hit Cases

{markdown_table(likely_no_hit_cases, ['case_id', 'recommended_status']) if likely_no_hit_cases else 'None labeled likely no-hit at case level.'}

## Manual Review Queue

{markdown_table(manual, ['case_id', 'ticker', 'announcement_date', 'filing_date', 'filing_type', 'recommended_status', 'keyword_hits', 'source_url']) if manual else 'No manual-review rows generated.'}

## Rules Applied

- Screened only filings dated before the acquisition announcement date.
- Used an 18-month pre-announcement search window.
- Excluded later proxy/background-only private negotiation context from possible-hit labeling.
- Used `LIKELY_NO_HIT` only as a conservative workflow label, not as confirmed no-hit evidence.
""", encoding='utf-8')


def update_confirmation_report(path: Path, targets: list[dict[str, str]], hits: list[dict[str, str]], case_status: dict[str, str]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding='utf-8')
    marker = '\n## Pre-Announcement Filing Collector Addendum\n'
    text = text.split(marker, 1)[0].rstrip()
    status_counts = Counter(case_status.values())
    manual = representative_case_rows(targets, {'POSSIBLE_HIT', 'NEEDS_MANUAL_REVIEW', 'DATE_OR_CIK_BLOCKED'})
    best_beyond_mdvn = [row for row in hits if row.get('ticker') != 'MDVN'][:10]
    addendum = f"""

## Pre-Announcement Filing Collector Addendum

Updated by `src/historical_case_tools/pre_announcement_filing_collector.py`.

- Cases checked: {len(case_status)}
- Filing target rows collected: {len(targets)}
- Possible signal hit rows: {len(hits)}
- Possible-hit cases: {status_counts.get('POSSIBLE_HIT', 0)}
- Likely no-hit cases: {status_counts.get('LIKELY_NO_HIT', 0)}
- Needs manual review cases: {status_counts.get('NEEDS_MANUAL_REVIEW', 0)}
- Date or CIK blocked cases: {status_counts.get('DATE_OR_CIK_BLOCKED', 0)}

### Manual Review First

{markdown_table(manual[:15], ['case_id', 'ticker', 'announcement_date', 'filing_date', 'filing_type', 'recommended_status', 'keyword_hits']) if manual else 'No manual-review rows generated.'}

### Best Possible MDVN-Like Candidates Beyond MDVN

{markdown_table(best_beyond_mdvn, ['case_id', 'ticker', 'announcement_date', 'filing_date', 'filing_type', 'possible_signal_type', 'keyword_hits']) if best_beyond_mdvn else 'None found beyond MDVN from collected pre-announcement filing text.'}
"""
    path.write_text(text + addendum, encoding='utf-8')


def run(args: argparse.Namespace) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]]:
    confirmation_rows = read_csv(args.confirmation_results)
    date_rows = index_by(read_csv(args.acquisition_dates), 'case_id')
    source_rows_by_case = group_by(read_csv(args.source_evidence), 'case_id')
    targets, hits, case_status = build_targets(
        confirmation_rows,
        date_rows,
        source_rows_by_case,
        use_api=not args.no_api,
    )
    write_csv(args.targets_output, targets, ROW_FIELDS)
    write_csv(args.hits_output, hits, ROW_FIELDS)
    write_report(args.report, targets, hits, case_status)
    update_confirmation_report(args.confirmation_report, targets, hits, case_status)
    return targets, hits, case_status


def main() -> int:
    parser = argparse.ArgumentParser(description='Collect and screen pre-announcement SEC filings for acquired historical cases.')
    parser.add_argument('--acquisition-dates', type=Path, default=DEFAULT_ACQUISITION_DATES)
    parser.add_argument('--confirmation-results', type=Path, default=DEFAULT_CONFIRMATION_RESULTS)
    parser.add_argument('--queue', type=Path, default=DEFAULT_QUEUE)
    parser.add_argument('--source-evidence', type=Path, default=DEFAULT_SOURCE_EVIDENCE)
    parser.add_argument('--targets-output', type=Path, default=DEFAULT_TARGETS_OUTPUT)
    parser.add_argument('--hits-output', type=Path, default=DEFAULT_HITS_OUTPUT)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    parser.add_argument('--confirmation-report', type=Path, default=DEFAULT_CONFIRMATION_REPORT)
    parser.add_argument('--no-api', action='store_true', help='Skip EDGAR API calls and generate blocked/manual rows only.')
    args = parser.parse_args()

    targets, hits, case_status = run(args)
    status_counts = Counter(case_status.values())
    print(f'Cases checked: {len(case_status)}')
    print(f'Filing target rows collected: {len(targets)}')
    print(f'Possible signal hit rows: {len(hits)}')
    print(f'Possible-hit cases: {status_counts.get("POSSIBLE_HIT", 0)}')
    print(f'Likely no-hit cases: {status_counts.get("LIKELY_NO_HIT", 0)}')
    print(f'Needs manual review cases: {status_counts.get("NEEDS_MANUAL_REVIEW", 0)}')
    print(f'Date or CIK blocked cases: {status_counts.get("DATE_OR_CIK_BLOCKED", 0)}')
    print(f'Targets -> {args.targets_output}')
    print(f'Hits -> {args.hits_output}')
    print(f'Report -> {args.report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
