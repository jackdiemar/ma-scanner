# Batch 51–70 Date Prefill Queue

Generated: 2026-05-16

Work queue only. Dates in this report are not inserted into any canonical file.
Resolve each NEEDS_DATE_BACKFILL=TRUE case before running the filing collector.

## Summary

- Cases in scope: 26
- Needs date backfill: 26
- Date already present: 0

## Cases Needing Date Backfill

| case_id | ticker | company | year | edgar_merger_8k_query_url |
|---|---|---|---|---|
| RHC-0072-ACQUIRED-FATE | FATE | Fate Therapeutics | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Fate%20Therapeutics%22%20%22agreem... |
| RHC-0073-ACQUIRED-FUSN | FUSN | Fusion Pharmaceuticals Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Fusion%20Pharmaceuticals%20Inc.%22... |
| RHC-0074-ACQUIRED-G1T | G1T | G1 Therapeutics | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22G1%20Therapeutics%22%20%22agreemen... |
| RHC-0075-ACQUIRED-GRCL | GRCL | Gracell Biotechnologies | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Gracell%20Biotechnologies%22%20%22... |
| RHC-0076-ACQUIRED-KRTX | KRTX | Karuna Therapeutics, Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Karuna%20Therapeutics%2C%20Inc.%22... |
| RHC-0077-ACQUIRED-LBPH | LBPH | Longboard Pharmaceuticals, Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Longboard%20Pharmaceuticals%2C%20I... |
| RHC-0078-ACQUIRED-MORF | MORF | Morphic Holding, Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Morphic%20Holding%2C%20Inc.%22%20%... |
| RHC-0079-ACQUIRED-MRTX | MRTX | Mirati Therapeutics, Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Mirati%20Therapeutics%2C%20Inc.%22... |
| RHC-0101-ACQUIRED-CHMA | CHMA | Chiasma | 2021 | https://efts.sec.gov/LATEST/search-index?q=%22Chiasma%22%20%22agreement%20and%20... |
| RHC-0102-ACQUIRED-CNST | CNST | Constellation Pharmaceuticals | 2021 | https://efts.sec.gov/LATEST/search-index?q=%22Constellation%20Pharmaceuticals%22... |
| RHC-0103-ACQUIRED-STML | STML | Stemline Therapeutics | 2021 | https://efts.sec.gov/LATEST/search-index?q=%22Stemline%20Therapeutics%22%20%22ag... |
| RHC-0104-ACQUIRED-ALBO | ALBO | Albireo Pharma | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Albireo%20Pharma%22%20%22agreement... |
| RHC-0105-ACQUIRED-HZNP | HZNP | Horizon Therapeutics plc | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Horizon%20Therapeutics%20plc%22%20... |
| RHC-0106-ACQUIRED-SGEN | SGEN | Seagen Inc. | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Seagen%20Inc.%22%20%22agreement%20... |
| RHC-0107-ACQUIRED-SNDX | SNDX | Syndax Pharmaceuticals | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Syndax%20Pharmaceuticals%22%20%22a... |
| RHC-0108-ACQUIRED-VECT | VECT | VectivBio Holding | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22VectivBio%20Holding%22%20%22agreem... |
| RHC-0109-ACQUIRED-MOR | MOR | MorphoSys AG | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22MorphoSys%20AG%22%20%22agreement%2... |
| RHC-0131-ACQUIRED-LMNX | LMNX | Luminex Corporation | 2021 | https://efts.sec.gov/LATEST/search-index?q=%22Luminex%20Corporation%22%20%22agre... |
| RHC-0132-ACQUIRED-TBIO | TBIO | Translate Bio | 2021 | https://efts.sec.gov/LATEST/search-index?q=%22Translate%20Bio%22%20%22agreement%... |
| RHC-0134-ACQUIRED-ENLV | ENLV | Enliven Therapeutics | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Enliven%20Therapeutics%22%20%22agr... |
| RHC-0135-ACQUIRED-HRMY | HRMY | Harmony Biosciences | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Harmony%20Biosciences%22%20%22agre... |
| RHC-0136-ACQUIRED-SYNH | SYNH | Syneos Health, Inc. | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Syneos%20Health%2C%20Inc.%22%20%22... |
| RHC-0137-ACQUIRED-KPTI | KPTI | Karyopharm Therapeutics | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Karyopharm%20Therapeutics%22%20%22... |
| RHC-0138-ACQUIRED-KROS | KROS | Keros Therapeutics | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Keros%20Therapeutics%22%20%22agree... |
| RHC-0139-ACQUIRED-TGTX | TGTX | TG Therapeutics | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22TG%20Therapeutics%22%20%22agreemen... |
| RHC-0140-ACQUIRED-VSTM | VSTM | Verastem Oncology | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Verastem%20Oncology%22%20%22agreem... |

## Cases With Date Present

None.

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
