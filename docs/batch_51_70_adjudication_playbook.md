# Batch 51-70 Adjudication Playbook

Generated: 2026-05-15

Status: manual review playbook. No classifications changed.

## Current State

- First 50-case study is complete.
- Batch 51-70 announcement dates are backfilled and HIGH confidence.
- Commit `a9ef49a` moved all 20 Batch 51-70 cases from `BLOCKED` to `PENDING_FILING_COLLECTION`.
- Claude is collecting pre-announcement filings and rebuilding the exception queue.

Use this once `batch_51_70_exception_queue_report.md` is ready.

## Review Order

1. `P1`: explicit acquisition-process phrases.
2. `P2`: strategic alternatives plus banker/advisor context.
3. `P3`: SC 13D Item 4 acquisition pressure.
4. `P4`: rights language requiring company-vs-asset scope check.
5. `BLOCKED`: source, date, or coverage failures.
6. `P5` / `P6`: private-background or clean baseline spot checks.

## Decision Tree

1. Was the source public before announcement?
   - If no, not `TRUE_PUBLIC_PRIOR_SIGNAL`.
2. Is the evidence company-level?
   - If no, classify as `ASSET_SPECIFIC_RIGHTS_ONLY`.
3. Is it generic legal rights language?
   - If yes, classify as `RIGHTS_LANGUAGE_ONLY`.
4. Is the process described only in later SC 14D-9 or proxy background?
   - If yes, classify as `PRIVATE_BACKGROUND_ONLY`.
5. Is there explicit pre-announcement proposal or process language?
   - If yes, possible `TRUE_PUBLIC_PRIOR_SIGNAL`, but require source URL, filing date, excerpt, and days-before calculation.
6. Is there no public process evidence?
   - Classify as `DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE`.

If evidence is unclear, leave the case as `POSSIBLE_SIGNAL_NEEDS_REVIEW`. Do not force it.

## Evidence Requirements

Every non-baseline or upgraded case needs:

- `case_id`
- `ticker`
- `announcement_date`
- `source_url`
- `filing_type`
- `filing_date`
- `accession_number` if available
- `excerpt`
- `days_before_announcement`
- `classification`
- `reason`
- `false_positive_check`

## Phrases That Matter

High value:

- `unsolicited proposal`
- `superior proposal`
- `acquisition proposal`
- `proposal to acquire`
- `competing proposal`
- `strategic alternatives` with banker/advisor context

Lower value or risky:

- `right of first refusal`
- `right of first negotiation`
- `option`
- `co-funding`
- `collaboration`
- `equity investment`
- `confidentiality agreement`

## False-Positive Rules From The First 50

- Generic ROFR is not process evidence.
- Asset-specific rights are not company-level process evidence.
- Post-announcement SC 14D-9 background is not prior public signal.
- Equity investments without acquisition options are not signals.
- Private unsolicited offers do not count unless publicly disclosed before announcement.

## Fast Workflow Once Claude Finishes

1. Open `data/historical_cases/batch_51_70_exception_queue_report.md`.
2. Count `P1`, `P2`, `P3`, `P4`, and `BLOCKED` cases.
3. Review `P1`, `P2`, and `P3` manually first.
4. Use `edgar_source_pull_helper.py` for source snippets.
5. Append `source_evidence.csv` rows only after source-backed review.
6. Leave unclear cases as `POSSIBLE_SIGNAL_NEEDS_REVIEW`.
7. Run the batch runner only after decisions are made.

## EDGAR Helper Example

```bash
python3 src/historical_case_tools/edgar_source_pull_helper.py \
  --url "SEC_ARCHIVE_URL" \
  --case-id "RHC-XXXX" \
  --ticker "TICKER" \
  --filing-type "8-K" \
  --find "unsolicited proposal" \
  --find "superior proposal" \
  --find "acquisition proposal"
```

## What Not To Do

- Do not mark `VERIFIED`.
- Do not mark `CALIBRATION_ELIGIBLE`.
- Do not claim alpha.
- Do not scale to 100.
- Do not treat scores as evidence.
- Do not let post-announcement background become prior signal.
- Do not force ambiguous cases.
