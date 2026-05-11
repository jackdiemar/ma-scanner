#!/usr/bin/env python3
"""
candidate_triage.py

Triage generated CANDIDATE rows before verification.

This tool does not verify cases, assign PARTIAL/VERIFIED status, or mark any
row calibration-ready. It separates likely historical verification targets from
live/unresolved and weak query rows.

Usage:
    python src/historical_case_tools/candidate_triage.py
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'
DEFAULT_INPUT = HISTORICAL_DIR / 'candidate_case_universe.csv'
DEFAULT_OUTPUT = HISTORICAL_DIR / 'candidate_case_universe_triaged.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'candidate_triage_report.md'
DEFAULT_PREDICTIONS = REPO_ROOT / 'data' / 'predictions' / 'predictions_v12.csv'
DEFAULT_SCAN = REPO_ROOT / 'data' / 'scans' / 'scan_latest.json'

TRIAGE_FIELDS = [
    'triage_bucket',
    'outcome_known_flag',
    'likely_resolved_historical',
    'likely_live_unresolved',
    'verification_priority_score',
    'reason_for_triage',
    'next_best_source',
    'next_verification_action',
]

TRIAGE_BUCKETS = [
    'RESOLVED_HISTORICAL_PRIORITY',
    'RESOLVED_HISTORICAL_SECONDARY',
    'LIVE_UNRESOLVED',
    'NEEDS_OUTCOME_CHECK',
    'WEAK_QUERY_TARGET',
    'LIKELY_BAD_TARGET',
]

PRIORITY_POINTS = {'HIGH': 30, 'MED': 18, 'LOW': 4}
CONFIDENCE_POINTS = {'HIGH': 30, 'MED': 18, 'LOW': 3}

CATEGORY_BASE_POINTS = {
    'COMPLETED_DEAL': 26,
    'BANKRUPTCY_OR_WIND_DOWN': 24,
    'FAILED_STRATEGIC_REVIEW': 22,
    'ACTIVIST_13D_NO_DEAL': 18,
    'SALE_PRESSURE_13D': 18,
    'REVERSE_MERGER': 17,
    'ASSET_SALE': 15,
    'ROFR_ROFN_CASE': 14,
    'CAPITAL_RAISE_AFTER_PROCESS': 12,
    'GOVERNANCE_ONLY_13D': 10,
}

NEXT_BEST_SOURCE = {
    'COMPLETED_DEAL': 'BioPharma Dive tracker, then EDGAR merger 8-K',
    'FAILED_STRATEGIC_REVIEW': 'EDGAR 8-K strategic alternatives search',
    'ACTIVIST_13D_NO_DEAL': 'EDGAR SC 13D Item 4 filing text',
    'SALE_PRESSURE_13D': 'EDGAR SC 13D Item 4 sale-process phrase search',
    'GOVERNANCE_ONLY_13D': 'EDGAR SC 13D Item 4 governance phrase search',
    'ROFR_ROFN_CASE': 'EDGAR 8-K/10-K agreement exhibit search',
    'ASSET_SALE': 'EDGAR 8-K asset purchase agreement search',
    'CAPITAL_RAISE_AFTER_PROCESS': 'EDGAR 8-K/S-3 capital raise search after process-language check',
    'BANKRUPTCY_OR_WIND_DOWN': 'EDGAR 8-K wind-down or bankruptcy filing search',
    'REVERSE_MERGER': 'EDGAR 8-K strategic alternatives and reverse merger follow-up search',
}

NEXT_ACTION = {
    'COMPLETED_DEAL': 'Confirm whether an actual announced acquisition exists, then pull merger 8-K and search prior process filings.',
    'FAILED_STRATEGIC_REVIEW': 'Search 8-Ks for strategic alternatives language, then check later 8-Ks for outcome.',
    'ACTIVIST_13D_NO_DEAL': 'Find the initial SC 13D, extract Item 4, then verify no subsequent deal within the outcome window.',
    'SALE_PRESSURE_13D': 'Find Item 4 sale-pressure language and then verify whether a deal, no-deal, or stale outcome followed.',
    'GOVERNANCE_ONLY_13D': 'Find Item 4 and classify governance-only language before using as a false-positive calibration case.',
    'ROFR_ROFN_CASE': 'Find the agreement exhibit and classify ROFR/ROFN scope before checking later outcome.',
    'ASSET_SALE': 'Find the asset-sale 8-K and confirm whether the transaction is asset-only, not whole-company.',
    'CAPITAL_RAISE_AFTER_PROCESS': 'Confirm a prior process signal before treating a later financing as process outcome.',
    'BANKRUPTCY_OR_WIND_DOWN': 'Find the wind-down or bankruptcy 8-K and look backward for any process announcement.',
    'REVERSE_MERGER': 'Find the reverse merger 8-K and look backward for strategic alternatives language.',
}

BAD_TARGET_TERMS = {
    'homecare',
    'animal health',
    'genetics, inc. common stock',
    'bio-medical science',
    'accolade',
    'atricure',
    'invitae',
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_active_tickers(predictions_path: Path, scan_path: Path) -> set[str]:
    active: set[str] = set()
    if predictions_path.exists():
        with predictions_path.open(newline='') as f:
            for row in csv.DictReader(f):
                ticker = (row.get('ticker') or '').strip().upper()
                if ticker:
                    active.add(ticker)
    if scan_path.exists():
        data = json.loads(scan_path.read_text())
        for row in data:
            ticker = (row.get('ticker') or '').strip().upper()
            if ticker:
                active.add(ticker)
    return active


def is_range_year(value: str) -> bool:
    return '-' in (value or '') or not (value or '').strip().isdigit()


def is_likely_bad_target(row: dict[str, str]) -> bool:
    text = f"{row.get('ticker', '')} {row.get('company_name', '')} {row.get('reason_for_inclusion', '')}".lower()
    return any(term in text for term in BAD_TARGET_TERMS)


def score_row(row: dict[str, str], active_tickers: set[str]) -> int:
    category = row['category']
    score = CATEGORY_BASE_POINTS.get(category, 5)
    score += PRIORITY_POINTS.get(row.get('priority'), 0)
    score += CONFIDENCE_POINTS.get(row.get('confidence_level'), 0)

    if row['ticker'] in active_tickers:
        score -= 12
    if is_range_year(row.get('likely_event_year', '')):
        score -= 8
    if 'not verified evidence' in row.get('reason_for_inclusion', '').lower():
        score -= 10
    if row.get('priority') == 'LOW' and row.get('confidence_level') == 'LOW':
        score -= 12
    if category in {'COMPLETED_DEAL', 'BANKRUPTCY_OR_WIND_DOWN', 'REVERSE_MERGER'}:
        score += 8
    if is_likely_bad_target(row):
        score -= 35
    return max(0, min(100, score))


def triage_row(row: dict[str, str], active_tickers: set[str]) -> dict[str, str]:
    category = row['category']
    ticker = row['ticker']
    score = score_row(row, active_tickers)
    priority = row.get('priority')
    confidence = row.get('confidence_level')
    range_year = is_range_year(row.get('likely_event_year', ''))
    active = ticker in active_tickers
    generic_query = 'not verified evidence' in row.get('reason_for_inclusion', '').lower()
    bad_target = is_likely_bad_target(row)

    outcome_known = 'FALSE'
    likely_resolved = 'FALSE'
    likely_live = 'TRUE' if active else 'FALSE'

    if bad_target:
        bucket = 'LIKELY_BAD_TARGET'
        reason = 'Company/category appears outside the clean biotech historical-process target set or is too ambiguous.'
    elif generic_query and priority == 'LOW' and confidence == 'LOW':
        if active:
            bucket = 'LIVE_UNRESOLVED' if category in {'COMPLETED_DEAL', 'FAILED_STRATEGIC_REVIEW', 'ROFR_ROFN_CASE'} else 'WEAK_QUERY_TARGET'
            reason = 'Low-confidence row generated from a current scanner ticker; no historical outcome should be assumed.'
        else:
            bucket = 'WEAK_QUERY_TARGET'
            reason = 'Low-confidence deterministic EDGAR query row with no known event or outcome.'
    elif active and category in {'FAILED_STRATEGIC_REVIEW', 'ROFR_ROFN_CASE', 'ACTIVIST_13D_NO_DEAL', 'SALE_PRESSURE_13D'}:
        bucket = 'NEEDS_OUTCOME_CHECK'
        reason = 'Local scanner hints suggest a possible process signal, but ticker remains in the active universe; outcome must be checked.'
    elif category in {'COMPLETED_DEAL', 'BANKRUPTCY_OR_WIND_DOWN', 'REVERSE_MERGER'} and not range_year and confidence != 'LOW':
        bucket = 'RESOLVED_HISTORICAL_PRIORITY'
        outcome_known = 'TRUE'
        likely_resolved = 'TRUE'
        likely_live = 'FALSE'
        reason = 'Specific historical year plus higher-confidence resolved-event category makes this a clean verification target.'
    elif category in {'COMPLETED_DEAL', 'BANKRUPTCY_OR_WIND_DOWN', 'REVERSE_MERGER', 'ASSET_SALE'} and confidence != 'LOW':
        bucket = 'RESOLVED_HISTORICAL_SECONDARY'
        likely_resolved = 'TRUE'
        reason = 'Resolved-event category with some source strength, but outcome still needs primary-source confirmation.'
    else:
        bucket = 'NEEDS_OUTCOME_CHECK'
        reason = 'Candidate has some verification value, but outcome is not known from the row and must be checked before use.'

    if bucket in {'WEAK_QUERY_TARGET', 'LIKELY_BAD_TARGET'}:
        score = min(score, 20)
    if bucket == 'LIVE_UNRESOLVED':
        score = min(score, 35)
    if bucket == 'NEEDS_OUTCOME_CHECK':
        score = min(score, 60)

    row.update({
        'triage_bucket': bucket,
        'outcome_known_flag': outcome_known,
        'likely_resolved_historical': likely_resolved,
        'likely_live_unresolved': likely_live,
        'verification_priority_score': str(score),
        'reason_for_triage': reason,
        'next_best_source': NEXT_BEST_SOURCE.get(category, 'EDGAR company filing search'),
        'next_verification_action': NEXT_ACTION.get(category, 'Run EDGAR search and confirm source-backed event details.'),
    })
    return row


def sort_key(row: dict[str, str]) -> tuple[int, int, str]:
    bucket_rank = {
        'RESOLVED_HISTORICAL_PRIORITY': 0,
        'RESOLVED_HISTORICAL_SECONDARY': 1,
        'NEEDS_OUTCOME_CHECK': 2,
        'LIVE_UNRESOLVED': 3,
        'WEAK_QUERY_TARGET': 4,
        'LIKELY_BAD_TARGET': 5,
    }
    return (
        bucket_rank.get(row['triage_bucket'], 9),
        -int(row['verification_priority_score']),
        row['ticker'],
    )


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    lines = [
        '| ' + ' | '.join(columns) + ' |',
        '| ' + ' | '.join(['---'] * len(columns)) + ' |',
    ]
    for row in rows:
        lines.append('| ' + ' | '.join(str(row.get(col, '')) for col in columns) + ' |')
    return '\n'.join(lines)


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    by_bucket = Counter(row['triage_bucket'] for row in rows)
    by_category_bucket = defaultdict(Counter)
    for row in rows:
        by_category_bucket[row['category']][row['triage_bucket']] += 1

    top_resolved = [
        row for row in sorted(rows, key=sort_key)
        if row['triage_bucket'] in {'RESOLVED_HISTORICAL_PRIORITY', 'RESOLVED_HISTORICAL_SECONDARY', 'NEEDS_OUTCOME_CHECK'}
    ][:50]
    deprioritized = [
        row for row in sorted(rows, key=sort_key)
        if row['triage_bucket'] in {'LIVE_UNRESOLVED', 'WEAK_QUERY_TARGET', 'LIKELY_BAD_TARGET'}
    ][:50]

    bucket_rows = [{'triage_bucket': bucket, 'count': by_bucket.get(bucket, 0)} for bucket in TRIAGE_BUCKETS]
    category_rows = []
    for category in sorted(by_category_bucket):
        total = sum(by_category_bucket[category].values())
        category_rows.append({
            'category': category,
            'total': total,
            'resolved_priority': by_category_bucket[category].get('RESOLVED_HISTORICAL_PRIORITY', 0),
            'resolved_secondary': by_category_bucket[category].get('RESOLVED_HISTORICAL_SECONDARY', 0),
            'needs_outcome_check': by_category_bucket[category].get('NEEDS_OUTCOME_CHECK', 0),
            'live_unresolved': by_category_bucket[category].get('LIVE_UNRESOLVED', 0),
            'weak_or_bad': (
                by_category_bucket[category].get('WEAK_QUERY_TARGET', 0) +
                by_category_bucket[category].get('LIKELY_BAD_TARGET', 0)
            ),
        })

    top_rows = [{
        'candidate_id': row['candidate_id'],
        'ticker': row['ticker'],
        'company_name': row['company_name'],
        'category': row['category'],
        'triage_bucket': row['triage_bucket'],
        'score': row['verification_priority_score'],
    } for row in top_resolved]

    deprioritized_rows = [{
        'candidate_id': row['candidate_id'],
        'ticker': row['ticker'],
        'company_name': row['company_name'],
        'category': row['category'],
        'triage_bucket': row['triage_bucket'],
        'reason': row['reason_for_triage'],
    } for row in deprioritized]

    path.write_text(f"""# Candidate Triage Report

Generated by `src/historical_case_tools/candidate_triage.py`.

## Summary

- Total triaged rows: {len(rows)}
- No rows are PARTIAL, VERIFIED, or CALIBRATION_ELIGIBLE.
- Triage is conservative. Current scanner-universe tickers are not treated as resolved unless the candidate row has a specific, higher-confidence historical signal.
- `outcome_known_flag=TRUE` means the row shape suggests a resolved historical category, not that the case is verified.

## Count By Triage Bucket

{markdown_table(bucket_rows, ['triage_bucket', 'count'])}

## Top 50 Resolved Historical Verification Targets

No row currently qualifies for `RESOLVED_HISTORICAL_PRIORITY` or `RESOLVED_HISTORICAL_SECONDARY` without an outcome check. The table below shows the closest resolved-historical verification targets to check first.

{markdown_table(top_rows, ['candidate_id', 'ticker', 'company_name', 'category', 'triage_bucket', 'score'])}

## Cases To Deprioritize

{markdown_table(deprioritized_rows, ['candidate_id', 'ticker', 'company_name', 'category', 'triage_bucket', 'reason'])}

## Category Balance After Triage

{markdown_table(category_rows, ['category', 'total', 'resolved_priority', 'resolved_secondary', 'needs_outcome_check', 'live_unresolved', 'weak_or_bad'])}

## Interpretation

`NEEDS_OUTCOME_CHECK` is the main useful queue for the current candidate universe. Most rows were generated from live scanner tickers and broad EDGAR query templates, so they should be checked for actual historical outcomes before verification work begins.
""")


def main() -> int:
    parser = argparse.ArgumentParser(description='Triage historical candidate case universe rows.')
    parser.add_argument('--input', default=str(DEFAULT_INPUT))
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--report-output', default=str(DEFAULT_REPORT))
    parser.add_argument('--predictions', default=str(DEFAULT_PREDICTIONS))
    parser.add_argument('--scan', default=str(DEFAULT_SCAN))
    args = parser.parse_args()

    rows = read_csv(Path(args.input))
    active_tickers = read_active_tickers(Path(args.predictions), Path(args.scan))
    triaged = [triage_row(dict(row), active_tickers) for row in rows]
    fieldnames = list(rows[0].keys()) + [field for field in TRIAGE_FIELDS if field not in rows[0]]

    write_csv(Path(args.output), sorted(triaged, key=sort_key), fieldnames)
    write_report(Path(args.report_output), triaged)

    counts = Counter(row['triage_bucket'] for row in triaged)
    print(f'Triaged {len(triaged)} candidates -> {args.output}')
    for bucket in TRIAGE_BUCKETS:
        print(f'{bucket}: {counts.get(bucket, 0)}')
    print(f'Report -> {args.report_output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
