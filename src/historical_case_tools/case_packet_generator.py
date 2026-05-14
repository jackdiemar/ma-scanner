#!/usr/bin/env python3
"""
case_packet_generator.py

Build deterministic research packets for the Historical Case Factory.

The generator is read-only against evidence/status inputs. It writes packet
artifacts, an index, and a generation report, but it never promotes cases,
marks cases VERIFIED, marks cases CALIBRATION_ELIGIBLE, changes scanner
scoring, or touches dashboard files.

Usage:
    python3 src/historical_case_tools/case_packet_generator.py
    python3 src/historical_case_tools/case_packet_generator.py --limit 50
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'

DEFAULT_CANDIDATES = HISTORICAL_DIR / 'resolved_case_candidates.csv'
DEFAULT_QUEUE = HISTORICAL_DIR / 'acquisition_verification_queue.csv'
DEFAULT_BACKGROUND_FINDINGS = HISTORICAL_DIR / 'acquisition_background_findings.csv'
DEFAULT_SOURCE_EVIDENCE = HISTORICAL_DIR / 'source_evidence.csv'
DEFAULT_CASES_PARTIAL = HISTORICAL_DIR / 'cases_partial.csv'
DEFAULT_PRICE_WINDOWS = HISTORICAL_DIR / 'price_windows.csv'
DEFAULT_CHECKLIST = HISTORICAL_DIR / 'verification_checklist.md'
DEFAULT_PRIOR_SIGNAL_CONFIRMATION = HISTORICAL_DIR / 'prior_signal_confirmation_results.csv'
DEFAULT_PRIOR_SIGNAL_ADJUDICATION = HISTORICAL_DIR / 'prior_signal_adjudication_queue.csv'
DEFAULT_PACKET_DIR = HISTORICAL_DIR / 'case_packets'
DEFAULT_INDEX = HISTORICAL_DIR / 'case_packet_index.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'case_packet_generation_report.md'

RUN_DATE = '2026-05-14'

INDEX_FIELDS = [
    'case_id',
    'ticker',
    'company_name',
    'current_status',
    'packet_path',
    'json_packet_path',
    'completeness_score',
    'missing_field_count',
    'recommended_status',
    'recommended_next_action',
    'prior_signal_hit_status',
    'prior_signal_adjudication_status',
    'true_prior_signal_rows',
    'false_positive_rows',
    'priority',
]

CORE_ACQUISITION_EVIDENCE_TYPES = {
    '8K_MERGER',
    'MERGER_8K',
    'MERGER_PROXY',
    'SC_TO_T',
    'SC_TO_I',
}
SOURCE_BACKED_STATUSES = {'VERIFIED', 'PARTIAL'}
PARTIAL_READY_STATUSES = {'PARTIAL_READY', 'PARTIAL', 'NEEDS_MANUAL_RESEARCH', 'BAD_TARGET'}
MISSING_VALUE_TOKENS = {'', 'VERIFY_REQUIRED', 'UNKNOWN', 'TBD', 'N/A', 'NA'}


@dataclass
class Packet:
    data: dict[str, Any]
    markdown_path: Path
    json_path: Path


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, '') for field in fields})


def is_present(value: str | None) -> bool:
    return str(value or '').strip().upper() not in MISSING_VALUE_TOKENS


def normalize_status(value: str | None) -> str:
    return str(value or '').strip().upper()


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def safe_filename(value: str) -> str:
    clean = re.sub(r'[^A-Za-z0-9_.-]+', '_', value.strip())
    return clean.strip('_') or 'UNKNOWN'


def group_by(rows: Iterable[dict[str, str]], field: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = row.get(field, '').strip()
        if key:
            grouped[key].append(row)
    return dict(grouped)


def index_by(rows: Iterable[dict[str, str]], field: str) -> dict[str, dict[str, str]]:
    indexed = {}
    for row in rows:
        key = row.get(field, '').strip()
        if key and key not in indexed:
            indexed[key] = row
    return indexed


def queue_row_from_candidate(candidate: dict[str, str]) -> dict[str, str]:
    return {
        'candidate_id': candidate.get('candidate_id', '').strip(),
        'ticker': candidate.get('ticker', '').strip(),
        'company_name': candidate.get('company_name', '').strip(),
        'likely_outcome_year': candidate.get('likely_outcome_year', '').strip(),
        'merger_8k_query': candidate.get('outcome_edgar_query', '').strip(),
        'proxy_query': candidate.get('proxy_or_s4_query', '').strip(),
        'background_section_needed': 'TRUE',
        'prior_process_signal_query': candidate.get('prior_process_signal_query', '').strip(),
        'deal_terms_needed': 'TRUE',
        'price_window_needed': 'TRUE',
        'recommended_status': candidate.get('verification_status', '').strip() or 'CANDIDATE',
        'next_best_action': 'Open primary acquisition evidence, then run date and pre-announcement signal workflows.',
        'notes': candidate.get('notes', '').strip(),
    }


def selected_queue_rows(
    queue_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    limit: int,
) -> list[dict[str, str]]:
    selected = []
    seen: set[str] = set()
    for row in queue_rows:
        case_id = row.get('candidate_id', '').strip()
        if not case_id or case_id in seen:
            continue
        selected.append(row)
        seen.add(case_id)
    for candidate in candidate_rows:
        if len(selected) >= limit:
            break
        if candidate.get('likely_outcome_type', '').strip().upper() != 'ACQUIRED':
            continue
        case_id = candidate.get('candidate_id', '').strip()
        if not case_id or case_id in seen:
            continue
        selected.append(queue_row_from_candidate(candidate))
        seen.add(case_id)
    return selected[:limit]


def source_evidence_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            'evidence_id': row.get('evidence_id', ''),
            'evidence_type': row.get('evidence_type', ''),
            'source_name': row.get('source_name', ''),
            'source_url': row.get('source_url', ''),
            'filing_type': row.get('filing_type', ''),
            'filing_date': row.get('filing_date', ''),
            'supports_field': row.get('supports_field', ''),
            'confidence': row.get('confidence', ''),
            'verification_status': row.get('verification_status', ''),
            'excerpt': row.get('excerpt', ''),
            'notes': row.get('notes', ''),
        }
        for row in rows
    ]


def has_source_rows(rows: list[dict[str, str]]) -> bool:
    return bool(rows)


def has_core_acquisition_evidence(rows: list[dict[str, str]], partial_row: dict[str, str] | None) -> bool:
    for row in rows:
        evidence_type = normalize_status(row.get('evidence_type'))
        verification_status = normalize_status(row.get('verification_status'))
        supports = normalize_status(row.get('supports_field'))
        if verification_status not in SOURCE_BACKED_STATUSES:
            continue
        if evidence_type in CORE_ACQUISITION_EVIDENCE_TYPES:
            return True
        if 'DEAL_ANNOUNCEMENT_DATE' in supports and 'ACQUIRER' in supports:
            return True
    if partial_row:
        return (
            normalize_status(partial_row.get('data_quality')) == 'PARTIAL'
            and is_present(partial_row.get('source_filing_url'))
            and is_present(partial_row.get('deal_date'))
            and is_present(partial_row.get('acquirer'))
        )
    return False


def background_status(finding: dict[str, str] | None) -> dict[str, str]:
    if not finding:
        return {
            'status': 'NOT_REVIEWED',
            'background_section_available': 'FALSE',
            'background_heading': '',
            'proxy_source_url': '',
        }
    available = finding.get('background_section_available', '')
    return {
        'status': 'FOUND' if normalize_status(available) == 'TRUE' else 'NOT_FOUND',
        'background_section_available': available,
        'background_heading': finding.get('background_heading', ''),
        'proxy_source_url': finding.get('proxy_source_url', ''),
    }


def prior_process_status(finding: dict[str, str] | None, partial_row: dict[str, str] | None) -> dict[str, str]:
    if finding and normalize_status(finding.get('prior_process_signal')) in {'FOUND_PUBLIC', 'NONE_FOUND'}:
        return {
            'status': 'REVIEWED',
            'prior_process_signal': finding.get('prior_process_signal', ''),
            'prior_process_signal_type': finding.get('prior_process_signal_type', ''),
            'prior_process_signal_date': finding.get('prior_process_signal_date', ''),
        }
    if partial_row and is_present(partial_row.get('had_prior_process_signal')):
        return {
            'status': 'REVIEWED',
            'prior_process_signal': 'FOUND_PUBLIC' if normalize_status(partial_row.get('had_prior_process_signal')) == 'TRUE' else 'NONE_FOUND',
            'prior_process_signal_type': '',
            'prior_process_signal_date': '',
        }
    return {
        'status': 'NOT_REVIEWED',
        'prior_process_signal': '',
        'prior_process_signal_type': '',
        'prior_process_signal_date': '',
    }


def observation_candidate(
    finding: dict[str, str] | None,
    partial_row: dict[str, str] | None,
) -> tuple[str, str]:
    if finding and is_present(finding.get('observation_date_candidate')):
        return finding.get('observation_date_candidate', ''), finding.get('observation_date_reasoning', '')
    if partial_row and is_present(partial_row.get('observation_date')):
        return partial_row.get('observation_date', ''), 'Using cases_partial.csv observation_date until background review supplies a more specific candidate.'
    return '', ''


def premium_status(rows: list[dict[str, str]], partial_row: dict[str, str] | None) -> dict[str, str]:
    if partial_row and is_present(partial_row.get('deal_premium_pct')):
        return {
            'status': 'FOUND',
            'source': 'cases_partial.csv deal_premium_pct',
        }
    for row in rows:
        verification_status = normalize_status(row.get('verification_status'))
        supports = normalize_status(row.get('supports_field'))
        evidence_type = normalize_status(row.get('evidence_type'))
        if verification_status in SOURCE_BACKED_STATUSES and ('PREMIUM' in supports or 'PREMIUM' in evidence_type):
            return {
                'status': 'FOUND',
                'source': row.get('evidence_id', ''),
            }
    return {
        'status': 'MISSING',
        'source': '',
    }


def price_window_status(price_row: dict[str, str] | None) -> dict[str, str]:
    if not price_row:
        return {
            'status': 'NOT_STARTED',
            'price_source': '',
            'missing_data_flag': '',
            'fallback_needed': '',
            'notes': '',
        }
    complete = (
        normalize_status(price_row.get('missing_data_flag')) == 'FALSE'
        and is_present(price_row.get('price_before_signal'))
        and is_present(price_row.get('price_30d_after'))
        and is_present(price_row.get('price_90d_after'))
    )
    status = 'READY' if complete else 'ATTEMPTED_INCOMPLETE'
    return {
        'status': status,
        'price_source': price_row.get('price_source', ''),
        'missing_data_flag': price_row.get('missing_data_flag', ''),
        'fallback_needed': price_row.get('fallback_needed', ''),
        'notes': price_row.get('notes', ''),
    }


def prior_signal_adjudication_status(
    adjudication_rows: list[dict[str, str]],
    confirmation_row: dict[str, str] | None,
) -> dict[str, Any]:
    classifications = Counter(
        row.get('adjudication_classification', '').strip()
        for row in adjudication_rows
        if row.get('adjudication_classification', '').strip()
    )
    true_rows = classifications.get('TRUE_PUBLIC_PRIOR_SIGNAL', 0)
    false_positive_rows = sum(
        count for classification, count in classifications.items()
        if classification != 'TRUE_PUBLIC_PRIOR_SIGNAL'
    )
    hit_status = confirmation_row.get('hit_status', '') if confirmation_row else ''
    confidence = confirmation_row.get('confidence', '') if confirmation_row else ''
    best_source_url = confirmation_row.get('best_source_url', '') if confirmation_row else ''
    best_source_excerpt = confirmation_row.get('best_source_excerpt', '') if confirmation_row else ''

    if true_rows:
        status = 'TRUE_PUBLIC_PRIOR_SIGNAL'
    elif false_positive_rows:
        status = '|'.join(sorted(classifications)) or 'FALSE_POSITIVE'
    elif hit_status == 'CONFIRMED_NO_HIT':
        status = 'DEAL_ANNOUNCEMENT_BASELINE'
    elif hit_status == 'NEEDS_MANUAL_REVIEW':
        status = 'NEEDS_MANUAL_REVIEW'
    elif hit_status:
        status = hit_status
    else:
        status = 'NOT_ADJUDICATED'

    source_rows = []
    for row in adjudication_rows:
        source_rows.append({
            'filing_date': row.get('filing_date', ''),
            'filing_type': row.get('filing_type', ''),
            'source_url': row.get('source_url', ''),
            'collector_signal_type': row.get('collector_signal_type', ''),
            'collector_keyword_hits': row.get('collector_keyword_hits', ''),
            'adjudication_classification': row.get('adjudication_classification', ''),
            'adjudicated_signal_type': row.get('adjudicated_signal_type', ''),
            'confidence': row.get('confidence', ''),
            'notes': row.get('notes', ''),
        })

    return {
        'status': status,
        'confirmation_hit_status': hit_status,
        'confirmation_confidence': confidence,
        'best_source_url': best_source_url,
        'best_source_excerpt': best_source_excerpt,
        'true_prior_signal_rows': true_rows,
        'false_positive_rows': false_positive_rows,
        'classification_counts': dict(sorted(classifications.items())),
        'case_level_true_signal': 'TRUE' if true_rows else 'FALSE',
        'source_rows': source_rows,
    }


def current_status(
    candidate: dict[str, str],
    queue_row: dict[str, str],
    partial_row: dict[str, str] | None,
) -> str:
    if partial_row and is_present(partial_row.get('data_quality')):
        return partial_row.get('data_quality', '').strip().upper()
    if is_present(candidate.get('verification_status')):
        return candidate.get('verification_status', '').strip().upper()
    if is_present(queue_row.get('recommended_status')) and normalize_status(queue_row.get('recommended_status')) in PARTIAL_READY_STATUSES:
        return 'CANDIDATE'
    return 'CANDIDATE'


def build_missing_fields(
    *,
    core_acquisition_evidence_exists: bool,
    source_rows_exist: bool,
    background: dict[str, str],
    prior: dict[str, str],
    observation_date_candidate: str,
    premium: dict[str, str],
    price: dict[str, str],
) -> list[str]:
    missing = []
    if not core_acquisition_evidence_exists:
        missing.append('core acquisition evidence')
    if not source_rows_exist:
        missing.append('source evidence rows')
    if background['status'] != 'FOUND':
        missing.append('background section extraction')
    if prior['status'] != 'REVIEWED':
        missing.append('prior process signal review')
    if not is_present(observation_date_candidate):
        missing.append('observation date candidate')
    if premium['status'] != 'FOUND':
        missing.append('premium extraction')
    if price['status'] not in {'READY', 'COMPLETED'}:
        missing.append('price-window verification')
    return missing


def completeness_score(
    *,
    core_acquisition_evidence_exists: bool,
    source_rows_exist: bool,
    background_found: bool,
    prior_reviewed: bool,
    observation_date_candidate_exists: bool,
    premium_found: bool,
    price_ready: bool,
    missing_fields_listed: bool,
) -> int:
    score = 0
    if core_acquisition_evidence_exists:
        score += 20
    if source_rows_exist:
        score += 15
    if background_found:
        score += 15
    if prior_reviewed:
        score += 15
    if observation_date_candidate_exists:
        score += 10
    if premium_found:
        score += 10
    if price_ready:
        score += 10
    if missing_fields_listed:
        score += 5
    return score


def recommended_status(
    *,
    queue_status: str,
    current: str,
    core_acquisition_evidence_exists: bool,
    background_found: bool,
    prior_reviewed: bool,
    observation_date_candidate_exists: bool,
    candidate: dict[str, str],
    missing_fields: list[str],
) -> str:
    normalized_queue_status = normalize_status(queue_status)
    if normalized_queue_status == 'BAD_TARGET':
        return 'BAD_TARGET'
    if 'CRITICAL SEED ERROR' in (candidate.get('notes', '') + ' ' + candidate.get('outcome_source_hint', '')).upper():
        return 'BAD_TARGET'
    if current == 'PARTIAL':
        return 'PARTIAL'
    if normalized_queue_status == 'NEEDS_MANUAL_RESEARCH':
        return 'NEEDS_MANUAL_RESEARCH'
    if core_acquisition_evidence_exists and not current == 'PARTIAL':
        return 'PARTIAL_READY'
    if background_found and prior_reviewed and observation_date_candidate_exists:
        return 'PARTIAL_READY'
    if normalized_queue_status == 'PARTIAL_READY':
        return 'PARTIAL_READY'
    if missing_fields:
        return 'KEEP_CANDIDATE'
    return 'KEEP_CANDIDATE'


def recommended_next_action(recommended: str, missing_fields: list[str], queue_row: dict[str, str]) -> str:
    if recommended == 'BAD_TARGET':
        return 'Confirm ticker, company identity, acquisition year, and whether this belongs in the acquisition queue.'
    if recommended == 'NEEDS_MANUAL_RESEARCH':
        return queue_row.get('next_best_action', '') or 'Manually locate the correct transaction filing path before field extraction.'
    if recommended == 'PARTIAL':
        if 'price-window verification' in missing_fields:
            return 'Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status.'
        if 'premium extraction' in missing_fields:
            return 'Extract premium evidence from proxy or Schedule 14D-9, then run price-window verification.'
        return 'Keep as PARTIAL until verification checklist gates are completed.'
    if recommended == 'PARTIAL_READY':
        if 'core acquisition evidence' in missing_fields:
            return queue_row.get('next_best_action', '') or 'Open merger 8-K first and extract acquirer, consideration, filing date, accession, and excerpt.'
        if 'background section extraction' in missing_fields:
            return 'Run acquisition_background_extractor.py or manually capture proxy/Schedule 14D-9 background section.'
        if 'prior process signal review' in missing_fields:
            return 'Review background section and contemporaneous pre-announcement filings for public process signal.'
        return 'Promote only after primary-source evidence supports the PARTIAL checklist.'
    return queue_row.get('next_best_action', '') or 'Keep in candidate queue until primary EDGAR source evidence is opened and excerpted.'


def acquisition_evidence_status(core_exists: bool, rows: list[dict[str, str]]) -> str:
    if core_exists:
        return 'SOURCE_BACKED'
    if any(normalize_status(row.get('verification_status')) == 'VERIFY_REQUIRED' for row in rows):
        return 'RESEARCH_TARGETS_ONLY'
    return 'NOT_STARTED'


def build_packet(
    queue_row: dict[str, str],
    candidate: dict[str, str],
    evidence_rows: list[dict[str, str]],
    background_finding: dict[str, str] | None,
    partial_row: dict[str, str] | None,
    price_row: dict[str, str] | None,
    adjudication_rows: list[dict[str, str]],
    confirmation_row: dict[str, str] | None,
    packet_dir: Path,
) -> Packet:
    case_id = queue_row.get('candidate_id', '').strip()
    ticker = queue_row.get('ticker', '').strip()
    company_name = queue_row.get('company_name', '').strip()
    background = background_status(background_finding)
    prior = prior_process_status(background_finding, partial_row)
    observation_date_candidate, observation_date_reasoning = observation_candidate(background_finding, partial_row)
    premium = premium_status(evidence_rows, partial_row)
    price = price_window_status(price_row)
    adjudication = prior_signal_adjudication_status(adjudication_rows, confirmation_row)
    source_rows_exist = has_source_rows(evidence_rows)
    core_exists = has_core_acquisition_evidence(evidence_rows, partial_row)
    current = current_status(candidate, queue_row, partial_row)
    missing_fields = build_missing_fields(
        core_acquisition_evidence_exists=core_exists,
        source_rows_exist=source_rows_exist,
        background=background,
        prior=prior,
        observation_date_candidate=observation_date_candidate,
        premium=premium,
        price=price,
    )
    score = completeness_score(
        core_acquisition_evidence_exists=core_exists,
        source_rows_exist=source_rows_exist,
        background_found=background['status'] == 'FOUND',
        prior_reviewed=prior['status'] == 'REVIEWED',
        observation_date_candidate_exists=is_present(observation_date_candidate),
        premium_found=premium['status'] == 'FOUND',
        price_ready=price['status'] in {'READY', 'COMPLETED'},
        missing_fields_listed=True,
    )
    rec_status = recommended_status(
        queue_status=queue_row.get('recommended_status', ''),
        current=current,
        core_acquisition_evidence_exists=core_exists,
        background_found=background['status'] == 'FOUND',
        prior_reviewed=prior['status'] == 'REVIEWED',
        observation_date_candidate_exists=is_present(observation_date_candidate),
        candidate=candidate,
        missing_fields=missing_fields,
    )
    next_action = recommended_next_action(rec_status, missing_fields, queue_row)

    markdown_path = packet_dir / f'{safe_filename(case_id)}_{safe_filename(ticker)}.md'
    json_path = packet_dir / f'{safe_filename(case_id)}_{safe_filename(ticker)}.json'
    packet_data = {
        'case_id': case_id,
        'ticker': ticker,
        'company_name': company_name,
        'likely_outcome_type': candidate.get('likely_outcome_type', 'ACQUIRED'),
        'likely_outcome_year': queue_row.get('likely_outcome_year', ''),
        'current_status': current,
        'priority': candidate.get('priority', '') or 'UNSPECIFIED',
        'source_evidence_rows': source_evidence_summary(evidence_rows),
        'source_evidence_count': len(evidence_rows),
        'acquisition_evidence_status': acquisition_evidence_status(core_exists, evidence_rows),
        'background_section_status': background,
        'prior_process_signal_status': prior,
        'observation_date_candidate': observation_date_candidate,
        'observation_date_reasoning': observation_date_reasoning,
        'premium_evidence_status': premium,
        'price_window_status': price,
        'prior_signal_adjudication_status': adjudication,
        'missing_fields': missing_fields,
        'missing_field_count': len(missing_fields),
        'recommended_next_action': next_action,
        'recommended_status': rec_status,
        'workflow_completeness_score': score,
        'workflow_score_note': 'Workflow completeness only. Not investment quality and not P(deal).',
        'queue_fields': {
            'merger_8k_query': queue_row.get('merger_8k_query', ''),
            'proxy_query': queue_row.get('proxy_query', ''),
            'prior_process_signal_query': queue_row.get('prior_process_signal_query', ''),
            'deal_terms_needed': queue_row.get('deal_terms_needed', ''),
            'price_window_needed': queue_row.get('price_window_needed', ''),
            'queue_recommended_status': queue_row.get('recommended_status', ''),
            'queue_next_best_action': queue_row.get('next_best_action', ''),
            'queue_notes': queue_row.get('notes', ''),
        },
        'candidate_fields': {
            'outcome_source_hint': candidate.get('outcome_source_hint', ''),
            'reason_for_inclusion': candidate.get('reason_for_inclusion', ''),
            'candidate_notes': candidate.get('notes', ''),
        },
        'generated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    return Packet(packet_data, markdown_path, json_path)


def markdown_list(items: list[str]) -> str:
    if not items:
        return '- none'
    return '\n'.join(f'- {item}' for item in items)


def evidence_markdown(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return ['No source evidence rows found.']
    lines = []
    for row in rows:
        lines.extend([
            f"- `{row.get('evidence_id', '')}`",
            f"  - type: {row.get('evidence_type', '')}",
            f"  - status: {row.get('verification_status', '')}",
            f"  - filing: {row.get('filing_type', '')} {row.get('filing_date', '')}".rstrip(),
            f"  - source: {row.get('source_url', '')}",
            f"  - supports: {row.get('supports_field', '')}",
            f"  - excerpt: {row.get('excerpt', '') or 'No excerpt.'}",
        ])
    return lines


def adjudication_rows_markdown(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return ['- none']
    lines = []
    for row in rows:
        lines.append(
            f"- {row.get('filing_date', '')} {row.get('filing_type', '')}: "
            f"{row.get('adjudication_classification', '')} "
            f"({row.get('collector_signal_type', '')}; {row.get('collector_keyword_hits', '')})"
        )
        if row.get('source_url'):
            lines.append(f"  - source: {row.get('source_url')}")
        if row.get('notes'):
            lines.append(f"  - notes: {row.get('notes')}")
    return lines


def packet_to_markdown(packet: dict[str, Any]) -> str:
    background = packet['background_section_status']
    prior = packet['prior_process_signal_status']
    premium = packet['premium_evidence_status']
    price = packet['price_window_status']
    adjudication = packet['prior_signal_adjudication_status']
    lines = [
        f"# Case Packet: {packet['ticker']} - {packet['case_id']}",
        '',
        '## Summary',
        '',
        f"- Company: {packet['company_name']}",
        f"- Likely outcome type: {packet['likely_outcome_type']}",
        f"- Current status: {packet['current_status']}",
        f"- Recommended status: {packet['recommended_status']}",
        f"- Workflow completeness score: {packet['workflow_completeness_score']}/100",
        '- Score note: workflow completeness only. Not investment quality and not P(deal).',
        f"- Priority: {packet['priority']}",
        '',
        '## Evidence Status',
        '',
        f"- Source evidence rows: {packet['source_evidence_count']}",
        f"- Acquisition evidence status: {packet['acquisition_evidence_status']}",
        f"- Background section status: {background['status']}",
        f"- Background heading: {background['background_heading'] or 'not available'}",
        f"- Proxy source URL: {background['proxy_source_url'] or 'not available'}",
        f"- Prior process signal status: {prior['status']}",
        f"- Prior process signal: {prior['prior_process_signal'] or 'not reviewed'}",
        f"- Prior process signal type: {prior['prior_process_signal_type'] or 'not available'}",
        f"- Prior process signal date: {prior['prior_process_signal_date'] or 'not available'}",
        f"- Observation date candidate: {packet['observation_date_candidate'] or 'not available'}",
        f"- Observation date reasoning: {packet['observation_date_reasoning'] or 'not available'}",
        f"- Premium evidence status: {premium['status']}",
        f"- Premium evidence source: {premium['source'] or 'not available'}",
        f"- Price window status: {price['status']}",
        f"- Price window notes: {price['notes'] or 'not available'}",
        '',
        '## Prior Signal Adjudication',
        '',
        f"- Adjudication status: {adjudication['status']}",
        f"- Confirmation hit status: {adjudication['confirmation_hit_status'] or 'not available'}",
        f"- Case-level true signal: {adjudication['case_level_true_signal']}",
        f"- True prior-signal rows: {adjudication['true_prior_signal_rows']}",
        f"- False-positive rows: {adjudication['false_positive_rows']}",
        f"- Classification counts: {json.dumps(adjudication['classification_counts'], sort_keys=True)}",
        f"- Best source URL: {adjudication['best_source_url'] or 'not available'}",
        f"- Best source excerpt: {adjudication['best_source_excerpt'] or 'not available'}",
        '',
        '### Adjudicated Rows',
        '',
        *adjudication_rows_markdown(adjudication['source_rows']),
        '',
        '## Missing Fields',
        '',
        markdown_list(packet['missing_fields']),
        '',
        '## Recommended Next Action',
        '',
        packet['recommended_next_action'],
        '',
        '## Source Evidence Rows',
        '',
        *evidence_markdown(packet['source_evidence_rows']),
        '',
        '## Queue Queries',
        '',
        f"- Merger 8-K query: {packet['queue_fields']['merger_8k_query']}",
        f"- Proxy query: {packet['queue_fields']['proxy_query']}",
        f"- Prior process signal query: {packet['queue_fields']['prior_process_signal_query']}",
        '',
        '## Guardrails',
        '',
        '- Do not mark VERIFIED from this packet alone.',
        '- Do not mark CALIBRATION_ELIGIBLE from this packet alone.',
        '- Do not use this workflow score as investment quality or P(deal).',
    ]
    return '\n'.join(lines) + '\n'


def write_packet(packet: Packet) -> None:
    packet.markdown_path.parent.mkdir(parents=True, exist_ok=True)
    packet.markdown_path.write_text(packet_to_markdown(packet.data), encoding='utf-8')
    packet.json_path.write_text(json.dumps(packet.data, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def index_row(packet: Packet) -> dict[str, Any]:
    data = packet.data
    adjudication = data['prior_signal_adjudication_status']
    return {
        'case_id': data['case_id'],
        'ticker': data['ticker'],
        'company_name': data['company_name'],
        'current_status': data['current_status'],
        'packet_path': rel(packet.markdown_path),
        'json_packet_path': rel(packet.json_path),
        'completeness_score': data['workflow_completeness_score'],
        'missing_field_count': data['missing_field_count'],
        'recommended_status': data['recommended_status'],
        'recommended_next_action': data['recommended_next_action'],
        'prior_signal_hit_status': adjudication['confirmation_hit_status'],
        'prior_signal_adjudication_status': adjudication['status'],
        'true_prior_signal_rows': adjudication['true_prior_signal_rows'],
        'false_positive_rows': adjudication['false_positive_rows'],
        'priority': data['priority'],
    }


def status_rank(status: str) -> int:
    return {
        'PARTIAL': 0,
        'PARTIAL_READY': 1,
        'NEEDS_MANUAL_RESEARCH': 2,
        'KEEP_CANDIDATE': 3,
        'BAD_TARGET': 4,
    }.get(status, 5)


def next_verification_batch(packets: list[Packet], size: int = 10) -> list[Packet]:
    candidates = [
        packet for packet in packets
        if packet.data['recommended_status'] in {'PARTIAL_READY', 'PARTIAL', 'NEEDS_MANUAL_RESEARCH'}
        and packet.data['missing_fields']
    ]
    return sorted(
        candidates,
        key=lambda packet: (
            status_rank(packet.data['recommended_status']),
            -int(packet.data['workflow_completeness_score']),
            int(packet.data['missing_field_count']),
            packet.data['case_id'],
        ),
    )[:size]


def closest_to_partial(packets: list[Packet]) -> list[Packet]:
    candidates = [
        packet for packet in packets
        if packet.data['recommended_status'] != 'PARTIAL'
    ]
    return sorted(
        candidates,
        key=lambda packet: (
            -int(packet.data['workflow_completeness_score']),
            int(packet.data['missing_field_count']),
            status_rank(packet.data['recommended_status']),
            packet.data['case_id'],
        ),
    )[:10]


def closest_to_verified(packets: list[Packet]) -> list[Packet]:
    candidates = [
        packet for packet in packets
        if packet.data['current_status'] == 'PARTIAL'
    ]
    return sorted(
        candidates,
        key=lambda packet: (
            int(packet.data['missing_field_count']),
            -int(packet.data['workflow_completeness_score']),
            packet.data['case_id'],
        ),
    )[:10]


def table_rows(packets: list[Packet], include_action: bool = False) -> list[str]:
    lines = ['| case | ticker | score | recommended_status | missing fields |' + (' next action |' if include_action else '')]
    lines.append('| --- | --- | ---: | --- | ---: |' + (' --- |' if include_action else ''))
    for packet in packets:
        data = packet.data
        row = (
            f"| {data['case_id']} | {data['ticker']} | {data['workflow_completeness_score']} | "
            f"{data['recommended_status']} | {data['missing_field_count']} |"
        )
        if include_action:
            row += f" {data['recommended_next_action']} |"
        lines.append(row)
    return lines


def write_report(packets: list[Packet], path: Path) -> None:
    highest = sorted(packets, key=lambda packet: (-int(packet.data['workflow_completeness_score']), packet.data['case_id']))[:10]
    lowest = sorted(packets, key=lambda packet: (int(packet.data['workflow_completeness_score']), packet.data['case_id']))[:10]
    missing_counter = Counter(
        missing
        for packet in packets
        for missing in packet.data['missing_fields']
    )
    closest_partial = closest_to_partial(packets)
    closest_verified = closest_to_verified(packets)
    next_batch = next_verification_batch(packets)
    adjudication_counter = Counter(
        packet.data['prior_signal_adjudication_status']['status']
        for packet in packets
    )
    true_signal_packets = [
        packet for packet in packets
        if packet.data['prior_signal_adjudication_status']['status'] == 'TRUE_PUBLIC_PRIOR_SIGNAL'
    ]
    false_positive_packets = [
        packet for packet in packets
        if packet.data['prior_signal_adjudication_status']['false_positive_rows']
    ]

    lines = [
        '# Case Packet Generation Report',
        '',
        f'Generated: {RUN_DATE}',
        '',
        '## Summary',
        '',
        f'- Packets generated: {len(packets)}',
        '- Scope: acquisition queue first, then additional ACQUIRED candidates from resolved_case_candidates.csv as needed.',
        '- Workflow completeness score is not investment quality and not P(deal).',
        '- No cases were marked VERIFIED or CALIBRATION_ELIGIBLE.',
        '',
        '## Prior Signal Adjudication Summary',
        '',
    ]
    if adjudication_counter:
        lines.extend(f'- {status}: {count}' for status, count in adjudication_counter.most_common())
    else:
        lines.append('- none')
    lines.extend([
        '',
        '## True Prior Public Signal Packets',
        '',
        *table_rows(true_signal_packets),
        '',
        '## False-Positive Prior Signal Packets',
        '',
        *table_rows(false_positive_packets),
        '',
        '## Top 10 Highest-Completeness Packets',
        '',
        *table_rows(highest),
        '',
        '## Bottom 10 Lowest-Completeness Packets',
        '',
        *table_rows(lowest),
        '',
        '## Common Missing Fields',
        '',
    ])
    if missing_counter:
        lines.extend(f'- {field}: {count}' for field, count in missing_counter.most_common())
    else:
        lines.append('- none')
    lines.extend([
        '',
        '## Cases Closest To PARTIAL',
        '',
        *table_rows(closest_partial, include_action=True),
        '',
        '## Cases Closest To Future VERIFIED',
        '',
        *table_rows(closest_verified, include_action=True),
        '',
        '## Next Best Verification Batch',
        '',
        *table_rows(next_batch, include_action=True),
        '',
    ])
    path.write_text('\n'.join(lines), encoding='utf-8')


def load_context(args: argparse.Namespace) -> dict[str, Any]:
    _, candidate_rows = read_csv(args.candidates)
    _, queue_rows = read_csv(args.queue)
    _, background_rows = read_csv(args.background_findings)
    _, evidence_rows = read_csv(args.source_evidence)
    _, partial_rows = read_csv(args.cases_partial)
    _, price_rows = read_csv(args.price_windows)
    _, confirmation_rows = read_csv(args.prior_signal_confirmation)
    _, adjudication_rows = read_csv(args.prior_signal_adjudication)
    if args.checklist.exists():
        args.checklist.read_text(encoding='utf-8')
    return {
        'candidate_rows': candidate_rows,
        'candidate_by_id': index_by(candidate_rows, 'candidate_id'),
        'queue_rows': queue_rows,
        'background_by_id': index_by(background_rows, 'case_id'),
        'evidence_by_id': group_by(evidence_rows, 'case_id'),
        'partial_by_id': index_by(partial_rows, 'case_id'),
        'price_by_id': index_by(price_rows, 'case_id'),
        'confirmation_by_id': index_by(confirmation_rows, 'case_id'),
        'adjudication_by_id': group_by(adjudication_rows, 'case_id'),
    }


def generate(args: argparse.Namespace) -> list[Packet]:
    context = load_context(args)
    queue_rows = selected_queue_rows(context['queue_rows'], context['candidate_rows'], args.limit)
    packets = []
    for queue_row in queue_rows:
        case_id = queue_row.get('candidate_id', '').strip()
        if not case_id:
            continue
        candidate = context['candidate_by_id'].get(case_id, {})
        packet = build_packet(
            queue_row=queue_row,
            candidate=candidate,
            evidence_rows=context['evidence_by_id'].get(case_id, []),
            background_finding=context['background_by_id'].get(case_id),
            partial_row=context['partial_by_id'].get(case_id),
            price_row=context['price_by_id'].get(case_id),
            adjudication_rows=context['adjudication_by_id'].get(case_id, []),
            confirmation_row=context['confirmation_by_id'].get(case_id),
            packet_dir=args.packet_dir,
        )
        write_packet(packet)
        packets.append(packet)
    write_csv(args.index, [index_row(packet) for packet in packets], INDEX_FIELDS)
    write_report(packets, args.report)
    return packets


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate historical case research packets.')
    parser.add_argument('--limit', type=int, default=50, help='Number of acquisition rows to packetize.')
    parser.add_argument('--candidates', type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument('--queue', type=Path, default=DEFAULT_QUEUE)
    parser.add_argument('--background-findings', type=Path, default=DEFAULT_BACKGROUND_FINDINGS)
    parser.add_argument('--source-evidence', type=Path, default=DEFAULT_SOURCE_EVIDENCE)
    parser.add_argument('--cases-partial', type=Path, default=DEFAULT_CASES_PARTIAL)
    parser.add_argument('--price-windows', type=Path, default=DEFAULT_PRICE_WINDOWS)
    parser.add_argument('--checklist', type=Path, default=DEFAULT_CHECKLIST)
    parser.add_argument('--prior-signal-confirmation', type=Path, default=DEFAULT_PRIOR_SIGNAL_CONFIRMATION)
    parser.add_argument('--prior-signal-adjudication', type=Path, default=DEFAULT_PRIOR_SIGNAL_ADJUDICATION)
    parser.add_argument('--packet-dir', type=Path, default=DEFAULT_PACKET_DIR)
    parser.add_argument('--index', type=Path, default=DEFAULT_INDEX)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    packets = generate(args)
    print(f'Packets generated: {len(packets)}')
    print(f'Packet directory: {args.packet_dir}')
    print(f'Index written: {args.index}')
    print(f'Report written: {args.report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
