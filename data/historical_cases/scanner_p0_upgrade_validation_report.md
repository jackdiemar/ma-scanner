# Scanner P0 Upgrade Validation Report

Generated: 2026-05-15

## Summary

All five P0 scanner-core upgrades implemented in `src/PRODUCTION_SCANNER_V12.py`.
Validation suite: 33/33 tests passed, 0 failed.

Validation script: `src/historical_case_tools/validate_scanner_p0_upgrades.py`

---

## Changes Implemented

### P0-A: Negation detection in 8-K phrase matching

**File:** `src/PRODUCTION_SCANNER_V12.py`

Added two constants:

```python
_NEGATION_PREFIXES = (
    'no plan or proposal', 'no plans or proposals', 'no current plan',
    'no current plans', 'does not have any plan', 'have no plan',
    'have not formulated', 'has not formulated', 'no present intention',
    'no intention to', 'without any plan', 'currently have no',
    'do not have any', 'have not adopted',
)
_NEGATION_SENSITIVE_KEYS = frozenset({
    'acquisition_proposal', 'unsolicited_proposal', 'superior_proposal',
    'rofn', 'rofr', 'rofo',
})
```

In the phrase match loop: if the matched key is in `_NEGATION_SENSITIVE_KEYS`, the scanner checks the 55-character window immediately before the match for any negation prefix. If found, the phrase is added to `negated_phrases` and scoring is skipped.

SA phrases (`strategic_alternatives`) and merger phrases (`merger_agreement`) are exempt — those phrasing patterns do not appear in negated boilerplate the same way.

### P0-B: Source traceability for 8-K text signals

**File:** `src/PRODUCTION_SCANNER_V12.py`

The result dict for `fetch_8k_text_signals()` now initializes five new fields:

```python
'source_url':             '',
'source_accession':       '',
'source_filing_date':     '',
'source_form_type':       '',
'source_matched_phrase':  '',
```

On the first affirmative phrase match (not negated), these fields are populated from the filing metadata. Downstream, these are exposed as `signal_source_url`, `signal_source_accession`, and `signal_source_date` on the ticker result dict.

### P0-C: ROFR/ROFN scope classification and score gating

**File:** `src/PRODUCTION_SCANNER_V12.py`

New function `_classify_rights_scope(text, phrase, idx)`:

- Checks 150 chars before + 250 chars after the match location
- Priority order: `securities_or_lockup_likely` → `asset_specific_likely` → `company_level_possible` → `unknown_scope`
- Securities/lockup terms: shares, stock, warrant, option, convertible, lock-up, lockup, promissory, note
- Asset-specific terms: license, intellectual property, IP, program, compound, asset, territory, indication, product candidate, collaboration
- Company-level terms: company, corporation, issuer, entity, business, acquiror, target

Score adjustment in phrase match loop:
- `asset_specific_likely` or `securities_or_lockup_likely` → score_pts = 0
- `unknown_scope` → score_pts = pts // 2
- `company_level_possible` → full pts

`has_real_process_evidence()` now uses scope hints to gate ROFR/ROFN:
- `asset_specific_likely` and `securities_or_lockup_likely` scopes do NOT clear the process gate
- `company_level_possible` and `unknown_scope` do clear the gate (conservative)

### P0-D: Raise 8-K scan depth

**File:** `src/PRODUCTION_SCANNER_V12.py`

`fetch_8k_text_signals()` default changed from `n_filings=4` to `n_filings=8`.
Call site updated to match.

Rationale: Prior-signal study showed several cases where the signal appeared in the 5th–7th most recent 8-K. A depth of 4 would have missed them.

### P0-E: Tighten 13D fallback

**File:** `src/PRODUCTION_SCANNER_V12.py`

Updated `has_real_process_evidence()`:

**Before:** Any 13D filing (activist_signal present) cleared the process gate regardless of filer identity or whether Item 4 was parsed.

**After:**
- If Item 4 was parsed: gate clears only if `is_sale_pressure=True` or `classification='ACTIVIST_ESCALATION'` (unchanged)
- If Item 4 is unavailable (filing fetch failed or doc not found):
  - Known activist (`is_known=True`): filing existence itself is treated as signal → gate clears
  - Unknown filer (`is_known=False`): gate does NOT clear

Rationale: Unknown filers routinely file SC 13D for passive accumulation, governance, or disclosure reasons. Clearing the process gate on filing existence alone generated false positives in historical review (cases like DICE where a passive filer's boilerplate language appeared to clear process evidence).

---

## Result dict initialization fix

Both `fetch_8k_text_signals()` in the scanner and `simulate_phrase_match()` in the validation script previously initialized only the ROFR/ROFN/SA/merger phrase keys. The dynamic-keyed phrases (`acquisition_proposal`, `unsolicited_proposal`, `superior_proposal`) were only set when they fired affirmatively. This caused KeyError when negation suppressed a match and downstream code accessed the key directly.

Fixed: all three keys now initialized to `False` at result dict construction. Compile check clean. No downstream behavior change when phrases fire normally.

---

## Examples Tested

| Test | Pattern | Expected | Result |
|------|---------|----------|--------|
| 1 | DICE-style "no plan or proposal to acquire the issuer" | `acquisition_proposal=False`, `pts=0`, `source_url=''` | PASS |
| 2 | MDVN/DMTX "received an unsolicited proposal to acquire all outstanding shares" | `unsolicited_proposal=True`, `acquisition_proposal=True`, `pts>0` | PASS |
| 3 | EPZM-style ROFN in collaboration context "right of first negotiation for the licensed program" | `rofn=True`, `rofn_scope_hint=asset_specific_likely`, `pts=0` | PASS |
| 4 | Lock-up ROFR "right of first refusal on any transfer of shares or other securities" | `rofr=True`, `rofr_scope_hint=securities_or_lockup_likely`, `pts=0` | PASS |
| 5 | Company-level ROFR "right of first refusal to acquire the company or its business" | `rofr=True`, `rofr_scope_hint=company_level_possible`, `pts>0` | PASS |
| 6 | Scope gate — asset-specific ROFN vs company-level ROFN in `has_real_process_evidence()` | asset_specific does NOT clear; company_level DOES clear | PASS |
| 7 | Unknown filer, no Item 4 doc | gate NOT cleared | PASS |
| 8 | Known activist, no Item 4 doc | gate DOES clear | PASS |
| 9 | Affirmative 8-K match — source metadata captured | `source_url`, `source_accession`, `source_filing_date`, `source_form_type`, `source_matched_phrase` all set | PASS |
| 10 | ROFN score comparison: asset_specific (0 pts) vs company_level (18 pts) | asset_specific=0, company_level=18 | PASS |

---

## Before/After Expected Behavior

### DICE-style passive filer boilerplate

**Before P0-A/E:** Scanner scores `acquisition_proposal=True` (+25 pts) from "proposal to acquire" in negated 13D boilerplate. Unknown filer clears process gate. Ticker enters LIVE state.

**After P0-A/E:** Negation suppresses `acquisition_proposal`. Unknown filer does not clear process gate. Ticker stays in SCREENING or AGING state.

### EPZM-style collaboration 8-K

**Before P0-C:** `rofn=True`, full 18 pts added, process gate cleared → PATHWAY state.

**After P0-C:** `rofn=True`, `rofn_scope_hint=asset_specific_likely`, 0 pts, gate not cleared → SCREENING state (score only).

### MDVN/DMTX real acquisition proposal

**Before:** Fires correctly.

**After P0-A:** Still fires correctly. Negation check is skipped for "unsolicited proposal" in positive context (no negation prefix in the 55-char window). Score and gate behavior unchanged.

---

## Known Remaining Limitations

1. **Negation window is 55 chars.** Long negation clauses may extend past the window. Rare in practice given standard 13D boilerplate structure.

2. **SA phrases not negation-gated.** "Strategic alternatives" can appear in risk factor disclaimers ("we may explore strategic alternatives in the future if..."). These are lower-priority false positives because SA quality scoring (`sa_is_affirm` vs boilerplate) already handles them.

3. **Scope classifier uses keyword proximity, not parsing.** Unusual phrasing or multi-clause sentences can produce wrong scope. Precision improves as the asset-term and company-term lists are tuned on more cases.

4. **unknown_scope ROFN/ROFR still clears process gate.** Conservative choice — avoids missing real company-level rights. May produce occasional false positives for ambiguous phrasing. Flag for P1 review if observed in live scan.

5. **Item 4 parsing still stub-only for most filings.** `enrich_activist_item4()` is the highest-ROI remaining P1 gap. Until it's live, known-filer fallback (P0-E) is a proxy.

6. **n_filings=8 doubles EDGAR fetch volume per ticker.** No rate-limit issues observed in testing, but watch for latency impact on the full 500-ticker scan.

---

## Recommended Next P1 Upgrades

These are the remaining gaps from `docs/scanner_core_upgrade_plan.md` section 4 (P1 list):

1. **Item 4 parsing — live integration.** `enrich_activist_item4()` in `src/item4_parser.py` exists as a stub. Wiring it into the live scan path for known SC 13D filers is the single highest-ROI remaining upgrade. Distinguishes sale-pressure activists from governance/passive filers with real evidence rather than name lookup.

2. **SA quality scorer tuning.** Expand `_BOILERPLATE_MARKERS` in `score_strategic_alternatives_quality()` based on false-positive patterns in Batch 51-70 (especially PWERM language, which appears in 10-Qs but not 8-Ks — confirm whether live scanner sees it).

3. **Negation window expansion for SA phrases.** Once SA boilerplate patterns are catalogued, add negation gating for `strategic_alternatives` with a wider window (120 chars). Low priority until a false-positive is observed in live scan.

4. **Score threshold recalibration.** With P0-C reducing ROFN/ROFR scores for non-company-level scope, some tickers that previously entered PATHWAY may now fall below PROCESS_EVIDENCE_SCORE_CAP. Verify score distribution on next full scan before adjusting the cap.

5. **Batch 71-90 historical study.** Engineering improvements are now in place. Next historical batch can proceed with improved collector (binary artifact exclusion, negation lookback, lock-up exhibit exclusion).
