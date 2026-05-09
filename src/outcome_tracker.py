"""
outcome_tracker.py — Persistent outcome logging for M&A Scanner picks.

Every HIGH/MEDIUM pick is logged with entry date, price, score, and tier.
When a deal closes (or fails), the outcome is recorded and used to calibrate
the P(deal) table in trade_logic.py.

Schema per pick:
    ticker          str
    company         str
    pick_date       ISO date string (YYYY-MM-DD)
    pick_price      float
    pick_tier       'HIGH_CONVICTION' | 'MEDIUM_CONVICTION'
    pick_score      float
    signal_quality  str  (from trade_logic)
    p_deal_at_pick  float
    outcome         'PENDING' | 'DEAL_ANNOUNCED' | 'DEAL_CLOSED' | 'DEAL_FAILED' | 'DELISTED'
    outcome_date    str or null
    acquirer        str or null
    deal_price      float or null   (per-share offer price)
    premium_pct     float or null   (vs pick_price)
    notes           str
"""

import json
import os
from datetime import datetime
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKING_DIR = os.path.join(REPO_ROOT, 'data', 'tracking')
os.makedirs(TRACKING_DIR, exist_ok=True)
OUTCOMES_PATH = os.path.join(TRACKING_DIR, 'outcomes.json')

VALID_OUTCOMES = {'PENDING', 'DEAL_ANNOUNCED', 'DEAL_CLOSED', 'DEAL_FAILED', 'DELISTED'}


# ─────────────────────────────────────────────────────────────────────────────
# IO
# ─────────────────────────────────────────────────────────────────────────────

def _load() -> dict:
    if not os.path.exists(OUTCOMES_PATH):
        return {}
    try:
        with open(OUTCOMES_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> None:
    with open(OUTCOMES_PATH, 'w') as f:
        json.dump(data, f, indent=2, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def log_pick(result: dict) -> bool:
    """
    Log a scanner result as a tracked pick if it's HIGH or MEDIUM conviction
    and hasn't been logged before (first-seen only).

    Returns True if a new pick was added, False if already tracked.
    """
    tier = result.get('conviction_tier', '')
    if tier not in ('HIGH_CONVICTION', 'MEDIUM_CONVICTION'):
        return False

    ticker = result['ticker']
    data   = _load()

    # Only log first appearance — don't overwrite existing entries
    if ticker in data:
        return False

    data[ticker] = {
        'ticker':         ticker,
        'company':        result.get('company', ''),
        'pick_date':      datetime.now().strftime('%Y-%m-%d'),
        'pick_price':     result.get('price'),
        'pick_tier':      tier,
        'pick_score':     result.get('score'),
        'signal_quality': result.get('signal_quality', ''),
        'p_deal_at_pick': result.get('p_deal'),
        'outcome':        'PENDING',
        'outcome_date':   None,
        'acquirer':       None,
        'deal_price':     None,
        'premium_pct':    None,
        'notes':          '',
    }
    _save(data)
    return True


def update_outcome(ticker: str,
                   outcome: str,
                   outcome_date: Optional[str] = None,
                   acquirer: Optional[str] = None,
                   deal_price: Optional[float] = None,
                   notes: str = '') -> bool:
    """
    Update the outcome for a tracked pick.

    outcome: one of PENDING | DEAL_ANNOUNCED | DEAL_CLOSED | DEAL_FAILED | DELISTED
    deal_price: per-share offer price (used to compute premium vs pick_price)
    """
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f'outcome must be one of {VALID_OUTCOMES}')

    data = _load()
    if ticker not in data:
        print(f'  {ticker} not found in outcomes — run a scan first to log the pick')
        return False

    entry = data[ticker]
    entry['outcome']      = outcome
    entry['outcome_date'] = outcome_date or datetime.now().strftime('%Y-%m-%d')
    entry['acquirer']     = acquirer
    entry['deal_price']   = deal_price
    entry['notes']        = notes

    if deal_price and entry.get('pick_price'):
        entry['premium_pct'] = round(
            (deal_price - entry['pick_price']) / entry['pick_price'] * 100, 1
        )

    _save(data)
    print(f'  {ticker}: outcome updated → {outcome}'
          + (f' | deal at ${deal_price} ({entry["premium_pct"]:+.1f}% vs pick price)' if deal_price else ''))
    return True


def log_picks_from_scan(results: list) -> int:
    """
    Bulk-log all HIGH/MEDIUM picks from a scan result list.
    Returns count of new picks added.
    """
    added = sum(log_pick(r) for r in results)
    if added:
        print(f'  Outcome tracker: {added} new pick(s) logged to outcomes.json')
    return added


def auto_detect_deals(results: list) -> None:
    """
    Scan results for merger_agreement signals — these are virtually certain
    deals and should be flagged for outcome update.
    """
    data = _load()
    for r in results:
        ticker = r.get('ticker', '')
        ts     = r.get('_text_signals', {}) or {}
        if ts.get('merger_agreement') and ticker in data:
            if data[ticker]['outcome'] == 'PENDING':
                print(f'  ★ {ticker}: merger_agreement detected — update outcome with update_outcome()')


# ─────────────────────────────────────────────────────────────────────────────
# CALIBRATION
# ─────────────────────────────────────────────────────────────────────────────

def calibration_stats() -> dict:
    """
    Compute realised deal rates by signal quality and tier.
    Only counts resolved outcomes (not PENDING).

    Returns dict with per-group stats used to validate/update P(deal) table.
    """
    data    = _load()
    entries = list(data.values())

    resolved = [e for e in entries if e['outcome'] != 'PENDING']
    if not resolved:
        return {'error': 'No resolved outcomes yet — need deals to close or fail'}

    # Group by signal_quality
    groups = {}
    for e in resolved:
        sq  = e.get('signal_quality', 'UNKNOWN')
        grp = groups.setdefault(sq, {'deals': 0, 'total': 0, 'premiums': []})
        grp['total'] += 1
        if e['outcome'] in ('DEAL_ANNOUNCED', 'DEAL_CLOSED'):
            grp['deals'] += 1
            if e.get('premium_pct') is not None:
                grp['premiums'].append(e['premium_pct'])

    stats = {}
    for sq, g in groups.items():
        hit_rate = g['deals'] / g['total'] if g['total'] else 0
        stats[sq] = {
            'hit_rate':      round(hit_rate, 3),
            'deals':         g['deals'],
            'total':         g['total'],
            'avg_premium':   round(sum(g['premiums']) / len(g['premiums']), 1) if g['premiums'] else None,
        }

    # Overall
    total_resolved = len(resolved)
    total_deals    = sum(1 for e in resolved if e['outcome'] in ('DEAL_ANNOUNCED', 'DEAL_CLOSED'))
    all_premiums   = [e['premium_pct'] for e in resolved if e.get('premium_pct') is not None]

    return {
        'by_signal_quality': stats,
        'overall': {
            'hit_rate':    round(total_deals / total_resolved, 3) if total_resolved else None,
            'deals':       total_deals,
            'total':       total_resolved,
            'avg_premium': round(sum(all_premiums) / len(all_premiums), 1) if all_premiums else None,
            'pending':     len([e for e in entries if e['outcome'] == 'PENDING']),
        }
    }


def print_summary() -> None:
    """Print a human-readable summary of all tracked picks."""
    data = _load()
    if not data:
        print('  No picks tracked yet.')
        return

    pending  = [e for e in data.values() if e['outcome'] == 'PENDING']
    resolved = [e for e in data.values() if e['outcome'] != 'PENDING']

    print(f'\n{"─"*72}')
    print(f'  OUTCOME TRACKER  —  {len(data)} picks total  |  '
          f'{len(pending)} pending  |  {len(resolved)} resolved')
    print(f'{"─"*72}')

    # Pending picks
    if pending:
        print(f'\n  PENDING ({len(pending)}):')
        for e in sorted(pending, key=lambda x: x['pick_date'], reverse=True):
            print(f"    {e['ticker']:<8} {e['pick_tier'][:4]}  "
                  f"picked {e['pick_date']} @ ${e['pick_price']:.2f}  "
                  f"score={e['pick_score']}  quality={e['signal_quality']}")

    # Resolved picks
    if resolved:
        print(f'\n  RESOLVED ({len(resolved)}):')
        for e in sorted(resolved, key=lambda x: x['outcome_date'] or '', reverse=True):
            prem = f"{e['premium_pct']:+.1f}%" if e.get('premium_pct') is not None else ''
            print(f"    {e['ticker']:<8} {e['outcome']:<16} "
                  f"{e.get('acquirer', ''):<20} {prem}")

    # Calibration stats
    stats = calibration_stats()
    if 'overall' in stats:
        ov = stats['overall']
        print(f'\n  CALIBRATION:')
        print(f"    Overall hit rate: {ov['hit_rate']:.1%}  "
              f"({ov['deals']}/{ov['total']} resolved deals)")
        if ov['avg_premium']:
            print(f"    Avg premium: {ov['avg_premium']:+.1f}%")
        for sq, s in stats.get('by_signal_quality', {}).items():
            print(f"    {sq:<12} hit={s['hit_rate']:.1%}  n={s['total']}"
                  + (f"  avg_prem={s['avg_premium']:+.1f}%" if s['avg_premium'] else ''))
    print()
