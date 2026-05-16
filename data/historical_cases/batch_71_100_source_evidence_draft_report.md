# Batch 51–70 Source Evidence Draft

Generated: 2026-05-16

Draft file only. Do NOT copy these rows to source_evidence.csv without verification.
All PLACEHOLDER fields must be filled from the actual filing before promoting.

## Summary

- Draft rows generated: 26
- Cases skipped (P5/P6/PENDING_FILING_COLLECTION): 0

## Draft Rows

| evidence_id | ticker | tier | reason |
|---|---|---|---|
| RHC-0072-ACQUIRED-FATE-ADJ-DRAFT-001 | FATE | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0073-ACQUIRED-FUSN-ADJ-DRAFT-001 | FUSN | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0074-ACQUIRED-G1T-ADJ-DRAFT-001 | G1T | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0075-ACQUIRED-GRCL-ADJ-DRAFT-001 | GRCL | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0076-ACQUIRED-KRTX-ADJ-DRAFT-001 | KRTX | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0077-ACQUIRED-LBPH-ADJ-DRAFT-001 | LBPH | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0078-ACQUIRED-MORF-ADJ-DRAFT-001 | MORF | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0079-ACQUIRED-MRTX-ADJ-DRAFT-001 | MRTX | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0101-ACQUIRED-CHMA-ADJ-DRAFT-001 | CHMA | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0102-ACQUIRED-CNST-ADJ-DRAFT-001 | CNST | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0103-ACQUIRED-STML-ADJ-DRAFT-001 | STML | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0104-ACQUIRED-ALBO-ADJ-DRAFT-001 | ALBO | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0105-ACQUIRED-HZNP-ADJ-DRAFT-001 | HZNP | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0106-ACQUIRED-SGEN-ADJ-DRAFT-001 | SGEN | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0107-ACQUIRED-SNDX-ADJ-DRAFT-001 | SNDX | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0108-ACQUIRED-VECT-ADJ-DRAFT-001 | VECT | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0109-ACQUIRED-MOR-ADJ-DRAFT-001 | MOR | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0131-ACQUIRED-LMNX-ADJ-DRAFT-001 | LMNX | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0132-ACQUIRED-TBIO-ADJ-DRAFT-001 | TBIO | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0134-ACQUIRED-ENLV-ADJ-DRAFT-001 | ENLV | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0135-ACQUIRED-HRMY-ADJ-DRAFT-001 | HRMY | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0136-ACQUIRED-SYNH-ADJ-DRAFT-001 | SYNH | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0137-ACQUIRED-KPTI-ADJ-DRAFT-001 | KPTI | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0138-ACQUIRED-KROS-ADJ-DRAFT-001 | KROS | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0139-ACQUIRED-TGTX-ADJ-DRAFT-001 | TGTX | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |
| RHC-0140-ACQUIRED-VSTM-ADJ-DRAFT-001 | VSTM | BLOCKED | No HIGH/MEDIUM announcement date — run merger_date_prefiller |

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
