"""
test_opportunity_selector_smoke.py — Smoke tests for suppression registry,
change detector, and opportunity selector.

Run:
  python3 src/ai_research/test_opportunity_selector_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
if str(_SRCDIR) not in sys.path:
    sys.path.insert(0, str(_SRCDIR))

from ai_research.suppression_registry import (
    load_registry, save_registry, check_suppressed, update_registry,
    force_unsuppress, clear_suppression, get_suppression_summary,
)
from ai_research.change_detector import (
    classify_change, compute_evidence_fingerprint, compute_source_fingerprint,
    NEW_CASE, CHANGED_EVIDENCE, CHANGED_SOURCE, CHANGED_DECISION,
    UNCHANGED_SUPPRESSED, UNCHANGED_ACTIVE,
)
from ai_research.opportunity_selector import (
    build_opportunity_queue, split_decisions_by_queue,
    P0_ESCALATE_NOW, P1_HUMAN_REVIEW, P2_WATCHLIST_SETUP,
    P3_MONITOR_CHANGE, P4_SUPPRESSED,
)

_PASS = 0
_FAIL = 0


def _ok(name: str) -> None:
    global _PASS
    _PASS += 1
    print(f'  PASS  {name}')


def _fail(name: str, detail: str = '') -> None:
    global _FAIL
    _FAIL += 1
    msg = f'  FAIL  {name}'
    if detail:
        msg += f': {detail}'
    print(msg)


def _assert(name: str, condition: bool, detail: str = '') -> None:
    if condition:
        _ok(name)
    else:
        _fail(name, detail)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _case(ticker: str = 'TEST', extra: dict | None = None) -> dict:
    base = {
        'ticker':        ticker,
        'company_name':  f'{ticker} Corp',
        'signal_type':   'ACQUISITION_LANGUAGE',
        'source_url':    f'https://sec.gov/Archives/{ticker}/0001234.htm',
        'accession':     '0001234567-24-000001',
        'filing_date':   '2024-01-15',
        'filing_type':   '10-K',
        'source_excerpt': 'The Company is reviewing strategic alternatives including a potential sale.',
        'trigger_phrase': 'strategic alternatives',
        'signal_quality': 'PROCESS',
    }
    if extra:
        base.update(extra)
    return base


def _decision(
    ticker: str = 'TEST',
    action: str = 'DISCARD',
    cls: str = 'ALREADY_ANNOUNCED_DEAL',
    extra: dict | None = None,
) -> dict:
    base = {
        'ticker':                             ticker,
        'company_name':                       f'{ticker} Corp',
        'research_action':                    action,
        'classification':                     cls,
        'confidence':                         0.8,
        'investability_score':                10,
        'evidence_grade':                     'D',
        'strategy_bucket':                    'already-announced',
        'matched_false_positive_archetypes':  ['ALREADY_ANNOUNCED_MERGER'],
        'matched_true_signal_archetypes':     [],
        'note':                               '',
    }
    if extra:
        base.update(extra)
    return base


# ── Test 1: Already-announced DISCARD gets suppressed after first decision ────

def test_discard_gets_suppressed() -> None:
    registry: dict = {}
    case     = _case('AANN')
    decision = _decision('AANN', action='DISCARD', cls='ALREADY_ANNOUNCED_DEAL')

    update_registry('AANN', decision, case, registry)
    _assert('discard_enters_registry', 'AANN' in registry)
    _assert('discard_reason_set', bool(registry.get('AANN', {}).get('suppression_reason')))
    _assert('discard_action_stored', registry.get('AANN', {}).get('action') == 'DISCARD')


# ── Test 2: Unchanged suppressed case does not re-enter main queue ─────────

def test_unchanged_suppressed_stays_out() -> None:
    registry: dict = {}
    case     = _case('UNCA')
    decision = _decision('UNCA', action='DISCARD', cls='ALREADY_ANNOUNCED_DEAL')

    update_registry('UNCA', decision, case, registry)

    # Same case again — should be suppressed
    is_supp, reason = check_suppressed('UNCA', case, registry)
    _assert('unchanged_suppressed_is_suppressed', is_supp,
            f'expected suppressed, got is_supp={is_supp} reason={reason}')

    change_status, _ = classify_change(case, registry)
    _assert('unchanged_suppressed_status', change_status == UNCHANGED_SUPPRESSED,
            f'expected UNCHANGED_SUPPRESSED, got {change_status}')


# ── Test 3: Changed source URL unsuppresses ───────────────────────────────

def test_changed_source_unsuppresses() -> None:
    registry: dict = {}
    case     = _case('CHSRC')
    decision = _decision('CHSRC', action='DISCARD', cls='ALREADY_ANNOUNCED_DEAL')
    update_registry('CHSRC', decision, case, registry)

    # New source URL
    new_case = _case('CHSRC', extra={
        'source_url': 'https://sec.gov/Archives/CHSRC/0009999.htm',
        'accession':  '0009999999-24-000099',
    })
    is_supp, reason = check_suppressed('CHSRC', new_case, registry)
    _assert('changed_source_not_suppressed', not is_supp,
            f'expected unsuppressed, got is_supp={is_supp} reason={reason}')

    change_status, _ = classify_change(new_case, registry)
    _assert('changed_source_status', change_status == CHANGED_SOURCE,
            f'expected CHANGED_SOURCE, got {change_status}')


# ── Test 4: WATCH case stays in main queue ────────────────────────────────

def test_watch_stays_in_queue() -> None:
    registry: dict = {}
    case     = _case('WWATCH')
    decision = _decision('WWATCH', action='WATCH', cls='PRE_PROCESS_OPPORTUNITY')

    update_registry('WWATCH', decision, case, registry)
    _assert('watch_not_suppressed', 'WWATCH' not in registry,
            'WATCH case should not be added to suppression registry')

    is_supp, _ = check_suppressed('WWATCH', case, registry)
    _assert('watch_check_not_suppressed', not is_supp)


# ── Test 5: ESCALATE always appears ──────────────────────────────────────

def test_escalate_always_in_queue() -> None:
    registry  : dict = {}
    watchlist : dict = {}
    cases     = [_case('ESC1')]
    decisions = [_decision('ESC1', action='ESCALATE', cls='PRE_PROCESS_OPPORTUNITY',
                            extra={'investability_score': 80})]

    queue = build_opportunity_queue(decisions, cases, registry, watchlist)
    esc_tickers = [e['ticker'] for e in queue.get(P0_ESCALATE_NOW, [])]
    _assert('escalate_in_p0', 'ESC1' in esc_tickers,
            f'P0 tickers: {esc_tickers}')

    active, suppressed = split_decisions_by_queue(queue, decisions)
    _assert('escalate_in_active', any(d['ticker'] == 'ESC1' for d in active),
            f'active: {[d["ticker"] for d in active]}')
    _assert('escalate_not_suppressed', not any(d['ticker'] == 'ESC1' for d in suppressed))


# ── Test 6: No-opportunity state when all suppressed ─────────────────────

def test_no_opportunity_state() -> None:
    registry : dict = {}
    watchlist: dict = {}

    tickers = ['NOP1', 'NOP2', 'NOP3']
    cases     = [_case(t) for t in tickers]
    decisions = [_decision(t, action='DISCARD', cls='ALREADY_ANNOUNCED_DEAL') for t in tickers]

    for decision, case in zip(decisions, cases):
        update_registry(decision['ticker'], decision, case, registry)

    queue = build_opportunity_queue(decisions, cases, registry, watchlist)
    _assert('no_opp_state_set', queue.get('no_opportunity') is True,
            f'no_opportunity={queue.get("no_opportunity")}')
    _assert('no_opp_total_active_zero', queue.get('total_active', 999) == 0,
            f'total_active={queue.get("total_active")}')
    _assert('no_opp_suppressed_count', queue.get('total_suppressed_full', 0) == len(tickers),
            f'total_suppressed={queue.get("total_suppressed_full")}')


# ── Test 7: Suppression registry does not delete records accidentally ─────

def test_registry_preserves_records() -> None:
    registry: dict = {}

    for i in range(5):
        t        = f'SAFE{i}'
        case     = _case(t)
        decision = _decision(t, action='DISCARD', cls='ALREADY_ANNOUNCED_DEAL')
        update_registry(t, decision, case, registry)

    _assert('registry_has_5', len(registry) == 5,
            f'registry has {len(registry)} entries')

    # Run same cases again — should increment times_seen, not delete
    for i in range(5):
        t        = f'SAFE{i}'
        case     = _case(t)
        decision = _decision(t, action='DISCARD', cls='ALREADY_ANNOUNCED_DEAL')
        update_registry(t, decision, case, registry)

    _assert('registry_still_5', len(registry) == 5,
            f'registry has {len(registry)} entries after second run')
    _assert('times_seen_incremented',
            all(registry[f'SAFE{i}'].get('times_seen', 0) == 2 for i in range(5)),
            'expected times_seen=2 for all')


# ── Test 8: Force unsuppress flag works ───────────────────────────────────

def test_force_unsuppress() -> None:
    registry: dict = {}
    case     = _case('FRC')
    decision = _decision('FRC', action='DISCARD', cls='ALREADY_ANNOUNCED_DEAL')
    update_registry('FRC', decision, case, registry)

    # Confirm suppressed
    is_supp, _ = check_suppressed('FRC', case, registry)
    _assert('force_unsuppress_pre_suppressed', is_supp)

    # Set force_unsuppress
    result = force_unsuppress('FRC', registry)
    _assert('force_unsuppress_returns_true', result)

    is_supp_after, reason = check_suppressed('FRC', case, registry)
    _assert('force_unsuppress_clears_suppression', not is_supp_after,
            f'is_supp={is_supp_after} reason={reason}')

    change_status, _ = classify_change(case, registry)
    _assert('force_unsuppress_change_status', change_status == CHANGED_DECISION,
            f'expected CHANGED_DECISION, got {change_status}')


# ── Test 9: Clear suppression removes record ──────────────────────────────

def test_clear_suppression() -> None:
    registry: dict = {}
    case     = _case('CLR')
    decision = _decision('CLR', action='DISCARD', cls='ALREADY_ANNOUNCED_DEAL')
    update_registry('CLR', decision, case, registry)
    _assert('clear_pre_exists', 'CLR' in registry)

    result = clear_suppression('CLR', registry)
    _assert('clear_returns_true', result)
    _assert('clear_removed', 'CLR' not in registry)

    result2 = clear_suppression('NONEXISTENT', registry)
    _assert('clear_missing_returns_false', not result2)


# ── Test 10: New filing date unsuppresses ────────────────────────────────

def test_new_filing_date_unsuppresses() -> None:
    registry: dict = {}
    case     = _case('NDTST')
    decision = _decision('NDTST', action='DISCARD', cls='ALREADY_ANNOUNCED_DEAL')
    update_registry('NDTST', decision, case, registry)

    new_case = _case('NDTST', extra={'filing_date': '2025-06-01'})
    is_supp, reason = check_suppressed('NDTST', new_case, registry)
    _assert('new_date_not_suppressed', not is_supp,
            f'is_supp={is_supp} reason={reason}')


# ── Test 11: Suppression summary stats ───────────────────────────────────

def test_suppression_summary() -> None:
    registry: dict = {}
    tickers = ['SS1', 'SS2', 'SS3']
    for t in tickers:
        update_registry(t, _decision(t, 'DISCARD', 'ALREADY_ANNOUNCED_DEAL'), _case(t), registry)

    summary = get_suppression_summary(registry)
    _assert('summary_total', summary['total_suppressed'] == 3,
            f'total={summary["total_suppressed"]}')
    _assert('summary_has_by_reason', bool(summary['by_reason']))
    _assert('summary_top_repeated', len(summary['top_repeated']) <= 10)


# ── Test 12: Opportunity queue splits correctly ───────────────────────────

def test_queue_split() -> None:
    registry : dict = {}
    watchlist: dict = {}

    # Mix: 1 ESCALATE, 1 WATCH, 2 suppressed DISCARD
    cases = [_case('ESC'), _case('WCH'), _case('DSC1'), _case('DSC2')]
    decisions = [
        _decision('ESC',  'ESCALATE',         'PRE_PROCESS_OPPORTUNITY', {'investability_score': 90}),
        _decision('WCH',  'WATCH',             'REAL_STRATEGIC_REVIEW',  {'investability_score': 60}),
        _decision('DSC1', 'DISCARD',           'ALREADY_ANNOUNCED_DEAL', {}),
        _decision('DSC2', 'DISCARD',           'FALSE_POSITIVE',         {}),
    ]

    # Pre-suppress DSC1, DSC2
    for i, d in enumerate(decisions[2:], start=2):
        update_registry(d['ticker'], d, cases[i], registry)

    queue = build_opportunity_queue(decisions, cases, registry, watchlist)
    _assert('queue_p0_has_esc', any(e['ticker'] == 'ESC' for e in queue.get(P0_ESCALATE_NOW, [])))
    _assert('queue_p2_has_watch', any(e['ticker'] == 'WCH' for e in queue.get(P2_WATCHLIST_SETUP, [])))
    _assert('queue_suppressed_count', queue.get('total_suppressed_full', 0) >= 2,
            f'suppressed={queue.get("total_suppressed_full")}')

    active, suppressed = split_decisions_by_queue(queue, decisions)
    active_tickers = [d['ticker'] for d in active]
    _assert('active_has_esc', 'ESC' in active_tickers)
    _assert('active_has_wch', 'WCH' in active_tickers)
    _assert('suppressed_has_dsc1', any(d['ticker'] == 'DSC1' for d in suppressed))
    _assert('active_excludes_dsc', 'DSC1' not in active_tickers and 'DSC2' not in active_tickers,
            f'active_tickers={active_tickers}')


# ── Runner ────────────────────────────────────────────────────────────────────

def main() -> int:
    print('Opportunity Selector — Smoke Tests')
    print('====================================')

    tests = [
        test_discard_gets_suppressed,
        test_unchanged_suppressed_stays_out,
        test_changed_source_unsuppresses,
        test_watch_stays_in_queue,
        test_escalate_always_in_queue,
        test_no_opportunity_state,
        test_registry_preserves_records,
        test_force_unsuppress,
        test_clear_suppression,
        test_new_filing_date_unsuppresses,
        test_suppression_summary,
        test_queue_split,
    ]

    for test_fn in tests:
        name = test_fn.__name__
        try:
            test_fn()
        except Exception as exc:
            _fail(name, f'EXCEPTION: {exc}')

    print()
    print(f'Results: {_PASS} passed, {_FAIL} failed, {_PASS + _FAIL} total')

    if _FAIL > 0:
        print('SMOKE TEST FAILED')
        return 1

    print('SMOKE TEST PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
