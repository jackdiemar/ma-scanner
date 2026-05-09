# Historical Case Library — Design Plan

**Created:** 2026-05-09  
**Status:** Infrastructure phase. Schema finalized. Seed cases in progress.  
**Goal:** 500+ labeled biotech strategic-process events — winners and false positives.

---

## Strategic Purpose

This is the calibration layer. Every scoring weight, P(deal) estimate, sequence
pattern, and false-positive gate in the scanner is currently assumption-based.
The historical case library converts assumptions into empirically grounded numbers.

The moat is not the scanner architecture. Any competent quant can rebuild the
architecture in weeks. The moat is:

1. Running process-state infrastructure generating new data every scan
2. A labeled historical dataset of 500+ cases mapping signal → outcome
3. Calibrated P(deal) by signal type, sequence, and market-cap band
4. A trained false-positive suppression layer with real labeled examples

None of these are replicable without years of operational history.

---

## What This Dataset Will Eventually Calibrate

| Model Input | Uses Cases Of Type |
|---|---|
| P(deal) by signal_quality tier | All types |
| P(deal) by sequence_type | Multi-event sequence cases |
| EV/share distribution | Completed deals with deal_premium_pct |
| Holding period assumptions | completed_deal cases, days_signal_to_outcome |
| Downside scenarios | failed_review, bankrupt, capital_raise cases |
| Item 4 intent precision | activist_13d cases with labeled intent |
| ROFR scope utility | rofr_rofn cases with labeled rofr_scope |
| Sequence quality weights | All cases with sequence_type labeled |
| False-positive rate by ticker size | All non-deal cases |

**CRITICAL:** No calibration from this dataset should be applied to the scanner
scoring until at least 100 verified cases are labeled, with balanced outcomes.
With 10-25 seed cases, the only valid use is structural validation and schema
testing.

---

## Case Taxonomy

### event_type values (mutually exclusive per observation)

| event_type | Meaning |
|---|---|
| `COMPLETED_DEAL` | Target was acquired at a meaningful premium |
| `FAILED_REVIEW` | Board announced strategic review; no deal resulted |
| `ACTIVIST_NO_DEAL` | Activist filed 13D; no acquisition within 18 months |
| `ROFR_TRIGGERED` | ROFR/ROFN partner exercised rights; deal followed |
| `ROFR_NO_TRIGGER` | ROFR/ROFN disclosed; partner did not exercise; no deal |
| `CAPITAL_RAISE` | Strategic review led to capital raise, not sale |
| `MERGER_EQUALS` | Merger of equals (no premium; stock deal) |
| `ASSET_SALE` | Partial asset sale, not whole-company acquisition |
| `BANKRUPTCY` | Process failed; company went bankrupt or wound down |
| `ONGOING` | Signal observed; outcome not yet resolved |

### signal_type values (what triggered the case entry)

| signal_type | Trigger |
|---|---|
| `SA_AFFIRM` | Board 8-K affirming strategic alternatives review |
| `SA_BOILERPLATE` | Risk-factor SA language; not board-affirmed |
| `ACTIVIST_13D` | SC 13D filed with process-relevant Item 4 |
| `ACTIVIST_13D_PASSIVE` | SC 13D filed; Item 4 governance/passive only |
| `BANKER_RETAINED` | Advisor retention or potential-sale 8-K language |
| `ROFR_ROFN` | Right of first refusal/negotiation detected |
| `MERGER_AGREEMENT` | Merger agreement 8-K filed |
| `SCORE_ONLY` | No process signal; score-driven inclusion |

---

## Labeling Rules — Avoiding Look-Ahead Bias

These rules are mandatory. Violating them produces a biased dataset.

### Rule 1: Observation Date = First Public Signal Date

`observation_date` is the date the signal FIRST appeared in a public SEC filing.
It is NOT the date the researcher added the case. It is NOT the deal announcement
date. It is the date a scanner running on that day would have first seen the signal.

### Rule 2: All Prices Are Relative to observation_date

- `price_at_signal` = closing price on observation_date
- `price_30d_after` = closing price 30 calendar days after observation_date
- `price_90d_after` = closing price 90 calendar days after observation_date
- `price_180d_after` = closing price 180 calendar days after observation_date

These prices are recorded mechanically. They do NOT encode outcome knowledge.
A false-positive case might show price_90d_after > price_at_signal even if no
deal occurred. That is correct — record it accurately.

### Rule 3: Deal Premium Uses Pre-Announcement Price

`deal_premium_pct` = (deal_price - price_30d_before_announcement) / price_30d_before_announcement.

Do NOT use price_at_signal as the premium denominator unless deal was announced
within 30 days of signal. This prevents inflating premiums on long-dated processes.

### Rule 4: Sequence Labels Are Retrospective, Not Predictive

`sequence_type` is labeled based on what actually occurred in the filing history
leading up to and including the signal. It is NOT a prediction. A case labeled
`ACTIVIST_THEN_SA` means: an activist 13D was filed, THEN an SA 8-K followed.
Label only what happened before or concurrent with observation_date.

### Rule 5: item4_intent From Actual Filing Text

`item4_intent` must come from actual reading or LLM parse of Item 4 text.
Do NOT infer from outcome. A passive accumulation 13D that preceded a deal
is still labeled `PASSIVE_ACCUMULATION`, not `SALE_PROCESS`.

### Rule 6: failure_reason Must Precede Hindsight

For FAILED_REVIEW and ACTIVIST_NO_DEAL cases, `failure_reason` explains
what was observable as the process deteriorated (company ran out of cash,
deal terms failed, acquirer pulled out). It does NOT encode outcome prediction.

### Rule 7: data_quality Must Reflect Verification Status

- `VERIFIED`: Prices checked against Bloomberg/Yahoo Finance, filing URL confirmed,
  deal terms from press release or 8-K. All dates confirmed.
- `PARTIAL`: Some fields verified, some approximated from memory/general knowledge.
  Dates and prices need Bloomberg confirmation.
- `VERIFY_REQUIRED`: Researcher recalled the case but specific data was not
  checked. Field may be directionally correct but cannot be used for calibration.

Only `VERIFIED` cases should be used in quantitative calibration. `PARTIAL` cases
can be used for structural testing. `VERIFY_REQUIRED` is placeholder only.

---

## Collection Workflow

### Phase 1 — First 25 Cases (Manual, High Quality)

**Target:** 25 cases, minimum 60% VERIFIED, by researcher.

**Sources:**
- BioPharma Catalyst / Evaluate Pharma deal databases for completed acquisitions
- SEC EDGAR full-text search for SA 8-Ks from 2019–2025
- Activist Monitor / WhaleWisdom for 13D filings in biotech

**Case selection criteria for Phase 1:**
- $100M–$2B market cap at signal date (slightly wider than live scanner range)
- 2019–2025 (post-COVID M&A cycle through present)
- Mix: target 15 completed deals + 10 false positives
- At least 3 ROFR/ROFN cases
- At least 5 activist cases
- At least 3 FAILED_REVIEW or BANKRUPTCY cases

**Specific cases to research first (from seed list):**
1. HARP — Harpoon/AbbVie (ROFR → completed deal)
2. GNCA — Genocea (SA_AFFIRM → bankruptcy, textbook false positive)
3. SRRA — Sierra Oncology/GSK (completed deal, small cap)
4. GRCL — Gracell/AstraZeneca (completed deal)
5. PAND — Pandion/Merck (completed deal)
6. CRBP — Corbus (SA_AFFIRM → no deal)
7. MGTA — Magenta Therapeutics (SA_AFFIRM → wind-down)
8. RIGL — Rigel Pharmaceuticals (activist → no deal)
9. IMGO — Imago/Merck (completed deal, no prior SA)
10. VNDA — Vanda (activist → no deal, ongoing)

**Estimated effort:** 2–3 hours per VERIFIED case (Bloomberg price pull, EDGAR
filing URL, deal terms from 8-K). 25 cases ≈ 50–75 hours of research assistant
work. Prioritize hiring a research assistant or intern for Phase 1.

### Phase 2 — First 100 Cases (Systematic)

**Target:** 100 cases, 70% VERIFIED, within 3 months.

**Expansion sources:**
- Bloomberg Law M&A database: filter for biotech/pharma, $100M–$2B deal value, 2015–2025
- SEC EDGAR 8-K full-text search: "exploring strategic alternatives" biotech, by quarter
- Activist database: 13D filings in biotech SIC codes 2836, 2835, 8731

**Add case categories not in Phase 1:**
- 5 ROFR_NO_TRIGGER cases (ROFR disclosed, never exercised)
- 5 CAPITAL_RAISE cases (SA process → equity offering instead of deal)
- 5 MERGER_EQUALS cases (stock deals with minimal or no premium)
- 5 pre-2019 cases (2015–2018 cycle for longer time series)

**At 100 cases:** Run first P(deal) frequency table by signal_type.
Compare to current scanner assumptions. Adjust prior assumptions in
trade_logic.py comments only — not yet in scoring weights.

### Phase 3 — Path to 500 Cases (Operational)

**Target:** 500 cases over 18–24 months.

**Methods:**
- Forward accumulation: every LIVE/PATHWAY case in the scanner becomes a
  historical case once resolved. Current scan generates ~20 LIVE names.
  At 2 scans/week × ~5 new resolutions/month = ~60 new cases/year from live data.
- Backfill automation: build a script that queries SEC EDGAR for SA 8-Ks
  in SIC codes 2836/2835/8731 from 2015–2025, generates PARTIAL cases,
  queues for human verification.
- Outcome tagging: add outcome tagging to scanner UI so every resolved
  LIVE/PATHWAY case in the watchlist gets labeled when deal closes or falls apart.

**At 500 cases:** P(deal) tables are calibration-grade for:
- Signal quality tier (AFFIRM, PROCESS, ROFR)
- Sequence type (ACTIVIST_THEN_SA, COMPOUND_LIVE, etc.)
- Market cap band ($100M–$300M vs. $300M–$800M vs. $800M–$1.5B)
- Days from signal to outcome distribution
- Premium distribution by acquirer type (large pharma vs. mid-cap vs. PE)

---

## How This Becomes the Moat

The case library creates compounding advantages:

**Year 1 (25–100 cases):**
- First honest P(deal) frequency table from real data
- Initial false-positive rate by signal type (what % of SA_AFFIRM cases dealt vs. not)
- Sequence validation: do sequences like ACTIVIST_THEN_SA actually have higher P(deal)?
- Can update scanner assumption comments with real historical priors

**Year 2 (100–300 cases):**
- Enough data to segment by market cap, therapeutic area, and signal age
- Can build calibration curve: P(deal | mcap_band, signal_quality, sequence_type)
- Sequence quality weights become empirical rather than rule-based assumptions
- Can identify new false-positive patterns from labeled failures

**Year 3+ (300–500 cases):**
- Calibration-grade P(deal) and holding period tables
- Enough false positives to train (or rule-base) a false-positive suppressor
- Enough ROFR cases to characterize scope (whole-company vs. asset-level success rates)
- Analog matching: given a live situation, find the 5 most similar historical cases
  and surface their outcomes as base-rate context

**Defensibility:** A competitor building this today starts 3 years behind. The
architecture is replicable. The labeled history is not.

---

## Integration Points (Future)

Once 100+ VERIFIED cases exist:

1. **P(deal) calibration:** Replace hardcoded priors in `src/trade_logic.py` with
   empirically derived rates from this dataset, segmented by signal_quality and mcap_band.

2. **Sequence quality weighting:** Replace `compound_signal_quality` labels with
   empirically validated P(deal) deltas from `src/sequence_detector.py` patterns.

3. **Analog matching in modal:** `buildModalSequenceSection()` in `dashboard.html`
   can surface "3 similar historical situations: 2 acquired, 1 failed review" as
   context alongside the sequence timeline.

4. **False-positive suppression tuning:** Item 4 parsing thresholds in
   `src/item4_parser.py` can be calibrated against labeled false-positive cases.

5. **ROFR scope scoring:** `src/PRODUCTION_SCANNER_V12.py` ROFR detection can
   weight whole-company vs. asset-level ROFR differently once scope base rates exist.

---

## Files

| File | Purpose |
|---|---|
| `data/historical_cases/schema.json` | Field definitions, types, allowed values |
| `data/historical_cases/cases_seed.csv` | 15 seed cases (VERIFY_REQUIRED or PARTIAL) |
| `data/historical_cases/cases_verified.csv` | Verified cases (start empty, add as verified) |
| `data/historical_cases/COLLECTION_LOG.md` | Track verification progress, sources, gaps |

Start adding to `cases_verified.csv` only after Bloomberg/EDGAR confirmation.
`cases_seed.csv` is structural scaffolding only — do not use for calibration.
