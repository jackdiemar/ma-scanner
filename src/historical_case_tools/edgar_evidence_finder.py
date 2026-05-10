#!/usr/bin/env python3
"""
edgar_evidence_finder.py

Given ticker, company, date range, and event type, locate SEC EDGAR filings
that constitute process-signal evidence for Historical Process Intelligence cases.

Workflow:
  1. Looks up CIK via EDGAR company tickers JSON (no HTML scraping)
  2. Pulls full filing history from EDGAR submissions API
  3. Filters by form type and date window
  4. Optionally runs EDGAR full-text search for phrase confirmation
  5. Outputs filing candidates + manual research URLs + structured checklist

EDGAR rate limit: 10 req/sec. This script sleeps 0.15s between API calls.

Usage:
    python3 edgar_evidence_finder.py --ticker HARP \\
        --company "harpoon therapeutics" \\
        --event ROFR_ROFN \\
        --year-from 2020 --year-to 2021

    python3 edgar_evidence_finder.py --ticker GNCA \\
        --company "genocea biosciences" \\
        --event SA_AFFIRM \\
        --year-from 2022 --year-to 2022 \\
        --output json

    python3 edgar_evidence_finder.py --ticker RIGL \\
        --company "rigel pharmaceuticals" \\
        --event ACTIVIST_13D \\
        --year-from 2019 --year-to 2021 \\
        --no-api
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from typing import Optional


# ─── Event → filing type mapping ────────────────────────────────────────────

EVENT_FORM_MAP: dict[str, list[str]] = {
    'SA_AFFIRM':        ['8-K'],
    'BANKER_RETAINED':  ['8-K'],
    'MERGER_AGREEMENT': ['8-K', 'SC TO-T', 'SC 13E-3'],
    'ACTIVIST_13D':     ['SC 13D', 'SC 13D/A'],
    'ROFR_ROFN':        ['8-K', '10-K', '10-Q'],
    'WIND_DOWN':        ['8-K'],
    'BANKRUPTCY':       ['8-K'],
    'ASSET_SALE':       ['8-K'],
    'DEAL_TERMINATION': ['8-K'],
    'DEAL_CLOSE':       ['8-K'],
}

# Full-text search phrase sets per event type
EVENT_PHRASE_MAP: dict[str, list[str]] = {
    'SA_AFFIRM':        ['strategic alternatives', 'sale of the company', 'maximize shareholder value'],
    'BANKER_RETAINED':  ['financial advisor', 'strategic alternatives', 'investment banking services'],
    'MERGER_AGREEMENT': ['agreement and plan of merger', 'per share in cash', 'tender offer'],
    'ACTIVIST_13D':     ['purpose of transaction', 'explore strategic alternatives', 'board representation'],
    'ROFR_ROFN':        ['right of first refusal', 'right of first negotiation', 'right of first offer'],
    'WIND_DOWN':        ['wind down', 'cease operations', 'orderly wind-down'],
    'BANKRUPTCY':       ['chapter 11', 'chapter 7', 'voluntary petition'],
    'ASSET_SALE':       ['asset purchase agreement', 'asset sale', 'divestiture'],
    'DEAL_TERMINATION': ['termination agreement', 'merger agreement has been terminated', 'withdrawn'],
    'DEAL_CLOSE':       ['acquisition was completed', 'merger was completed', 'closing of the'],
}

# Evidence type mapping (for source_evidence.csv population)
EVENT_EVIDENCE_TYPE: dict[str, str] = {
    'SA_AFFIRM':        '8K_SA',
    'BANKER_RETAINED':  '8K_SA',
    'MERGER_AGREEMENT': '8K_MERGER',
    'ACTIVIST_13D':     '13D_INITIAL',
    'ROFR_ROFN':        'EXHIBIT_AGREEMENT',
    'WIND_DOWN':        '8K_WINDDOWN',
    'BANKRUPTCY':       '8K_BANKRUPTCY',
    'ASSET_SALE':       '8K_ASSET_SALE',
    'DEAL_TERMINATION': '8K_OTHER',
    'DEAL_CLOSE':       '8K_OTHER',
}

# Checklist items per event type
EVENT_CHECKLIST: dict[str, list[str]] = {
    'SA_AFFIRM': [
        'Search 8-K filings for "strategic alternatives" or "maximize shareholder value" in date range.',
        'Open matching 8-K. Check Item 1.01 AND Exhibit 99.1 (press release).',
        'Extract verbatim SA language. Record as excerpt_text (max 300 chars).',
        'Record EDGAR filing date (not press release date) as observation_date.',
        'Check for separate banker-retained 8-K within 30 days — if found, evaluate which is earlier.',
        'Pull adjusted close price on confirmed filing date via yfinance.',
    ],
    'BANKER_RETAINED': [
        'Search 8-K filings for "financial advisor" + "strategic" in date range.',
        'Check if banker language appears in the SAME 8-K as SA announcement.',
        'If separate 8-K — record the EARLIER filing date as observation_date.',
        'Extract verbatim banker-retained language. Record advisor name.',
        'Pull adjusted close price on confirmed filing date via yfinance.',
    ],
    'MERGER_AGREEMENT': [
        'Search 8-K filings for "agreement and plan of merger" in date range.',
        'Open 8-K Item 1.01. Extract deal_price_per_share verbatim.',
        'Record outcome_date = EDGAR 8-K filing date (not signing date).',
        'CRITICAL: Search for any 8-K with SA or banker language BEFORE this merger 8-K.',
        'If prior SA/banker signal found — that earlier date is observation_date; merger 8-K is outcome_date.',
        'Calculate deal_premium_pct = premium to 30-day pre-announcement average (NOT to price_at_signal).',
    ],
    'ACTIVIST_13D': [
        'Search SC 13D filings for this company in date range.',
        'Find the INITIAL 13D (form type = "SC 13D", not "SC 13D/A" which are amendments).',
        'Open the 13D. Read "Item 4. Purpose of Transaction" in full.',
        'Extract Item 4 text verbatim (complete text, not paraphrase).',
        'Record filer name from EDGAR header / Item 1 of the 13D — not from news articles.',
        'Record activist_ownership_pct from Item 5.',
        'Run exhibit_scope_extractor.py if Item 4 references a separate letter or exhibit.',
        'Run item4_parser.py on extracted Item 4 text to get item4_intent classification.',
        'Pull adjusted close price on 13D filing date via yfinance.',
    ],
    'ROFR_ROFN': [
        'Search 8-K filings for "right of first refusal" or "right of first negotiation" in date range.',
        'Open matching 8-K. Check filing index for Exhibit 10.x entries.',
        'Download the collaboration/license/option agreement exhibit (Exhibit 10.1, 10.2, etc.).',
        'Search exhibit for ROFR / ROFN / ROFO clause. Typical location: Article [X] or Section [X.X].',
        'Run exhibit_scope_extractor.py on the exhibit text to classify scope.',
        'Record rofr_scope: WHOLE_COMPANY / PROGRAM_SPECIFIC / ASSET_SPECIFIC / TERRITORY_SPECIFIC.',
        'Extract verbatim ROFR clause (max 500 chars) for excerpt_text and source_evidence.csv.',
        'Record rights_holder (counterparty name) from the ROFR clause.',
        'Pull adjusted close price on 8-K filing date via yfinance.',
    ],
    'WIND_DOWN': [
        'Search 8-K filings for "wind down" / "cease operations" in date range.',
        'Check for separate SA announcement 8-K BEFORE the wind-down 8-K.',
        'If SA 8-K found: observation_date = SA 8-K date. Wind-down 8-K date = outcome_date.',
        'Verify no Chapter 11/7 bankruptcy petition on PACER. If filed → reclassify to BANKRUPTCY.',
        'Extract verbatim wind-down announcement language.',
        'Record outcome_date = wind-down 8-K EDGAR filing date (not press release date).',
    ],
    'BANKRUPTCY': [
        'Search 8-K filings for "chapter 11" / "chapter 7" / "voluntary petition" in date range.',
        'Record outcome_date = 8-K announcing bankruptcy filing date.',
        'Check PACER (https://pacer.gov) for actual petition date — may differ from 8-K by 1-2 days.',
        'Confirm Chapter 7 (liquidation) vs Chapter 11 (reorganization). Record in notes.',
        'Check for separate SA announcement 8-K BEFORE bankruptcy 8-K.',
        'If prior SA found: observation_date = SA 8-K date.',
    ],
    'ASSET_SALE': [
        'Search 8-K filings for "asset purchase agreement" in date range.',
        'Open 8-K Item 1.01. Confirm whether deal is asset-only or whole-company.',
        'Record deal consideration for the specific asset only (not company equity value).',
        'Note rofr_scope = ASSET_SPECIFIC for this event type.',
        'Check for prior SA announcement. If found — SA date is observation_date.',
    ],
}

EDGAR_FULL_TEXT    = 'https://efts.sec.gov/LATEST/search-index'
EDGAR_TICKERS_JSON = 'https://www.sec.gov/files/company_tickers.json'
EDGAR_SUBMISSIONS  = 'https://data.sec.gov/submissions'
EDGAR_ARCHIVE      = 'https://www.sec.gov/Archives/edgar/data'
EDGAR_RATE_SLEEP   = 0.15  # seconds between API calls (10 req/sec limit)

_TICKERS_CACHE: dict | None = None


def _get_json(url: str, timeout: int = 12) -> Optional[dict]:
    """HTTP GET returning parsed JSON or None."""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'ma-scanner-research/1.0 jackdiemar@example.com'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as exc:
        print(f'  [WARN] EDGAR API unavailable: {exc}', file=sys.stderr)
        return None


def _edgar_tickers() -> dict:
    """Return cached EDGAR company tickers JSON (ticker → {cik_str, title})."""
    global _TICKERS_CACHE
    if _TICKERS_CACHE is None:
        print('  Fetching EDGAR company ticker list...')
        raw = _get_json(EDGAR_TICKERS_JSON)
        if raw:
            # Index by ticker (uppercase) and by name fragment
            _TICKERS_CACHE = {
                v['ticker'].upper(): {'cik': str(v['cik_str']).zfill(10), 'title': v['title']}
                for v in raw.values()
                if 'ticker' in v and 'cik_str' in v
            }
        else:
            _TICKERS_CACHE = {}
    return _TICKERS_CACHE


def lookup_cik(ticker: str, company: str = '') -> Optional[str]:
    """
    Look up EDGAR CIK for a ticker.
    Tries: (1) exact ticker match, (2) company name fuzzy match.
    Returns 10-digit zero-padded CIK or None.
    """
    tickers = _edgar_tickers()
    time.sleep(EDGAR_RATE_SLEEP)

    # 1. Exact ticker
    entry = tickers.get(ticker.upper())
    if entry:
        print(f'  CIK ({ticker}): {entry["cik"]} — "{entry["title"]}"')
        return entry['cik']

    # 2. Company name fuzzy match (first word match)
    if company:
        company_lower = company.lower()
        first_word = company_lower.split()[0] if company_lower.split() else ''
        for t, e in tickers.items():
            if first_word and first_word in e['title'].lower():
                print(f'  CIK (fuzzy "{company}"): {e["cik"]} — "{e["title"]}"')
                return e['cik']

    print(f'  CIK not found for ticker={ticker}, company={company}')
    return None


def get_filing_history(cik: str) -> Optional[dict]:
    """Fetch full filing history from EDGAR submissions API."""
    url = f'{EDGAR_SUBMISSIONS}/CIK{cik}.json'
    time.sleep(EDGAR_RATE_SLEEP)
    return _get_json(url)


def filter_filings(subs: dict, form_types: list[str],
                   start_date: str, end_date: str) -> list[dict]:
    """Filter a submission history dict for matching form types and date range."""
    recent = subs.get('filings', {}).get('recent', {})
    if not recent:
        return []

    forms   = recent.get('form', [])
    dates   = recent.get('filingDate', [])
    accns   = recent.get('accessionNumber', [])
    cik_raw = subs.get('cik', '')
    cik_pad = str(cik_raw).zfill(10)

    results = []
    for form, d, accn in zip(forms, dates, accns):
        if form in form_types and start_date <= d <= end_date:
            accn_clean = accn.replace('-', '')
            results.append({
                'filing_type':      form,
                'filing_date':      d,
                'accession_number': accn,
                'index_url':        f'{EDGAR_ARCHIVE}/{cik_raw}/{accn_clean}/{accn}-index.htm',
                'cik':              cik_pad,
            })
    return results


def full_text_search(phrase: str, form_types: list[str],
                     start_date: str, end_date: str,
                     company: str = '') -> list[dict]:
    """
    Run EDGAR full-text search for a single phrase.
    Returns list of hit dicts from EDGAR API.
    """
    params: dict = {
        'q':         f'"{phrase}"',
        'dateRange': 'custom',
        'startdt':   start_date,
        'enddt':     end_date,
        'forms':     ','.join(form_types),
    }
    if company:
        params['entity'] = company

    url = f'{EDGAR_FULL_TEXT}?{urllib.parse.urlencode(params)}'
    print(f'  Full-text: {url}')
    time.sleep(EDGAR_RATE_SLEEP)

    data = _get_json(url)
    if not data:
        return []

    hits = data.get('hits', {}).get('hits', [])
    out = []
    for h in hits:
        src = h.get('_source', {})
        out.append({
            'filing_type':       src.get('file_type', ''),
            'filing_date':       src.get('file_date', ''),
            'entity_name':       src.get('entity_name', ''),
            'accession_number':  src.get('accession_no', ''),
            'period_of_report':  src.get('period_of_report', ''),
        })
    return out


def build_manual_urls(ticker: str, company: str, event_type: str,
                      start_date: str, end_date: str) -> dict:
    """
    Generate deterministic EDGAR research URLs for manual browser-based verification.
    No network calls — purely URL construction.
    """
    forms   = EVENT_FORM_MAP.get(event_type, ['8-K'])
    phrases = EVENT_PHRASE_MAP.get(event_type, [])

    company_encoded = urllib.parse.quote(company)
    form_primary    = urllib.parse.quote(forms[0])

    company_search = (
        f'https://www.sec.gov/cgi-bin/browse-edgar?company={company_encoded}'
        f'&CIK={ticker}&type={form_primary}&dateb=&owner=include&count=40&action=getcompany'
    )

    full_text_urls = []
    for phrase in phrases:
        p = urllib.parse.urlencode({
            'q':       f'"{phrase}"',
            'forms':   ','.join(forms),
            'dateRange': 'custom',
            'startdt': start_date,
            'enddt':   end_date,
            'entity':  company,
        })
        full_text_urls.append(f'{EDGAR_FULL_TEXT}?{p}')

    result = {
        'company_search_url': company_search,
        'full_text_search_urls': full_text_urls,
    }

    # 13D-specific direct search
    if event_type == 'ACTIVIST_13D':
        result['13d_search_url'] = (
            f'https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}'
            f'&type=SC+13D&dateb=&owner=include&count=40&action=getcompany'
        )

    # ROFR-specific exhibit note
    if event_type == 'ROFR_ROFN':
        result['exhibit_note'] = (
            'After finding the 8-K, open its filing index. '
            'Look for Exhibit 10.x entries (collaboration/license agreements). '
            'Download the exhibit and run exhibit_scope_extractor.py on the text.'
        )

    return result


def build_source_evidence_targets(ticker: str, case_id: str, event_type: str,
                                   expected_year: int) -> list[dict]:
    """
    Build RESEARCH_TARGET rows for source_evidence.csv.
    These are expected-but-not-yet-found evidence placeholders.
    """
    evidence_type = EVENT_EVIDENCE_TYPE.get(event_type, 'OTHER')
    forms         = EVENT_FORM_MAP.get(event_type, ['8-K'])
    phrases       = EVENT_PHRASE_MAP.get(event_type, [])

    # Determine which fields this evidence would support
    field_map = {
        'SA_AFFIRM':        'observation_date|source_filing_type|source_filing_date|source_filing_url|signal_type|excerpt_text',
        'BANKER_RETAINED':  'observation_date|source_filing_type|source_filing_date|source_filing_url|signal_type|excerpt_text',
        'MERGER_AGREEMENT': 'deal_date|deal_price_per_share|acquirer|outcome|deal_value_M',
        'ACTIVIST_13D':     'observation_date|source_filing_type|source_filing_date|source_filing_url|item4_intent|activist_filer|activist_ownership_pct',
        'ROFR_ROFN':        'observation_date|source_filing_type|source_filing_date|source_filing_url|rofr_scope|excerpt_text',
        'WIND_DOWN':        'outcome|outcome_date|days_signal_to_outcome|failure_reason',
        'BANKRUPTCY':       'outcome|outcome_date|days_signal_to_outcome',
        'ASSET_SALE':       'deal_date|deal_value_M|deal_type|outcome',
    }
    supports = field_map.get(event_type, 'observation_date|source_filing_url')

    n = 1
    targets = []

    # Primary signal evidence target
    targets.append({
        'evidence_id':          f'{case_id}-SRC-{n:03d}',
        'case_id':              case_id,
        'ticker':               ticker,
        'evidence_type':        evidence_type,
        'source_name':          'SEC EDGAR',
        'source_url':           'VERIFY_REQUIRED',
        'filing_type':          forms[0],
        'filing_date':          None,
        'accession_number':     None,
        'exhibit_number':       None,
        'excerpt':              f'Expected: {phrases[0] if phrases else ""}',
        'supports_field':       supports,
        'confidence':           'LOW',
        'verification_status':  'VERIFY_REQUIRED',
        'added_by':             'edgar_evidence_finder',
        'added_date':           '2026-05-10',
        'notes':                f'RESEARCH_TARGET — not yet confirmed. Run edgar_evidence_finder.py to locate. Expected in {expected_year}.',
    })
    n += 1

    # Price data target
    targets.append({
        'evidence_id':          f'{case_id}-SRC-{n:03d}',
        'case_id':              case_id,
        'ticker':               ticker,
        'evidence_type':        'PRICE_DATA',
        'source_name':          'Yahoo Finance / yfinance',
        'source_url':           f'https://finance.yahoo.com/quote/{ticker}/history/',
        'filing_type':          None,
        'filing_date':          None,
        'accession_number':     None,
        'exhibit_number':       None,
        'excerpt':              None,
        'supports_field':       'price_at_signal|price_30d_after|price_90d_after|price_180d_after|max_drawdown_pct_after_signal',
        'confidence':           'LOW',
        'verification_status':  'VERIFY_REQUIRED',
        'added_by':             'edgar_evidence_finder',
        'added_date':           '2026-05-10',
        'notes':                'RESEARCH_TARGET — pull after observation_date confirmed. Use yfinance auto_adjust=True. For delisted tickers: use Stooq or Bloomberg (see verification_checklist.md).',
    })
    n += 1

    # ROFR cases need exhibit evidence target
    if event_type == 'ROFR_ROFN':
        targets.append({
            'evidence_id':          f'{case_id}-SRC-{n:03d}',
            'case_id':              case_id,
            'ticker':               ticker,
            'evidence_type':        'EXHIBIT_AGREEMENT',
            'source_name':          'SEC EDGAR — Collaboration Agreement Exhibit',
            'source_url':           'VERIFY_REQUIRED',
            'filing_type':          '8-K',
            'filing_date':          None,
            'accession_number':     None,
            'exhibit_number':       'VERIFY_REQUIRED',
            'excerpt':              'Expected: right of first refusal / right of first negotiation clause with scope language',
            'supports_field':       'rofr_scope|excerpt_text',
            'confidence':           'LOW',
            'verification_status':  'VERIFY_REQUIRED',
            'added_by':             'edgar_evidence_finder',
            'added_date':           '2026-05-10',
            'notes':                'RESEARCH_TARGET — ROFR scope comes from Exhibit 10.x of the collaboration 8-K. Run exhibit_scope_extractor.py on downloaded exhibit text.',
        })

    # Activist cases need Item 4 evidence target
    if event_type == 'ACTIVIST_13D':
        targets.append({
            'evidence_id':          f'{case_id}-SRC-{n:03d}',
            'case_id':              case_id,
            'ticker':               ticker,
            'evidence_type':        '13D_INITIAL',
            'source_name':          'SEC EDGAR — SC 13D Item 4 Text',
            'source_url':           'VERIFY_REQUIRED',
            'filing_type':          'SC 13D',
            'filing_date':          None,
            'accession_number':     None,
            'exhibit_number':       None,
            'excerpt':              'Expected: verbatim "Item 4. Purpose of Transaction" text from initial SC 13D',
            'supports_field':       'item4_intent|activist_filer|activist_ownership_pct|excerpt_text',
            'confidence':           'LOW',
            'verification_status':  'VERIFY_REQUIRED',
            'added_by':             'edgar_evidence_finder',
            'added_date':           '2026-05-10',
            'notes':                'RESEARCH_TARGET — Item 4 text must come from INITIAL 13D only (not amendments). Run item4_parser.py on extracted text.',
        })

    return targets


def run(ticker: str, company: str, event_type: str,
        year_from: int, year_to: int,
        case_id: str = '',
        use_api: bool = True) -> dict:
    """
    Main entry point. Returns structured evidence search result.
    """
    start = f'{year_from}-01-01'
    end   = f'{year_to}-12-31'
    forms = EVENT_FORM_MAP.get(event_type, ['8-K'])

    result: dict = {
        'ticker':              ticker,
        'company':             company,
        'event_type':          event_type,
        'search_window':       f'{start} to {end}',
        'cik':                 None,
        'filing_candidates':   [],
        'full_text_hits':      [],
        'manual_urls':         build_manual_urls(ticker, company, event_type, start, end),
        'checklist':           EVENT_CHECKLIST.get(event_type, []),
        'source_evidence_targets': build_source_evidence_targets(
            ticker, case_id or f'{ticker}-{year_from}-001', event_type, year_from
        ),
        'status':              'NOT_STARTED',
    }

    if not use_api:
        result['status'] = 'MANUAL_ONLY'
        return result

    # 1. CIK lookup
    cik = lookup_cik(ticker, company)
    result['cik'] = cik

    if cik:
        # 2. Filing history from submissions API
        subs = get_filing_history(cik)
        if subs:
            matches = filter_filings(subs, forms, start, end)
            result['filing_candidates'] = matches
            print(f'  Submissions API: {len(matches)} matching filings in window')

    # 3. Full-text search (first 2 phrases, one round-trip each)
    phrases = EVENT_PHRASE_MAP.get(event_type, [])
    for phrase in phrases[:2]:
        hits = full_text_search(phrase, forms, start, end, company=company)
        result['full_text_hits'].extend(hits)

    total = len(result['filing_candidates']) + len(result['full_text_hits'])
    result['status'] = 'CANDIDATES_FOUND' if total > 0 else 'NO_RESULTS'
    return result


def _format_text(result: dict) -> None:
    print(f'\nEDGAR Evidence Finder — {result["ticker"]} / {result["event_type"]}')
    print('=' * 60)
    print(f'Status:  {result["status"]}')
    print(f'CIK:     {result["cik"] or "NOT FOUND"}')
    print(f'Window:  {result["search_window"]}')

    if result['filing_candidates']:
        print(f'\nFiling Candidates from Submissions API ({len(result["filing_candidates"])}):')
        for f in result['filing_candidates'][:10]:
            print(f'  {f["filing_date"]}  {f["filing_type"]:<12}  {f["accession_number"]}')
            print(f'    {f["index_url"]}')

    if result['full_text_hits']:
        print(f'\nFull-Text Search Hits ({len(result["full_text_hits"])}):')
        for h in result['full_text_hits'][:5]:
            print(f'  {h["filing_date"]}  {h["filing_type"]:<12}  {h["entity_name"]}')

    print('\nManual Research URLs:')
    urls = result['manual_urls']
    print(f'  Company search:  {urls["company_search_url"]}')
    for u in urls.get('full_text_search_urls', []):
        print(f'  Full-text:       {u}')
    if '13d_search_url' in urls:
        print(f'  13D search:      {urls["13d_search_url"]}')
    if 'exhibit_note' in urls:
        print(f'  Exhibit note:    {urls["exhibit_note"]}')

    print('\nVerification Checklist:')
    for item in result['checklist']:
        print(f'  □  {item}')

    if result['source_evidence_targets']:
        print(f'\nSource Evidence Targets ({len(result["source_evidence_targets"])} rows):')
        for t in result['source_evidence_targets']:
            print(f'  {t["evidence_id"]}  {t["evidence_type"]}  supports: {t["supports_field"][:60]}...')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Find EDGAR evidence for Historical Process Intelligence cases'
    )
    parser.add_argument('--ticker',      required=True, help='Stock ticker (e.g. HARP)')
    parser.add_argument('--company',     default='',    help='Company name for EDGAR search')
    parser.add_argument('--event',       required=True,
                        choices=sorted(EVENT_FORM_MAP.keys()),
                        help='Event type to search for')
    parser.add_argument('--year-from',   type=int, required=True, help='Search start year')
    parser.add_argument('--year-to',     type=int, required=True, help='Search end year')
    parser.add_argument('--case-id',     default='', help='case_id for source_evidence.csv rows')
    parser.add_argument('--no-api',      action='store_true',
                        help='Skip EDGAR API calls; generate manual URLs only')
    parser.add_argument('--output',      choices=['text', 'json'], default='text')
    args = parser.parse_args()

    result = run(
        ticker=args.ticker,
        company=args.company or args.ticker.lower(),
        event_type=args.event,
        year_from=args.year_from,
        year_to=args.year_to,
        case_id=args.case_id,
        use_api=not args.no_api,
    )

    if args.output == 'json':
        print(json.dumps(result, indent=2, default=str))
    else:
        _format_text(result)


if __name__ == '__main__':
    main()
