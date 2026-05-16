# Source Evidence Integrity Report

- Mode: non-strict
- Case prefix filter: none
- Ticker filter: none
- Overall status: FAIL
- Warnings: 64
- Failures: 9

## Inputs

| File | Rows | Columns | Parse status |
|---|---:|---:|---|
| `data/historical_cases/source_evidence.csv` | 121 | 17 | OK |
| `data/historical_cases/acquisition_announcement_dates.csv` | 77 | 9 | OK |
| `data/historical_cases/resolved_case_candidates.csv` | 203 | 15 | OK |

## Issue Summary

| Severity | Check | Count |
|---|---|---:|
| FAIL | announcement_evidence_missing_date | 4 |
| FAIL | duplicate_exact_source_evidence | 5 |
| WARN | announcement_evidence_missing_source_url | 4 |
| WARN | medium_confidence_acquisition_date | 9 |
| WARN | medium_confidence_source_evidence | 39 |
| WARN | missing_or_placeholder_source_url | 12 |

## Issues

| Severity | Check | File | Row | Case ID | Ticker | Detail |
|---|---|---|---:|---|---|---|
| FAIL | announcement_evidence_missing_date | `source_evidence.csv` | 22 | IMGO-2022-001 | IMGO | announcement/event/filing date required |
| FAIL | announcement_evidence_missing_date | `source_evidence.csv` | 26 | RHC-0038-ACQUIRED-FLXN | FLXN | announcement/event/filing date required |
| FAIL | announcement_evidence_missing_date | `source_evidence.csv` | 4 | HARP-2023-001 | HARP | announcement/event/filing date required |
| FAIL | announcement_evidence_missing_date | `source_evidence.csv` | 6 | SRRA-2022-001 | SRRA | announcement/event/filing date required |
| FAIL | duplicate_exact_source_evidence | `source_evidence.csv` | 34 | RHC-0001-ACQUIRED-NPSP | NPSP | Rows 34, 43 share case_id/ticker/source_url/date/evidence_type |
| FAIL | duplicate_exact_source_evidence | `source_evidence.csv` | 36 | RHC-0002-ACQUIRED-PCYC | PCYC | Rows 36, 44 share case_id/ticker/source_url/date/evidence_type |
| FAIL | duplicate_exact_source_evidence | `source_evidence.csv` | 38 | RHC-0003-ACQUIRED-ZSPH | ZSPH | Rows 38, 45 share case_id/ticker/source_url/date/evidence_type |
| FAIL | duplicate_exact_source_evidence | `source_evidence.csv` | 40 | RHC-0004-ACQUIRED-ANAC | ANAC | Rows 40, 46 share case_id/ticker/source_url/date/evidence_type |
| FAIL | duplicate_exact_source_evidence | `source_evidence.csv` | 42 | RHC-0006-ACQUIRED-MDVN | MDVN | Rows 42, 47 share case_id/ticker/source_url/date/evidence_type |
| WARN | announcement_evidence_missing_source_url | `source_evidence.csv` | 22 | IMGO-2022-001 | IMGO | source_url missing or placeholder |
| WARN | announcement_evidence_missing_source_url | `source_evidence.csv` | 26 | RHC-0038-ACQUIRED-FLXN | FLXN | source_url missing or placeholder |
| WARN | announcement_evidence_missing_source_url | `source_evidence.csv` | 4 | HARP-2023-001 | HARP | source_url missing or placeholder |
| WARN | announcement_evidence_missing_source_url | `source_evidence.csv` | 6 | SRRA-2022-001 | SRRA | source_url missing or placeholder |
| WARN | medium_confidence_acquisition_date | `acquisition_announcement_dates.csv` | 2 | RHC-0005-ACQUIRED-CPXX | CPXX | MEDIUM confidence row |
| WARN | medium_confidence_acquisition_date | `acquisition_announcement_dates.csv` | 66 | RHC-0073-ACQUIRED-FUSN | FUSN | MEDIUM confidence row |
| WARN | medium_confidence_acquisition_date | `acquisition_announcement_dates.csv` | 68 | RHC-0105-ACQUIRED-HZNP | HZNP | MEDIUM confidence row |
| WARN | medium_confidence_acquisition_date | `acquisition_announcement_dates.csv` | 69 | RHC-0138-ACQUIRED-KROS | KROS | MEDIUM confidence row |
| WARN | medium_confidence_acquisition_date | `acquisition_announcement_dates.csv` | 70 | RHC-0076-ACQUIRED-KRTX | KRTX | MEDIUM confidence row |
| WARN | medium_confidence_acquisition_date | `acquisition_announcement_dates.csv` | 72 | RHC-0078-ACQUIRED-MORF | MORF | MEDIUM confidence row |
| WARN | medium_confidence_acquisition_date | `acquisition_announcement_dates.csv` | 75 | RHC-0107-ACQUIRED-SNDX | SNDX | MEDIUM confidence row |
| WARN | medium_confidence_acquisition_date | `acquisition_announcement_dates.csv` | 76 | RHC-0103-ACQUIRED-STML | STML | MEDIUM confidence row |
| WARN | medium_confidence_acquisition_date | `acquisition_announcement_dates.csv` | 78 | RHC-0140-ACQUIRED-VSTM | VSTM | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 110 | RHC-0073-ACQUIRED-FUSN | FUSN | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 112 | RHC-0105-ACQUIRED-HZNP | HZNP | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 113 | RHC-0138-ACQUIRED-KROS | KROS | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 114 | RHC-0076-ACQUIRED-KRTX | KRTX | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 116 | RHC-0078-ACQUIRED-MORF | MORF | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 119 | RHC-0107-ACQUIRED-SNDX | SNDX | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 120 | RHC-0103-ACQUIRED-STML | STML | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 122 | RHC-0140-ACQUIRED-VSTM | VSTM | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 18 | PTGX-2022-001 | PTGX | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 43 | RHC-0001-ACQUIRED-NPSP | NPSP | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 44 | RHC-0002-ACQUIRED-PCYC | PCYC | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 45 | RHC-0003-ACQUIRED-ZSPH | ZSPH | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 46 | RHC-0004-ACQUIRED-ANAC | ANAC | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 47 | RHC-0006-ACQUIRED-MDVN | MDVN | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 49 | RHC-0008-ACQUIRED-TBRA | TBRA | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 51 | RHC-0010-ACQUIRED-ARIA | ARIA | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 53 | RHC-0013-ACQUIRED-KITE | KITE | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 55 | RHC-0015-ACQUIRED-BIVV | BIVV | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 57 | RHC-0017-ACQUIRED-JUNO | JUNO | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 59 | RHC-0025-ACQUIRED-TSRO | TSRO | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 60 | RHC-0025-ACQUIRED-TSRO | TSRO | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 61 | RHC-0026-ACQUIRED-ACHN | ACHN | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 62 | RHC-0027-ACQUIRED-BOLD | BOLD | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 63 | RHC-0028-ACQUIRED-DERM | DERM | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 64 | RHC-0030-ACQUIRED-MNTA | MNTA | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 65 | RHC-0032-ACQUIRED-PGNX | PGNX | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 66 | RHC-0034-ACQUIRED-PRVL | PRVL | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 67 | RHC-0036-ACQUIRED-DOVA | DOVA | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 68 | RHC-0037-ACQUIRED-DRNA | DRNA | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 69 | RHC-0038-ACQUIRED-FLXN | FLXN | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 70 | RHC-0039-ACQUIRED-FPRX | FPRX | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 71 | RHC-0040-ACQUIRED-GWPH | GWPH | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 72 | RHC-0041-ACQUIRED-PAND | PAND | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 73 | RHC-0044-ACQUIRED-VIE | VIE | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 74 | RHC-0046-ACQUIRED-ATRS | ATRS | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 75 | RHC-0047-ACQUIRED-AVEO | AVEO | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 76 | RHC-0048-ACQUIRED-BHVN | BHVN | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 77 | RHC-0049-ACQUIRED-CCXI | CCXI | MEDIUM confidence row |
| WARN | medium_confidence_source_evidence | `source_evidence.csv` | 78 | RHC-0050-ACQUIRED-CMPI | CMPI | MEDIUM confidence row |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 12 | CRBP-2022-001 | CRBP | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 13 | CRBP-2022-001 | CRBP | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 19 | PTGX-2022-001 | PTGX | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 2 | HARP-2023-001 | HARP | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 22 | IMGO-2022-001 | IMGO | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 24 | RIGL-2020-001 | RIGL | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 26 | RHC-0038-ACQUIRED-FLXN | FLXN | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 29 | RHC-0036-ACQUIRED-DOVA | DOVA | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 3 | HARP-2023-001 | HARP | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 32 | RIGL-2020-001 | RIGL | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 4 | HARP-2023-001 | HARP | source_url=VERIFY_REQUIRED |
| WARN | missing_or_placeholder_source_url | `source_evidence.csv` | 6 | SRRA-2022-001 | SRRA | source_url=VERIFY_REQUIRED |

## Rules

- Malformed dates, conflicting HIGH-confidence dates, duplicate exact evidence rows, and missing required columns are failures.
- MEDIUM confidence rows, missing source URLs, duplicate tickers with different dates, and implausible year differences are warnings in non-strict mode.
- The validator is read-only except for this report.