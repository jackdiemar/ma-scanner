#!/usr/bin/env python3
"""
validate_scanner_p0_upgrades.py

Validates the five P0 scanner-core upgrades implemented in PRODUCTION_SCANNER_V12.py.
Uses only the pure-Python logic from the scanner — does not call FMP, EDGAR, or any
external API. Does not run the full scanner. Does not touch dashboard or historical data.

Tests:
  1. P0-A: Negation detection — DICE-style "no plan or proposal to acquire" is suppressed.
  2. P0-A: Positive case — real acquisition proposal still fires.
  3. P0-C: Asset-specific ROFN → asset_specific_likely scope.
  4. P0-C: Lock-up ROFR → securities_or_lockup_likely scope.
  5. P0-C: Company-level ROFR → company_level_possible scope.
  6. P0-C: Scope gate — asset-specific ROFN does not clear has_real_process_evidence().
  7. P0-E: 13D fallback — unknown filer + unavailable doc does NOT clear process gate.
  8. P0-E: Known activist + unavailable doc DOES clear process gate.
  9. P0-A/P0-B: source_url captured after first affirmative match; empty for negated-only.
 10. P0-C: ROFR score reduced for asset_specific_likely vs company_level_possible.
"""

import sys
import os

# Add src to path so we can import directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PRODUCTION_SCANNER_V12 import (
    _NEGATION_PREFIXES,
    _NEGATION_SENSITIVE_KEYS,
    _classify_rights_scope,
    has_real_process_evidence,
    _8K_SIGNAL_PHRASES,
    fetch_8k_text_signals,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'

results = []


def check(name, condition, detail=''):
    tag = PASS if condition else FAIL
    print(f'  [{tag}] {name}')
    if not condition:
        print(f'         detail: {detail}')
    results.append((name, condition))


# ─────────────────────────────────────────────────────────────────────────────
# Helper: run phrase-match loop logic in isolation (without FMP or network)
# ─────────────────────────────────────────────────────────────────────────────

def simulate_phrase_match(text, filing_meta=None):
    """
    Run the P0-A/P0-B/P0-C phrase matching logic against synthetic text.
    Mirrors the logic in fetch_8k_text_signals() without any FMP or network calls.
    Returns a result dict equivalent to what the live scanner would produce.
    """
    url = (filing_meta or {}).get('finalLink', 'https://example.com/8k.htm')
    filing = filing_meta or {
        'finalLink':       url,
        'accessionNumber': '0001234567-23-000001',
        'filingDate':      '2023-06-01',
        'formType':        '8-K',
    }

    result = {
        'strategic_alternatives': False,
        'unsolicited_proposal':   False,
        'superior_proposal':      False,
        'acquisition_proposal':   False,
        'banker_retained':        False,
        'rofn':                   False,
        'rofr':                   False,
        'rofo':                   False,
        'merger_agreement':       False,
        'exclusive_license':      False,
        'collaboration':          False,
        'named_pharma':           None,
        'top_phrase':             '',
        'pts':                    0,
        'negated_phrases':        [],
        'source_url':             '',
        'source_accession':       '',
        'source_filing_date':     '',
        'source_form_type':       '',
        'source_matched_phrase':  '',
        'rofn_scope_hint':        None,
        'rofr_scope_hint':        None,
        'rofo_scope_hint':        None,
    }

    for phrase, key, pts in _8K_SIGNAL_PHRASES:
        if phrase in text and not result.get(key):
            idx = text.find(phrase)

            # P0-A: negation detection
            if key in _NEGATION_SENSITIVE_KEYS:
                ctx_before = text[max(0, idx - 55): idx]
                if any(neg in ctx_before for neg in _NEGATION_PREFIXES):
                    result['negated_phrases'].append(phrase)
                    continue

            # P0-C: ROFR/ROFN scope classification and score adjustment
            score_pts = pts
            if key in ('rofn', 'rofr', 'rofo'):
                scope = _classify_rights_scope(text, phrase, idx)
                result[key + '_scope_hint'] = scope
                if scope in ('asset_specific_likely', 'securities_or_lockup_likely'):
                    score_pts = 0
                elif scope == 'unknown_scope':
                    score_pts = pts // 2

            result[key]    = True
            result['pts'] += score_pts
            if not result['top_phrase']:
                result['top_phrase'] = phrase

            # P0-B: capture source metadata on first affirmative match
            if not result['source_url']:
                result['source_url']           = url
                result['source_accession']     = filing.get('accessionNumber', '')
                result['source_filing_date']   = filing.get('filingDate', '')
                result['source_form_type']     = filing.get('formType', '8-K')
                result['source_matched_phrase'] = phrase

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: P0-A — DICE-style negation suppression
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 1] P0-A: Negation detection — DICE pattern')
dice_text = (
    'the reporting persons currently have no plan or proposal to acquire the issuer '
    'or any of its securities, and have not formulated any plans or proposals which '
    'relate to or would result in any extraordinary corporate transaction.'
)
r1 = simulate_phrase_match(dice_text)
check('acquisition_proposal NOT fired on negated "proposal to acquire"',
      not r1['acquisition_proposal'],
      f'acquisition_proposal={r1["acquisition_proposal"]}')
check('"proposal to acquire" appears in negated_phrases',
      'proposal to acquire' in r1['negated_phrases'],
      f'negated_phrases={r1["negated_phrases"]}')
check('pts remain 0 (negated phrase adds no score)',
      r1['pts'] == 0,
      f'pts={r1["pts"]}')
check('source_url is empty (no affirmative signal fired)',
      r1['source_url'] == '',
      f'source_url={r1["source_url"]}')

# ─────────────────────────────────────────────────────────────────────────────
# Test 2: P0-A — Positive case (real acquisition proposal still fires)
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 2] P0-A: Positive case — MDVN/DMTX-style real acquisition proposal')
mdvn_text = (
    'the company received an unsolicited proposal to acquire all outstanding shares '
    'of the company at a price of $52.50 per share. the board of directors, in '
    'consultation with its financial advisor, rejected the proposal.'
)
r2 = simulate_phrase_match(mdvn_text)
check('unsolicited_proposal fires on real "unsolicited proposal"',
      r2.get('unsolicited_proposal'),
      f'unsolicited_proposal={r2.get("unsolicited_proposal")}')
check('acquisition_proposal fires on "proposal to acquire" in positive context',
      r2['acquisition_proposal'],
      f'acquisition_proposal={r2["acquisition_proposal"]}')
check('pts > 0 for real acquisition proposal',
      r2['pts'] > 0,
      f'pts={r2["pts"]}')
check('source_url populated after affirmative match',
      r2['source_url'] != '',
      f'source_url={r2["source_url"]}')
check('"unsolicited proposal" not in negated_phrases',
      'unsolicited proposal' not in r2['negated_phrases'],
      f'negated_phrases={r2["negated_phrases"]}')

# ─────────────────────────────────────────────────────────────────────────────
# Test 3: P0-C — Asset-specific ROFN (EPZM/TPTX pattern)
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 3] P0-C: Asset-specific ROFN scope classification')
epzm_text = (
    'pursuant to the collaboration agreement with eisai co., the company granted '
    'eisai a right of first negotiation for the licensed product in the japan '
    'territory, as well as a right of first negotiation for any other ezh2 product '
    'candidates in the geographic territory of asia.'
)
r3 = simulate_phrase_match(epzm_text)
check('rofn flag is True (phrase detected)',
      r3['rofn'],
      f'rofn={r3["rofn"]}')
check('rofn_scope_hint is asset_specific_likely',
      r3.get('rofn_scope_hint') == 'asset_specific_likely',
      f'rofn_scope_hint={r3.get("rofn_scope_hint")}')
check('pts = 0 for asset_specific ROFN (no process score)',
      r3['pts'] == 0,
      f'pts={r3["pts"]}')

# ─────────────────────────────────────────────────────────────────────────────
# Test 4: P0-C — Lock-up/securities ROFR (SRRA/ALPN pattern)
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 4] P0-C: Securities/lock-up ROFR scope classification')
srra_text = (
    'pursuant to the lock-up agreement, the company shall have a right of first '
    'refusal to repurchase any shares held by the participant upon termination of '
    'employment or service at the original purchase price per share.'
)
r4 = simulate_phrase_match(srra_text)
check('rofr flag is True (phrase detected)',
      r4['rofr'],
      f'rofr={r4["rofr"]}')
check('rofr_scope_hint is securities_or_lockup_likely',
      r4.get('rofr_scope_hint') == 'securities_or_lockup_likely',
      f'rofr_scope_hint={r4.get("rofr_scope_hint")}')
check('pts = 0 for securities/lockup ROFR (no process score)',
      r4['pts'] == 0,
      f'pts={r4["pts"]}')

# ─────────────────────────────────────────────────────────────────────────────
# Test 5: P0-C — Company-level ROFR (real acquisition pathway)
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 5] P0-C: Company-level ROFR scope classification')
company_rofr_text = (
    'the board of directors has determined to explore strategic alternatives '
    'including a potential sale of the company. in connection with the merger '
    'agreement, the company has granted the acquirer a right of first refusal '
    'on all outstanding shares if a superior proposal is received.'
)
r5 = simulate_phrase_match(company_rofr_text)
check('rofr flag is True',
      r5['rofr'],
      f'rofr={r5["rofr"]}')
check('rofr_scope_hint is company_level_possible',
      r5.get('rofr_scope_hint') == 'company_level_possible',
      f'rofr_scope_hint={r5.get("rofr_scope_hint")}')
check('pts > 0 for company_level ROFR',
      r5['pts'] > 0,
      f'pts={r5["pts"]}')

# ─────────────────────────────────────────────────────────────────────────────
# Test 6: P0-C — Scope gate in has_real_process_evidence
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 6] P0-C: Asset-specific ROFN does NOT clear process evidence gate')
ts_asset_rofn = {'rofn': True, 'rofn_scope_hint': 'asset_specific_likely'}
ts_company_rofn = {'rofn': True, 'rofn_scope_hint': 'company_level_possible'}
ts_unknown_rofn = {'rofn': True, 'rofn_scope_hint': 'unknown_scope'}
ts_lockup_rofr = {'rofr': True, 'rofr_scope_hint': 'securities_or_lockup_likely'}

check('asset_specific ROFN does NOT clear gate',
      not has_real_process_evidence(text_signals=ts_asset_rofn),
      'expected False')
check('company_level ROFN DOES clear gate',
      has_real_process_evidence(text_signals=ts_company_rofn),
      'expected True')
check('unknown_scope ROFN DOES clear gate (conservative)',
      has_real_process_evidence(text_signals=ts_unknown_rofn),
      'expected True')
check('securities_or_lockup ROFR does NOT clear gate',
      not has_real_process_evidence(text_signals=ts_lockup_rofr),
      'expected False')

# ─────────────────────────────────────────────────────────────────────────────
# Test 7: P0-E — Unknown filer + unavailable Item 4 does NOT clear gate
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 7] P0-E: Unknown filer + unavailable Item 4 does NOT clear process gate')
unknown_13d = {
    'filer':        'Generic Passive Holder LLC',
    'filing_date':  '2024-01-15',
    'is_known':     False,
    'pts':          12,
    # No 'item4' key — document unavailable
}
check('unknown filer, no item4 → does NOT clear gate',
      not has_real_process_evidence(activist_signal=unknown_13d, text_signals={}),
      'expected False')

# ─────────────────────────────────────────────────────────────────────────────
# Test 8: P0-E — Known activist + unavailable Item 4 DOES clear gate
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 8] P0-E: Known activist + unavailable Item 4 DOES clear gate')
known_13d = {
    'filer':        'Sarissa Capital Management LP',
    'filing_date':  '2024-01-15',
    'is_known':     True,
    'pts':          20,
    # No 'item4' key — document unavailable
}
check('known activist, no item4 → DOES clear gate',
      has_real_process_evidence(activist_signal=known_13d, text_signals={}),
      'expected True')

# ─────────────────────────────────────────────────────────────────────────────
# Test 9: P0-B — source_url/accession captured on first affirmative match
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 9] P0-B: Source URL and accession captured for affirmative signals')
filing_meta = {
    'finalLink':       'https://www.sec.gov/Archives/edgar/data/123456/0001234567-23-000001.htm',
    'accessionNumber': '0001234567-23-000001',
    'filingDate':      '2023-06-15',
    'formType':        '8-K',
}
affirm_text = (
    'the board of directors has initiated a formal review of strategic alternatives '
    'to maximize shareholder value, including a potential sale of the company. '
    'the company has retained goldman sachs as its exclusive financial advisor '
    'in connection with this process.'
)
r9 = simulate_phrase_match(affirm_text, filing_meta=filing_meta)
check('source_url populated',
      r9['source_url'] == filing_meta['finalLink'],
      f'source_url={r9["source_url"]}')
check('source_accession populated',
      r9['source_accession'] == filing_meta['accessionNumber'],
      f'source_accession={r9["source_accession"]}')
check('source_filing_date populated',
      r9['source_filing_date'] == filing_meta['filingDate'],
      f'source_filing_date={r9["source_filing_date"]}')
check('source_form_type is 8-K',
      r9['source_form_type'] == '8-K',
      f'source_form_type={r9["source_form_type"]}')
check('source_matched_phrase is set',
      r9['source_matched_phrase'] != '',
      f'source_matched_phrase={r9["source_matched_phrase"]}')

# ─────────────────────────────────────────────────────────────────────────────
# Test 10: P0-C — Score reduction for asset_specific vs company_level ROFN
# ─────────────────────────────────────────────────────────────────────────────

print('\n[Test 10] P0-C: ROFN score = 0 for asset_specific, full for company_level')
asset_rofn_text = (
    'the company has granted its partner a right of first negotiation for the '
    'licensed product in the territory of japan pursuant to the collaboration '
    'agreement dated march 15, 2022.'
)
company_rofn_text2 = (
    'the board of directors is exploring strategic alternatives. the company has '
    'received an acquisition proposal and granted a right of first negotiation '
    'to the potential acquirer for all outstanding shares of the company.'
)

r10a = simulate_phrase_match(asset_rofn_text)
r10b = simulate_phrase_match(company_rofn_text2)
check('asset_specific ROFN scores 0 pts',
      r10a['pts'] == 0,
      f'pts={r10a["pts"]} (expected 0)')
check('company_level ROFN scores full pts (18)',
      r10b['pts'] >= 18,
      f'pts={r10b["pts"]} (expected ≥18)')
check('asset_specific rofn_scope_hint is asset_specific_likely',
      r10a.get('rofn_scope_hint') == 'asset_specific_likely',
      f'rofn_scope_hint={r10a.get("rofn_scope_hint")}')
check('company_level rofn_scope_hint is company_level_possible',
      r10b.get('rofn_scope_hint') == 'company_level_possible',
      f'rofn_scope_hint={r10b.get("rofn_scope_hint")}')

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

print('\n' + '=' * 60)
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
total  = len(results)
print(f'Results: {passed}/{total} passed, {failed} failed')

if failed:
    print('\nFailed checks:')
    for name, ok in results:
        if not ok:
            print(f'  - {name}')
    sys.exit(1)
else:
    print('All P0 upgrade validations passed.')
    sys.exit(0)
