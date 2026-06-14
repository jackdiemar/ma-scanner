"""
opportunity_selector.py — Select and rank cases for the AI email.

Prevents the email from being dominated by repeated already-announced DISCARD cases.
Applies the suppression registry and change detector to build a priority queue.

Priority tiers:
  P0_ESCALATE_NOW     — ESCALATE action
  P1_HUMAN_REVIEW     — NEEDS_HUMAN_REVIEW action
  P2_WATCHLIST_SETUP  — WATCH/WAIT_FOR_PRICE on new or changed evidence
  P3_MONITOR_CHANGE   — WATCH on unchanged or changed DISCARD
  P4_SUPPRESSED       — Repeated DISCARD with no change

Output files:
  data/ai_research/latest_opportunity_queue.json
  data/ai_research/latest_opportunity_queue.md
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

from ai_research.suppression_registry import check_suppressed
from ai_research.change_detector import (
    classify_change,
    NEW_CASE, CHANGED_EVIDENCE, CHANGED_SOURCE, CHANGED_DECISION,
    UNCHANGED_SUPPRESSED, UNCHANGED_ACTIVE,
)

AI_RESEARCH_DIR = REPO / 'data' / 'ai_research'
QUEUE_JSON_PATH = AI_RESEARCH_DIR / 'latest_opportunity_queue.json'
QUEUE_MD_PATH   = AI_RESEARCH_DIR / 'latest_opportunity_queue.md'

P0_ESCALATE_NOW    = 'P0_ESCALATE_NOW'
P1_HUMAN_REVIEW    = 'P1_HUMAN_REVIEW'
P2_WATCHLIST_SETUP = 'P2_WATCHLIST_SETUP'
P3_MONITOR_CHANGE  = 'P3_MONITOR_CHANGE'
P4_SUPPRESSED      = 'P4_SUPPRESSED_DISCARD'

ALL_TIERS = (P0_ESCALATE_NOW, P1_HUMAN_REVIEW, P2_WATCHLIST_SETUP, P3_MONITOR_CHANGE, P4_SUPPRESSED)
ACTIVE_TIERS = (P0_ESCALATE_NOW, P1_HUMAN_REVIEW, P2_WATCHLIST_SETUP, P3_MONITOR_CHANGE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assign_priority(decision: dict, change_status: str) -> str:
    action = decision.get('research_action', '')

    if action == 'ESCALATE':
        return P0_ESCALATE_NOW

    if action == 'NEEDS_HUMAN_REVIEW':
        return P1_HUMAN_REVIEW

    if action in ('WATCH', 'WAIT_FOR_PRICE', 'WATCH_ONLY'):
        if change_status in (NEW_CASE, CHANGED_EVIDENCE, CHANGED_SOURCE, CHANGED_DECISION, UNCHANGED_ACTIVE):
            return P2_WATCHLIST_SETUP
        return P3_MONITOR_CHANGE

    # DISCARD — only P3 if changed, else P4
    if change_status in (CHANGED_EVIDENCE, CHANGED_SOURCE, CHANGED_DECISION):
        return P3_MONITOR_CHANGE

    return P4_SUPPRESSED


def build_opportunity_queue(
    decisions: list[dict],
    cases: list[dict],
    registry: dict[str, Any],
    watchlist: dict[str, Any],
    max_suppressed_summary: int = 5,
    include_suppressed: bool = False,
) -> dict[str, Any]:
    """
    Build a priority-sorted opportunity queue from decisions + registry.

    Returns structured dict with priority tiers and summary stats.
    """
    case_by_ticker: dict[str, dict] = {
        str(c.get('ticker', '')).upper(): c for c in (cases or [])
    }

    queues: dict[str, list[dict]] = {t: [] for t in ALL_TIERS}

    # Load signal strength scorer if available
    try:
        from ai_research.pre_gate_filter import compute_signal_strength_score as _sss
    except Exception:
        _sss = lambda c: c.get('_signal_strength_score', 50)  # noqa: E731

    for decision in decisions:
        ticker = str(decision.get('ticker', '')).upper()
        case   = case_by_ticker.get(ticker, {})

        change_status, change_detail = classify_change(case, registry, watchlist)
        is_suppressed, suppress_reason = check_suppressed(ticker, case, registry)

        priority = _assign_priority(decision, change_status)
        signal_strength = _sss(case)

        # Suppress if unchanged regardless of other signals
        if is_suppressed and change_status == UNCHANGED_SUPPRESSED:
            priority = P4_SUPPRESSED

        entry = {
            'ticker':           ticker,
            'company_name':     decision.get('company_name', '') or case.get('company_name', ''),
            'priority':         priority,
            'action':           decision.get('research_action', ''),
            'classification':   decision.get('classification', ''),
            'confidence':       decision.get('confidence', 0.0),
            'score':            decision.get('investability_score', 0),
            'signal_strength':  signal_strength,
            'evidence_grade':   decision.get('evidence_grade', 'F'),
            'change_status':    change_status,
            'change_detail':    change_detail,
            'is_suppressed':    is_suppressed,
            'suppress_reason':  suppress_reason,
            # Connectivity fields — SA/banker/distress context in queue
            'sa_type':          case.get('sa_type', ''),
            'banker_mandate':   case.get('banker_mandate_type', ''),
            'banker_strength':  case.get('banker_mandate_strength', ''),
            'distress_severity': case.get('distress_severity', ''),
            'distress_driven':  case.get('distress_driven_sa', False),
        }

        queues[priority].append(entry)

    # Sort within each active tier: signal_strength DESC, then score DESC
    for tier in (P0_ESCALATE_NOW, P1_HUMAN_REVIEW, P2_WATCHLIST_SETUP, P3_MONITOR_CHANGE):
        queues[tier].sort(key=lambda e: (e.get('signal_strength', 0), e.get('score', 0)), reverse=True)

    suppressed_all = list(queues[P4_SUPPRESSED])
    total_suppressed = len(suppressed_all)

    if not include_suppressed:
        queues[P4_SUPPRESSED] = suppressed_all[:max_suppressed_summary]

    total_active = sum(len(queues[t]) for t in ACTIVE_TIERS)
    no_opportunity = (total_active == 0 and total_suppressed > 0)

    return {
        'built_at':               _utc_now(),
        'total_decisions':        len(decisions),
        'total_active':           total_active,
        'total_suppressed':       total_suppressed,
        'total_suppressed_full':  total_suppressed,
        'no_opportunity':         no_opportunity,
        P0_ESCALATE_NOW:          queues[P0_ESCALATE_NOW],
        P1_HUMAN_REVIEW:          queues[P1_HUMAN_REVIEW],
        P2_WATCHLIST_SETUP:       queues[P2_WATCHLIST_SETUP],
        P3_MONITOR_CHANGE:        queues[P3_MONITOR_CHANGE],
        P4_SUPPRESSED:            queues[P4_SUPPRESSED],
    }


def save_opportunity_queue(queue: dict) -> None:
    """Write queue to JSON and Markdown."""
    AI_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_JSON_PATH.write_text(
        json.dumps(queue, indent=2, default=str),
        encoding='utf-8',
    )

    tier_labels = {
        P0_ESCALATE_NOW:    '## P0 — Escalate Now',
        P1_HUMAN_REVIEW:    '## P1 — Human Review',
        P2_WATCHLIST_SETUP: '## P2 — Watchlist Setup',
        P3_MONITOR_CHANGE:  '## P3 — Monitor for Change',
        P4_SUPPRESSED:      '## P4 — Suppressed Discards (sample)',
    }

    lines = [
        '# MA Scanner — Opportunity Queue',
        '',
        f'Built: {queue.get("built_at", "")}',
        '',
        '| Metric | Value |',
        '|---|---|',
        f'| Total decisions | {queue.get("total_decisions", 0)} |',
        f'| Active (P0–P3) | {queue.get("total_active", 0)} |',
        f'| Suppressed | {queue.get("total_suppressed_full", 0)} |',
        f'| No opportunity | {queue.get("no_opportunity", False)} |',
        '',
    ]

    for tier, label in tier_labels.items():
        entries = queue.get(tier, [])
        lines.append(label)
        lines.append('')
        if not entries:
            lines.append('_None_')
        else:
            for e in entries:
                line = (
                    f'- **{e["ticker"]}** | {e["action"]} | {e["classification"]} | '
                    f'grade={e["evidence_grade"]} | change={e["change_status"]}'
                )
                if e.get('is_suppressed'):
                    line += f' | suppress={e["suppress_reason"]}'
                lines.append(line)
        lines.append('')

    QUEUE_MD_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f'  [QUEUE] Written: {QUEUE_JSON_PATH.name} + {QUEUE_MD_PATH.name}')


def split_decisions_by_queue(
    queue: dict,
    decisions: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Split decisions into (active, suppressed) based on the opportunity queue.
    Active = P0/P1/P2/P3. Suppressed = P4.
    """
    active_tickers: set[str] = set()
    for tier in ACTIVE_TIERS:
        for e in queue.get(tier, []):
            active_tickers.add(str(e['ticker']).upper())

    active    = [d for d in decisions if str(d.get('ticker', '')).upper() in active_tickers]
    suppressed = [d for d in decisions if str(d.get('ticker', '')).upper() not in active_tickers]
    return active, suppressed


def print_opportunity_plan(
    cases: list[dict],
    registry: dict[str, Any],
    watchlist: dict[str, Any],
) -> None:
    """Print what cases would be selected/suppressed without running LLM."""
    print('Opportunity Plan (no LLM calls made)')
    print('=====================================')
    print(f'  Cases available : {len(cases)}')
    print()

    for case in cases:
        ticker = str(case.get('ticker', '?')).upper()
        change_status, change_detail = classify_change(case, registry, watchlist)
        is_supp, supp_reason = check_suppressed(ticker, case, registry)

        if is_supp and change_status == UNCHANGED_SUPPRESSED:
            label = 'SKIP (suppressed+unchanged) — LLM would NOT be called'
        elif change_status in (CHANGED_EVIDENCE, CHANGED_SOURCE, CHANGED_DECISION):
            label = f'INCLUDE ({change_status}) — LLM would be called'
        elif change_status == NEW_CASE:
            label = 'INCLUDE (new case) — LLM would be called'
        elif change_status == UNCHANGED_ACTIVE:
            label = 'INCLUDE (active watchlist) — LLM would be called'
        else:
            label = f'INCLUDE ({change_status}) — LLM would be called'

        record = registry.get(ticker, {})
        times  = record.get('times_seen', 0)
        print(f'  {ticker:<8} {label}')
        if is_supp:
            print(f'          → suppress_reason={supp_reason}  times_seen={times}')

    print()
