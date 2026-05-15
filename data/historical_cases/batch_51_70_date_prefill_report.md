# Batch 51–70 Date Prefill Queue

Generated: 2026-05-14

Work queue only. Dates in this report are not inserted into any canonical file.
Resolve each NEEDS_DATE_BACKFILL=TRUE case before running the filing collector.

## Summary

- Cases in scope: 20
- Needs date backfill: 20
- Date already present: 0

## Cases Needing Date Backfill

| case_id | ticker | company | year | edgar_merger_8k_query_url |
|---|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM | EPZM | Epizyme | 2022 | https://efts.sec.gov/LATEST/search-index?q=%22Epizyme%22%20%22agreement%20and%20... |
| RHC-0052-ACQUIRED-FMTX | FMTX | Forma Therapeutics Holdings, Inc. | 2022 | https://efts.sec.gov/LATEST/search-index?q=%22Forma%20Therapeutics%20Holdings%2C... |
| RHC-0053-ACQUIRED-GBT | GBT | Global Blood Therapeutics, Inc. | 2022 | https://efts.sec.gov/LATEST/search-index?q=%22Global%20Blood%20Therapeutics%2C%2... |
| RHC-0054-ACQUIRED-IMGO | IMGO | Imago BioSciences | 2022 | https://efts.sec.gov/LATEST/search-index?q=%22Imago%20BioSciences%22%20%22agreem... |
| RHC-0055-ACQUIRED-OYST | OYST | Oyster Point Pharma | 2022 | https://efts.sec.gov/LATEST/search-index?q=%22Oyster%20Point%20Pharma%22%20%22ag... |
| RHC-0056-ACQUIRED-SRRA | SRRA | Sierra Oncology | 2022 | https://efts.sec.gov/LATEST/search-index?q=%22Sierra%20Oncology%22%20%22agreemen... |
| RHC-0057-ACQUIRED-TPTX | TPTX | Turning Point Therapeutics, Inc. | 2022 | https://efts.sec.gov/LATEST/search-index?q=%22Turning%20Point%20Therapeutics%2C%... |
| RHC-0058-ACQUIRED-BLU | BLU | BELLUS Health Inc. | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22BELLUS%20Health%20Inc.%22%20%22agr... |
| RHC-0059-ACQUIRED-CINC | CINC | CinCor Pharma, Inc. | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22CinCor%20Pharma%2C%20Inc.%22%20%22... |
| RHC-0060-ACQUIRED-CTIC | CTIC | CTI BioPharma | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22CTI%20BioPharma%22%20%22agreement%... |
| RHC-0061-ACQUIRED-DICE | DICE | DICE Therapeutics, Inc. | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22DICE%20Therapeutics%2C%20Inc.%22%2... |
| RHC-0062-ACQUIRED-HARP | HARP | Harpoon Therapeutics | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Harpoon%20Therapeutics%22%20%22agr... |
| RHC-0063-ACQUIRED-ISEE | ISEE | IVERIC bio, Inc. | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22IVERIC%20bio%2C%20Inc.%22%20%22agr... |
| RHC-0064-ACQUIRED-RETA | RETA | Reata Pharmaceuticals, Inc. | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Reata%20Pharmaceuticals%2C%20Inc.%... |
| RHC-0066-ACQUIRED-ZYNE | ZYNE | Zynerba Pharmaceuticals, Inc. | 2023 | https://efts.sec.gov/LATEST/search-index?q=%22Zynerba%20Pharmaceuticals%2C%20Inc... |
| RHC-0067-ACQUIRED-ALPN | ALPN | Alpine Immune Sciences, Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Alpine%20Immune%20Sciences%2C%20In... |
| RHC-0068-ACQUIRED-AMAM | AMAM | Ambrx Biopharma Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Ambrx%20Biopharma%20Inc.%22%20%22a... |
| RHC-0069-ACQUIRED-CBAY | CBAY | CymaBay Therapeutics, Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22CymaBay%20Therapeutics%2C%20Inc.%2... |
| RHC-0070-ACQUIRED-CERE | CERE | Cerevel Therapeutics Holdings, Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Cerevel%20Therapeutics%20Holdings%... |
| RHC-0071-ACQUIRED-DCPH | DCPH | Deciphera Pharmaceuticals, Inc. | 2024 | https://efts.sec.gov/LATEST/search-index?q=%22Deciphera%20Pharmaceuticals%2C%20I... |

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
