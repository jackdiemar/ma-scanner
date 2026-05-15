# Batch 51–70 Source Evidence Draft

Generated: 2026-05-14

Draft file only. Do NOT copy these rows to source_evidence.csv without verification.
All PLACEHOLDER fields must be filled from the actual filing before promoting.

## Summary

- Draft rows generated: 0
- Cases skipped (P5/P6/PENDING_FILING_COLLECTION): 20

## Draft Rows

No draft rows generated — all cases are P5/P6/PENDING_FILING_COLLECTION.

## Skipped Cases

| case_id | ticker | tier | reason |
|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM | EPZM | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0052-ACQUIRED-FMTX | FMTX | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0053-ACQUIRED-GBT | GBT | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0054-ACQUIRED-IMGO | IMGO | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0055-ACQUIRED-OYST | OYST | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0056-ACQUIRED-SRRA | SRRA | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0057-ACQUIRED-TPTX | TPTX | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0058-ACQUIRED-BLU | BLU | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0059-ACQUIRED-CINC | CINC | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0060-ACQUIRED-CTIC | CTIC | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0061-ACQUIRED-DICE | DICE | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0062-ACQUIRED-HARP | HARP | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0063-ACQUIRED-ISEE | ISEE | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0064-ACQUIRED-RETA | RETA | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0066-ACQUIRED-ZYNE | ZYNE | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0067-ACQUIRED-ALPN | ALPN | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0068-ACQUIRED-AMAM | AMAM | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0069-ACQUIRED-CBAY | CBAY | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0070-ACQUIRED-CERE | CERE | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0071-ACQUIRED-DCPH | DCPH | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |

## Workflow

1. Open each PLACEHOLDER row.
2. Find the actual filing in EDGAR using the edgar_company_search_url from the exception queue.
3. Fill: source_name, source_url, filing_type, filing_date, accession_number, excerpt.
4. Change verification_status from DRAFT_PENDING_REVIEW to a real status.
5. Change confidence from LOW to HIGH/MEDIUM/LOW based on verified evidence.
6. Append to data/historical_cases/source_evidence.csv manually.
7. Do not mark any case VERIFIED or CALIBRATION_ELIGIBLE.
