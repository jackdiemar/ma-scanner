# Case Packet Generation Report

Generated: 2026-05-14

## Summary

- Packets generated: 50
- Scope: acquisition queue first, then additional ACQUIRED candidates from resolved_case_candidates.csv as needed.
- Workflow completeness score is not investment quality and not P(deal).
- No cases were marked VERIFIED or CALIBRATION_ELIGIBLE.

## Prior Signal Adjudication Summary

- NOT_ADJUDICATED: 28
- NEEDS_MANUAL_REVIEW: 11
- TRUE_PUBLIC_PRIOR_SIGNAL: 3
- PRIVATE_BACKGROUND_ONLY: 3
- ASSET_SPECIFIC_RIGHTS_ONLY: 2
- DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE: 2
- RIGHTS_LANGUAGE_ONLY: 1

## True Prior Public Signal Packets

| case | ticker | score | recommended_status | missing fields |
| --- | --- | ---: | --- | ---: |
| RHC-0006-ACQUIRED-MDVN | MDVN | 80 | PARTIAL | 2 |
| RHC-0012-ACQUIRED-DMTX | DMTX | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0025-ACQUIRED-TSRO | TSRO | 40 | PARTIAL_READY | 5 |

## False-Positive Prior Signal Packets

| case | ticker | score | recommended_status | missing fields |
| --- | --- | ---: | --- | ---: |
| RHC-0005-ACQUIRED-CPXX | CPXX | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0020-ACQUIRED-ARRY | ARRY | 5 | PARTIAL_READY | 7 |
| RHC-0029-ACQUIRED-FTSV | FTSV | 20 | KEEP_CANDIDATE | 6 |
| RHC-0031-ACQUIRED-MYOK | MYOK | 20 | KEEP_CANDIDATE | 6 |
| RHC-0033-ACQUIRED-PRNB | PRNB | 20 | KEEP_CANDIDATE | 6 |
| RHC-0035-ACQUIRED-ADMS | ADMS | 20 | KEEP_CANDIDATE | 6 |
| RHC-0043-ACQUIRED-TRIL | TRIL | 20 | KEEP_CANDIDATE | 6 |
| RHC-0045-ACQUIRED-XLRN | XLRN | 20 | KEEP_CANDIDATE | 6 |

## Top 10 Highest-Completeness Packets

| case | ticker | score | recommended_status | missing fields |
| --- | --- | ---: | --- | ---: |
| RHC-0001-ACQUIRED-NPSP | NPSP | 80 | PARTIAL | 2 |
| RHC-0002-ACQUIRED-PCYC | PCYC | 80 | PARTIAL | 2 |
| RHC-0003-ACQUIRED-ZSPH | ZSPH | 80 | PARTIAL | 2 |
| RHC-0004-ACQUIRED-ANAC | ANAC | 80 | PARTIAL | 2 |
| RHC-0006-ACQUIRED-MDVN | MDVN | 80 | PARTIAL | 2 |
| RHC-0008-ACQUIRED-TBRA | TBRA | 80 | PARTIAL_READY | 2 |
| RHC-0010-ACQUIRED-ARIA | ARIA | 80 | PARTIAL_READY | 2 |
| RHC-0013-ACQUIRED-KITE | KITE | 80 | PARTIAL_READY | 2 |
| RHC-0015-ACQUIRED-BIVV | BIVV | 80 | PARTIAL_READY | 2 |
| RHC-0017-ACQUIRED-JUNO | JUNO | 80 | PARTIAL_READY | 2 |

## Bottom 10 Lowest-Completeness Packets

| case | ticker | score | recommended_status | missing fields |
| --- | --- | ---: | --- | ---: |
| RHC-0005-ACQUIRED-CPXX | CPXX | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0007-ACQUIRED-RLYP | RLYP | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0009-ACQUIRED-VTAE | VTAE | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0011-ACQUIRED-CLCD | CLCD | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0012-ACQUIRED-DMTX | DMTX | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0014-ACQUIRED-AVXS | AVXS | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0016-ACQUIRED-CASC | CASC | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0018-ACQUIRED-RXDX | RXDX | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0019-ACQUIRED-ALDR | ALDR | 5 | PARTIAL_READY | 7 |
| RHC-0020-ACQUIRED-ARRY | ARRY | 5 | PARTIAL_READY | 7 |

## Common Missing Fields

- premium extraction: 50
- price-window verification: 50
- background section extraction: 40
- prior process signal review: 40
- observation date candidate: 40
- core acquisition evidence: 37
- source evidence rows: 14

## Cases Closest To PARTIAL

| case | ticker | score | recommended_status | missing fields | next action |
| --- | --- | ---: | --- | ---: | --- |
| RHC-0008-ACQUIRED-TBRA | TBRA | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
| RHC-0010-ACQUIRED-ARIA | ARIA | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
| RHC-0013-ACQUIRED-KITE | KITE | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
| RHC-0015-ACQUIRED-BIVV | BIVV | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
| RHC-0017-ACQUIRED-JUNO | JUNO | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
| RHC-0025-ACQUIRED-TSRO | TSRO | 40 | PARTIAL_READY | 5 | Run acquisition_background_extractor.py or manually capture proxy/Schedule 14D-9 background section. |
| RHC-0036-ACQUIRED-DOVA | DOVA | 40 | PARTIAL_READY | 5 | Run acquisition_background_extractor.py or manually capture proxy/Schedule 14D-9 background section. |
| RHC-0038-ACQUIRED-FLXN | FLXN | 40 | PARTIAL_READY | 5 | Run acquisition_background_extractor.py or manually capture proxy/Schedule 14D-9 background section. |
| RHC-0026-ACQUIRED-ACHN | ACHN | 20 | KEEP_CANDIDATE | 6 | Open primary acquisition evidence, then run date and pre-announcement signal workflows. |
| RHC-0027-ACQUIRED-BOLD | BOLD | 20 | KEEP_CANDIDATE | 6 | Open primary acquisition evidence, then run date and pre-announcement signal workflows. |

## Cases Closest To Future VERIFIED

| case | ticker | score | recommended_status | missing fields | next action |
| --- | --- | ---: | --- | ---: | --- |
| RHC-0001-ACQUIRED-NPSP | NPSP | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |
| RHC-0002-ACQUIRED-PCYC | PCYC | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |
| RHC-0003-ACQUIRED-ZSPH | ZSPH | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |
| RHC-0004-ACQUIRED-ANAC | ANAC | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |
| RHC-0006-ACQUIRED-MDVN | MDVN | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |

## Next Best Verification Batch

| case | ticker | score | recommended_status | missing fields | next action |
| --- | --- | ---: | --- | ---: | --- |
| RHC-0001-ACQUIRED-NPSP | NPSP | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |
| RHC-0002-ACQUIRED-PCYC | PCYC | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |
| RHC-0003-ACQUIRED-ZSPH | ZSPH | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |
| RHC-0004-ACQUIRED-ANAC | ANAC | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |
| RHC-0006-ACQUIRED-MDVN | MDVN | 80 | PARTIAL | 2 | Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status. |
| RHC-0008-ACQUIRED-TBRA | TBRA | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
| RHC-0010-ACQUIRED-ARIA | ARIA | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
| RHC-0013-ACQUIRED-KITE | KITE | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
| RHC-0015-ACQUIRED-BIVV | BIVV | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
| RHC-0017-ACQUIRED-JUNO | JUNO | 80 | PARTIAL_READY | 2 | Promote only after primary-source evidence supports the PARTIAL checklist. |
