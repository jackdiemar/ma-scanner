# Batch 71 100 Package Report

Generated: 2026-05-16

---

## 1. Scope

| Field | Value |
|---|---|
| Batch | batch_71_100 |
| Cases | 71–100 (30 target) |
| Run date | 2026-05-16 |
| Dry run | False |
| Dates confirmed | 16 / 30 |
| Dates missing | 10 |
| Date gate | PARTIAL |
| filing_collection_ran | true |
| enable_edgar_fetch | true |
| dated_cases_processed | 16 |
| filing_target_rows | 427 |
| possible_signal_hits | 25 |
| review_required_cases | 11 |
| clean_likely_no_hit_cases | 5 |
| blocked_missing_date_cases | 10 |
| next_recommended_step | resolve 10 blocked cases (date lookup) then proceed to batch_101_130 |
| adjudication_status | COMPLETE (16 dated cases) |
| true_prior_signals_this_batch | 0 |
| cumulative_signal_rate | 3/86 (3.5%) |

---

## 2. Step Results

| Step | Status | Notes |
|---|---|---|
| validate_candidate_queue | PASS | candidates=26 |
| date_prefill | PASS | output=batch_71_100_date_prefill_queue.csv; rows=26 |
| date_gate_initial | PARTIAL | dates_found=16; dates_missing=10; note=will attempt automated EDGAR backfill |
| date_backfill | PASS | attempted=10; found=0; not_found=10; new_dates_written=0 |
| date_gate_final | PARTIAL | dates_found=16; dates_missing=10 |
| exception_queue | PASS | output=batch_71_100_exception_queue.csv; rows=26; tiers={'BLOCKED': 10, 'PENDING_FILING_COLLECTION': 16} |
| filing_collection | PASS | mode=EDGAR API; staging=batch_71_100_confirmation_results_staging.csv; targets=batch_71_100_pre_announcement_filing_targets.csv; hits=batch_71_100_signal_hits.csv |
| source_evidence | PASS | output=batch_71_100_source_evidence_draft.csv; rows=10 |
| review_packet | PASS | output=batch_71_100_review_packet.md |
| proposed_baselines | SKIPPED | reason=allow_clean_baseline_autofinalize=False |
| adjudication_queue | PASS | output=batch_71_100_adjudication_queue.md; ranked_cases=11 |

---

## 3. Filing Collection Results

| Metric | Value |
|---|---|
| Cases checked | 16 |
| Cases blocked (no date) | 10 |
| Filing target rows | 427 |
| Possible signal hit rows | 25 |
| Cases with possible hits | 11 |
| Likely no-hit cases | 5 |

### 11 Cases Flagged for Manual Review

| Ticker | Hit count | Signal types | Priority |
|---|---|---|---|
| SGEN | 2 | rofr_rofn | P1 |
| TBIO | 1 | option_to_acquire | P1 |
| VSTM | 2 | rofr_rofn, sale_process | P2 |
| LBPH | 2 | sale_process, rofr_rofn | P2 |
| G1T | 4 | rofr_rofn, sale_process | P2 |
| HZNP | 3 | sale_process, option_to_acquire | P3 |
| SNDX | 2 | sale_process | P3 |
| STML | 5 | sale_process | P4 |
| MRTX | 1 | sale_process | P4 |
| ALBO | 1 | acquisition_proposal | P4 |
| CHMA | 2 | retained_advisor | P4 |

### 5 Likely Clean No-Hit Cases

| Ticker | Proposed classification |
|---|---|
| CNST | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| FUSN | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| KROS | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| KRTX | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| MORF | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |

### 10 Blocked Missing-Date Cases

ENLV, FATE, GRCL, HRMY, KPTI, LMNX, MOR, SYNH, TGTX, VECT

Resolve using EDGAR URLs in batch_71_100_date_prefill_queue.csv.

---

## 4. Validator Results

### Batch Alignment Validator

```
validate_batch_alignment.py --batch-name batch_71_100 → FAIL (expected)

[PASS] candidate_queue:    26 rows, tickers match
[PASS] staging_candidates: 26 rows, tickers match
[PASS] date_prefill_queue: 26 rows, tickers match
[PASS] exception_queue:    26 rows, tickers match
[WARN] source_evidence_draft: 10 rows — 16 dated cases skipped (filing collector ran; no draft rows needed)
[FAIL] pre_announcement_filing_targets: 16 rows (10 blocked tickers absent by design)
[PASS] filing_targets:     26 rows (no-api pass still covers all 26)
[WARN] run_manifest:       0 ticker rows (manifest is not a CSV)
```

FAIL on pre_announcement_filing_targets is expected and correct. The real-EDGAR targets file covers only the 16 dated cases. Blocked cases are absent by design — they were excluded from EDGAR fetch staging.

### Source Evidence Integrity Validator

```
validate_source_evidence_integrity.py → FAIL
Failures: 9 (all pre-existing, not caused by batch_71_100)
  - 4x announcement_evidence_missing_date: IMGO, FLXN, HARP, SRRA (batch 51-70 era)
  - 5x duplicate_exact_source_evidence: NPSP, PCYC, ZSPH, ANAC, MDVN (first-50 era)
Warnings: 64 (medium-confidence rows, including 8 new batch_71_100 MEDIUM rows)
```

No failures caused by batch_71_100. New batch_71_100 rows generate WARN (MEDIUM confidence) only, not FAIL.

---

## 4b. Adjudication Results

| Metric | Value |
|---|---|
| Adjudication date | 2026-05-16 |
| Cases adjudicated | 16 (11 review + 5 spot-check) |
| Cases blocked (no date) | 10 |
| TRUE_PUBLIC_PRIOR_SIGNAL | 0 |
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 16 |
| Total false-positive hits | 25 |

### False-Positive Pattern Breakdown

| Pattern | Hits |
|---|---|
| Securities offering prospectus disclaimer | 5 |
| Asset-specific ROFN/ROFR | 7 |
| Director biography | 3 |
| Performance condition equity award boilerplate | 3 |
| Partner equity stake divestiture | 2 |
| Wrong-direction acquisition | 2 |
| Anti-takeover provision disclosure | 1 |
| ROFR warranty (negative statement) | 1 |
| UUEncoded binary artifact | 1 |

### Adjudication Files

- `batch_71_100_adjudication_results.csv`
- `batch_71_100_adjudication_working_summary.md`
- `batch_71_100_adjudication_report.md`

---

## 5. Files Written

- `batch_71_100_date_prefill_queue.csv`
- `batch_71_100_date_prefill_report.md`
- `batch_71_100_staging_candidates.csv`
- `batch_71_100_date_backfill_report.md`
- `batch_71_100_exception_queue.csv`
- `batch_71_100_exception_queue_report.md`
- `batch_71_100_confirmation_results_staging.csv`
- `batch_71_100_pre_announcement_filing_targets.csv`
- `batch_71_100_signal_hits.csv`
- `batch_71_100_filing_report.md`
- `batch_71_100_confirmation_results_report.md`
- `batch_71_100_source_evidence_draft.csv`
- `batch_71_100_source_evidence_draft_report.md`
- `batch_71_100_review_packet.md`
- `batch_71_100_adjudication_queue.md`
- `batch_71_100_package_report.md`
- `batch_71_100_adjudication_results.csv`
- `batch_71_100_adjudication_working_summary.md`
- `batch_71_100_adjudication_report.md`

---

## 6. Safety Constraints

- No cases adjudicated.
- No VERIFIED flag set.
- No CALIBRATION_ELIGIBLE flag set.
- No live FMP API calls made.
- No live scanner run.
- No first-70 classifications changed.
- `source_evidence.csv` not written by this pipeline (automated date backfill evidence rows added with AUTOMATED_EDGAR_MATCH status only).
