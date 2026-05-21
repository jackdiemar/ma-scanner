"""
change_detector.py — Compute evidence fingerprints and classify case change status.

For each case, determines whether it is:
  NEW_CASE             — never seen in suppression registry
  CHANGED_EVIDENCE     — evidence fingerprint changed vs. registry
  CHANGED_SOURCE       — source URL / filing date changed
  CHANGED_DECISION     — force_unsuppress set or action improved
  UNCHANGED_SUPPRESSED — same evidence as last run, in suppression registry
  UNCHANGED_ACTIVE     — same or not in registry, in active watchlist
  STALE                — in registry but not seen recently
"""
from __future__ import annotations

import hashlib
from typing import Any

NEW_CASE              = 'NEW_CASE'
CHANGED_EVIDENCE      = 'CHANGED_EVIDENCE'
CHANGED_SOURCE        = 'CHANGED_SOURCE'
CHANGED_DECISION      = 'CHANGED_DECISION'
UNCHANGED_SUPPRESSED  = 'UNCHANGED_SUPPRESSED'
UNCHANGED_ACTIVE      = 'UNCHANGED_ACTIVE'
STALE                 = 'STALE'


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:20]


def compute_evidence_fingerprint(case: dict) -> str:
    key = '|'.join([
        str(case.get('ticker', '')),
        str(case.get('signal_type', '')),
        str(case.get('source_url', '')),
        str(case.get('accession', '')),
        str(case.get('filing_date', '')),
        str(case.get('filing_type', '')),
        str(case.get('source_excerpt', ''))[:300],
    ])
    return _hash(key)


def compute_source_fingerprint(case: dict) -> str:
    key = '|'.join([
        str(case.get('source_url', '')),
        str(case.get('accession', '')),
        str(case.get('filing_date', '')),
    ])
    return _hash(key)


def compute_decision_fingerprint(decision: dict) -> str:
    key = '|'.join([
        str(decision.get('ticker', '')),
        str(decision.get('classification', '')),
        str(decision.get('research_action', '')),
        str(int(decision.get('confidence', 0.0) * 100)),
        str(decision.get('strategy_bucket', '')),
    ])
    return _hash(key)


def compute_price_context_fingerprint(case: dict) -> str | None:
    price = case.get('price') or case.get('current_price')
    mkt   = case.get('market_cap') or case.get('mktcap')
    if not price and not mkt:
        return None
    key = '|'.join([str(price or ''), str(mkt or ''), str(case.get('priced_in_flag', ''))])
    return _hash(key)


def classify_change(
    case: dict,
    registry: dict[str, Any],
    watchlist: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """
    Classify a case against the suppression registry.
    Returns (status_constant, detail_string).
    """
    ticker = str(case.get('ticker', '')).upper()
    efp    = compute_evidence_fingerprint(case)
    sfp    = compute_source_fingerprint(case)

    record = registry.get(ticker)

    if record is None:
        if watchlist and ticker in watchlist:
            wl_status = watchlist[ticker].get('status', '')
            if wl_status in ('active_watch', 'escalated', 'needs_review'):
                return UNCHANGED_ACTIVE, f'watchlist={wl_status}'
        return NEW_CASE, 'not_in_registry'

    if record.get('force_unsuppress'):
        return CHANGED_DECISION, 'force_unsuppress_set'

    stored_sfp = record.get('source_fingerprint', '')
    if sfp != stored_sfp:
        return CHANGED_SOURCE, f'sfp:{stored_sfp[:8]}->{sfp[:8]}'

    stored_efp = record.get('evidence_fingerprint', '')
    if efp != stored_efp:
        return CHANGED_EVIDENCE, f'efp:{stored_efp[:8]}->{efp[:8]}'

    new_signal  = str(case.get('signal_type', '')).strip()
    stored_signal = str(record.get('signal_type', '')).strip()
    if new_signal and new_signal != stored_signal:
        return CHANGED_EVIDENCE, f'signal:{stored_signal}->{new_signal}'

    new_date    = str(case.get('filing_date', '')).strip()
    stored_date = str(record.get('filing_date', '')).strip()
    if new_date and new_date != stored_date:
        return CHANGED_SOURCE, f'date:{stored_date}->{new_date}'

    return UNCHANGED_SUPPRESSED, f'reason={record.get("suppression_reason", "")}'
