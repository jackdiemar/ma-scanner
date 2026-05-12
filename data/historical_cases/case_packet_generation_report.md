# Case Packet Generation Report

Generated: 2026-05-12

## Summary

- Packets generated: 25
- Scope: top acquisition cases from acquisition_verification_queue.csv
- Workflow completeness score is not investment quality and not P(deal).
- No cases were marked VERIFIED or CALIBRATION_ELIGIBLE.

## Top 10 Highest-Completeness Packets

| case | ticker | score | recommended_status | missing fields |
| --- | --- | ---: | --- | ---: |
| RHC-0001-ACQUIRED-NPSP | NPSP | 80 | PARTIAL | 2 |
| RHC-0002-ACQUIRED-PCYC | PCYC | 80 | PARTIAL | 2 |
| RHC-0003-ACQUIRED-ZSPH | ZSPH | 80 | PARTIAL | 2 |
| RHC-0004-ACQUIRED-ANAC | ANAC | 80 | PARTIAL | 2 |
| RHC-0006-ACQUIRED-MDVN | MDVN | 80 | PARTIAL | 2 |
| RHC-0005-ACQUIRED-CPXX | CPXX | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0007-ACQUIRED-RLYP | RLYP | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0008-ACQUIRED-TBRA | TBRA | 5 | PARTIAL_READY | 7 |
| RHC-0009-ACQUIRED-VTAE | VTAE | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0010-ACQUIRED-ARIA | ARIA | 5 | PARTIAL_READY | 7 |

## Bottom 10 Lowest-Completeness Packets

| case | ticker | score | recommended_status | missing fields |
| --- | --- | ---: | --- | ---: |
| RHC-0005-ACQUIRED-CPXX | CPXX | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0007-ACQUIRED-RLYP | RLYP | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0008-ACQUIRED-TBRA | TBRA | 5 | PARTIAL_READY | 7 |
| RHC-0009-ACQUIRED-VTAE | VTAE | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0010-ACQUIRED-ARIA | ARIA | 5 | PARTIAL_READY | 7 |
| RHC-0011-ACQUIRED-CLCD | CLCD | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0012-ACQUIRED-DMTX | DMTX | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0013-ACQUIRED-KITE | KITE | 5 | PARTIAL_READY | 7 |
| RHC-0014-ACQUIRED-AVXS | AVXS | 5 | NEEDS_MANUAL_RESEARCH | 7 |
| RHC-0015-ACQUIRED-BIVV | BIVV | 5 | PARTIAL_READY | 7 |

## Common Missing Fields

- premium extraction: 25
- price-window verification: 25
- core acquisition evidence: 20
- source evidence rows: 20
- background section extraction: 20
- prior process signal review: 20
- observation date candidate: 20

## Cases Closest To PARTIAL

| case | ticker | score | recommended_status | missing fields | next action |
| --- | --- | ---: | --- | ---: | --- |
| RHC-0008-ACQUIRED-TBRA | TBRA | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0010-ACQUIRED-ARIA | ARIA | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0013-ACQUIRED-KITE | KITE | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0015-ACQUIRED-BIVV | BIVV | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0017-ACQUIRED-JUNO | JUNO | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0019-ACQUIRED-ALDR | ALDR | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0020-ACQUIRED-ARRY | ARRY | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0022-ACQUIRED-LOXO | LOXO | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0024-ACQUIRED-ONCE | ONCE | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0025-ACQUIRED-TSRO | TSRO | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |

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
| RHC-0008-ACQUIRED-TBRA | TBRA | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0010-ACQUIRED-ARIA | ARIA | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0013-ACQUIRED-KITE | KITE | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0015-ACQUIRED-BIVV | BIVV | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
| RHC-0017-ACQUIRED-JUNO | JUNO | 5 | PARTIAL_READY | 7 | Open merger 8-K first, extract acquirer and consideration, then confirm proxy background section. |
