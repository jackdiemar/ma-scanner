# Strategic Pivot: Signal-Enriched Scanner

Generated: 2026-05-16
Scope: Strategic audit of the historical case factory. No classifications changed. No scanner run. No dashboard touched.
Basis: 86-case adjudication record, batch summaries, scanner_core_upgrade_plan.md, fmp_integration_opportunities.md, case_factory_library_opportunities.json, live scanner V12 architecture, trade_logic.py.

---

## 1. Current State — Blunt Assessment

### What Is Actually Built

| Layer | What Exists | Quality |
|---|---|---|
| Historical pipeline | Orchestrator, date backfiller, filing collector, exception queue builder, source pull helper, batch alignment validator, source evidence integrity validator, schema layer | Solid. All steps documented, committed, tested. |
| Historical data | 86 adjudicated cases, 78 dated announcement rows, 122 source_evidence.csv rows, ~935 pre-announcement filings collected across batches 51-70 and 71-100 | Real. Source-backed. Audit-friendly. |
| False-positive taxonomy | 9+ distinct patterns across 3 batches, each with case-level evidence and suppression rule | This is the moat. Most scanners don't have this. |
| Live scanner (V12) | Layer 0-7 scoring, SA quality check, 13D Item 4 parsing, trade logic with P(deal), PROCESS_EVIDENCE_SCORE_CAP, priced-in check | Functional but 5 known P0 gaps unpatched. |
| Strategic docs | scanner_core_upgrade_plan.md, fmp_integration_opportunities.md, case_factory_library_opportunities.json | Useful. Not code. |
| Signal vocabulary | _8K_SIGNAL_PHRASES, _ADVISOR_PHRASES, signal_quality taxonomy (AFFIRM/PROCESS/ROFR/MERGER/BOILERPLATE/SCORE_ONLY), item4_parser.py | Live scanner has it. Historical batch collector has its own phrase set. They diverge. |

### What Is Missing

| Gap | Impact |
|---|---|
| No signal-enriched historical cohort | We are proving base rate, not finding true positives faster |
| 5 live scanner P0 gaps not patched | Alerts are untraceable (no source URL), negation fires false positives, ROFR scope not classified |
| No live monitoring cadence | V12 runs ad hoc; no weekly output, no standing watchlist, no alert log |
| FMP price/liquidity overlay not built | Historical cases have no market context; live alerts have no tradability check beyond `is_priced_in()` |
| Historical and live phrase vocabularies diverge | EFTS batch collector sees phrases V12 doesn't and vice versa |
| No source-linked alert format | Analyst memo requires source URL + excerpt; current scan output has neither for 8-K signals |

### Current Limitation

Batch 71-100 processed 427 pre-announcement filings across 16 cases in one EDGAR API run. 25 possible hits emerged. 25 false positives resolved. 0 true signals. This is correct behavior for a base-rate study. It is the wrong workload for finding signals fast.

The bottleneck is not the pipeline. It is the candidate selection strategy.

---

## 2. Is the Current Case Selection Too Random?

**Yes, for product development. No, for base-rate calibration.**

The current selection draws from the five-year biotech acquisition universe (2015-2024, US-listed, $150M-$1.5B). Cases are assigned case numbers sequentially. No filter preferentially selects cases with known prior process activity.

The consequence: at 3.5% true signal rate, running 200 random cases to completion produces ~7 true signals. At current pace (roughly 30 cases per batch, multiple sessions per batch), completing 200 cases takes months of work. The expected return per batch is 0.6 true signals.

This is a viable base-rate study design. It is not a viable product development design.

**What the data already shows:**

From `batch_51_70_final_summary.md` and `batch_71_100_adjudication_report.md`, the 25 signal hits in batch 71-100 resolved as follows:
- 7 hits: asset-specific ROFN/ROFR (program, compound, territory)
- 5 hits: offering prospectus disclaimer
- 3 hits: director biography
- 3 hits: performance condition equity award boilerplate
- 2 hits: partner equity stake divestiture
- 2 hits: wrong-direction acquisition
- 1 hit: anti-takeover provision disclosure
- 1 hit: ROFR warranty (negative statement)
- 1 hit: UUEncoded binary artifact

**Zero** of these 25 hits were from the high-precision signal types that produced the 3 true signals:
- "unsolicited proposal" (MDVN, DMTX)
- "superior proposal" (DMTX)
- "strategic alternatives" with affirm context
- "as its exclusive financial advisor" + strategic review context

The batch did not fire on any of the high-precision phrases. This means we processed 427 filings and found only low-precision hits. A smarter selection would have put those 427 filing reads toward cases where the high-precision phrases actually appear.

**Conclusion:**
- **Broad baseline cohort**: continue at low priority. Value is base-rate proof and false-positive taxonomy expansion.
- **Signal-enriched cohort**: build now. Value is product development, true-positive discovery, and precision measurement.
- **Live monitoring cohort**: highest priority if goal is a profitable system within weeks.

---

## 3. Proposed New Cohort Strategy

### Cohort A — Broad Baseline (Current Path, Reduced Priority)

**Purpose:** Prove real base rate across a representative sample. Document false-positive taxonomy. Build calibration denominator.

**Status:** 86 cases done (70 finalized + 16 from batch 71-100 dated cases). Methodologically correct. Continue at low pace.

**When to stop:** Stop expanding the broad baseline once the false-positive taxonomy stops producing new patterns. Batches 51-70 and 71-100 produced 9+ patterns total, several repeating (binary artifact, S-8 boilerplate, director bio). Diminishing returns. The taxonomy is roughly stable.

**Target:** 100-120 cases total (add ~15-35 more). Not 200. 200 broad cases is 6+ more months of work for an expected 1-2 additional true signals.

### Cohort B — Signal-Enriched Historical Cohort (Build Next)

**Purpose:** Find more true positives. Measure precision on high-signal phrases. Build the training set for calibration.

**How to build:**
1. Use EDGAR EFTS (already wired in the batch collector) to search for historical acquisition filings containing high-precision phrases: "unsolicited proposal," "superior proposal," "strategic alternatives" with affirm context, "exploring a sale," "retained [bank] as its financial advisor."
2. Filter to companies with known acquisition announcement dates.
3. Exclude hits that appear only in post-announcement filings (SC 14D-9, proxy).
4. Rank resulting cases by phrase precision, filing proximity to announcement, and filing form type (8-K > 13D > 10-Q).
5. Run these cases through the existing pipeline first — they should produce true signals at much higher rates.

**Distinct from broad baseline:** The enriched cohort doesn't care about the base rate. It is specifically designed to find cases where real process language existed before the deal announcement. Its purpose is precision testing, not population estimation.

**Non-acquired companies:** Also include current live names (no acquisition) where similar phrases appeared historically but deals didn't close. This is the false positive / missed signal surface — critical for calibrating P(deal).

**Priority:** High. Build this before running Batch 101-130.

### Cohort C — Live Scanner Candidate Cohort (Highest Priority)

**Purpose:** Operate the scanner as a live product. Flag current names with active process evidence. Weekly review cadence.

**How to build:**
1. Run V12 against the current $150M-$1.5B biotech universe.
2. Apply FMP market cap/liquidity filter at scan start (already planned in scanner_core_upgrade_plan.md P1-E).
3. Surface names with AFFIRM/PROCESS/ROFR signal_quality above SCORE_ONLY.
4. Attach source URL + accession to every alert (P0-B, not yet implemented).
5. Run weekly. Compare to prior week. Flag new or escalated signals.
6. Produce a top-10 analyst memo weekly.

**This is the product.** Cohort A and B feed calibration. Cohort C is the deliverable.

---

## 4. Why the Low Hit Rate Is Valuable

3.5% is not failure. It is signal.

**The filtering problem is hard.** The false-positive surface is enormous: 9 confirmed patterns, each with multiple variants, each appearing in legal standard-issue filings across every form type. A naive keyword scanner would fire on "right of first negotiation" in 15-20% of biotech filings. The binary artifact pattern (GBT, RETA, SGEN) would trick any substring matcher. The anti-takeover provision pattern (ALBO) looks exactly like a real acquisition proposal phrase.

**Most generic NLP scanners overfire.** They cannot distinguish:
- Arena's ROFN on LP659 (LBPH) from AstraZeneca's option to buy the whole company
- "Cash settlement on the sale of the Company's common stock" = partner divesting equity stake (SNDX) from actual sale-process language
- Director biography about Keryx's acquisition (STML) from Stemline's own process
- CHMA's proxy annual director bio (9 days before announcement) from actual board strategic review disclosure

The ability to correctly classify all 25 of the batch 71-100 hits as false positives — with reasons, excerpts, and source URLs — is more valuable than hitting on them. An analyst who reads a boilerplate 424B3 anti-takeover section (ALBO) as a real acquisition signal burns two hours and finds nothing. The taxonomy prevents that.

**The moat is precision, not hit count.** A system that flags 3 real signals per 86 cases — and correctly discards 25 false positives — is more valuable than one that flags 28 and leaves the analyst to sort it out. Time compression is the product.

**False positives teach what to buy more clearly than true positives alone.** Each pattern in the taxonomy is a filter that can be applied in the live scanner to suppress boilerplate and surface real signals. The taxonomy is growing. SNDX (partner equity stake divestiture) was a new pattern in batch 71-100 that isn't yet in the live scanner suppression logic.

---

## 5. Does This Already Exist?

### What Exists in the Repo

The combination that exists:

- **Source-backed historical taxonomy** — 86 cases adjudicated with verbatim excerpts, accession numbers, filing dates, false-positive categorization, and reasoning. `source_evidence.csv` has 122 rows.
- **Filing-level false-positive map** — 9 patterns documented with case-level evidence. Each pattern has an engineering fix recommendation (`scanner_core_upgrade_plan.md`, `batch_51_70_final_summary.md`).
- **Live scanner logic** — V12 with Layer 0-7 scoring, SA quality check, 13D Item 4 parsing, trade logic, process state taxonomy, priced-in check. `src/PRODUCTION_SCANNER_V12.py` + `src/trade_logic.py` + `src/item4_parser.py`.
- **Market context design** — FMP integration plan with price reaction, volume spike, liquidity bucket, priced-in flag. `docs/fmp_integration_opportunities.md`.
- **Adjudication queue** — Priority-ranked manual review system with P1-P4 tiers and source pull tools. `edgar_source_pull_helper.py`.
- **Validator layer** — `validate_batch_alignment.py`, `validate_source_evidence_integrity.py`, `run_case_factory_validations.py`. Prevents data corruption at scale.

### What Is Missing From the Repo

- **Signal-enriched cohort builder** — not built. Cases are selected broadly, not by prior-signal presence.
- **Live monitoring cadence** — no scheduled scan, no standing watchlist, no alert log auto-populated.
- **Source URL in scan output** — `top_8k_phrase` stores a phrase string, not a link. Alerts are unverifiable without re-running. (P0-B not yet implemented.)
- **Negation detection** — "no plan or proposal to acquire" fires `acquisition_proposal = True` in V12. (P0-A not yet implemented.)
- **ROFR/ROFN scope hint** — any ROFN phrase in any 8-K sets `has_rofn = True`. No asset vs. company classification. (P0-C not yet implemented.)
- **Weekly analyst memo** — no template, no cadence, no recipient format.
- **False-positive suppression module** — taxonomy is documented in markdown. Not yet applied in V12 as code.
- **FMP context builder** — `docs/fmp_integration_opportunities.md` is a design note. `src/historical_case_tools/fmp_candidate_discovery_stub.py` is a stub. No production FMP context enrichment runs.

### Is This System Uncommon?

The combination of source-backed EDGAR taxonomy + live scanner + adjudication queue is not found in standard quantitative tools. Bloomberg, FactSet, and Capital IQ have M&A filing feeds but no source-backed false-positive suppression at the process-evidence level. Generic NLP scanners (e.g., Bloomberg's event extraction) fire on ROFN/ROFR without scope classification. They cannot distinguish ALBO's anti-takeover boilerplate from an actual acquisition proposal.

However: the system is currently more research factory than product. It is closer to an analyst workflow than a live scanner. The distinction matters.

**Current classification:**

| Component | Status |
|---|---|
| Research factory (historical taxonomy) | Built. Useful. |
| Live scanner (V12 with Layer 7) | Built. 5 P0 gaps. No source URLs in output. |
| Analyst workflow compression | Partial. No standing weekly memo. No auto-alert. |
| Investable live product | Not yet. Missing source-linked alerts + FMP tradability overlay. |

The system is distinct if the live scanner gaps are closed and the false-positive taxonomy is applied as code. It is not distinct if it remains a research document plus an ad-hoc scan.

---

## 6. Fastest Path to Useful/Profitable System (3-Week Plan)

The constraint: summer work starts soon. Do not optimize for completeness. Optimize for a usable signal-review workflow in an analyst's hands within 3 weeks.

### Week 1 — Patch the Scanner, Get One Clean Run

**Day 1-2: P0 scanner patches** (all in `src/PRODUCTION_SCANNER_V12.py`)
- P0-A: Negation detection in phrase match loop (4-8 lines). Fix confirmed DICE pattern.
- P0-B: Store `source_url` and `source_accession` in text_signals output. Alerts become verifiable.
- P0-C: Add `rofn_scope_hint` field ("company_level_possible" vs "asset_level_likely") based on co-occurrence with collaboration/license phrases.
- P0-D: Raise 8-K scan window from 4 to 8 filings. MDVN filed 8+ relevant 8-Ks in 116-day window.
- P0-E: Tighten 13D fallback. Unknown filers with unavailable docs should not clear process evidence gate.

**Day 3: Run scanner against live universe.**
- Produce `data/scans/scan_latest.json`.
- Extract all names with signal_quality in {AFFIRM, PROCESS, ROFR, MERGER}.
- For each, verify source_url populated (P0-B must be working).

**Day 4-5: Build top-10 source-linked review list.**
- Manually inspect the top 10 hits using the source URLs from scan output.
- Apply false-positive taxonomy from 3-batch study.
- Classify each: TRUE_AFFIRM / RIGHTS_LANGUAGE / BOILERPLATE / ASSET_SPECIFIC / WATCH.
- Write `data/live_monitoring/week1_process_review.md`.

**Output of Week 1:** One clean scanner run, 5 P0 gaps closed, top-10 annotated live list with source links.

### Week 2 — Build Signal-Enriched Historical Cohort + Alert Format

**Day 1-3: Signal-enriched cohort builder.**
- Build `src/historical_case_tools/signal_enriched_cohort_builder.py`.
- Input: `acquisition_announcement_dates.csv` (known deal universe).
- Step 1: Load existing filing targets from `batch_51_70_pre_announcement_filing_targets.csv` and `batch_71_100_pre_announcement_filing_targets.csv`.
- Step 2: Search for HIGH-precision phrases in existing signal_hits files: "unsolicited proposal," "superior proposal," "strategic alternatives" + affirm context markers, "as its financial advisor" + strategic review context.
- Step 3: Exclude hits matching known false-positive patterns (binary artifact, PWERM, offering disclaimer, director bio, S-8 plan, anti-takeover boilerplate, asset-specific ROFN/ROFR, ROFR warranty).
- Step 4: Rank remaining hits by precision phrase, filing type, days before announcement.
- Output: `data/historical_cases/signal_enriched_candidate_queue.csv` + `signal_enriched_candidate_queue_report.md`.

**Day 4-5: Source-linked alert format.**
- Define the standard alert record: ticker, signal_quality, source_url, accession, filing_date, filing_type, excerpt_150_chars, days_since_filing, market_cap, priced_in_flag, analyst_action_required.
- Write `data/live_monitoring/alert_format_schema.json`.
- Write a sample alert for the highest-confidence name from the Week 1 scan.

**Output of Week 2:** Signal-enriched queue (historical cases with real process hits pre-identified), alert format schema, sample live alert with source link.

### Week 3 — Weekly Memo + Live Watchlist

**Day 1-2: Weekly scan cadence.**
- Set up a simple `scripts/run_weekly_scan.sh` that runs V12 and extracts the top-10 alert list to a markdown file.
- Auto-populate `data/live_monitoring/live_monitoring_log.csv` with new or changed AFFIRM/PROCESS signals.
- Include: ticker, scan_date, signal_quality, source_url, accession, filing_date, excerpt, market_cap, priced_in.

**Day 3-4: First weekly memo.**
- Write `data/live_monitoring/weekly_memo_YYYYMMDD.md` covering:
  - Top 5-10 live names with active process evidence
  - Source filing and excerpt for each
  - False-positive check: is this boilerplate or real?
  - Market context: market cap, priced-in flag, days since filing
  - Action: WATCH / INVESTIGATE / DISCARD

**Day 5: Paper-trade / watchlist validation.**
- For each confirmed non-boilerplate hit: record entry in watchlist_tracking.json.
- Review after 30 days: did a deal announce? Did the stock move?
- This generates outcome data to calibrate P(deal) thresholds in `trade_logic.py`.

**Output of Week 3:** Weekly memo template, live monitoring log running, watchlist validation starting.

**3-week deliverable:** A weekly analyst memo with top 10 live biotech names showing source-backed process evidence, false-positive classifications, and market context. Each name links directly to the EDGAR filing that triggered the signal.

---

## 7. What to Stop Doing

**Stop expanding the broad baseline past 120 cases.** The taxonomy is stable. Each additional broad batch produces ~0.5 true signals and 5-10 new instances of known false-positive patterns. Diminishing returns set in after 100 cases. At 86, the base rate is already statistically meaningful for this universe.

**Stop writing standalone planning docs without tied implementation.** `scanner_core_upgrade_plan.md`, `fmp_integration_opportunities.md`, `case_factory_library_opportunities.json`, and `docs/case_factory_library_opportunities.md` are four planning documents. Only one has been partially implemented (scanner upgrade plan — none of the P0 items are in code yet). Stop adding planning docs. Write code.

**Stop treating every ROFR/ROFN hit as equally useful.** 7 of 25 batch 71-100 hits were asset-specific ROFN/ROFR patterns (SGEN, TBIO, LBPH, G1T). The batch adjudication report correctly classified these, but the live scanner (P0-C gap) still fires on any ROFN/ROFR phrase with no scope check. Fix this before running more batches.

**Stop running batches without a cohort reason.** Batch 71-100 exists because `configs/case_factory.yaml` sets `start_case_number: 71`. That is not a strategic reason. The next batch should be a signal-enriched cohort with cases pre-selected for high-precision phrase presence, not the next 30 sequential case numbers.

**Stop delaying live monitoring until the historical dataset is "complete."** The live scanner V12 exists and runs today. The historical study's purpose was to prove the concept and calibrate thresholds — not to be a prerequisite for live use. The study showed the system works (3 true signals caught) and the false-positive taxonomy is usable. That is enough to start monitoring live.

---

## 8. What to Build Next — Prioritized

### P0 — This Week

| Task | File | Why |
|---|---|---|
| Negation detection in phrase match | `src/PRODUCTION_SCANNER_V12.py` — `fetch_8k_text_signals()` | DICE pattern confirmed. 4-8 lines. No true positives use negated phrasing. |
| Store source_url + source_accession in scan output | Same function | Live alerts cannot be verified without source links. Required for any analyst workflow. |
| Add rofn_scope_hint field | Same function | 7 of 25 batch 71-100 hits were asset-specific ROFN. Live scanner fires on all of them identically. |
| Raise 8-K scan depth to 8 | Same function — `n_filings=4` → 8 | MDVN filed 8+ 8-Ks. Earliest signal was in the 5th or later filing. |
| Tighten 13D fallback | `has_real_process_evidence()` | Unknown filer + unavailable doc → process gate clears today. Should not. |
| Run scanner + produce top-10 review list | `scripts/` | Proves P0 patches work. Generates first usable live output. |

### P1 — Next 2 Weeks

| Task | File | Why |
|---|---|---|
| Signal-enriched cohort builder | `src/historical_case_tools/signal_enriched_cohort_builder.py` | Pre-select cases with high-precision phrase hits from existing filing targets. Find true positives faster. |
| Alert format schema | `data/live_monitoring/alert_format_schema.json` | Defines what an analyst-ready alert looks like: source URL, excerpt, market cap, priced-in flag. |
| Weekly scan script | `scripts/run_weekly_scan.sh` | Automate the scan → top-10 → log pipeline. |
| Live monitoring log auto-populate | `src/PRODUCTION_SCANNER_V12.py` main() | Record new/changed AFFIRM/PROCESS signals each run with source URL and filing date. |
| SNDX false-positive pattern added to live scanner | Phrase handling in scanner | Partner equity stake divestiture pattern not yet in scanner suppression logic. |

### P2 — Later

| Task | File | Why |
|---|---|---|
| FMP context builder for historical cases | `src/historical_case_tools/fmp_context_builder.py` | Add market cap, price, volume, liquidity fields to exception queue rows. Context-only, no classification change. |
| Dynamic universe filtering by current market cap | `src/PRODUCTION_SCANNER_V12.py` main() | Universe currently static. Names above $1.5B or below $150M still score. |
| False-positive suppression module | `src/false_positive_suppression.py` | Extract shared suppression logic after P0 patterns stabilize in production. |
| Central SEC client | New `src/utils/sec_client.py` | CIK lookup, submissions JSON, archive URL construction duplicated across 4 EDGAR tools. Merge before scaling to 250 cases. |
| SQLite EDGAR cache | Behind central SEC client | Prevent repeated submissions/index/document fetches. Currently no shared cache. |
| Blocked-date resolver for batch 71-100 | Manual + `edgar_source_pull_helper.py` | 10 cases still BLOCKED. Use EDGAR EFTS and manual lookup. Low priority vs. live scanner work. |
| Pytest fixtures for batch alignment | `tests/` | Prevent wrong-batch contamination regressions before scaling past 100 cases. |

---

## 9. Exact Next Implementation Prompt

Run this prompt immediately after this memo is committed.

---

**Prompt:**

```
Repo: /Users/jack/Downloads/ma-scanner

Task:
Build src/historical_case_tools/signal_enriched_cohort_builder.py

Purpose:
Scan existing historical filing data to identify cases with high-precision process
phrases that are NOT explainable by the documented false-positive taxonomy. Rank these
cases for prioritized adjudication in a signal-enriched cohort — separate from the
broad baseline.

This is NOT a new batch pipeline run. It reads existing data only.

Inputs to read:
- data/historical_cases/batch_51_70_pre_announcement_signal_hits.csv (batch 51-70 hits)
- data/historical_cases/batch_71_100_signal_hits.csv (batch 71-100 hits)
- data/historical_cases/acquisition_announcement_dates.csv (dated cases)
- data/historical_cases/batch_71_100_adjudication_results.csv (resolved hits)
- data/historical_cases/batch_51_70_final_summary.md (batch 51-70 false-positive patterns)
- data/historical_cases/batch_71_100_adjudication_report.md (batch 71-100 false-positive patterns)

False-positive patterns to suppress (from 3-batch study):
1. UUEncoded binary artifact — garbled ASCII around phrase match
2. PWERM / stock-comp valuation footnote — co-occurs with: pwerm, probability-weighted, pre-IPO, prior to our IPO
3. Negated phrase context — no plan or proposal, no right of first, not subject to any ROFR
4. Lock-up agreement exhibit — co-occurs with: lock-up, lock_up, lockup, exhibit 99
5. Director biography at prior employer — co-occurs with: Dr., Mr., served as, prior to joining, prior role, led the sale
6. Performance condition equity award — co-occurs with: no expense is recognized, measurement date, performance condition, change in control or a sale
7. Securities offering prospectus disclaimer — co-occurs with: only by means of a written prospectus, Section 10 of the Securities Act, qualification under the securities laws
8. Asset-specific ROFN/ROFR — co-occurs with: LP659, specific compound name, Greater China, Japan/Asia, territory, geographic, license agreement as subject context
9. Anti-takeover provision disclosure — co-occurs with: Section 203, Delaware, vulnerability to, DGCL, anti-takeover
10. Partner equity stake divestiture — co-occurs with: cash settlement on the sale of the Company's common stock, upfront payment returned, make the parties whole
11. Wrong-direction acquisition — company is acquiring, not being acquired; subject is "The Company received an option to acquire"
12. S-8 equity plan boilerplate — co-occurs with: Form S-8, offer or the sale of the Company's securities to such person, Continuous Service
13. ROFR warranty (negative) — "not subject to any agreement granting...right of first refusal"
14. VC/PE investor self-reservation 13D — co-occurs with: IPO, initial public offering, pre-IPO investor, Blackstone, Clarus, reservation of rights

High-precision phrases to prioritize (these are the signal-enriched signal types):
- "unsolicited proposal"
- "superior proposal"
- "competing bid"
- "strategic alternatives" (require affirm context: initiated, exploring, engaged, hired, retained, appointed)
- "retained [bank_name] as its" + "financial advisor" in same 200-char window
- "exploring a potential sale"
- "as its exclusive financial advisor" + "sale of the company" in same 300-char window
- "acquisition proposal" without negation ("no acquisition proposal", "any acquisition proposal" are lower value)
- "right of first negotiation" + company-level context (no named compound, no geographic territory, no specific product in same 100-char window)

Logic:
1. Load all POSSIBLE_HIT rows from both batch signal_hits files.
2. For each hit row, apply false-positive suppression rules above against the excerpt field.
3. Score each hit:
   - HIGH_PRECISION: matches a high-precision phrase, no false-positive pattern found → score 10
   - MEDIUM_PRECISION: matches a moderately specific phrase, ambiguous context → score 5
   - LOW_PRECISION / SUPPRESSED: matches known false-positive pattern → score 0 or -1
4. For each case_id, sum the scores across all hits.
5. Rank cases descending by score. Filter to score > 0.
6. Cross-reference against acquisition_announcement_dates.csv to confirm dated cases.
7. Mark cases that already have adjudication_results rows as ALREADY_ADJUDICATED.

Outputs:
- data/historical_cases/signal_enriched_candidate_queue.csv
  Columns: case_id, ticker, announcement_date, total_score, hit_count, suppressed_hit_count,
  high_precision_hits, medium_precision_hits, best_phrase, best_form, best_filing_date,
  days_before_announcement, false_positive_patterns_detected, adjudication_status,
  recommended_action

- data/historical_cases/signal_enriched_candidate_queue_report.md
  Sections:
  1. Scope and method
  2. Hit score distribution
  3. Ranked candidate table (score > 0)
  4. Already-adjudicated cases (for reference)
  5. Suppressed hits summary (which patterns fired most)
  6. Recommended next adjudication order

Rules:
- Do not change any classifications.
- Do not mark VERIFIED.
- Do not mark CALIBRATION_ELIGIBLE.
- Do not run full live scanner.
- Do not use live FMP API.
- Do not touch dashboard/frontend.
- Do not edit source_evidence.csv.
- Do not edit acquisition_announcement_dates.csv.
- Do not run any batch pipeline steps.
- Read existing data only. Write new output files only.

Validation:
- git diff --check
- git status --short

Commit:
git add data/historical_cases/signal_enriched_candidate_queue.csv
git add data/historical_cases/signal_enriched_candidate_queue_report.md
git add src/historical_case_tools/signal_enriched_cohort_builder.py
git commit -m "Build signal-enriched historical cohort builder"
```

---

## Summary

**Case selection is too random** for product development. Continue the broad baseline to ~120 cases and stop. Build the signal-enriched cohort now.

**The 3.5% hit rate is valuable** because the false-positive taxonomy is the moat, not the signal count. Precision and analyst-time compression are the product.

**The combination is uncommon** if the live scanner P0 gaps are closed and the taxonomy is applied as code. It is not uncommon as a research document.

**Fastest path:** Patch 5 P0 scanner gaps this week. Run scanner. Produce top-10 source-linked review list. Build signal-enriched cohort next week. Write weekly memo week 3. That is a usable analyst workflow in 3 weeks without touching the broad baseline further.

**Do not run Batch 101-130** as a broad sequential batch. Run the signal-enriched cohort builder first and let the score ranking drive which cases go next.
