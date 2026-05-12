#!/usr/bin/env python3
"""
acquisition_background_extractor.py

Extract Schedule 14D-9 / proxy background sections for PARTIAL acquisition
cases and classify whether a public pre-announcement process signal existed.

The extractor is intentionally conservative. Private negotiations disclosed
after the deal do not set the observation date unless the background section
states that the signal was publicly announced or otherwise public at the time.

Usage:
    python3 src/historical_case_tools/acquisition_background_extractor.py
    python3 src/historical_case_tools/acquisition_background_extractor.py --tickers NPSP MDVN
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / 'data' / 'historical_cases'
CASES_PARTIAL = HISTORICAL_DIR / 'cases_partial.csv'
SOURCE_EVIDENCE = HISTORICAL_DIR / 'source_evidence.csv'
DEFAULT_FINDINGS = HISTORICAL_DIR / 'acquisition_background_findings.csv'
DEFAULT_REPORT = HISTORICAL_DIR / 'acquisition_background_report.md'

TARGET_TICKERS = ['NPSP', 'PCYC', 'ZSPH', 'ANAC', 'MDVN']
RUN_DATE = '2026-05-12'
USER_AGENT = 'ma-scanner-research/1.0 jackdiemar@example.com'
REQUEST_SLEEP_SECONDS = 0.15

FINDING_FIELDS = [
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


@dataclass(frozen=True)
class TargetCase:
    ticker: str
    case_id: str
    company: str
    deal_date: str
    proxy_url: str
    proxy_filing_type: str
    proxy_filing_date: str
    proxy_accession: str
    merger_8k_url: str


TARGETS: dict[str, TargetCase] = {
    'NPSP': TargetCase(
        ticker='NPSP',
        case_id='RHC-0001-ACQUIRED-NPSP',
        company='NPS Pharmaceuticals, Inc.',
        deal_date='2015-01-12',
        proxy_url='https://www.sec.gov/Archives/edgar/data/890465/000104746915000380/a2222816zsc14d9.htm',
        proxy_filing_type='SC 14D9',
        proxy_filing_date='2015-01-23',
        proxy_accession='0001047469-15-000380',
        merger_8k_url='https://www.sec.gov/Archives/edgar/data/890465/000110465915001685/a15-2148_18k.htm',
    ),
    'PCYC': TargetCase(
        ticker='PCYC',
        case_id='RHC-0002-ACQUIRED-PCYC',
        company='Pharmacyclics, Inc.',
        deal_date='2015-03-06',
        proxy_url='https://www.sec.gov/Archives/edgar/data/949699/000119312515101106/d893590dsc14d9.htm',
        proxy_filing_type='SC 14D9',
        proxy_filing_date='2015-03-23',
        proxy_accession='0001193125-15-101106',
        merger_8k_url='https://www.sec.gov/Archives/edgar/data/949699/000119312515081198/d885732d8k.htm',
    ),
    'ZSPH': TargetCase(
        ticker='ZSPH',
        case_id='RHC-0003-ACQUIRED-ZSPH',
        company='ZS Pharma, Inc.',
        deal_date='2015-11-06',
        proxy_url='https://www.sec.gov/Archives/edgar/data/1459266/000119312515380466/d28720dsc14d9.htm',
        proxy_filing_type='SC 14D9',
        proxy_filing_date='2015-11-18',
        proxy_accession='0001193125-15-380466',
        merger_8k_url='https://www.sec.gov/Archives/edgar/data/1459266/000119312515369081/d73329d8k.htm',
    ),
    'ANAC': TargetCase(
        ticker='ANAC',
        case_id='RHC-0004-ACQUIRED-ANAC',
        company='Anacor Pharmaceuticals, Inc.',
        deal_date='2016-05-16',
        proxy_url='https://www.sec.gov/Archives/edgar/data/1411158/000119312516603880/d319707dsc14d9.htm',
        proxy_filing_type='SC 14D9',
        proxy_filing_date='2016-05-26',
        proxy_accession='0001193125-16-603880',
        merger_8k_url='https://www.sec.gov/Archives/edgar/data/1411158/000095010316013361/dp65732_8k.htm',
    ),
    'MDVN': TargetCase(
        ticker='MDVN',
        case_id='RHC-0006-ACQUIRED-MDVN',
        company='Medivation, Inc.',
        deal_date='2016-08-22',
        proxy_url='https://www.sec.gov/Archives/edgar/data/1011835/000119312516696911/d234696dsc14d9.htm',
        proxy_filing_type='SC 14D9',
        proxy_filing_date='2016-08-30',
        proxy_accession='0001193125-16-696911',
        merger_8k_url='https://www.sec.gov/Archives/edgar/data/1011835/000119312516686961/d245915d8k.htm',
    ),
}

SECTION_HEADINGS = [
    'Background of the Offer and the Merger',
    'Background of Offer and Merger',
    'Background of the Merger',
    'Background of the Offer',
    'Background of the Proposed Transaction',
]

NEXT_SECTION_PATTERNS = [
    r'\bReasons for Recommendation\b',
    r'\bReasons for the Recommendation\b',
    r'\bReasons for the Board',
    r'\bReasons for the Merger\b',
    r'\bRecommendation of the Board\b',
    r'\bOpinion of',
    r'\bIntent to Tender\b',
]

DATE_TEXT_PATTERN = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}'
DATE_RE = re.compile(DATE_TEXT_PATTERN)
PUBLIC_MARKER_RE = re.compile(
    r'\b(publicly\s+(?:announced|disclosed|confirmed|made)|made\s+public|announced\s+publicly|issued\s+a\s+press\s+release)\b',
    re.I,
)
ACQUISITION_TERM_RE = re.compile(r'\b(proposal|offer|bid|acquir|tender\s+offer|merger)\b', re.I)

PUBLIC_SIGNAL_PATTERNS = [
    (
        'outreach / competing bids',
        re.compile(
            rf'(?P<date>{DATE_TEXT_PATTERN}).{{0,280}}?'
            r'(?:publicly\s+(?:announced|disclosed|confirmed|made)|made\s+public|announced\s+publicly|issued\s+a\s+press\s+release).{0,360}?'
            r'(?:proposal|offer|bid|acquir|tender\s+offer|merger)',
            re.I | re.S,
        ),
    ),
    (
        'outreach / competing bids',
        re.compile(
            r'(?:publicly\s+(?:announced|disclosed|confirmed|made)|made\s+public|announced\s+publicly|issued\s+a\s+press\s+release).{0,280}?'
            r'(?:proposal|offer|bid|acquir|tender\s+offer|merger).{0,180}?'
            rf'(?P<date>{DATE_TEXT_PATTERN})',
            re.I | re.S,
        ),
    ),
    (
        'strategic alternatives',
        re.compile(
            rf'(?P<date>{DATE_TEXT_PATTERN}).{{0,280}}?'
            r'(?:publicly\s+(?:announced|disclosed)|announced\s+publicly|issued\s+a\s+press\s+release).{0,260}?strategic\s+alternatives',
            re.I | re.S,
        ),
    ),
    (
        'activist pressure',
        re.compile(
            rf'(?P<date>{DATE_TEXT_PATTERN}).{{0,280}}?'
            r'(?:Schedule\s+13D|activist|shareholder).{0,260}?(?:publicly|filed|announced)',
            re.I | re.S,
        ),
    ),
    (
        'ROFR / ROFN / option rights',
        re.compile(
            rf'(?P<date>{DATE_TEXT_PATTERN}).{{0,280}}?'
            r'(?:publicly\s+(?:announced|disclosed)|filed).{0,260}?(?:right\s+of\s+first|option\s+to\s+acquire)',
            re.I | re.S,
        ),
    ),
]

PRIVATE_PROCESS_HINTS = re.compile(
    r'\b(contacted|met with|negotiat|indication of interest|confidentiality agreement|non-disclosure agreement|due diligence|management presentation)\b',
    re.I,
)

def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str], *, quote_all: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            quoting=csv.QUOTE_ALL if quote_all else csv.QUOTE_MINIMAL,
            lineterminator='\n',
        )
        writer.writeheader()
        writer.writerows(rows)


def fetch_text(url: str) -> str:
    time.sleep(REQUEST_SLEEP_SECONDS)
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode('utf-8', errors='replace')


def html_to_text(raw: str) -> str:
    text = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', ' ', raw)
    text = re.sub(r'(?is)<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = text.replace('\xa0', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\s*\n\s*', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def clean_excerpt(text: str, max_chars: int = 500) -> str:
    cleaned = re.sub(r'\s+', ' ', text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(' ', 1)[0].rstrip(' ,.;') + '...'


def excerpt_around(text: str, start: int, end: int, max_chars: int = 500) -> str:
    left = max(text.rfind('. ', 0, start), text.rfind('\n', 0, start))
    right_period = text.find('. ', end)
    right_break = text.find('\n', end)
    right_candidates = [pos for pos in [right_period, right_break] if pos != -1]
    excerpt_start = left + 1 if left != -1 else max(0, start - 120)
    excerpt_end = min(right_candidates) + 1 if right_candidates else min(len(text), end + 240)
    return clean_excerpt(text[excerpt_start:excerpt_end], max_chars=max_chars)


def parse_date(value: str) -> str:
    return datetime.strptime(value, '%B %d, %Y').strftime('%Y-%m-%d')


def extract_background(text: str) -> tuple[bool, str, str]:
    lowered = text.lower()
    candidates: list[tuple[int, str, str]] = []
    for heading in SECTION_HEADINGS:
        for match in re.finditer(re.escape(heading.lower()), lowered):
            start = match.start()
            end = len(text)
            tail = text[start + len(heading):]
            for pattern in NEXT_SECTION_PATTERNS:
                next_match = re.search(pattern, tail, re.I)
                if next_match:
                    end = start + len(heading) + next_match.start()
                    break
            section = text[start:end].strip()
            after_heading = section[len(heading):len(heading) + 120]
            if re.search(r'\bin\s+(?:this\s+)?Item\s+4\(b\)\s+above\b', after_heading, re.I):
                continue
            # Schedule 14D-9 tables of contents often repeat headings with no
            # body text. Require enough narrative text to avoid TOC matches.
            if len(section) >= 1000:
                candidates.append((len(section), heading, section))
    if not candidates:
        return False, '', ''
    _, heading, section = max(candidates, key=lambda item: item[0])
    return True, heading, section


def find_public_signal(section: str, deal_date: str) -> tuple[str, str, str, str]:
    sentence_hits = []
    for marker in PUBLIC_MARKER_RE.finditer(section):
        excerpt = excerpt_around(section, marker.start(), marker.end())
        if not ACQUISITION_TERM_RE.search(excerpt):
            continue
        window_start = max(0, marker.start() - 160)
        window = section[window_start:marker.end() + 240]
        marker_offset = marker.start() - window_start
        dated_markers = list(DATE_RE.finditer(window))
        prior_dates = [date_match for date_match in dated_markers if date_match.end() <= marker_offset]
        selected_dates = [max(prior_dates, key=lambda date_match: date_match.end())] if prior_dates else dated_markers[:1]
        for date_match in selected_dates:
            try:
                signal_date = parse_date(date_match.group(0))
            except ValueError:
                continue
            if signal_date >= deal_date:
                continue
            sentence_hits.append((signal_date, 'outreach / competing bids', excerpt))

    if sentence_hits:
        signal_date, signal_type, excerpt = sorted(sentence_hits, key=lambda item: item[0])[0]
        return 'FOUND_PUBLIC', signal_type, signal_date, excerpt

    hits = []
    for signal_type, pattern in PUBLIC_SIGNAL_PATTERNS:
        for match in pattern.finditer(section):
            try:
                signal_date = parse_date(match.group('date'))
            except ValueError:
                continue
            if signal_date >= deal_date:
                continue
            excerpt = excerpt_around(section, match.start(), match.end())
            hits.append((signal_date, signal_type, excerpt))
    if hits:
        signal_date, signal_type, excerpt = sorted(hits, key=lambda item: item[0])[0]
        return 'FOUND_PUBLIC', signal_type, signal_date, excerpt

    private_hint = PRIVATE_PROCESS_HINTS.search(section)
    if private_hint:
        lookback_start = max(0, private_hint.start() - 300)
        lookback = section[lookback_start:private_hint.start()]
        prior_dates = []
        for date_match in DATE_RE.finditer(lookback):
            try:
                if parse_date(date_match.group(0)) < deal_date:
                    prior_dates.append(date_match)
            except ValueError:
                continue
        excerpt_start = lookback_start + prior_dates[-1].start() if prior_dates else max(0, private_hint.start() - 180)
        excerpt = clean_excerpt(section[excerpt_start:excerpt_start + 650])
        return 'NONE_FOUND', 'none found', '', excerpt

    return 'NONE_FOUND', 'none found', '', clean_excerpt(section)


def build_finding(target: TargetCase) -> dict[str, str]:
    raw = fetch_text(target.proxy_url)
    text = html_to_text(raw)
    available, heading, section = extract_background(text)
    if not available:
        return {
            'case_id': target.case_id,
            'ticker': target.ticker,
            'company': target.company,
            'proxy_source_url': target.proxy_url,
            'proxy_filing_type': target.proxy_filing_type,
            'proxy_filing_date': target.proxy_filing_date,
            'background_section_available': 'FALSE',
            'background_heading': '',
            'first_public_acquisition_announcement_date': target.deal_date,
            'prior_process_signal': 'UNKNOWN',
            'prior_process_signal_type': 'unknown',
            'prior_process_signal_date': '',
            'relevant_excerpt': '',
            'confidence': 'LOW',
            'observation_date_candidate': target.deal_date,
            'observation_date_reasoning': 'Background section was not extracted; keep deal announcement date as placeholder candidate until manual review.',
            'remaining_evidence_gaps': common_gaps(),
        }

    signal, signal_type, signal_date, excerpt = find_public_signal(section, target.deal_date)
    if signal == 'FOUND_PUBLIC':
        obs_date = signal_date
        reasoning = (
            'A public pre-announcement acquisition signal appears in the background section; '
            'use the first public signal date as observation_date_candidate pending contemporaneous source confirmation.'
        )
        confidence = 'MEDIUM'
    else:
        obs_date = target.deal_date
        reasoning = (
            'No public pre-announcement process signal was detected in the extracted background section. '
            'Private outreach, negotiations, diligence, and bid activity disclosed later are not public t=0 signals, '
            'so the acquisition announcement date remains the observation_date_candidate.'
        )
        confidence = 'MEDIUM' if excerpt else 'LOW'

    return {
        'case_id': target.case_id,
        'ticker': target.ticker,
        'company': target.company,
        'proxy_source_url': target.proxy_url,
        'proxy_filing_type': target.proxy_filing_type,
        'proxy_filing_date': target.proxy_filing_date,
        'background_section_available': 'TRUE',
        'background_heading': heading,
        'first_public_acquisition_announcement_date': target.deal_date,
        'prior_process_signal': signal,
        'prior_process_signal_type': signal_type,
        'prior_process_signal_date': signal_date,
        'relevant_excerpt': excerpt,
        'confidence': confidence,
        'observation_date_candidate': obs_date,
        'observation_date_reasoning': reasoning,
        'remaining_evidence_gaps': remaining_gaps(signal),
    }


def common_gaps() -> str:
    return (
        'manual background review; contemporaneous prior-process source check; '
        'premium extraction; price-window verification'
    )


def remaining_gaps(signal: str) -> str:
    gaps = ['price-window verification']
    if signal == 'FOUND_PUBLIC':
        gaps.extend([
            'contemporaneous public-source confirmation for prior signal date',
            'premium extraction review',
        ])
    else:
        gaps.extend([
            'manual no-hit confirmation across pre-announcement 8-K/13D/10-K/10-Q filings',
            'premium extraction review',
        ])
    return '; '.join(gaps)


def update_cases_partial(findings: list[dict[str, str]]) -> None:
    fields, rows = read_csv(CASES_PARTIAL)
    if not fields:
        raise RuntimeError(f'missing or empty {CASES_PARTIAL}')

    by_case = {finding['case_id']: finding for finding in findings}
    for row in rows:
        finding = by_case.get(row.get('case_id', ''))
        if not finding:
            continue
        signal = finding['prior_process_signal']
        row['had_prior_process_signal'] = 'TRUE' if signal == 'FOUND_PUBLIC' else 'FALSE'
        row['data_quality'] = 'PARTIAL'
        existing_notes = row.get('notes', '').strip()
        existing_notes = re.sub(r'\s*\|\s*BACKGROUND_EXTRACT_2026-05-12:.*?(?=\s*\|\s*|$)', '', existing_notes).strip()
        note = (
            f"BACKGROUND_EXTRACT_2026-05-12: prior_process_signal={finding['prior_process_signal']}; "
            f"prior_process_signal_type={finding['prior_process_signal_type']}; "
            f"observation_date_candidate={finding['observation_date_candidate']}. "
            f"Do not mark VERIFIED/CALIBRATION_ELIGIBLE until remaining gaps are closed: {finding['remaining_evidence_gaps']}."
        )
        row['notes'] = f'{existing_notes} | {note}' if existing_notes else note

    write_csv(CASES_PARTIAL, rows, fields)


def next_evidence_id(existing_rows: list[dict[str, str]], case_id: str) -> str:
    max_seen = 0
    prefix = f'{case_id}-SRC-'
    for row in existing_rows:
        evidence_id = row.get('evidence_id', '')
        if evidence_id.startswith(prefix):
            suffix = evidence_id.removeprefix(prefix)
            if suffix.isdigit():
                max_seen = max(max_seen, int(suffix))
    return f'{prefix}{max_seen + 1:03d}'


def update_source_evidence(findings: list[dict[str, str]]) -> None:
    fields, rows = read_csv(SOURCE_EVIDENCE)
    if not fields:
        raise RuntimeError(f'missing or empty {SOURCE_EVIDENCE}')

    for finding in findings:
        if finding['background_section_available'] != 'TRUE' or not finding['relevant_excerpt']:
            continue
        notes = (
            f"BACKGROUND_EXTRACT_2026-05-12: prior_process_signal={finding['prior_process_signal']}; "
            f"observation_date_candidate={finding['observation_date_candidate']}; not VERIFIED/calibration eligible."
        )
        existing = next(
            (
                row for row in rows
                if row.get('case_id') == finding['case_id']
                and row.get('evidence_type') == 'PROXY_SA_LANGUAGE'
                and row.get('notes', '').startswith('BACKGROUND_EXTRACT_2026-05-12:')
            ),
            None,
        )
        payload = {
            'evidence_id': existing['evidence_id'] if existing else next_evidence_id(rows, finding['case_id']),
            'case_id': finding['case_id'],
            'ticker': finding['ticker'],
            'evidence_type': 'PROXY_SA_LANGUAGE',
            'source_name': 'SEC EDGAR Schedule 14D-9',
            'source_url': finding['proxy_source_url'],
            'filing_type': finding['proxy_filing_type'],
            'filing_date': finding['proxy_filing_date'],
            'accession_number': TARGETS[finding['ticker']].proxy_accession,
            'exhibit_number': '',
            'excerpt': finding['relevant_excerpt'],
            'supports_field': 'had_prior_process_signal|notes|observation_date',
            'confidence': finding['confidence'],
            'verification_status': 'PARTIAL',
            'added_by': 'manual',
            'added_date': RUN_DATE,
            'notes': notes,
        }
        if existing:
            existing.update(payload)
            continue
        rows.append(payload)

    write_csv(SOURCE_EVIDENCE, rows, fields, quote_all=True)


def write_report(findings: list[dict[str, str]], path: Path) -> None:
    found_count = sum(1 for row in findings if row['background_section_available'] == 'TRUE')
    prior_count = sum(1 for row in findings if row['prior_process_signal'] == 'FOUND_PUBLIC')
    lines = [
        '# Acquisition Background Extraction Report',
        '',
        f'Generated: {RUN_DATE}',
        '',
        '## Summary',
        '',
        f'- Target cases reviewed: {len(findings)}',
        f'- Background sections found: {found_count}',
        f'- Public pre-announcement process signals found: {prior_count}',
        '- No cases were marked VERIFIED or CALIBRATION_ELIGIBLE.',
        '',
        '## Findings',
        '',
        '| ticker | background found | prior_process_signal | prior_process_signal_type | observation_date_candidate | confidence |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for row in findings:
        lines.append(
            f"| {row['ticker']} | {row['background_section_available']} | {row['prior_process_signal']} | "
            f"{row['prior_process_signal_type']} | {row['observation_date_candidate']} | {row['confidence']} |"
        )

    lines.extend([
        '',
        '## Case Notes',
        '',
    ])
    for row in findings:
        lines.extend([
            f"### {row['ticker']} - {row['case_id']}",
            '',
            f"- Proxy source: {row['proxy_source_url']}",
            f"- Background heading: {row['background_heading'] or 'not extracted'}",
            f"- First public acquisition announcement date: {row['first_public_acquisition_announcement_date']}",
            f"- Prior process signal: {row['prior_process_signal']} ({row['prior_process_signal_type']})",
            f"- Observation date candidate: {row['observation_date_candidate']}",
            f"- Reasoning: {row['observation_date_reasoning']}",
            f"- Remaining gaps: {row['remaining_evidence_gaps']}",
            f"- Excerpt: {row['relevant_excerpt'] or 'No excerpt extracted.'}",
            '',
        ])
    path.write_text('\n'.join(lines), encoding='utf-8')


def selected_targets(tickers: Iterable[str] | None) -> list[TargetCase]:
    if not tickers:
        return [TARGETS[ticker] for ticker in TARGET_TICKERS]
    selected = []
    for ticker in tickers:
        clean = ticker.upper()
        if clean not in TARGETS:
            raise ValueError(f'unsupported ticker for first-five extraction: {ticker}')
        selected.append(TARGETS[clean])
    return selected


def run(args: argparse.Namespace) -> list[dict[str, str]]:
    targets = selected_targets(args.tickers)
    findings = [build_finding(target) for target in targets]
    write_csv(args.findings, findings, FINDING_FIELDS)
    write_report(findings, args.report)
    if not args.no_update_cases:
        update_cases_partial(findings)
    if not args.no_update_evidence:
        update_source_evidence(findings)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description='Extract first-five acquisition background sections.')
    parser.add_argument('--tickers', nargs='*', help='Optional subset of target tickers.')
    parser.add_argument('--findings', type=Path, default=DEFAULT_FINDINGS)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    parser.add_argument('--no-update-cases', action='store_true')
    parser.add_argument('--no-update-evidence', action='store_true')
    args = parser.parse_args()

    findings = run(args)
    print(f'Wrote {args.findings}')
    print(f'Wrote {args.report}')
    print(f'Background sections found: {sum(1 for row in findings if row["background_section_available"] == "TRUE")}/{len(findings)}')
    print(f'Public prior process signals found: {sum(1 for row in findings if row["prior_process_signal"] == "FOUND_PUBLIC")}/{len(findings)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
