"""
run_ai_research.py — Main CLI orchestrator for the AI research layer.

Usage:
  python3 src/ai_research/run_ai_research.py --latest --limit 5
  python3 src/ai_research/run_ai_research.py --latest --limit 5 --plan
  python3 src/ai_research/run_ai_research.py --latest --dry-run
  python3 src/ai_research/run_ai_research.py --latest --limit 10 --depth fast_gate --email
  python3 src/ai_research/run_ai_research.py --latest --limit 5 --force-refresh
  python3 src/ai_research/run_ai_research.py --ticker SDGR
  python3 src/ai_research/run_ai_research.py --status
  python3 src/ai_research/run_ai_research.py --email-latest-summary

Behavior:
  - Builds research cases from latest scanner outputs.
  - Dry-run builds cases and validates schema without calling the LLM.
  - Live runs require AI_RESEARCH_ENABLED=true and OPENAI_API_KEY.
  - If AI enabled and not dry-run: runs investment gate on up to limit cases.
  - Saves JSON decisions into case files.
  - Updates watchlist.
  - Writes data/ai_research/latest_ai_research_summary.md.
  - Optionally sends branded HTML research email via --email.
  - --force-refresh bypasses the fingerprint cache and reruns LLM.

No auto-trading. No broker APIs. No transaction recommendation language.
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
CACHE_DIR        = AI_RESEARCH_DIR / 'cache'
WATCHLIST_PATH   = AI_RESEARCH_DIR / 'watchlist.json'
SUMMARY_PATH     = AI_RESEARCH_DIR / 'latest_ai_research_summary.md'
LIVE_DATA        = REPO / 'data' / 'live_monitoring'
LATEST_ALERTS    = LIVE_DATA / 'latest_alerts.json'
ALERT_LOG        = LIVE_DATA / 'live_alert_log.csv'

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


def _bool_text(value: bool) -> str:
    return 'true' if value else 'false'


def _load_json_file(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None


def _alert_count_available() -> tuple[int, str]:
    data = _load_json_file(LATEST_ALERTS)
    if isinstance(data, dict):
        return len(data), str(LATEST_ALERTS)
    if ALERT_LOG.exists():
        try:
            with ALERT_LOG.open(encoding='utf-8') as fh:
                rows = max(sum(1 for _ in fh) - 1, 0)
            return rows, str(ALERT_LOG)
        except OSError:
            return 0, str(ALERT_LOG)
    return 0, str(LATEST_ALERTS)


def _scanner_output_status() -> str:
    if LATEST_ALERTS.exists():
        return f'found ({LATEST_ALERTS})'
    if ALERT_LOG.exists():
        return f'found fallback ({ALERT_LOG})'
    return f'missing ({LATEST_ALERTS})'


def _live_call_allowed_reason(cfg) -> tuple[bool, str]:
    if not cfg.enabled:
        return False, 'AI_RESEARCH_ENABLED=false'
    if cfg.dry_run:
        return False, 'AI_RESEARCH_DRY_RUN=true'
    if not cfg.api_key:
        return False, 'OPENAI_API_KEY not set'
    return True, 'enabled, dry-run off, key set'


def _case_json_path(run_date: str, ticker: str) -> Path:
    return CASES_BASE_DIR / run_date / f'{ticker}_research_case.json'


def _validate_cases(cases: list[dict]) -> list[str]:
    from ai_research.research_case_builder import validate_case_schema

    errors: list[str] = []
    for case in cases:
        ticker = case.get('ticker', 'UNKNOWN')
        for err in validate_case_schema(case):
            errors.append(f'{ticker}: {err}')
    return errors


def _validate_decisions(decisions: list[dict]) -> list[str]:
    from ai_research.investment_gate import validate_decision_schema

    errors: list[str] = []
    for decision in decisions:
        ticker = decision.get('ticker', 'UNKNOWN')
        for err in validate_decision_schema(decision):
            errors.append(f'{ticker}: {err}')
    return errors


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
        '# AI Research Layer - Latest Run Summary',
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
    depth: str | None = None,
    run_date: str | None = None,
    force_refresh: bool = False,
    send_email: bool = False,
) -> int:
    """
    Main execution: build cases, optionally run gate, update watchlist, write summary.

    Args:
        ticker:        Run for a single ticker instead of latest alerts.
        limit:         Max cases to process.
        dry_run:       Skip LLM calls; return placeholder decisions.
        depth:         Research depth preset (fast_gate, deep).
        run_date:      Override the run date (YYYY-MM-DD).
        force_refresh: Bypass cache and rerun LLM for every case.
        send_email:    Send branded AI research email after run completes.

    Returns:
        Exit code (0 = success).
    """
    _load_env()
    run_at   = _utc_now()
    run_date = run_date or _today_utc()

    from ai_research.llm_client import LLMClient, load_config as load_llm_config
    from ai_research.research_case_builder import build_cases
    from ai_research.investment_gate import run_gate
    from ai_research.watchlist_manager import WatchlistManager

    llm_cfg    = load_llm_config()
    ai_ready   = llm_cfg.ready

    # Dry-run override: flag on CLI takes precedence; else use config
    effective_dry_run = dry_run or llm_cfg.dry_run
    depth = depth or llm_cfg.default_depth

    if not effective_dry_run:
        blockers: list[str] = []
        if not llm_cfg.enabled:
            blockers.append('AI_RESEARCH_ENABLED=false')
        if not llm_cfg.api_key:
            blockers.append('OPENAI_API_KEY is not set')
        if blockers:
            print('AI Research Layer')
            print('=================')
            print('ERROR: Live LLM run is not allowed.')
            for blocker in blockers:
                print(f'  - {blocker}')
            print()
            print('Safe options:')
            print('  python3 src/ai_research/run_ai_research.py --status')
            print('  python3 src/ai_research/run_ai_research.py --latest --limit 5 --plan')
            print('  python3 src/ai_research/run_ai_research.py --latest --limit 5 --dry-run')
            return 2

    print('AI Research Layer')
    print('=================')
    print(f'Run at        : {run_at}')
    print(f'AI ready      : {_bool_text(ai_ready)}')
    print(f'Dry run       : {_bool_text(effective_dry_run)}')
    print(f'Depth         : {depth}')
    print(f'Limit         : {limit or "none"}')
    print(f'Ticker        : {ticker or "all (from latest)"}')
    print(f'Force refresh : {_bool_text(force_refresh)}')
    print(f'Send email    : {_bool_text(send_email)}')
    print()

    # ── 1. Build research cases ──────────────────────────────────────────────
    print('Step 1: Building research cases ...')
    cases = build_cases(
        ticker   = ticker,
        limit    = limit,
        run_date = run_date,
        dry_run  = False,  # always write case files even if AI is off
        research_depth = depth,
    )
    print(f'Built {len(cases)} case(s).')
    case_errors = _validate_cases(cases)
    if case_errors:
        print('Case schema validation: FAIL')
        for err in case_errors:
            print(f'  - {err}')
        return 1
    print(f'Case schema validation: PASS ({len(cases)} case(s))')
    print()

    if not cases:
        print('[INFO] No cases to process. Exiting.')
        _write_summary(
            run_at            = run_at,
            cases             = cases,
            decisions         = [],
            dry_run           = effective_dry_run,
            ai_enabled        = ai_ready,
            watchlist_summary = {},
        )
        return 0

    # ── 2. Run investment gate ───────────────────────────────────────────────
    decisions: list[dict] = []
    wm = WatchlistManager(WATCHLIST_PATH)

    cap = llm_cfg.max_cases_per_run
    gate_cases = cases[:cap] if limit is None else cases
    print(f'Step 2: Running research gate on {len(gate_cases)} case(s) ...')
    if effective_dry_run:
        print('  (dry-run: LLM will not be called; watchlist will not be updated)')
    print()

    client = LLMClient(llm_cfg)

    for case in gate_cases:
        t = case.get('ticker', 'UNKNOWN')
        decision = run_gate(
            case,
            client=client,
            dry_run=effective_dry_run,
            force_refresh=force_refresh,
        )
        decisions.append(decision)

        case_json_path = _case_json_path(run_date, t)
        if case_json_path.exists():
            _inject_decision_into_case_file(case_json_path, decision)

        if not effective_dry_run:
            wm.update(
                ticker    = t,
                decision  = decision,
                case      = case,
                case_path = str(case_json_path),
            )

    decision_errors = _validate_decisions(decisions)
    # Warnings (empty narrative fields) are non-fatal — filter real errors.
    # Format from _validate_decisions is "TICKER: WARNING: <msg>" or "TICKER: <msg>"
    warnings    = [e for e in decision_errors if 'WARNING:' in e]
    hard_errors = [e for e in decision_errors if 'WARNING:' not in e]
    if hard_errors:
        print('Decision schema validation: FAIL')
        for err in hard_errors:
            print(f'  - {err}')
        return 1
    if warnings:
        for w in warnings:
            print(f'  {w}')
    print()
    print(f'Decision schema validation: PASS ({len(decisions)} decision(s))')
    print(f'Gate complete: {len(decisions)} decision(s) made.')
    print()

    # ── 3. Mark stale entries ────────────────────────────────────────────────
    if not effective_dry_run:
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
        ai_enabled        = ai_ready,
        watchlist_summary = watchlist_summary,
    )

    # ── 6. Send email (optional) ─────────────────────────────────────────────
    if send_email:
        cache_hits = sum(
            1 for d in decisions
            if 'CACHE_HIT' in str(d.get('note', ''))
        )
        run_metadata = {
            'run_at':       run_at,
            'model':        getattr(llm_cfg, 'model', 'unknown'),
            'ai_enabled':   ai_ready,
            'dry_run':      effective_dry_run,
            'case_count':   len(cases),
            'decision_count': len(decisions),
            'cache_hits':   cache_hits,
        }
        from ai_research.ai_emailer import send_ai_research_email
        send_ai_research_email(decisions, run_metadata)

    return 0


# ── Plan command ─────────────────────────────────────────────────────────────

def print_plan(ticker: str | None = None, limit: int | None = None, depth: str | None = None) -> None:
    """
    Preview what would run — no files written, no LLM calls.
    Shows tickers, cache status, and estimated LLM/cache action.
    """
    _load_env()
    from ai_research.llm_client import load_config as load_llm_config
    from ai_research.research_case_builder import build_cases
    from ai_research.investment_gate import cache_status

    llm_cfg = load_llm_config()
    depth = depth or llm_cfg.default_depth
    live_allowed, live_reason = _live_call_allowed_reason(llm_cfg)

    cases = build_cases(
        ticker=ticker,
        limit=limit,
        run_date=_today_utc(),
        dry_run=True,
        research_depth=depth,
        verbose=False,
    )
    case_errors = _validate_cases(cases)

    cap = llm_cfg.max_cases_per_run
    planned_cases = cases[:cap] if limit is None else cases

    print('AI Research Layer - Plan Preview')
    print('=================================')
    print(f'  Ticker filter   : {ticker or "all"}')
    print(f'  Latest output   : {_scanner_output_status()}')
    print(f'  Alert count     : {_alert_count_available()[0]}')
    print(f'  Cases found     : {len(cases)}')
    print(f'  Limit flag      : {limit or "none"}')
    print(f'  Depth           : {depth}')
    print(f'  AI enabled      : {_bool_text(llm_cfg.enabled)}')
    print(f'  API key set     : {_bool_text(bool(llm_cfg.api_key))}')
    print(f'  Model           : {llm_cfg.model}')
    print(f'  Max cases/run   : {cap}')
    print(f'  Dry run config  : {_bool_text(llm_cfg.dry_run)}')
    print(f'  Live LLM allowed: {_bool_text(live_allowed)} ({live_reason})')
    print(f'  Cases to assess : {len(planned_cases)}')
    print()

    if case_errors:
        print('  Case schema validation: FAIL')
        for err in case_errors:
            print(f'    - {err}')
        print()
    else:
        print(f'  Case schema validation: PASS ({len(cases)} case(s))')
        print()

    if planned_cases:
        print('  Tickers that would be researched:')
        for case in planned_cases:
            t = str(case.get('ticker', '?')).strip()
            fp, status = cache_status(case)
            estimated_action = 'would_reuse_cache' if status == 'hit' else 'would_call_llm'
            cls = str(case.get('fp_classification', '?')).strip()
            action = str(case.get('recommended_scanner_action', '?')).strip()
            print(
                f'    {t:<8} cache={status:<4} estimated_action={estimated_action:<17} '
                f'fingerprint={fp} scanner={cls or "-"} action={action or "-"}'
            )
    else:
        print('  No cases found: run scanner first.')

    print()
    print('  Plan mode wrote no files and made no LLM calls.')


# ── Status command ────────────────────────────────────────────────────────────

def print_status() -> None:
    _load_env()
    from ai_research.llm_client import LLMClient, load_config as load_llm_config
    from ai_research.watchlist_manager import WatchlistManager

    llm_cfg = load_llm_config()
    client  = LLMClient(llm_cfg)
    wm      = WatchlistManager(WATCHLIST_PATH)
    alert_count, alert_source = _alert_count_available()
    live_allowed, live_reason = _live_call_allowed_reason(llm_cfg)

    print('AI Research Layer - Status')
    print('==========================')
    print(f'  Config .env exists              : {_bool_text(ENV_FILE.exists())}')
    print(f'  AI_RESEARCH_ENABLED             : {_bool_text(llm_cfg.enabled)}')
    print(f'  AI_RESEARCH_DRY_RUN             : {_bool_text(llm_cfg.dry_run)}')
    print(f'  OPENAI_API_KEY set              : {_bool_text(bool(llm_cfg.api_key))}')
    print(f'  AI_MODEL                        : {llm_cfg.model}')
    print(f'  AI_RESEARCH_MAX_CASES_PER_RUN   : {llm_cfg.max_cases_per_run}')
    print(f'  AI_RESEARCH_DEFAULT_DEPTH       : {llm_cfg.default_depth}')
    print(f'  Latest scanner output           : {_scanner_output_status()}')
    print(f'  Alert count available           : {alert_count} ({alert_source})')
    print(f'  Watchlist path                  : {WATCHLIST_PATH}')
    print(f'  Cache path                      : {CACHE_DIR}')
    print(f'  Latest AI summary path          : {SUMMARY_PATH}')
    print(f'  Live LLM call allowed           : {_bool_text(live_allowed)} ({live_reason})')
    print(f'  LLM client status               : {client.status_message}')
    print()
    wm.print_summary()

    if SUMMARY_PATH.exists():
        print()
        print(f'Last summary: {SUMMARY_PATH}')


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description='AI research layer orchestrator - research gate, not trading signal.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=False)
    mode.add_argument('--latest', action='store_true',
                      help='Build cases + run gate from latest scanner outputs')
    mode.add_argument('--ticker', metavar='TICKER',
                      help='Run for a single ticker')
    mode.add_argument('--status', action='store_true',
                      help='Print current watchlist + config summary')

    p.add_argument('--plan', action='store_true',
                   help='Preview what would run - no files written, no LLM calls')
    p.add_argument('--limit',   type=int, default=None,
                   help='Max cases to process (default: AI_RESEARCH_MAX_CASES_PER_RUN)')
    p.add_argument('--depth', default='fast_gate',
                   choices=['fast_gate', 'deep'],
                   help='Research depth preset (default: fast_gate)')
    p.add_argument('--dry-run', action='store_true',
                   help='Build cases but do not call LLM')
    p.add_argument('--force-refresh', action='store_true',
                   help='Bypass cache and rerun LLM for all cases')
    p.add_argument('--email', action='store_true',
                   help='Send branded AI research email after run')
    p.add_argument('--email-latest-summary', action='store_true',
                   help='Send latest AI summary email without rerunning LLM')
    args = p.parse_args(argv)
    if (not args.status and not args.plan and not args.latest
            and not args.ticker and not args.email_latest_summary):
        p.error('one of --status, --plan, --latest, --ticker, or --email-latest-summary is required')
    return args


def main(argv=None) -> int:
    args = _parse_args(argv)

    if args.status:
        print_status()
        return 0

    # --email-latest-summary is independent of the main run modes
    if args.email_latest_summary:
        _load_env()
        from ai_research.ai_emailer import send_latest_summary_email
        result = send_latest_summary_email(force=True)
        return 0 if result.get('sent') else 1

    _load_env()
    from ai_research.llm_client import load_config as load_llm_config

    llm_cfg = load_llm_config()
    depth = args.depth or llm_cfg.default_depth
    if args.plan:
        ticker = args.ticker.upper() if args.ticker else None
        print_plan(ticker=ticker, limit=args.limit, depth=depth)
        return 0

    ticker = args.ticker.upper() if args.ticker else None
    return run(
        ticker        = ticker,
        limit         = args.limit,
        dry_run       = args.dry_run,
        depth         = depth,
        force_refresh = args.force_refresh,
        send_email    = args.email,
    )


if __name__ == '__main__':
    sys.exit(main())
