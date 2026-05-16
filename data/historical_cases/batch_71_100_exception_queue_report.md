# Batch 51–70 Exception Queue

Generated: 2026-05-16

Work queue only. No cases adjudicated. Do not classify any case as TRUE_PUBLIC_PRIOR_SIGNAL.
Resolve BLOCKED cases first (date backfill), then run filing collector, then review P1–P4.

## Summary

- Cases in scope: 26
- BLOCKED: 26

## Priority Queue

### BLOCKED (26 cases)

| case_id | ticker | company | year | reason |
|---|---|---|---|---|
| RHC-0072-ACQUIRED-FATE | FATE | Fate Therapeutics | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0073-ACQUIRED-FUSN | FUSN | Fusion Pharmaceuticals Inc. | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0074-ACQUIRED-G1T | G1T | G1 Therapeutics | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0075-ACQUIRED-GRCL | GRCL | Gracell Biotechnologies | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0076-ACQUIRED-KRTX | KRTX | Karuna Therapeutics, Inc. | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0077-ACQUIRED-LBPH | LBPH | Longboard Pharmaceuticals, Inc. | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0078-ACQUIRED-MORF | MORF | Morphic Holding, Inc. | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0079-ACQUIRED-MRTX | MRTX | Mirati Therapeutics, Inc. | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0101-ACQUIRED-CHMA | CHMA | Chiasma | 2021 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0102-ACQUIRED-CNST | CNST | Constellation Pharmaceuticals | 2021 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0103-ACQUIRED-STML | STML | Stemline Therapeutics | 2021 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0104-ACQUIRED-ALBO | ALBO | Albireo Pharma | 2023 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0105-ACQUIRED-HZNP | HZNP | Horizon Therapeutics plc | 2023 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0106-ACQUIRED-SGEN | SGEN | Seagen Inc. | 2023 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0107-ACQUIRED-SNDX | SNDX | Syndax Pharmaceuticals | 2023 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0108-ACQUIRED-VECT | VECT | VectivBio Holding | 2023 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0109-ACQUIRED-MOR | MOR | MorphoSys AG | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0131-ACQUIRED-LMNX | LMNX | Luminex Corporation | 2021 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0132-ACQUIRED-TBIO | TBIO | Translate Bio | 2021 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0134-ACQUIRED-ENLV | ENLV | Enliven Therapeutics | 2023 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0135-ACQUIRED-HRMY | HRMY | Harmony Biosciences | 2023 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0136-ACQUIRED-SYNH | SYNH | Syneos Health, Inc. | 2023 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0137-ACQUIRED-KPTI | KPTI | Karyopharm Therapeutics | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0138-ACQUIRED-KROS | KROS | Keros Therapeutics | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0139-ACQUIRED-TGTX | TGTX | TG Therapeutics | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |
| RHC-0140-ACQUIRED-VSTM | VSTM | Verastem Oncology | 2024 | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. |

## Next Steps

1. Resolve all BLOCKED cases: add HIGH/MEDIUM announcement dates via merger_date_prefiller queue.
2. Run pre_announcement_filing_collector.py for PENDING_FILING_COLLECTION cases.
3. Re-run this script after filing collection — PENDING cases will be re-classified P1–P6.
4. Review P1 cases first: open filing links, read phrase context, adjudicate case_level_true_signal.
5. Review P2, P3, P4 in order. P5 and P6 require minimal review.
6. Add source evidence rows to acquisition_announcement_dates.csv for confirmed dates.
7. Add adjudication rows to prior_signal_adjudication_queue.csv for all reviewed cases.
