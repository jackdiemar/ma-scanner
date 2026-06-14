"""
run_ai_research.py — Main CLI orchestrator for the AI research layer.

Usage:
  python3 src/ai_research/run_ai_research.py --latest --limit 5
  python3 src/ai_research/run_ai_research.py --latest --limit 5 --plan
  python3 src/ai_research/run_ai_research.py --latest --limit 5 --opportunity-plan
  python3 src/ai_research/run_ai_research.py --latest --dry-run
  python3 src/ai_research/run_ai_research.py --latest --limit 10 --depth fast_gate --email --opportunity-mode
  python3 src/ai_research/run_ai_research.py --latest --limit 5 --force-refresh
  python3 src/ai_research/run_ai_research.py --ticker SDGR
  python3 src/ai_research/run_ai_research.py --status
  python3 src/ai_research/run_ai_research.py --suppression-status
  python3 src/ai_research/run_ai_research.py --email-latest-summary
  python3 src/ai_research/run_ai_research.py --force-unsuppress TICKER
  python3 src/ai_research/run_ai_research.py --clear-suppression TICKER

Behavior:
  - Builds research cases from latest scanner outputs.
  - Dry-run builds cases and validates schema without calling the LLM.
  - Live runs require AI_RESEARCH_ENABLED=true and OPENAI_API_KEY.
  - If AI enabled and not dry-run: runs investment gate on up to limit cases.
  - Saves JSON decisions into case files.
  - Updates watchlist.
  - Writes data/ai_research/latest_ai_research_summary.md.
  - Optionally sends branded HTML research email via --email.
  - --opportunity-mode: suppresses repeated DISCARD cases and sends
    opportunity-focused emails. Default for scheduled runs.
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

ENV_FILE             = REPO / 'config' / '.env'
AI_RESEARCH_DIR      = REPO / 'data' / 'ai_research'
CASES_BASE_DIR       = AI_RESEARCH_DIR / 'cases'
CACHE_DIR            = AI_RESEARCH_DIR / 'cache'
WATCHLIST_PATH       = AI_RESEARCH_DIR / 'watchlist.json'
SUMMARY_PATH         = AI_RESEARCH_DIR / 'latest_ai_research_summary.md'
SUPPRESSION_PATH     = AI_RESEARCH_DIR / 'suppression_registry.json'
QUEUE_JSON_PATH      = AI_RESEARCH_DIR / 'latest_opportunity_queue.json'
LIVE_DATA            = REPO / 'data' / 'live_monitoring'
LATEST_ALERTS        = LIVE_DATA / 'latest_alerts.json'
ALERT_LOG            = LIVE_DATA / 'live_alert_log.csv'

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


# ── Suppressed case stub ──────────────────────────────────────────────────────

def _make_suppressed_stub(case: dict, suppress_reason: str) -> dict:
    """
    Minimal decision dict for a case that is suppressed and unchanged.
    Does not call the LLM. Goes into P4 suppressed queue only.
    """
    ticker = str(case.get('ticker', 'UNKNOWN')).upper()
    return {
        'ticker':                             ticker,
        'company_name':                       case.get('company_name', ''),
        'classification':                     'ALREADY_ANNOUNCED_DEAL',
        'research_action':                    'DISCARD',
        'confidence':                         0.0,
        'investability_score':                0,
        'evidence_strength':                  'LOW',
        'priced_in_assessment':               'UNKNOWN',
        'time_sensitivity':                   'LOW',
        'why_interesting':                    [],
        'why_not':                            ['Suppressed: unchanged from prior run'],
        'key_evidence':                       [],
        'missing_information':                [],
        'next_research_steps':                [],
        'human_review_questions':             [],
        'short_thesis':                       f'Suppressed: {suppress_reason}',
        'why_this_matters':                   '',
        'why_now':                            '',
        'evidence_summary':                   'No change detected vs. prior run.',
        'source_timing_analysis':             '',
        'signal_quality_analysis':            '',
        'priced_in_analysis':                 '',
        'false_positive_risk':                '',
        'key_reasons':                        [f'Suppressed: {suppress_reason}'],
        'operator_next_steps':                [],
        'what_would_change_the_decision':     'New filing date, source URL, or signal type',
        'watch_triggers':                     [],
        'discard_reason':                     suppress_reason,
        'escalation_reason':                  '',
        'human_review_reason':                '',
        'evidence_grade':                     case.get('evidence_grade', 'F'),
        'evidence_completeness_score':        0,
        'evidence_gaps':                      [],
        'filing_text_available':              False,
        'primary_source_quotes':              [],
        'strategy_bucket':                    '',
        'matched_true_signal_archetypes':     [],
        'matched_false_positive_archetypes':  ['ALREADY_ANNOUNCED_MERGER'],
        'historical_analogue':                '',
        'true_signal_similarity_score':       0,
        'false_positive_similarity_score':    100,
        'timing_edge_score':                  0,
        'company_level_process_score':        0,
        'process_specificity_score':          0,
        'investability_setup_score':          0,
        'deterministic_strategy_summary':     '',
        'why_this_fired':                     'Scanner detected M&A language in filing',
        'why_this_is_or_is_not_actionable':   'Suppressed: repeated DISCARD, no change',
        'why_not_like_true_signal_examples':  '',
        'how_it_compares_to_mdvn_dmtx_tsro':  '',
        'what_market_may_already_know':       '',
        'what_operator_should_check_next':    '',
        'monitoring_plan':                    '',
        'kill_criteria':                      '',
        'escalation_criteria':                '',
        'next_filing_or_news_to_watch':       '',
        'suggested_follow_up_queries':        [],
        # Diligence memo fields
        'one_sentence_bottom_line':           f'Suppressed: {suppress_reason}',
        'executive_case_takeaway':            '',
        'why_this_case_matters_now':          '',
        'source_evidence_read':               '',
        'exact_quotes_used':                  [],
        'acquisition_situation_read':         '',
        'completed_deal_analogue_read':       '',
        'probability_bucket_read':            '',
        'what_is_already_known_by_market':    '',
        'what_is_not_yet_answered':           '',
        'operator_decision':                  'DISCARD',
        'immediate_next_steps':               [],
        'next_sources_to_check':              [],
        'what_would_upgrade':                 'New filing date, source URL, or signal type for this ticker',
        'what_would_downgrade':               '',
        'why_this_is_not_actionable_yet':     suppress_reason,
        'note':                               f'SUPPRESSED_UNCHANGED: {suppress_reason}',
        'ran_at':                             datetime.now(timezone.utc).isoformat(),
        'primary_acquisition_situation':              '',
        'possible_acquisition_situations':            [],
        'completed_deal_analogues':                   [],
        'closest_completed_deal_analogue':            None,
        'acquisition_research_probability_score':     0,
        'probability_bucket':                         'P1_DISCARD_ALREADY_ANNOUNCED',
        'probability_components':                     {},
        'base_rate_anchor':                           4.0,
        'upward_probability_factors':                 [],
        'downward_probability_factors':               [],
        'successful_deal_traits_present':             [],
        'successful_deal_traits_missing':             [],
        'external_research_status':                   {},
        'external_sources_reviewed':                  [],
        'online_research_gaps':                       [],
        'is_explicit_process_signal':                 False,
        'is_setup_signal_only':                       False,
        'is_probabilistic_watch_case':                False,
        'why_probability_not_higher':                 '',
        'evidence_needed_to_upgrade':                 [],
        'next_source_queries':                        [],
    }


# ── Summary writer ────────────────────────────────────────────────────────────

def _write_summary(
    run_at: str,
    cases: list[dict],
    decisions: list[dict],
    dry_run: bool,
    ai_enabled: bool,
    watchlist_summary: dict,
    opportunity_mode: bool = False,
    queue: dict | None = None,
) -> None:
    AI_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        '# AI Research Layer - Latest Run Summary',
        '',
        f'**Run at:** {run_at}  ',
        f'**AI enabled:** {ai_enabled}  ',
        f'**Dry run:** {dry_run}  ',
        f'**Opportunity mode:** {opportunity_mode}  ',
        f'**Cases built:** {len(cases)}  ',
        f'**Decisions made:** {len(decisions)}  ',
    ]

    if queue:
        lines += [
            f'**Active (P0–P3):** {queue.get("total_active", 0)}  ',
            f'**Suppressed:** {queue.get("total_suppressed_full", 0)}  ',
            f'**No opportunity:** {queue.get("no_opportunity", False)}  ',
        ]

    lines += ['', '---', '', '## Watchlist Summary', '',
              '| Status | Count |', '|---|---|',
              f'| Total | {watchlist_summary.get("total", 0)} |',
              f'| Escalated | {watchlist_summary.get("escalated", 0)} |',
              f'| Active watch | {watchlist_summary.get("active_watch", 0)} |',
              f'| Needs review | {watchlist_summary.get("needs_review", 0)} |',
              f'| Discarded | {watchlist_summary.get("discarded", 0)} |',
              f'| Stale | {watchlist_summary.get("stale", 0)} |',
              '', '---', '']

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
            '## Cases Built (No AI Run)', '',
            '_AI research was disabled or dry-run active._', '',
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
        '---', '',
        '_This summary is for research tracking only. '
        'Nothing here constitutes investment advice or a recommendation to trade any security._',
    ]
    SUMMARY_PATH.write_text('\n'.join(lines), encoding='utf-8')
    print(f'  [WROTE] {SUMMARY_PATH.relative_to(REPO)}')


# ── Case file updater ─────────────────────────────────────────────────────────

def _inject_decision_into_case_file(case_path: Path, decision: dict) -> None:
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
    opportunity_mode: bool = False,
    include_suppressed: bool = False,
    max_suppressed_summary: int = 5,
) -> int:
    """
    Main execution: build cases, optionally run gate, update watchlist, write summary.

    opportunity_mode: applies suppression registry — skips LLM for unchanged suppressed
    cases, sends email focused on P0/P1/P2/P3 priority cases only.
    """
    _load_env()
    run_at   = _utc_now()
    run_date = run_date or _today_utc()

    from ai_research.llm_client import LLMClient, load_config as load_llm_config
    from ai_research.research_case_builder import build_cases
    from ai_research.investment_gate import run_gate
    from ai_research.watchlist_manager import WatchlistManager

    llm_cfg           = load_llm_config()
    ai_ready          = llm_cfg.ready
    effective_dry_run = dry_run or llm_cfg.dry_run
    depth             = depth or llm_cfg.default_depth

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
            for b in blockers:
                print(f'  - {b}')
            print()
            print('Safe options:')
            print('  python3 src/ai_research/run_ai_research.py --status')
            print('  python3 src/ai_research/run_ai_research.py --latest --limit 5 --plan')
            print('  python3 src/ai_research/run_ai_research.py --latest --limit 5 --dry-run')
            return 2

    print('AI Research Layer')
    print('=================')
    print(f'Run at          : {run_at}')
    print(f'AI ready        : {_bool_text(ai_ready)}')
    print(f'Dry run         : {_bool_text(effective_dry_run)}')
    print(f'Depth           : {depth}')
    print(f'Limit           : {limit or "none"}')
    print(f'Ticker          : {ticker or "all (from latest)"}')
    print(f'Force refresh   : {_bool_text(force_refresh)}')
    print(f'Send email      : {_bool_text(send_email)}')
    print(f'Opportunity mode: {_bool_text(opportunity_mode)}')
    print(f'Strategic brief : {_bool_text(strategic_brief)}')
    print()

    # ── 1. Build research cases ──────────────────────────────────────────────
    print('Step 1: Building research cases ...')
    cases = build_cases(
        ticker         = ticker,
        limit          = limit,
        run_date       = run_date,
        dry_run        = False,
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
        _write_summary(run_at=run_at, cases=cases, decisions=[], dry_run=effective_dry_run,
                       ai_enabled=ai_ready, watchlist_summary={})
        return 0

    # ── 1b. Fetch catalyst summary ───────────────────────────────────────────
    catalyst_summary: dict | None = None
    try:
        from ai_research.catalyst_tracker import build_catalyst_summary
        company_names = {str(c.get('ticker', '')).upper(): c.get('company_name', '') for c in cases}
        fmp_key = os.environ.get('FMP_API_KEY', '')
        catalyst_summary = build_catalyst_summary(
            universe_tickers = set(company_names.keys()),
            company_names    = company_names,
            fmp_api_key      = fmp_key,
            days_ahead       = 45,
        )
        stats = catalyst_summary.get('stats', {})
        print(
            f'  [CATALYST] {stats.get("total_ticker_catalysts", 0)} events | '
            f'{stats.get("earnings_count", 0)} earnings | '
            f'{stats.get("pdufa_count", 0)} PDUFA | '
            f'{stats.get("trial_count", 0)} trials | '
            f'{stats.get("imminent_p0", 0)} imminent'
        )
    except Exception as _cat_exc:
        print(f'  [WARN] Catalyst tracker skipped: {_cat_exc}')

    # ── 2. Load suppression registry + change detection ──────────────────────
    from ai_research.suppression_registry import (
        load_registry, save_registry, check_suppressed, update_registry,
    )
    from ai_research.change_detector import classify_change
    from ai_research.opportunity_selector import (
        build_opportunity_queue, save_opportunity_queue, split_decisions_by_queue,
    )

    registry = load_registry() if opportunity_mode else {}
    wm       = WatchlistManager(WATCHLIST_PATH)
    watchlist = {}
    try:
        watchlist = wm._load() if hasattr(wm, '_load') else {}
    except Exception:
        try:
            raw = _load_json_file(WATCHLIST_PATH)
            watchlist = raw if isinstance(raw, dict) else {}
        except Exception:
            watchlist = {}

    # ── 3. Run investment gate ────────────────────────────────────────────────
    decisions: list[dict] = []

    cap        = llm_cfg.max_cases_per_run
    gate_cases = cases[:cap] if limit is None else cases
    print(f'Step 2: Running research gate on {len(gate_cases)} case(s) ...')
    if effective_dry_run:
        print('  (dry-run: LLM will not be called; watchlist will not be updated)')
    if opportunity_mode:
        print('  (opportunity mode: suppressed+unchanged cases will skip LLM)')
    print()

    client = LLMClient(llm_cfg)
    suppressed_count = 0
    llm_called_count = 0

    for case in gate_cases:
        t = str(case.get('ticker', 'UNKNOWN')).upper()

        if opportunity_mode and not effective_dry_run:
            is_supp, supp_reason = check_suppressed(t, case, registry)
            if is_supp:
                from ai_research.change_detector import classify_change, UNCHANGED_SUPPRESSED
                change_status, _ = classify_change(case, registry, watchlist)
                if change_status == UNCHANGED_SUPPRESSED:
                    stub = _make_suppressed_stub(case, supp_reason)
                    decisions.append(stub)
                    suppressed_count += 1
                    continue

        # Inject catalyst context into case for prompt enrichment
        if catalyst_summary:
            from ai_research.catalyst_tracker import get_catalyst_context_for_ticker
            _cat_ctx = get_catalyst_context_for_ticker(t, catalyst_summary)
            if _cat_ctx:
                case = dict(case)
                case['_catalyst_context'] = _cat_ctx

        decision = run_gate(
            case,
            client        = client,
            dry_run       = effective_dry_run,
            force_refresh = force_refresh,
            depth         = depth,
        )
        decisions.append(decision)
        llm_called_count += 1

        case_json_path = _case_json_path(run_date, t)
        if case_json_path.exists():
            _inject_decision_into_case_file(case_json_path, decision)

        if not effective_dry_run:
            wm.update(ticker=t, decision=decision, case=case,
                      case_path=str(case_json_path))

    if opportunity_mode:
        print(f'  LLM calls made  : {llm_called_count}')
        print(f'  Suppressed stubs: {suppressed_count}')

    decision_errors  = _validate_decisions(
        [d for d in decisions if 'SUPPRESSED_UNCHANGED' not in str(d.get('note', ''))]
    )
    warnings    = [e for e in decision_errors if 'WARNING:' in e]
    hard_errors = [e for e in decision_errors if 'WARNING:' not in e]
    if hard_errors:
        print('Decision schema validation: FAIL')
        for err in hard_errors:
            print(f'  - {err}')
        return 1
    for w in warnings:
        print(f'  {w}')
    print()
    print(f'Decision schema validation: PASS ({len(decisions)} decision(s))')
    print(f'Gate complete: {len(decisions)} decision(s) made.')
    print()

    # ── 4. Update suppression registry ───────────────────────────────────────
    queue: dict | None = None
    if opportunity_mode and not effective_dry_run:
        for decision in decisions:
            if 'SUPPRESSED_UNCHANGED' in str(decision.get('note', '')):
                continue
            t    = str(decision.get('ticker', '')).upper()
            case = next((c for c in cases if str(c.get('ticker', '')).upper() == t), {})
            update_registry(t, decision, case, registry)
        save_registry(registry)
        print(f'  [SUPPRESS] Registry saved: {len(registry)} entries')

        queue = build_opportunity_queue(
            decisions               = decisions,
            cases                   = cases,
            registry                = registry,
            watchlist               = watchlist,
            max_suppressed_summary  = max_suppressed_summary,
            include_suppressed      = include_suppressed,
        )
        save_opportunity_queue(queue)

        print()
        print('Opportunity queue:')
        print(f'  P0 Escalate    : {len(queue.get("P0_ESCALATE_NOW", []))}')
        print(f'  P1 Human review: {len(queue.get("P1_HUMAN_REVIEW", []))}')
        print(f'  P2 Watchlist   : {len(queue.get("P2_WATCHLIST_SETUP", []))}')
        print(f'  P3 Monitor     : {len(queue.get("P3_MONITOR_CHANGE", []))}')
        print(f'  P4 Suppressed  : {queue.get("total_suppressed_full", 0)}')
        print(f'  No opportunity : {queue.get("no_opportunity", False)}')
        print()

    # ── 5. Paper portfolio — open positions on ESCALATE ──────────────────────
    portfolio_summary: dict | None = None
    try:
        import sys as _sys
        if str(_SRCDIR) not in _sys.path:
            _sys.path.insert(0, str(_SRCDIR))
        from paper_portfolio import (
            _enabled as _pp_enabled, load_portfolio, open_position,
            mark_positions, get_summary, save_portfolio,
        )
        if _pp_enabled() and not effective_dry_run:
            _portfolio = load_portfolio()
            _case_price: dict[str, float] = {
                str(c.get('ticker', '')).upper(): float(c['price'])
                for c in cases if c.get('price')
            }
            _new_positions = 0
            for _d in decisions:
                if _d.get('research_action') == 'ESCALATE':
                    _t     = str(_d.get('ticker', '')).upper()
                    _price = _case_price.get(_t)
                    if _price:
                        _portfolio = open_position(
                            ticker            = _t,
                            entry_price       = _price,
                            signal_date       = run_date,
                            signal_quality    = next(
                                (c.get('signal_quality', '') for c in cases
                                 if str(c.get('ticker', '')).upper() == _t), ''),
                            ai_classification = _d.get('classification', ''),
                            ai_confidence     = float(_d.get('confidence', 0)),
                            portfolio         = _portfolio,
                        )
                        _new_positions += 1
            if _new_positions:
                save_portfolio(_portfolio)
            portfolio_summary = get_summary(_portfolio)
            print(f'  [PORTFOLIO] Open: {portfolio_summary["total_open"]} | '
                  f'Deployed: {portfolio_summary["deployed_pct"]}% | '
                  f'Unrealized: {portfolio_summary["unrealized_weighted_pct"]:+.1f}%')
    except Exception as _pp_exc:
        print(f'  [PORTFOLIO] Skipped: {_pp_exc}')

    # ── 6. Mark stale watchlist entries ──────────────────────────────────────
    if not effective_dry_run:
        stale = wm.mark_stale(days=14)
        if stale:
            print(f'  Marked {len(stale)} watchlist entries as stale: {", ".join(stale)}')

    watchlist_summary = wm.summary()
    print('Watchlist after this run:')
    wm.print_summary()
    print()

    # ── 6. Write summary markdown ─────────────────────────────────────────────
    _write_summary(
        run_at            = run_at,
        cases             = cases,
        decisions         = decisions,
        dry_run           = effective_dry_run,
        ai_enabled        = ai_ready,
        watchlist_summary = watchlist_summary,
        opportunity_mode  = opportunity_mode,
        queue             = queue,
    )

    # ── 7. Send email ─────────────────────────────────────────────────────────
    if send_email:
        cache_hits = sum(1 for d in decisions if 'CACHE_HIT' in str(d.get('note', '')))
        run_metadata = {
            'run_at':             run_at,
            'model':              getattr(llm_cfg, 'model', 'unknown'),
            'ai_enabled':         ai_ready,
            'dry_run':            effective_dry_run,
            'case_count':         len(cases),
            'decision_count':     len(decisions),
            'cache_hits':         cache_hits,
            'opportunity_mode':   opportunity_mode,
            'suppressed_count':   suppressed_count,
            'llm_called_count':   llm_called_count,
        }
        from ai_research.ai_emailer import send_ai_research_email
        send_ai_research_email(
            decisions         = decisions,
            run_metadata      = run_metadata,
            strategic_brief   = strategic_brief,
            opportunity_queue = queue,
            catalyst_summary  = catalyst_summary,
            portfolio_summary = portfolio_summary,
        )

    return 0


# ── Evidence audit command ────────────────────────────────────────────────────

def run_evidence_audit(
    ticker: str | None = None,
    limit: int | None = None,
    fetch_text: bool = False,
) -> int:
    _load_env()
    from ai_research.research_case_builder import build_cases
    from ai_research.quote_extractor import compute_evidence_quality, extract_quotes

    print('AI Research Layer — Evidence Audit')
    print('===================================')
    print(f'Ticker filter : {ticker or "all"}')
    print(f'Limit         : {limit or "none"}')
    print(f'Fetch text    : {_bool_text(fetch_text)}')
    print()

    cases = build_cases(ticker=ticker, limit=limit, run_date=_today_utc(),
                        dry_run=True, verbose=False)

    if not cases:
        print('[INFO] No cases found. Run scanner first.')
        return 0

    rows: list[dict] = []
    for case in cases:
        t = case.get('ticker', '?')

        filing_text: str | None = None
        if fetch_text:
            from ai_research.source_fetcher import fetch_sec_filing_text_for_case
            print(f'  Fetching {t} ...', end=' ', flush=True)
            result = fetch_sec_filing_text_for_case(case)
            filing_text = result.get('text') or None
            fetch_error = result.get('error')
            cached      = result.get('cached', False)
            status      = 'cached' if cached else ('ok' if not fetch_error else f'FAIL: {fetch_error}')
            print(status)

        quotes = extract_quotes(case, filing_text)
        eq     = compute_evidence_quality(case, filing_text, quotes)
        case['evidence_quality'] = eq
        rows.append({
            'ticker':    t,
            'grade':     eq['evidence_grade'],
            'score':     eq['evidence_completeness_score'],
            'excerpt':   eq['excerpt_length'],
            'full':      eq['full_text_length'],
            'gaps':      len(eq['evidence_gaps']),
            'quotes':    len(quotes),
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
    _load_env()
    from ai_research.research_case_builder import build_cases
    from ai_research.quote_extractor import compute_evidence_quality, extract_quotes

    cases = build_cases(ticker=ticker.upper(), limit=1, run_date=_today_utc(),
                        dry_run=True, verbose=False)

    if not cases:
        print(f'[WARN] No case found for {ticker}. Run scanner first.')
        return 1

    case = cases[0]

    filing_text: str | None = None
    if fetch_text:
        from ai_research.source_fetcher import fetch_sec_filing_text_for_case
        result = fetch_sec_filing_text_for_case(case)
        filing_text = result.get('text') or None
        if result.get('error'):
            print(f'  [WARN] Fetch error: {result["error"]}')

    quotes = extract_quotes(case, filing_text)
    eq     = compute_evidence_quality(case, filing_text, quotes)

    print(f'Evidence Detail: {ticker}')
    print('=' * 60)
    print(f'  Ticker          : {case.get("ticker")}')
    print(f'  Company         : {case.get("company_name")}')
    print(f'  Signal quality  : {case.get("signal_quality")}')
    print(f'  Signal type     : {case.get("signal_type")}')
    print(f'  Filing type     : {case.get("filing_type") or "—"}')
    print(f'  Filing date     : {case.get("filing_date") or "—"}')
    print(f'  Source URL      : {case.get("source_url") or "—"}')
    print(f'  Trigger phrase  : {case.get("trigger_phrase") or "—"}')
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


# ── Plan command ──────────────────────────────────────────────────────────────

def print_plan(
    ticker: str | None = None,
    limit: int | None = None,
    depth: str | None = None,
) -> None:
    _load_env()
    from ai_research.llm_client import load_config as load_llm_config
    from ai_research.research_case_builder import build_cases
    from ai_research.investment_gate import cache_status

    llm_cfg = load_llm_config()
    depth   = depth or llm_cfg.default_depth
    live_allowed, live_reason = _live_call_allowed_reason(llm_cfg)

    cases = build_cases(ticker=ticker, limit=limit, run_date=_today_utc(),
                        dry_run=True, research_depth=depth, verbose=False)
    case_errors  = _validate_cases(cases)
    cap          = llm_cfg.max_cases_per_run
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
            t  = str(case.get('ticker', '?')).strip()
            fp, status = cache_status(case)
            estimated_action = 'would_reuse_cache' if status == 'hit' else 'would_call_llm'
            cls    = str(case.get('fp_classification', '?')).strip()
            action = str(case.get('recommended_scanner_action', '?')).strip()
            print(
                f'    {t:<8} cache={status:<4} estimated_action={estimated_action:<17} '
                f'fingerprint={fp} scanner={cls or "-"} action={action or "-"}'
            )
    else:
        print('  No cases found: run scanner first.')

    print()
    print('  Plan mode wrote no files and made no LLM calls.')


def print_opportunity_plan(
    ticker: str | None = None,
    limit: int | None = None,
    depth: str | None = None,
) -> None:
    """Preview what opportunity mode would select — no LLM calls, no files written."""
    _load_env()
    from ai_research.llm_client import load_config as load_llm_config
    from ai_research.research_case_builder import build_cases
    from ai_research.opportunity_selector import print_opportunity_plan as _opp_plan

    llm_cfg = load_llm_config()
    depth   = depth or llm_cfg.default_depth

    cases = build_cases(ticker=ticker, limit=limit, run_date=_today_utc(),
                        dry_run=True, research_depth=depth, verbose=False)

    from ai_research.suppression_registry import load_registry
    registry  = load_registry()
    watchlist = _load_json_file(WATCHLIST_PATH) or {}

    print('AI Research Layer — Opportunity Plan')
    print('=====================================')
    print(f'  Cases available   : {len(cases)}')
    print(f'  Registry entries  : {len(registry)}')
    print()
    _opp_plan(cases, registry, watchlist)
    print('  No files written. No LLM calls made.')


# ── Suppression status command ────────────────────────────────────────────────

def print_suppression_status() -> None:
    _load_env()
    from ai_research.suppression_registry import load_registry, get_suppression_summary

    registry = load_registry()
    summary  = get_suppression_summary(registry)

    print('AI Research Layer — Suppression Registry Status')
    print('================================================')
    print(f'  Registry path     : {SUPPRESSION_PATH}')
    print(f'  Total suppressed  : {summary["total_suppressed"]}')
    print()

    if summary['by_reason']:
        print('  By reason:')
        for reason, count in sorted(summary['by_reason'].items()):
            print(f'    {reason:<30} {count}')
        print()

    if summary['by_classification']:
        print('  By classification:')
        for cls, count in sorted(summary['by_classification'].items()):
            print(f'    {cls:<40} {count}')
        print()

    if summary['top_repeated']:
        print('  Top repeated (by times_seen):')
        for rec in summary['top_repeated']:
            ticker     = rec.get('ticker', '?')
            times      = rec.get('times_seen', 0)
            cls        = rec.get('classification', '?')
            last_seen  = rec.get('last_seen_at', '')[:10]
            reason     = rec.get('suppression_reason', '')[:60]
            print(f'    {ticker:<8} seen={times:<4} cls={cls:<30} last={last_seen}')
            print(f'           reason: {reason}')
        print()

    if summary['last_suppressed_date']:
        print(f'  Last suppressed   : {summary["last_suppressed_date"][:10]}')

    print()
    print('  Unsuppression rules:')
    print('    - New source URL for the ticker')
    print('    - New filing date for the ticker')
    print('    - New signal type for the ticker')
    print('    - Action changes from DISCARD to WATCH/ESCALATE/NEEDS_HUMAN_REVIEW')
    print('    - force_unsuppress flag set manually')
    print()
    print('  Management commands:')
    print('    --force-unsuppress TICKER   Set force_unsuppress flag (re-analyze next run)')
    print('    --clear-suppression TICKER  Remove ticker entirely from registry')


# ── Status command ────────────────────────────────────────────────────────────

def print_status() -> None:
    _load_env()
    from ai_research.llm_client import LLMClient, load_config as load_llm_config
    from ai_research.watchlist_manager import WatchlistManager
    from ai_research.suppression_registry import load_registry

    llm_cfg = load_llm_config()
    client  = LLMClient(llm_cfg)
    wm      = WatchlistManager(WATCHLIST_PATH)
    registry       = load_registry()
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
    print(f'  Suppression registry            : {len(registry)} entries ({SUPPRESSION_PATH})')
    print(f'  Cache path                      : {CACHE_DIR}')
    print(f'  Latest AI summary path          : {SUMMARY_PATH}')
    print(f'  Live LLM call allowed           : {_bool_text(live_allowed)} ({live_reason})')
    print(f'  LLM client status               : {client.status_message}')
    print()
    wm.print_summary()

    if SUMMARY_PATH.exists():
        print()
        print(f'Last summary: {SUMMARY_PATH}')


EMAIL_PREVIEW_DIR = AI_RESEARCH_DIR / 'email_preview'


def run_email_preview(
    ticker: str | None = None,
    limit: int | None = None,
    depth: str | None = None,
    strategic_brief: bool = False,
    opportunity_mode: bool = False,
) -> int:
    """
    Generate email preview to data/ai_research/email_preview/ without sending.
    Uses cached AI decisions from case files; dry-run placeholders for uncached cases.
    Does NOT call the LLM unless explicitly configured otherwise.
    """
    _load_env()
    from ai_research.llm_client import load_config as load_llm_config
    from ai_research.research_case_builder import build_cases
    from ai_research.investment_gate import _dry_run_decision

    llm_cfg = load_llm_config()
    run_at  = _utc_now()
    run_date = _today_utc()
    preview_depth = depth or 'diligence_memo'

    print('AI Research Layer — Email Preview')
    print('===================================')
    print(f'  Run at      : {run_at}')
    print(f'  Depth       : {preview_depth}')
    print(f'  Ticker      : {ticker or "all (latest)"}')
    print(f'  Limit       : {limit or "none"}')
    print()

    EMAIL_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    html_path = EMAIL_PREVIEW_DIR / 'latest_ai_email_preview.html'
    txt_path  = EMAIL_PREVIEW_DIR / 'latest_ai_email_preview.txt'

    cases = build_cases(ticker=ticker, limit=limit, run_date=run_date,
                        dry_run=True, research_depth=preview_depth, verbose=False)
    if not cases:
        print('[INFO] No cases found. Run scanner first.')
        return 0

    print(f'  Cases found : {len(cases)}')

    # Load cached decisions from case JSON files
    decisions: list[dict] = []
    covered: set[str] = set()
    for case in cases:
        t = str(case.get('ticker', '')).upper()
        case_path = _case_json_path(run_date, t)
        if case_path.exists():
            try:
                case_data = json.loads(case_path.read_text(encoding='utf-8'))
                ai_dec = case_data.get('ai_decision')
                if ai_dec and isinstance(ai_dec, dict):
                    ai_dec.setdefault('company_name', case.get('company_name', ''))
                    decisions.append(ai_dec)
                    covered.add(t)
            except Exception:
                pass

    # Fill uncached cases with dry-run placeholders
    placeholder_count = 0
    for case in cases:
        t = str(case.get('ticker', '')).upper()
        if t not in covered:
            stub = _dry_run_decision(t, note='EMAIL_PREVIEW_PLACEHOLDER')
            stub['company_name'] = case.get('company_name', '')
            decisions.append(stub)
            placeholder_count += 1

    if placeholder_count:
        print(f'  [NOTE] {placeholder_count} case(s) have no cached decisions — '
              f'using dry-run placeholders. Run with --latest --depth diligence_memo for live analysis.')
        print(f'  [NOTE] LLM was NOT called for this preview.')
    else:
        print(f'  [NOTE] All {len(decisions)} case(s) loaded from cache. LLM not called.')

    # Build opportunity queue if opportunity_mode
    queue: dict | None = None
    if opportunity_mode:
        from ai_research.suppression_registry import load_registry
        from ai_research.opportunity_selector import build_opportunity_queue
        registry = load_registry()
        watchlist = _load_json_file(WATCHLIST_PATH) or {}
        queue = build_opportunity_queue(
            decisions=decisions,
            cases=cases,
            registry=registry,
            watchlist=watchlist,
        )

    run_metadata = {
        'run_at':           run_at,
        'model':            llm_cfg.model,
        'ai_enabled':       llm_cfg.enabled,
        'dry_run':          True,
        'case_count':       len(cases),
        'decision_count':   len(decisions),
        'cache_hits':       len(decisions) - placeholder_count,
        'opportunity_mode': opportunity_mode,
        'suppressed_count': 0,
        'llm_called_count': 0,
    }

    from ai_research.ai_emailer import (
        build_ai_email_html, build_ai_email_plain,
        build_ai_email_subject, load_ai_email_config,
    )
    cfg     = load_ai_email_config()
    subject = build_ai_email_subject(decisions, cfg['subject_prefix'], opportunity_queue=queue)
    body_html  = build_ai_email_html(decisions, run_metadata, strategic_brief=strategic_brief,
                                      opportunity_queue=queue)
    body_plain = build_ai_email_plain(decisions, run_metadata, strategic_brief=strategic_brief,
                                       opportunity_queue=queue)

    html_path.write_text(body_html,  encoding='utf-8')
    txt_path.write_text(body_plain,  encoding='utf-8')

    print()
    print(f'  [PREVIEW] Subject   : {subject}')
    print(f'  [PREVIEW] HTML file : {html_path.relative_to(REPO)}')
    print(f'  [PREVIEW] Text file : {txt_path.relative_to(REPO)}')
    print(f'  [PREVIEW] Email NOT sent.')
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description='AI research layer orchestrator - research gate, not trading signal.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  --latest --limit 10\n'
            '  --latest --limit 10 --evidence-audit\n'
            '  --latest --limit 10 --opportunity-mode --email\n'
            '  --latest --limit 20 --opportunity-plan\n'
            '  --latest --limit 20 --opportunity-mode --dry-run\n'
            '  --suppression-status\n'
            '  --force-unsuppress AAPL\n'
            '  --clear-suppression AAPL\n'
            '  --status\n'
            '  --email-latest-summary\n'
        ),
    )
    mode = p.add_mutually_exclusive_group(required=False)
    mode.add_argument('--latest', action='store_true',
                      help='Build cases + run gate from latest scanner outputs')
    mode.add_argument('--ticker', metavar='TICKER',
                      help='Run for a single ticker')
    mode.add_argument('--status', action='store_true',
                      help='Print current watchlist + config summary')
    mode.add_argument('--suppression-status', action='store_true',
                      help='Print suppression registry status')
    mode.add_argument('--show-evidence', metavar='TICKER',
                      help='Print full evidence detail for a single ticker')
    mode.add_argument('--inspect-source-fields', action='store_true',
                      help='Print source field availability table')
    mode.add_argument('--email-latest-summary', action='store_true',
                      help='Send latest AI summary email without rerunning LLM')
    mode.add_argument('--force-unsuppress', metavar='TICKER',
                      help='Set force_unsuppress flag for a ticker in the registry')
    mode.add_argument('--clear-suppression', metavar='TICKER',
                      help='Remove a ticker completely from the suppression registry')

    # Modifiers
    p.add_argument('--evidence-audit', action='store_true',
                   help='Print evidence grade table')
    p.add_argument('--plan', action='store_true',
                   help='Preview what would run — no LLM calls, no files written')
    p.add_argument('--opportunity-plan', action='store_true',
                   help='Preview opportunity selector decisions — no LLM, no files written')
    p.add_argument('--limit',   type=int, default=None,
                   help='Max cases to process')
    p.add_argument('--depth', default='fast_gate',
                   choices=['fast_gate', 'deep', 'diligence_memo'],
                   help='Research depth preset (default: fast_gate; diligence_memo fetches filing text + produces full research memo)')
    p.add_argument('--dry-run', action='store_true',
                   help='Build cases but do not call LLM')
    p.add_argument('--force-refresh', action='store_true',
                   help='Bypass cache and rerun LLM for all cases')
    p.add_argument('--force-refresh-email-analysis', action='store_true',
                   help='Force richer email synthesis: bypass LLM cache for active cases while respecting suppression rules')
    p.add_argument('--email-preview', action='store_true',
                   help='Generate email HTML/text preview to file without sending (uses cached decisions, no LLM)')
    p.add_argument('--fetch-text', action='store_true',
                   help='Fetch full filing text from source URL')
    p.add_argument('--email', action='store_true',
                   help='Send branded AI research email after run')
    p.add_argument('--strategic-brief', action='store_true',
                   help='Include strategic analysis fields in email')
    p.add_argument('--include-completed-analogues', action='store_true',
                   help='Include completed deal analogues in research (no-op: wired in prompts)')
    p.add_argument('--probability-analysis', action='store_true',
                   help='Include acquisition probability analysis (no-op: wired in gate)')
    p.add_argument('--opportunity-mode', action='store_true',
                   help='Apply suppression registry; email focuses on P0-P3 only')
    p.add_argument('--include-suppressed', action='store_true',
                   help='Include all suppressed cases in output (with --opportunity-mode)')
    p.add_argument('--max-suppressed-summary', type=int, default=5,
                   help='Max suppressed cases shown in email archive (default: 5)')

    args = p.parse_args(argv)

    has_primary = (
        args.latest or args.ticker or args.status or args.suppression_status
        or args.show_evidence or args.inspect_source_fields or args.email_latest_summary
        or args.force_unsuppress or args.clear_suppression
    )
    has_modifier = args.evidence_audit or args.plan or args.opportunity_plan or args.dry_run

    if not has_primary and not has_modifier and not args.email_preview:
        p.error(
            'specify a mode: --latest, --ticker TICKER, --status, --suppression-status, '
            '--show-evidence TICKER, --email-latest-summary, '
            '--force-unsuppress TICKER, --clear-suppression TICKER; '
            'or use --email-preview [--latest] [--limit N] for preview'
        )
    if has_modifier and not args.email_preview and not (args.latest or args.ticker):
        p.error('--evidence-audit, --plan, --opportunity-plan, and --dry-run require --latest or --ticker')

    return args


def main(argv=None) -> int:
    args = _parse_args(argv)

    if args.email_preview:
        ticker = args.ticker.upper() if args.ticker else None
        _load_env()
        from ai_research.llm_client import load_config as load_llm_config
        llm_cfg = load_llm_config()
        depth   = args.depth or llm_cfg.default_depth
        return run_email_preview(
            ticker           = ticker,
            limit            = args.limit,
            depth            = depth,
            strategic_brief  = args.strategic_brief,
            opportunity_mode = args.opportunity_mode,
        )

    if args.status:
        print_status()
        return 0

    if args.suppression_status:
        print_suppression_status()
        return 0

    if args.force_unsuppress:
        _load_env()
        from ai_research.suppression_registry import load_registry, save_registry, force_unsuppress
        registry = load_registry()
        ticker   = args.force_unsuppress.upper()
        if force_unsuppress(ticker, registry):
            save_registry(registry)
            print(f'[SUPPRESS] force_unsuppress set for {ticker}. '
                  f'Will re-analyze on next --opportunity-mode run.')
        else:
            print(f'[SUPPRESS] {ticker} not found in suppression registry.')
        return 0

    if args.clear_suppression:
        _load_env()
        from ai_research.suppression_registry import load_registry, save_registry, clear_suppression
        registry = load_registry()
        ticker   = args.clear_suppression.upper()
        if clear_suppression(ticker, registry):
            save_registry(registry)
            print(f'[SUPPRESS] {ticker} removed from suppression registry.')
        else:
            print(f'[SUPPRESS] {ticker} was not in suppression registry.')
        return 0

    if args.evidence_audit:
        return run_evidence_audit(ticker=None, limit=args.limit, fetch_text=args.fetch_text)

    if args.show_evidence:
        return run_show_evidence(args.show_evidence.upper(), fetch_text=args.fetch_text)

    if args.email_latest_summary:
        _load_env()
        from ai_research.ai_emailer import send_latest_summary_email
        result = send_latest_summary_email(force=True)
        return 0 if result.get('sent') else 1

    _load_env()
    from ai_research.llm_client import load_config as load_llm_config
    llm_cfg = load_llm_config()
    depth   = args.depth or llm_cfg.default_depth

    if args.opportunity_plan:
        ticker = args.ticker.upper() if args.ticker else None
        print_opportunity_plan(ticker=ticker, limit=args.limit, depth=depth)
        return 0

    if args.plan:
        ticker = args.ticker.upper() if args.ticker else None
        print_plan(ticker=ticker, limit=args.limit, depth=depth)
        return 0

    if args.inspect_source_fields:
        from ai_research.research_case_builder import build_cases
        cases = build_cases(ticker=None, limit=args.limit, run_date=_today_utc(),
                            dry_run=True, verbose=False)
        if not cases:
            print('[INFO] No cases found.')
            return 0
        fields_to_check = ['source_url', 'accession', 'filing_date', 'filing_type',
                           'source_excerpt', 'trigger_phrase', 'signal_type', 'signal_quality']
        print(f'{"Ticker":<10}' + ''.join(f'  {f[:12]:<12}' for f in fields_to_check))
        print('-' * (10 + len(fields_to_check) * 14))
        for c in cases[:args.limit or 20]:
            t = c.get('ticker', '?')
            row = f'{t:<10}'
            for f in fields_to_check:
                val = c.get(f)
                row += f'  {"Y" if val else ".":<12}'
            print(row)
        return 0

    ticker = args.ticker.upper() if args.ticker else None
    # --force-refresh-email-analysis: bypass LLM cache for active cases (suppression respected)
    effective_force_refresh = args.force_refresh or getattr(args, 'force_refresh_email_analysis', False)
    return run(
        ticker                  = ticker,
        limit                   = args.limit,
        dry_run                 = args.dry_run,
        depth                   = depth,
        force_refresh           = effective_force_refresh,
        send_email              = args.email,
        strategic_brief         = args.strategic_brief,
        opportunity_mode        = args.opportunity_mode,
        include_suppressed      = args.include_suppressed,
        max_suppressed_summary  = args.max_suppressed_summary,
    )


if __name__ == '__main__':
    sys.exit(main())
