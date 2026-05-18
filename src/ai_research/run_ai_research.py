"""
run_ai_research.py — Main CLI orchestrator for the AI research layer.

Usage:
  python3 src/ai_research/run_ai_research.py --latest --limit 5
  python3 src/ai_research/run_ai_research.py --latest --dry-run
  python3 src/ai_research/run_ai_research.py --ticker SDGR
  python3 src/ai_research/run_ai_research.py --status

Behavior:
  - Builds research cases from latest scanner outputs.
  - If AI_RESEARCH_ENABLED=false or key missing: builds cases, skips LLM, prints status.
  - If AI enabled and not dry-run: runs investment gate on up to limit cases.
  - Saves JSON decisions into case files.
  - Updates watchlist.
  - Writes data/ai_research/latest_ai_research_summary.md.

No auto-trading. No broker APIs. No BUY/SELL language.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

ENV_FILE         = REPO / 'config' / '.env'
AI_RESEARCH_DIR  = REPO / 'data' / 'ai_research'
CASES_BASE_DIR   = AI_RESEARCH_DIR / 'cases'
WATCHLIST_PATH   = AI_RESEARCH_DIR / 'watchlist.json'
SUMMARY_PATH     = AI_RESEARCH_DIR / 'latest_ai_research_summary.md'

# Ensure src/ is on sys.path for direct script execution and relative imports
if str(_SRCDIR) not in sys.path:
    sys.path.insert(0, str(_SRCDIR))


# ── Env loader ────────────────────────────────────────────────────────────────

def _load_env() -> None:
    if not ENV_FILE.exists():
        return
    with ENV_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


# ── Summary writer ────────────────────────────────────────────────────────────

def _write_summary(
    run_at: str,
    cases: list[dict],
    decisions: list[dict],
    dry_run: bool,
    ai_enabled: bool,
    watchlist_summary: dict,
) -> None:
    AI_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        '# AI Research Layer — Latest Run Summary',
        '',
        f'**Run at:** {run_at}  ',
        f'**AI enabled:** {ai_enabled}  ',
        f'**Dry run:** {dry_run}  ',
        f'**Cases built:** {len(cases)}  ',
        f'**Decisions made:** {len(decisions)}  ',
        '',
        '---',
        '',
        '## Watchlist Summary',
        '',
        f'| Status | Count |',
        f'|---|---|',
        f'| Total | {watchlist_summary.get("total", 0)} |',
        f'| Escalated | {watchlist_summary.get("escalated", 0)} |',
        f'| Active watch | {watchlist_summary.get("active_watch", 0)} |',
        f'| Needs review | {watchlist_summary.get("needs_review", 0)} |',
        f'| Discarded | {watchlist_summary.get("discarded", 0)} |',
        f'| Stale | {watchlist_summary.get("stale", 0)} |',
        '',
        '---',
        '',
    ]

    if decisions:
        lines += ['## Decisions This Run', '']
        for d in decisions:
            ticker = d.get('ticker', '?')
            cls    = d.get('classification', '?')
            action = d.get('research_action', '?')
            conf   = d.get('confidence', 0.0)
            score  = d.get('investability_score', 0)
            note   = d.get('note', '')
            lines.append(
                f'- **{ticker}** → {cls} | action={action} | '
                f'confidence={conf:.2f} | score={score}'
                + (f' _{note}_' if note else '')
            )
        lines.append('')
    elif cases:
        lines += [
            '## Cases Built (No AI Run)',
            '',
            '_AI research was disabled or dry-run active. Cases were built but LLM gate was not run._',
            '',
        ]
        for c in cases:
            ticker = c.get('ticker', '?')
            action = c.get('recommended_scanner_action', '?')
            sq     = c.get('signal_quality', '?')
            lines.append(f'- **{ticker}** | {sq} | scanner action: {action}')
        lines.append('')
    else:
        lines += ['_No cases built this run._', '']

    lines += [
        '---',
        '',
        '_This summary is for research tracking only. '
        'Nothing here constitutes investment advice or a recommendation to trade any security._',
    ]
    SUMMARY_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f'  [WROTE] {SUMMARY_PATH.relative_to(REPO)}')


# ── Case file updater ─────────────────────────────────────────────────────────

def _inject_decision_into_case_file(case_path: Path, decision: dict) -> None:
    """
    Write the AI decision into the case JSON file.
    Only updates ai_decision and ai_run_at fields — does not mutate the original case data.
    Historical case files are never mutated (only today's run date cases are updated).
    """
    if not case_path.exists():
        return
    try:
        case = json.loads(case_path.read_text(encoding='utf-8'))
    except Exception:
        return
    case['ai_decision'] = decision
    case['ai_run_at']   = _utc_now()
    case_path.write_text(json.dumps(case, indent=2, default=str), encoding='utf-8')


# ── Main run ──────────────────────────────────────────────────────────────────

def run(
    ticker: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    run_date: str | None = None,
) -> int:
    """
    Main execution: build cases, optionally run gate, update watchlist, write summary.
    Returns exit code (0 = success).
    """
    _load_env()
    run_at   = _utc_now()
    run_date = run_date or _today_utc()

    from ai_research.llm_client import LLMClient, load_config as load_llm_config
    from ai_research.research_case_builder import build_cases
    from ai_research.investment_gate import run_gate
    from ai_research.watchlist_manager import WatchlistManager

    llm_cfg    = load_llm_config()
    ai_enabled = llm_cfg.enabled and bool(llm_cfg.api_key)

    # Dry-run override: flag on CLI takes precedence; else use config
    effective_dry_run = dry_run or llm_cfg.dry_run

    print('AI Research Layer')
    print('=================')
    print(f'Run at      : {run_at}')
    print(f'AI enabled  : {ai_enabled}')
    print(f'Dry run     : {effective_dry_run}')
    print(f'Limit       : {limit or "none"}')
    print(f'Ticker      : {ticker or "all (from latest)"}')
    print()

    # ── 1. Build research cases ──────────────────────────────────────────────
    print('Step 1: Building research cases …')
    cases = build_cases(
        ticker   = ticker,
        limit    = limit,
        run_date = run_date,
        dry_run  = False,  # always write case files even if AI is off
    )
    print(f'Built {len(cases)} case(s).')
    print()

    if not cases:
        print('[INFO] No cases to process. Exiting.')
        _write_summary(
            run_at            = run_at,
            cases             = cases,
            decisions         = [],
            dry_run           = effective_dry_run,
            ai_enabled        = ai_enabled,
            watchlist_summary = {},
        )
        return 0

    # ── 2. Run investment gate ───────────────────────────────────────────────
    decisions: list[dict] = []
    wm = WatchlistManager(WATCHLIST_PATH)

    if not ai_enabled:
        print('Step 2: AI layer disabled — skipping LLM gate.')
        print(f'  Reason: {LLMClient(llm_cfg).status_message}')
        print()
    else:
        cap = llm_cfg.max_cases_per_run
        gate_cases = cases[:cap] if limit is None else cases
        print(f'Step 2: Running investment gate on {len(gate_cases)} case(s) …')
        if effective_dry_run:
            print('  (dry-run — LLM will not be called)')
        print()

        client = LLMClient(llm_cfg)

        for case in gate_cases:
            t = case.get('ticker', 'UNKNOWN')
            decision = run_gate(case, client=client, dry_run=effective_dry_run)
            decisions.append(decision)

            # Locate case JSON on disk to inject decision
            case_json_path = CASES_BASE_DIR / run_date / f'{t}_research_case.json'
            if case_json_path.exists():
                _inject_decision_into_case_file(case_json_path, decision)

            # Update watchlist
            wm.update(
                ticker    = t,
                decision  = decision,
                case      = case,
                case_path = str(case_json_path),
            )

        print()
        print(f'Gate complete: {len(decisions)} decision(s) made.')
        print()

    # ── 3. Mark stale entries ────────────────────────────────────────────────
    stale = wm.mark_stale(days=14)
    if stale:
        print(f'  Marked {len(stale)} watchlist entries as stale: {", ".join(stale)}')

    # ── 4. Print watchlist summary ───────────────────────────────────────────
    watchlist_summary = wm.summary()
    print('Watchlist after this run:')
    wm.print_summary()
    print()

    # ── 5. Write summary markdown ────────────────────────────────────────────
    _write_summary(
        run_at            = run_at,
        cases             = cases,
        decisions         = decisions,
        dry_run           = effective_dry_run,
        ai_enabled        = ai_enabled,
        watchlist_summary = watchlist_summary,
    )

    return 0


# ── Plan command ─────────────────────────────────────────────────────────────

def print_plan(ticker: str | None = None, limit: int | None = None) -> None:
    """
    Preview what would run — no files written, no LLM calls.
    Shows case count, alert sources, and AI gate config.
    """
    _load_env()
    from ai_research.llm_client import LLMClient, load_config as load_llm_config
    from ai_research.research_case_builder import (
        _load_alerts_from_json, _load_alerts_from_csv,
    )

    llm_cfg = load_llm_config()
    ai_enabled = llm_cfg.enabled and bool(llm_cfg.api_key)

    # Load alerts (mirrors build_cases logic, no file writes)
    if ticker:
        alerts_json = _load_alerts_from_json()
        alerts = [a for a in alerts_json if str(a.get('ticker', '')).strip() == ticker]
        if not alerts:
            alerts = _load_alerts_from_csv(ticker=ticker)
    else:
        alerts = _load_alerts_from_json()
        if not alerts:
            alerts = _load_alerts_from_csv()

    if limit:
        alerts = alerts[:limit]

    cap = llm_cfg.max_cases_per_run
    gate_count = min(len(alerts), cap) if not limit else len(alerts)

    print('AI Research Layer — Plan Preview')
    print('=================================')
    print(f'  Ticker filter   : {ticker or "all"}')
    print(f'  Alerts found    : {len(alerts)}')
    print(f'  Limit flag      : {limit or "none"}')
    print(f'  AI enabled      : {ai_enabled}')
    print(f'  Model           : {llm_cfg.model}')
    print(f'  Max cases/run   : {cap}')
    print(f'  Cases to gate   : {gate_count if ai_enabled else 0} ({"AI disabled" if not ai_enabled else "AI enabled"})')
    print(f'  Dry run config  : {llm_cfg.dry_run}')
    print()

    if alerts:
        print('  Tickers (by priority):')
        for a in alerts[:20]:
            t = str(a.get('ticker', '?')).strip()
            cls = str(a.get('fp_classification', '?')).strip()
            action = str(a.get('recommended_action', '?')).strip()
            print(f'    {t:<8} {cls:<30} {action}')
        if len(alerts) > 20:
            print(f'    ... and {len(alerts) - 20} more')
    else:
        print('  No alerts found — run scanner first.')

    print()
    print('  Run with --latest (--limit N) to execute.')


# ── Status command ────────────────────────────────────────────────────────────

def print_status() -> None:
    _load_env()
    from ai_research.llm_client import LLMClient, load_config as load_llm_config
    from ai_research.watchlist_manager import WatchlistManager

    llm_cfg = load_llm_config()
    client  = LLMClient(llm_cfg)
    wm      = WatchlistManager(WATCHLIST_PATH)

    print('AI Research Layer — Status')
    print('==========================')
    print(f'  Config .env exists : {ENV_FILE.exists()}')
    print(f'  AI_RESEARCH_ENABLED: {llm_cfg.enabled}')
    print(f'  API key set        : {bool(llm_cfg.api_key)}')
    print(f'  Model              : {llm_cfg.model}')
    print(f'  Max cases/run      : {llm_cfg.max_cases_per_run}')
    print(f'  Dry run (config)   : {llm_cfg.dry_run}')
    print(f'  LLM client status  : {client.status_message}')
    print(f'  Watchlist path     : {WATCHLIST_PATH}')
    print(f'  Summary path       : {SUMMARY_PATH}')
    print()
    wm.print_summary()

    if SUMMARY_PATH.exists():
        print()
        print(f'Last summary: {SUMMARY_PATH}')


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description='AI research layer orchestrator — research gate, not trading signal.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--latest', action='store_true',
                      help='Build cases + run gate from latest scanner outputs')
    mode.add_argument('--ticker', metavar='TICKER',
                      help='Run for a single ticker')
    mode.add_argument('--status', action='store_true',
                      help='Print current watchlist + config summary')
    mode.add_argument('--plan', action='store_true',
                      help='Preview what would run — no files written, no LLM calls')

    p.add_argument('--limit',   type=int, default=None,
                   help='Max cases to process (default: AI_RESEARCH_MAX_CASES_PER_RUN)')
    p.add_argument('--dry-run', action='store_true',
                   help='Build cases but do not call LLM')
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)

    if args.status:
        print_status()
        return 0

    if args.plan:
        ticker = args.ticker.upper() if args.ticker else None
        print_plan(ticker=ticker, limit=args.limit)
        return 0

    ticker = args.ticker.upper() if args.ticker else None
    return run(
        ticker   = ticker,
        limit    = args.limit,
        dry_run  = args.dry_run,
    )


if __name__ == '__main__':
    sys.exit(main())
