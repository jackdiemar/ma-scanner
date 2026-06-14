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
RUNS_DIR       = LIVE_DATA / 'runs'
CASES_BASE_DIR = REPO / 'data' / 'ai_research' / 'cases'

_PRIORITY_ORDER = {
    'INVESTIGATE': 0,
    'KEEP_HIGH_PRIORITY': 0,
    'KEEP_REVIEW': 1,              # verified PROCESS/ROFR with source URL
    'WATCH': 2,
    'DOWNGRADE_WATCH': 2,
    'SUPPRESS_FALSE_POSITIVE': 3,
}

# Secondary sort within same FP priority tier: prefer unresolved over signed deals
_SIGNAL_QUALITY_ORDER = {
    'AFFIRM': 0,
    'PROCESS': 1,
    'ROFR': 2,
    'MERGER': 3,    # already-signed — last, not a new opportunity
    'BOILERPLATE': 4,
    'SCORE_ONLY': 5,
}

# EDGAR URL pattern for company filings (ticker-based)
_EDGAR_COMPANY_URL = (
    'https://www.sec.gov/cgi-bin/browse-edgar'
    '?action=getcompany&CIK={ticker}&type={form_type}'
    '&dateb=&owner=include&count=10'
)
# EDGAR full-text search (returns JSON with filing list)
_EDGAR_SEARCH_URL = (
    'https://efts.sec.gov/LATEST/search-index'
    '?q=%22{phrase}%22&forms={form}&dateRange=custom&startdt={start}&entity={ticker}'
)

_SIGNAL_TYPE_TO_EDGAR_FORM = {
    'merger_agreement':              '8-K',
    'strategic_alternatives_affirm': '8-K',
    'strategic_alternatives':        '8-K',
    'rofn':                          '8-K',
    'rofr':                          '8-K',
    'activist_13d':                  'SC+13D',
    'activist_13g':                  'SC+13G',
    'unsolicited_proposal':          '8-K',
    'banker_retained':               '8-K',
}

_SIGNAL_TYPE_TO_TRIGGER_PHRASE = {
    'merger_agreement':              'merger agreement',
    'strategic_alternatives_affirm': 'strategic alternatives',
    'strategic_alternatives':        'strategic alternatives',
    'rofn':                          'right of first negotiation',
    'rofr':                          'right of first refusal',
    'activist_13d':                  'acquisition',
    'unsolicited_proposal':          'acquisition proposal',
    'banker_retained':               'strategic alternatives',
}

# Regex for extracting filing dates (YYYY-MM-DD) from flags text
_DATE_RE   = re.compile(r'\((\d{4}-\d{2}-\d{2})')
# Regex for recognizing SEC form type names
_FORM_RE   = re.compile(
    r'\b(8-K|DEF 14A|DEFM14A|SC TO-T|SC 13D|SC 13G|13D|13G|S-4|10-K|10-Q|DEF14A)\b'
)


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


def _parse_flags_for_evidence(flags_str: str) -> dict:
    """
    Extract filing type, date, and context from the pipe-delimited flags string.

    Examples:
      "ACTIVIST 13D: Unknown (2026-04-28 00:00:00)|Change-of-control provisions in DEF 14A"
        → {filing_type: "SC 13D", filing_date: "2026-04-28", context_hints: [...]}

      "STRATEGIC ALTERNATIVES in 8-K — board hired a banker"
        → {filing_type: "8-K", filing_date: "", context_hints: [...]}
    """
    if not flags_str:
        return {'filing_type': '', 'filing_date': '', 'context_hints': []}

    parts = [p.strip() for p in flags_str.split('|') if p.strip()]
    dates = _DATE_RE.findall(flags_str)
    forms = _FORM_RE.findall(flags_str)

    # Normalise: prefer "8-K" over "DEF 14A" as primary filing_type for M&A signals
    # because DEF 14A is almost always a secondary flag
    primary_forms = [f for f in forms if '14A' not in f and '10-' not in f]
    secondary_forms = [f for f in forms if f not in primary_forms]
    filing_type = primary_forms[0] if primary_forms else (secondary_forms[0] if secondary_forms else '')
    # Normalise "13D" → "SC 13D" for EDGAR URL construction
    if filing_type in ('13D', 'SC 13D'):
        filing_type = 'SC+13D'
    elif filing_type in ('13G', 'SC 13G'):
        filing_type = 'SC+13G'

    return {
        'filing_type':    filing_type,
        'filing_date':    dates[0] if dates else '',
        'context_hints':  parts,
    }


def _construct_edgar_url(ticker: str, signal_type: str, filing_type: str, trigger_phrase: str) -> str:
    """
    Build a best-effort EDGAR company filings URL for this ticker + signal combination.
    Used when signal_source_url is empty (e.g. scanner ran in dry-run mode).
    The returned URL points to EDGAR's company filing page — source_fetcher can fetch it.
    """
    form = filing_type or _SIGNAL_TYPE_TO_EDGAR_FORM.get(signal_type, '8-K')
    # EDGAR uses SC+13D in URLs
    if form in ('13D', 'SC 13D'):
        form = 'SC+13D'
    elif form in ('13G', 'SC 13G'):
        form = 'SC+13G'
    return _EDGAR_COMPANY_URL.format(ticker=ticker, form_type=form)


def _is_scanner_dry_run() -> bool:
    """
    Detect whether the scanner ran in dry-run mode (no live EDGAR fetches).
    Checks latest review memo header and most recent run snapshot.
    """
    if MEMO_PATH.exists():
        try:
            header = MEMO_PATH.read_text(encoding='utf-8', errors='replace')[:500]
            if 'DRY RUN' in header.upper():
                return True
        except OSError:
            pass
    # Check the most recent run snapshot
    try:
        runs = sorted(RUNS_DIR.glob('run_*.json')) if RUNS_DIR.exists() else []
        if runs:
            data = json.loads(runs[-1].read_text(encoding='utf-8'))
            if data.get('dry_run') is True:
                return True
    except Exception:
        pass
    return False


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

    # ── Extract source fields — prefer explicit scanner fields, enrich from flags ──
    signal_type   = str(alert.get('signal_type', '')).strip()
    filing_type   = str(alert.get('signal_source_form', '')).strip()
    filing_date   = str(alert.get('signal_source_date', '')).strip()
    source_url    = str(alert.get('signal_source_url', '')).strip()
    accession     = str(alert.get('signal_source_accession', '')).strip()
    source_excerpt_raw = str(alert.get('signal_source_excerpt', '')).strip()

    # Fallback: parse flags for filing type and date hints
    flags_raw = str(alert.get('flags', '')).strip()
    flags_evidence = _parse_flags_for_evidence(flags_raw)
    if not filing_type and flags_evidence['filing_type']:
        filing_type = flags_evidence['filing_type']
    if not filing_date and flags_evidence['filing_date']:
        filing_date = flags_evidence['filing_date']

    # Fallback: construct EDGAR URL when scanner didn't populate source_url
    scanner_dry_run = _is_scanner_dry_run()
    constructed_edgar_url = ''
    if not source_url and ticker:
        constructed_edgar_url = _construct_edgar_url(ticker, signal_type, filing_type, trigger_phrase)

    # False positive flags
    fp_flags: list[str] = []
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
        'signal_type':              signal_type,
        'recommended_scanner_action': str(alert.get('recommended_action', '')).strip(),
        'filing_type':              filing_type,
        'filing_date':              filing_date,
        'source_url':               source_url or constructed_edgar_url,
        'source_url_constructed':   bool(constructed_edgar_url and not source_url),
        'accession':                accession,
        'source_excerpt':           source_excerpt or source_excerpt_raw,
        'trigger_phrase':           trigger_phrase,
        'flags_context':            flags_evidence['context_hints'],
        'scanner_dry_run':          scanner_dry_run,
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

    # SA type classification — deterministic, no HTTP
    try:
        import sys as _sys
        _src = str(Path(__file__).resolve().parent.parent)
        if _src not in _sys.path:
            _sys.path.insert(0, _src)
        from sa_classifier import classify_sa_type
        sa_result = classify_sa_type(
            excerpt        = case.get('source_excerpt', '') or '',
            trigger_phrase = case.get('trigger_phrase', '') or '',
            flags          = case.get('scanner_flags', []) or [],
            has_banker     = str(case.get('banker_retained', '')).lower() == 'true',
            signal_quality = case.get('signal_quality', '') or '',
        )
        case['sa_type']              = sa_result['sa_type']
        case['sa_confidence']        = sa_result['sa_confidence']
        case['sa_reasons']           = sa_result['sa_reasons']
        case['sa_is_company_level']  = sa_result['is_company_level']
        case['sa_asset_level_flags'] = sa_result['asset_level_flags']
        case['sa_requires_deeper_read'] = sa_result['requires_deeper_read']
    except Exception as _sa_exc:
        case['sa_type']              = 'UNKNOWN'
        case['sa_confidence']        = 'LOW'
        case['sa_reasons']           = []
        case['sa_is_company_level']  = True
        case['sa_asset_level_flags'] = []
        case['sa_requires_deeper_read'] = True

    # Distress detection — fetches 30d price history via yfinance
    try:
        from sa_classifier import detect_distress
        distress = detect_distress(ticker, case.get('filing_date', '') or '')
        case['distress_driven_sa']    = distress['distress_driven_sa']
        case['distress_severity']     = distress['distress_severity']
        case['distress_note']         = distress['distress_note']
        case['price_change_30d_pct']  = distress['price_change_30d_pct']
        case['price_at_filing']       = distress['price_at_filing']
        case['price_30d_before']      = distress['price_30d_before']
    except Exception as _dist_exc:
        case['distress_driven_sa']    = False
        case['distress_severity']     = 'UNKNOWN'
        case['distress_note']         = str(_dist_exc)
        case['price_change_30d_pct']  = None
        case['price_at_filing']       = None
        case['price_30d_before']      = None

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


# ── Source field inspector ────────────────────────────────────────────────────

def inspect_source_fields(
    ticker: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    For each alert, report what raw source fields are available in each data source.
    Used by --inspect-source-fields CLI command.

    Returns list of inspection dicts — one per ticker.
    """
    # Load from JSON (authoritative)
    alerts_json = _load_alerts_from_json() if not ticker else [
        a for a in _load_alerts_from_json() if str(a.get('ticker', '')).strip() == ticker
    ]
    # Load from CSV for cross-reference
    csv_rows_by_ticker: dict[str, dict] = {}
    for row in _load_csv_log(ALERT_LOG):
        t = str(row.get('ticker', '')).strip()
        if t:
            csv_rows_by_ticker[t] = row  # last wins

    scanner_dry_run = _is_scanner_dry_run()
    alerts = alerts_json[:limit] if limit else alerts_json

    results: list[dict] = []
    for alert in alerts:
        t = str(alert.get('ticker', '')).strip()
        if not t:
            continue

        # JSON source fields
        j_url     = str(alert.get('signal_source_url', '')).strip()
        j_excerpt = str(alert.get('signal_source_excerpt', '')).strip()
        j_date    = str(alert.get('signal_source_date', '')).strip()
        j_form    = str(alert.get('signal_source_form', '')).strip()
        j_acc     = str(alert.get('signal_source_accession', '')).strip()

        # CSV source fields
        csv_row   = csv_rows_by_ticker.get(t, {})
        c_url     = str(csv_row.get('signal_source_url', '')).strip()
        c_excerpt = str(csv_row.get('signal_source_excerpt', '')).strip()
        c_date    = str(csv_row.get('signal_source_date', '')).strip()
        c_form    = str(csv_row.get('signal_source_form', '')).strip()

        # Enriched from flags
        flags_evidence = _parse_flags_for_evidence(str(alert.get('flags', '')).strip())
        signal_type    = str(alert.get('signal_type', '')).strip()
        trigger        = str(alert.get('top_8k_phrase', '')).strip()
        e_form   = flags_evidence['filing_type']
        e_date   = flags_evidence['filing_date']
        e_url    = _construct_edgar_url(t, signal_type, e_form, trigger) if not j_url else j_url

        results.append({
            'ticker':              t,
            'signal_type':         signal_type,
            'in_latest_alerts':    True,
            'in_csv':              t in csv_rows_by_ticker,
            'scanner_dry_run':     scanner_dry_run,
            # Raw latest_alerts fields
            'json_source_url':     j_url,
            'json_excerpt_len':    len(j_excerpt),
            'json_filing_date':    j_date,
            'json_filing_form':    j_form,
            'json_accession':      j_acc,
            # Raw CSV fields
            'csv_source_url':      c_url,
            'csv_excerpt_len':     len(c_excerpt),
            'csv_filing_date':     c_date,
            'csv_filing_form':     c_form,
            # After enrichment
            'enriched_filing_type': e_form or j_form or c_form,
            'enriched_filing_date': e_date or j_date or c_date,
            'enriched_source_url':  e_url,
            'source_url_is_constructed': bool(not j_url and not c_url),
        })

    return results


# ── Alert loading ─────────────────────────────────────────────────────────────

def _load_alerts_from_json() -> list[dict]:
    """Load alerts from latest_alerts.json. Returns list sorted by priority."""
    data = _load_json(ALERTS_PATH)
    if not data or not isinstance(data, dict):
        return []
    alerts = list(data.values())
    return sorted(
        alerts,
        key=lambda a: (
            _PRIORITY_ORDER.get(str(a.get('fp_classification', '')), 99),
            _SIGNAL_QUALITY_ORDER.get(str(a.get('signal_quality', '')).upper(), 99),
        ),
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
        key=lambda a: (
            _PRIORITY_ORDER.get(str(a.get('fp_classification', '')), 99),
            _SIGNAL_QUALITY_ORDER.get(str(a.get('signal_quality', '')).upper(), 99),
        ),
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
