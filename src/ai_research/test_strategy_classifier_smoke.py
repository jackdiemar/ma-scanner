"""
test_strategy_classifier_smoke.py — Smoke tests for strategy_classifier.py

Run directly (no pytest dependency):
  python3 src/ai_research/test_strategy_classifier_smoke.py

Exit code 0 = all tests pass.
Exit code 1 = one or more tests failed.
"""
from __future__ import annotations

import sys
import os

# Allow direct execution from repo root
_HERE   = os.path.dirname(os.path.abspath(__file__))
_SRCDIR = os.path.dirname(_HERE)
if _SRCDIR not in sys.path:
    sys.path.insert(0, _SRCDIR)

from ai_research.strategy_classifier import run_strategy_classification


# ── Test runner ───────────────────────────────────────────────────────────────

_PASS = 0
_FAIL = 0
_RESULTS: list[str] = []


def _check(name: str, condition: bool, detail: str = '') -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        _RESULTS.append(f'  PASS  {name}')
    else:
        _FAIL += 1
        _RESULTS.append(f'  FAIL  {name}' + (f' — {detail}' if detail else ''))


def _case(excerpt: str, trigger: str = '', flags: list | None = None) -> dict:
    return {
        'ticker': 'TEST',
        'source_excerpt': excerpt,
        'trigger_phrase': trigger,
        'scanner_flags': flags or [],
        'filing_date': '2025-05-01',
        'evidence_quality': {
            'evidence_grade': 'C',
            'evidence_completeness_score': 55,
            'evidence_gaps': [],
        },
    }


# ── Test 1: merger agreement text → ALREADY_ANNOUNCED_MERGER ─────────────────

def test_merger_agreement_false_positive():
    case = _case(
        excerpt=(
            'On May 5, 2025, the Company entered into a definitive agreement and plan '
            'of merger with AcquireCo Inc. pursuant to which AcquireCo will acquire '
            'all outstanding shares of the Company for $42.00 per share in cash.'
        ),
        trigger='agreement and plan of merger',
    )
    sf = run_strategy_classification(case)

    _check(
        'Merger agreement → FP archetype ALREADY_ANNOUNCED_MERGER',
        'ALREADY_ANNOUNCED_MERGER' in sf['matched_false_positive_archetypes'],
        f'got: {sf["matched_false_positive_archetypes"]}',
    )
    _check(
        'Merger agreement → announcement_status_score >= 70',
        sf['announcement_status_score'] >= 70,
        f'got: {sf["announcement_status_score"]}',
    )
    _check(
        'Merger agreement → default action DISCARD',
        sf['default_research_action'] == 'DISCARD',
        f'got: {sf["default_research_action"]}',
    )
    _check(
        'Merger agreement → company_level_process_score <= 30',
        sf['company_level_process_score'] <= 30,
        f'got: {sf["company_level_process_score"]}',
    )
    _check(
        'Merger agreement → primary_bucket contains ALREADY_ANNOUNCED',
        'ALREADY_ANNOUNCED' in sf['primary_strategy_bucket'],
        f'got: {sf["primary_strategy_bucket"]}',
    )


# ── Test 2: strategic alternatives + retained advisor → company-level high ────

def test_strategic_alternatives_high_score():
    case = _case(
        excerpt=(
            'The board has retained Goldman Sachs as its financial advisor to assist '
            'in its review of strategic alternatives, which may include a sale of the '
            'company. The board has formed a special committee to oversee the process.'
        ),
        trigger='strategic alternatives',
    )
    sf = run_strategy_classification(case)

    _check(
        'Strategic alternatives → company_level_process_score >= 40',
        sf['company_level_process_score'] >= 40,
        f'got: {sf["company_level_process_score"]}',
    )
    _check(
        'Strategic alternatives → process_specificity_score >= 30',
        sf['process_specificity_score'] >= 30,
        f'got: {sf["process_specificity_score"]}',
    )
    _check(
        'Strategic alternatives → false_positive_score <= 40',
        sf['false_positive_score'] <= 40,
        f'got: {sf["false_positive_score"]}',
    )
    _check(
        'Strategic alternatives → announcement_status_score <= 30',
        sf['announcement_status_score'] <= 30,
        f'got: {sf["announcement_status_score"]}',
    )
    _check(
        'Strategic alternatives → no ALREADY_ANNOUNCED_MERGER in FP archetypes',
        'ALREADY_ANNOUNCED_MERGER' not in sf['matched_false_positive_archetypes'],
        f'got: {sf["matched_false_positive_archetypes"]}',
    )


# ── Test 3: ROFR/license text → ASSET_SPECIFIC_RIGHTS_ONLY ──────────────────

def test_rofr_license_asset_specific():
    case = _case(
        excerpt=(
            'Under the terms of the collaboration agreement, BioPartner Inc. has a '
            'right of first negotiation to acquire the exclusive rights to compound X '
            'in the United States upon achievement of Phase 2 proof of concept.'
        ),
        trigger='right of first negotiation',
    )
    sf = run_strategy_classification(case)

    _check(
        'ROFR/license → FP archetype ASSET_SPECIFIC_RIGHTS_ONLY',
        'ASSET_SPECIFIC_RIGHTS_ONLY' in sf['matched_false_positive_archetypes'],
        f'got: {sf["matched_false_positive_archetypes"]}',
    )
    _check(
        'ROFR/license → company_level_process_score <= 30',
        sf['company_level_process_score'] <= 30,
        f'got: {sf["company_level_process_score"]}',
    )
    _check(
        'ROFR/license → false_positive_score >= 30',
        sf['false_positive_score'] >= 30,
        f'got: {sf["false_positive_score"]}',
    )


# ── Test 4: superior proposal text → SUPERIOR_PROPOSAL true-signal archetype ─

def test_superior_proposal_true_signal():
    case = _case(
        excerpt=(
            'On August 25, 2017, the Company received an unsolicited superior proposal '
            'from a third party that the board determined constitutes a superior proposal '
            'under the terms of the existing merger agreement, triggering the fiduciary out.'
        ),
        trigger='superior proposal',
    )
    sf = run_strategy_classification(case)

    _check(
        'Superior proposal → matched TRUE SIGNAL SUPERIOR_PROPOSAL_OR_COMPETING_BID',
        'SUPERIOR_PROPOSAL_OR_COMPETING_BID' in sf['matched_true_signal_archetypes'],
        f'got: {sf["matched_true_signal_archetypes"]}',
    )
    _check(
        'Superior proposal → process_specificity_score >= 40',
        sf['process_specificity_score'] >= 40,
        f'got: {sf["process_specificity_score"]}',
    )
    _check(
        'Superior proposal → historical analogues reference DMTX',
        any('DMTX' in a for a in sf['historical_analogues']),
        f'got: {sf["historical_analogues"]}',
    )


# ── Test 5: unsolicited proposal → PUBLIC_UNSOLICITED_PROPOSAL ───────────────

def test_unsolicited_proposal_true_signal():
    case = _case(
        excerpt=(
            'On April 28, 2016, the Company disclosed a public unsolicited acquisition '
            'proposal received from Sanofi SA to acquire all outstanding shares '
            'of the Company for $52.50 per share. The board is reviewing the proposal '
            'with its financial advisors and has not yet determined its response.'
        ),
        trigger='unsolicited proposal',
    )
    sf = run_strategy_classification(case)

    _check(
        'Unsolicited proposal → matched TRUE SIGNAL PUBLIC_UNSOLICITED_PROPOSAL',
        'PUBLIC_UNSOLICITED_PROPOSAL' in sf['matched_true_signal_archetypes'],
        f'got: {sf["matched_true_signal_archetypes"]}',
    )
    _check(
        'Unsolicited proposal → company_level_process_score >= 40',
        sf['company_level_process_score'] >= 40,
        f'got: {sf["company_level_process_score"]}',
    )
    _check(
        'Unsolicited proposal → historical analogues reference MDVN',
        any('MDVN' in a for a in sf['historical_analogues']),
        f'got: {sf["historical_analogues"]}',
    )


# ── Test 6: no evidence → conservative output ─────────────────────────────────

def test_no_evidence_conservative():
    case = _case(
        excerpt='',
        trigger='',
    )
    case['evidence_quality'] = {
        'evidence_grade': 'F',
        'evidence_completeness_score': 0,
        'evidence_gaps': ['no excerpt', 'no filing text'],
    }
    sf = run_strategy_classification(case)

    _check(
        'No evidence → evidence_strength_score <= 10',
        sf['evidence_strength_score'] <= 10,
        f'got: {sf["evidence_strength_score"]}',
    )
    _check(
        'No evidence → investability_setup_score < 30',
        sf['investability_setup_score'] < 30,
        f'got: {sf["investability_setup_score"]}',
    )
    _check(
        'No evidence → no error key in output',
        'error' not in sf,
        f'got error: {sf.get("error", "")}',
    )


# ── Test 7: S-8 boilerplate → false positive ──────────────────────────────────

def test_s8_boilerplate():
    case = _case(
        excerpt=(
            'We have filed a Form S-8 registration statement to register shares '
            'available under our 2022 Equity Incentive Plan. Participants will '
            'receive accelerated vesting upon a change of control event as defined '
            'in the equity award agreement.'
        ),
        trigger='change of control',
        flags=['FILING_TYPE:S-8', 'TRIGGER:change of control vesting'],
    )
    sf = run_strategy_classification(case)

    _check(
        'S-8 boilerplate → FP archetype S8_EQUITY_PLAN_BOILERPLATE',
        'S8_EQUITY_PLAN_BOILERPLATE' in sf['matched_false_positive_archetypes'],
        f'got: {sf["matched_false_positive_archetypes"]}',
    )
    _check(
        'S-8 boilerplate → default_research_action DISCARD',
        sf['default_research_action'] == 'DISCARD',
        f'got: {sf["default_research_action"]}',
    )


# ── Test 8: negation → NEGATED_ACQUISITION_LANGUAGE ──────────────────────────

def test_negated_acquisition_language():
    case = _case(
        excerpt=(
            'The Company confirms that it has not received any acquisition proposal '
            'and is not exploring strategic alternatives. The Company remains committed '
            'to its standalone growth strategy and is not for sale.'
        ),
        trigger='acquisition proposal',
    )
    sf = run_strategy_classification(case)

    _check(
        'Negation → FP archetype NEGATED_ACQUISITION_LANGUAGE',
        'NEGATED_ACQUISITION_LANGUAGE' in sf['matched_false_positive_archetypes'],
        f'got: {sf["matched_false_positive_archetypes"]}',
    )
    _check(
        'Negation → company_level_process_score low (<= 20)',
        sf['company_level_process_score'] <= 20,
        f'got: {sf["company_level_process_score"]}',
    )


# ── Test 9: classifier never raises ───────────────────────────────────────────

def test_classifier_never_raises_on_garbage():
    bad_cases = [
        {},
        {'ticker': None},
        {'source_excerpt': None, 'trigger_phrase': None, 'scanner_flags': None},
        {'source_excerpt': '   ', 'filing_date': 'not-a-date'},
    ]
    for i, c in enumerate(bad_cases):
        try:
            sf = run_strategy_classification(c)
            _check(
                f'Garbage case {i+1} → no exception, has primary_strategy_bucket',
                'primary_strategy_bucket' in sf,
                f'got keys: {list(sf.keys())}',
            )
        except Exception as exc:
            _check(f'Garbage case {i+1} → no exception', False, str(exc))


# ── Runner ─────────────────────────────────────────────────────────────────────

def main() -> int:
    print('Strategy Classifier Smoke Tests')
    print('=' * 48)

    test_merger_agreement_false_positive()
    test_strategic_alternatives_high_score()
    test_rofr_license_asset_specific()
    test_superior_proposal_true_signal()
    test_unsolicited_proposal_true_signal()
    test_no_evidence_conservative()
    test_s8_boilerplate()
    test_negated_acquisition_language()
    test_classifier_never_raises_on_garbage()

    print()
    for r in _RESULTS:
        print(r)

    print()
    print(f'Results: {_PASS} PASS / {_FAIL} FAIL out of {_PASS + _FAIL} checks')

    if _FAIL > 0:
        print('SMOKE TEST FAILED — see above')
        return 1
    print('SMOKE TEST PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
