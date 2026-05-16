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
| Dates confirmed | 0 / 30 |
| Dates missing | 26 |
| Date gate | PARTIAL |

---

## 2. Step Results

| Step | Status | Notes |
|---|---|---|
| validate_candidate_queue | PASS | candidates=26 |
| date_prefill | PASS | output=batch_71_100_date_prefill_queue.csv; rows=26 |
| date_gate | PARTIAL | dates_found=0; dates_missing=26; note=allow_date_backfill — continuing; BLOCKED tiers expected in exception queue |
| exception_queue | PASS | output=batch_71_100_exception_queue.csv; rows=26; tiers={'BLOCKED': 26} |
| filing_collection | SKIPPED | reason=No candidates with confirmed dates |
| source_evidence | PASS | output=batch_71_100_source_evidence_draft.csv; rows=26 |
| review_packet | PASS | output=batch_71_100_review_packet.md |
| proposed_baselines | SKIPPED | reason=allow_clean_baseline_autofinalize=False |

---

## 3. Files Written

- `batch_71_100_date_prefill_queue.csv`
- `batch_71_100_date_prefill_report.md`
- `batch_71_100_staging_candidates.csv`
- `batch_71_100_exception_queue.csv`
- `batch_71_100_exception_queue_report.md`
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
