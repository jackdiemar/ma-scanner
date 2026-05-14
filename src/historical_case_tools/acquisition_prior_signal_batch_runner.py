#!/usr/bin/env python3
"""
acquisition_prior_signal_batch_runner.py

Batch runner for acquired-case prior-public-signal review.

The runner reuses existing workflow artifacts where available, writes a
case-level batch result table and report, updates the mini-study, and
regenerates case packets. It does not mark cases VERIFIED or
CALIBRATION_ELIGIBLE.

Usage:
    python3 src/historical_case_tools/acquisition_prior_signal_batch_runner.py --limit 50
    python3 src/historical_case_tools/acquisition_prior_signal_batch_runner.py --tickers RLYP VTAE CLCD AVXS CASC
    python3 src/historical_case_tools/acquisition_prior_signal_batch_runner.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'

DEFAULT_QUEUE = HISTORICAL_DIR / 'acquisition_verification_queue.csv'
DEFAULT_CANDIDATES = HISTORICAL_DIR / 'resolved_case_candidates.csv'
DEFAULT_ACQUISITION_DATES = HISTORICAL_DIR / 'acquisition_announcement_dates.csv'
DEFAULT_FILING_TARGETS = HISTORICAL_DIR / 'pre_announcement_filing_targets.csv'
DEFAULT_SIGNAL_HITS = HISTORICAL_DIR / 'pre_announcement_signal_hits.csv'
DEFAULT_ADJUDICATION_QUEUE = HISTORICAL_DIR / 'prior_signal_adjudication_queue.csv'
DEFAULT_CONFIRMATION_RESULTS = HISTORICAL_DIR / 'prior_signal_confirmation_results.csv'
DEFAULT_SOURCE_EVIDENCE = HISTORICAL_DIR / 'source_evidence.csv'
DEFAULT_PACKET_INDEX = HISTORICAL_DIR / 'case_packet_index.csv'
DEFAULT_BATCH_RESULTS = HISTORICAL_DIR / 'acquisition_prior_signal_batch_results.csv'
DEFAULT_BATCH_REPORT = HISTORICAL_DIR / 'acquisition_prior_signal_batch_report.md'
DEFAULT_MINI_STUDY = HISTORICAL_DIR / 'acquisition_prior_signal_mini_study.md'
CASE_PACKET_GENERATOR = REPO_ROOT / 'src' / 'historical_case_tools' / 'case_packet_generator.py'

RUN_DATE = '2026-05-14'

BATCH_FIELDS = [
    'case_id',
    'ticker',
    'company_name',
    'announcement_date',
    'announcement_date_confidence',
    'filings_checked_count',
    'possible_hits_count',
    'adjudication_status',
    'confidence',
    'next_action',
    'packet_path',
    'completeness_score',
]

FINAL_STATUSES = {
    'TRUE_PUBLIC_PRIOR_SIGNAL',
    'RIGHTS_LANGUAGE_ONLY',
    'ASSET_SPECIFIC_RIGHTS_ONLY',
    'PRIVATE_BACKGROUND_ONLY',
    'FALSE_POSITIVE',
    'DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE',
}


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


def group_by(rows: Iterable[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        value = row.get(key, '').strip()
        if value:
            grouped[value].append(row)
    return dict(grouped)


def index_by(rows: Iterable[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    indexed = {}
    for row in rows:
        value = row.get(key, '').strip()
        if value and value not in indexed:
            indexed[value] = row
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


def target_priority(
    row: dict[str, str],
    *,
    dates_by_case: dict[str, dict[str, str]],
    targets_by_case: dict[str, list[dict[str, str]]],
    evidence_by_case: dict[str, list[dict[str, str]]],
) -> int:
    case_id = row.get('candidate_id', '').strip()
    score = 0
    if evidence_by_case.get(case_id):
        score += 4
    date_confidence = dates_by_case.get(case_id, {}).get('confidence', '').strip().upper()
    if date_confidence == 'HIGH':
        score += 4
    elif date_confidence:
        score += 2
    if targets_by_case.get(case_id):
        score += 3
    if row.get('merger_8k_query', '').strip():
        score += 1
    if row.get('proxy_query', '').strip():
        score += 1
    return score


def selected_target_rows(
    *,
    queue_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    tickers: list[str],
    limit: int,
    dates_by_case: dict[str, dict[str, str]],
    targets_by_case: dict[str, list[dict[str, str]]],
    evidence_by_case: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    wanted = {ticker.upper() for ticker in tickers}
    selected = []
    seen: set[str] = set()

    for row in queue_rows:
        case_id = row.get('candidate_id', '').strip()
        ticker = row.get('ticker', '').strip().upper()
        if not case_id or case_id in seen:
            continue
        if wanted and ticker not in wanted:
            continue
        selected.append(row)
        seen.add(case_id)

    fallback_rows = []
    for index, candidate in enumerate(candidate_rows):
        if candidate.get('likely_outcome_type', '').strip().upper() != 'ACQUIRED':
            continue
        case_id = candidate.get('candidate_id', '').strip()
        ticker = candidate.get('ticker', '').strip().upper()
        if not case_id or case_id in seen:
            continue
        if wanted and ticker not in wanted:
            continue
        row = queue_row_from_candidate(candidate)
        fallback_rows.append((
            -target_priority(
                row,
                dates_by_case=dates_by_case,
                targets_by_case=targets_by_case,
                evidence_by_case=evidence_by_case,
            ),
            index,
            row,
        ))

    selected.extend(row for _, _, row in sorted(fallback_rows))
    if wanted:
        return selected
    return selected[:limit]


def source_date(case_id: str, evidence_by_case: dict[str, list[dict[str, str]]]) -> tuple[str, str]:
    for row in evidence_by_case.get(case_id, []):
        supports = row.get('supports_field', '').upper()
        if 'DEAL_ANNOUNCEMENT_DATE' not in supports:
            continue
        date = row.get('filing_date', '').strip()
        if date:
            return date, row.get('confidence', '').strip() or 'MEDIUM'
    return '', ''


def source_prior_none(case_id: str, evidence_by_case: dict[str, list[dict[str, str]]]) -> bool:
    for row in evidence_by_case.get(case_id, []):
        supports = row.get('supports_field', '').upper()
        notes = row.get('notes', '').upper()
        if 'HAD_PRIOR_PROCESS_SIGNAL' in supports and 'NONE_FOUND' in notes:
            return True
    return False


def source_proxy_background_only(case_id: str, evidence_by_case: dict[str, list[dict[str, str]]]) -> bool:
    for row in evidence_by_case.get(case_id, []):
        evidence_type = row.get('evidence_type', '').upper()
        supports = row.get('supports_field', '').upper()
        notes = row.get('notes', '').upper()
        if evidence_type != 'PROXY_SA_LANGUAGE':
            continue
        if 'FOUND_PUBLIC' in notes or 'HAD_PRIOR_PROCESS_SIGNAL' in supports:
            continue
        if 'PROXY_OR_TENDER_BACKGROUND' in supports or 'PROCESS_TIMELINE' in supports:
            return True
    return False


def status_from_adjudication(rows: list[dict[str, str]]) -> str:
    classes = Counter(
        row.get('adjudication_classification', '').strip()
        for row in rows
        if row.get('adjudication_classification', '').strip()
    )
    if not classes:
        return ''
    if classes.get('TRUE_PUBLIC_PRIOR_SIGNAL'):
        return 'TRUE_PUBLIC_PRIOR_SIGNAL'
    if classes.get('NEEDS_MORE_REVIEW'):
        return 'POSSIBLE_SIGNAL_NEEDS_REVIEW'
    if classes.get('PRIVATE_BACKGROUND_ONLY') and len(classes) == 1:
        return 'PRIVATE_BACKGROUND_ONLY'
    if classes.get('ASSET_SPECIFIC_RIGHTS_ONLY') and len(classes) == 1:
        return 'ASSET_SPECIFIC_RIGHTS_ONLY'
    if classes.get('RIGHTS_LANGUAGE_ONLY') and len(classes) == 1:
        return 'RIGHTS_LANGUAGE_ONLY'
    return 'FALSE_POSITIVE'


def adjudication_confidence(rows: list[dict[str, str]], status: str, default: str = 'MEDIUM') -> str:
    if status == 'TRUE_PUBLIC_PRIOR_SIGNAL':
        relevant = [
            row.get('confidence', '').strip().upper()
            for row in rows
            if row.get('adjudication_classification', '').strip() == status
        ]
    else:
        relevant = [row.get('confidence', '').strip().upper() for row in rows]
    ranks = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
    ranked = [confidence for confidence in relevant if confidence in ranks]
    if not ranked:
        return default
    return sorted(ranked, key=lambda confidence: ranks[confidence], reverse=True)[0]


def status_from_case(
    *,
    case_id: str,
    announcement_date: str,
    confirmation: dict[str, str],
    target_rows: list[dict[str, str]],
    hit_rows: list[dict[str, str]],
    adjudication_rows: list[dict[str, str]],
    evidence_by_case: dict[str, list[dict[str, str]]],
    force: bool,
) -> tuple[str, str, str]:
    adjudicated_status = status_from_adjudication(adjudication_rows)
    if adjudicated_status and (not force or adjudicated_status in FINAL_STATUSES):
        adjudicated_confidence = adjudication_confidence(adjudication_rows, adjudicated_status)
        if adjudicated_status == 'TRUE_PUBLIC_PRIOR_SIGNAL':
            return adjudicated_status, adjudicated_confidence, 'Reused adjudicated true prior public signal; do not mark VERIFIED without independent review.'
        if adjudicated_status in {'RIGHTS_LANGUAGE_ONLY', 'ASSET_SPECIFIC_RIGHTS_ONLY', 'PRIVATE_BACKGROUND_ONLY', 'FALSE_POSITIVE'}:
            return adjudicated_status, adjudicated_confidence, 'Keep out of true prior-signal counts unless separate public whole-company process evidence is found.'
        return adjudicated_status, 'LOW', 'Review possible-hit source filings manually before case-level confirmation.'

    if not announcement_date:
        return 'DATE_MISSING', 'LOW', 'Backfill exact acquisition announcement date before prior-signal review.'

    target_statuses = {row.get('recommended_status', '').strip() for row in target_rows}
    confirmation_status = confirmation.get('hit_status', '').strip()

    if hit_rows:
        return 'POSSIBLE_SIGNAL_NEEDS_REVIEW', 'LOW', 'Adjudicate possible pre-announcement signal hits using source filing text.'
    if 'DATE_OR_CIK_BLOCKED' in target_statuses:
        return 'SOURCE_BLOCKED', 'LOW', 'Resolve CIK or SEC filing collection blocker, then rerun filing collection.'
    if target_rows and target_statuses <= {'LIKELY_NO_HIT'}:
        return 'DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE', 'MEDIUM', 'Use as baseline candidate after final manual EDGAR hit/no-hit spot check.'
    if confirmation_status == 'CONFIRMED_HIT':
        return 'TRUE_PUBLIC_PRIOR_SIGNAL', 'HIGH', 'Reused confirmation hit; confirm source filing before calibration use.'
    if confirmation_status == 'CONFIRMED_NO_HIT':
        return 'DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE', 'MEDIUM', 'Use as baseline candidate unless later manual review finds public pre-deal process evidence.'
    if source_prior_none(case_id, evidence_by_case):
        return 'DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE', 'MEDIUM', 'Source evidence indicates no public prior process signal; keep as baseline candidate pending final hit/no-hit confirmation.'
    if source_proxy_background_only(case_id, evidence_by_case):
        return 'PRIVATE_BACKGROUND_ONLY', 'MEDIUM', 'Existing evidence is post-announcement proxy or tender background only; keep out of prior-public-signal counts unless pre-announcement public evidence is found.'
    return 'NEEDS_MANUAL_REVIEW', 'LOW', 'Run or manually complete pre-announcement filing collection and hit/no-hit confirmation.'


def build_batch_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    queue_rows = read_csv(args.queue)
    candidate_rows = read_csv(args.candidates)
    dates_by_case = index_by(read_csv(args.acquisition_dates), 'case_id')
    targets_by_case = group_by(read_csv(args.filing_targets), 'case_id')
    hits_by_case = group_by(read_csv(args.signal_hits), 'case_id')
    adjudication_by_case = group_by(read_csv(args.adjudication_queue), 'case_id')
    confirmation_by_case = index_by(read_csv(args.confirmation_results), 'case_id')
    evidence_by_case = group_by(read_csv(args.source_evidence), 'case_id')
    packet_by_case = index_by(read_csv(args.packet_index), 'case_id')
    target_rows = selected_target_rows(
        queue_rows=queue_rows,
        candidate_rows=candidate_rows,
        tickers=args.tickers,
        limit=args.limit,
        dates_by_case=dates_by_case,
        targets_by_case=targets_by_case,
        evidence_by_case=evidence_by_case,
    )

    rows = []
    for queue_row in target_rows:
        case_id = queue_row.get('candidate_id', '').strip()
        date_row = dates_by_case.get(case_id, {})
        confirmation = confirmation_by_case.get(case_id, {})
        packet = packet_by_case.get(case_id, {})
        source_date_value, source_date_confidence = source_date(case_id, evidence_by_case)
        announcement_date = (
            date_row.get('acquisition_announcement_date', '').strip()
            or confirmation.get('acquisition_announcement_date', '').strip()
            or source_date_value
        )
        date_confidence = date_row.get('confidence', '').strip() or source_date_confidence or ''
        target_rows = targets_by_case.get(case_id, [])
        hit_rows = hits_by_case.get(case_id, [])
        status, confidence, next_action = status_from_case(
            case_id=case_id,
            announcement_date=announcement_date,
            confirmation=confirmation,
            target_rows=target_rows,
            hit_rows=hit_rows,
            adjudication_rows=adjudication_by_case.get(case_id, []),
            evidence_by_case=evidence_by_case,
            force=args.force,
        )
        rows.append({
            'case_id': case_id,
            'ticker': queue_row.get('ticker', '').strip(),
            'company_name': queue_row.get('company_name', '').strip(),
            'announcement_date': announcement_date,
            'announcement_date_confidence': date_confidence,
            'filings_checked_count': str(sum(1 for row in target_rows if row.get('filing_date', '').strip())),
            'possible_hits_count': str(len(hit_rows)),
            'adjudication_status': status,
            'confidence': confidence,
            'next_action': next_action,
            'packet_path': packet.get('packet_path', ''),
            'completeness_score': packet.get('completeness_score', ''),
        })
    return rows


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    lines = [
        '| ' + ' | '.join(columns) + ' |',
        '| ' + ' | '.join(['---'] * len(columns)) + ' |',
    ]
    for row in rows:
        values = [str(row.get(column, '')).replace('|', '/') for column in columns]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)


def next_manual_reviews(rows: list[dict[str, str]], limit: int = 10) -> list[dict[str, str]]:
    priority = {
        'POSSIBLE_SIGNAL_NEEDS_REVIEW': 0,
        'NEEDS_MANUAL_REVIEW': 1,
        'SOURCE_BLOCKED': 2,
        'DATE_MISSING': 3,
        'DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE': 4,
    }
    candidates = [
        row for row in rows
        if row['adjudication_status'] in priority
        and row['adjudication_status'] != 'TRUE_PUBLIC_PRIOR_SIGNAL'
    ]
    return sorted(
        candidates,
        key=lambda row: (
            priority[row['adjudication_status']],
            -int(row['possible_hits_count'] or 0),
            -int(row['filings_checked_count'] or 0),
            row['case_id'],
        ),
    )[:limit]


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row['adjudication_status'] for row in rows)
    true_rows = [row for row in rows if row['adjudication_status'] == 'TRUE_PUBLIC_PRIOR_SIGNAL']
    false_rows = [
        row for row in rows
        if row['adjudication_status'] in {'RIGHTS_LANGUAGE_ONLY', 'ASSET_SPECIFIC_RIGHTS_ONLY', 'PRIVATE_BACKGROUND_ONLY', 'FALSE_POSITIVE'}
    ]
    baselines = [row for row in rows if row['adjudication_status'] == 'DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE']
    blockers = [row for row in rows if row['adjudication_status'] in {'DATE_MISSING', 'SOURCE_BLOCKED'}]
    manual = next_manual_reviews(rows, limit=10)
    lines = [
        '# Acquisition Prior-Signal Batch Report',
        '',
        f'Generated: {RUN_DATE}',
        '',
        '## Summary',
        '',
        f'- Cases processed: {len(rows)}',
        f'- True prior public signals: {counts.get("TRUE_PUBLIC_PRIOR_SIGNAL", 0)}',
        f'- Baseline candidates: {counts.get("DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE", 0)}',
        f'- False positives: {sum(counts.get(status, 0) for status in ["RIGHTS_LANGUAGE_ONLY", "ASSET_SPECIFIC_RIGHTS_ONLY", "PRIVATE_BACKGROUND_ONLY", "FALSE_POSITIVE"])}',
        f'- Needs manual review: {counts.get("NEEDS_MANUAL_REVIEW", 0) + counts.get("POSSIBLE_SIGNAL_NEEDS_REVIEW", 0)}',
        f'- Blockers: {counts.get("DATE_MISSING", 0) + counts.get("SOURCE_BLOCKED", 0)}',
        '- No cases were marked `VERIFIED` or `CALIBRATION_ELIGIBLE`.',
        '',
        '## Counts By Adjudication Status',
        '',
    ]
    lines.extend(f'- {status}: {count}' for status, count in counts.most_common())
    lines.extend([
        '',
        '## True Prior Public Signal Candidates',
        '',
        markdown_table(true_rows, ['case_id', 'ticker', 'announcement_date', 'adjudication_status', 'confidence', 'packet_path']) if true_rows else 'None.',
        '',
        '## False Positives',
        '',
        markdown_table(false_rows, ['case_id', 'ticker', 'adjudication_status', 'confidence', 'next_action']) if false_rows else 'None.',
        '',
        '## Baseline Candidates',
        '',
        markdown_table(baselines, ['case_id', 'ticker', 'announcement_date', 'filings_checked_count', 'adjudication_status', 'confidence']) if baselines else 'None.',
        '',
        '## Blockers',
        '',
        markdown_table(blockers, ['case_id', 'ticker', 'adjudication_status', 'next_action']) if blockers else 'None.',
        '',
        '## Next 10 Manual Reviews',
        '',
        markdown_table(manual, ['case_id', 'ticker', 'announcement_date', 'filings_checked_count', 'possible_hits_count', 'adjudication_status', 'next_action']) if manual else 'None.',
        '',
        '## All Batch Results',
        '',
        markdown_table(rows, BATCH_FIELDS),
    ])
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def write_mini_study(path: Path, rows: list[dict[str, str]]) -> None:
    counts = Counter(row['adjudication_status'] for row in rows)
    true_rows = [row for row in rows if row['adjudication_status'] == 'TRUE_PUBLIC_PRIOR_SIGNAL']
    false_rows = [
        row for row in rows
        if row['adjudication_status'] in {'RIGHTS_LANGUAGE_ONLY', 'ASSET_SPECIFIC_RIGHTS_ONLY', 'PRIVATE_BACKGROUND_ONLY', 'FALSE_POSITIVE'}
    ]
    baselines = [row for row in rows if row['adjudication_status'] == 'DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE']
    manual = next_manual_reviews(rows, limit=10)
    lines = [
        '# Acquisition Prior-Signal Mini-Study',
        '',
        f'Generated: {RUN_DATE}',
        '',
        '## Scope',
        '',
        f'This mini-study summarizes the current acquisition prior-signal batch of {len(rows)} acquired historical cases.',
        '',
        'The workflow reuses acquisition announcement dates, pre-announcement filing targets, possible signal hits, adjudication rows, confirmation results, source evidence, and packet metadata. It does not mark any case `VERIFIED` or `CALIBRATION_ELIGIBLE`.',
        '',
        '## Results',
        '',
        f'- Cases reviewed: {len(rows)}',
        f'- True prior public signal cases: {counts.get("TRUE_PUBLIC_PRIOR_SIGNAL", 0)}',
        f'- Deal-announcement baseline candidates: {counts.get("DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE", 0)}',
        f'- False-positive cases: {len(false_rows)}',
        f'- Needs manual review: {counts.get("NEEDS_MANUAL_REVIEW", 0) + counts.get("POSSIBLE_SIGNAL_NEEDS_REVIEW", 0)}',
        f'- Date/source blockers: {counts.get("DATE_MISSING", 0) + counts.get("SOURCE_BLOCKED", 0)}',
        '',
        '## True Prior Public Signal Cases',
        '',
        markdown_table(true_rows, ['case_id', 'ticker', 'announcement_date', 'adjudication_status', 'confidence']) if true_rows else 'None.',
        '',
        '## Deal-Announcement Baseline Candidates',
        '',
        markdown_table(baselines, ['case_id', 'ticker', 'announcement_date', 'filings_checked_count', 'confidence']) if baselines else 'None.',
        '',
        '## False-Positive Cases',
        '',
        markdown_table(false_rows, ['case_id', 'ticker', 'adjudication_status', 'next_action']) if false_rows else 'None.',
        '',
        '## Signal Types Found',
        '',
        '- Public unsolicited acquisition proposal.',
        '- Public rejected proposal.',
        '- Competing bid or superior proposal.',
        '- Board response after consultation with financial or legal advisors.',
        '- Public process pressure through consent solicitation or matching-right waiver context.',
        '',
        'No confirmed activist 13D sale-pressure case has been found in this batch.',
        '',
        '## False-Positive Patterns',
        '',
        '- Generic securities-rights language is not process evidence.',
        '- Asset, subsidiary, product, license, noteholder, or collaboration rights are not whole-company sale process evidence unless clearly connected to a company-sale pathway.',
        '- Later proxy background language does not become a prior public signal unless the process was publicly disclosed before the acquisition announcement.',
        '',
        '## What The Scanner Could Have Caught',
        '',
        'The scanner could have caught MDVN and DMTX because public pre-announcement filings contained unsolicited proposal, competing bid, superior proposal, advisor, and process language before the final acquisition announcement.',
        '',
        'TSRO is different: the public signal was a pre-announcement media report later cited in Schedule 14D-9 background. An EDGAR-only scanner would not reliably catch it before announcement unless external public-news evidence is part of the workflow.',
        '',
        '## What The Scanner Could Not Have Caught',
        '',
        'The scanner should not count private negotiations later disclosed in proxy or Schedule 14D-9 background sections. It also should not count generic rights language, asset-specific ROFR/ROFN language, or final merger announcement language as prior public process evidence.',
        '',
        '## Implications For Future Case Verification',
        '',
        '1. Run batch-level status aggregation before opening individual case packets.',
        '2. Adjudicate possible hits only from source filing text or sufficiently specific excerpts.',
        '3. Treat no-hit rows as baseline candidates until the searched filing set is complete enough.',
        '4. Keep ROFR/ROFN hits out of true-signal counts until scope is classified.',
        '5. Use packet fields to prevent false positives from being re-promoted.',
        '',
        '## Next 10 Manual Reviews',
        '',
        markdown_table(manual, ['case_id', 'ticker', 'announcement_date', 'filings_checked_count', 'possible_hits_count', 'adjudication_status', 'next_action']) if manual else 'None.',
        '',
        '## Current Packet Fields',
        '',
        '- `prior_signal_hit_status`',
        '- `prior_signal_adjudication_status`',
        '- `true_prior_signal_rows`',
        '- `false_positive_rows`',
        '- Packet-level prior signal adjudication section with source URLs, filing dates, classifications, and notes.',
    ]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def run_packet_generator(dry_run: bool, limit: int) -> None:
    if dry_run:
        return
    subprocess.run(['python3', str(CASE_PACKET_GENERATOR), '--limit', str(limit)], cwd=REPO_ROOT, check=True)


def run(args: argparse.Namespace) -> list[dict[str, str]]:
    run_packet_generator(args.dry_run, args.limit)
    rows = build_batch_rows(args)
    if args.dry_run:
        return rows
    write_csv(args.output, rows, BATCH_FIELDS)
    write_report(args.report, rows)
    write_mini_study(args.mini_study, rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description='Batch acquired prior-public-signal workflow.')
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--tickers', nargs='*', default=[])
    parser.add_argument('--force', action='store_true', help='Reconsider already adjudicated cases in batch aggregation.')
    parser.add_argument('--dry-run', action='store_true', help='Build in memory and print summary without writing files.')
    parser.add_argument('--queue', type=Path, default=DEFAULT_QUEUE)
    parser.add_argument('--candidates', type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument('--acquisition-dates', type=Path, default=DEFAULT_ACQUISITION_DATES)
    parser.add_argument('--filing-targets', type=Path, default=DEFAULT_FILING_TARGETS)
    parser.add_argument('--signal-hits', type=Path, default=DEFAULT_SIGNAL_HITS)
    parser.add_argument('--adjudication-queue', type=Path, default=DEFAULT_ADJUDICATION_QUEUE)
    parser.add_argument('--confirmation-results', type=Path, default=DEFAULT_CONFIRMATION_RESULTS)
    parser.add_argument('--source-evidence', type=Path, default=DEFAULT_SOURCE_EVIDENCE)
    parser.add_argument('--packet-index', type=Path, default=DEFAULT_PACKET_INDEX)
    parser.add_argument('--output', type=Path, default=DEFAULT_BATCH_RESULTS)
    parser.add_argument('--report', type=Path, default=DEFAULT_BATCH_REPORT)
    parser.add_argument('--mini-study', type=Path, default=DEFAULT_MINI_STUDY)
    args = parser.parse_args()

    rows = run(args)
    counts = Counter(row['adjudication_status'] for row in rows)
    print(f'Cases processed: {len(rows)}')
    for status, count in counts.most_common():
        print(f'{status}: {count}')
    print(f'True prior public signals: {counts.get("TRUE_PUBLIC_PRIOR_SIGNAL", 0)}')
    print(f'Baseline candidates: {counts.get("DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE", 0)}')
    print(f'Needs manual review: {counts.get("NEEDS_MANUAL_REVIEW", 0) + counts.get("POSSIBLE_SIGNAL_NEEDS_REVIEW", 0)}')
    print(f'Blockers: {counts.get("DATE_MISSING", 0) + counts.get("SOURCE_BLOCKED", 0)}')
    if not args.dry_run:
        print(f'Results -> {args.output}')
        print(f'Report -> {args.report}')
        print(f'Mini-study -> {args.mini_study}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
