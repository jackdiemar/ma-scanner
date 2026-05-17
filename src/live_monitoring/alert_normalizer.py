"""
alert_normalizer.py — Convert V12 scan results into standardized alert records.

Handles both old-format scans (pre-Gate-1, missing source fields) and new-format
scans with signal_source_url / signal_source_excerpt populated.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ALERT_FIELDS = [
    'alert_id', 'scan_timestamp', 'ticker', 'company_name',
    'signal_quality', 'signal_type', 'top_8k_phrase',
    'signal_source_form', 'signal_source_date',
    'signal_source_url', 'signal_source_accession',
    'signal_source_excerpt', 'negated_8k_phrases',
    'rofn_scope_hint', 'rofr_scope_hint',
    'market_cap', 'price', 'priced_in_flag',
    'recommended_action', 'false_positive_risk', 'fp_classification',
    'alert_hash', 'first_seen', 'last_seen', 'status',
    'flags', 'activist_filer', 'strategic_alternatives',
    'banker_retained', 'has_rofn', 'has_rofr',
    'conviction_tier', 'score', 'p_deal', 'trade_decision',
]


def _infer_signal_type(row: dict) -> str:
    sq = row.get('signal_quality', '') or ''
    if sq == 'AFFIRM':
        return 'strategic_alternatives_affirm'
    if sq == 'MERGER':
        return 'merger_agreement'
    if sq == 'PROCESS':
        parts = []
        if row.get('banker_retained'):
            parts.append('banker_retained')
        if row.get('has_activist_13d'):
            parts.append('activist_13d')
        if not parts:
            parts.append('process')
        return '|'.join(parts)
    if sq == 'ROFR':
        return 'rofr_rofn'
    if sq == 'BOILERPLATE':
        return 'boilerplate'
    return 'score_only'


def _alert_hash(ticker: str, signal_quality: str, source_accession: str) -> str:
    """
    Stable 16-char hex ID for deduplication.
    Changes if the accession changes (new filing) or signal_quality changes.
    Does NOT change if excerpt wording changes slightly.
    """
    raw = f"{ticker}|{signal_quality}|{source_accession}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _priced_in_flag(row: dict) -> str:
    try:
        price     = float(row.get('price', 0) or 0)
        year_low  = float(row.get('year_low', 0) or 0)
        first_px  = float(row.get('first_price', 0) or 0)
        if year_low > 0 and price / year_low > 1.55:
            return 'PARTLY_REPRICED'
        if first_px > 0 and price / first_px > 1.35:
            return 'ALREADY_REPRICED'
        if price > 0:
            return 'NOT_PRICED_IN'
    except (TypeError, ZeroDivisionError):
        pass
    return 'UNKNOWN'


def normalize_row(row: dict, scan_ts: str) -> dict:
    """Convert one V12 result dict to a standard alert record."""
    ticker    = row.get('ticker', '') or ''
    sq        = row.get('signal_quality', 'SCORE_ONLY') or 'SCORE_ONLY'
    accession = row.get('signal_source_accession', '') or ''
    ah        = _alert_hash(ticker, sq, accession)
    negated   = row.get('negated_8k_phrases', []) or []

    return {
        'alert_id':               f"{ticker}_{ah}",
        'scan_timestamp':         scan_ts,
        'ticker':                 ticker,
        'company_name':           row.get('company', '') or '',
        'signal_quality':         sq,
        'signal_type':            _infer_signal_type(row),
        'top_8k_phrase':          row.get('top_8k_phrase', '') or '',
        'signal_source_form':     row.get('signal_source_form', '') or '',
        'signal_source_date':     row.get('signal_source_date', '') or '',
        'signal_source_url':      row.get('signal_source_url', '') or '',
        'signal_source_accession': accession,
        'signal_source_excerpt':  row.get('signal_source_excerpt', '') or '',
        'negated_8k_phrases':     json.dumps(negated if isinstance(negated, list) else []),
        'rofn_scope_hint':        row.get('rofn_scope_hint', '') or '',
        'rofr_scope_hint':        row.get('rofr_scope_hint', '') or '',
        'market_cap':             row.get('mcap_M', '') or '',
        'price':                  row.get('price', '') or '',
        'priced_in_flag':         _priced_in_flag(row),
        'recommended_action':     '',   # filled by false_positive_filter
        'false_positive_risk':    '',   # filled by false_positive_filter
        'fp_classification':      '',   # filled by false_positive_filter
        'alert_hash':             ah,
        'first_seen':             '',   # filled by deduplicate()
        'last_seen':              scan_ts,
        'status':                 'NEW',  # updated by deduplicate()
        'flags':                  '|'.join(row.get('flags', []) or []),
        'activist_filer':         row.get('activist_filer', '') or '',
        'strategic_alternatives': str(bool(row.get('strategic_alternatives'))),
        'banker_retained':        str(bool(row.get('banker_retained'))),
        'has_rofn':               str(bool(row.get('has_rofn'))),
        'has_rofr':               str(bool(row.get('has_rofr'))),
        'conviction_tier':        row.get('conviction_tier', '') or '',
        'score':                  str(row.get('score', '') or ''),
        'p_deal':                 str(row.get('p_deal', '') or ''),
        'trade_decision':         row.get('trade_decision', '') or '',
    }


def normalize_scan_results(scan_results: list, scan_ts: str) -> list:
    """
    Convert V12 result list to alert records.
    Includes AFFIRM, MERGER, PROCESS, ROFR, and notable BOILERPLATE signals.
    Skips plain SCORE_ONLY names.
    """
    alerts = []
    for row in scan_results:
        sq = row.get('signal_quality', 'SCORE_ONLY') or 'SCORE_ONLY'
        if sq in ('AFFIRM', 'MERGER', 'PROCESS', 'ROFR'):
            alerts.append(normalize_row(row, scan_ts))
        elif sq == 'BOILERPLATE' and (row.get('has_activist_13d') or row.get('has_rofn')):
            # Log notable BOILERPLATE for FP taxonomy tracking even though not tradeable
            alerts.append(normalize_row(row, scan_ts))
        # SCORE_ONLY: intentionally skipped
    return alerts


def load_alert_log(log_path: Path) -> dict:
    """
    Load existing alert log CSV, return dict keyed by alert_hash.
    Returns most recent row per hash (last-wins for status/fields).
    """
    existing: dict = {}
    if not log_path.exists():
        return existing
    with open(log_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            h = row.get('alert_hash', '')
            if h:
                existing[h] = row  # last row for this hash wins
    return existing


def deduplicate(alerts: list, existing: dict, scan_ts: str) -> list:
    """
    Compare new alerts against the existing log.
    Assigns first_seen, last_seen, and status.
    Status rules:
      NEW      — hash not seen before
      UPDATED  — signal_quality changed since last seen
      WATCHLIST — previously marked WATCHLIST by analyst
      SEEN     — same hash, same quality as before
    """
    result = []
    for a in alerts:
        h = a['alert_hash']
        if h not in existing:
            a['first_seen'] = scan_ts
            a['status']     = 'NEW'
        else:
            prev            = existing[h]
            a['first_seen'] = prev.get('first_seen', scan_ts) or scan_ts
            prev_sq         = prev.get('signal_quality', '')
            if prev.get('status') == 'WATCHLIST':
                a['status'] = 'WATCHLIST'
            elif prev_sq and prev_sq != a['signal_quality']:
                a['status'] = 'UPDATED'
            else:
                a['status'] = 'SEEN'
        result.append(a)
    return result


def append_to_alert_log(alerts: list, log_path: Path) -> None:
    """Append this run's alerts to the CSV log. One row per alert per run (append-only)."""
    if not alerts:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = log_path.exists()
    with open(log_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=ALERT_FIELDS, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerows(alerts)


def write_latest_alerts(alerts: list, latest_path: Path) -> None:
    """Overwrite latest_alerts.json with current dedup state (keyed by alert_hash)."""
    state = {a['alert_hash']: a for a in alerts}
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)
