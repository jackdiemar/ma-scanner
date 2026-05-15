# Batch 51–70 Date Prefill Queue

Generated: 2026-05-14

Work queue only. Dates in this report are not inserted into any canonical file.
Resolve each NEEDS_DATE_BACKFILL=TRUE case before running the filing collector.

## Summary

- Cases in scope: 20
- Needs date backfill: 0
- Date already present: 20

## Cases Needing Date Backfill

None — all cases in scope have a date.

## Cases With Date Present

| case_id | ticker | date | confidence |
|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM | EPZM | 2022-06-27 | HIGH |
| RHC-0052-ACQUIRED-FMTX | FMTX | 2022-09-01 | HIGH |
| RHC-0053-ACQUIRED-GBT | GBT | 2022-08-08 | HIGH |
| RHC-0054-ACQUIRED-IMGO | IMGO | 2022-11-21 | HIGH |
| RHC-0055-ACQUIRED-OYST | OYST | 2022-11-08 | HIGH |
| RHC-0056-ACQUIRED-SRRA | SRRA | 2022-04-13 | HIGH |
| RHC-0057-ACQUIRED-TPTX | TPTX | 2022-06-03 | HIGH |
| RHC-0058-ACQUIRED-BLU | BLU | 2023-04-18 | HIGH |
| RHC-0059-ACQUIRED-CINC | CINC | 2023-01-09 | HIGH |
| RHC-0060-ACQUIRED-CTIC | CTIC | 2023-05-10 | HIGH |
| RHC-0061-ACQUIRED-DICE | DICE | 2023-06-20 | HIGH |
| RHC-0062-ACQUIRED-HARP | HARP | 2024-01-08 | HIGH |
| RHC-0063-ACQUIRED-ISEE | ISEE | 2023-05-01 | HIGH |
| RHC-0064-ACQUIRED-RETA | RETA | 2023-07-31 | HIGH |
| RHC-0066-ACQUIRED-ZYNE | ZYNE | 2023-08-14 | HIGH |
| RHC-0067-ACQUIRED-ALPN | ALPN | 2024-04-10 | HIGH |
| RHC-0068-ACQUIRED-AMAM | AMAM | 2024-01-08 | HIGH |
| RHC-0069-ACQUIRED-CBAY | CBAY | 2024-02-12 | HIGH |
| RHC-0070-ACQUIRED-CERE | CERE | 2023-12-07 | HIGH |
| RHC-0071-ACQUIRED-DCPH | DCPH | 2024-04-29 | HIGH |

## Next Steps

1. For each NEEDS_DATE_BACKFILL=TRUE case:
   - Open the edgar_merger_8k_query_url.
   - Find the earliest 8-K with 'agreement and plan of merger' in the filing.
   - Note the filing date and add a CURATED_DATE_EVIDENCE entry to
     src/historical_case_tools/acquisition_announcement_date_backfiller.py.
   - Or add a source_evidence row with evidence_type=8K_MERGER.
2. Re-run acquisition_announcement_date_backfiller.py.
3. Confirm all 20 cases have HIGH or MEDIUM confidence.
4. Run pre_announcement_filing_collector.py.
5. Then run exception_queue_builder.py to build the review queue.
