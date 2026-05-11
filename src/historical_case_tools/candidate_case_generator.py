#!/usr/bin/env python3
"""
candidate_case_generator.py

Create conservative CANDIDATE rows for the historical process library.

This tool does not verify cases, assign PARTIAL/VERIFIED status, or mark
anything calibration-ready. It builds deterministic search targets from local
scanner outputs and historical-case source files.

Usage:
    python src/historical_case_tools/candidate_case_generator.py
    python src/historical_case_tools/candidate_case_generator.py --limit 300
"""

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'
DEFAULT_PREDICTIONS = REPO_ROOT / 'data' / 'predictions' / 'predictions_v12.csv'
DEFAULT_SCAN = REPO_ROOT / 'data' / 'scans' / 'scan_latest.json'
DEFAULT_SEED = HISTORICAL_DIR / 'cases_seed.csv'
DEFAULT_TARGETS = HISTORICAL_DIR / 'collection_targets.csv'
DEFAULT_OUTPUT = HISTORICAL_DIR / 'candidate_case_universe.csv'
DEFAULT_SOURCES = HISTORICAL_DIR / 'candidate_generation_sources.md'
DEFAULT_REPORT = HISTORICAL_DIR / 'candidate_generation_report.md'

CATEGORIES = [
    'COMPLETED_DEAL',
    'FAILED_STRATEGIC_REVIEW',
    'ACTIVIST_13D_NO_DEAL',
    'SALE_PRESSURE_13D',
    'GOVERNANCE_ONLY_13D',
    'ROFR_ROFN_CASE',
    'ASSET_SALE',
    'CAPITAL_RAISE_AFTER_PROCESS',
    'BANKRUPTCY_OR_WIND_DOWN',
    'REVERSE_MERGER',
]

OUTPUT_FIELDS = [
    'candidate_id',
    'ticker',
    'company_name',
    'category',
    'likely_event_year',
    'source_hint',
    'source_url_if_known',
    'edgar_query',
    'confidence_level',
    'priority',
    'verification_status',
    'reason_for_inclusion',
    'fields_needed_for_partial',
    'notes',
]

FIELDS_NEEDED = {
    'COMPLETED_DEAL': (
        'merger_8k_url|merger_filing_date|deal_date|deal_price_per_share|'
        'acquirer|prior_process_signal_search|price_window'
    ),
    'FAILED_STRATEGIC_REVIEW': (
        'sa_8k_url|observation_date|sa_excerpt|outcome_check|'
        'price_window|no_deal_confirmation'
    ),
    'ACTIVIST_13D_NO_DEAL': (
        'initial_13d_url|filing_date|activist_filer|item4_text|'
        'item4_intent|outcome_check|price_window'
    ),
    'SALE_PRESSURE_13D': (
        'initial_13d_url|filing_date|activist_filer|item4_text|'
        'sale_pressure_excerpt|outcome_check|price_window'
    ),
    'GOVERNANCE_ONLY_13D': (
        'initial_13d_url|filing_date|activist_filer|item4_text|'
        'governance_only_classification|outcome_check'
    ),
    'ROFR_ROFN_CASE': (
        'agreement_8k_url|exhibit_url|observation_date|rights_holder|'
        'rofr_scope|excerpt|outcome_check|price_window'
    ),
    'ASSET_SALE': (
        'asset_sale_8k_url|asset_description|buyer|consideration|'
        'retained_company_status|price_window'
    ),
    'CAPITAL_RAISE_AFTER_PROCESS': (
        'sa_or_process_8k_url|capital_raise_8k_or_s3_url|raise_date|'
        'raise_size|outcome_check|price_window'
    ),
    'BANKRUPTCY_OR_WIND_DOWN': (
        'sa_or_distress_8k_url|wind_down_or_bankruptcy_8k_url|'
        'outcome_date|chapter_check|price_window'
    ),
    'REVERSE_MERGER': (
        'sa_8k_url|reverse_merger_8k_url|counterparty|deal_structure|'
        'outcome_date|price_window'
    ),
}

SOURCE_HINTS = {
    'COMPLETED_DEAL': (
        'BioPharma Dive M&A tracker; Biotechgate M&A archives; EDGAR 8-K merger agreement search'
    ),
    'FAILED_STRATEGIC_REVIEW': (
        'EDGAR 8-K strategic alternatives search; source_queries.md Section 1A'
    ),
    'ACTIVIST_13D_NO_DEAL': (
        'EDGAR SC 13D search; WhaleWisdom / 13D Monitor cross-check; source_queries.md Section 1B'
    ),
    'SALE_PRESSURE_13D': (
        'EDGAR SC 13D Item 4 sale-process phrase search; source_queries.md Section 1B'
    ),
    'GOVERNANCE_ONLY_13D': (
        'EDGAR SC 13D Item 4 governance phrase search; item4_parser governance-only calibration queue'
    ),
    'ROFR_ROFN_CASE': (
        'EDGAR 8-K and 10-K ROFR/ROFN search; source_queries.md Section 1C'
    ),
    'ASSET_SALE': (
        'EDGAR 8-K asset purchase agreement search; source_queries.md Section 1E'
    ),
    'CAPITAL_RAISE_AFTER_PROCESS': (
        'EDGAR 8-K/S-3 capital raise search after process language'
    ),
    'BANKRUPTCY_OR_WIND_DOWN': (
        'EDGAR 8-K wind-down and bankruptcy search; source_queries.md Section 1D'
    ),
    'REVERSE_MERGER': (
        'EDGAR 8-K reverse merger and strategic alternatives follow-up search'
    ),
}

SOURCE_URLS = {
    'COMPLETED_DEAL': 'https://www.biopharmadive.com/news/biotech-pharma-deals-merger-acquisitions-tracker/604262/',
    'FAILED_STRATEGIC_REVIEW': 'https://efts.sec.gov/LATEST/search-index',
    'ACTIVIST_13D_NO_DEAL': 'https://www.sec.gov/edgar/search/',
    'SALE_PRESSURE_13D': 'https://www.sec.gov/edgar/search/',
    'GOVERNANCE_ONLY_13D': 'https://www.sec.gov/edgar/search/',
    'ROFR_ROFN_CASE': 'https://efts.sec.gov/LATEST/search-index',
    'ASSET_SALE': 'https://efts.sec.gov/LATEST/search-index',
    'CAPITAL_RAISE_AFTER_PROCESS': 'https://www.sec.gov/edgar/search/',
    'BANKRUPTCY_OR_WIND_DOWN': 'https://efts.sec.gov/LATEST/search-index',
    'REVERSE_MERGER': 'https://efts.sec.gov/LATEST/search-index',
}

CATEGORY_PHRASES = {
    'COMPLETED_DEAL': '"agreement and plan of merger" "per share"',
    'FAILED_STRATEGIC_REVIEW': '"strategic alternatives" "board of directors"',
    'ACTIVIST_13D_NO_DEAL': '"Item 4" "board representation"',
    'SALE_PRESSURE_13D': '"Item 4" "sale of the company"',
    'GOVERNANCE_ONLY_13D': '"Item 4" "board of directors" "governance"',
    'ROFR_ROFN_CASE': '"right of first refusal" OR "right of first negotiation"',
    'ASSET_SALE': '"asset purchase agreement" "program"',
    'CAPITAL_RAISE_AFTER_PROCESS': '"strategic alternatives" "registered direct offering"',
    'BANKRUPTCY_OR_WIND_DOWN': '"wind down" OR "chapter 11" OR "cease operations"',
    'REVERSE_MERGER': '"strategic alternatives" "reverse merger"',
}

CATEGORY_FORMS = {
    'COMPLETED_DEAL': '8-K',
    'FAILED_STRATEGIC_REVIEW': '8-K',
    'ACTIVIST_13D_NO_DEAL': 'SC 13D,SC 13D/A',
    'SALE_PRESSURE_13D': 'SC 13D,SC 13D/A',
    'GOVERNANCE_ONLY_13D': 'SC 13D,SC 13D/A',
    'ROFR_ROFN_CASE': '8-K,10-K,10-Q',
    'ASSET_SALE': '8-K',
    'CAPITAL_RAISE_AFTER_PROCESS': '8-K,S-3,424B5',
    'BANKRUPTCY_OR_WIND_DOWN': '8-K',
    'REVERSE_MERGER': '8-K',
}


@dataclass
class UniverseCompany:
    ticker: str
    company_name: str
    score: float
    mcap_m: float
    has_activist_13d: bool
    strategic_alternatives: bool
    has_rofn: bool
    has_recent_8k: bool
    runway_q: float
    phase3_count: int
    top_signals: str
    flags: str
    source: str


def boolish(value) -> bool:
    return str(value).strip().lower() in {'true', '1', 'yes', 'y'}


def number(value, default=0.0) -> float:
    try:
        if value in ('', None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def read_existing_tickers(paths: list[Path]) -> set[str]:
    tickers: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        with path.open(newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = (row.get('ticker') or '').strip().upper()
                if ticker:
                    tickers.add(ticker)
    return tickers


def read_predictions(path: Path) -> dict[str, UniverseCompany]:
    companies: dict[str, UniverseCompany] = {}
    if not path.exists():
        return companies

    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = (row.get('ticker') or '').strip().upper()
            company = (row.get('company') or '').strip()
            if not ticker or not company:
                continue
            companies[ticker] = UniverseCompany(
                ticker=ticker,
                company_name=company,
                score=number(row.get('score')),
                mcap_m=number(row.get('mcap_M')),
                has_activist_13d=boolish(row.get('has_activist_13d')),
                strategic_alternatives=boolish(row.get('strategic_alternatives')),
                has_rofn=boolish(row.get('has_rofn')),
                has_recent_8k=boolish(row.get('has_recent_8k')),
                runway_q=number(row.get('runway_Q'), default=99.0),
                phase3_count=int(number(row.get('phase3_count'))),
                top_signals=(row.get('top_signals') or '').strip(),
                flags=(row.get('flags') or '').strip(),
                source='predictions_v12.csv',
            )
    return companies


def read_scan(path: Path) -> dict[str, UniverseCompany]:
    companies: dict[str, UniverseCompany] = {}
    if not path.exists():
        return companies

    data = json.loads(path.read_text())
    for row in data:
        ticker = (row.get('ticker') or '').strip().upper()
        company = (row.get('company') or '').strip()
        if not ticker or not company:
            continue
        signals = ' | '.join(stringify_item(item) for item in (row.get('signals') or []))
        flags = ' | '.join(stringify_item(item) for item in (row.get('flags') or []))
        companies[ticker] = UniverseCompany(
            ticker=ticker,
            company_name=company,
            score=number(row.get('score')),
            mcap_m=number(row.get('mcap_M')),
            has_activist_13d='13D' in signals or '13D' in flags,
            strategic_alternatives='strategic alternatives' in signals.lower(),
            has_rofn='ROFR' in signals or 'ROFN' in signals or 'right of first' in signals.lower(),
            has_recent_8k='8-K' in signals or '8-K' in flags,
            runway_q=number(row.get('runway_Q'), default=99.0),
            phase3_count=int(number(row.get('phase3_count'))),
            top_signals=signals,
            flags=flags,
            source='scan_latest.json',
        )
    return companies


def stringify_item(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return ' '.join(str(v) for v in item.values() if v not in ('', None))
    return str(item)


def merge_universe(primary: dict[str, UniverseCompany],
                   secondary: dict[str, UniverseCompany]) -> dict[str, UniverseCompany]:
    merged = dict(primary)
    for ticker, company in secondary.items():
        merged.setdefault(ticker, company)
    return merged


def choose_category(company: UniverseCompany, index: int) -> tuple[str, str, str]:
    text = f'{company.top_signals} {company.flags}'.lower()
    if company.has_rofn:
        return 'ROFR_ROFN_CASE', 'MED', 'HIGH'
    if company.strategic_alternatives:
        return 'FAILED_STRATEGIC_REVIEW', 'MED', 'HIGH'
    if company.has_activist_13d and any(token in text for token in ('sale', 'strategic alternatives', 'maximize shareholder')):
        return 'SALE_PRESSURE_13D', 'MED', 'HIGH'
    if company.has_activist_13d:
        return 'ACTIVIST_13D_NO_DEAL', 'MED', 'MED'
    if company.mcap_m and company.mcap_m < 150 and company.runway_q < 8:
        return 'BANKRUPTCY_OR_WIND_DOWN', 'LOW', 'MED'
    if company.has_recent_8k and company.mcap_m and company.mcap_m < 500:
        return 'CAPITAL_RAISE_AFTER_PROCESS', 'LOW', 'MED'
    if company.phase3_count >= 2 and 150 <= company.mcap_m <= 1500:
        return 'COMPLETED_DEAL', 'LOW', 'MED'
    return CATEGORIES[index % len(CATEGORIES)], 'LOW', 'LOW'


def edgar_query(ticker: str, company_name: str, category: str) -> str:
    phrase = CATEGORY_PHRASES[category]
    forms = quote_plus(CATEGORY_FORMS[category])
    query = quote_plus(f'{ticker} "{company_name}" {phrase}')
    return (
        'https://efts.sec.gov/LATEST/search-index?'
        f'q={query}&forms={forms}&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31'
    )


def reason_for(company: UniverseCompany, category: str, confidence: str) -> str:
    if confidence != 'LOW':
        reasons = []
        if company.has_rofn:
            reasons.append('local scanner row indicates possible ROFR/ROFN signal')
        if company.strategic_alternatives:
            reasons.append('local scanner row indicates strategic alternatives language')
        if company.has_activist_13d:
            reasons.append('local scanner row indicates SC 13D activity')
        if reasons:
            return '; '.join(reasons)
    return (
        f'{company.ticker} appears in the local biotech scanner universe; row is a '
        f'category-specific EDGAR search target for {category}, not verified evidence'
    )


def build_candidate(company: UniverseCompany, category: str, confidence: str,
                    priority: str, index: int) -> dict[str, str]:
    year = '2018-2024'
    return {
        'candidate_id': f'CAND-{index:04d}-{category}-{company.ticker}',
        'ticker': company.ticker,
        'company_name': company.company_name,
        'category': category,
        'likely_event_year': year,
        'source_hint': SOURCE_HINTS[category],
        'source_url_if_known': SOURCE_URLS[category],
        'edgar_query': edgar_query(company.ticker, company.company_name, category),
        'confidence_level': confidence,
        'priority': priority,
        'verification_status': 'CANDIDATE',
        'reason_for_inclusion': reason_for(company, category, confidence),
        'fields_needed_for_partial': FIELDS_NEEDED[category],
        'notes': (
            f'Generated from {company.source}. Candidate only. '
            'Do not promote without EDGAR/source_evidence verification.'
        ),
    }


def generate_candidates(universe: dict[str, UniverseCompany], existing_tickers: set[str],
                        limit: int) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    used_pairs: set[tuple[str, str]] = set()
    sorted_companies = sorted(
        (c for c in universe.values() if c.ticker not in existing_tickers),
        key=lambda c: (
            not c.has_rofn,
            not c.strategic_alternatives,
            not c.has_activist_13d,
            -c.score,
            c.ticker,
        ),
    )

    for i, company in enumerate(sorted_companies):
        category, confidence, priority = choose_category(company, i)
        candidates.append(build_candidate(company, category, confidence, priority, len(candidates) + 1))
        used_pairs.add((company.ticker, category))
        if len(candidates) >= limit:
            return candidates

    for category in CATEGORIES:
        for company in sorted_companies:
            pair = (company.ticker, category)
            if pair in used_pairs:
                continue
            candidates.append(build_candidate(company, category, 'LOW', 'LOW', len(candidates) + 1))
            used_pairs.add(pair)
            if len(candidates) >= limit:
                return candidates
    return candidates


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def priority_rank(row: dict[str, str]) -> tuple[int, int, str]:
    priority = {'HIGH': 0, 'MED': 1, 'LOW': 2}.get(row['priority'], 3)
    confidence = {'HIGH': 0, 'MED': 1, 'LOW': 2}.get(row['confidence_level'], 3)
    return priority, confidence, row['ticker']


def write_sources(path: Path) -> None:
    path.write_text("""# Candidate Generation Sources

This file documents discovery sources for `candidate_case_universe.csv`.
Rows generated by `candidate_case_generator.py` are CANDIDATE search targets only.
They are not source-backed cases and must not be promoted without EDGAR/source_evidence verification.

## Local Sources

- `data/historical_cases/collection_targets.csv`: existing manually curated targets. Used only for dedupe, not duplicated into the candidate universe.
- `data/historical_cases/cases_seed.csv`: existing seeded cases. Used only for dedupe, not duplicated into the candidate universe.
- `data/historical_cases/source_queries.md`: EDGAR, 13D, ROFR/ROFN, bankruptcy, asset-sale, and price-query templates.
- `data/predictions/predictions_v12.csv`: scanner universe and local signal hints.
- `data/scans/scan_latest.json`: fallback scanner universe and local signal hints.

## External Source Hints

- BioPharma Dive M&A tracker: https://www.biopharmadive.com/news/biotech-pharma-deals-merger-acquisitions-tracker/604262/
  - Use only as a secondary discovery source for completed public-company acquisition candidates.
  - Tracker scope: human-medicine company buyouts since 2018 with at least $50M upfront consideration.
  - EDGAR merger agreement filings remain required for PARTIAL or VERIFIED status.
- Biotechgate life sciences M&A reports and archives: https://www.biotechgate.com/
  - Use only as a secondary discovery source for deal and archive discovery.
  - Report scope: quarterly life-sciences M&A transaction reporting based on Biotechgate transaction data.
  - EDGAR filings remain required before any case status promotion.
- SEC EDGAR full-text search: https://efts.sec.gov/LATEST/search-index
  - Primary discovery path for 8-K strategic alternatives, merger agreements, ROFR/ROFN, wind-downs, bankruptcies, asset sales, and reverse mergers.
- SEC EDGAR company search: https://www.sec.gov/edgar/search/
  - Primary discovery path for SC 13D Item 4 text and company-specific filing history.
- WhaleWisdom 13D discovery: https://whalewisdom.com/filer_13d
  - Secondary 13D discovery source only. Item 4 classification must come from EDGAR filing text.

## Status Rules

- `verification_status` must remain `CANDIDATE`.
- Candidate rows do not support PARTIAL, VERIFIED, or CALIBRATION_ELIGIBLE status.
- Candidate rows are source hints and query targets, not evidence rows.
""")


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    lines = [
        '| ' + ' | '.join(columns) + ' |',
        '| ' + ' | '.join(['---'] * len(columns)) + ' |',
    ]
    for row in rows:
        lines.append('| ' + ' | '.join(row.get(col, '') for col in columns) + ' |')
    return '\n'.join(lines)


def write_report(path: Path, candidates: list[dict[str, str]]) -> None:
    by_category = Counter(row['category'] for row in candidates)
    by_year = Counter(row['likely_event_year'] for row in candidates)
    top50 = sorted(candidates, key=priority_rank)[:50]
    easiest = [
        row for row in top50
        if row['category'] in {
            'COMPLETED_DEAL',
            'FAILED_STRATEGIC_REVIEW',
            'ACTIVIST_13D_NO_DEAL',
            'SALE_PRESSURE_13D',
            'ROFR_ROFN_CASE',
        }
    ][:20]
    underrepresented = [
        category for category in CATEGORIES
        if by_category.get(category, 0) < 15
    ]

    category_rows = [{'category': k, 'count': str(by_category.get(k, 0))} for k in CATEGORIES]
    year_rows = [{'likely_event_year': k, 'count': str(v)} for k, v in sorted(by_year.items())]
    top_rows = [
        {
            'candidate_id': row['candidate_id'],
            'ticker': row['ticker'],
            'company_name': row['company_name'],
            'category': row['category'],
            'priority': row['priority'],
            'confidence_level': row['confidence_level'],
        }
        for row in top50
    ]
    easiest_rows = [
        {
            'ticker': row['ticker'],
            'company_name': row['company_name'],
            'category': row['category'],
            'why_easy': row['source_hint'],
        }
        for row in easiest
    ]

    path.write_text(f"""# Candidate Generation Report

Generated by `src/historical_case_tools/candidate_case_generator.py`.

## Summary

- Total candidate rows: {len(candidates)}
- Verification status: CANDIDATE only
- Existing `cases_seed.csv` and `collection_targets.csv` tickers were excluded from the generated universe.
- No rows are PARTIAL, VERIFIED, or CALIBRATION_ELIGIBLE.

## Count By Category

{markdown_table(category_rows, ['category', 'count'])}

## Count By Year

{markdown_table(year_rows, ['likely_event_year', 'count'])}

## Top 50 Highest-Priority Cases To Verify First

{markdown_table(top_rows, ['candidate_id', 'ticker', 'company_name', 'category', 'priority', 'confidence_level'])}

## Likely Easiest To Verify

{markdown_table(easiest_rows, ['ticker', 'company_name', 'category', 'why_easy'])}

## Underrepresented Categories

{', '.join(underrepresented) if underrepresented else 'None'}

## Notes

Rows with MED confidence come from local scanner fields such as possible SC 13D activity, strategic alternatives language, or ROFR/ROFN indicators. LOW confidence rows are deterministic EDGAR search targets. They should be treated as sourcing leads, not factual case records.
""")


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate historical case candidate search targets.')
    parser.add_argument('--predictions', default=str(DEFAULT_PREDICTIONS))
    parser.add_argument('--scan', default=str(DEFAULT_SCAN))
    parser.add_argument('--cases-seed', default=str(DEFAULT_SEED))
    parser.add_argument('--collection-targets', default=str(DEFAULT_TARGETS))
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--sources-output', default=str(DEFAULT_SOURCES))
    parser.add_argument('--report-output', default=str(DEFAULT_REPORT))
    parser.add_argument('--limit', type=int, default=300)
    args = parser.parse_args()

    predictions = read_predictions(Path(args.predictions))
    scan = read_scan(Path(args.scan))
    universe = merge_universe(predictions, scan)
    existing = read_existing_tickers([Path(args.cases_seed), Path(args.collection_targets)])
    candidates = generate_candidates(universe, existing, args.limit)

    write_csv(Path(args.output), candidates)
    write_sources(Path(args.sources_output))
    write_report(Path(args.report_output), candidates)

    by_category = Counter(row['category'] for row in candidates)
    print(f'Generated {len(candidates)} candidates -> {args.output}')
    for category in CATEGORIES:
        print(f'{category}: {by_category.get(category, 0)}')
    print(f'Sources -> {args.sources_output}')
    print(f'Report -> {args.report_output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
