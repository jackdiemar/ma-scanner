#!/usr/bin/env python3
"""
acquisition_batch_enricher.py

Build batch enrichment outputs for the first 10 acquisition cases.

The workflow is deterministic and source-conservative. It reads existing
source-backed acquisition evidence and background findings, writes enrichment
sidecars, and updates background findings only for prior-process review and
observation-date candidate fields. It never marks cases VERIFIED or
CALIBRATION_ELIGIBLE.

Usage:
    python3 src/historical_case_tools/acquisition_batch_enricher.py
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'

DEFAULT_SOURCE_EVIDENCE = HISTORICAL_DIR / 'source_evidence.csv'
DEFAULT_BACKGROUND_FINDINGS = HISTORICAL_DIR / 'acquisition_background_findings.csv'
DEFAULT_CASES_PARTIAL = HISTORICAL_DIR / 'cases_partial.csv'
DEFAULT_PRICE_WINDOWS = HISTORICAL_DIR / 'price_windows.csv'
DEFAULT_PACKET_INDEX = HISTORICAL_DIR / 'case_packet_index.csv'

DEFAULT_PREMIUM_FINDINGS = HISTORICAL_DIR / 'acquisition_premium_findings.csv'
DEFAULT_OBSERVATION_CANDIDATES = HISTORICAL_DIR / 'observation_date_candidates.csv'
DEFAULT_READINESS = HISTORICAL_DIR / 'first10_verification_readiness.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'acquisition_batch_enrichment_report.md'

RUN_DATE = '2026-05-12'
TARGET_TICKERS = ['NPSP', 'PCYC', 'ZSPH', 'ANAC', 'MDVN', 'TBRA', 'ARIA', 'KITE', 'BIVV', 'JUNO']
SOURCE_BACKED_STATUSES = {'VERIFIED', 'PARTIAL'}
CORE_EVIDENCE_TYPES = {'8K_MERGER', 'MERGER_8K', 'SC_TO_T', 'SC_TO_I'}
MISSING_VALUES = {'', 'VERIFY_REQUIRED', 'UNKNOWN', 'TBD', 'N/A', 'NA', 'NULL', 'NONE'}

BACKGROUND_FIELDS = [
    'case_id',
    'ticker',
    'company',
    'proxy_source_url',
    'proxy_filing_type',
    'proxy_filing_date',
    'background_section_available',
    'background_heading',
    'first_public_acquisition_announcement_date',
    'prior_process_signal',
    'prior_process_signal_type',
    'prior_process_signal_date',
    'relevant_excerpt',
    'confidence',
    'observation_date_candidate',
    'observation_date_reasoning',
    'remaining_evidence_gaps',
]

PREMIUM_FIELDS = [
    'case_id',
    'ticker',
    'company',
    'consideration_status',
    'deal_price_or_consideration',
    'consideration_source_evidence_id',
    'consideration_source_url',
    'consideration_excerpt',
    'premium_status',
    'premium_value',
    'premium_source_url',
    'confidence',
    'remaining_gaps',
]

OBSERVATION_FIELDS = [
    'case_id',
    'ticker',
    'company',
    'prior_process_signal',
    'prior_process_signal_type',
    'prior_process_signal_date',
    'manual_no_hit_confirmation_needed',
    'observation_date_candidate',
    'observation_date_reasoning',
    'source_url',
    'source_excerpt',
    'confidence',
    'remaining_gaps',
]

READINESS_FIELDS = [
    'case_id',
    'ticker',
    'company',
    'current_status',
    'acquisition_evidence_status',
    'background_section_status',
    'prior_process_signal',
    'observation_date_candidate',
    'premium_status',
    'price_window_status',
    'price_window_fetcher_can_run',
    'remaining_fields_before_verified',
    'recommended_next_action',
    'readiness_score',
    'closest_to_verified_rank',
]

PUBLIC_MARKER_RE = re.compile(
    r'\b(publicly\s+(?:announced|disclosed|confirmed|made)|made\s+public|announced\s+publicly|issued\s+a\s+press\s+release)\b',
    re.I,
)
ACQUISITION_TERM_RE = re.compile(r'\b(proposal|offer|bid|acquir|tender\s+offer|merger)\b', re.I)
PRICE_RE = re.compile(
    r'\$\s?\d+(?:\.\d+)?(?:\s*(?:per|for)\s+(?:Share|share|Juno Share|Company Share))?'
    r'(?:\s+in\s+cash)?(?:\s+plus\s+one\s+[^.;,]+)?',
    re.I,
)


@dataclass
class CaseBundle:
    ticker: str
    case_id: str
    company: str
    evidence_rows: list[dict[str, str]]
    background: dict[str, str]
    partial: dict[str, str]
    price_window: dict[str, str]
    packet_index: dict[str, str]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, '') for field in fields})


def normalize(value: str | None) -> str:
    return str(value or '').strip().upper()


def is_present(value: str | None) -> bool:
    return normalize(value) not in MISSING_VALUES


def group_by(rows: Iterable[dict[str, str]], field: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = row.get(field, '').strip()
        if key:
            grouped.setdefault(key, []).append(row)
    return grouped


def index_by(rows: Iterable[dict[str, str]], field: str) -> dict[str, dict[str, str]]:
    indexed = {}
    for row in rows:
        key = row.get(field, '').strip()
        if key and key not in indexed:
            indexed[key] = row
    return indexed


def indexed_by_ticker(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed = {}
    for row in rows:
        ticker = normalize(row.get('ticker'))
        if ticker and ticker not in indexed:
            indexed[ticker] = row
    return indexed


def clean_excerpt(value: str, max_chars: int = 450) -> str:
    cleaned = re.sub(r'\s+', ' ', value or '').strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(' ', 1)[0].rstrip(' ,.;') + '...'


def source_backed(row: dict[str, str]) -> bool:
    return normalize(row.get('verification_status')) in SOURCE_BACKED_STATUSES


def core_evidence_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    results = []
    for row in rows:
        supports = normalize(row.get('supports_field'))
        evidence_type = normalize(row.get('evidence_type'))
        if not source_backed(row):
            continue
        if evidence_type in CORE_EVIDENCE_TYPES or ('ACQUIRER' in supports and 'DEAL' in supports):
            results.append(row)
    return results


def extract_price_or_consideration(bundle: CaseBundle) -> tuple[str, dict[str, str] | None]:
    partial_price = bundle.partial.get('deal_price_per_share', '')
    if is_present(partial_price):
        return f'${partial_price} per share' if not partial_price.startswith('$') else partial_price, None

    for row in core_evidence_rows(bundle.evidence_rows):
        text = ' '.join([row.get('excerpt', ''), row.get('notes', '')])
        match = PRICE_RE.search(text)
        if match:
            return re.sub(r'\s+', ' ', match.group(0)).strip(), row
    return '', None


def premium_finding(bundle: CaseBundle) -> dict[str, str]:
    consideration, source_row = extract_price_or_consideration(bundle)
    premium_value = bundle.partial.get('deal_premium_pct', '')
    premium_found = is_present(premium_value)

    if source_row is None and is_present(bundle.partial.get('source_filing_url')):
        source_url = bundle.partial.get('source_filing_url', '')
        source_id = 'cases_partial.csv'
        excerpt = bundle.partial.get('excerpt_text', '')
        confidence = 'MEDIUM'
    elif source_row:
        source_url = source_row.get('source_url', '')
        source_id = source_row.get('evidence_id', '')
        excerpt = source_row.get('excerpt', '')
        confidence = source_row.get('confidence', '') or 'MEDIUM'
    else:
        source_url = ''
        source_id = ''
        excerpt = ''
        confidence = 'LOW'

    gaps = []
    if not premium_found:
        gaps.append('premium extraction')
    if not consideration:
        gaps.append('consideration extraction')
    return {
        'case_id': bundle.case_id,
        'ticker': bundle.ticker,
        'company': bundle.company,
        'consideration_status': 'FOUND' if consideration else 'MISSING',
        'deal_price_or_consideration': consideration,
        'consideration_source_evidence_id': source_id,
        'consideration_source_url': source_url,
        'consideration_excerpt': clean_excerpt(excerpt),
        'premium_status': 'FOUND' if premium_found else 'MISSING',
        'premium_value': premium_value if premium_found else '',
        'premium_source_url': source_url if premium_found else '',
        'confidence': confidence if consideration or premium_found else 'LOW',
        'remaining_gaps': '; '.join(gaps),
    }


def classify_prior_process(bundle: CaseBundle) -> dict[str, str]:
    background = bundle.background
    prior = normalize(background.get('prior_process_signal'))
    if prior in {'FOUND_PUBLIC', 'NONE_FOUND'}:
        manual_needed = 'TRUE' if prior == 'NONE_FOUND' else 'FALSE'
        return {
            'prior_process_signal': prior,
            'prior_process_signal_type': background.get('prior_process_signal_type', ''),
            'prior_process_signal_date': background.get('prior_process_signal_date', ''),
            'manual_no_hit_confirmation_needed': manual_needed,
            'observation_date_candidate': background.get('observation_date_candidate', ''),
            'observation_date_reasoning': background.get('observation_date_reasoning', ''),
            'source_url': background.get('proxy_source_url', ''),
            'source_excerpt': background.get('relevant_excerpt', ''),
            'confidence': background.get('confidence', '') or 'MEDIUM',
            'remaining_gaps': background.get('remaining_evidence_gaps', ''),
        }

    text = background.get('relevant_excerpt', '')
    announcement_date = background.get('first_public_acquisition_announcement_date', '')
    if PUBLIC_MARKER_RE.search(text) and ACQUISITION_TERM_RE.search(text):
        signal = 'FOUND_PUBLIC'
        signal_type = 'outreach / competing bids'
        signal_date = ''
        manual_needed = 'FALSE'
        observation_date = ''
        reasoning = (
            'Available background excerpt contains public acquisition-process language, '
            'but the first public signal date still needs source-backed extraction before use.'
        )
        gaps = 'prior public signal date extraction; premium extraction; price-window verification'
        confidence = 'LOW'
    else:
        signal = 'NONE_FOUND'
        signal_type = 'none found'
        signal_date = ''
        manual_needed = 'TRUE'
        observation_date = announcement_date
        reasoning = (
            'No source-backed public pre-announcement process signal was found in the available '
            'background excerpt. Private negotiations disclosed after announcement are not used '
            'as observation dates, so default to the acquisition announcement date pending manual no-hit confirmation.'
        )
        gaps = 'manual no-hit confirmation across pre-announcement filings; premium extraction; price-window verification'
        confidence = 'LOW'

    return {
        'prior_process_signal': signal,
        'prior_process_signal_type': signal_type,
        'prior_process_signal_date': signal_date,
        'manual_no_hit_confirmation_needed': manual_needed,
        'observation_date_candidate': observation_date,
        'observation_date_reasoning': reasoning,
        'source_url': background.get('proxy_source_url', ''),
        'source_excerpt': text,
        'confidence': confidence,
        'remaining_gaps': gaps,
    }


def observation_row(bundle: CaseBundle) -> dict[str, str]:
    prior = classify_prior_process(bundle)
    return {
        'case_id': bundle.case_id,
        'ticker': bundle.ticker,
        'company': bundle.company,
        'prior_process_signal': prior['prior_process_signal'],
        'prior_process_signal_type': prior['prior_process_signal_type'],
        'prior_process_signal_date': prior['prior_process_signal_date'],
        'manual_no_hit_confirmation_needed': prior['manual_no_hit_confirmation_needed'],
        'observation_date_candidate': prior['observation_date_candidate'],
        'observation_date_reasoning': prior['observation_date_reasoning'],
        'source_url': prior['source_url'],
        'source_excerpt': clean_excerpt(prior['source_excerpt']),
        'confidence': prior['confidence'],
        'remaining_gaps': prior['remaining_gaps'],
    }


def price_window_status(bundle: CaseBundle, observation_date: str) -> tuple[str, str]:
    if bundle.price_window:
        complete = (
            normalize(bundle.price_window.get('missing_data_flag')) == 'FALSE'
            and is_present(bundle.price_window.get('price_before_signal'))
            and is_present(bundle.price_window.get('price_30d_after'))
            and is_present(bundle.price_window.get('price_90d_after'))
        )
        return ('READY' if complete else 'ATTEMPTED_INCOMPLETE'), 'FALSE' if complete else 'TRUE'
    return 'NOT_STARTED', 'TRUE' if is_present(observation_date) else 'FALSE'


def remaining_fields(
    observation: dict[str, str],
    premium: dict[str, str],
    price_status: str,
) -> list[str]:
    missing = []
    if observation['prior_process_signal'] == 'NEEDS_MANUAL_CONFIRMATION':
        missing.append('prior process signal review')
    if observation['manual_no_hit_confirmation_needed'] == 'TRUE':
        missing.append('manual no-hit confirmation')
    if not is_present(observation['observation_date_candidate']):
        missing.append('observation date selection')
    if premium['premium_status'] != 'FOUND':
        missing.append('premium extraction')
    if price_status not in {'READY', 'COMPLETED'}:
        missing.append('price-window verification')
    return missing


def recommended_next_action(missing: list[str], observation: dict[str, str]) -> str:
    if 'manual no-hit confirmation' in missing:
        return 'Manually confirm no pre-announcement public process signal across 8-K, 13D, 10-K, and 10-Q filings, then run price-window verification.'
    if 'premium extraction' in missing:
        return 'Extract premium evidence from the proxy or Schedule 14D-9 fairness/offer materials.'
    if 'price-window verification' in missing and is_present(observation['observation_date_candidate']):
        return 'Run price_window_fetcher.py for the observation_date_candidate and verify delisted ticker price data.'
    return 'Review against verification_checklist.md before any future VERIFIED decision.'


def readiness_score(
    bundle: CaseBundle,
    observation: dict[str, str],
    premium: dict[str, str],
    price_status: str,
    missing: list[str],
) -> int:
    score = 0
    if core_evidence_rows(bundle.evidence_rows):
        score += 20
    if bundle.evidence_rows:
        score += 15
    if normalize(bundle.background.get('background_section_available')) == 'TRUE':
        score += 15
    if observation['prior_process_signal'] in {'FOUND_PUBLIC', 'NONE_FOUND'}:
        score += 15
    if is_present(observation['observation_date_candidate']):
        score += 10
    if premium['premium_status'] == 'FOUND':
        score += 10
    if price_status in {'READY', 'COMPLETED'}:
        score += 10
    if missing:
        score += 5
    return score


def readiness_row(bundle: CaseBundle, observation: dict[str, str], premium: dict[str, str]) -> dict[str, str]:
    price_status, can_run = price_window_status(bundle, observation['observation_date_candidate'])
    missing = remaining_fields(observation, premium, price_status)
    current_status = bundle.packet_index.get('current_status') or bundle.partial.get('data_quality') or 'CANDIDATE'
    return {
        'case_id': bundle.case_id,
        'ticker': bundle.ticker,
        'company': bundle.company,
        'current_status': current_status,
        'acquisition_evidence_status': 'SOURCE_BACKED' if core_evidence_rows(bundle.evidence_rows) else 'MISSING',
        'background_section_status': 'FOUND' if normalize(bundle.background.get('background_section_available')) == 'TRUE' else 'MISSING',
        'prior_process_signal': observation['prior_process_signal'],
        'observation_date_candidate': observation['observation_date_candidate'],
        'premium_status': premium['premium_status'],
        'price_window_status': price_status,
        'price_window_fetcher_can_run': can_run,
        'remaining_fields_before_verified': '; '.join(missing),
        'recommended_next_action': recommended_next_action(missing, observation),
        'readiness_score': str(readiness_score(bundle, observation, premium, price_status, missing)),
        'closest_to_verified_rank': '',
    }


def update_background_rows(rows: list[dict[str, str]], observations: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    updated = []
    for row in rows:
        ticker = normalize(row.get('ticker'))
        if ticker in observations:
            obs = observations[ticker]
            row = dict(row)
            row['prior_process_signal'] = obs['prior_process_signal']
            row['prior_process_signal_type'] = obs['prior_process_signal_type']
            row['prior_process_signal_date'] = obs['prior_process_signal_date']
            row['observation_date_candidate'] = obs['observation_date_candidate']
            row['observation_date_reasoning'] = obs['observation_date_reasoning']
            row['remaining_evidence_gaps'] = obs['remaining_gaps']
            if obs['confidence']:
                row['confidence'] = obs['confidence']
        updated.append(row)
    return updated


def apply_ranks(rows: list[dict[str, str]]) -> None:
    ranked = sorted(
        rows,
        key=lambda row: (
            len([field for field in row['remaining_fields_before_verified'].split('; ') if field]),
            -int(row['readiness_score']),
            0 if row['current_status'] == 'PARTIAL' else 1,
            row['case_id'],
        ),
    )
    for index, row in enumerate(ranked, start=1):
        row['closest_to_verified_rank'] = str(index)


def markdown_table(rows: list[dict[str, str]], fields: list[str]) -> list[str]:
    lines = ['| ' + ' | '.join(fields) + ' |']
    lines.append('| ' + ' | '.join('---' for _ in fields) + ' |')
    for row in rows:
        lines.append('| ' + ' | '.join(row.get(field, '') for field in fields) + ' |')
    return lines


def write_report(
    path: Path,
    premium_rows: list[dict[str, str]],
    observation_rows: list[dict[str, str]],
    readiness_rows: list[dict[str, str]],
) -> None:
    closest = sorted(readiness_rows, key=lambda row: int(row['closest_to_verified_rank']))[:5]
    score_counts = Counter(row['readiness_score'] for row in readiness_rows)
    premium_missing = [row['ticker'] for row in premium_rows if row['premium_status'] != 'FOUND']
    price_missing = [row['ticker'] for row in readiness_rows if row['price_window_status'] != 'READY']
    manual_needed = [row['ticker'] for row in observation_rows if row['manual_no_hit_confirmation_needed'] == 'TRUE']

    lines = [
        '# Acquisition Batch Enrichment Report',
        '',
        f'Generated: {RUN_DATE}',
        '',
        '## Summary',
        '',
        f'- Cases enriched: {len(readiness_rows)}',
        f'- Prior process FOUND_PUBLIC: {sum(1 for row in observation_rows if row["prior_process_signal"] == "FOUND_PUBLIC")}',
        f'- Prior process NONE_FOUND: {sum(1 for row in observation_rows if row["prior_process_signal"] == "NONE_FOUND")}',
        f'- Premium findings complete: {sum(1 for row in premium_rows if row["premium_status"] == "FOUND")}',
        f'- Price windows ready: {sum(1 for row in readiness_rows if row["price_window_status"] == "READY")}',
        '- No cases were marked VERIFIED or CALIBRATION_ELIGIBLE.',
        '',
        '## Top 5 Closest To VERIFIED',
        '',
        *markdown_table(closest, ['closest_to_verified_rank', 'case_id', 'ticker', 'current_status', 'readiness_score', 'remaining_fields_before_verified']),
        '',
        '## Observation Date Candidates',
        '',
        *markdown_table(observation_rows, ['case_id', 'ticker', 'prior_process_signal', 'manual_no_hit_confirmation_needed', 'observation_date_candidate']),
        '',
        '## Premium Findings',
        '',
        *markdown_table(premium_rows, ['case_id', 'ticker', 'consideration_status', 'deal_price_or_consideration', 'premium_status']),
        '',
        '## Blockers',
        '',
        f'- Manual no-hit confirmation needed: {", ".join(manual_needed) if manual_needed else "none"}',
        f'- Premium extraction missing: {", ".join(premium_missing) if premium_missing else "none"}',
        f'- Price-window verification missing: {", ".join(price_missing) if price_missing else "none"}',
        '',
        '## Readiness Score Distribution',
        '',
    ]
    lines.extend(f'- {score}: {count}' for score, count in sorted(score_counts.items(), key=lambda item: int(item[0]), reverse=True))
    lines.append('')
    path.write_text('\n'.join(lines), encoding='utf-8')


def load_bundles(args: argparse.Namespace) -> tuple[list[CaseBundle], list[dict[str, str]]]:
    _, evidence_rows = read_csv(args.source_evidence)
    background_fields, background_rows = read_csv(args.background_findings)
    _, partial_rows = read_csv(args.cases_partial)
    _, price_rows = read_csv(args.price_windows)
    _, packet_rows = read_csv(args.packet_index)

    evidence_by_case = group_by(evidence_rows, 'case_id')
    background_by_ticker = indexed_by_ticker(background_rows)
    partial_by_ticker = indexed_by_ticker(partial_rows)
    price_by_case = index_by(price_rows, 'case_id')
    packet_by_ticker = indexed_by_ticker(packet_rows)

    bundles = []
    for ticker in TARGET_TICKERS:
        background = background_by_ticker.get(ticker, {})
        partial = partial_by_ticker.get(ticker, {})
        packet = packet_by_ticker.get(ticker, {})
        case_id = background.get('case_id') or partial.get('case_id') or packet.get('case_id')
        company = background.get('company') or partial.get('company') or packet.get('company_name')
        bundles.append(CaseBundle(
            ticker=ticker,
            case_id=case_id,
            company=company,
            evidence_rows=evidence_by_case.get(case_id, []),
            background=background,
            partial=partial,
            price_window=price_by_case.get(case_id, {}),
            packet_index=packet,
        ))
    return bundles, background_rows if background_fields else []


def enrich(args: argparse.Namespace) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    bundles, background_rows = load_bundles(args)
    premium_rows = [premium_finding(bundle) for bundle in bundles]
    observation_rows = [observation_row(bundle) for bundle in bundles]
    observations_by_ticker = {row['ticker']: row for row in observation_rows}
    readiness_rows = [
        readiness_row(bundle, observations_by_ticker[bundle.ticker], premium_rows[index])
        for index, bundle in enumerate(bundles)
    ]
    apply_ranks(readiness_rows)

    write_csv(args.premium_findings, premium_rows, PREMIUM_FIELDS)
    write_csv(args.observation_candidates, observation_rows, OBSERVATION_FIELDS)
    write_csv(args.readiness, readiness_rows, READINESS_FIELDS)
    if background_rows:
        write_csv(args.background_findings, update_background_rows(background_rows, observations_by_ticker), BACKGROUND_FIELDS)
    write_report(args.report, premium_rows, observation_rows, readiness_rows)
    return premium_rows, observation_rows, readiness_rows


def main() -> int:
    parser = argparse.ArgumentParser(description='Enrich first 10 acquisition cases toward verification readiness.')
    parser.add_argument('--source-evidence', type=Path, default=DEFAULT_SOURCE_EVIDENCE)
    parser.add_argument('--background-findings', type=Path, default=DEFAULT_BACKGROUND_FINDINGS)
    parser.add_argument('--cases-partial', type=Path, default=DEFAULT_CASES_PARTIAL)
    parser.add_argument('--price-windows', type=Path, default=DEFAULT_PRICE_WINDOWS)
    parser.add_argument('--packet-index', type=Path, default=DEFAULT_PACKET_INDEX)
    parser.add_argument('--premium-findings', type=Path, default=DEFAULT_PREMIUM_FINDINGS)
    parser.add_argument('--observation-candidates', type=Path, default=DEFAULT_OBSERVATION_CANDIDATES)
    parser.add_argument('--readiness', type=Path, default=DEFAULT_READINESS)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    premium_rows, observation_rows, readiness_rows = enrich(args)
    print(f'Cases enriched: {len(readiness_rows)}')
    print(f'Premium findings: {args.premium_findings}')
    print(f'Observation candidates: {args.observation_candidates}')
    print(f'Readiness index: {args.readiness}')
    print(f'Report written: {args.report}')
    print('Closest to VERIFIED:')
    for row in sorted(readiness_rows, key=lambda item: int(item['closest_to_verified_rank']))[:5]:
        print(f"  {row['closest_to_verified_rank']}. {row['ticker']} score={row['readiness_score']} blockers={row['remaining_fields_before_verified']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
