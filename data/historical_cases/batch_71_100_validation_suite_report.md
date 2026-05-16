# Case Factory Validation Suite Report: batch_71_100

- Timestamp: 2026-05-16T17:20:21
- Batch name: batch_71_100
- Mode: non-strict
- Overall result: FAIL
- Next recommended action: Stop and resolve batch alignment before running package or adjudication steps.

## Summary

| Validator | Result | Scope | Exit code | Warnings | Failures |
|---|---|---|---:|---:|---:|
| alignment | FAIL | batch-specific | 1 | 2 | 1 |
| source_evidence | FAIL | global | 1 | 64 | 9 |

## Commands Run

- `python3 src/historical_case_tools/validate_batch_alignment.py --batch-name batch_71_100`
- `python3 src/historical_case_tools/validate_source_evidence_integrity.py`

## Findings

### alignment

- Result: FAIL
- Exit code: 1
- Scope: batch-specific
- Warnings: 2
- Failures: 1

```text
Batch alignment validation: FAIL
Batch: batch_71_100
Mode: non-strict
Report: data/historical_cases/batch_71_100_alignment_validation_report.md

Files compared: 8
Files missing: None

[PASS] candidate_queue: tickers=26 case_ids=26
[PASS] staging_candidates: tickers=26 case_ids=26
[PASS] date_prefill_queue: tickers=26 case_ids=26
[PASS] exception_queue: tickers=26 case_ids=26
[WARN] source_evidence_draft: tickers=10 case_ids=10
  missing tickers: ALBO, CHMA, CNST, FUSN, G1T, HZNP, KROS, KRTX, LBPH, MORF, MRTX, SGEN, SNDX, STML, TBIO, VSTM
  missing case_ids: RHC-0073-ACQUIRED-FUSN, RHC-0074-ACQUIRED-G1T, RHC-0076-ACQUIRED-KRTX, RHC-0077-ACQUIRED-LBPH, RHC-0078-ACQUIRED-MORF, RHC-0079-ACQUIRED-MRTX, RHC-0101-ACQUIRED-CHMA, RHC-0102-ACQUIRED-CNST, RHC-0103-ACQUIRED-STML, RHC-0104-ACQUIRED-ALBO, RHC-0105-ACQUIRED-HZNP, RHC-0106-ACQUIRED-SGEN, RHC-0107-ACQUIRED-SNDX, RHC-0132-ACQUIRED-TBIO, RHC-0138-ACQUIRED-KROS, RHC-0140-ACQUIRED-VSTM
[FAIL] pre_announcement_filing_targets: tickers=16 case_ids=16
  missing tickers: ENLV, FATE, GRCL, HRMY, KPTI, LMNX, MOR, SYNH, TGTX, VECT
  missing case_ids: RHC-0072-ACQUIRED-FATE, RHC-0075-ACQUIRED-GRCL, RHC-0108-ACQUIRED-VECT, RHC-0109-ACQUIRED-MOR, RHC-0131-ACQUIRED-LMNX, RHC-0134-ACQUIRED-ENLV, RHC-0135-ACQUIRED-HRMY, RHC-0136-ACQUIRED-SYNH, RHC-0137-ACQUIRED-KPTI, RHC-0139-ACQUIRED-TGTX
  duplicated tickers: ALBO, CHMA, CNST, FUSN, G1T, HZNP, KROS, KRTX, LBPH, MORF, MRTX, SGEN, SNDX, STML, TBIO, VSTM
  duplicated case_ids: RHC-0073-ACQUIRED-FUSN, RHC-0074-ACQUIRED-G1T, RHC-0076-ACQUIRED-KRTX, RHC-0077-ACQUIRED-LBPH, RHC-0078-ACQUIRED-MORF, RHC-0079-ACQUIRED-MRTX, RHC-0101-ACQUIRED-CHMA, RHC-0102-ACQUIRED-CNST, RHC-0103-ACQUIRED-STML, RHC-0104-ACQUIRED-ALBO, RHC-0105-ACQUIRED-HZNP, RHC-0106-ACQUIRED-SGEN, RHC-0107-ACQUIRED-SNDX, RHC-0132-ACQUIRED-TBIO, RHC-0138-ACQUIRED-KROS, RHC-0140-ACQUIRED-VSTM
[PASS] filing_targets: tickers=26 case_ids=26
[WARN] run_manifest: tickers=0 case_ids=0
```

### source_evidence

- Result: FAIL
- Exit code: 1
- Scope: global
- Warnings: 64
- Failures: 9

```text
Source evidence integrity: FAIL
Warnings: 64
Failures: 9
Report: data/historical_cases/source_evidence_integrity_report.md

[FAIL] announcement_evidence_missing_date source_evidence.csv:22 IMGO-2022-001 IMGO - announcement/event/filing date required
[FAIL] announcement_evidence_missing_date source_evidence.csv:26 RHC-0038-ACQUIRED-FLXN FLXN - announcement/event/filing date required
[FAIL] announcement_evidence_missing_date source_evidence.csv:4 HARP-2023-001 HARP - announcement/event/filing date required
[FAIL] announcement_evidence_missing_date source_evidence.csv:6 SRRA-2022-001 SRRA - announcement/event/filing date required
[FAIL] duplicate_exact_source_evidence source_evidence.csv:34 RHC-0001-ACQUIRED-NPSP NPSP - Rows 34, 43 share case_id/ticker/source_url/date/evidence_type
[FAIL] duplicate_exact_source_evidence source_evidence.csv:36 RHC-0002-ACQUIRED-PCYC PCYC - Rows 36, 44 share case_id/ticker/source_url/date/evidence_type
[FAIL] duplicate_exact_source_evidence source_evidence.csv:38 RHC-0003-ACQUIRED-ZSPH ZSPH - Rows 38, 45 share case_id/ticker/source_url/date/evidence_type
[FAIL] duplicate_exact_source_evidence source_evidence.csv:40 RHC-0004-ACQUIRED-ANAC ANAC - Rows 40, 46 share case_id/ticker/source_url/date/evidence_type
[FAIL] duplicate_exact_source_evidence source_evidence.csv:42 RHC-0006-ACQUIRED-MDVN MDVN - Rows 42, 47 share case_id/ticker/source_url/date/evidence_type
[WARN] announcement_evidence_missing_source_url source_evidence.csv:22 IMGO-2022-001 IMGO - source_url missing or placeholder
[WARN] announcement_evidence_missing_source_url source_evidence.csv:26 RHC-0038-ACQUIRED-FLXN FLXN - source_url missing or placeholder
[WARN] announcement_evidence_missing_source_url source_evidence.csv:4 HARP-2023-001 HARP - source_url missing or placeholder
[WARN] announcement_evidence_missing_source_url source_evidence.csv:6 SRRA-2022-001 SRRA - source_url missing or placeholder
[WARN] medium_confidence_acquisition_date acquisition_announcement_dates.csv:2 RHC-0005-ACQUIRED-CPXX CPXX - MEDIUM confidence row
[WARN] medium_confidence_acquisition_date acquisition_announcement_dates.csv:66 RHC-0073-ACQUIRED-FUSN FUSN - MEDIUM confidence row
[WARN] medium_confidence_acquisition_date acquisition_announcement_dates.csv:68 RHC-0105-ACQUIRED-HZNP HZNP - MEDIUM confidence row
[WARN] medium_confidence_acquisition_date acquisition_announcement_dates.csv:69 RHC-0138-ACQUIRED-KROS KROS - MEDIUM confidence row
[WARN] medium_confidence_acquisition_date acquisition_announcement_dates.csv:70 RHC-0076-ACQUIRED-KRTX KRTX - MEDIUM confidence row
[WARN] medium_confidence_acquisition_date acquisition_announcement_dates.csv:72 RHC-0078-ACQUIRED-MORF MORF - MEDIUM confidence row
[WARN] medium_confidence_acquisition_date acquisition_announcement_dates.csv:75 RHC-0107-ACQUIRED-SNDX SNDX - MEDIUM confidence row
[WARN] medium_confidence_acquisition_date acquisition_announcement_dates.csv:76 RHC-0103-ACQUIRED-STML STML - MEDIUM confidence row
[WARN] medium_confidence_acquisition_date acquisition_announcement_dates.csv:78 RHC-0140-ACQUIRED-VSTM VSTM - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:110 RHC-0073-ACQUIRED-FUSN FUSN - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:112 RHC-0105-ACQUIRED-HZNP HZNP - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:113 RHC-0138-ACQUIRED-KROS KROS - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:114 RHC-0076-ACQUIRED-KRTX KRTX - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:116 RHC-0078-ACQUIRED-MORF MORF - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:119 RHC-0107-ACQUIRED-SNDX SNDX - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:120 RHC-0103-ACQUIRED-STML STML - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:122 RHC-0140-ACQUIRED-VSTM VSTM - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:18 PTGX-2022-001 PTGX - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:43 RHC-0001-ACQUIRED-NPSP NPSP - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:44 RHC-0002-ACQUIRED-PCYC PCYC - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:45 RHC-0003-ACQUIRED-ZSPH ZSPH - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:46 RHC-0004-ACQUIRED-ANAC ANAC - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:47 RHC-0006-ACQUIRED-MDVN MDVN - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:49 RHC-0008-ACQUIRED-TBRA TBRA - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:51 RHC-0010-ACQUIRED-ARIA ARIA - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:53 RHC-0013-ACQUIRED-KITE KITE - MEDIUM confidence row
[WARN] medium_confidence_source_evidence source_evidence.csv:55 RHC-0015-ACQUIRED-BIVV BIVV - MEDIUM confidence row
... 33 more issues in report
```

## Scope Notes

- Alignment failures are batch-specific.
- Source evidence integrity failures are global unless the source validator is run with filters.
- This suite does not run the scanner, run package commands, adjudicate cases, or edit source CSVs.