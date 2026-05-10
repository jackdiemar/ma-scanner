# Historical Process Intelligence — System Plan

**Created:** 2026-05-09  
**Status:** Infrastructure phase. Schema complete. Collection pipeline seeded.  
**Replaces:** `HISTORICAL_CASE_LIBRARY_PLAN.md` (superseded by this document)

---

## 1. What This Is and Is Not

**Is:** A longitudinal empirical dataset of biotech strategic-process events,
mapped across five normalized observation layers, designed to eventually
calibrate P(deal), EV assumptions, sequence quality, and false-positive rates.

**Is not:** A predictive model. Not ML training data (yet). Not a live signal.
Not validation of the current scanner's P(deal) assumptions — those are placeholders
until enough verified cases exist to replace them.

The scanner currently uses hard-coded prior probabilities (e.g., P(deal | AFFIRM) ≈ 0.42).
Those numbers came from rough base rates in biotech M&A literature. This dataset will
replace them with empirically derived rates from labeled outcomes. That is the purpose.

---

## 2. Data Model — Five Normalized Layers

A single company case expands into multiple observation layers:

```
CASE (company-level, 1 per process episode)
  └─ FILING_EVENTS (1+ per case: each SEC filing with a process signal)
       └─ LANGUAGE_OBSERVATIONS (1+ per filing: each key phrase detected)
  └─ TRANSITIONS (1+ per case: each state change detected)
  └─ OUTCOME (1 per case: final resolution)
```

**Scale expectation:**

| Cases | Filing Events | Language Obs | Transitions | Outcomes |
|---|---|---|---|---|
| 25 | ~75 | ~200 | ~50 | 25 |
| 100 | ~350 | ~900 | ~200 | 100 |
| 250 | ~1,000 | ~2,500 | ~600 | 250 |
| 500 | ~2,500 | ~6,000 | ~1,500 | 500 |

At 500 cases: enough for segment-level P(deal) tables, sequence calibration,
and analog matching with N≥10 per cell across key dimensions.

### Why Normalize?

A flat "cases.csv" with one row per company loses the filing-level and
phrase-level signal. The moat is not "HARP was acquired." The moat is:
- HARP's ROFR disclosure language in the 2020 collaboration 8-K
- The 32 months between ROFR introduction and deal signing
- The exact phrase triggering the ROFR classification
- The process-state trajectory: PATHWAY → LIVE (SA board filed) → SIGNED

All of that is in the filing events, transitions, and language observations —
not in the company-level case row.

---

## 3. Anti-Look-Ahead Rules — Mandatory

These rules prevent the dataset from encoding future knowledge into past labels.
Violations produce biased calibration. All contributors must follow these.

### Rule 1: observation_date = First Public Signal Date
The date the signal FIRST appeared in a public SEC filing accessible to the
market. NOT the research date. NOT the deal announcement date.

A scanner running on that day would have seen the signal. Label it as of that day only.

### Rule 2: Prices Are Point-in-Time from observation_date
- `price_at_signal` = closing price on observation_date
- `price_30d_after` = closing price 30 calendar days later
- `price_90d_after` = 90 days. `price_180d_after` = 180 days.

Record mechanically. Do not adjust for deal outcome. A false-positive may show
price_90d > price_at_signal because the market was briefly hopeful. Record it.

### Rule 3: item4_intent From Filing Text, Not Outcome
The Item 4 classification must come from actual reading of the SC 13D Item 4 section.
Do NOT infer intent from what happened next. A passive accumulation 13D that
coincidentally preceded a deal is still labeled PASSIVE_ACCUMULATION.

### Rule 4: process_state Requires Only Information Available at observation_date
If the deal was announced 6 months later, the process_state on observation_date
is still whatever the signal alone implied — SCREENING, LIVE, PATHWAY. Never SIGNED
unless the merger agreement 8-K was filed on or before observation_date.

### Rule 5: sequence_type Is Retrospective, Not Predictive
sequence_type documents what happened in the observable filing history up to and
including observation_date. ACTIVIST_THEN_SA means: activist 13D was filed, then
SA 8-K followed. Label based on the sequence that already occurred, not on what
you think will happen.

### Rule 6: deal_premium_pct Uses Pre-Announcement Price
Premium denominator = 30-day average pre-announcement. NOT price_at_signal
unless deal was announced within 30 days of signal. This prevents inflating premiums
on long-dated processes where price moved significantly before the deal.

### Rule 7: failure_reason Grounded in Contemporaneous Evidence
For non-deal outcomes: what was visibly going wrong at the time. Do NOT encode
hindsight. "Pipeline failed in Phase 3 trial — announced [date]" is correct.
"Company was too small to attract buyers" is hindsight speculation — exclude.

### Rule 8: False Positives Are Required
The collection target ratio must include at minimum 30% false-positive cases
(FAILED_REVIEW, ACTIVIST_NO_DEAL, CAPITAL_RAISE, BANKRUPTCY). A dataset
skewed toward completed deals produces a biased P(deal) inflated well above reality.
Historical AFFIRM deal rates in biotech are roughly 30-45%. Build that in from the start.

### Rule 9: VERIFY_REQUIRED ≠ Usable for Calibration
Cases marked VERIFY_REQUIRED are structural placeholders only. No P(deal) calculation,
no sequence weight, no frequency table should use VERIFY_REQUIRED data. Move cases
to PARTIAL or VERIFIED only after primary source confirmation.

---

## 4. Calibration Roadmap

### What Gets Calibrated and When

**Phase 1 (25 VERIFIED cases):**
- Structural validation only. Does the schema work? Are edge cases handled?
- No quantitative calibration.

**Phase 2 (100 VERIFIED cases):**
- First P(deal) frequency table by signal_type:
  - P(deal within 12m | SA_AFFIRM) = X/Y from data
  - P(deal within 12m | ACTIVIST_13D) = X/Y from data
  - P(deal within 12m | ROFR_ROFN) = X/Y from data
- Compare against current hard-coded priors in trade_logic.py.
  Update comments with empirical priors. Do NOT change code yet.
- Median premium distribution by signal type.
- False-positive rate by signal type.

**Phase 3 (250 VERIFIED cases):**
- Segment P(deal) by:
  - signal_type × mcap_band (small $100–400M, mid $400M–$1B, upper $1B–$2B)
  - signal_type × analyst_coverage_bucket
  - sequence_type × signal_type
- Median days_signal_to_deal by signal type.
- Failure drawdown distribution (price decline from signal to outcome).
- Sequence quality: do ACTIVIST_THEN_SA cases show higher P(deal) than SINGLE_SIGNAL?

**Phase 4 (500 VERIFIED cases):**
- Calibration-grade P(deal) and holding period tables.
- Replace hard-coded priors in trade_logic.py with empirically derived rates.
- Sequence compound_signal_quality weights validated against outcome data.
- Item 4 intent calibration: P(deal | SALE_PROCESS intent) vs. P(deal | BOARD_CHANGE).
- ROFR scope calibration: P(deal | WHOLE_COMPANY ROFR) vs. P(deal | ASSET_SPECIFIC ROFR).
- False-positive suppression: can we build a rule that reduces false signal rate
  from baseline using Item 4 intent + analyst coverage + mcap_band?

### Calibration Metrics (Future State)

| Metric | Current Basis | Future Basis |
|---|---|---|
| P(deal | AFFIRM) | ~0.42 (literature) | Empirical from dataset |
| P(deal | PROCESS) | ~0.25 (assumed) | Empirical from dataset |
| P(deal | ROFR) | ~0.18 (assumed) | Empirical from dataset |
| Median premium | ~62% (literature) | Empirical by signal type |
| Median time to deal | ~180d (assumed) | Empirical distribution |
| Failure drawdown | ~-35% (assumed) | Empirical distribution |
| Sequence delta | 0 (not calibrated) | Empirical from sequence cases |
| Item 4 delta | 0 (not calibrated) | Empirical by intent bucket |
| ROFR scope delta | 0 (not calibrated) | Empirical whole vs. asset |
| Stale signal decay | Linear (assumed) | Empirical staleness curves |

All "Future Basis" columns require minimum 100 VERIFIED cases with balanced
outcome mix before implementation.

---

## 5. Historical Analog Matching — Architecture Roadmap

### What It Produces (Future State)

Given a live ticker in the scanner, the analog matching layer finds the N
most similar historical cases and surfaces outcome distributions:

```
CURRENT SITUATION: ACCD — LIVE · COMPOUND_LIVE sequence
  Activist (SALE_PROCESS, STRONG) + SA board review + banker retained
  mcap: $340M · analyst coverage: 2 · signal age: 18d

ANALOG MATCHES: 31 similar historical situations found
  Outcome distribution:
    Acquired:       18 (58%)  — median 127d, median premium 61%
    Failed review:   9 (29%)  — median decline -31% over 180d
    Ongoing:         4 (13%)  — no resolution within 18 months
  Most common failure mode: Process abandoned after lead acquirer walkaway
  Reference cases: SRRA (acquired 2022), GNCA (failed 2022), IMGO (acquired 2022)
```

### Data Prerequisites for Analog Matching

Analog matching requires all of the following:
1. Minimum 100 VERIFIED cases (for meaningful N per segment)
2. Labeled sequence_type for all cases
3. Labeled item4_intent for all activist cases
4. Labeled mcap_band and analyst_coverage_bucket
5. Labeled outcome with days_signal_to_outcome
6. Labeled rofr_scope for ROFR cases
7. Validated compound_signal_quality mapping to outcomes

### Similarity Function Design (Future)

Two cases are similar when they share:
- Same or adjacent signal_type
- Same process_state_at_signal
- Same sequence_type (or SINGLE_SIGNAL in both)
- Same mcap_band (within one band)
- Same ± 1 analyst_coverage_bucket

Similarity score = weighted Hamming distance on categorical fields.
No ML required. Pure rule-based matching against a labeled index.

**Do NOT build this until 100 VERIFIED cases exist.** Analog matching with
N < 50 produces misleading confidence. The query could return "3 of 4 similar
cases were acquired" which sounds compelling but is meaningless at N=4.

---

## 6. Integration Plan — Existing System Modules

This dataset connects to existing code as follows. No code changes today.

| Future Integration | Connected Module | When |
|---|---|---|
| P(deal) calibration | `src/trade_logic.py` | Phase 4 (500 cases) |
| Sequence quality weights | `src/sequence_detector.py` | Phase 3 (250 cases) |
| Item 4 intent calibration | `src/item4_parser.py` | Phase 3 (250 cases) |
| State history alignment | `src/process_history.py` | Phase 2 (100 cases) |
| Analog match display | `dashboards/dashboard_v12.html` | Phase 4 (500 cases) |
| Live case forward-accumulation | `src/PRODUCTION_SCANNER_V12.py` | Phase 2 start |
| ROFR scope calibration | `src/PRODUCTION_SCANNER_V12.py` (L7) | Phase 3 (250 cases) |

**Schema compatibility check (do now):**
The `state_history.json` generated by `src/process_history.py` uses the same
process-state labels (LIVE/PATHWAY/SIGNED/SCREENING/AGING) as this dataset.
The `sequence_type` values in `src/sequence_detector.py` match the allowed values
in this schema. No breaking changes needed.

**Forward accumulation (start at Phase 2):**
Every LIVE/PATHWAY/SIGNED ticker in a scanner run that later resolves (deal
announced, process abandoned, bankruptcy) automatically generates a new
historical case from `state_history.json` transitions. Build a script that
reads state_history.json and generates candidate rows in cases.csv when
a ticker transitions to a terminal state. Verify before adding to VERIFIED table.

---

## 7. Scaling Plan — Four Phases

### Phase 1: Foundation (25 VERIFIED cases)
**Who:** Primary researcher (Jack). Manual only.  
**How:** EDGAR search + Bloomberg price pull for 10 priority cases from COLLECTION_LOG.  
**Time:** Estimated 2–3 hours per case. ~50–75 hours total.  
**Target:** 10 COMPLETED_DEAL, 8 FAILED_REVIEW/ACTIVIST_NO_DEAL, 4 ROFR, 3 BANKRUPTCY.  
**Output:** First honest false-positive rate by signal type. Schema validation.

### Phase 2: Systematic (100 VERIFIED cases)
**Who:** Research assistant or intern (2–4 hours/week task).  
**How:**
- Bloomberg Law M&A database for deal cases
- EDGAR full-text search for SA 8-Ks by SIC code and year
- Activist Monitor / 13D Monitor for activist cases
- BioPharma Catalyst deal database for false-positive confirmation
**Time:** ~4 months at research assistant pace.  
**Output:** First P(deal) frequency table. Compare to hard-coded priors. Flag divergences.

### Phase 3: Scale (250 VERIFIED cases)
**Who:** Research assistant + automated EDGAR backfill script.  
**How:**
- Build `scripts/backfill_candidates.py`: queries EDGAR for SA 8-Ks in SIC
  2836/2835/8731 from 2015–2025, generates CANDIDATE rows in collection_targets.csv,
  queues for human verification.
- Forward accumulation script from state_history.json.
**Time:** ~6 months.  
**Output:** Segment-level P(deal) tables. Sequence quality validation.

### Phase 4: Calibration (500 VERIFIED cases)
**Who:** Automated pipeline + quarterly manual review.  
**How:**
- Live scanner generates new cases as they resolve.
- Quarterly backfill of new deal announcements.
- Annual recheck of ONGOING cases.
**Output:** Calibration-grade P(deal), sequence weights, ROFR scope rates.
         Replace hard-coded priors in trade_logic.py.
         Implement analog matching in dashboard.

### Path to 1,000+ Cases
At 500 verified cases + live forward accumulation at ~5 resolved cases/month
= 1,000 cases within ~8 years of continuous operation.

Alternatively: license Evaluate Pharma or DealForma deal database for historical
bulk import (2010–2025 biotech deals). Validate a sample, bulk-import verified
fields. This could add 200–400 cases in one quarter if budget allows.

---

## 8. How This Becomes the Moat

**The case library creates a compounding first-mover advantage.**

A competitor building this today starts 18–24 months behind in data accumulation.
The architecture is replicable in weeks. The labeled history is not.

Specific defensibility layers:

1. **False-positive rate by signal type** — knowing empirically that 60% of
   AFFIRM signals in the $150–400M mcap range result in no deal within 18 months
   is information that requires 3–5 years of operational history. You cannot buy it.

2. **Sequence quality validation** — knowing that ACTIVIST_THEN_SA sequences
   produce P(deal) 2.3× higher than single ACTIVIST_13D signals (hypothetical)
   requires labeled historical data, not assumptions.

3. **Item 4 intent calibration** — knowing that SALE_PROCESS intent in Item 4
   increases P(deal | ACTIVIST_13D) from X% to Y% requires cases where Item 4
   was labeled before outcome was known.

4. **Failure mode patterns** — knowing which process-state trajectories reliably
   predict failure (capital_raise → signal death, activist_gone → rapid state
   downgrade, signal age > 90d without escalation → ~80% no-deal) requires labeled
   historical failures.

5. **Analog matching database** — the ability to say "this situation resembles
   31 historical cases, 58% of which resulted in acquisition at median 127d" is
   only possible with the labeled historical dataset. No competitor without 3+
   years of accumulated, verified cases can offer this.

---

## 9. Files

| File | Layer | Status |
|---|---|---|
| `data/historical_cases/schema.json` | Company cases | Complete |
| `data/historical_cases/filing_events_schema.json` | Filing events | Complete |
| `data/historical_cases/transitions_schema.json` | Transitions | Complete |
| `data/historical_cases/language_observations_schema.json` | Language | Complete |
| `data/historical_cases/outcomes_schema.json` | Outcomes | Complete |
| `data/historical_cases/cases_seed.csv` | Company cases | 15 seed (VERIFY_REQUIRED) |
| `data/historical_cases/collection_targets.csv` | Research queue | 150 CANDIDATE |
| `data/historical_cases/cases_verified.csv` | Company cases | Empty — start here |
| `data/historical_cases/source_queries.md` | Collection ops | Complete |
| `data/historical_cases/verification_checklist.md` | Collection ops | Complete |
| `data/historical_cases/COLLECTION_LOG.md` | Tracking | Seeded |
| `strategy_audit/HISTORICAL_PROCESS_INTELLIGENCE_PLAN.md` | Strategy | This document |

---

## 10. Next 10 Cases to Verify First

Ordered by research effort + strategic value (false positives first — they are
the rarest and most important for calibration):

1. **GNCA** — Genocea SA_AFFIRM → bankruptcy. Cleanest false positive in dataset.
   Find 8-K date on EDGAR. Confirm wind-down announcement. Confirm price on 8-K date.

2. **CRBP** — Corbus SA_AFFIRM → no deal. Find the specific SA 8-K on EDGAR.
   Confirm what happened: deal failed, capital raise, ongoing?

3. **MGTA** — Magenta SA_AFFIRM → wind-down. Find 8-K + wind-down announcement.

4. **HARP** — ROFR → acquired. Find AbbVie collaboration 8-K (2020). Confirm ROFR
   language. Get price on that date. Get deal announcement 8-K (2023). Calculate premium.

5. **SRRA** — Banker/SA → acquired (GSK). Find first process signal 8-K. Get price.
   Get deal announcement. Calculate premium.

6. **PTGX** — ROFR (program-specific). Find J&J collaboration 8-K. Confirm scope
   language. Confirm no whole-company exercise.

7. **IMGO** — SCORE_ONLY → acquired (Merck). Confirm no prior process signal.
   Get deal announcement 8-K. Calculate premium.

8. **RIGL** — Activist 13D → no deal. Find SC 13D on EDGAR. Read Item 4. Confirm
   no acquisition as of 2025. Label item4_intent from text.

9. **FLXN** — Flexion/Pacira completed deal 2021. EDGAR 8-K. Price. Premium.
   Confirm deal value ~$448M. Small cap, fits target range.

10. **DOVA** — Dova Pharma/SOBI completed deal 2021. EDGAR 8-K. Confirm deal value
    ~$915M. Confirm prior process signals if any.
