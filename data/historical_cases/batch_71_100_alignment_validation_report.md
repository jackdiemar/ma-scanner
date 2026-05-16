# Batch Alignment Validation Report: batch_71_100

- Mode: non-strict
- Overall status: PASS
- Canonical source: `batch_71_100_candidate_queue.csv`

## Files Found

- `data/historical_cases/batch_71_100_candidate_queue.csv`
- `data/historical_cases/batch_71_100_staging_candidates.csv`
- `data/historical_cases/batch_71_100_date_prefill_queue.csv`
- `data/historical_cases/batch_71_100_exception_queue.csv`
- `data/historical_cases/batch_71_100_source_evidence_draft.csv`
- `data/historical_cases/batch_71_100_pre_announcement_filing_targets.csv`
- `data/historical_cases/batch_71_100_filing_targets.csv`
- `data/historical_cases/batch_71_100_run_manifest.json`

## Files Missing

- None

## Counts By File

| File | Rows | Ticker field | Unique ticker count | Case ID field | Unique case ID count | Repeated tickers | Repeated case_ids |
|---|---:|---|---:|---|---:|---|---|
| candidate_queue | 26 | ticker | 26 | candidate_id | 26 | None | None |
| staging_candidates | 26 | ticker | 26 | candidate_id | 26 | None | None |
| date_prefill_queue | 26 | ticker | 26 | case_id | 26 | None | None |
| exception_queue | 26 | ticker | 26 | case_id | 26 | None | None |
| source_evidence_draft | 10 | ticker | 10 | case_id | 10 | None | None |
| pre_announcement_filing_targets | 427 | ticker | 16 | case_id | 16 | expected multi-row file | expected multi-row file |
| filing_targets | 26 | ticker | 26 | case_id | 26 | None | None |
| run_manifest | 0 | recursive_json | 0 | recursive_json | 0 | None | None |

## Alignment Results

| File | Expected set | Status | Extra tickers | Missing tickers | Extra case_ids | Missing case_ids | Wrong old-index tickers | Notes |
|---|---|---|---|---|---|---|---|---|
| candidate_queue | candidate_queue | PASS | None | None | None | None | None | None |
| staging_candidates | candidate_queue | PASS | None | None | None | None | None | None |
| date_prefill_queue | candidate_queue | PASS | None | None | None | None | None | None |
| exception_queue | candidate_queue | PASS | None | None | None | None | None | None |
| source_evidence_draft | candidate_queue | WARN | None | ALBO, CHMA, CNST, FUSN, G1T, HZNP, KROS, KRTX, LBPH, MORF, MRTX, SGEN, SNDX, STML, TBIO, VSTM | None | RHC-0073-ACQUIRED-FUSN, RHC-0074-ACQUIRED-G1T, RHC-0076-ACQUIRED-KRTX, RHC-0077-ACQUIRED-LBPH, RHC-0078-ACQUIRED-MORF, RHC-0079-ACQUIRED-MRTX, RHC-0101-ACQUIRED-CHMA, RHC-0102-ACQUIRED-CNST, RHC-0103-ACQUIRED-STML, RHC-0104-ACQUIRED-ALBO, RHC-0105-ACQUIRED-HZNP, RHC-0106-ACQUIRED-SGEN, RHC-0107-ACQUIRED-SNDX, RHC-0132-ACQUIRED-TBIO, RHC-0138-ACQUIRED-KROS, RHC-0140-ACQUIRED-VSTM | None | missing_tickers, missing_case_ids |
| pre_announcement_filing_targets | eligible_dated_cases_from_exception_queue | PASS | None | None | None | None | None | None |
| filing_targets | candidate_queue | PASS | None | None | None | None | None | None |
| run_manifest | candidate_queue | WARN | None | None | None | None | None | no_ticker_or_case_id_values |

## Interpretation

- Full-batch files must contain every candidate queue ticker and case_id.
- Multi-row filing target files are compared against eligible dated cases, not the full candidate queue.
- Eligible dated cases come from the exception queue when available, excluding BLOCKED / DATE_OR_CIK_BLOCKED rows.
- Repeated tickers and case_ids are expected in multi-row filing target files.
- Partial downstream files may omit canonical candidates, but may not introduce extras.
- Any extra ticker outside the expected set, outside-candidate ticker, duplicate in one-row-per-case files, read error, or wrong old-index detection is a failure.
- In strict mode, missing expected downstream files are failures.
