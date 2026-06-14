"""
paper_portfolio.py — Paper portfolio tracker for event-driven screener positions.

Opens a paper position on every AI ESCALATE decision.
Marks positions daily with current price from scan_latest.json.
Auto-closes at 90-day time stop or on deal announcement (MERGER signal).

Data file: data/paper_portfolio/portfolio.json

Config (.env):
  PAPER_PORTFOLIO_ENABLED=true        (default: false)
  PAPER_POSITION_SIZE_PCT=2.0         (default: 2.0%)
  PAPER_TIME_STOP_DAYS=90             (default: 90)

No auto-trading. No broker APIs. Research tracking only.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
REPO  = _HERE.parent

PORTFOLIO_PATH = REPO / 'data' / 'paper_portfolio' / 'portfolio.json'

STATUS_OPEN        = 'OPEN'
STATUS_TIME_STOP   = 'CLOSED_TIME_STOP'
STATUS_DEAL        = 'CLOSED_DEAL'
STATUS_THESIS_BREAK = 'CLOSED_THESIS_BREAK'
STATUS_DUPLICATE   = 'DUPLICATE'


# ── Config ────────────────────────────────────────────────────────────────────

def _enabled() -> bool:
    return os.environ.get('PAPER_PORTFOLIO_ENABLED', 'false').strip().lower() in {'1', 'true', 'yes'}

def _position_size() -> float:
    try:
        return float(os.environ.get('PAPER_POSITION_SIZE_PCT', '2.0'))
    except ValueError:
        return 2.0

def _time_stop_days() -> int:
    try:
        return int(os.environ.get('PAPER_TIME_STOP_DAYS', '90'))
    except ValueError:
        return 90


# ── Persistence ───────────────────────────────────────────────────────────────

def load_portfolio() -> dict[str, Any]:
    if not PORTFOLIO_PATH.exists():
        return {}
    try:
        data = json.loads(PORTFOLIO_PATH.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_portfolio(portfolio: dict[str, Any]) -> None:
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_PATH.write_text(
        json.dumps(portfolio, indent=2, default=str),
        encoding='utf-8',
    )


# ── Core operations ───────────────────────────────────────────────────────────

def open_position(
    ticker: str,
    entry_price: float,
    signal_date: str,
    signal_quality: str,
    ai_classification: str,
    ai_confidence: float,
    portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Open a paper position. If ticker already has OPEN position, skip.
    Returns the (possibly existing) portfolio dict.
    """
    if portfolio is None:
        portfolio = load_portfolio()

    ticker = ticker.upper().strip()
    existing = portfolio.get(ticker)
    if existing and existing.get('status') == STATUS_OPEN:
        print(f'  [PORTFOLIO] {ticker}: already open — skipping duplicate')
        return portfolio

    now     = datetime.now(timezone.utc)
    size    = _position_size()
    stop_dt = now + timedelta(days=_time_stop_days())

    portfolio[ticker] = {
        'ticker':             ticker,
        'signal_date':        signal_date,
        'signal_quality':     signal_quality,
        'ai_classification':  ai_classification,
        'ai_confidence':      round(ai_confidence, 2),
        'entry_price':        round(entry_price, 4) if entry_price else None,
        'entry_date':         now.date().isoformat(),
        'position_size_pct':  size,
        'time_stop_date':     stop_dt.date().isoformat(),
        'status':             STATUS_OPEN,
        'last_price':         round(entry_price, 4) if entry_price else None,
        'last_updated':       now.isoformat(),
        'unrealized_pct':     0.0,
        'days_held':          0,
        'days_remaining':     _time_stop_days(),
        'closed_date':        None,
        'closed_price':       None,
        'realized_pct':       None,
        'close_reason':       None,
    }

    print(f'  [PORTFOLIO] Opened: {ticker} @ ${entry_price:.2f} | {size}% | stop {stop_dt.date()}')
    return portfolio


def mark_positions(
    scan_results: list[dict],
    portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Update all OPEN positions with latest price from scan_results.
    Auto-close on time stop or deal announcement (MERGER signal).
    Call this after every scanner run.
    """
    if portfolio is None:
        portfolio = load_portfolio()

    if not portfolio:
        return portfolio

    now = datetime.now(timezone.utc).date()

    # Build price + signal_quality lookup from scan
    price_map: dict[str, float]  = {}
    merger_set: set[str]         = set()
    for row in scan_results:
        t  = str(row.get('ticker', '')).upper()
        sq = str(row.get('signal_quality', '')).upper()
        p  = row.get('price')
        if t and p:
            try:
                price_map[t] = float(p)
            except (TypeError, ValueError):
                pass
        if sq == 'MERGER':
            merger_set.add(t)

    changed = False
    for ticker, pos in portfolio.items():
        if pos.get('status') != STATUS_OPEN:
            continue

        current_price = price_map.get(ticker)
        entry_price   = pos.get('entry_price')
        stop_date_str = pos.get('time_stop_date', '')
        entry_date_str = pos.get('entry_date', '')

        # Compute days held / remaining
        try:
            entry_dt  = datetime.fromisoformat(entry_date_str).date() if entry_date_str else now
            stop_dt   = datetime.fromisoformat(stop_date_str).date() if stop_date_str else now
            days_held = (now - entry_dt).days
            days_rem  = (stop_dt - now).days
        except ValueError:
            days_held = 0
            days_rem  = _time_stop_days()

        # Update price + unrealized
        if current_price and entry_price:
            unrealized = ((current_price - entry_price) / entry_price) * 100
            pos['last_price']     = round(current_price, 4)
            pos['unrealized_pct'] = round(unrealized, 2)
        pos['last_updated'] = datetime.now(timezone.utc).isoformat()
        pos['days_held']     = days_held
        pos['days_remaining'] = max(days_rem, 0)
        changed = True

        # Auto-close: deal announced
        if ticker in merger_set:
            pos['status']       = STATUS_DEAL
            pos['closed_date']  = now.isoformat()
            pos['closed_price'] = current_price
            pos['close_reason'] = 'MERGER signal detected in scanner'
            if current_price and entry_price:
                pos['realized_pct'] = round(((current_price - entry_price) / entry_price) * 100, 2)
            print(f'  [PORTFOLIO] DEAL: {ticker} closed @ ${current_price} | {pos.get("realized_pct",0):+.1f}%')
            continue

        # Auto-close: time stop
        if days_rem <= 0:
            pos['status']       = STATUS_TIME_STOP
            pos['closed_date']  = now.isoformat()
            pos['closed_price'] = current_price
            pos['close_reason'] = '90-day time stop'
            if current_price and entry_price:
                pos['realized_pct'] = round(((current_price - entry_price) / entry_price) * 100, 2)
            print(f'  [PORTFOLIO] STOP: {ticker} closed @ ${current_price} | {pos.get("realized_pct",0):+.1f}%')

    if changed:
        save_portfolio(portfolio)
    return portfolio


def close_position(
    ticker: str,
    reason: str = STATUS_THESIS_BREAK,
    portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Manually close a position (thesis break or override)."""
    if portfolio is None:
        portfolio = load_portfolio()
    ticker = ticker.upper()
    pos = portfolio.get(ticker)
    if not pos or pos.get('status') != STATUS_OPEN:
        print(f'  [PORTFOLIO] {ticker}: no open position to close')
        return portfolio
    now   = datetime.now(timezone.utc).date()
    price = pos.get('last_price') or pos.get('entry_price')
    entry = pos.get('entry_price')
    pos['status']       = reason
    pos['closed_date']  = now.isoformat()
    pos['closed_price'] = price
    pos['close_reason'] = reason
    if price and entry:
        pos['realized_pct'] = round(((price - entry) / entry) * 100, 2)
    save_portfolio(portfolio)
    print(f'  [PORTFOLIO] Closed {ticker}: {reason} | {pos.get("realized_pct",0):+.1f}%')
    return portfolio


# ── Summary ───────────────────────────────────────────────────────────────────

def get_summary(portfolio: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Return portfolio summary dict for email and status display.
    """
    if portfolio is None:
        portfolio = load_portfolio()

    open_positions = [p for p in portfolio.values() if p.get('status') == STATUS_OPEN]
    closed = [p for p in portfolio.values() if p.get('status') != STATUS_OPEN]

    deals      = [p for p in closed if p.get('status') == STATUS_DEAL]
    time_stops = [p for p in closed if p.get('status') == STATUS_TIME_STOP]
    breaks     = [p for p in closed if p.get('status') == STATUS_THESIS_BREAK]

    realized   = [p['realized_pct'] for p in closed if p.get('realized_pct') is not None]
    wins       = [r for r in realized if r > 0]
    losses     = [r for r in realized if r <= 0]

    deployed_pct  = sum(p.get('position_size_pct', 0) for p in open_positions)
    unrealized_weighted = (
        sum(p.get('unrealized_pct', 0) * p.get('position_size_pct', 0) for p in open_positions)
        / deployed_pct if deployed_pct else 0
    )

    return {
        'open':              sorted(open_positions, key=lambda p: p.get('entry_date', ''), reverse=True),
        'closed_recent':     sorted(closed, key=lambda p: p.get('closed_date', ''), reverse=True)[:10],
        'total_open':        len(open_positions),
        'total_closed':      len(closed),
        'total_deals':       len(deals),
        'total_time_stops':  len(time_stops),
        'total_breaks':      len(breaks),
        'deployed_pct':      round(deployed_pct, 1),
        'unrealized_weighted_pct': round(unrealized_weighted, 2),
        'avg_realized_pct':  round(sum(realized) / len(realized), 2) if realized else None,
        'win_rate_pct':      round(len(wins) / len(realized) * 100, 1) if realized else None,
        'avg_win_pct':       round(sum(wins) / len(wins), 2) if wins else None,
        'avg_loss_pct':      round(sum(losses) / len(losses), 2) if losses else None,
    }
