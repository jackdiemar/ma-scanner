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

---

## 3. Files Written

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

---

## 4. Safety Constraints

- No cases adjudicated.
- No VERIFIED flag set.
- No CALIBRATION_ELIGIBLE flag set.
- No live API calls made.
- No live scanner run.
- No first-70 classifications changed.
- `source_evidence.csv` not written by this pipeline.
