#!/usr/bin/env python3
"""
acquisition_announcement_date_backfiller.py

Backfill exact acquisition announcement dates for historical acquired cases.

The workflow is conservative: it never uses likely_outcome_year as a date, never
marks rows VERIFIED or CALIBRATION_ELIGIBLE, and distinguishes exact press
release dates from filing-date proxies that still need manual confirmation.

Usage:
    python3 src/historical_case_tools/acquisition_announcement_date_backfiller.py
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'

DEFAULT_QUEUE = HISTORICAL_DIR / 'acquisition_verification_queue.csv'
DEFAULT_SOURCE_EVIDENCE = HISTORICAL_DIR / 'source_evidence.csv'
DEFAULT_RESOLVED_CANDIDATES = HISTORICAL_DIR / 'resolved_case_candidates.csv'
DEFAULT_CONFIRMATION_RESULTS = HISTORICAL_DIR / 'prior_signal_confirmation_results.csv'
DEFAULT_OUTPUT = HISTORICAL_DIR / 'acquisition_announcement_dates.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'acquisition_announcement_date_report.md'

OUTPUT_FIELDS = [
    'case_id',
    'ticker',
    'company_name',
    'acquisition_announcement_date',
    'source_evidence_type',
    'source_url',
    'confidence',
    'notes',
    'next_action',
]


@dataclass(frozen=True)
class DateEvidence:
    date: str
    source_type: str
    source_url: str
    confidence: str
    notes: str
    next_action: str


CURATED_DATE_EVIDENCE = {
    'RHC-0005-ACQUIRED-CPXX': DateEvidence(
        date='2016-05-31',
        source_type='merger 8-K filing date',
        source_url='https://www.sec.gov/Archives/edgar/data/1327467/000114420416105668/v441287_8k.htm',
        confidence='MEDIUM',
        notes='Celator merger 8-K says the merger agreement was entered May 27, 2016; SEC archive filing date supports May 31, 2016 as the public filing date. Manual press-release confirmation still recommended.',
        next_action='Open the SEC 8-K and confirm whether Exhibit 99.1 or contemporaneous press release text says the transaction was announced on May 31, 2016.',
    ),
    'RHC-0007-ACQUIRED-RLYP': DateEvidence(
        date='2016-07-21',
        source_type='press release date',
        source_url='https://www.sec.gov/Archives/edgar/data/1416792/000119312516653088/d180740dex991.htm',
        confidence='HIGH',
        notes='SEC-filed press release says Galenica and Relypsa announced the acquisition on July 21, 2016.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0009-ACQUIRED-VTAE': DateEvidence(
        date='2016-09-14',
        source_type='SEC archive evidence',
        source_url='https://www.sec.gov/Archives/edgar/data/1157602/000119312516709207/d259988d8k.htm',
        confidence='HIGH',
        notes='Allergan 8-K says Allergan and Vitae issued a joint press release on September 14, 2016 announcing execution of the merger agreement.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0011-ACQUIRED-CLCD': DateEvidence(
        date='2017-01-18',
        source_type='SEC archive evidence',
        source_url='https://www.sec.gov/Archives/edgar/data/1348649/000119312517025226/d293672dsc14d9.htm',
        confidence='HIGH',
        notes='Schedule 14D-9 references the joint press release issued by Lilly and CoLucid dated January 18, 2017 and CoLucid 8-K filed January 18, 2017.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0012-ACQUIRED-DMTX': DateEvidence(
        date='2017-10-03',
        source_type='press release date',
        source_url='https://www.sec.gov/Archives/edgar/data/1592288/000119312517301611/d465335dex991.htm',
        confidence='HIGH',
        notes='SEC-filed press release dated October 3, 2017 says Ultragenyx and Dimension announced a definitive merger agreement.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0014-ACQUIRED-AVXS': DateEvidence(
        date='2018-04-09',
        source_type='press release date',
        source_url='https://www.sec.gov/Archives/edgar/data/1652923/000104746918002890/a2235337zsc14d9.htm',
        confidence='HIGH',
        notes='Schedule 14D-9 exhibit index incorporates AveXis press release dated April 9, 2018 and the AveXis 8-K filed April 9, 2018.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0016-ACQUIRED-CASC': DateEvidence(
        date='2018-01-31',
        source_type='press release date',
        source_url='https://www.sec.gov/Archives/edgar/data/1060736/000119312518026316/d519414dex991.htm',
        confidence='HIGH',
        notes='SEC-filed joint press release dated January 31, 2018 says Seattle Genetics and Cascadian announced a definitive merger agreement.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0018-ACQUIRED-RXDX': DateEvidence(
        date='2017-12-22',
        source_type='press release date',
        source_url='https://www.sec.gov/Archives/edgar/data/904566/000119312517377640/d510205dex992.htm',
        confidence='HIGH',
        notes='SEC-filed Roche key messages dated December 22, 2017 state Roche and Ignyta announced a definitive merger agreement.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0019-ACQUIRED-ALDR': DateEvidence(
        date='2019-09-16',
        source_type='SEC archive evidence',
        source_url='https://www.sec.gov/Archives/edgar/data/1423824/000119312519252175/d802332dsc14d9.htm',
        confidence='HIGH',
        notes='Schedule 14D-9 incorporates Alder 8-K filed September 16, 2019 and September 16 public communications for the Lundbeck transaction.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0020-ACQUIRED-ARRY': DateEvidence(
        date='2019-06-17',
        source_type='SEC archive evidence',
        source_url='https://www.sec.gov/Archives/edgar/data/1100412/000110465919035824/a19-11481_18k.htm',
        confidence='HIGH',
        notes='Array 8-K says Pfizer and Array issued a joint press release on June 17, 2019 announcing entry into the merger agreement.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0021-ACQUIRED-CMTA': DateEvidence(
        date='2019-02-25',
        source_type='press release date',
        source_url='https://www.sec.gov/Archives/edgar/data/1647320/000114420419009711/tv514509_6k.htm',
        confidence='HIGH',
        notes='Clementia 6-K furnishes a press release dated February 25, 2019 announcing Ipsen acquisition agreement.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0022-ACQUIRED-LOXO': DateEvidence(
        date='2019-01-07',
        source_type='SEC archive evidence',
        source_url='https://www.sec.gov/Archives/edgar/data/1581720/000119312519010967/d632967dsc14d9.htm',
        confidence='HIGH',
        notes='Schedule 14D-9 incorporates Lilly and Loxo joint press release dated January 7, 2019 and Loxo 8-K filed January 7, 2019.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0023-ACQUIRED-NITE': DateEvidence(
        date='2019-03-04',
        source_type='press release date',
        source_url='https://www.sec.gov/Archives/edgar/data/1711675/000119312519061793/d701876dex993.htm',
        confidence='HIGH',
        notes='SEC-filed press release dated March 4, 2019 says Nightstar reached agreement to be acquired by Biogen.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
    'RHC-0024-ACQUIRED-ONCE': DateEvidence(
        date='2019-02-25',
        source_type='SEC archive evidence',
        source_url='https://www.sec.gov/Archives/edgar/data/1609351/000119312519050035/d712070dsc14d9c.htm',
        confidence='HIGH',
        notes='Spark 14D-9C employee Q&A says Spark and Roche announced a definitive merger agreement on February 25, 2019.',
        next_action='Use this date as the prior-signal search cutoff; no date backfill action remaining.',
    ),
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


def index_by(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    indexed = {}
    for row in rows:
        value = row.get(key, '').strip()
        if value and value not in indexed:
            indexed[value] = row
    return indexed


def target_cases(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    missing = [row for row in rows if row.get('hit_status', '').strip() == 'DATE_MISSING']
    if missing:
        return missing, len(missing)
    return [row for row in rows if row.get('case_id', '').strip() in CURATED_DATE_EVIDENCE], 0


def local_source_evidence(row: dict[str, str], evidence_by_id: dict[str, list[dict[str, str]]]) -> DateEvidence | None:
    for evidence in evidence_by_id.get(row.get('case_id', ''), []):
        supports = evidence.get('supports_field', '').upper()
        if 'DEAL_ANNOUNCEMENT_DATE' not in supports:
            continue
        filing_date = evidence.get('filing_date', '').strip()
        source_url = evidence.get('source_url', '').strip()
        if not filing_date or not source_url or source_url == 'VERIFY_REQUIRED':
            continue
        evidence_type = evidence.get('evidence_type', '').strip().upper()
        source_type = 'merger 8-K filing date' if '8K' in evidence_type or '8-K' in evidence.get('filing_type', '') else 'SEC archive evidence'
        return DateEvidence(
            date=filing_date,
            source_type=source_type,
            source_url=source_url,
            confidence='MEDIUM',
            notes=f"Local source_evidence row {evidence.get('evidence_id', '')} supports deal_announcement_date; filing date used unless announcement text explicitly confirms the same date.",
            next_action='Open the source and confirm whether the filing date equals the public announcement date.',
        )
    return None


def evidence_by_case(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        case_id = row.get('case_id', '').strip()
        if case_id:
            grouped.setdefault(case_id, []).append(row)
    return grouped


def build_row(
    target: dict[str, str],
    queue_by_id: dict[str, dict[str, str]],
    candidates_by_id: dict[str, dict[str, str]],
    evidence_by_id: dict[str, list[dict[str, str]]],
) -> dict[str, str]:
    case_id = target.get('case_id', '').strip()
    evidence = local_source_evidence(target, evidence_by_id) or CURATED_DATE_EVIDENCE.get(case_id)
    queue_row = queue_by_id.get(case_id, {})
    candidate_row = candidates_by_id.get(case_id, {})
    ticker = target.get('ticker') or queue_row.get('ticker') or candidate_row.get('ticker', '')
    company = target.get('company_name') or queue_row.get('company_name') or candidate_row.get('company_name', '')

    if evidence is None:
        return {
            'case_id': case_id,
            'ticker': ticker,
            'company_name': company,
            'acquisition_announcement_date': '',
            'source_evidence_type': 'manual needed',
            'source_url': '',
            'confidence': 'MISSING',
            'notes': 'No source-backed exact acquisition announcement date found in local evidence or curated SEC backfill evidence. likely_outcome_year was not used as a date.',
            'next_action': 'Open merger 8-K, press release, Schedule TO, 6-K, or Schedule 14D-9 and record exact public announcement date.',
        }

    return {
        'case_id': case_id,
        'ticker': ticker,
        'company_name': company,
        'acquisition_announcement_date': evidence.date,
        'source_evidence_type': evidence.source_type,
        'source_url': evidence.source_url,
        'confidence': evidence.confidence,
        'notes': evidence.notes,
        'next_action': evidence.next_action,
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


def write_report(path: Path, rows: list[dict[str, str]], before_missing: int) -> None:
    counts = Counter(row['confidence'] for row in rows)
    backfilled = sum(1 for row in rows if row.get('acquisition_announcement_date'))
    missing = sum(1 for row in rows if not row.get('acquisition_announcement_date'))
    path.write_text(f"""# Acquisition Announcement Date Backfill Report

Generated by `src/historical_case_tools/acquisition_announcement_date_backfiller.py`.

## Summary

- DATE_MISSING cases in current confirmation input: {before_missing}
- Original backfill target set: {len(rows)} prior DATE_MISSING target cases
- Target cases processed: {len(rows)}
- Announcement dates backfilled: {backfilled}
- Remaining missing: {missing}
- HIGH confidence: {counts.get('HIGH', 0)}
- MEDIUM confidence: {counts.get('MEDIUM', 0)}
- LOW confidence: {counts.get('LOW', 0)}
- MISSING confidence: {counts.get('MISSING', 0)}
- No rows were marked `VERIFIED` or `CALIBRATION_ELIGIBLE`.

## Backfilled Dates

{markdown_table(rows, ['case_id', 'ticker', 'company_name', 'acquisition_announcement_date', 'source_evidence_type', 'confidence', 'source_url'])}

## Remaining Manual Work

{markdown_table([row for row in rows if row['confidence'] in {'MEDIUM', 'LOW', 'MISSING'}], ['case_id', 'ticker', 'acquisition_announcement_date', 'confidence', 'next_action']) if any(row['confidence'] in {'MEDIUM', 'LOW', 'MISSING'} for row in rows) else 'None for date backfill.'}

## Rules Applied

- Did not use `likely_outcome_year` as an announcement date.
- Preferred SEC-filed press release dates when available.
- Used `MEDIUM` when a filing date likely equals announcement date but the excerpt does not independently confirm announcement timing.
- Did not change scanner scoring, dashboard files, `VERIFIED`, or `CALIBRATION_ELIGIBLE` fields.
""", encoding='utf-8')


def run(args: argparse.Namespace) -> list[dict[str, str]]:
    confirmation_rows = read_csv(args.confirmation_results)
    targets, before_missing = target_cases(confirmation_rows)
    queue_by_id = index_by(read_csv(args.queue), 'candidate_id')
    candidates_by_id = index_by(read_csv(args.resolved_candidates), 'candidate_id')
    evidence_by_id = evidence_by_case(read_csv(args.source_evidence))
    rows = [
        build_row(target, queue_by_id, candidates_by_id, evidence_by_id)
        for target in targets
    ]
    write_csv(args.output, rows, OUTPUT_FIELDS)
    write_report(args.report, rows, before_missing)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description='Backfill exact acquisition announcement dates for historical acquired cases.')
    parser.add_argument('--queue', type=Path, default=DEFAULT_QUEUE)
    parser.add_argument('--source-evidence', type=Path, default=DEFAULT_SOURCE_EVIDENCE)
    parser.add_argument('--resolved-candidates', type=Path, default=DEFAULT_RESOLVED_CANDIDATES)
    parser.add_argument('--confirmation-results', type=Path, default=DEFAULT_CONFIRMATION_RESULTS)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    rows = run(args)
    counts = Counter(row['confidence'] for row in rows)
    backfilled = sum(1 for row in rows if row.get('acquisition_announcement_date'))
    print(f'Target cases processed: {len(rows)}')
    print(f'Announcement dates backfilled: {backfilled}')
    print(f'HIGH confidence: {counts.get("HIGH", 0)}')
    print(f'MEDIUM confidence: {counts.get("MEDIUM", 0)}')
    print(f'LOW confidence: {counts.get("LOW", 0)}')
    print(f'MISSING confidence: {counts.get("MISSING", 0)}')
    print(f'Output -> {args.output}')
    print(f'Report -> {args.report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
