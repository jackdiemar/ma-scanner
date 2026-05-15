# Batch 51–70 Source Evidence Draft

Generated: 2026-05-14

Draft file only. Do NOT copy these rows to source_evidence.csv without verification.
All PLACEHOLDER fields must be filled from the actual filing before promoting.

## Summary

- Draft rows generated: 20
- Cases skipped (P5/P6/PENDING_FILING_COLLECTION): 0

## Draft Rows

| evidence_id | ticker | tier | reason |
|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM-ADJ-DRAFT-001 | EPZM | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0052-ACQUIRED-FMTX-ADJ-DRAFT-001 | FMTX | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0053-ACQUIRED-GBT-ADJ-DRAFT-001 | GBT | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0054-ACQUIRED-IMGO-ADJ-DRAFT-001 | IMGO | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0055-ACQUIRED-OYST-ADJ-DRAFT-001 | OYST | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0056-ACQUIRED-SRRA-ADJ-DRAFT-001 | SRRA | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0057-ACQUIRED-TPTX-ADJ-DRAFT-001 | TPTX | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0058-ACQUIRED-BLU-ADJ-DRAFT-001 | BLU | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0059-ACQUIRED-CINC-ADJ-DRAFT-001 | CINC | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0060-ACQUIRED-CTIC-ADJ-DRAFT-001 | CTIC | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0061-ACQUIRED-DICE-ADJ-DRAFT-001 | DICE | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0062-ACQUIRED-HARP-ADJ-DRAFT-001 | HARP | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0063-ACQUIRED-ISEE-ADJ-DRAFT-001 | ISEE | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0064-ACQUIRED-RETA-ADJ-DRAFT-001 | RETA | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0066-ACQUIRED-ZYNE-ADJ-DRAFT-001 | ZYNE | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0067-ACQUIRED-ALPN-ADJ-DRAFT-001 | ALPN | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0068-ACQUIRED-AMAM-ADJ-DRAFT-001 | AMAM | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0069-ACQUIRED-CBAY-ADJ-DRAFT-001 | CBAY | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0070-ACQUIRED-CERE-ADJ-DRAFT-001 | CERE | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0071-ACQUIRED-DCPH-ADJ-DRAFT-001 | DCPH | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |

## Skipped Cases

None.

## Workflow

1. Open each PLACEHOLDER row.
2. Find the actual filing in EDGAR using the edgar_company_search_url from the exception queue.
3. Fill: source_name, source_url, filing_type, filing_date, accession_number, excerpt.
4. Change verification_status from DRAFT_PENDING_REVIEW to a real status.
5. Change confidence from LOW to HIGH/MEDIUM/LOW based on verified evidence.
6. Append to data/historical_cases/source_evidence.csv manually.
7. Do not mark any case VERIFIED or CALIBRATION_ELIGIBLE.
