# Acquisition First-Five Evidence Report

Generated for the focused first-five acquisition verification pass.

## Summary

- Target cases reviewed: NPSP, PCYC, ZSPH, ANAC, MDVN.
- Evidence rows added to `source_evidence.csv`: 10.
- Cases promoted from `PARTIAL_READY` to structured `PARTIAL`: 5.
- Cases still needing manual research before recommendation: 0 in this first-five set.
- No case was marked `VERIFIED` or `CALIBRATION_ELIGIBLE`.
- Evidence rows are source-backed SEC EDGAR filings and excerpts; the structured PARTIAL rows still require background, prior-process, premium, observation-date, and price-window work before any further promotion.

## Evidence Located

| ticker | case_id | recommendation | merger 8-K | proxy/tender equivalent | source-backed fields |
| --- | --- | --- | --- | --- | --- |
| NPSP | RHC-0001-ACQUIRED-NPSP | PARTIAL | 2015-01-12, accession 0001104659-15-001685, https://www.sec.gov/Archives/edgar/data/890465/000110465915001685/a15-2148_18k.htm | SC 14D9, 2015-01-23, accession 0001047469-15-000380, https://www.sec.gov/Archives/edgar/data/890465/000104746915000380/a2222816zsc14d9.htm | acquirer, merger agreement date, deal consideration target, filing URL, background filing target |
| PCYC | RHC-0002-ACQUIRED-PCYC | PARTIAL | 2015-03-06, accession 0001193125-15-081198, https://www.sec.gov/Archives/edgar/data/949699/000119312515081198/d885732d8k.htm | SC 14D9, 2015-03-23, accession 0001193125-15-101106, https://www.sec.gov/Archives/edgar/data/949699/000119312515101106/d893590dsc14d9.htm | acquirer, deal consideration, filing URL, background section target |
| ZSPH | RHC-0003-ACQUIRED-ZSPH | PARTIAL | 2015-11-06, accession 0001193125-15-369081, https://www.sec.gov/Archives/edgar/data/1459266/000119312515369081/d73329d8k.htm | SC 14D9, 2015-11-18, accession 0001193125-15-380466, https://www.sec.gov/Archives/edgar/data/1459266/000119312515380466/d28720dsc14d9.htm | acquirer, deal price, filing URL, background section target |
| ANAC | RHC-0004-ACQUIRED-ANAC | PARTIAL | 2016-05-16, accession 0000950103-16-013361, https://www.sec.gov/Archives/edgar/data/1411158/000095010316013361/dp65732_8k.htm | SC 14D9, 2016-05-26, accession 0001193125-16-603880, https://www.sec.gov/Archives/edgar/data/1411158/000119312516603880/d319707dsc14d9.htm | acquirer, merger agreement date, deal consideration target, filing URL, background filing target |
| MDVN | RHC-0006-ACQUIRED-MDVN | PARTIAL | 2016-08-22, accession 0001193125-16-686961, https://www.sec.gov/Archives/edgar/data/1011835/000119312516686961/d245915d8k.htm | SC 14D9, 2016-08-30, accession 0001193125-16-696911, https://www.sec.gov/Archives/edgar/data/1011835/000119312516696911/d234696dsc14d9.htm | acquirer, merger agreement date, deal consideration target, filing URL, background filing target |

## Rows Added

| ticker | evidence rows |
| --- | --- |
| NPSP | RHC-0001-ACQUIRED-NPSP-SRC-001, RHC-0001-ACQUIRED-NPSP-SRC-002 |
| PCYC | RHC-0002-ACQUIRED-PCYC-SRC-001, RHC-0002-ACQUIRED-PCYC-SRC-002 |
| ZSPH | RHC-0003-ACQUIRED-ZSPH-SRC-001, RHC-0003-ACQUIRED-ZSPH-SRC-002 |
| ANAC | RHC-0004-ACQUIRED-ANAC-SRC-001, RHC-0004-ACQUIRED-ANAC-SRC-002 |
| MDVN | RHC-0006-ACQUIRED-MDVN-SRC-001, RHC-0006-ACQUIRED-MDVN-SRC-002 |

## Structured PARTIAL Promotion

All five target cases now have rows in `cases_partial.csv` with `data_quality=PARTIAL`, `signal_type=MERGER_AGREEMENT`, `process_state_at_signal=SIGNED`, and `signal_quality=MERGER`. No row is `VERIFIED` or `CALIBRATION_ELIGIBLE`.

## Remaining Evidence Gaps

Each promoted case still needs:

- Background section extraction for prior process signals, including strategic alternatives, banker/advisor role, prior outreach, competing bids, activist involvement, and ROFR/ROFN or option rights.
- Prior process signal review before `had_prior_process_signal` can be finalized.
- Premium extraction where disclosed in the tender recommendation or transaction filing.
- Observation date selection review if background extraction finds an earlier public process signal.
- Price-window verification after the final observation date is selected.

## EDGAR And Tool Blockers

- The current ticker lookup path misses delisted tickers in SEC company ticker JSON, so CIK-based SEC submissions were used for this pass.
- The earlier EDGAR full-text/entity path returned server errors or no usable results for at least one delisted ticker lookup.
- CIK-based SEC submissions and archive filing URLs worked for all five target cases.
