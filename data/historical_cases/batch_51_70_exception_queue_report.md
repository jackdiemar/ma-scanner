# Batch 51–70 Exception Queue

Generated: 2026-05-14

Work queue only. No cases adjudicated. Do not classify any case as TRUE_PUBLIC_PRIOR_SIGNAL.
Resolve BLOCKED cases first (date backfill), then run filing collector, then review P1–P4.

## Summary

- Cases in scope: 20
- PENDING_FILING_COLLECTION: 20

## Priority Queue

### PENDING_FILING_COLLECTION (20 cases)

| case_id | ticker | company | year | reason |
|---|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM | EPZM | Epizyme | 2022 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0052-ACQUIRED-FMTX | FMTX | Forma Therapeutics Holdings, Inc. | 2022 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0053-ACQUIRED-GBT | GBT | Global Blood Therapeutics, Inc. | 2022 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0054-ACQUIRED-IMGO | IMGO | Imago BioSciences | 2022 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0055-ACQUIRED-OYST | OYST | Oyster Point Pharma | 2022 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0056-ACQUIRED-SRRA | SRRA | Sierra Oncology | 2022 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0057-ACQUIRED-TPTX | TPTX | Turning Point Therapeutics, Inc. | 2022 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0058-ACQUIRED-BLU | BLU | BELLUS Health Inc. | 2023 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0059-ACQUIRED-CINC | CINC | CinCor Pharma, Inc. | 2023 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0060-ACQUIRED-CTIC | CTIC | CTI BioPharma | 2023 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0061-ACQUIRED-DICE | DICE | DICE Therapeutics, Inc. | 2023 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0062-ACQUIRED-HARP | HARP | Harpoon Therapeutics | 2023 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0063-ACQUIRED-ISEE | ISEE | IVERIC bio, Inc. | 2023 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0064-ACQUIRED-RETA | RETA | Reata Pharmaceuticals, Inc. | 2023 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0066-ACQUIRED-ZYNE | ZYNE | Zynerba Pharmaceuticals, Inc. | 2023 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0067-ACQUIRED-ALPN | ALPN | Alpine Immune Sciences, Inc. | 2024 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0068-ACQUIRED-AMAM | AMAM | Ambrx Biopharma Inc. | 2024 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0069-ACQUIRED-CBAY | CBAY | CymaBay Therapeutics, Inc. | 2024 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0070-ACQUIRED-CERE | CERE | Cerevel Therapeutics Holdings, Inc. | 2024 | Date confirmed; filing collector has not yet run for this case. |
| RHC-0071-ACQUIRED-DCPH | DCPH | Deciphera Pharmaceuticals, Inc. | 2024 | Date confirmed; filing collector has not yet run for this case. |

## Next Steps

1. Resolve all BLOCKED cases: add HIGH/MEDIUM announcement dates via merger_date_prefiller queue.
2. Run pre_announcement_filing_collector.py for PENDING_FILING_COLLECTION cases.
3. Re-run this script after filing collection — PENDING cases will be re-classified P1–P6.
4. Review P1 cases first: open filing links, read phrase context, adjudicate case_level_true_signal.
5. Review P2, P3, P4 in order. P5 and P6 require minimal review.
6. Add source evidence rows to acquisition_announcement_dates.csv for confirmed dates.
7. Add adjudication rows to prior_signal_adjudication_queue.csv for all reviewed cases.
