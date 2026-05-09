"""
sequence_detector.py — Process Sequence Detector.

Reads transition events from state_history (built by process_history.py) and
identifies named multi-event patterns that compound the intelligence value of
individual signals.

A single ACTIVIST_INTRODUCED event tells you someone filed a 13D.
An ACTIVIST_THEN_SA sequence tells you an activist arrived, then the board
opened a formal alternatives process — a structurally different situation.

Sequences are re-derived from state_history each scan.
No new storage file needed: state_history.json already holds all events.

Output fields added to scan results:
  - detected_sequences   list of all matched sequence dicts (may be empty)
  - sequence_type        type of highest-priority matched sequence (or None)
  - sequence_label       human-readable label for primary sequence (or None)
  - sequence_window_days days spanned by primary sequence (or None)
  - compound_signal_quality  compound quality label for primary sequence (or None)

MVP: label only. No P(deal) adjustments — requires validated outcome data first.
Rule-based only. No ML, no embeddings.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

# ── Event type imports ─────────────────────────────────────────────────────────
# Avoid string literals for event types — import from process_history.
try:
    from process_history import (
        EV_FIRST_DETECTED,
        EV_STATE_UPGRADED,
        EV_STATE_DOWNGRADED,
        EV_MERGER_SIGNED,
        EV_SA_INTRODUCED,
        EV_ADVISOR_INTRODUCED,
        EV_ACTIVIST_INTRODUCED,
        EV_ACTIVIST_INTENT_ESCALATED,
        EV_INTENT_INTENSITY_UPGRADED,
        EV_ROFR_INTRODUCED,
        EV_SIGNAL_STALE,
        EV_ACTIVIST_GONE,
        EV_PROCESS_WEAKENED,
        EV_SCORE_JUMP,
        EV_SCORE_DROP,
    )
except ImportError:
    # Fallback literals if running standalone
    EV_FIRST_DETECTED            = 'FIRST_DETECTED'
    EV_STATE_UPGRADED            = 'STATE_UPGRADED'
    EV_STATE_DOWNGRADED          = 'STATE_DOWNGRADED'
    EV_MERGER_SIGNED             = 'MERGER_SIGNED'
    EV_SA_INTRODUCED             = 'SA_INTRODUCED'
    EV_ADVISOR_INTRODUCED        = 'ADVISOR_INTRODUCED'
    EV_ACTIVIST_INTRODUCED       = 'ACTIVIST_INTRODUCED'
    EV_ACTIVIST_INTENT_ESCALATED = 'ACTIVIST_INTENT_ESCALATED'
    EV_INTENT_INTENSITY_UPGRADED = 'INTENT_INTENSITY_UPGRADED'
    EV_ROFR_INTRODUCED           = 'ROFR_INTRODUCED'
    EV_SIGNAL_STALE              = 'SIGNAL_STALE'
    EV_ACTIVIST_GONE             = 'ACTIVIST_GONE'
    EV_PROCESS_WEAKENED          = 'PROCESS_WEAKENED'
    EV_SCORE_JUMP                = 'SCORE_JUMP'
    EV_SCORE_DROP                = 'SCORE_DROP'


# ── Compound signal quality labels (ordered: strongest → weakest) ──────────────

CQ_MERGER_PATHWAY        = 'MERGER_PATHWAY'      # converging on signed deal
CQ_STRONG_PROCESS        = 'STRONG_PROCESS'       # multi-signal live process
CQ_ESCALATING_PROCESS    = 'ESCALATING_PROCESS'   # sequential escalation
CQ_PROCESS_WITH_RIGHTS   = 'PROCESS_WITH_RIGHTS'  # ROFR/ROFN context
CQ_ACTIVIST_PRESSURE     = 'ACTIVIST_PRESSURE'    # activist-only compound
CQ_STALENESS_RESET       = 'STALENESS_RESET'      # revived after silence
CQ_PROCESS_COLLAPSE      = 'PROCESS_COLLAPSE'     # deteriorating situation

# Priority order for selecting the primary sequence to surface
CQ_PRIORITY = [
    CQ_MERGER_PATHWAY,
    CQ_STRONG_PROCESS,
    CQ_ESCALATING_PROCESS,
    CQ_PROCESS_WITH_RIGHTS,
    CQ_ACTIVIST_PRESSURE,
    CQ_STALENESS_RESET,
    CQ_PROCESS_COLLAPSE,
]


# ── Escalation event set (used in RAPID_ESCALATION) ──────────────────────────

ESCALATION_EVENTS = {
    EV_SA_INTRODUCED,
    EV_ADVISOR_INTRODUCED,
    EV_ACTIVIST_INTRODUCED,
    EV_ACTIVIST_INTENT_ESCALATED,
    EV_INTENT_INTENSITY_UPGRADED,
    EV_STATE_UPGRADED,
    EV_ROFR_INTRODUCED,
    EV_MERGER_SIGNED,
}


# ── Timestamp helpers ─────────────────────────────────────────────────────────

def _parse_ts(ts_str: str) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except Exception:
        return None


def _window_days(dt_a: datetime, dt_b: datetime) -> int:
    return abs((dt_b - dt_a).days)


def _fmt_ts(dt: datetime) -> str:
    return dt.isoformat()


# ── Sequence dict constructor ─────────────────────────────────────────────────

def _make_sequence(
    sequence_type: str,
    sequence_label: str,
    compound_signal_quality: str,
    anchor_event: dict,
    completing_event: dict,
    window_days: int,
    supporting_events: Optional[list] = None,
) -> dict:
    """Construct a standardized detected-sequence dict."""
    return {
        'sequence_type':          sequence_type,
        'sequence_label':         sequence_label,
        'compound_signal_quality': compound_signal_quality,
        'anchor_event':           anchor_event,
        'completing_event':       completing_event,
        'sequence_window_days':   window_days,
        'supporting_events':      supporting_events or [],
        'detected_ts':            completing_event.get('ts', ''),
    }


# ── Pattern 1: ESCALATING_ACTIVIST ───────────────────────────────────────────
# Lower-intent activist (BOARD_CHANGE / CAPITAL_ALLOCATION / GOVERNANCE_ONLY)
# → ACTIVIST_INTENT_ESCALATED within 120d
# Interpretation: originally governance-play, now explicitly sale-oriented.

def _detect_escalating_activist(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001 — reserved for future snapshot checks
) -> list[dict]:
    LOW_INTENT = {'BOARD_CHANGE', 'CAPITAL_ALLOCATION', 'GOVERNANCE_ONLY',
                  'GENERIC_SHAREHOLDER_PRESSURE', 'PASSIVE_ACCUMULATION'}
    sequences = []
    anchor_candidates = [
        ev for ev in events
        if ev['event_type'] == EV_ACTIVIST_INTRODUCED
        and (ev.get('delta', {}).get('intent') in LOW_INTENT
             or ev.get('delta', {}).get('intent') is None)
    ]
    for anchor in anchor_candidates:
        anchor_dt = _parse_ts(anchor['ts'])
        if not anchor_dt:
            continue
        window_end = anchor_dt + timedelta(days=120)
        completers = [
            ev for ev in events
            if ev['event_type'] == EV_ACTIVIST_INTENT_ESCALATED
            and _parse_ts(ev['ts']) is not None
            and anchor_dt < _parse_ts(ev['ts']) <= window_end
        ]
        for completer in completers:
            sequences.append(_make_sequence(
                'ESCALATING_ACTIVIST',
                'Activist intent escalated: governance → sale pressure',
                CQ_ESCALATING_PROCESS,
                anchor, completer,
                _window_days(anchor_dt, _parse_ts(completer['ts'])),
            ))
    return sequences


# ── Pattern 2: ADVISOR_THEN_SA ───────────────────────────────────────────────
# ADVISOR_INTRODUCED → SA_INTRODUCED within 60d
# Interpretation: advisor hired first, board then disclosed SA process.
# Sequence matters — advisor retention often precedes formal disclosure.

def _detect_advisor_then_sa(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    anchors = [ev for ev in events if ev['event_type'] == EV_ADVISOR_INTRODUCED]
    for anchor in anchors:
        anchor_dt = _parse_ts(anchor['ts'])
        if not anchor_dt:
            continue
        window_end = anchor_dt + timedelta(days=60)
        completers = [
            ev for ev in events
            if ev['event_type'] == EV_SA_INTRODUCED
            and _parse_ts(ev['ts']) is not None
            and anchor_dt < _parse_ts(ev['ts']) <= window_end
        ]
        for completer in completers:
            sequences.append(_make_sequence(
                'ADVISOR_THEN_SA',
                'Advisor retained → board opens strategic alternatives',
                CQ_STRONG_PROCESS,
                anchor, completer,
                _window_days(anchor_dt, _parse_ts(completer['ts'])),
            ))
    return sequences


# ── Pattern 3: ACTIVIST_THEN_SA ──────────────────────────────────────────────
# ACTIVIST_INTRODUCED → SA_INTRODUCED within 90d
# Interpretation: activist pressure triggered board-level SA disclosure.

def _detect_activist_then_sa(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    anchors = [ev for ev in events if ev['event_type'] == EV_ACTIVIST_INTRODUCED]
    for anchor in anchors:
        anchor_dt = _parse_ts(anchor['ts'])
        if not anchor_dt:
            continue
        window_end = anchor_dt + timedelta(days=90)
        completers = [
            ev for ev in events
            if ev['event_type'] == EV_SA_INTRODUCED
            and _parse_ts(ev['ts']) is not None
            and anchor_dt < _parse_ts(ev['ts']) <= window_end
        ]
        for completer in completers:
            sequences.append(_make_sequence(
                'ACTIVIST_THEN_SA',
                'Activist filed → board opens strategic alternatives',
                CQ_ESCALATING_PROCESS,
                anchor, completer,
                _window_days(anchor_dt, _parse_ts(completer['ts'])),
            ))
    return sequences


# ── Pattern 4: SA_THEN_ACTIVIST ──────────────────────────────────────────────
# SA_INTRODUCED → ACTIVIST_INTRODUCED within 90d
# Interpretation: board opened SA process, activist followed with 13D.
# Suggests external validation of board's stated intent — or pressure to execute faster.

def _detect_sa_then_activist(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    anchors = [ev for ev in events if ev['event_type'] == EV_SA_INTRODUCED]
    for anchor in anchors:
        anchor_dt = _parse_ts(anchor['ts'])
        if not anchor_dt:
            continue
        window_end = anchor_dt + timedelta(days=90)
        completers = [
            ev for ev in events
            if ev['event_type'] == EV_ACTIVIST_INTRODUCED
            and _parse_ts(ev['ts']) is not None
            and anchor_dt < _parse_ts(ev['ts']) <= window_end
        ]
        for completer in completers:
            sequences.append(_make_sequence(
                'SA_THEN_ACTIVIST',
                'Board opens alternatives → activist files 13D',
                CQ_STRONG_PROCESS,
                anchor, completer,
                _window_days(anchor_dt, _parse_ts(completer['ts'])),
            ))
    return sequences


# ── Pattern 5: ROFR_THEN_ACTIVIST ────────────────────────────────────────────
# ROFR_INTRODUCED → ACTIVIST_INTRODUCED within 120d
# Interpretation: existing ROFR/ROFN, now activist is pushing.
# May indicate ROFR party is blocking a deal and activist wants to force resolution.

def _detect_rofr_then_activist(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    anchors = [ev for ev in events if ev['event_type'] == EV_ROFR_INTRODUCED]
    for anchor in anchors:
        anchor_dt = _parse_ts(anchor['ts'])
        if not anchor_dt:
            continue
        window_end = anchor_dt + timedelta(days=120)
        completers = [
            ev for ev in events
            if ev['event_type'] == EV_ACTIVIST_INTRODUCED
            and _parse_ts(ev['ts']) is not None
            and anchor_dt < _parse_ts(ev['ts']) <= window_end
        ]
        for completer in completers:
            sequences.append(_make_sequence(
                'ROFR_THEN_ACTIVIST',
                'ROFR/ROFN rights held → activist files 13D',
                CQ_PROCESS_WITH_RIGHTS,
                anchor, completer,
                _window_days(anchor_dt, _parse_ts(completer['ts'])),
            ))
    return sequences


# ── Pattern 6: ACTIVIST_THEN_ROFR ────────────────────────────────────────────
# ACTIVIST_INTRODUCED → ROFR_INTRODUCED within 120d
# Interpretation: activist pressure, then transaction rights emerged.
# ROFR/ROFN appearing after activist = partner may be entering or clarifying position.

def _detect_activist_then_rofr(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    anchors = [ev for ev in events if ev['event_type'] == EV_ACTIVIST_INTRODUCED]
    for anchor in anchors:
        anchor_dt = _parse_ts(anchor['ts'])
        if not anchor_dt:
            continue
        window_end = anchor_dt + timedelta(days=120)
        completers = [
            ev for ev in events
            if ev['event_type'] == EV_ROFR_INTRODUCED
            and _parse_ts(ev['ts']) is not None
            and anchor_dt < _parse_ts(ev['ts']) <= window_end
        ]
        for completer in completers:
            sequences.append(_make_sequence(
                'ACTIVIST_THEN_ROFR',
                'Activist files 13D → acquisition rights clause surfaces',
                CQ_PROCESS_WITH_RIGHTS,
                anchor, completer,
                _window_days(anchor_dt, _parse_ts(completer['ts'])),
            ))
    return sequences


# ── Pattern 7: STALENESS_RESET ───────────────────────────────────────────────
# SIGNAL_STALE → new process signal (SA / advisor / activist / state upgrade)
# within 180d
# Interpretation: situation went quiet, then re-activated. Second wave often more serious.

_RESET_EVENT_TYPES = {
    EV_SA_INTRODUCED,
    EV_ADVISOR_INTRODUCED,
    EV_ACTIVIST_INTRODUCED,
    EV_STATE_UPGRADED,
    EV_ROFR_INTRODUCED,
}

def _detect_staleness_reset(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    anchors = [ev for ev in events if ev['event_type'] == EV_SIGNAL_STALE]
    for anchor in anchors:
        anchor_dt = _parse_ts(anchor['ts'])
        if not anchor_dt:
            continue
        window_end = anchor_dt + timedelta(days=180)
        completers = [
            ev for ev in events
            if ev['event_type'] in _RESET_EVENT_TYPES
            and _parse_ts(ev['ts']) is not None
            and anchor_dt < _parse_ts(ev['ts']) <= window_end
        ]
        if completers:
            first_reset = min(completers, key=lambda ev: ev['ts'])
            sequences.append(_make_sequence(
                'STALENESS_RESET',
                'Process went stale → new signal revived it',
                CQ_STALENESS_RESET,
                anchor, first_reset,
                _window_days(anchor_dt, _parse_ts(first_reset['ts'])),
                supporting_events=completers[1:4],
            ))
    return sequences


# ── Pattern 8: MERGER_PRECEDED_BY_SA ─────────────────────────────────────────
# SA_INTRODUCED in history → MERGER_SIGNED (any time after)
# Retrospective pattern. Confirms SA language was meaningful.
# Primary value: outcome calibration seed data.

def _detect_merger_preceded_by_sa(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    merger_events = [ev for ev in events if ev['event_type'] == EV_MERGER_SIGNED]
    if not merger_events:
        return sequences
    sa_events = [ev for ev in events if ev['event_type'] == EV_SA_INTRODUCED]
    if not sa_events:
        return sequences
    for merger_ev in merger_events:
        merger_dt = _parse_ts(merger_ev['ts'])
        if not merger_dt:
            continue
        # Find SA events that preceded this merger
        preceding_sa = [
            ev for ev in sa_events
            if _parse_ts(ev['ts']) is not None
            and _parse_ts(ev['ts']) < merger_dt
        ]
        if preceding_sa:
            earliest = min(preceding_sa, key=lambda ev: ev['ts'])
            sequences.append(_make_sequence(
                'MERGER_PRECEDED_BY_SA',
                'Strategic alternatives process → merger signed',
                CQ_MERGER_PATHWAY,
                earliest, merger_ev,
                _window_days(_parse_ts(earliest['ts']), merger_dt),
            ))
    return sequences


# ── Pattern 9: MERGER_PRECEDED_BY_ACTIVIST ───────────────────────────────────
# ACTIVIST_INTRODUCED → MERGER_SIGNED (any time after)
# Retrospective: activist pressure resolved in deal.

def _detect_merger_preceded_by_activist(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    merger_events = [ev for ev in events if ev['event_type'] == EV_MERGER_SIGNED]
    if not merger_events:
        return sequences
    activist_events = [ev for ev in events if ev['event_type'] == EV_ACTIVIST_INTRODUCED]
    if not activist_events:
        return sequences
    for merger_ev in merger_events:
        merger_dt = _parse_ts(merger_ev['ts'])
        if not merger_dt:
            continue
        preceding = [
            ev for ev in activist_events
            if _parse_ts(ev['ts']) is not None
            and _parse_ts(ev['ts']) < merger_dt
        ]
        if preceding:
            earliest = min(preceding, key=lambda ev: ev['ts'])
            sequences.append(_make_sequence(
                'MERGER_PRECEDED_BY_ACTIVIST',
                'Activist pressure → merger signed',
                CQ_MERGER_PATHWAY,
                earliest, merger_ev,
                _window_days(_parse_ts(earliest['ts']), merger_dt),
            ))
    return sequences


# ── Pattern 10: RAPID_ESCALATION ─────────────────────────────────────────────
# 2+ distinct escalation events within any rolling 30d window.
# Interpretation: situation is accelerating; multiple independent signals
# appearing together indicate a process moving toward resolution.

def _detect_rapid_escalation(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    escalation_evs = [
        ev for ev in events
        if ev['event_type'] in ESCALATION_EVENTS
        and _parse_ts(ev['ts']) is not None
    ]
    if len(escalation_evs) < 2:
        return sequences

    # Sort by timestamp
    escalation_evs = sorted(escalation_evs, key=lambda ev: ev['ts'])

    # Sliding window: for each event, find all within 30d
    used_anchors = set()
    for i, anchor in enumerate(escalation_evs):
        anchor_dt = _parse_ts(anchor['ts'])
        window_end = anchor_dt + timedelta(days=30)
        cluster = [
            ev for j, ev in enumerate(escalation_evs)
            if j != i
            and _parse_ts(ev['ts']) <= window_end
            and _parse_ts(ev['ts']) >= anchor_dt
            and ev['event_type'] != anchor['event_type']  # distinct types only
        ]
        if cluster:
            key = (anchor['ts'], anchor['event_type'])
            if key in used_anchors:
                continue
            used_anchors.add(key)
            last_ev = max(cluster, key=lambda ev: ev['ts'])
            sequences.append(_make_sequence(
                'RAPID_ESCALATION',
                f'{len(cluster) + 1} escalation signals in {_window_days(anchor_dt, _parse_ts(last_ev["ts"]))}d window',
                CQ_ESCALATING_PROCESS,
                anchor, last_ev,
                _window_days(anchor_dt, _parse_ts(last_ev['ts'])),
                supporting_events=cluster[:-1],
            ))
    return sequences


# ── Pattern 11: COMPOUND_LIVE ─────────────────────────────────────────────────
# Latest snapshot shows 2+ simultaneous LIVE signals.
# (SA + banker, activist + SA, activist + banker, or all three)
# Interpretation: not a single-thread process — multiple independent process
# indicators live simultaneously. Highest-conviction live state.
#
# This pattern uses current snapshot state, not sequential events.

def _detect_compound_live(
    events: list[dict],
    snapshots: list[dict],
) -> list[dict]:
    if not snapshots:
        return []
    latest = snapshots[-1]

    # Count simultaneous live signal types
    live_signals = []
    if latest.get('strategic_alternatives'):
        live_signals.append('strategic_alternatives')
    if latest.get('banker_retained'):
        live_signals.append('banker_retained')
    if latest.get('has_activist_13d'):
        # Only count activist if intent is genuinely process-relevant
        intent = latest.get('activist_13d_intent') or 'UNKNOWN'
        process_intents = {'SALE_PROCESS', 'STRATEGIC_REVIEW', 'ACTIVIST_ESCALATION'}
        if intent in process_intents:
            live_signals.append(f'activist_13d({intent})')
    if latest.get('has_rofn') or latest.get('has_rofr'):
        clause = 'ROFN' if latest.get('has_rofn') else 'ROFR'
        live_signals.append(f'{clause}_rights')

    if len(live_signals) < 2:
        return []

    # Build synthetic anchor + completing events from snapshot timestamp
    snap_ts = latest.get('ts', datetime.now().isoformat())
    synthetic_anchor = {
        'ts': snap_ts,
        'event_type': 'COMPOUND_SNAPSHOT',
        'event_label': 'Simultaneous multi-signal live state',
        'detail': f'Active signals: {", ".join(live_signals)}',
    }
    synthetic_completer = synthetic_anchor

    label = f'Simultaneous: {" + ".join(live_signals)}'
    return [_make_sequence(
        'COMPOUND_LIVE',
        label,
        CQ_STRONG_PROCESS,
        synthetic_anchor, synthetic_completer,
        0,  # window = 0 (simultaneous)
        supporting_events=live_signals,
    )]


# ── Pattern 12: PROCESS_COLLAPSE ─────────────────────────────────────────────
# STATE_DOWNGRADED + ACTIVIST_GONE within 30d (either order).
# OR PROCESS_WEAKENED + STATE_DOWNGRADED within 30d.
# Interpretation: process deteriorating — activist exited and state fell together.
# Useful for aging/false-positive suppression.

def _detect_process_collapse(
    events: list[dict],
    snapshots: list[dict],  # noqa: ARG001
) -> list[dict]:
    sequences = []
    decay_types = {EV_STATE_DOWNGRADED, EV_ACTIVIST_GONE, EV_PROCESS_WEAKENED}
    decay_evs = [
        ev for ev in events
        if ev['event_type'] in decay_types
        and _parse_ts(ev['ts']) is not None
    ]
    if len(decay_evs) < 2:
        return sequences

    decay_evs = sorted(decay_evs, key=lambda ev: ev['ts'])
    used = set()
    for i, anchor in enumerate(decay_evs):
        anchor_dt = _parse_ts(anchor['ts'])
        window_end = anchor_dt + timedelta(days=30)
        cluster = [
            ev for j, ev in enumerate(decay_evs)
            if j != i
            and _parse_ts(ev['ts']) <= window_end
            and _parse_ts(ev['ts']) >= anchor_dt
            and ev['event_type'] != anchor['event_type']
        ]
        if cluster:
            key = (anchor['ts'], anchor['event_type'])
            if key in used:
                continue
            used.add(key)
            last_ev = max(cluster, key=lambda ev: ev['ts'])
            sequences.append(_make_sequence(
                'PROCESS_COLLAPSE',
                'Process deteriorating — simultaneous decay signals',
                CQ_PROCESS_COLLAPSE,
                anchor, last_ev,
                _window_days(anchor_dt, _parse_ts(last_ev['ts'])),
                supporting_events=cluster,
            ))
    return sequences


# ── Pattern registry ───────────────────────────────────────────────────────────

_PATTERN_DETECTORS = [
    _detect_escalating_activist,
    _detect_advisor_then_sa,
    _detect_activist_then_sa,
    _detect_sa_then_activist,
    _detect_rofr_then_activist,
    _detect_activist_then_rofr,
    _detect_staleness_reset,
    _detect_merger_preceded_by_sa,
    _detect_merger_preceded_by_activist,
    _detect_rapid_escalation,
    _detect_compound_live,
    _detect_process_collapse,
]


# ── Public API ────────────────────────────────────────────────────────────────

def detect_sequences(ticker: str, state_history_db: dict) -> list[dict]:
    """
    Detect all named sequence patterns for a single ticker.

    Args:
        ticker:           stock symbol
        state_history_db: full state_history dict (as loaded by load_state_history)

    Returns:
        List of matched sequence dicts, sorted by detected_ts (newest first).
        Empty list if ticker not in history or no patterns match.
    """
    entry = state_history_db.get(ticker, {})
    if not entry:
        return []

    events    = entry.get('transitions', [])
    snapshots = entry.get('snapshots', [])

    if not events and not snapshots:
        return []

    all_sequences = []
    for detector in _PATTERN_DETECTORS:
        try:
            found = detector(events, snapshots)
            all_sequences.extend(found)
        except Exception:
            pass

    # Deduplicate: same type + same anchor ts = same detection
    seen = set()
    unique_sequences = []
    for seq in all_sequences:
        key = (seq['sequence_type'], seq['anchor_event'].get('ts', ''))
        if key not in seen:
            seen.add(key)
            unique_sequences.append(seq)

    # Sort newest-first by detecting_ts
    unique_sequences.sort(key=lambda s: s.get('detected_ts', ''), reverse=True)
    return unique_sequences


def detect_all_sequences(state_history_db: dict) -> dict[str, list[dict]]:
    """
    Run sequence detection for all tickers in the state history DB.

    Args:
        state_history_db: full state_history dict

    Returns:
        {ticker: [sequence, ...]} — tickers with no matches are excluded.
    """
    result = {}
    for ticker in state_history_db:
        sequences = detect_sequences(ticker, state_history_db)
        if sequences:
            result[ticker] = sequences
    return result


def primary_sequence(sequences: list[dict]) -> Optional[dict]:
    """
    Select the highest-priority sequence from a list of detected sequences.

    Priority is determined by compound_signal_quality rank (CQ_PRIORITY),
    then recency (detected_ts).

    Returns the primary sequence dict, or None if list is empty.
    """
    if not sequences:
        return None

    def _priority_key(seq: dict) -> tuple:
        cq = seq.get('compound_signal_quality', '')
        try:
            rank = CQ_PRIORITY.index(cq)
        except ValueError:
            rank = len(CQ_PRIORITY)
        return (rank, seq.get('detected_ts', ''))

    return min(sequences, key=_priority_key)


def attach_sequences_to_result(result: dict, sequences: list[dict]) -> dict:
    """
    Attach sequence detection fields to a scan result dict.

    Adds:
      detected_sequences       — full list (may be empty)
      sequence_type            — primary sequence type (or None)
      sequence_label           — primary sequence label (or None)
      sequence_window_days     — primary sequence window (or None)
      compound_signal_quality  — primary compound quality label (or None)

    Returns the result dict (mutated in-place and returned).
    """
    result['detected_sequences'] = sequences
    primary = primary_sequence(sequences)
    if primary:
        result['sequence_type']           = primary['sequence_type']
        result['sequence_label']          = primary['sequence_label']
        result['sequence_window_days']    = primary['sequence_window_days']
        result['compound_signal_quality'] = primary['compound_signal_quality']
    else:
        result['sequence_type']           = None
        result['sequence_label']          = None
        result['sequence_window_days']    = None
        result['compound_signal_quality'] = None
    return result


# ── Query helpers ──────────────────────────────────────────────────────────────

def get_tickers_by_sequence(
    all_seq: dict[str, list[dict]],
    sequence_type: str,
) -> list[str]:
    """Return tickers that have at least one matched sequence of the given type."""
    return [
        tkr for tkr, seqs in all_seq.items()
        if any(s['sequence_type'] == sequence_type for s in seqs)
    ]


def get_recent_sequences(
    all_seq: dict[str, list[dict]],
    last_n_days: int = 14,
) -> list[dict]:
    """
    Return all detected sequences across all tickers, filtered to those
    detected within last_n_days. Sorted newest-first.

    Each entry has '_ticker' field injected for identification.
    """
    cutoff = datetime.now() - timedelta(days=last_n_days)
    results = []
    for ticker, seqs in all_seq.items():
        for seq in seqs:
            detected_dt = _parse_ts(seq.get('detected_ts', ''))
            if detected_dt and detected_dt >= cutoff:
                results.append({**seq, '_ticker': ticker})
    results.sort(key=lambda s: s.get('detected_ts', ''), reverse=True)
    return results


# ── Standalone test harness ───────────────────────────────────────────────────

if __name__ == '__main__':
    import json
    import sys

    # Usage: python3 sequence_detector.py [state_history.json] [TICKER]
    history_path = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(__file__), '..', 'data', 'tracking', 'state_history.json')

    if not os.path.exists(history_path):
        print(f'No state_history.json at {history_path}')
        sys.exit(0)

    with open(history_path) as f:
        db = json.load(f)

    filter_ticker = sys.argv[2].upper() if len(sys.argv) > 2 else None

    tickers_to_check = [filter_ticker] if filter_ticker else sorted(db.keys())
    total_sequences = 0

    for tkr in tickers_to_check:
        if tkr not in db:
            print(f'{tkr}: not in state history')
            continue
        seqs = detect_sequences(tkr, db)
        if not seqs:
            print(f'{tkr}: no sequences detected')
            continue
        total_sequences += len(seqs)
        print(f'\n{tkr}: {len(seqs)} sequence(s) detected')
        primary = primary_sequence(seqs)
        for seq in seqs:
            marker = '  [PRIMARY]' if seq is primary else '         '
            print(f'{marker} {seq["sequence_type"]:35s} | {seq["compound_signal_quality"]:22s} | '
                  f'{seq["sequence_window_days"]:>4}d | {seq["sequence_label"]}')

    print(f'\nTotal: {total_sequences} sequence(s) across {len(tickers_to_check)} ticker(s)')
