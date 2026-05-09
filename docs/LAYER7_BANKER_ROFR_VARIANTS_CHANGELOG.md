# Layer 7 — Banker/Advisor Detection + ROFR/ROFN Variants
**Date:** 2026-04-29  
**Version:** V12.4  

---

## Files Changed
- `PRODUCTION_SCANNER_V12.py`

## Functions Changed

| Function | Change |
|---|---|
| `fetch_8k_text_signals()` | Added `banker_retained` field to result dict; added `_ADVISOR_PHRASES` detection loop after named pharma detection |
| `has_real_process_evidence()` | Added `ts.get('banker_retained')` to gate-clearing conditions |
| `calculate_ma_score()` Layer 7 block | Added `elif ts.get('banker_retained')` scoring branch (20-25 pts) between strategic_alternatives and rofn/rofr |
| Output dict (per-ticker) | Added `'banker_retained'` field to JSON output |
| `format_result()` display flags | Added `▲▲ FINANCIAL ADVISOR RETAINED` display line |

---

## Logic Added

### 1. `_ADVISOR_PHRASES` constant (new)
Phrases in 8-K filings that indicate a company has engaged an M&A advisor or is explicitly exploring a sale — appearing **before** a formal "strategic alternatives" announcement.

| Phrase | Points |
|---|---|
| `potential sale of the company` | 25 |
| `exploring a potential sale` | 25 |
| `as its exclusive financial advisor` | 22 |
| `as financial advisor to the company` | 22 |
| `as its financial advisor in connection` | 22 |
| `retained as its financial advisor` | 22 |
| `engaged as its financial advisor` | 22 |
| `retained a financial advisor` | 20 |
| `engaged a financial advisor` | 20 |
| `retained an investment bank` | 20 |
| `engaged an investment bank` | 20 |

**Detection:** Takes highest-scoring match per filing; only fires if `strategic_alternatives` not already set. Adds best_pts to `result['pts']`.

### 2. ROFR/ROFN legal variants (additive to `_8K_SIGNAL_PHRASES`)

| New phrase | Key | Points | Rationale |
|---|---|---|---|
| `first right to negotiate` | rofn | 18 | Alternate legal drafting of ROFN |
| `right of first purchase` | rofr | 15 | Alternate legal drafting of ROFR |

### 3. Process evidence gate — `banker_retained` now clears cap
`has_real_process_evidence()` now returns True if `banker_retained` is set.  
Effect: companies with advisor-engagement 8-Ks can score above 80.

---

## Scoring Impact

**Before V12.4:** Company files 8-K: "Company has retained [Bank] as its exclusive financial advisor in connection with the evaluation of strategic options" → Layer 7 = 0 pts, capped at 80.

**After V12.4:** Same 8-K → `banker_retained = True`, Layer 7 += 22 pts, process evidence gate cleared, can score above 80.

---

## Assumptions

- "Financial advisor" in biotech 8-Ks = M&A advisor. Capital market transactions use "placement agent" or "underwriter" — phrases do not overlap.
- "Potential sale of the company" in an 8-K is affirmative, not a risk-factor disclaimer (risk factors say "there is no assurance we will explore" etc.)
- ROFR/ROFN variants (`first right to negotiate`, `right of first purchase`) are specific enough in pharma licensing context to not generate significant false positives.

---

## Risks / Edge Cases

| Risk | Likelihood | Mitigation |
|---|---|---|
| "Financial advisor" appears in capital raise context | Low | Capital raises use "placement agent"/"underwriter" language |
| "Potential sale" in risk factor section | Low-Medium | Risk factors phrase it hypothetically ("may consider"); 8-K item 1.01 language is affirmative |
| `banker_retained` fires alongside collaboration signal, inflating ts.pts | Medium | layer7 = min(layer7, 35) cap absorbs; total capped at 35 |
| ROFR variant "right of first purchase" in non-M&A context | Low | Biotech 8-Ks use this in licensing agreements only |

---

## Validation
- Python syntax: `py_compile.compile()` — **PASSED**
- No changes to Layers 1-6 or CoC proxy logic
