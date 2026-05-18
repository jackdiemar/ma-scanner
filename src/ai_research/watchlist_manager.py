"""
watchlist_manager.py — Manage the AI research watchlist.

Creates and updates data/ai_research/watchlist.json.
Each entry tracks per-ticker classification history, current status, and case path.

Statuses:
  active_watch   — signal is real, monitoring in progress
  escalated      — flagged for immediate human research
  discarded      — noise or resolved; no longer watching
  needs_review   — model uncertain; human must look
  stale          — not seen in N days; auto-archived
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

WATCHLIST_PATH = REPO / 'data' / 'ai_research' / 'watchlist.json'

_STATUS_FROM_ACTION = {
    'ESCALATE':           'escalated',
    'WATCH':              'active_watch',
    'WAIT_FOR_PRICE':     'active_watch',
    'DISCARD':            'discarded',
    'NEEDS_HUMAN_REVIEW': 'needs_review',
}

_KNOWN_STATUSES = frozenset({
    'active_watch', 'escalated', 'discarded', 'needs_review', 'stale',
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_watchlist() -> dict[str, Any]:
    """Load watchlist.json. Returns empty dict if missing or corrupt."""
    if not WATCHLIST_PATH.exists():
        return {}
    try:
        data = json.loads(WATCHLIST_PATH.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return data
    except Exception as exc:
        print(f'  [WARN] Could not load watchlist: {exc}', file=sys.stderr)
    return {}


def _save_watchlist(data: dict[str, Any]) -> None:
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_PATH.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')


# ── Per-entry schema ──────────────────────────────────────────────────────────

def _entry_status(research_action: str) -> str:
    return _STATUS_FROM_ACTION.get(research_action, 'active_watch')


def _new_entry(
    ticker: str,
    decision: dict,
    case: dict,
    case_path: str,
) -> dict:
    now = _utc_now_iso()
    return {
        'ticker':                 ticker,
        'company_name':           case.get('company_name', ''),
        'latest_classification':  decision.get('classification', ''),
        'latest_research_action': decision.get('research_action', ''),
        'confidence':             decision.get('confidence', 0.0),
        'investability_score':    decision.get('investability_score', 0),
        'first_seen':             case.get('first_seen', now),
        'last_seen':              now,
        'status':                 _entry_status(decision.get('research_action', '')),
        'reason_summary':         _build_reason_summary(decision),
        'source_url':             case.get('source_url', ''),
        'latest_case_path':       case_path,
        'history':                [],
    }


def _build_reason_summary(decision: dict) -> str:
    """One-sentence summary from the decision dict."""
    classification = decision.get('classification', '')
    why_interesting = decision.get('why_interesting', [])
    why_not = decision.get('why_not', [])
    note = decision.get('note', '')

    if note and note not in ('DRY_RUN',):
        return note

    parts: list[str] = [f'Classification: {classification}.']
    if why_interesting:
        parts.append(f'For: {why_interesting[0]}')
    if why_not:
        parts.append(f'Against: {why_not[0]}')
    return ' '.join(parts)


def _history_entry(entry: dict) -> dict:
    """Snapshot current state into a history record."""
    return {
        'recorded_at':       _utc_now_iso(),
        'classification':    entry.get('latest_classification', ''),
        'research_action':   entry.get('latest_research_action', ''),
        'confidence':        entry.get('confidence', 0.0),
        'investability_score': entry.get('investability_score', 0),
        'status':            entry.get('status', ''),
        'case_path':         entry.get('latest_case_path', ''),
    }


# ── WatchlistManager ──────────────────────────────────────────────────────────

class WatchlistManager:
    """
    Manages the per-ticker watchlist for AI research decisions.

    Immutable history: update() appends to history, never overwrites past entries.
    """

    def __init__(self, path: Path = WATCHLIST_PATH) -> None:
        self._path = path
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._data = {}
            return
        try:
            loaded = json.loads(self._path.read_text(encoding='utf-8'))
            self._data = loaded if isinstance(loaded, dict) else {}
        except Exception as exc:
            print(f'  [WARN] Watchlist load error: {exc}', file=sys.stderr)
            self._data = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2, default=str), encoding='utf-8')

    def update(self, ticker: str, decision: dict, case: dict, case_path: str) -> dict:
        """
        Insert or update a ticker's watchlist entry with a new AI decision.

        - Pushes the previous state to history before updating.
        - Does NOT mutate historical case files.

        Returns the updated entry dict.
        """
        ticker = ticker.upper().strip()

        if ticker in self._data:
            existing = self._data[ticker]
            # Archive current state to history before overwriting
            history = list(existing.get('history', []))
            history.append(_history_entry(existing))

            existing['latest_classification']  = decision.get('classification', '')
            existing['latest_research_action'] = decision.get('research_action', '')
            existing['confidence']             = decision.get('confidence', 0.0)
            existing['investability_score']    = decision.get('investability_score', 0)
            existing['last_seen']              = _utc_now_iso()
            existing['status']                 = _entry_status(decision.get('research_action', ''))
            existing['reason_summary']         = _build_reason_summary(decision)
            existing['source_url']             = case.get('source_url', '') or existing.get('source_url', '')
            existing['latest_case_path']       = case_path
            existing['history']                = history
            # Update company name if we have a better one
            if case.get('company_name'):
                existing['company_name'] = case['company_name']

            entry = existing
        else:
            entry = _new_entry(ticker, decision, case, case_path)

        self._data[ticker] = entry
        self._save()
        return entry

    def get(self, ticker: str) -> dict | None:
        """Return the watchlist entry for ticker, or None if not present."""
        return self._data.get(ticker.upper().strip())

    def get_all(self) -> dict[str, dict]:
        """Return a copy of the full watchlist."""
        return dict(self._data)

    def mark_stale(self, days: int = 14) -> list[str]:
        """
        Mark entries as 'stale' if they have not been updated in `days` days.
        Only marks active_watch and needs_review entries (not escalated/discarded).
        Returns list of tickers marked stale.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stale: list[str] = []

        for ticker, entry in self._data.items():
            if entry.get('status') not in ('active_watch', 'needs_review'):
                continue
            last_seen_raw = entry.get('last_seen', '')
            if not last_seen_raw:
                continue
            try:
                # Support both ISO format and our UTC string format
                last_seen = datetime.fromisoformat(last_seen_raw.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue
            if last_seen < cutoff:
                history = list(entry.get('history', []))
                history.append(_history_entry(entry))
                entry['history'] = history
                entry['status']  = 'stale'
                stale.append(ticker)

        if stale:
            self._save()
        return stale

    def summary(self) -> dict[str, int]:
        """Return counts by status."""
        counts: dict[str, int] = {s: 0 for s in _KNOWN_STATUSES}
        for entry in self._data.values():
            status = entry.get('status', 'active_watch')
            if status in counts:
                counts[status] += 1
            else:
                counts[status] = counts.get(status, 0) + 1
        counts['total'] = len(self._data)
        return counts

    def print_summary(self) -> None:
        s = self.summary()
        print('Watchlist Summary')
        print('-----------------')
        print(f'  Total          : {s["total"]}')
        print(f'  Escalated      : {s["escalated"]}')
        print(f'  Active watch   : {s["active_watch"]}')
        print(f'  Needs review   : {s["needs_review"]}')
        print(f'  Discarded      : {s["discarded"]}')
        print(f'  Stale          : {s["stale"]}')
