# Batch 51–70 Source Evidence Draft

Generated: 2026-05-16

Draft file only. Do NOT copy these rows to source_evidence.csv without verification.
All PLACEHOLDER fields must be filled from the actual filing before promoting.

## Summary

- Draft rows generated: 10
- Cases skipped (P5/P6/PENDING_FILING_COLLECTION): 16

## Draft Rows

| evidence_id | ticker | tier | reason |
|---|---|---|---|
| RHC-0072-ACQUIRED-FATE-ADJ-DRAFT-001 | FATE | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0075-ACQUIRED-GRCL-ADJ-DRAFT-001 | GRCL | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0108-ACQUIRED-VECT-ADJ-DRAFT-001 | VECT | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0109-ACQUIRED-MOR-ADJ-DRAFT-001 | MOR | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0131-ACQUIRED-LMNX-ADJ-DRAFT-001 | LMNX | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0134-ACQUIRED-ENLV-ADJ-DRAFT-001 | ENLV | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0135-ACQUIRED-HRMY-ADJ-DRAFT-001 | HRMY | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0136-ACQUIRED-SYNH-ADJ-DRAFT-001 | SYNH | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0137-ACQUIRED-KPTI-ADJ-DRAFT-001 | KPTI | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0139-ACQUIRED-TGTX-ADJ-DRAFT-001 | TGTX | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |

## Skipped Cases

| case_id | ticker | tier | reason |
|---|---|---|---|
| RHC-0073-ACQUIRED-FUSN | FUSN | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0074-ACQUIRED-G1T | G1T | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0076-ACQUIRED-KRTX | KRTX | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0077-ACQUIRED-LBPH | LBPH | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0078-ACQUIRED-MORF | MORF | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0079-ACQUIRED-MRTX | MRTX | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0101-ACQUIRED-CHMA | CHMA | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0102-ACQUIRED-CNST | CNST | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0103-ACQUIRED-STML | STML | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0104-ACQUIRED-ALBO | ALBO | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0105-ACQUIRED-HZNP | HZNP | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0106-ACQUIRED-SGEN | SGEN | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0107-ACQUIRED-SNDX | SNDX | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0132-ACQUIRED-TBIO | TBIO | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0138-ACQUIRED-KROS | KROS | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |
| RHC-0140-ACQUIRED-VSTM | VSTM | PENDING_FILING_COLLECTION | Date confirmed; filing collector has not yet run for this ca |

## Workflow

1. Open each PLACEHOLDER row.
2. Find the actual filing in EDGAR using the edgar_company_search_url from the exception queue.
3. Fill: source_name, source_url, filing_type, filing_date, accession_number, excerpt.
4. Change verification_status from DRAFT_PENDING_REVIEW to a real status.
5. Change confidence from LOW to HIGH/MEDIUM/LOW based on verified evidence.
6. Append to data/historical_cases/source_evidence.csv manually.
7. Do not mark any case VERIFIED or CALIBRATION_ELIGIBLE.
