# Scanner Core Upgrade Plan

Generated: 2026-05-15
Status: Audit and planning document. No scanner code changed.

Basis: 70-case historical prior-signal study (3/70 = 4.3% TRUE_PUBLIC_PRIOR_SIGNAL rate) + live 8-K catchability review + direct source audit of `src/PRODUCTION_SCANNER_V12.py` and `src/trade_logic.py`.

---

## 1. Current Scanner Architecture

### Data Sources

| Source | Role | Current usage |
|---|---|---|
| FMP (primary) | Quotes, profiles, historical price, EV, analyst estimates, SEC filing search, insider transactions, 13D filing feed | Extensive — all Layer 1-6 fundamentals + Layer 7 filing fetch |
| EDGAR via FMP | 8-K document bodies, SC 13D document bodies, proxy DEF 14A links | Layer 7 only; uses FMP's `finalLink` to fetch primary HTML documents |
| yfinance | Supplemental price and RSI data | Fallback where FMP quote data is stale |
| EDGAR EFTS | Full-text search across all filings | Historical batch collector only — NOT used in live scanner |

### Universe

Approximately 500 biotech/pharma tickers organized by therapeutic area (Autoimmune, Oncology, Metabolic, Rare Disease, Neuroscience, Renal, Gene/Cell Therapy, Cardiovascular, Commercial-Stage, Infectious Disease, Ophthalmology, Women's Health, Additional, Broad Biotech, Verified New). Target range: $150M–$1.5B market cap. Built as a static Python list, deduplicated via `set()`. Not dynamically filtered by current market cap at runtime.

### Scoring Architecture

**Two-pass design:**

Pass 1: Layer 0–6 scoring for all universe tickers in parallel (fundamentals, pipeline, financial health, catalysts, acquisition pattern match, institutional signals). Layer 0 excludes bankruptcy-risk names (price < $1.50, mcap < $150M, runway < 2Q).

Pass 2: Layer 7 SEC document fetch — only tickers scoring ≥60 (`LAYER7_THRESHOLD`) proceed to Layer 7. This limits expensive document fetches to high-scoring names.

**Layer 7 sub-components:**
- `fetch_8k_text_signals()`: fetches the 4 most recent 8-Ks, runs phrase matching
- `enrich_activist_item4()`: fetches SC 13D/A document, calls `parse_13d_item4()` from `src/item4_parser.py`
- `fetch_proxy_signal()`: fetches most recent DEF 14A, scans for CoC provisions

**Process evidence cap:** Tickers without confirmed process evidence are capped at `PROCESS_EVIDENCE_SCORE_CAP = 80`, preventing score-only names from appearing as HIGH or MEDIUM tier.

### Signal Detection

**8-K phrase list** (`_8K_SIGNAL_PHRASES`): Ordered by signal strength. Current entries:

| Phrase | Key | Score |
|---|---|---|
| strategic alternatives, exploring strategic | strategic_alternatives | 30 |
| unsolicited proposal | unsolicited_proposal | 30 |
| superior proposal | superior_proposal | 28 |
| proposal to acquire | acquisition_proposal | 25 |
| acquisition proposal | acquisition_proposal | 25 |
| right of first negotiation, first right to negotiate | rofn | 18 |
| right of first refusal, right of first purchase | rofr | 15 |
| right of first offer | rofo | 14 |
| merger agreement | merger_agreement | 12 |
| exclusive worldwide license, exclusive license agreement | exclusive_license | 8 |
| collaboration and license, co-development agreement | collaboration | 5 |

**SA quality check** (`score_strategic_alternatives_quality()`): Inspects ±400 chars around "strategic alternatives" phrase. Returns `(pts, is_affirm)`:
- Boilerplate context markers → (8, False), does not clear evidence cap
- Affirm context markers → (30, True), clears evidence cap
- Ambiguous → (15, False), partial score, cap not cleared

**Advisor/banker detection** (`_ADVISOR_PHRASES`): Scores 20–25 pts for phrases like "as its exclusive financial advisor," "potential sale of the company," "exploring a potential sale." Only fires if no SA signal already found.

**13D detection** (`preload_activist_signals()`): One-call preload at scan start, last 60 days, cross-referenced against universe. Known biotech activists score 20 pts; others score 12 pts. Item 4 intent is enriched per-ticker during Layer 7 via `enrich_activist_item4()`.

**13D gate logic** in `has_real_process_evidence()`:
- Item 4 parsed → SALE_PROCESS (moderate+) or ACTIVIST_ESCALATION clears gate
- Item 4 parsed → GOVERNANCE_ONLY / CAPITAL_ALLOCATION / PASSIVE does NOT clear gate
- Item 4 doc unavailable → fallback: any 13D clears gate (pre-Item4 behavior preserved)

**CoC proxy signal** (`fetch_proxy_signal()`): Scans most recent DEF 14A for change-of-control provisions and dollar-size payout estimates. Scores 2–10 pts. Does not run phrase list from `_8K_SIGNAL_PHRASES` — only `_COC_PHRASES` (change in control, accelerated vesting, golden parachute).

### Trade Logic

`trade_logic.py`:
- `classify_signal_quality()`: maps scanner output to AFFIRM / MERGER / PROCESS / ROFR / BOILERPLATE / SCORE_ONLY
- `score_to_p_deal()`: maps signal quality to calibrated P(deal) — conservative estimates pending historical calibration
- `build_trade_rec()`: deterministic BUY / WATCH / IGNORE with position sizing, EV, Kelly, staleness haircuts, priced-in check
- `is_priced_in()`: price/year_low > 1.55 OR price/first_price > 1.35 → reduces upside assumption by 40%, prevents BUY

### Current Output

Per-ticker output includes:
- `signal_quality` (AFFIRM/MERGER/PROCESS/ROFR/BOILERPLATE/SCORE_ONLY)
- `process_state` (LIVE/PATHWAY/SIGNED/SCREENING/AGING)
- `top_8k_phrase` (highest-scoring phrase string — no URL, no accession)
- `activist_13d_intent`, `activist_13d_intensity`, `activist_13d_excerpt` (200 chars), `activist_13d_triggers`
- `trade_decision`, `no_trade_reason`, `p_deal`, `ev_per_share`, `position_pct`
- Score breakdown by layer

### Current False-Positive Controls

| Control | Implementation | Status |
|---|---|---|
| SA quality check (boilerplate vs affirm) | `score_strategic_alternatives_quality()` | Active |
| Process evidence cap at 80 | `PROCESS_EVIDENCE_SCORE_CAP = 80` | Active |
| 13D Item 4 gate | `has_real_process_evidence()` + `enrich_activist_item4()` | Active (with fallback gap) |
| Staleness penalty | -5 pts at 90d, -10 pts at 180d | Active |
| Signal expiry | Per signal type, 60–540 days | Active |
| SCORE_ONLY/BOILERPLATE trade gate | Max position = 0.0 | Active |
| Bankruptcy exclusion (Layer 0) | Price < $1.50, mcap < $150M, runway < 2Q | Active |
| Priced-in check | price/year_low > 1.55 or price/first_price > 1.35 | Active |

### Current Limitations

1. Phrase matching is substring-only — no negation check, no context window, no structural position check.
2. ROFR/ROFN are boolean flags with no scope classification.
3. Layer 7 fetches 4 8-Ks only; earlier filings in the same period may be missed.
4. No source URL or accession number stored for 8-K text signals.
5. 13D fallback (unavailable doc) reverts to pre-Item4 behavior: any 13D clears process gate.
6. SA scoring defaults to ambiguous (15, False) when neither boilerplate nor affirm markers found.
7. Universe is a static Python list — not filtered dynamically by current market cap or listing status.

---

## 2. Gap Analysis vs. Historical Findings

### Form-type scope comparison

The live scanner's Layer 7 scans **8-Ks only** for text signals, plus one DEF 14A for CoC provisions only, plus SC 13D/A documents for Item 4. The historical collector scanned 8-K, 10-Q, 10-K, DEF 14A, SC 13D, SC 13D/A, 424B3, and S-4.

This means most Batch 51–70 false-positive patterns were found in forms the live scanner does not phrase-scan. The live scanner's 8-K-only scope is a strength for false-positive suppression. Many historical findings do not transfer directly to the live scanner.

### Issue-by-Issue Gap Table

| Issue | Historical batch evidence | Live scanner coverage | Status |
|---|---|---|---|
| Explicit unsolicited/superior/acquisition proposal language | MDVN, DMTX — key signal phrases | `_8K_SIGNAL_PHRASES` lines 1497–1500 now include all 4 phrases | **HANDLED** — phrases added (catchability review recommendations implemented) |
| Strategic alternatives with SA quality check | MDVN — "strategic alternatives" in 8-K, 84 days before | `score_strategic_alternatives_quality()` + `sa_is_affirm` flag | **HANDLED** |
| Banker/advisor retention | DMTX — "as its financial advisor in connection" in 8-K | `_ADVISOR_PHRASES` list + `banker_retained` flag | **HANDLED** |
| Generic ROFR/ROFN — scope not verified | EPZM (Eisai Japan ROFN), TPTX (Zai Lab Greater China ROFN) | Boolean `has_rofn`/`has_rofr` flags; no scope classification | **GAP** — any ROFN/ROFR phrase in any 8-K fires the flag |
| Asset-specific rights in collaboration/license filings | EPZM, TPTX in 10-Q filings | 10-Qs are not scanned in live scanner; 8-K ROFNs from collaboration announcements are a live risk | **PARTIAL** — lower live risk since 10-Qs not scanned, but collaboration 8-Ks could still trigger |
| Passive 13D Item 4 boilerplate — investor self-reservation | IMGO (Blackstone/Clarus IPO-era 13D) | `enrich_activist_item4()` + `parse_13d_item4()` should classify PASSIVE | **HANDLED** — but depends on Item 4 doc availability |
| Negated acquisition-proposal language | DICE — "no plan or proposal to acquire" | No negation detection in phrase matching loop | **GAP** — confirmed false positive pattern, not handled |
| Binary/UUEncoded complete submission .txt artifacts | GBT, RETA — ROFR matched in encoded binary | `_fetch_doc_text()` uses FMP's `finalLink` which typically points to HTML primary documents, not raw .txt wrappers | **LOW RISK** in live scanner — FMP finalLink selects primary HTML; historical collector fetched .txt wrappers |
| Pre-IPO PWERM stock-comp "sale of the Company" disclosures | FMTX (4 hits), CINC (3 hits) — all in 10-Q footnotes | 10-Qs are not scanned by `fetch_8k_text_signals()` | **NOT APPLICABLE** to live scanner — form type excluded |
| Lock-up/offering exhibit ROFR and sale-language artifacts | SRRA (employment ROFR in lock-up), ALPN (investor share-sale restriction) | 8-K scan matches all content in fetched document; lock-up exhibits embedded in 8-K would be scanned | **LOW RISK** — typically in SC 13D/A exhibits, not primary 8-K documents |
| Director biography cross-entity sale references | ZYNE — "sale of the company" in DEF 14A director bio | "sale of the company" not in `_8K_SIGNAL_PHRASES`; would only trigger via "potential sale of the company" in `_ADVISOR_PHRASES` | **LOW RISK** — less precise phrases in `_ADVISOR_PHRASES` require "potential" qualifier |
| 13D fallback when Item 4 doc unavailable | Any 13D clears gate when document fetch fails | `has_real_process_evidence()` line 1900: `activist_clears = True` if `not item4` | **GAP** — fallback is conservative but a false-positive risk for governance filings when doc is unavailable |
| FMP market cap/liquidity/priced-in checks | Not directly a historical batch issue | `is_priced_in()`, `MIN_MCAP_BUY`, `MIN_MCAP_ILLIQ` all present | **HANDLED** |
| Source excerpt and auditability | Live monitoring protocol requires source URL + accession per alert | `top_8k_phrase` is a phrase string only; no URL, no accession stored in text_signal output | **GAP** — 8-K alerts cannot be traced to a specific filing without re-running |
| Signal context label (AFFIRMATIVE vs RIGHTS_ONLY vs BOILERPLATE) | Process-state taxonomy covers some of this | `signal_quality` + `process_state` cover main classes; no structured context type for ROFN scope or 13D boilerplate | **PARTIAL** — main classifications present; sub-types missing |

### Summary of Top 5 Gaps

1. **Negation detection absent.** "No plan or proposal to acquire" fires `acquisition_proposal = True`. (DICE pattern)

2. **ROFR/ROFN scope not classified.** Any ROFN or ROFR phrase in a scanned 8-K sets `has_rofn = True` and contributes 18 pts with no check for whether it is whole-company, asset-specific, or geographic. Asset-specific licensing ROFNs in collaboration announcement 8-Ks would score identically to whole-company acquisition ROFNs.

3. **No source URL or accession for 8-K text signals.** `top_8k_phrase` stores a phrase string, not a link. The live monitoring protocol requires a source URL or accession for every accepted alert. 8-K-triggered alerts cannot currently satisfy that standard without manual re-lookup.

4. **13D fallback when Item 4 unavailable.** When FMP cannot retrieve the SC 13D document, the system falls back to: any 13D clears the process evidence gate. For a governance-only 13D from an unavailable document, this is a false escalation.

5. **8-K scan limited to 4 filings.** If a company files multiple 8-Ks within the lookback period (as MDVN did across April–July 2016), earlier ones may be missed. The highest-signal filing might be #5 or #6.

---

## 3. Recommended Scanner-Core Upgrades

### P0 — Must Do Now

| ID | Upgrade | Rationale | Files |
|---|---|---|---|
| P0-A | **Negation detection in phrase match loop** | Prevents DICE-type false positive (confirmed in historical batch). "no plan or proposal to acquire" should not fire `acquisition_proposal`. Single check, 4 lines. | `src/PRODUCTION_SCANNER_V12.py` — `fetch_8k_text_signals()` |
| P0-B | **Store source URL and accession in text_signals output** | Live monitoring protocol cannot be satisfied without traceability. Every 8-K-triggered alert should record which filing it came from. Add `source_url` and `source_accession` to `result` dict in `fetch_8k_text_signals()`, populated from the filing object when a phrase first matches. | `src/PRODUCTION_SCANNER_V12.py` — `fetch_8k_text_signals()` and result dict assembly |
| P0-C | **Add ROFN/ROFR scope hint to text_signals output** | Not full scope classification — just preserve named_pharma linkage and whether the ROFN/ROFR co-occurs with a collaboration/license agreement phrase. Add `rofn_scope_hint` field: "company_level_possible" vs "asset_level_likely" based on co-occurrence of "collaboration," "license," specific territory names, or product names in the same 200-char window. | `src/PRODUCTION_SCANNER_V12.py` — add `rofn_scope_hint` field near `rofn`/`rofr` detection |
| P0-D | **Raise 8-K scan window from 4 to 8 filings** | MDVN filed 8+ relevant 8-Ks across the 116-day pre-announcement period. 4-filing cap means earlier signals can be missed. n_filings=8 costs one additional FMP doc fetch per ticker in Layer 7. Low risk. | `src/PRODUCTION_SCANNER_V12.py` — `fetch_8k_text_signals(fmp, ticker, n_filings=4)` |
| P0-E | **Tighten 13D fallback behavior** | When Item 4 doc is unavailable, downgrade `activist_clears` to `True` only for known activists (from `_KNOWN_ACTIVISTS`). Unknown filers with unavailable docs should not clear the process evidence gate. This is a single conditional in `has_real_process_evidence()`. | `src/PRODUCTION_SCANNER_V12.py` — `has_real_process_evidence()` |

### P1 — Next After P0

| ID | Upgrade | Rationale | Files |
|---|---|---|---|
| P1-A | **FMP context builder: price and volume reaction after filing** | After a text signal fires, check whether price or volume moved abnormally in the 1–3 days after the filing date. Abnormal volume with a process signal is much more credible than a quiet signal. This is a market-context layer, not a classification gate. | New function in scanner; FMP historical price and volume endpoint |
| P1-B | **Alert confidence tiers: add source_context_type label** | Add a structured label to each alert: AFFIRMATIVE_PROCESS / NEGATED_PROCESS (suppressed) / RIGHTS_LANGUAGE / ASSET_SPECIFIC_ROFN / INVESTOR_BOILERPLATE / COLLABORATION_LICENSE. Output this in the scan result for use by dashboard and live log. | `src/PRODUCTION_SCANNER_V12.py` — result dict; dashboard as secondary |
| P1-C | **Add source URL and accession to dashboard card** | Surface `source_url` and `source_accession` (from P0-B) in the dashboard's process interpretation card. Reviewers should be able to click through to the primary EDGAR filing in one step. | `dashboards/dashboard_v12.html` and `/Users/jack/Documents/ma-scanner/dashboard.html` |
| P1-D | **Live monitoring log integration** | Add automatic `FILING_REVIEW` and `ALERT_DECISION` rows to `data/live_monitoring/live_monitoring_log.csv` when a scan produces a new or changed process signal. Includes source URL, accession, signal type, and signal_quality. This bridges the gap between scanner output and the live monitoring protocol standard. | New module or addition to `src/PRODUCTION_SCANNER_V12.py` main() |
| P1-E | **Dynamic universe filtering by current market cap** | At scan start, query FMP for current market cap of all universe tickers and exclude those outside $150M–$1.5B before scoring. This prevents false positives from names that have grown above the target range (institutional coverage reduces edge above $1.5B) or fallen below the bankruptcy risk threshold. | `src/PRODUCTION_SCANNER_V12.py` — universe construction in main() |

### P2 — Later

| ID | Upgrade | Rationale | Files |
|---|---|---|---|
| P2-A | **External news integration for media-sourced signals** | TSRO-type signal (sale-process media report, 17 days before announcement) cannot be captured by EDGAR-only monitoring. News integration requires a separate data source and a different evidence type. Cannot implement without source verification standards. | New data source; significant design work |
| P2-B | **100-case calibrated P(deal) thresholds** | Current P(deal) values in `trade_logic.py` are conservative estimates marked "pending historical calibration." Do not change until ≥100 cases with outcome data are available. | `src/trade_logic.py` — P_DEAL table |
| P2-C | **Structured false-positive suppression module** | Extract shared suppression logic into `src/false_positive_suppression.py` shared between live scanner and historical collector. Only worth doing after P0 items are validated in production and the pattern library is stable enough to warrant shared code. | New file: `src/false_positive_suppression.py` |
| P2-D | **Universe builder via FMP** | Replace or supplement the static Python list with a quarterly FMP query that filters by sector, market cap, and liquidity. Would keep the universe current without manual maintenance. Current static list has known staleness issues (acquired tickers still present, renamed companies). | New script: `src/universe_builder.py` |
| P2-E | **EDGAR EFTS live integration** | Switch `fetch_8k_text_signals()` from FMP-sourced filing links to direct EDGAR EFTS full-text search for more reliable phrase detection across all 8-Ks in a date range (not just the 4 most recent). Higher implementation effort; defer until P0 items are stable. | `src/PRODUCTION_SCANNER_V12.py` — `fetch_8k_text_signals()` |

---

## 4. Refactor Recommendation

### Proposed New Files

| File | Purpose | Status |
|---|---|---|
| `src/signal_context.py` | `classify_process_context(text, phrase, idx, form_type)` — returns structured context type label | **Worthwhile after P0; do not create yet** |
| `src/false_positive_suppression.py` | Shared suppression predicates (negation check, PWERM section detector, lock-up exhibit check) | **Do not create yet** — wait until P0 is validated and patterns stabilize |
| `src/fmp_context.py` | Market cap, liquidity, price reaction, volume spike, priced-in — standalone FMP context layer | **Worthwhile in P1 phase; do not create yet** |
| `src/alert_schema.py` | Canonical alert dict definition with required fields (source_url, accession, phrase, signal_quality, context_type) | **Worthwhile in P1 phase; do not create yet** |

**Decision:** Do not extract new files now. The P0 changes are 4–8-line additions to existing functions. Extracting modules before the patterns are stable would create premature abstraction with no immediate benefit. After P0 is validated in a full scan run, evaluate whether the shared suppression logic and alert schema warrant separate files.

The existing `src/item4_parser.py` is already a successful extract — it was the right call because 13D Item 4 parsing is large, deterministic, and independently testable. Use that as the bar for when to extract.

---

## 5. Smallest Next Code Change

**Recommended: Add negation detection to `fetch_8k_text_signals()` phrase match loop.**

This is P0-A. It is the smallest, safest, highest-ROI change.

**What it does:** Before setting `result[key] = True` for any acquisition-pressure phrase match, check the 25 characters immediately preceding the match index for negation words. If negation is present, skip the match.

**Why it is safe:** Real acquisition proposal disclosures do not say "no plan or proposal to acquire." The check targets the specific false-positive construct from the DICE case. No true-positive case in the 70-case batch used negated phrasing to express a real process.

**Where to implement:** `src/PRODUCTION_SCANNER_V12.py`, inside `fetch_8k_text_signals()`, the phrase match loop starting at line 1752.

**Skeleton:**

```python
_NEGATION_PREFIXES = ('no ', 'not ', 'without ', 'never ', 'no plan or ', 'no current ')

for phrase, key, pts in _8K_SIGNAL_PHRASES:
    if phrase in text and not result.get(key):
        idx = text.find(phrase)
        ctx_before = text[max(0, idx - 25): idx]
        if any(neg in ctx_before for neg in _NEGATION_PREFIXES):
            continue  # negated context — skip this match
        result[key]    = True
        result['pts'] += pts
        if not result['top_phrase']:
            result['top_phrase'] = phrase
```

**Validation cases (manual test before deploying):**

| Test input | Expected result |
|---|---|
| `"currently have no plan or proposal to acquire any additional"` | `acquisition_proposal` does NOT fire |
| `"the company received an unsolicited proposal to acquire all outstanding shares"` | `acquisition_proposal` fires |
| `"disclosed an acquisition proposal from biotech corp"` | `acquisition_proposal` fires |
| `"superior proposal within the meaning of the merger agreement"` | `superior_proposal` fires |
| `"the board determined not to solicit superior proposals"` | `superior_proposal` does NOT fire |
| `"right of first refusal in the asset purchase agreement"` | `rofr` fires (legitimate — 8-K asset deal) |
| `"no right of first refusal shall apply to"` | `rofr` does NOT fire |

---

## 6. Safety Rules

All upgrades must preserve these constraints:

- **EDGAR/source evidence is truth.** No classification upgrade should change what counts as evidence — only how precisely evidence is classified.
- **No VERIFIED labels.** No code path should write or infer VERIFIED status.
- **No CALIBRATION_ELIGIBLE labels.** P(deal) thresholds remain uncalibrated until outcome data justifies updating them.
- **No alpha claims.** The scanner is a strategic-process intelligence tool and workflow compressor. No output field should claim deal probability, trading alpha, or investment recommendation status.
- **Conservative false-positive handling.** Any ambiguous case should default to the less aggressive classification. Negation detection should err toward suppressing if uncertain. Scope hints should err toward "asset_level_likely" when context is unclear.
- **No dashboard or frontend changes** in the same commit as scanner logic changes. Separate commits preserve auditability.
- **Do not change historical classifications.** Scanner improvements affect live output only. Historical case adjudications in `data/historical_cases/` are frozen.
- **Do not run full live scanner** to validate this plan. Test each function in isolation with unit-test inputs first.

---

## 7. Source Auditability Standard (Reference)

The live monitoring protocol (`docs/live_monitoring_protocol.md`) requires five questions answered per alert:

1. Which company was monitored?
2. What source filing or public source changed?
3. What signal fired?
4. Was the alert accepted, rejected, or left open?
5. Why did that decision matter?

Current scanner output satisfies questions 1, 3, and partially 4. It does not satisfy question 2 (no source filing URL or accession for 8-K text signals). P0-B closes this gap by storing `source_url` and `source_accession` in the text_signals output. P1-C surfaces these in the dashboard card.

---

## 8. Positive Findings (Scanner Is Already Better Than Historical Collector)

These findings from the audit should NOT be treated as gaps:

- **Acquisition proposal phrases are in the scanner.** "Unsolicited proposal," "superior proposal," "proposal to acquire," and "acquisition proposal" are in `_8K_SIGNAL_PHRASES` at lines 1497–1500. The live 8-K catchability review (written before these phrases were added) recommended adding them; they have since been added. DMTX-type signals would now be caught at the right confidence level.

- **Item 4 parsing is integrated and wired.** `enrich_activist_item4()` calls `parse_13d_item4()` from `src/item4_parser.py` and the result flows through `has_real_process_evidence()`. The IMGO-type (VC/PE IPO-era 13D boilerplate) and governance-only 13D patterns are handled when the document is available.

- **SA quality scoring prevents most boilerplate escalation.** `score_strategic_alternatives_quality()` uses context markers to distinguish "may consider" (boilerplate) from "has initiated" (affirm). This handles the most common SA false positive.

- **10-Qs and DEF 14As are not phrase-scanned.** The PWERM stock-comp false positive pattern (FMTX, CINC — 7 hits combined) does not apply to the live scanner because `fetch_8k_text_signals()` only processes `formType == '8-K'`. The historical collector's broader scope created false positives that the live scanner's 8-K focus inherently avoids.

- **PROCESS_EVIDENCE_SCORE_CAP = 80** prevents score-only names from inflating into HIGH conviction without process evidence. This is a meaningful structural guard.

---

## Files Changed by This Plan

| File | Change |
|---|---|
| `docs/scanner_core_upgrade_plan.md` | New — this document |

No scanner code modified. Audit only.

## Commit Reference

See adjacent commits for historical context:
- `b2a893c` — Batch 51-70 final summary (source of historical findings)
- `d7a3ca0` — P6 adjudication (false-positive patterns documented)
- `e52dea8` — High-priority adjudication (DICE negation pattern, IMGO 13D boilerplate pattern)
