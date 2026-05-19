"""
research_case_builder.py — Build structured research case files from live scanner outputs.

Reads:
  data/live_monitoring/latest_review_memo.md
  data/live_monitoring/latest_alerts.json  (if available)
  data/live_monitoring/live_alert_log.csv

Writes per ticker:
  data/ai_research/cases/YYYY-MM-DD/{ticker}_research_case.json
  data/ai_research/cases/YYYY-MM-DD/{ticker}_research_case.md

CLI:
  python3 src/ai_research/research_case_builder.py --latest
  python3 src/ai_research/research_case_builder.py --latest --limit 5
  python3 src/ai_research/research_case_builder.py --ticker SDGR
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

LIVE_DATA      = REPO / 'data' / 'live_monitoring'
MEMO_PATH      = LIVE_DATA / 'latest_review_memo.md'
ALERTS_PATH    = LIVE_DATA / 'latest_alerts.json'
ALERT_LOG      = LIVE_DATA / 'live_alert_log.csv'
CASES_BASE_DIR = REPO / 'data' / 'ai_research' / 'cases'

_PRIORITY_ORDER = {
    'INVESTIGATE': 0,
    'KEEP_HIGH_PRIORITY': 0,
    'WATCH': 1,
    'DOWNGRADE_WATCH': 1,
    'SUPPRESS_FALSE_POSITIVE': 2,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        print(f'  [WARN] Could not parse {path.name}: {exc}', file=sys.stderr)
        return None


def _load_csv_log(path: Path) -> list[dict]:
    """Load live_alert_log.csv into a list of row dicts."""
    rows: list[dict] = []
    if not path.exists():
        return rows
    try:
        with path.open(newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(row)
    except Exception as exc:
        print(f'  [WARN] Could not read CSV log: {exc}', file=sys.stderr)
    return rows


def _parse_memo_sections(memo_text: str) -> dict[str, str]:
    """
    Parse per-ticker sections from the memo.
    Returns {ticker: raw_section_text}.
    """
    sections: dict[str, str] = {}
    # Sections begin with ### N. TICKER — Company Name
    header_re = re.compile(r'^### \d+\.\s+[^\s]+\s+([A-Z0-9]+)\s+—', re.MULTILINE)
    matches = list(header_re.finditer(memo_text))
    for idx, m in enumerate(matches):
        ticker = m.group(1).strip()
        start  = m.start()
        end    = matches[idx + 1].start() if idx + 1 < len(matches) else len(memo_text)
        sections[ticker] = memo_text[start:end].strip()
    return sections


# ── Core case builder ─────────────────────────────────────────────────────────

def _build_case_from_alert(
    alert: dict,
    memo_section: str,
    run_date: str,
    research_depth: str = 'fast_gate',
) -> dict:
    """
    Build a single research case dict from an alert + memo section.
    All fields are extracted; unknown fields default to empty/None/[].
    """
    ticker       = str(alert.get('ticker', '')).strip()
    company_name = str(alert.get('company_name', '')).strip()

    # Derive trigger_phrase: prefer top_8k_phrase, fall back to memo scan
    trigger_phrase = str(alert.get('top_8k_phrase', '')).strip()
    if not trigger_phrase and memo_section:
        tp_match = re.search(r'\*\*Trigger phrase:\*\*\s+`(.+?)`', memo_section)
        if tp_match:
            trigger_phrase = tp_match.group(1)

    # Source excerpt from memo (between **Excerpt:** and next heading/flag)
    source_excerpt = str(alert.get('signal_source_excerpt', '')).strip()
    if not source_excerpt and memo_section:
        exc_match = re.search(
            r'\*\*Excerpt:\*\*\s*\n+(.*?)(?=\n\*\*|\Z)',
            memo_section,
            re.DOTALL,
        )
        if exc_match:
            raw = exc_match.group(1).strip()
            # Strip markdown italics wrapping
            raw = re.sub(r'^_(.*)_$', r'\1', raw, flags=re.DOTALL).strip()
            source_excerpt = raw if raw != 'No excerpt available — re-run scanner with Gate 1 patches active.' else ''

    # False positive flags
    fp_flags: list[str] = []
    flags_raw = str(alert.get('flags', '')).strip()
    if flags_raw:
        fp_flags = [f.strip() for f in flags_raw.split('|') if f.strip()]

    # Known false positive flags from fp_classification
    fp_classification = str(alert.get('fp_classification', '')).strip()
    known_fp_flags: list[str] = []
    if fp_classification in ('SUPPRESS_FALSE_POSITIVE',):
        known_fp_flags = fp_flags

    # Memo section snippet (first 1200 chars)
    memo_excerpt = (memo_section[:1200].strip() + ' ...') if len(memo_section) > 1200 else memo_section.strip()

    case: dict = {
        'ticker':                   ticker,
        'company_name':             company_name,
        'run_date':                 run_date,
        'signal_quality':           str(alert.get('signal_quality', '')).strip(),
        'signal_type':              str(alert.get('signal_type', '')).strip(),
        'recommended_scanner_action': str(alert.get('recommended_action', '')).strip(),
        'filing_type':              str(alert.get('signal_source_form', '')).strip(),
        'filing_date':              str(alert.get('signal_source_date', '')).strip(),
        'source_url':               str(alert.get('signal_source_url', '')).strip(),
        'source_excerpt':           source_excerpt,
        'trigger_phrase':           trigger_phrase,
        'market_cap':               alert.get('market_cap'),
        'price':                    alert.get('price'),
        'priced_in_flag':           str(alert.get('priced_in_flag', '')).strip(),
        'first_seen':               str(alert.get('first_seen', '')).strip(),
        'last_seen':                str(alert.get('last_seen', '')).strip(),
        'fp_classification':        fp_classification,
        'false_positive_risk':      str(alert.get('false_positive_risk', '')).strip(),
        'known_false_positive_flags': known_fp_flags,
        'scanner_flags':            fp_flags,
        'conviction_tier':          str(alert.get('conviction_tier', '')).strip(),
        'score':                    alert.get('score'),
        'p_deal':                   alert.get('p_deal'),
        'strategic_alternatives':   alert.get('strategic_alternatives'),
        'banker_retained':          alert.get('banker_retained'),
        'has_rofn':                 alert.get('has_rofn'),
        'has_rofr':                 alert.get('has_rofr'),
        'memo_section_excerpt':     memo_excerpt,
        'research_depth':           research_depth,
        'initial_classification':   'PENDING',
        'ai_decision':              None,
        'ai_run_at':                None,
    }

    # Evidence quality — computed from available metadata (no HTTP fetch at build time)
    try:
        from ai_research.quote_extractor import compute_evidence_quality, extract_quotes
        quotes = extract_quotes(case, filing_text=None)
        case['evidence_quality'] = compute_evidence_quality(case, filing_text=None, quotes=quotes)
    except Exception:
        case['evidence_quality'] = {}

    return case


_REQUIRED_CASE_FIELDS = frozenset({
    'ticker',
    'company_name',
    'run_date',
    'signal_quality',
    'signal_type',
    'recommended_scanner_action',
    'filing_type',
    'filing_date',
    'source_url',
    'source_excerpt',
    'trigger_phrase',
    'memo_section_excerpt',
    'research_depth',
    'initial_classification',
    'ai_decision',
    'ai_run_at',
})


def validate_case_schema(case: dict) -> list[str]:
    """Return schema validation errors for a research case dict."""
    errors: list[str] = []
    missing = sorted(_REQUIRED_CASE_FIELDS - set(case.keys()))
    if missing:
        errors.append(f'Missing fields: {", ".join(missing)}')
    if not str(case.get('ticker', '')).strip():
        errors.append('ticker is required')
    if not isinstance(case.get('scanner_flags', []), list):
        errors.append('scanner_flags must be a list')
    if not isinstance(case.get('known_false_positive_flags', []), list):
        errors.append('known_false_positive_flags must be a list')
    return errors


def _write_case_files(case: dict, cases_dir: Path) -> tuple[Path, Path]:
    """Write JSON and Markdown case files. Returns (json_path, md_path)."""
    cases_dir.mkdir(parents=True, exist_ok=True)
    ticker = case['ticker']
    json_path = cases_dir / f'{ticker}_research_case.json'
    md_path   = cases_dir / f'{ticker}_research_case.md'

    # JSON
    json_path.write_text(json.dumps(case, indent=2, default=str), encoding='utf-8')

    # Markdown
    lines = [
        f'# Research Case: {ticker} — {case["company_name"]}',
        '',
        f'**Run date:** {case["run_date"]}  ',
        f'**Signal quality:** {case["signal_quality"]}  ',
        f'**Signal type:** {case["signal_type"]}  ',
        f'**Scanner action:** {case["recommended_scanner_action"]}  ',
        f'**Conviction tier:** {case["conviction_tier"]}  ',
        f'**Score:** {case["score"]}  ',
        f'**P(deal):** {case["p_deal"]}  ',
        '',
        '## Market Data',
        '',
        f'- Market cap: {case["market_cap"]}',
        f'- Price: {case["price"]}',
        f'- Priced-in flag: {case["priced_in_flag"]}',
        '',
        '## Signal Detail',
        '',
        f'- Filing type: {case["filing_type"] or "—"}',
        f'- Filing date: {case["filing_date"] or "—"}',
        f'- Trigger phrase: `{case["trigger_phrase"] or "—"}`',
        f'- Source URL: {case["source_url"] or "—"}',
        '',
        '## Source Excerpt',
        '',
        f'{case["source_excerpt"] or "_No excerpt available._"}',
        '',
        '## Scanner Flags',
        '',
    ]
    if case['scanner_flags']:
        for flag in case['scanner_flags']:
            lines.append(f'- {flag}')
    else:
        lines.append('_None._')

    lines += [
        '',
        '## False Positive Assessment',
        '',
        f'- Risk level: {case["false_positive_risk"]}',
        f'- FP classification: {case["fp_classification"]}',
    ]
    if case['known_false_positive_flags']:
        lines.append('- Known FP flags:')
        for f in case['known_false_positive_flags']:
            lines.append(f'  - {f}')

    lines += [
        '',
        '## Dates',
        '',
        f'- First seen: {case["first_seen"]}',
        f'- Last seen: {case["last_seen"]}',
        '',
        '## Memo Section',
        '',
        f'{case["memo_section_excerpt"]}',
        '',
        '## AI Classification',
        '',
        f'**Status:** {case["initial_classification"]}',
        '',
        '_AI gate has not run yet on this case._',
    ]

    md_path.write_text('\n'.join(lines), encoding='utf-8')
    return json_path, md_path


# ── Alert loading ─────────────────────────────────────────────────────────────

def _load_alerts_from_json() -> list[dict]:
    """Load alerts from latest_alerts.json. Returns list sorted by priority."""
    data = _load_json(ALERTS_PATH)
    if not data or not isinstance(data, dict):
        return []
    alerts = list(data.values())
    return sorted(
        alerts,
        key=lambda a: _PRIORITY_ORDER.get(str(a.get('fp_classification', '')), 99),
    )


def _load_alerts_from_csv(ticker: str | None = None) -> list[dict]:
    """Load most recent entry per ticker from live_alert_log.csv."""
    rows = _load_csv_log(ALERT_LOG)
    # Keep the most recent row per ticker
    by_ticker: dict[str, dict] = {}
    for row in rows:
        t = str(row.get('ticker', '')).strip()
        if not t:
            continue
        by_ticker[t] = row  # last wins (CSV is append-only, newest rows last)
    if ticker:
        return [by_ticker[ticker]] if ticker in by_ticker else []
    return sorted(
        by_ticker.values(),
        key=lambda a: _PRIORITY_ORDER.get(str(a.get('fp_classification', '')), 99),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def build_cases(
    ticker: str | None = None,
    limit: int | None = None,
    run_date: str | None = None,
    dry_run: bool = False,
    research_depth: str = 'fast_gate',
    verbose: bool = True,
) -> list[dict]:
    """
    Build research cases from latest scanner outputs.

    Args:
        ticker:   If set, build only this ticker.
        limit:    Max number of cases to build (prioritised by scanner action).
        run_date: YYYY-MM-DD date for case directory. Defaults to today UTC.
        dry_run:  If True, print what would happen but do not write files.
        research_depth: Research depth preset to include in each case.
        verbose:  If False, suppress per-case logging.

    Returns:
        List of case dicts (regardless of dry_run).
    """
    run_date = run_date or _today_utc()
    cases_dir = CASES_BASE_DIR / run_date

    # Load memo text
    memo_text = MEMO_PATH.read_text(encoding='utf-8') if MEMO_PATH.exists() else ''
    memo_sections = _parse_memo_sections(memo_text)

    # Load alerts: prefer latest_alerts.json (richer, deduped) then fall back to CSV
    if ticker:
        # For single-ticker: try JSON first, then CSV
        alerts_json = _load_alerts_from_json()
        alerts = [a for a in alerts_json if str(a.get('ticker', '')).strip() == ticker]
        if not alerts:
            alerts = _load_alerts_from_csv(ticker=ticker)
    else:
        alerts = _load_alerts_from_json()
        if not alerts:
            print('  [INFO] latest_alerts.json empty or missing; falling back to CSV log.', file=sys.stderr)
            alerts = _load_alerts_from_csv()

    if not alerts:
        if verbose:
            print(f'  [WARN] No alerts found{" for " + ticker if ticker else ""}.', file=sys.stderr)
        return []

    if limit:
        alerts = alerts[:limit]

    cases: list[dict] = []
    for alert in alerts:
        t = str(alert.get('ticker', '')).strip()
        if not t:
            continue
        memo_section = memo_sections.get(t, '')
        case = _build_case_from_alert(alert, memo_section, run_date, research_depth=research_depth)
        cases.append(case)

        if dry_run:
            if verbose:
                print(f'  [DRY-RUN] Would write case for {t} to {cases_dir / (t + "_research_case.json")}')
        else:
            json_path, md_path = _write_case_files(case, cases_dir)
            if verbose:
                print(f'  [WROTE] {json_path.relative_to(REPO)}')

    return cases


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description='Build AI research cases from latest scanner outputs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--latest', action='store_true', help='Build cases from latest scanner outputs')
    mode.add_argument('--ticker', metavar='TICKER', help='Build case for a single ticker')
    p.add_argument('--limit',   type=int, default=None, help='Max number of cases to build')
    p.add_argument('--depth',   default='fast_gate', help='Research depth label to write into cases')
    p.add_argument('--dry-run', action='store_true',    help='Preview without writing files')
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    ticker = args.ticker.upper() if args.ticker else None

    print('Research Case Builder')
    print('---------------------')
    print(f'Mode        : {"single ticker: " + ticker if ticker else "latest"}')
    print(f'Limit       : {args.limit or "none"}')
    print(f'Dry-run     : {args.dry_run}')
    print(f'Memo        : {MEMO_PATH} ({"exists" if MEMO_PATH.exists() else "MISSING"})')
    print(f'Alerts JSON : {ALERTS_PATH} ({"exists" if ALERTS_PATH.exists() else "MISSING"})')
    print(f'Alert CSV   : {ALERT_LOG} ({"exists" if ALERT_LOG.exists() else "MISSING"})')
    print()

    cases = build_cases(
        ticker   = ticker,
        limit    = args.limit,
        dry_run  = args.dry_run,
        research_depth = args.depth,
    )
    print()
    print(f'Cases built: {len(cases)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
