"""
process_history.py — Process-state transition tracking and historical state memory.

Moves the scanner from point-in-time classification to trajectory intelligence:
  - Persistent per-ticker state snapshots across scans
  - Transition event detection and labeling
  - Escalation / decay / wording-evolution tracking
  - Chronological process evolution record

Storage: data/tracking/state_history.json
Format:  { TICKER: { snapshots: [...], transitions: [...], current_state, first_seen_ts } }

Rule-based only. No ML, no embeddings, no vector DB.

Integration:
  1. Call load_state_history() at scan start
  2. Call update_ticker_history(ticker, result, db) after each ticker is scored
  3. Call save_state_history(db) at scan end
  4. Attach result['state_transitions'] and result['process_state'] from update_ticker_history()
"""

import os
import json
from datetime import datetime

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_SNAPSHOTS = 52          # ~1 year of weekly scans per ticker
SCORE_DELTA_THRESHOLD = 10  # Minimum score change to generate SCORE_JUMP/DROP event

# Process state hierarchy — higher rank = stronger process evidence
STATE_RANK = {
    'SIGNED':    5,
    'LIVE':      4,
    'PATHWAY':   3,
    'SCREENING': 2,
    'AGING':     1,
}

# Activist intent hierarchy — higher rank = stronger sale pressure
INTENT_RANK = {
    'SALE_PROCESS':                 8,
    'STRATEGIC_REVIEW':             7,
    'ACTIVIST_ESCALATION':          6,
    'BOARD_CHANGE':                 5,
    'CAPITAL_ALLOCATION':           4,
    'GOVERNANCE_ONLY':              3,
    'GENERIC_SHAREHOLDER_PRESSURE': 2,
    'PASSIVE_ACCUMULATION':         1,
    'UNKNOWN':                      0,
}

# Intensity hierarchy
INTENSITY_RANK = {
    'STRONG_PROCESS_SIGNAL':   4,
    'MODERATE_PROCESS_SIGNAL': 3,
    'WEAK_PROCESS_SIGNAL':     2,
    'GENERIC_ACTIVISM':        1,
    'PASSIVE':                 0,
}

# Staleness thresholds that trigger SIGNAL_STALE events (days)
STALE_THRESHOLDS = [45, 90]

# ── Transition event types ────────────────────────────────────────────────────

EV_FIRST_DETECTED           = 'FIRST_DETECTED'
EV_STATE_UPGRADED           = 'STATE_UPGRADED'
EV_STATE_DOWNGRADED         = 'STATE_DOWNGRADED'
EV_MERGER_SIGNED            = 'MERGER_SIGNED'
EV_SA_INTRODUCED            = 'SA_INTRODUCED'
EV_ADVISOR_INTRODUCED       = 'ADVISOR_INTRODUCED'
EV_ACTIVIST_INTRODUCED      = 'ACTIVIST_INTRODUCED'
EV_ACTIVIST_INTENT_ESCALATED = 'ACTIVIST_INTENT_ESCALATED'
EV_INTENT_INTENSITY_UPGRADED = 'INTENT_INTENSITY_UPGRADED'
EV_ROFR_INTRODUCED          = 'ROFR_INTRODUCED'
EV_SIGNAL_STALE             = 'SIGNAL_STALE'
EV_ACTIVIST_GONE            = 'ACTIVIST_GONE'
EV_PROCESS_WEAKENED         = 'PROCESS_WEAKENED'
EV_SCORE_JUMP               = 'SCORE_JUMP'
EV_SCORE_DROP               = 'SCORE_DROP'


# ── Process state derivation ──────────────────────────────────────────────────

def derive_process_state(result: dict) -> str:
    """
    Derive backend process state from signal_quality and signal_age_days.

    Mirrors the frontend JS logic (PS_LIVE, PS_PATHWAY, PS_SIGNED, PS_SCREENING)
    so the backend and dashboard stay consistent.

    Returns: 'LIVE' | 'PATHWAY' | 'SIGNED' | 'SCREENING' | 'AGING'
    """
    sq  = result.get('signal_quality', 'SCORE_ONLY') or 'SCORE_ONLY'
    age = result.get('signal_age_days', 999) or 999

    if sq == 'MERGER':
        return 'SIGNED'
    if sq in ('AFFIRM', 'PROCESS'):
        return 'LIVE'
    if sq == 'ROFR':
        return 'PATHWAY'
    if age >= 90:
        return 'AGING'
    return 'SCREENING'


# ── Snapshot construction ─────────────────────────────────────────────────────

def build_snapshot(result: dict, process_state: str) -> dict:
    """
    Extract the minimal stable fields from a scan result for history storage.

    Only stores fields needed for transition detection and future sequencing.
    Excludes heavy fields (signals list, full description, layer scores).
    """
    return {
        'ts':                    result.get('scan_date', datetime.now().isoformat()),
        'process_state':         process_state,
        'signal_quality':        result.get('signal_quality', 'SCORE_ONLY'),
        'score':                 result.get('score', 0),
        'conviction_tier':       result.get('conviction_tier', 'BELOW_THRESHOLD'),
        # Activist 13D
        'has_activist_13d':      result.get('has_activist_13d', False),
        'activist_filer':        result.get('activist_filer'),
        'activist_13d_intent':   result.get('activist_13d_intent'),
        'activist_13d_intensity': result.get('activist_13d_intensity'),
        # 8-K signals
        'strategic_alternatives': result.get('strategic_alternatives', False),
        'banker_retained':        result.get('banker_retained', False),
        'has_rofn':               result.get('has_rofn', False),
        'has_rofr':               result.get('has_rofr', False),
        'named_pharma_partner':   result.get('named_pharma_partner'),
        'top_8k_phrase':          result.get('top_8k_phrase', ''),
        # Freshness
        'signal_age_days':        result.get('signal_age_days', 999),
    }


def _make_event(event_type: str, label: str, detail: str,
                from_state: str | None, to_state: str | None,
                ts: str, delta: dict | None = None) -> dict:
    """Construct a standardized transition event dict."""
    return {
        'ts':          ts,
        'event_type':  event_type,
        'event_label': label,
        'detail':      detail,
        'from_state':  from_state,
        'to_state':    to_state,
        'delta':       delta or {},
    }


# ── Transition detection ──────────────────────────────────────────────────────

def detect_transitions(new_snap: dict, prior_snap: dict | None,
                       ticker_entry: dict) -> list[dict]:
    """
    Compare new snapshot against the prior snapshot and generate transition events.

    Checks (in order of strategic importance):
      1. First detection
      2. State transitions (SCREENING→LIVE, LIVE→SIGNED, etc.)
      3. Merger signed
      4. New signals introduced (SA, advisor, activist, ROFR)
      5. Activist intent escalation
      6. Intent intensity upgrade
      7. Signal staleness crossing thresholds
      8. Signal withdrawal / process weakening
      9. Score jumps / drops

    Returns list of event dicts. Empty list = no meaningful change.
    """
    events = []
    ts = new_snap['ts']

    # ── 1. First detection ────────────────────────────────────────────────────
    if prior_snap is None:
        ps = new_snap['process_state']
        sq = new_snap['signal_quality']
        events.append(_make_event(
            EV_FIRST_DETECTED,
            f'First detected: {ps}',
            f'{ticker_entry.get("ticker","")} entered scan universe as {ps} '
            f'(signal_quality={sq}, score={new_snap["score"]:.0f})',
            None, ps, ts,
            {'signal_quality': sq, 'score': new_snap['score']},
        ))
        return events   # no comparisons without prior

    prev_ps = prior_snap['process_state']
    new_ps  = new_snap['process_state']

    # ── 2. State transitions ──────────────────────────────────────────────────
    if new_ps != prev_ps:
        prev_rank = STATE_RANK.get(prev_ps, 0)
        new_rank  = STATE_RANK.get(new_ps, 0)

        if new_ps == 'SIGNED':
            events.append(_make_event(
                EV_MERGER_SIGNED,
                'Merger agreement signed — process resolved',
                f'Signal quality upgraded to MERGER. Process state: {prev_ps} → SIGNED.',
                prev_ps, 'SIGNED', ts,
                {'prev_signal_quality': prior_snap['signal_quality']},
            ))
        elif new_rank > prev_rank:
            events.append(_make_event(
                EV_STATE_UPGRADED,
                f'Process state upgraded: {prev_ps} → {new_ps}',
                _state_upgrade_detail(prior_snap, new_snap),
                prev_ps, new_ps, ts,
                {
                    'prev_signal_quality': prior_snap['signal_quality'],
                    'new_signal_quality':  new_snap['signal_quality'],
                    'score_delta': round(new_snap['score'] - prior_snap['score'], 1),
                },
            ))
        elif new_rank < prev_rank:
            events.append(_make_event(
                EV_STATE_DOWNGRADED,
                f'Process state downgraded: {prev_ps} → {new_ps}',
                _state_downgrade_detail(prior_snap, new_snap),
                prev_ps, new_ps, ts,
                {
                    'prev_signal_quality': prior_snap['signal_quality'],
                    'new_signal_quality':  new_snap['signal_quality'],
                    'score_delta': round(new_snap['score'] - prior_snap['score'], 1),
                },
            ))

    # ── 3. New signals introduced ─────────────────────────────────────────────
    if new_snap['strategic_alternatives'] and not prior_snap.get('strategic_alternatives'):
        events.append(_make_event(
            EV_SA_INTRODUCED,
            'Strategic-alternatives language introduced in 8-K',
            f'Board-level strategic alternatives language newly detected. '
            f'Top phrase: "{new_snap.get("top_8k_phrase","")}".',
            prev_ps, new_ps, ts,
        ))

    if new_snap['banker_retained'] and not prior_snap.get('banker_retained'):
        events.append(_make_event(
            EV_ADVISOR_INTRODUCED,
            'Financial advisor / potential-sale language newly detected',
            f'Advisor retention or potential-sale language appeared in 8-K filing. '
            f'Top phrase: "{new_snap.get("top_8k_phrase","")}".',
            prev_ps, new_ps, ts,
        ))

    if new_snap['has_activist_13d'] and not prior_snap.get('has_activist_13d'):
        intent = new_snap.get('activist_13d_intent') or 'UNKNOWN'
        filer  = new_snap.get('activist_filer') or 'Unknown'
        events.append(_make_event(
            EV_ACTIVIST_INTRODUCED,
            f'Activist SC 13D newly filed by {filer}',
            f'{filer} filed SC 13D. Item 4 classification: {intent} '
            f'({new_snap.get("activist_13d_intensity","")}).',
            prev_ps, new_ps, ts,
            {'intent': intent, 'filer': filer},
        ))

    if (new_snap['has_rofn'] or new_snap['has_rofr']) and \
       not (prior_snap.get('has_rofn') or prior_snap.get('has_rofr')):
        clause = 'ROFN' if new_snap['has_rofn'] else 'ROFR'
        pharma = new_snap.get('named_pharma_partner') or 'major pharma'
        events.append(_make_event(
            EV_ROFR_INTRODUCED,
            f'{clause} clause newly detected with {pharma}',
            f'Acquisition rights clause ({clause}) appeared in 8-K. Partner: {pharma}.',
            prev_ps, new_ps, ts,
            {'clause': clause, 'partner': pharma},
        ))

    # ── 4. Activist intent escalation ────────────────────────────────────────
    if new_snap.get('has_activist_13d') and prior_snap.get('has_activist_13d'):
        new_intent  = new_snap.get('activist_13d_intent') or 'UNKNOWN'
        prev_intent = prior_snap.get('activist_13d_intent') or 'UNKNOWN'
        new_rank_i  = INTENT_RANK.get(new_intent, 0)
        prev_rank_i = INTENT_RANK.get(prev_intent, 0)

        if new_rank_i > prev_rank_i:
            events.append(_make_event(
                EV_ACTIVIST_INTENT_ESCALATED,
                f'Activist intent escalated: {prev_intent} → {new_intent}',
                f'Item 4 language shifted from {prev_intent} to {new_intent}. '
                f'Filer: {new_snap.get("activist_filer","Unknown")}.',
                prev_ps, new_ps, ts,
                {'prev_intent': prev_intent, 'new_intent': new_intent},
            ))

        # Intensity upgrade (same intent bucket, stronger phrasing)
        new_intens  = new_snap.get('activist_13d_intensity') or 'GENERIC_ACTIVISM'
        prev_intens = prior_snap.get('activist_13d_intensity') or 'GENERIC_ACTIVISM'
        new_rank_n  = INTENSITY_RANK.get(new_intens, 0)
        prev_rank_n = INTENSITY_RANK.get(prev_intens, 0)

        if new_rank_n > prev_rank_n:
            events.append(_make_event(
                EV_INTENT_INTENSITY_UPGRADED,
                f'Item 4 process intensity upgraded: {prev_intens} → {new_intens}',
                f'Activist language strengthened within {new_intent} classification.',
                prev_ps, new_ps, ts,
                {'prev_intensity': prev_intens, 'new_intensity': new_intens},
            ))

    # ── 5. Staleness thresholds ───────────────────────────────────────────────
    new_age  = new_snap.get('signal_age_days', 999)
    prev_age = prior_snap.get('signal_age_days', 999)
    for threshold in STALE_THRESHOLDS:
        if new_age >= threshold > prev_age:
            events.append(_make_event(
                EV_SIGNAL_STALE,
                f'Signal stale — {new_age}d without escalation (threshold: {threshold}d)',
                f'Process signal has aged past {threshold} days with no new escalation. '
                f'Current state: {new_ps}.',
                prev_ps, new_ps, ts,
                {'signal_age_days': new_age, 'threshold': threshold},
            ))

    # ── 6. Signal withdrawal / process weakening ──────────────────────────────
    if prior_snap.get('has_activist_13d') and not new_snap.get('has_activist_13d'):
        events.append(_make_event(
            EV_ACTIVIST_GONE,
            'Activist 13D no longer detected',
            f'SC 13D previously filed by {prior_snap.get("activist_filer","Unknown")} '
            f'is no longer in the 60-day window. Possible withdrawal or expiry.',
            prev_ps, new_ps, ts,
            {'prev_filer': prior_snap.get('activist_filer')},
        ))

    weakened = []
    if prior_snap.get('strategic_alternatives') and not new_snap.get('strategic_alternatives'):
        weakened.append('strategic alternatives language removed')
    if prior_snap.get('banker_retained') and not new_snap.get('banker_retained'):
        weakened.append('advisor/potential-sale language removed')
    if (prior_snap.get('has_rofn') or prior_snap.get('has_rofr')) and \
       not (new_snap.get('has_rofn') or new_snap.get('has_rofr')):
        weakened.append('ROFR/ROFN clause no longer detected')

    if weakened:
        events.append(_make_event(
            EV_PROCESS_WEAKENED,
            'Process language weakened or removed',
            f'Signals dropped since prior scan: {"; ".join(weakened)}.',
            prev_ps, new_ps, ts,
            {'dropped_signals': weakened},
        ))

    # ── 7. Score jumps / drops ────────────────────────────────────────────────
    score_delta = new_snap['score'] - prior_snap['score']
    if score_delta >= SCORE_DELTA_THRESHOLD:
        events.append(_make_event(
            EV_SCORE_JUMP,
            f'Score jumped +{score_delta:.0f} pts ({prior_snap["score"]:.0f} → {new_snap["score"]:.0f})',
            f'Meaningful score increase. Current state: {new_ps}.',
            prev_ps, new_ps, ts,
            {'prev_score': prior_snap['score'], 'new_score': new_snap['score'],
             'delta': round(score_delta, 1)},
        ))
    elif score_delta <= -SCORE_DELTA_THRESHOLD:
        events.append(_make_event(
            EV_SCORE_DROP,
            f'Score dropped {score_delta:.0f} pts ({prior_snap["score"]:.0f} → {new_snap["score"]:.0f})',
            f'Meaningful score decrease. Current state: {new_ps}.',
            prev_ps, new_ps, ts,
            {'prev_score': prior_snap['score'], 'new_score': new_snap['score'],
             'delta': round(score_delta, 1)},
        ))

    return events


def _state_upgrade_detail(prior: dict, new: dict) -> str:
    sq_new = new.get('signal_quality', '')
    if sq_new == 'AFFIRM':
        return ('Board affirmed strategic alternatives in 8-K. '
                f'Process state: {prior["process_state"]} → {new["process_state"]}.')
    if sq_new == 'PROCESS':
        if new.get('banker_retained'):
            return ('Financial advisor retained — process state upgraded. '
                    f'{prior["process_state"]} → {new["process_state"]}.')
        if new.get('has_activist_13d'):
            intent = new.get('activist_13d_intent') or ''
            return (f'Activist 13D detected [{intent}] — process state upgraded. '
                    f'{prior["process_state"]} → {new["process_state"]}.')
    if sq_new == 'ROFR':
        pharma = new.get('named_pharma_partner') or 'major pharma'
        return (f'ROFR/ROFN clause with {pharma} — process state upgraded. '
                f'{prior["process_state"]} → {new["process_state"]}.')
    return (f'Process state upgraded: {prior["process_state"]} → {new["process_state"]}. '
            f'Signal quality: {prior["signal_quality"]} → {sq_new}.')


def _state_downgrade_detail(prior: dict, new: dict) -> str:
    prev_ps = prior['process_state']
    new_ps  = new['process_state']
    if new_ps == 'AGING':
        return (f'Signal stale — no escalation detected. '
                f'Process state: {prev_ps} → AGING '
                f'(signal age: {new.get("signal_age_days", "?")} days).')
    return (f'Process state downgraded: {prev_ps} → {new_ps}. '
            f'Signal quality: {prior["signal_quality"]} → {new["signal_quality"]}. '
            f'Check whether key signals were removed or expired.')


# ── Main update function ──────────────────────────────────────────────────────

def update_ticker_history(ticker: str, result: dict, db: dict) -> list[dict]:
    """
    Update state history for a single ticker and return transition events.

    Args:
        ticker: stock symbol
        result: full scan result dict for this ticker
        db:     state history database (mutated in-place)

    Returns:
        list of transition events generated this scan (may be empty)
    """
    process_state = derive_process_state(result)
    new_snap      = build_snapshot(result, process_state)
    new_snap['ticker'] = ticker   # embed for future reference in stored events
    ts            = new_snap['ts']

    if ticker not in db:
        db[ticker] = {
            'snapshots':        [],
            'transitions':      [],
            'current_state':    process_state,
            'first_seen_ts':    ts,
            'last_updated_ts':  ts,
            'state_entered_ts': ts,
        }

    entry = db[ticker]

    prior_snap = entry['snapshots'][-1] if entry['snapshots'] else None

    # Detect transitions
    events = detect_transitions(new_snap, prior_snap, entry)

    # Track when current state was first entered
    if process_state != entry.get('current_state'):
        entry['state_entered_ts'] = ts
    entry['current_state']   = process_state
    entry['last_updated_ts'] = ts

    # Append snapshot (capped at MAX_SNAPSHOTS)
    entry['snapshots'].append(new_snap)
    if len(entry['snapshots']) > MAX_SNAPSHOTS:
        entry['snapshots'] = entry['snapshots'][-MAX_SNAPSHOTS:]

    # Append events
    entry['transitions'].extend(events)

    return events


# ── Persistence ───────────────────────────────────────────────────────────────

def load_state_history(path: str) -> dict:
    """
    Load state history from JSON file.
    Returns empty dict if file missing or corrupt.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_state_history(db: dict, path: str) -> None:
    """Write state history to JSON file (atomic via temp file approach)."""
    tmp = path + '.tmp'
    try:
        with open(tmp, 'w') as f:
            json.dump(db, f, indent=2, default=str)
        os.replace(tmp, path)
    except Exception as e:
        print(f'  [state_history] Save failed: {e}')


# ── Query helpers (for future analog matching) ─────────────────────────────────

def get_ticker_trajectory(ticker: str, db: dict) -> list[dict]:
    """
    Return the ordered list of state snapshots for a ticker.
    Oldest first. Used for sequencing analysis and analog matching.
    """
    return db.get(ticker, {}).get('snapshots', [])


def get_ticker_transitions(ticker: str, db: dict, last_n: int = 10) -> list[dict]:
    """Return the last N transition events for a ticker, newest first."""
    transitions = db.get(ticker, {}).get('transitions', [])
    return list(reversed(transitions))[:last_n]


def get_state_entered_ts(ticker: str, db: dict) -> str | None:
    """Return ISO timestamp when ticker entered its current state."""
    return db.get(ticker, {}).get('state_entered_ts')


def get_tickers_by_state(db: dict, state: str) -> list[str]:
    """Return all tickers currently in the given process state."""
    return [t for t, e in db.items() if e.get('current_state') == state]


def get_recent_transitions(db: dict, event_type: str = None,
                           last_n_days: int = 14) -> list[dict]:
    """
    Return all transition events across all tickers in the last N days.
    Optionally filter by event_type.
    Newest first. Useful for surfacing recent escalations across universe.
    """
    cutoff = datetime.now()
    results = []
    for ticker, entry in db.items():
        for ev in entry.get('transitions', []):
            try:
                ev_ts = datetime.fromisoformat(ev['ts'])
                age   = (cutoff - ev_ts).days
                if age > last_n_days:
                    continue
                if event_type and ev['event_type'] != event_type:
                    continue
                results.append({**ev, '_ticker': ticker})
            except Exception:
                continue
    results.sort(key=lambda x: x['ts'], reverse=True)
    return results


def summarize_ticker_evolution(ticker: str, db: dict) -> dict:
    """
    Produce a compact process-evolution summary for a ticker.
    Returns a dict usable as context for future analog-matching logic.

    Preserves:
      - state sequence (chronological state transitions)
      - escalation events
      - first/current process state
      - total scan history length
      - days in current state
    """
    entry = db.get(ticker, {})
    if not entry:
        return {}

    transitions = entry.get('transitions', [])
    snapshots   = entry.get('snapshots', [])

    # Build compact state sequence
    state_sequence = []
    for ev in transitions:
        if ev['event_type'] in (EV_FIRST_DETECTED, EV_STATE_UPGRADED,
                                EV_STATE_DOWNGRADED, EV_MERGER_SIGNED):
            state_sequence.append({
                'ts':    ev['ts'],
                'state': ev['to_state'],
                'event': ev['event_type'],
            })

    # Escalation events (meaningful process signal changes)
    escalations = [
        ev for ev in transitions
        if ev['event_type'] in (
            EV_SA_INTRODUCED, EV_ADVISOR_INTRODUCED, EV_ACTIVIST_INTRODUCED,
            EV_ACTIVIST_INTENT_ESCALATED, EV_INTENT_INTENSITY_UPGRADED,
            EV_ROFR_INTRODUCED, EV_MERGER_SIGNED, EV_STATE_UPGRADED,
        )
    ]

    # Days in current state
    entered_ts = entry.get('state_entered_ts')
    days_in_state = None
    if entered_ts:
        try:
            days_in_state = (datetime.now() - datetime.fromisoformat(entered_ts)).days
        except Exception:
            pass

    return {
        'ticker':           ticker,
        'current_state':    entry.get('current_state'),
        'first_seen_ts':    entry.get('first_seen_ts'),
        'state_entered_ts': entered_ts,
        'days_in_state':    days_in_state,
        'snapshot_count':   len(snapshots),
        'state_sequence':   state_sequence,
        'escalation_count': len(escalations),
        'escalation_events': escalations[-5:],  # last 5, for context
        'last_intent':      (snapshots[-1].get('activist_13d_intent') if snapshots else None),
        'last_intensity':   (snapshots[-1].get('activist_13d_intensity') if snapshots else None),
    }
