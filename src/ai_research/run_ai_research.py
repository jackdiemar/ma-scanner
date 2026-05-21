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


# ── Operator action queue ─────────────────────────────────────────────────────

OPERATOR_QUEUE_JSON = AI_RESEARCH_DIR / 'operator_action_queue.json'
OPERATOR_QUEUE_MD   = AI_RESEARCH_DIR / 'operator_action_queue.md'


def _write_operator_action_queue(decisions: list[dict], run_at: str) -> None:
    """Write operator action queue JSON and markdown."""
    AI_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    _PRIORITY = {
        'ESCALATE':          0,
        'NEEDS_HUMAN_REVIEW': 1,
        'WATCH':             2,
        'WAIT_FOR_PRICE':    2,
        'DISCARD':           3,
        'WATCH_ONLY':        3,
    }

    entries: list[dict] = []
    for d in decisions:
        action   = d.get('research_action', 'DISCARD')
        priority = _PRIORITY.get(action, 3)
        eq_grade = str(d.get('evidence_grade', 'F')).upper()

        # Downgrade NEEDS_HUMAN_REVIEW to P2 if evidence is F
        if action == 'NEEDS_HUMAN_REVIEW' and eq_grade == 'F':
            priority = 2

        entries.append({
            'ticker':         d.get('ticker', '?'),
            'action':         action,
            'priority':       f'P{priority}',
            'why':            d.get('short_thesis', '') or d.get('discard_reason', ''),
            'next_step':      (d.get('operator_next_steps', []) or [''])[0],
            'evidence_grade': eq_grade,
            'strategy_bucket': d.get('strategy_bucket', ''),
            'watch_trigger':  (d.get('watch_triggers', []) or [''])[0],
            'historical_analogue': d.get('historical_analogue', ''),
        })

    # Sort by priority then ticker
    entries.sort(key=lambda e: (int(e['priority'][1:]), e['ticker']))

    queue_data = {
        'run_at':  run_at,
        'count':   len(entries),
        'entries': entries,
    }

    try:
        OPERATOR_QUEUE_JSON.write_text(
            json.dumps(queue_data, indent=2, default=str), encoding='utf-8'
        )
    except OSError:
        pass

    # Write markdown
    lines = [
        '# Operator Action Queue',
        '',
        f'**Run at:** {run_at}',
        f'**Total entries:** {len(entries)}',
        '',
    ]

    p0 = [e for e in entries if e['priority'] == 'P0']
    p1 = [e for e in entries if e['priority'] == 'P1']
    p2 = [e for e in entries if e['priority'] == 'P2']
    p3 = [e for e in entries if e['priority'] == 'P3']

    if p0:
        lines += ['## P0 — ESCALATE (Immediate)', '']
        for e in p0:
            lines.append(f'### {e["ticker"]} — {e["action"]}')
            lines.append(f'- **Evidence grade:** {e["evidence_grade"]}')
            lines.append(f'- **Strategy bucket:** {e["strategy_bucket"]}')
            lines.append(f'- **Why:** {e["why"]}')
            lines.append(f'- **Next step:** {e["next_step"]}')
            lines.append('')

    if p1:
        lines += ['## P1 — Human Review Required', '']
        for e in p1:
            lines.append(f'### {e["ticker"]} — {e["action"]}')
            lines.append(f'- **Evidence grade:** {e["evidence_grade"]}')
            lines.append(f'- **Why:** {e["why"]}')
            lines.append(f'- **Next step:** {e["next_step"]}')
            lines.append('')

    if p2:
        lines += ['## P2 — Watch', '']
        for e in p2:
            lines.append(
                f'- **{e["ticker"]}** | {e["strategy_bucket"] or e["action"]} | '
                f'evidence={e["evidence_grade"]} | {e["next_step"]}'
            )
        lines.append('')

    if p3:
        lines += ['## P3 — Monitor / Discard', '']
        for e in p3:
            wt = f' | watch: {e["watch_trigger"]}' if e.get('watch_trigger') else ''
            lines.append(f'- **{e["ticker"]}** | {e["strategy_bucket"] or e["action"]}{wt}')
        lines.append('')

    if not any([p0, p1, p2]):
        lines += [
            '',
            '_No immediate operator actions. '
            'Continue monitoring for new company-level process evidence._',
            '',
        ]

    lines += [
        '---',
        '_Queue is for internal research tracking only. Not investment advice._',
    ]

    try:
        OPERATOR_QUEUE_MD.write_text('\n'.join(lines), encoding='utf-8')
    except OSError:
        pass

    print(f'  [WROTE] {OPERATOR_QUEUE_JSON.relative_to(REPO)}')
    print(f'  [WROTE] {OPERATOR_QUEUE_MD.relative_to(REPO)}')


# ── Summary writer ────────────────────────────────────────────────────────────

def _write_summary(
    run_at: str,
    cases: list[dict],
    decisions: list[dict],
    dry_run: bool,
    ai_enabled: bool,
    watchlist_summary: dict,
    strategic_brief: bool = False,
) -> None:
    AI_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    # Counts
    n_escalate = sum(1 for d in decisions if d.get('research_action') == 'ESCALATE')
    n_watch    = sum(1 for d in decisions if d.get('research_action') in ('WATCH', 'WAIT_FOR_PRICE', 'WATCH_ONLY'))
    n_discard  = sum(1 for d in decisions if d.get('research_action') == 'DISCARD')
    n_review   = sum(1 for d in decisions if d.get('research_action') == 'NEEDS_HUMAN_REVIEW')

    grade_counts: dict[str, int] = {}
    for d in decisions:
        g = str(d.get('evidence_grade', 'F')).upper()
        grade_counts[g] = grade_counts.get(g, 0) + 1

    fp_counts: dict[str, int] = {}
    for d in decisions:
        for fp in (d.get('matched_false_positive_archetypes', []) or []):
            fp_counts[fp] = fp_counts.get(fp, 0) + 1

    dominant_fp = max(fp_counts, key=lambda k: fp_counts[k]) if fp_counts else None
    true_signal_candidates = [
        d for d in decisions
        if d.get('matched_true_signal_archetypes')
        and d.get('research_action') not in ('DISCARD',)
    ]
    already_announced = sum(
        1 for d in decisions
        if 'ALREADY_ANNOUNCED_MERGER' in (d.get('matched_false_positive_archetypes', []) or [])
        or d.get('classification') == 'ALREADY_ANNOUNCED_DEAL'
    )

    lines = [
        '# MA Scanner AI Research Brief',
        '',
        f'**Run at:** {run_at}',
        f'**AI enabled:** {ai_enabled}  |  **Dry run:** {dry_run}',
        f'**Cases reviewed:** {len(cases)}  |  **Decisions:** {len(decisions)}',
        '',
        '---',
        '',
        '## Executive Summary',
        '',
        f'| Decision | Count |',
        f'|---|---|',
        f'| ESCALATE | {n_escalate} |',
        f'| WATCH | {n_watch} |',
        f'| DISCARD | {n_discard} |',
        f'| NEEDS_HUMAN_REVIEW | {n_review} |',
        '',
        '**Evidence grade distribution:** '
        + '  '.join(f'{g}={c}' for g, c in sorted(grade_counts.items())),
        '',
        f'**True-signal candidates:** {len(true_signal_candidates)}',
        f'**Resembling already-announced merger:** {already_announced}',
        f'**Dominant false-positive archetype:** {dominant_fp or "none detected"}',
        '',
    ]

    # Strategy read
    if strategic_brief or decisions:
        lines += ['## Strategy Read', '']
        if not decisions:
            lines.append('_No AI decisions this run._')
        elif n_escalate == 0 and len(true_signal_candidates) == 0:
            lines.append(
                f'Run found {len(decisions)} alerts. '
                f'No MDVN/DMTX/TSRO-like signal detected. '
                f'All top cases were discarded or require human review. '
                + (f'Dominant false-positive pattern: {dominant_fp}. '
                   if dominant_fp else '')
                + 'Source-backed evidence shows no open strategic process in this batch. '
                'This is the expected outcome — the system correctly filtered noise. '
                'Continue monitoring for new company-level process filings.'
            )
        else:
            escalated = [d for d in decisions if d.get('research_action') == 'ESCALATE']
            if escalated:
                lines.append(
                    f'{len(escalated)} case(s) escalated for immediate review. '
                    f'True-signal candidates: {", ".join(d["ticker"] for d in true_signal_candidates)}. '
                    'Review source filings and corroborate with independent news sources before acting.'
                )
            else:
                lines.append(
                    f'{len(true_signal_candidates)} case(s) matched partial true-signal criteria '
                    f'but did not meet full ESCALATE threshold. Monitor for follow-on filings.'
                )
        lines.append('')

    # Watchlist summary
    lines += [
        '---',
        '',
        '## Watchlist',
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
        if strategic_brief:
            lines += ['## Detailed Case Analysis', '']
            for d in decisions:
                ticker  = d.get('ticker', '?')
                cls     = d.get('classification', '?')
                action  = d.get('research_action', '?')
                conf    = d.get('confidence', 0.0)
                score   = d.get('investability_score', 0)
                grade   = d.get('evidence_grade', 'F')
                bucket  = d.get('strategy_bucket', '')
                analogue = d.get('historical_analogue', '')

                lines.append(f'### {ticker} — {action} | {grade} evidence')
                lines.append(f'**Classification:** {cls}  |  **Confidence:** {int(conf*100)}%  |  **Score:** {score}/100')
                if bucket:
                    lines.append(f'**Strategy bucket:** {bucket}')
                if analogue:
                    lines.append(f'**Historical analogue:** {analogue}')
                lines.append('')

                if d.get('short_thesis'):
                    lines.append(f'**Thesis:** {d["short_thesis"]}')
                    lines.append('')

                if d.get('why_this_fired'):
                    lines.append(f'**Why this fired:** {d["why_this_fired"]}')

                if d.get('evidence_summary'):
                    lines.append(f'**Evidence:** {d["evidence_summary"]}')

                if d.get('how_it_compares_to_mdvn_dmtx_tsro'):
                    lines.append(f'**vs MDVN/DMTX/TSRO:** {d["how_it_compares_to_mdvn_dmtx_tsro"]}')

                fps = d.get('matched_false_positive_archetypes', [])
                if fps:
                    lines.append(f'**False-positive archetypes:** {", ".join(fps)}')

                ts = d.get('matched_true_signal_archetypes', [])
                if ts:
                    lines.append(f'**True-signal archetypes matched:** {", ".join(ts)}')

                op_steps = d.get('operator_next_steps', [])
                if op_steps:
                    lines.append('**Operator next steps:**')
                    for s in op_steps:
                        lines.append(f'  - {s}')

                if d.get('kill_criteria'):
                    lines.append(f'**Kill criteria:** {d["kill_criteria"]}')

                if d.get('escalation_criteria'):
                    lines.append(f'**Escalation criteria:** {d["escalation_criteria"]}')

                if d.get('monitoring_plan'):
                    lines.append(f'**Monitoring plan:** {d["monitoring_plan"]}')

                note = d.get('note', '')
                if note:
                    lines.append(f'_Note: {note}_')

                lines.append('')
        else:
            lines += ['## Decisions This Run', '']
            for d in decisions:
                ticker = d.get('ticker', '?')
                cls    = d.get('classification', '?')
                action = d.get('research_action', '?')
                conf   = d.get('confidence', 0.0)
                score  = d.get('investability_score', 0)
                bucket = d.get('strategy_bucket', '')
                note   = d.get('note', '')
                lines.append(
                    f'- **{ticker}** → {cls} | action={action} | '
                    f'confidence={conf:.2f} | score={score}'
                    + (f' | bucket={bucket}' if bucket else '')
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
    strategic_brief: bool = False,
) -> int:
    """
    Main execution: build cases, optionally run gate, update watchlist, write summary.

    Args:
        ticker:          Run for a single ticker instead of latest alerts.
        limit:           Max cases to process.
        dry_run:         Skip LLM calls; return placeholder decisions.
        depth:           Research depth preset (fast_gate, deep).
        run_date:        Override the run date (YYYY-MM-DD).
        force_refresh:   Bypass cache and rerun LLM for every case.
        send_email:      Send branded AI research email after run completes.
        strategic_brief: Include full strategy analysis in summary and email.

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
    print(f'Force refresh    : {_bool_text(force_refresh)}')
    print(f'Send email       : {_bool_text(send_email)}')
    print(f'Strategic brief  : {_bool_text(strategic_brief)}')
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
            strategic_brief   = strategic_brief,
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
        strategic_brief   = strategic_brief,
    )

    # ── 5b. Write operator action queue ─────────────────────────────────────
    if decisions and not effective_dry_run:
        _write_operator_action_queue(decisions, run_at)

    # ── 6. Send email (optional) ─────────────────────────────────────────────
    if send_email:
        cache_hits = sum(
            1 for d in decisions
            if 'CACHE_HIT' in str(d.get('note', ''))
        )
        run_metadata = {
            'run_at':          run_at,
            'model':           getattr(llm_cfg, 'model', 'unknown'),
            'ai_enabled':      ai_ready,
            'dry_run':         effective_dry_run,
            'case_count':      len(cases),
            'decision_count':  len(decisions),
            'cache_hits':      cache_hits,
            'strategic_brief': strategic_brief,
        }
        from ai_research.ai_emailer import send_ai_research_email
        send_ai_research_email(decisions, run_metadata, strategic_brief=strategic_brief)

    return 0


# ── Evidence audit command ───────────────────────────────────────────────────

def run_evidence_audit(
    ticker: str | None = None,
    limit: int | None = None,
    fetch_text: bool = False,
) -> int:
    """
    Build cases, compute evidence quality, optionally fetch filing text.
    Prints evidence grade table. No LLM calls. No email.
    """
    _load_env()
    from ai_research.research_case_builder import build_cases
    from ai_research.quote_extractor import compute_evidence_quality, extract_quotes

    print('AI Research Layer — Evidence Audit')
    print('===================================')
    print(f'Ticker filter : {ticker or "all"}')
    print(f'Limit         : {limit or "none"}')
    print(f'Fetch text    : {_bool_text(fetch_text)}')
    print()

    cases = build_cases(
        ticker=ticker,
        limit=limit,
        run_date=_today_utc(),
        dry_run=True,
        verbose=False,
    )

    if not cases:
        print('[INFO] No cases found. Run scanner first.')
        return 0

    if fetch_text:
        from ai_research.source_fetcher import fetch_sec_filing_text_for_case

    rows: list[dict] = []
    for case in cases:
        t = case.get('ticker', '?')

        filing_text: str | None = None
        fetch_error: str | None = None
        if fetch_text:
            print(f'  Fetching {t} ...', end=' ', flush=True)
            result = fetch_sec_filing_text_for_case(case)
            filing_text = result.get('text') or None
            fetch_error = result.get('error')
            cached      = result.get('cached', False)
            status      = 'cached' if cached else ('ok' if not fetch_error else f'FAIL: {fetch_error}')
            print(status)

        quotes = extract_quotes(case, filing_text)
        eq     = compute_evidence_quality(case, filing_text, quotes)

        # Update case evidence_quality with fetched-text results
        case['evidence_quality'] = eq
        rows.append({
            'ticker':  t,
            'grade':   eq['evidence_grade'],
            'score':   eq['evidence_completeness_score'],
            'excerpt': eq['excerpt_length'],
            'full':    eq['full_text_length'],
            'gaps':    len(eq['evidence_gaps']),
            'quotes':  len(quotes),
            'gaps_list': eq['evidence_gaps'],
        })

    print()
    print(f'{"Ticker":<8}  {"Grade":>5}  {"Score":>5}  {"Excerpt":>7}  {"FullText":>8}  {"Gaps":>4}  {"Quotes":>6}')
    print('-' * 60)
    for r in rows:
        print(
            f'{r["ticker"]:<8}  {r["grade"]:>5}  {r["score"]:>5}  '
            f'{r["excerpt"]:>7}  {r["full"]:>8}  {r["gaps"]:>4}  {r["quotes"]:>6}'
        )

    print()
    for r in rows:
        if r['gaps_list']:
            print(f'  {r["ticker"]} gaps: {" | ".join(r["gaps_list"])}')

    grade_counts: dict[str, int] = {}
    for r in rows:
        grade_counts[r['grade']] = grade_counts.get(r['grade'], 0) + 1
    print()
    print('Grade summary: ' + '  '.join(f'{g}={c}' for g, c in sorted(grade_counts.items())))
    return 0


def run_show_evidence(ticker: str, fetch_text: bool = False) -> int:
    """
    Print full evidence detail for a single ticker: raw source fields from each
    data source, enriched case fields, evidence quality, and extracted quotes.
    No LLM calls. No email.
    """
    _load_env()
    from ai_research.research_case_builder import build_cases, inspect_source_fields
    from ai_research.quote_extractor import compute_evidence_quality, extract_quotes

    t = ticker.upper()

    # Show raw source inspection first
    raw_rows = inspect_source_fields(ticker=t, limit=1)

    cases = build_cases(
        ticker=t,
        limit=1,
        run_date=_today_utc(),
        dry_run=True,
        verbose=False,
    )

    if not cases:
        print(f'[WARN] No case found for {ticker}. Run scanner first.')
        return 1

    case = cases[0]

    filing_text: str | None = None
    fetch_status = 'not attempted'
    if fetch_text:
        from ai_research.source_fetcher import fetch_sec_filing_text_for_case
        fetch_result = fetch_sec_filing_text_for_case(case)
        filing_text  = fetch_result.get('text') or None
        fetch_status = 'cached' if fetch_result.get('cached') else (
            f'FAIL: {fetch_result["error"]}' if fetch_result.get('error') else
            f'ok ({len(filing_text or "")} chars)'
        )

    quotes = extract_quotes(case, filing_text)
    eq     = compute_evidence_quality(case, filing_text, quotes)

    print(f'Evidence Detail: {ticker}')
    print('=' * 60)

    # Raw fields per data source
    if raw_rows:
        r = raw_rows[0]
        print('Raw source fields:')
        print(f'  latest_alerts.json  : url={"yes" if r["json_source_url"] else "no"}'
              f'  excerpt={r["json_excerpt_len"]}chars'
              f'  date={r["json_filing_date"] or "—"}'
              f'  form={r["json_filing_form"] or "—"}'
              f'  accession={"yes" if r["json_accession"] else "no"}')
        print(f'  live_alert_log.csv  : url={"yes" if r["csv_source_url"] else "no"}'
              f'  excerpt={r["csv_excerpt_len"]}chars'
              f'  date={r["csv_filing_date"] or "—"}'
              f'  form={r["csv_filing_form"] or "—"}')
        print(f'  Scanner dry-run     : {r["scanner_dry_run"]}')
        print()

    print('Enriched case fields:')
    print(f'  Ticker          : {case.get("ticker")}')
    print(f'  Company         : {case.get("company_name")}')
    print(f'  Signal quality  : {case.get("signal_quality")}')
    print(f'  Signal type     : {case.get("signal_type")}')
    print(f'  Filing type     : {case.get("filing_type") or "—"} (enriched from flags)')
    print(f'  Filing date     : {case.get("filing_date") or "—"} (enriched from flags)')
    print(f'  Source URL      : {case.get("source_url") or "—"}')
    print(f'  URL constructed : {case.get("source_url_constructed", False)}')
    print(f'  Accession       : {case.get("accession") or "—"}')
    print(f'  Trigger phrase  : {case.get("trigger_phrase") or "—"}')
    if case.get('flags_context'):
        print(f'  Flags context   :')
        for fc in case['flags_context'][:5]:
            print(f'    - {fc}')
    if fetch_text:
        print(f'  Fetch status    : {fetch_status}')
    print()

    print('Evidence Quality:')
    print(f'  Grade                 : {eq["evidence_grade"]}')
    print(f'  Score                 : {eq["evidence_completeness_score"]}/100')
    print(f'  Can be confident      : {eq["can_make_confident_decision"]}')
    print(f'  Source is SEC         : {eq["source_is_sec"]}')
    print(f'  Excerpt length        : {eq["excerpt_length"]} chars')
    print(f'  Full text length      : {eq["full_text_length"]} chars')
    if eq['evidence_gaps']:
        print('  Gaps:')
        for g in eq['evidence_gaps']:
            print(f'    - {g}')
    print()

    src_excerpt = case.get('source_excerpt', '') or ''
    print('Source Excerpt:')
    print(f'  {src_excerpt[:600] or "(none)"}')
    print()

    if quotes:
        print(f'Extracted Quotes ({len(quotes)}):')
        for i, q in enumerate(quotes, 1):
            print(f'  [{i}] phrase="{q["phrase"]}" source={q["source"]}')
            print(f'      reason : {q["reason"]}')
            print(f'      context: {q["context"][:300]}')
            print()
    else:
        print('No quotes extracted.')

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
        epilog=(
            'Examples:\n'
            '  --latest --limit 10\n'
            '  --latest --limit 10 --evidence-audit\n'
            '  --latest --limit 5  --evidence-audit --fetch-text\n'
            '  --latest --limit 3  --dry-run\n'
            '  --latest --limit 3  --plan\n'
            '  --show-evidence APLS\n'
            '  --inspect-source-fields --limit 10\n'
            '  --status\n'
            '  --email-latest-summary\n'
        ),
    )
    # Primary mode flags — ONLY --status, --show-evidence, --inspect-source-fields,
    # and --email-latest-summary are truly standalone.
    # --latest and --ticker can be combined with --evidence-audit, --plan, --dry-run.
    mode = p.add_mutually_exclusive_group(required=False)
    mode.add_argument('--latest', action='store_true',
                      help='Build cases + run gate from latest scanner outputs')
    mode.add_argument('--ticker', metavar='TICKER',
                      help='Run for a single ticker')
    mode.add_argument('--status', action='store_true',
                      help='Print current watchlist + config summary')
    mode.add_argument('--show-evidence', metavar='TICKER',
                      help='Print full evidence detail for a single ticker — no LLM, no email')
    mode.add_argument('--inspect-source-fields', action='store_true',
                      help='Print source field availability table — no LLM, no email')
    mode.add_argument('--email-latest-summary', action='store_true',
                      help='Send latest AI summary email without rerunning LLM')
    mode.add_argument('--completed-acquisition-status', action='store_true',
                      help='Print completed acquisition library stats — no LLM, no email')
    mode.add_argument('--compare-completed-deals', metavar='TICKER',
                      help='Show closest analogues + probability bucket for a ticker — no LLM')

    # Modifiers — can combine with --latest or --ticker
    p.add_argument('--evidence-audit', action='store_true',
                   help='Print evidence grade table (combine with --latest or --ticker)')
    p.add_argument('--plan', action='store_true',
                   help='Preview what would run - no files written, no LLM calls')
    p.add_argument('--probability-audit', action='store_true',
                   help='Print situation type, probability score, bucket for latest cases — no LLM')
    p.add_argument('--include-completed-analogues', action='store_true', default=True,
                   help='Include completed deal analogues in analysis (default: True)')
    p.add_argument('--probability-analysis', action='store_true', default=True,
                   help='Include probability analysis in output (default: True)')
    p.add_argument('--limit',   type=int, default=None,
                   help='Max cases to process (default: AI_RESEARCH_MAX_CASES_PER_RUN)')
    p.add_argument('--depth', default='fast_gate',
                   choices=['fast_gate', 'deep'],
                   help='Research depth preset (default: fast_gate)')
    p.add_argument('--dry-run', action='store_true',
                   help='Build cases but do not call LLM')
    p.add_argument('--force-refresh', action='store_true',
                   help='Bypass cache and rerun LLM for all cases')
    p.add_argument('--fetch-text', action='store_true',
                   help='Fetch full filing text from source URL (used with --evidence-audit, --show-evidence)')
    p.add_argument('--email', action='store_true',
                   help='Send branded AI research email after run')
    p.add_argument('--strategic-brief', action='store_true',
                   help='Include full strategy analysis, historical analogues, and operator queue in summary and email')
    args = p.parse_args(argv)

    has_primary = (args.latest or args.ticker or args.status or args.show_evidence
                   or args.inspect_source_fields or args.email_latest_summary
                   or args.completed_acquisition_status or args.compare_completed_deals)
    has_modifier = args.evidence_audit or args.plan or args.dry_run

    if not has_primary and not has_modifier:
        p.error(
            'specify a mode: --latest, --ticker TICKER, --status, --show-evidence TICKER, '
            '--inspect-source-fields, or --email-latest-summary'
        )
    if has_modifier and not (args.latest or args.ticker):
        # Allow --probability-audit as a standalone modifier (it reads existing case data)
        if args.probability_audit:
            pass
        else:
            p.error('--evidence-audit, --plan, and --dry-run require --latest or --ticker')

    return args


def run_inspect_source_fields(limit: int | None = None) -> int:
    """
    Print source field availability for each alert — shows raw fields from every
    data source and whether enrichment (flags parsing, EDGAR URL construction) improved them.
    No LLM calls. No email.
    """
    _load_env()
    from ai_research.research_case_builder import inspect_source_fields

    rows = inspect_source_fields(limit=limit)
    if not rows:
        print('[INFO] No alerts found. Run scanner first.')
        return 0

    print('Source Field Inspection')
    print('=======================')
    print(f'{"Ticker":<8}  {"Signal type":<30}  {"JSON URL":>7}  {"Exc":>4}  {"Date":>10}  {"Form":>8}  {"Constructed":>11}  {"DryRun":>6}')
    print('-' * 105)
    for r in rows:
        print(
            f'{r["ticker"]:<8}  {r["signal_type"]:<30}  '
            f'{"yes" if r["json_source_url"] else "no":>7}  '
            f'{r["json_excerpt_len"]:>4}  '
            f'{(r["enriched_filing_date"] or "—"):>10}  '
            f'{(r["enriched_filing_type"] or "—"):>8}  '
            f'{"constructed" if r["source_url_is_constructed"] else "direct":>11}  '
            f'{"yes" if r["scanner_dry_run"] else "no":>6}'
        )

    print()
    # Show constructed URLs for each ticker
    for r in rows:
        if r['source_url_is_constructed']:
            print(f'  {r["ticker"]} → {r["enriched_source_url"]}')

    if rows and rows[0]['scanner_dry_run']:
        print()
        print(
            'NOTE: Scanner has been running in dry-run mode. Gate 1 (EDGAR filing fetch)\n'
            'was skipped for all runs. To populate source fields, re-run the live scanner\n'
            'with LIVE_SCANNER_DRY_RUN=false on the VPS:\n'
            '  systemctl start ma-scanner-live.service\n'
            '  python3 src/live_monitoring/live_scanner_runner.py --once'
        )
    return 0


def run_completed_acquisition_status() -> int:
    """Print completed acquisition library stats. No LLM calls."""
    _load_env()
    from ai_research.acquisition_case_library import print_library_status, load_completed_acquisition_cases, validate_completed_acquisition_cases
    print_library_status()
    return 0


def run_compare_completed_deals(ticker: str, limit: int | None = None) -> int:
    """
    For a live ticker, show closest analogues, probability bucket, situation type, traits.
    No LLM calls.
    """
    _load_env()
    from ai_research.research_case_builder import build_cases
    from ai_research.acquisition_situation_classifier import classify_acquisition_situation
    from ai_research.acquisition_probability_engine import compute_acquisition_probability, format_probability_summary
    from ai_research.acquisition_case_library import (
        load_completed_acquisition_cases,
        retrieve_completed_deal_analogues,
    )

    t = ticker.upper()
    cases = build_cases(ticker=t, limit=1, run_date=_today_utc(), dry_run=True, verbose=False)

    if not cases:
        print(f'[WARN] No case found for {t}. Run scanner first.')
        return 1

    case = cases[0]
    print(f'Completed Deal Comparison: {t}')
    print('=' * 60)

    situation_result = classify_acquisition_situation(case)
    prob_result      = compute_acquisition_probability(case)

    print(f'Primary situation   : {situation_result.get("primary_acquisition_situation", "?")}')
    print(f'Probability bucket  : {prob_result.get("probability_bucket", "?")}')
    print(f'Research score      : {prob_result.get("acquisition_research_probability_score", 0)}/100')
    print(f'Explicit process    : {situation_result.get("is_explicit_process_signal", False)}')
    print(f'Setup signal only   : {situation_result.get("is_setup_signal_only", False)}')
    print()

    print('Situation scores:')
    for sit, score in sorted(
        situation_result.get('situation_scores', {}).items(),
        key=lambda x: x[1], reverse=True,
    )[:5]:
        print(f'  {sit:<45} {score:>5.0f}')
    print()

    print('Reasoning:')
    print(f'  {situation_result.get("deterministic_reasoning", "")}')
    print()

    completed_cases = load_completed_acquisition_cases()
    analogues = retrieve_completed_deal_analogues(case, completed_cases, max_cases=5)
    if analogues:
        print(f'Top {len(analogues)} completed deal analogues:')
        for i, a in enumerate(analogues, 1):
            print(f'  [{i}] {a.get("ticker", "?")} — {a.get("company_name", "")}')
            print(f'       Situation: {a.get("acquisition_situation_type", "?")}')
            print(f'       Signal   : {a.get("public_signal_category", "?")}')
            print(f'       Catchable: {a.get("public_catchability", "?")}')
            print(f'       Relevance: {a.get("_relevance_score", 0.0):.2f}')
            lesson = a.get('operator_lesson', '')
            if lesson:
                print(f'       Lesson   : {lesson[:150]}')
            print()

    traits_present = prob_result.get('successful_deal_traits_present', [])
    traits_missing = prob_result.get('successful_deal_traits_missing', [])
    if traits_present:
        print('Successful deal traits PRESENT:')
        for t_item in traits_present:
            print(f'  + {t_item}')
        print()
    if traits_missing:
        print('Successful deal traits MISSING:')
        for t_item in traits_missing[:4]:
            print(f'  - {t_item}')
        print()

    why_not = prob_result.get('why_probability_not_higher', '')
    if why_not:
        print(f'Why not higher: {why_not}')
        print()

    return 0


def run_probability_audit(ticker: str | None = None, limit: int | None = None) -> int:
    """
    For the latest N cases, print situation type, probability score, bucket, top reasons.
    No LLM calls. Uses existing case data from today.
    """
    _load_env()
    from ai_research.research_case_builder import build_cases
    from ai_research.acquisition_situation_classifier import classify_acquisition_situation
    from ai_research.acquisition_probability_engine import compute_acquisition_probability

    cases = build_cases(
        ticker=ticker,
        limit=limit,
        run_date=_today_utc(),
        dry_run=True,
        verbose=False,
    )

    if not cases:
        print('[INFO] No cases found. Run scanner first.')
        return 0

    print('Probability Audit')
    print('=================')
    print(f'{"Ticker":<8}  {"Bucket":<35}  {"Score":>5}  {"Situation":<40}  {"Confidence"}')
    print('-' * 110)

    for case in cases:
        t = case.get('ticker', '?')
        try:
            sit_result = classify_acquisition_situation(case)
            prob_result = compute_acquisition_probability(case)
            bucket     = prob_result.get('probability_bucket', '?')
            score      = prob_result.get('acquisition_research_probability_score', 0)
            situation  = sit_result.get('primary_acquisition_situation', '?')
            confidence = prob_result.get('confidence_level', '?')
            print(f'{t:<8}  {bucket:<35}  {score:>5.0f}  {situation:<40}  {confidence}')
        except Exception as exc:
            print(f'{t:<8}  ERROR: {exc}')

    print()
    print('Probability audit complete. No LLM calls were made.')
    return 0


def main(argv=None) -> int:
    args = _parse_args(argv)

    if args.status:
        print_status()
        return 0

    if args.show_evidence:
        return run_show_evidence(args.show_evidence.upper(), fetch_text=args.fetch_text)

    if args.inspect_source_fields:
        return run_inspect_source_fields(limit=args.limit)

    if args.completed_acquisition_status:
        return run_completed_acquisition_status()

    if args.compare_completed_deals:
        return run_compare_completed_deals(args.compare_completed_deals.upper(), limit=args.limit)

    # --email-latest-summary is standalone
    if args.email_latest_summary:
        _load_env()
        from ai_research.ai_emailer import send_latest_summary_email
        result = send_latest_summary_email(force=True)
        return 0 if result.get('sent') else 1

    _load_env()
    from ai_research.llm_client import load_config as load_llm_config

    llm_cfg = load_llm_config()
    depth = args.depth or llm_cfg.default_depth
    ticker = args.ticker.upper() if args.ticker else None

    # --plan is a preview modifier for --latest / --ticker
    if args.plan:
        print_plan(ticker=ticker, limit=args.limit, depth=depth)
        return 0

    # --evidence-audit is a modifier for --latest / --ticker
    if args.evidence_audit:
        return run_evidence_audit(ticker=ticker, limit=args.limit, fetch_text=args.fetch_text)

    # --probability-audit is a modifier (can be standalone or with --latest/--ticker)
    if args.probability_audit:
        return run_probability_audit(ticker=ticker, limit=args.limit)

    return run(
        ticker          = ticker,
        limit           = args.limit,
        dry_run         = args.dry_run,
        depth           = depth,
        force_refresh   = args.force_refresh,
        send_email      = args.email,
        strategic_brief = args.strategic_brief,
    )


if __name__ == '__main__':
    sys.exit(main())
