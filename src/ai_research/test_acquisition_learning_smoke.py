"""
test_acquisition_learning_smoke.py — Smoke tests for acquisition learning engine.

Run: python3 src/ai_research/test_acquisition_learning_smoke.py

These tests are deterministic and do not require LLM, API keys, or live data.
Failures indicate a code bug, not a data availability issue.
"""
from __future__ import annotations

import sys
import os

# Ensure src/ is on path for direct script execution
_HERE   = os.path.dirname(os.path.abspath(__file__))
_SRCDIR = os.path.dirname(_HERE)
_REPO   = os.path.dirname(_SRCDIR)
if _SRCDIR not in sys.path:
    sys.path.insert(0, _SRCDIR)


# ── Test helpers ──────────────────────────────────────────────────────────────

def _make_case(**overrides) -> dict:
    """Make a minimal live case dict for testing."""
    base = {
        'ticker':                  'TEST',
        'company_name':            'Test Pharma Inc.',
        'signal_type':             'STRATEGIC_ALTERNATIVES',
        'trigger_phrase':          '',
        'source_excerpt':          '',
        'memo_section_excerpt':    '',
        'scanner_flags':           [],
        'fp_classification':       '',
        'filing_type':             '8-K',
        'filing_date':             '2026-05-01',
        'evidence_quality':        {
            'evidence_grade':            'C',
            'evidence_completeness_score': 50,
            'evidence_gaps':             [],
            'top_evidence_quotes':       [],
            'has_full_filing_text':      False,
        },
        'matched_true_signal_archetypes': [],
    }
    base.update(overrides)
    return base


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_cases_load():
    """Completed acquisition cases load without error."""
    from ai_research.acquisition_case_library import load_completed_acquisition_cases
    cases = load_completed_acquisition_cases()
    assert isinstance(cases, list), f'Expected list, got {type(cases)}'
    assert len(cases) > 0, 'No cases loaded — seed file may be missing or empty'
    print(f'  Loaded {len(cases)} cases')


def test_canonical_cases_exist():
    """MDVN, DMTX, TSRO exist in library."""
    from ai_research.acquisition_case_library import load_completed_acquisition_cases
    cases = load_completed_acquisition_cases()
    tickers = {c.get('ticker') for c in cases}

    for expected in ('MDVN', 'DMTX', 'TSRO'):
        assert expected in tickers, f'Expected canonical case {expected} not found in library'
    print(f'  Found canonical cases: MDVN, DMTX, TSRO')


def test_already_announced_gets_low_bucket():
    """Case with merger agreement language gets P1_DISCARD_ALREADY_ANNOUNCED."""
    from ai_research.acquisition_situation_classifier import classify_acquisition_situation

    case = _make_case(
        trigger_phrase='agreement and plan of merger',
        source_excerpt=(
            'The Company entered into a definitive merger agreement and plan of merger '
            'pursuant to which the Company will be acquired. The merger consideration '
            'is $42.00 per share. The go-shop period expires 30 days from execution.'
        ),
        filing_type='DEFM14A',
    )

    result = classify_acquisition_situation(case)
    bucket = result.get('probability_bucket', '')
    assert bucket == 'P1_DISCARD_ALREADY_ANNOUNCED', (
        f'Expected P1_DISCARD_ALREADY_ANNOUNCED, got {bucket!r}. '
        f'Scores: {result.get("situation_scores", {})}'
    )
    print(f'  Bucket: {bucket} (correct)')


def test_strategic_alternatives_gets_higher_score():
    """Strategic alternatives + advisor retained gets P4 or P5 setup score."""
    from ai_research.acquisition_situation_classifier import classify_acquisition_situation

    case = _make_case(
        trigger_phrase='strategic alternatives',
        source_excerpt=(
            'The Board of Directors has formed a special committee to review and evaluate '
            'all strategic alternatives. The Company has retained Morgan Stanley as its '
            'financial advisor to assist in exploring strategic options, including a potential '
            'sale of the Company.'
        ),
        filing_type='8-K',
    )

    result = classify_acquisition_situation(case)
    bucket = result.get('probability_bucket', '')
    assert bucket in ('P4_RESEARCH_PRIORITY', 'P5_HIGH_PRIORITY_PROCESS_SIGNAL'), (
        f'Expected P4 or P5, got {bucket!r}. '
        f'Scores: {result.get("situation_scores", {})}'
    )
    print(f'  Bucket: {bucket} (correct)')


def test_catalyst_only_is_watch_not_process():
    """Phase 3 catalyst only case is P3_WATCHLIST_SETUP, not P5."""
    from ai_research.acquisition_situation_classifier import classify_acquisition_situation

    case = _make_case(
        trigger_phrase='phase 3',
        source_excerpt=(
            'The Company announced positive Phase 3 results for its pivotal trial. '
            'The NDA submission is expected in Q4 2026. The FDA has granted Breakthrough '
            'Therapy designation. PDUFA date expected Q2 2027.'
        ),
        filing_type='8-K',
    )

    result = classify_acquisition_situation(case)
    bucket = result.get('probability_bucket', '')
    assert bucket not in ('P5_HIGH_PRIORITY_PROCESS_SIGNAL',), (
        f'Phase 3 catalyst should NOT be P5, got {bucket!r}. '
        f'Scores: {result.get("situation_scores", {})}'
    )
    # Should be P3 or lower
    assert bucket in ('P2_MONITOR_ONLY', 'P3_WATCHLIST_SETUP', 'P0_NO_ACTION_FALSE_POSITIVE', 'P1_DISCARD_ALREADY_ANNOUNCED'), (
        f'Expected P2 or P3, got {bucket!r}'
    )
    print(f'  Bucket: {bucket} (correct — catalyst-only is not a process signal)')


def test_rofr_asset_specific_stays_low():
    """ROFR / asset-specific license rights stays P2 or P3 unless company-level."""
    from ai_research.acquisition_situation_classifier import classify_acquisition_situation

    case = _make_case(
        trigger_phrase='right of first refusal',
        source_excerpt=(
            'Pursuant to the License Agreement, the licensor retains a right of first refusal '
            'with respect to the licensed compound in the event the Company seeks to sublicense '
            'or sell this specific product. This right applies only to the collaboration compound '
            'and not to the Company as a whole.'
        ),
        filing_type='10-K',
    )

    result = classify_acquisition_situation(case)
    bucket = result.get('probability_bucket', '')
    assert bucket not in ('P4_RESEARCH_PRIORITY', 'P5_HIGH_PRIORITY_PROCESS_SIGNAL'), (
        f'Asset-specific ROFR should NOT be P4 or P5, got {bucket!r}. '
        f'Scores: {result.get("situation_scores", {})}'
    )
    print(f'  Bucket: {bucket} (correct — asset-specific ROFR stays low)')


def test_external_research_disabled_safe():
    """External research disabled returns safe status dict."""
    from ai_research.external_source_provider import get_external_research_status, search_company_deal_status

    # Ensure env var is not set for this test
    original = os.environ.get('EXTERNAL_RESEARCH_ENABLED', '')
    os.environ['EXTERNAL_RESEARCH_ENABLED'] = 'false'

    try:
        status = get_external_research_status()
        assert isinstance(status, dict), 'get_external_research_status should return dict'
        assert status.get('enabled') is False, 'Expected enabled=False'
        assert status.get('status') == 'disabled', f'Expected status=disabled, got {status.get("status")}'

        result = search_company_deal_status('TEST', 'Test Pharma')
        assert isinstance(result, dict), 'search_company_deal_status should return dict'
        assert result.get('enabled') is False, 'Expected disabled result'
        assert result.get('results') == [], 'Expected empty results when disabled'
        print(f'  External research status: {status}')
    finally:
        if original:
            os.environ['EXTERNAL_RESEARCH_ENABLED'] = original
        elif 'EXTERNAL_RESEARCH_ENABLED' in os.environ:
            del os.environ['EXTERNAL_RESEARCH_ENABLED']


def test_probability_starts_skeptical():
    """No-evidence case starts near base rate, does not escalate."""
    from ai_research.acquisition_probability_engine import compute_acquisition_probability, BASE_RATE_SKEPTICISM

    case = _make_case(
        trigger_phrase='',
        source_excerpt='',
        evidence_quality={
            'evidence_grade': 'F',
            'evidence_completeness_score': 0,
            'evidence_gaps': ['no source excerpt'],
            'top_evidence_quotes': [],
            'has_full_filing_text': False,
        },
    )

    result = compute_acquisition_probability(case)
    score = result.get('acquisition_research_probability_score', 0)

    # Score should be low for no-evidence case — not higher than 25
    assert score <= 25, (
        f'No-evidence case score should be <= 25, got {score}. '
        f'Base rate is {BASE_RATE_SKEPTICISM}.'
    )
    print(f'  No-evidence score: {score}/100 (base rate: {BASE_RATE_SKEPTICISM}%)')


def test_no_evidence_does_not_escalate():
    """Case with no signal evidence does not get P4 or P5."""
    from ai_research.acquisition_probability_engine import compute_acquisition_probability

    case = _make_case(
        trigger_phrase='change of control',
        source_excerpt=(
            'In connection with this offering, the Company has agreed not to issue any shares '
            'for 90 days. Change of control provisions apply to executive compensation plans.'
        ),
        filing_type='S-1',
        evidence_quality={
            'evidence_grade': 'D',
            'evidence_completeness_score': 10,
            'evidence_gaps': ['filing is S-1 prospectus', 'boilerplate language'],
            'top_evidence_quotes': [],
            'has_full_filing_text': False,
        },
    )

    result = compute_acquisition_probability(case)
    bucket = result.get('probability_bucket', '')
    score  = result.get('acquisition_research_probability_score', 0)

    assert bucket not in ('P4_RESEARCH_PRIORITY', 'P5_HIGH_PRIORITY_PROCESS_SIGNAL'), (
        f'Boilerplate case should NOT be P4 or P5, got {bucket!r} (score={score})'
    )
    print(f'  Bucket: {bucket}, score: {score}/100 (correct — boilerplate stays low)')


def test_library_validation_passes():
    """Library validates successfully with no fatal errors."""
    from ai_research.acquisition_case_library import (
        load_completed_acquisition_cases,
        validate_completed_acquisition_cases,
    )
    cases = load_completed_acquisition_cases()
    validation = validate_completed_acquisition_cases(cases)
    # Fatal errors: any non-WARNING error
    hard_errors = [e for e in validation.get('errors', []) if 'WARNING' not in e]
    assert not hard_errors, f'Library validation has hard errors: {hard_errors[:3]}'
    print(f'  Library validation: {validation["valid"]}/{validation["total"]} valid')


def test_retrieval_returns_results():
    """Retrieval for a live case returns a list (may be empty if no match)."""
    from ai_research.acquisition_case_library import (
        load_completed_acquisition_cases,
        retrieve_completed_deal_analogues,
    )
    cases = load_completed_acquisition_cases()
    live  = _make_case(
        trigger_phrase='unsolicited proposal',
        source_excerpt='The Board received an unsolicited proposal to acquire the Company.',
    )
    analogues = retrieve_completed_deal_analogues(live, cases, max_cases=5)
    assert isinstance(analogues, list), 'retrieve_completed_deal_analogues should return list'
    print(f'  Retrieved {len(analogues)} analogues')
    if analogues:
        print(f'  Top analogue: {analogues[0].get("ticker")} (score={analogues[0].get("_relevance_score", 0):.2f})')


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        test_cases_load,
        test_canonical_cases_exist,
        test_already_announced_gets_low_bucket,
        test_strategic_alternatives_gets_higher_score,
        test_catalyst_only_is_watch_not_process,
        test_rofr_asset_specific_stays_low,
        test_external_research_disabled_safe,
        test_probability_starts_skeptical,
        test_no_evidence_does_not_escalate,
        test_library_validation_passes,
        test_retrieval_returns_results,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f'PASS: {test.__name__}')
            passed += 1
        except Exception as exc:
            print(f'FAIL: {test.__name__}: {exc}')
            failed += 1

    print()
    print(f'{passed} passed, {failed} failed')
    sys.exit(0 if failed == 0 else 1)
