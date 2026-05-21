"""
suppression_registry.py — Track and suppress repeated already-announced / false-positive
discard cases so the AI email does not repeat the same noise every run.

Runtime file: data/ai_research/suppression_registry.json

Cases are suppressed when:
  - classification = ALREADY_ANNOUNCED_DEAL and action = DISCARD
  - classification = FALSE_POSITIVE and action = DISCARD
  - strategy_bucket contains already-announced / boilerplate language
  - any DISCARD with ALREADY_ANNOUNCED fp_archetype

Cases are unsuppressed when:
  - new source URL
  - new filing date
  - new signal type
  - action changes from DISCARD to WATCH/ESCALATE/NEEDS_HUMAN_REVIEW
  - force_unsuppress flag set
  - manual clear via --clear-suppression TICKER
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

if str(_SRCDIR) not in sys.path:
    sys.path.insert(0, str(_SRCDIR))

from ai_research.change_detector import (
    compute_evidence_fingerprint as _compute_evidence_fingerprint,
    compute_source_fingerprint   as _compute_source_fingerprint,
)

REGISTRY_PATH = REPO / 'data' / 'ai_research' / 'suppression_registry.json'

_SUPPRESS_CLASSIFICATIONS = frozenset({
    'ALREADY_ANNOUNCED_DEAL',
    'FALSE_POSITIVE',
    'GENERIC_PARTNERSHIP_LANGUAGE',
})

_SUPPRESS_BUCKET_KEYWORDS = (
    'already-announced',
    'post-announcement',
    'boilerplate',
    'merger-announcement',
    'signed-merger',
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _should_suppress(decision: dict, case: dict) -> tuple[bool, str]:
    """Return (should_suppress, reason). Only DISCARD actions enter suppression."""
    action = decision.get('research_action', '')
    if action != 'DISCARD':
        return False, ''

    cls    = decision.get('classification', '')
    bucket = (decision.get('strategy_bucket', '') or '').lower()

    if cls in _SUPPRESS_CLASSIFICATIONS:
        return True, f'classification={cls} action=DISCARD'

    for kw in _SUPPRESS_BUCKET_KEYWORDS:
        if kw in bucket:
            return True, f'strategy_bucket contains {kw}'

    fp_archetypes = decision.get('matched_false_positive_archetypes', []) or []
    if any('ALREADY_ANNOUNCED' in str(fp).upper() for fp in fp_archetypes):
        return True, 'fp_archetype=ALREADY_ANNOUNCED action=DISCARD'

    # All DISCARD cases get suppressed after first run
    return True, 'action=DISCARD'


def load_registry() -> dict[str, Any]:
    """Load suppression registry. Returns empty dict if missing."""
    if not REGISTRY_PATH.exists():
        return {}
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_registry(registry: dict[str, Any]) -> None:
    """Save suppression registry to disk."""
    try:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(
            json.dumps(registry, indent=2, default=str),
            encoding='utf-8',
        )
    except OSError as exc:
        print(f'  [SUPPRESS] Could not save registry: {exc}', file=sys.stderr)


def check_suppressed(
    ticker: str,
    case: dict,
    registry: dict[str, Any],
) -> tuple[bool, str]:
    """
    Return (is_suppressed, reason).
    Checks all unsuppression conditions automatically.
    """
    record = registry.get(ticker)
    if record is None:
        return False, 'not_in_registry'

    if record.get('force_unsuppress'):
        return False, 'force_unsuppress_flag_set'

    new_efp = _compute_evidence_fingerprint(case)
    stored_efp = record.get('evidence_fingerprint', '')
    if new_efp != stored_efp:
        return False, 'evidence_fingerprint_changed'

    new_sfp = _compute_source_fingerprint(case)
    stored_sfp = record.get('source_fingerprint', '')
    if new_sfp != stored_sfp:
        return False, 'source_fingerprint_changed'

    new_signal = str(case.get('signal_type', '')).strip()
    stored_signal = str(record.get('signal_type', '')).strip()
    if new_signal and new_signal != stored_signal:
        return False, f'signal_type_changed:{stored_signal}->{new_signal}'

    new_date = str(case.get('filing_date', '')).strip()
    stored_date = str(record.get('filing_date', '')).strip()
    if new_date and new_date != stored_date:
        return False, f'filing_date_changed:{stored_date}->{new_date}'

    return True, record.get('suppression_reason', 'suppressed')


def update_registry(
    ticker: str,
    decision: dict,
    case: dict,
    registry: dict[str, Any],
) -> None:
    """
    Update registry with result of a gate decision. Modifies registry in-place.
    Caller must call save_registry() when done.
    """
    should, reason = _should_suppress(decision, case)

    if not should:
        # If action improved from DISCARD, remove from registry
        if ticker in registry:
            old_action = registry[ticker].get('action', '')
            new_action = decision.get('research_action', '')
            if old_action == 'DISCARD' and new_action != 'DISCARD':
                del registry[ticker]
                print(f'  [SUPPRESS] Unsuppressed {ticker}: action {old_action}→{new_action}')
        return

    efp = _compute_evidence_fingerprint(case)
    sfp = _compute_source_fingerprint(case)
    now = _utc_now()
    existing = registry.get(ticker, {})
    times_seen = existing.get('times_seen', 0) + 1

    registry[ticker] = {
        'ticker':               ticker,
        'company_name':         decision.get('company_name', '') or case.get('company_name', ''),
        'first_suppressed_at':  existing.get('first_suppressed_at', now),
        'last_seen_at':         now,
        'suppression_reason':   reason,
        'classification':       decision.get('classification', ''),
        'action':               decision.get('research_action', ''),
        'evidence_fingerprint': efp,
        'source_fingerprint':   sfp,
        'source_url':           str(case.get('source_url', '')),
        'filing_date':          str(case.get('filing_date', '')),
        'signal_type':          str(case.get('signal_type', '')),
        'times_seen':           times_seen,
        'force_unsuppress':     False,
        'unsuppress_if': [
            'new source URL',
            'new filing date',
            'new signal type',
            'action changes from DISCARD',
            'force_unsuppress flag set',
        ],
        'latest_decision_path': '',
    }

    if times_seen == 1:
        print(f'  [SUPPRESS] Added {ticker}: {reason}')
    else:
        print(f'  [SUPPRESS] Updated {ticker}: seen {times_seen}x ({reason})')


def force_unsuppress(ticker: str, registry: dict[str, Any]) -> bool:
    """Set force_unsuppress flag. Returns True if ticker was in registry."""
    if ticker in registry:
        registry[ticker]['force_unsuppress'] = True
        return True
    return False


def clear_suppression(ticker: str, registry: dict[str, Any]) -> bool:
    """Remove ticker entirely from registry. Returns True if removed."""
    if ticker in registry:
        del registry[ticker]
        return True
    return False


def get_suppression_summary(registry: dict[str, Any]) -> dict:
    """Return summary stats for --suppression-status output."""
    total = len(registry)
    by_reason: dict[str, int] = {}
    by_classification: dict[str, int] = {}

    for record in registry.values():
        reason = record.get('suppression_reason', 'unknown')
        cls    = record.get('classification', 'unknown')
        # Normalize reason to short key
        if 'ALREADY_ANNOUNCED' in reason.upper():
            short = 'already_announced'
        elif 'boilerplate' in reason.lower():
            short = 'boilerplate'
        elif 'FALSE_POSITIVE' in reason.upper():
            short = 'false_positive'
        else:
            short = 'discard'
        by_reason[short] = by_reason.get(short, 0) + 1
        by_classification[cls] = by_classification.get(cls, 0) + 1

    top_repeated = sorted(
        registry.values(),
        key=lambda r: r.get('times_seen', 0),
        reverse=True,
    )[:10]

    last_suppressed = max(
        (r.get('last_seen_at', '') for r in registry.values()),
        default='',
    ) if registry else ''

    return {
        'total_suppressed':     total,
        'by_reason':            by_reason,
        'by_classification':    by_classification,
        'top_repeated':         top_repeated,
        'last_suppressed_date': last_suppressed,
    }
