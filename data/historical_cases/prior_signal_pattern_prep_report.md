# Prior Signal Pattern Prep

Run date: 2026-05-14

Read-only analysis prep for the 50-case acquisition prior-signal study. This does not change classifications, case data, packets, scanner logic, or dashboard logic.

## Executive Summary

- Current distribution: DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE=33, POSSIBLE_SIGNAL_NEEDS_REVIEW=6, PRIVATE_BACKGROUND_ONLY=5, TRUE_PUBLIC_PRIOR_SIGNAL=3, RIGHTS_LANGUAGE_ONLY=1, ASSET_SPECIFIC_RIGHTS_ONLY=1, DATE_MISSING=1.
- True public prior signals currently cluster around explicit public acquisition pressure: unsolicited proposals, competing/superior proposals, and public sale-process media reports.
- The clearest false-positive families are generic rights language, asset-specific rights, and private transaction-background narratives.
- Cases still most likely to change the study conclusion: MYOK, PRNB, ADMS.
- Treat all findings as prep for human/Claude review, not final adjudication.

## Current 50-Case Distribution by Status

| Status | Cases |
| --- | --- |
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 33 |
| POSSIBLE_SIGNAL_NEEDS_REVIEW | 6 |
| PRIVATE_BACKGROUND_ONLY | 5 |
| TRUE_PUBLIC_PRIOR_SIGNAL | 3 |
| RIGHTS_LANGUAGE_ONLY | 1 |
| ASSET_SPECIFIC_RIGHTS_ONLY | 1 |
| DATE_MISSING | 1 |

## True-Signal Pattern Table

| Ticker | Category | Earliest signal | Days before | Filing types | Reason |
| --- | --- | --- | --- | --- | --- |
| MDVN | unsolicited_proposal | 2016-04-28 | 116 | 10-K|8-K|DEF 14A|10-Q|SC 14D9 | Adjudicated as public prior signal; category inferred as unsolicited_proposal. Earliest signal was 116 days before announcement. |
| DMTX | superior_proposal | 2017-08-25 | 39 | DEF 14A|8-K|10-Q|10-K | Adjudicated as public prior signal; category inferred as superior_proposal. Earliest signal was 39 days before announcement. |
| TSRO | sale_process_media_report | 2018-11-16 | 17 | NEWS|8-K/A|SC 14D9 | Adjudicated as public prior signal; category inferred as sale_process_media_report. Earliest signal was 17 days before announcement. |

## False-Positive Pattern Table

| Ticker | Status | Category | Keywords | Reason |
| --- | --- | --- | --- | --- |
| CPXX | RIGHTS_LANGUAGE_ONLY | rights_language | right of first refusal | Rights-language hit appears legal or generic rather than whole-company process evidence. |
| TBRA | PRIVATE_BACKGROUND_ONLY | private_background_only |  | Signal appears in transaction-background narrative but was not public before announcement. |
| ARIA | PRIVATE_BACKGROUND_ONLY | private_background_only |  | Signal appears in transaction-background narrative but was not public before announcement. |
| KITE | PRIVATE_BACKGROUND_ONLY | private_background_only |  | Signal appears in transaction-background narrative but was not public before announcement. |
| BIVV | PRIVATE_BACKGROUND_ONLY | private_background_only |  | Signal appears in transaction-background narrative but was not public before announcement. |
| JUNO | PRIVATE_BACKGROUND_ONLY | private_background_only |  | Signal appears in transaction-background narrative but was not public before announcement. |
| ARRY | ASSET_SPECIFIC_RIGHTS_ONLY | asset_specific_rights | right of first refusal | Rights signal appears limited to an asset or program, not a company-level sale process. |

## Possible-Signal Review Priority Table

| Ticker | Category | Edge value | Earliest signal | Days before | Why review |
| --- | --- | --- | --- | --- | --- |
| MYOK | sale_process_media_report | HIGH |  |  | Still needs manual review; current keyword basis: unclear. |
| ADMS | unclear | MEDIUM |  |  | Still needs manual review; current keyword basis: unclear. |
| PRNB | unclear | MEDIUM |  |  | Still needs manual review; current keyword basis: unclear. |
| FTSV | rights_language | LOW |  |  | Still needs manual review; current keyword basis: unclear. |
| TRIL | rights_language | LOW |  |  | Still needs manual review; current keyword basis: unclear. |
| XLRN | rights_language | LOW |  |  | Still needs manual review; current keyword basis: unclear. |

## Signal Timing Table

| Ticker | Status | Category | Signal date | Announcement | Days before |
| --- | --- | --- | --- | --- | --- |
| ARRY | ASSET_SPECIFIC_RIGHTS_ONLY | asset_specific_rights | 2018-02-06 | 2019-06-17 | 496 |
| MDVN | TRUE_PUBLIC_PRIOR_SIGNAL | unsolicited_proposal | 2016-04-28 | 2016-08-22 | 116 |
| CPXX | RIGHTS_LANGUAGE_ONLY | rights_language | 2016-03-23 | 2016-05-31 | 69 |
| DMTX | TRUE_PUBLIC_PRIOR_SIGNAL | superior_proposal | 2017-08-25 | 2017-10-03 | 39 |
| TSRO | TRUE_PUBLIC_PRIOR_SIGNAL | sale_process_media_report | 2018-11-16 | 2018-12-03 | 17 |

## Filing / Source Type Usefulness Ranking

| Filing type | Lookback rows | Possible hits | True rows | Non-true rows | Score |
| --- | --- | --- | --- | --- | --- |
| 8-K | 286 | 13 | 12 | 1 | 72 |
| 10-Q | 57 | 3 | 1 | 2 | 6 |
| NEWS | 0 | 0 | 1 | 0 | 5 |
| 10-K | 16 | 0 | 0 | 0 | 0 |
| DEF 14A | 18 | 0 | 0 | 0 | 0 |
| SC 13D | 5 | 0 | 0 | 0 | 0 |
| SC 13D/A | 29 | 0 | 0 | 0 | 0 |
| UNKNOWN | 0 | 0 | 0 | 6 | -6 |

## Public Media Reports Before Announcement

| Ticker | Status | Category | Reason |
| --- | --- | --- | --- |
| TSRO | TRUE_PUBLIC_PRIOR_SIGNAL | sale_process_media_report | Adjudicated as public prior signal; category inferred as sale_process_media_report. Earliest signal was 17 days before announcement. |

## SEC-Filed Signals Before Announcement

| Ticker | Status | Category | Earliest signal | Filing types |
| --- | --- | --- | --- | --- |
| CPXX | RIGHTS_LANGUAGE_ONLY | rights_language | 2016-03-23 | 8-K|10-K|DEF 14A|10-Q|SC 13D/A |
| MDVN | TRUE_PUBLIC_PRIOR_SIGNAL | unsolicited_proposal | 2016-04-28 | 10-K|8-K|DEF 14A|10-Q|SC 14D9 |
| DMTX | TRUE_PUBLIC_PRIOR_SIGNAL | superior_proposal | 2017-08-25 | DEF 14A|8-K|10-Q|10-K |
| ARRY | ASSET_SPECIFIC_RIGHTS_ONLY | asset_specific_rights | 2018-02-06 | 8-K|10-Q|10-K|DEF 14A |

## Early Live-Scanner Rule Recommendations

1. Elevate explicit public unsolicited proposal language when it appears before a signed merger announcement, especially in 8-Ks, 10-Qs, and public communications filed with SEC.
2. Treat superior-proposal language as high-value only when the filing date precedes the final acquisition announcement and source text confirms public availability.
3. Separate generic rights language from company-level transaction rights. Generic legal representations should not count as prior process evidence.
4. Separate asset-specific rights from whole-company acquisition rights. Asset or subsidiary rights should not clear the company-level process gate.
5. Do not count private background-only negotiations as public prior signals unless the pre-announcement source itself was public.
6. Keep media reports in a distinct category from SEC filings. Public sale-process reports can matter, but source availability and date must be verified.
7. Require Item 4 / exact-source context before treating activist or 13D pressure as sale-process evidence.

## Five Most Important Open Research Questions

1. Among the six possible-signal cases, how many are genuinely public before announcement versus private background-only?
2. Do media-reported sale processes produce materially different timing and reliability than SEC-filed acquisition proposals?
3. Are rights-language false positives mostly generic legal representations, or are any company-level ROFR/ROFN rights being missed?
4. Which filing types create the best precision: 8-K, 10-Q, Schedule 14D-9, proxy/tender filings, or news reports?
5. Does signal age matter enough to create freshness thresholds for the live scanner?

## Suggested Prompt for Claude After the 6-Case Adjudication Finishes

```text
Using the finalized 50-case acquisition prior-signal batch, review prior_signal_pattern_prep_report.md and prior_signal_pattern_prep.csv. Confirm which pattern claims are still valid after the six POSSIBLE_SIGNAL_NEEDS_REVIEW cases were adjudicated. Update the interpretation of true public prior signals versus false positives, identify any live-scanner rule changes that are now evidence-backed, and separate findings that are statistically suggestive from findings that are only anecdotal. Do not mark any cases VERIFIED or CALIBRATION_ELIGIBLE.
```

## Outputs

- `data/historical_cases/prior_signal_pattern_prep.csv`
- `data/historical_cases/prior_signal_pattern_prep_report.md`
