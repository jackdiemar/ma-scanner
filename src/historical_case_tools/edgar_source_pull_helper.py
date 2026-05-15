#!/usr/bin/env python3
"""
edgar_source_pull_helper.py

Lightweight helper for pulling SEC filing text into a local source-text cache.
It downloads or reads filing source text, normalizes it for manual review, writes
a text copy plus metadata sidecar, and can print snippets around process phrases.

Usage:
    python3 src/historical_case_tools/edgar_source_pull_helper.py \\
        --url "https://www.sec.gov/Archives/edgar/data/899866/000110465920056508/tm2018594d2_ex99-1.htm" \\
        --case-id "RHC-0042-ACQUIRED-PTLA" \\
        --ticker "PTLA" \\
        --filing-type "8-K" \\
        --find "tender offer" \\
        --find "merger agreement"
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / 'data' / 'historical_cases' / 'source_text_cache'
USER_AGENT = 'ma-scanner-edgar-source-pull/1.0 jackdiemar@example.com'


def safe_part(value: str, default: str = 'UNKNOWN') -> str:
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '_', value.strip())
    cleaned = cleaned.strip('_')
    return cleaned or default


def infer_accession(value: str) -> str:
    patterns = [
        r'([0-9]{10}-[0-9]{2}-[0-9]{6})',
        r'/Archives/edgar/data/[0-9]+/([0-9]{18})/',
        r'/ixviewer/doc/action\?doc=/Archives/edgar/data/[0-9]+/([0-9]{18})/',
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if not match:
            continue
        raw = match.group(1)
        if '-' in raw:
            return raw
        return f'{raw[:10]}-{raw[10:12]}-{raw[12:]}'
    return hashlib.sha1(value.encode('utf-8')).hexdigest()[:12]


def build_archive_url(cik: str, accession_number: str, primary_document: str) -> str:
    cik_digits = re.sub(r'\D+', '', cik)
    accession_digits = re.sub(r'\D+', '', accession_number)
    document = primary_document.strip().lstrip('/')
    return f'https://www.sec.gov/Archives/edgar/data/{cik_digits}/{accession_digits}/{document}'


def read_source(source: str, *, timeout: int = 20) -> tuple[str, str]:
    if source.startswith(('http://', 'https://')):
        req = urllib.request.Request(source, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            data = response.read()
        return data.decode(charset, errors='replace'), source

    path = Path(source).expanduser()
    return path.read_text(encoding='utf-8', errors='replace'), str(path)


def normalize_text(raw: str) -> str:
    text = raw
    text = re.sub(r'(?is)<(script|style).*?</\1>', ' ', text)
    text = re.sub(r'(?i)<br\s*/?>', '\n', text)
    text = re.sub(r'(?i)</(p|div|tr|table|section|article|h[1-6]|li)>', '\n', text)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = text.replace('\xa0', ' ')
    text = re.sub(r'[ \t\r\f\v]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip() + '\n'


def snippets(text: str, phrase: str, *, context_chars: int) -> list[str]:
    found = []
    pattern = re.compile(re.escape(phrase), re.IGNORECASE)
    for match in pattern.finditer(text):
        start = max(0, match.start() - context_chars // 2)
        end = min(len(text), match.end() + context_chars // 2)
        snippet = text[start:end].replace('\n', ' ')
        snippet = re.sub(r'\s+', ' ', snippet).strip()
        found.append(snippet)
    return found


def write_outputs(
    *,
    text: str,
    source_url: str,
    case_id: str,
    ticker: str,
    filing_type: str,
    accession_number: str,
    output_dir: Path,
    notes: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = '_'.join([
        safe_part(case_id),
        safe_part(ticker),
        safe_part(filing_type),
        safe_part(accession_number),
    ])
    text_path = output_dir / f'{stem}.txt'
    metadata_path = output_dir / f'{stem}.json'

    text_path.write_text(text, encoding='utf-8')
    metadata = {
        'case_id': case_id,
        'ticker': ticker,
        'filing_type': filing_type,
        'source_url': source_url,
        'accession_number': accession_number,
        'pulled_at': datetime.now(timezone.utc).isoformat(),
        'text_length': len(text),
        'normalized_text_path': str(text_path.relative_to(REPO_ROOT)),
        'notes': notes,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return text_path, metadata_path


def source_values(args: argparse.Namespace) -> list[str]:
    values = list(args.url or [])
    if args.input_file:
        values.extend(args.input_file)
    if not values and args.cik and args.accession_number and args.primary_document:
        values.append(build_archive_url(args.cik, args.accession_number, args.primary_document))
    return values


def process_source(source: str, args: argparse.Namespace) -> bool:
    try:
        raw, source_url = read_source(source, timeout=args.timeout)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        print(f'[ERROR] Could not read {source}: {exc}', file=sys.stderr)
        return False

    accession_number = args.accession_number or infer_accession(source_url)
    normalized = normalize_text(raw)
    notes = args.notes or 'Local source-text cache for historical case review; not final classification evidence.'

    text_path, metadata_path = write_outputs(
        text=normalized,
        source_url=source_url,
        case_id=args.case_id,
        ticker=args.ticker,
        filing_type=args.filing_type,
        accession_number=accession_number,
        output_dir=args.output_dir,
        notes=notes,
    )
    print(f'[OK] Wrote {text_path.relative_to(REPO_ROOT)}')
    print(f'[OK] Wrote {metadata_path.relative_to(REPO_ROOT)}')
    print(f'[OK] Normalized text length: {len(normalized):,} chars')

    for phrase in args.find or []:
        matches = snippets(normalized, phrase, context_chars=args.snippet_chars)
        if not matches:
            print(f'\n[find] "{phrase}": no matches')
            continue
        print(f'\n[find] "{phrase}": {len(matches)} match(es)')
        for index, snippet in enumerate(matches, start=1):
            print(f'  {index}. ...{snippet}...')
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Pull SEC filing text into a normalized local source-text cache.'
    )
    parser.add_argument('--url', action='append', help='SEC archive or accession URL. Can be repeated.')
    parser.add_argument('--input-file', action='append', help='Local filing text/HTML file to normalize. Can be repeated.')
    parser.add_argument('--case-id', required=True, help='Historical case ID, e.g. RHC-0042-ACQUIRED-PTLA.')
    parser.add_argument('--ticker', required=True, help='Ticker symbol.')
    parser.add_argument('--filing-type', required=True, help='Filing type, e.g. 8-K, SC 14D-9, 10-Q.')
    parser.add_argument('--cik', help='CIK used with --accession-number and --primary-document to build an SEC archive URL.')
    parser.add_argument('--accession-number', help='SEC accession number. Inferred from URL when possible.')
    parser.add_argument('--primary-document', help='Primary document filename used with --cik and --accession-number.')
    parser.add_argument('--find', action='append', help='Phrase to search in normalized text. Can be repeated.')
    parser.add_argument('--snippet-chars', type=int, default=420, help='Characters of context to print around --find matches.')
    parser.add_argument('--sleep-seconds', type=float, default=0.2, help='Sleep between multiple source pulls.')
    parser.add_argument('--timeout', type=int, default=20, help='HTTP read timeout in seconds.')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR, help='Output directory for text and metadata files.')
    parser.add_argument('--notes', default='', help='Optional metadata notes.')
    args = parser.parse_args()
    if not source_values(args):
        parser.error('Provide --url, --input-file, or --cik + --accession-number + --primary-document.')
    return args


def main() -> int:
    args = parse_args()
    ok = 0
    failed = 0
    for index, source in enumerate(source_values(args)):
        if index:
            time.sleep(max(args.sleep_seconds, 0))
        if process_source(source, args):
            ok += 1
        else:
            failed += 1
    if failed:
        print(f'[DONE] {ok} succeeded, {failed} failed.', file=sys.stderr)
        return 1
    print(f'[DONE] {ok} source(s) processed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
