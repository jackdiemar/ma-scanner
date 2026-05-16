# Batch 51–70 Date Prefill Queue

Generated: 2026-05-16

Work queue only. Dates in this report are not inserted into any canonical file.
Resolve each NEEDS_DATE_BACKFILL=TRUE case before running the filing collector.

## Summary

- Cases in scope: 26
- Needs date backfill: 10
- Date already present: 16

## Cases Needing Date Backfill

| case_id | ticker | company | year | edgar_merger_8k_query_url |
|---|---|---|---|---|
| RHC-0072-ACQUIRED-FATE | FATE | Fate Therapeutics | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Fate%20Therapeutics%22%20%22agreem... |
| RHC-0075-ACQUIRED-GRCL | GRCL | Gracell Biotechnologies | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Gracell%20Biotechnologies%22%20%22... |
| RHC-0108-ACQUIRED-VECT | VECT | VectivBio Holding | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22VectivBio%20Holding%22%20%22agreem... |
| RHC-0109-ACQUIRED-MOR | MOR | MorphoSys AG | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22MorphoSys%20AG%22%20%22agreement%2... |
| RHC-0131-ACQUIRED-LMNX | LMNX | Luminex Corporation | 2021 | https://efts.sec.gov/LATEST/search-index?q=%22Luminex%20Corporation%22%20%22agre... |
| RHC-0134-ACQUIRED-ENLV | ENLV | Enliven Therapeutics | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Enliven%20Therapeutics%22%20%22agr... |
| RHC-0135-ACQUIRED-HRMY | HRMY | Harmony Biosciences | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Harmony%20Biosciences%22%20%22agre... |
| RHC-0136-ACQUIRED-SYNH | SYNH | Syneos Health, Inc. | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Syneos%20Health%2C%20Inc.%22%20%22... |
| RHC-0137-ACQUIRED-KPTI | KPTI | Karyopharm Therapeutics | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Karyopharm%20Therapeutics%22%20%22... |
| RHC-0139-ACQUIRED-TGTX | TGTX | TG Therapeutics | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22TG%20Therapeutics%22%20%22agreemen... |

## Cases With Date Present

| case_id | ticker | date | confidence |
|---|---|---|---|
| RHC-0073-ACQUIRED-FUSN | FUSN | 2024-03-19 | MEDIUM |
| RHC-0074-ACQUIRED-G1T | G1T | 2024-08-07 | HIGH |
| RHC-0076-ACQUIRED-KRTX | KRTX | 2023-12-22 | MEDIUM |
| RHC-0077-ACQUIRED-LBPH | LBPH | 2024-10-15 | HIGH |
| RHC-0078-ACQUIRED-MORF | MORF | 2024-07-08 | MEDIUM |
| RHC-0079-ACQUIRED-MRTX | MRTX | 2023-10-10 | HIGH |
| RHC-0101-ACQUIRED-CHMA | CHMA | 2021-05-05 | HIGH |
| RHC-0102-ACQUIRED-CNST | CNST | 2021-06-02 | HIGH |
| RHC-0103-ACQUIRED-STML | STML | 2020-05-04 | MEDIUM |
| RHC-0104-ACQUIRED-ALBO | ALBO | 2023-01-09 | HIGH |
| RHC-0105-ACQUIRED-HZNP | HZNP | 2022-12-12 | MEDIUM |
| RHC-0106-ACQUIRED-SGEN | SGEN | 2023-03-13 | HIGH |
| RHC-0107-ACQUIRED-SNDX | SNDX | 2023-12-15 | MEDIUM |
| RHC-0132-ACQUIRED-TBIO | TBIO | 2021-08-03 | HIGH |
| RHC-0138-ACQUIRED-KROS | KROS | 2024-12-03 | MEDIUM |
| RHC-0140-ACQUIRED-VSTM | VSTM | 2024-01-08 | MEDIUM |

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
