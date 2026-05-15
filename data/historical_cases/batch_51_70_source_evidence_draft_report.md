# Batch 51–70 Source Evidence Draft

Generated: 2026-05-15

Draft file only. Do NOT copy these rows to source_evidence.csv without verification.
All PLACEHOLDER fields must be filled from the actual filing before promoting.

## Summary

- Draft rows generated: 5
- Cases skipped (P5/P6/PENDING_FILING_COLLECTION): 15

## Draft Rows

| evidence_id | ticker | tier | reason |
|---|---|---|---|
| RHC-0054-ACQUIRED-IMGO-ADJ-DRAFT-001 | IMGO | P3 | SC 13D filing found — verify Item 4 for acquisition-pressure |
| RHC-0055-ACQUIRED-OYST-ADJ-DRAFT-001 | OYST | P1 | Explicit process language: acquisition_proposal. |
| RHC-0056-ACQUIRED-SRRA-ADJ-DRAFT-001 | SRRA | P3 | SC 13D filing found — verify Item 4 for acquisition-pressure |
| RHC-0061-ACQUIRED-DICE-ADJ-DRAFT-001 | DICE | P1 | Explicit process language: acquisition_proposal. |
| RHC-0067-ACQUIRED-ALPN-ADJ-DRAFT-001 | ALPN | P3 | SC 13D filing found — verify Item 4 for acquisition-pressure |

## Skipped Cases

| case_id | ticker | tier | reason |
|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM | EPZM | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0052-ACQUIRED-FMTX | FMTX | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0053-ACQUIRED-GBT | GBT | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0057-ACQUIRED-TPTX | TPTX | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0058-ACQUIRED-BLU | BLU | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0059-ACQUIRED-CINC | CINC | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0060-ACQUIRED-CTIC | CTIC | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0062-ACQUIRED-HARP | HARP | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0063-ACQUIRED-ISEE | ISEE | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0064-ACQUIRED-RETA | RETA | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0066-ACQUIRED-ZYNE | ZYNE | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0068-ACQUIRED-AMAM | AMAM | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0069-ACQUIRED-CBAY | CBAY | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0070-ACQUIRED-CERE | CERE | P6 | Filing collection ran; no relevant signal phrases found. |
| RHC-0071-ACQUIRED-DCPH | DCPH | P6 | Filing collection ran; no relevant signal phrases found. |

## Workflow

1. Open each PLACEHOLDER row.
2. Find the actual filing in EDGAR using the edgar_company_search_url from the exception queue.
3. Fill: source_name, source_url, filing_type, filing_date, accession_number, excerpt.
4. Change verification_status from DRAFT_PENDING_REVIEW to a real status.
5. Change confidence from LOW to HIGH/MEDIUM/LOW based on verified evidence.
6. Append to data/historical_cases/source_evidence.csv manually.
7. Do not mark any case VERIFIED or CALIBRATION_ELIGIBLE.
