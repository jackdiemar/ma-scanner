# Case Factory Schema Validation Report

Generated: 2026-05-16

## Scope

Dependency-free schema validation pass using `src/historical_case_tools/case_factory_schema.py`.

This report is read-only with respect to the source data files. It does not edit
Batch 71-100 adjudication/package outputs, `source_evidence.csv`,
`acquisition_announcement_dates.csv`, classifications, VERIFIED status, or
CALIBRATION_ELIGIBLE status.

## Files Checked

| File | Row type | Rows | Status | Warnings | Failures |
|---|---|---:|---|---:|---:|
| `data/historical_cases/acquisition_announcement_dates.csv` | date_prefill | 77 | PASS | 0 | 0 |
| `data/historical_cases/source_evidence.csv` | source_evidence | 121 | WARN | 30 | 0 |
| `data/historical_cases/batch_71_100_candidate_queue.csv` | candidate | 26 | PASS | 0 | 0 |
| `data/historical_cases/batch_71_100_exception_queue.csv` | exception_queue | 26 | PASS | 0 | 0 |
| `data/historical_cases/batch_71_100_pre_announcement_filing_targets.csv` | filing_target | 427 | PASS | 0 | 0 |
| `data/historical_cases/batch_71_100_signal_hits.csv` | signal_hit | 25 | PASS | 0 | 0 |

## Summary

| Metric | Count |
|---|---:|
| Files checked | 6 |
| Rows checked | 702 |
| Warnings | 30 |
| Failures | 0 |

Overall result: **WARN** because `source_evidence.csv` contains existing
placeholder source URLs. No schema failures were found in the checked files.

## Common Schema Issues

| Issue | Count | Files | Interpretation |
|---|---:|---|---|
| `missing_or_placeholder_source_url` | 30 | `source_evidence.csv` | Existing research-target or placeholder evidence rows use `VERIFY_REQUIRED` or blank source URLs. This is a warning unless a row claims VERIFIED evidence without a usable source URL. |

## Batch-Specific Notes

Batch 71-100 schema checks passed for:

- candidate queue
- exception queue
- pre-announcement filing targets
- signal hits

The Batch 71-100 files checked here have no malformed dates, missing required
case/ticker identifiers, or missing required filing-target/signal-hit fields
under the new lightweight contracts.

## Pre-Existing / Global Notes

The 30 warnings are global `source_evidence.csv` warnings, not active
Batch 71-100 adjudication changes. They are consistent with older
`VERIFY_REQUIRED` research-target rows and placeholder source evidence that
predates this schema layer.

Representative affected rows include:

- HARP research targets
- CRBP research targets
- PTGX research target
- older first-50 and seed evidence placeholders

These warnings should not block the Batch 71-100 adjudication pass. They do
identify candidates for later evidence cleanup or promotion from placeholder
rows into verified source-backed rows.

## Validation Rules Applied

- Tickers normalize to uppercase.
- ISO dates must parse as `YYYY-MM-DD` when present.
- Required case/ticker/status/source fields are checked by row type.
- Missing source URLs in source evidence are warnings by default.
- VERIFIED source evidence without a usable source URL is a failure.
- Filing targets and signal hits are allowed to have many rows per case.
- Source evidence is allowed to have many rows per case.

## Result

Schema validation layer is safe to use as internal infrastructure. It adds
contract checks without changing taxonomy, adjudication, scoring, evidence
classification, or scanner behavior.
