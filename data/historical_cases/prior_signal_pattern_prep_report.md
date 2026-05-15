# Prior Signal Pattern Prep

Run date: 2026-05-14 (final — all 50 cases adjudicated)

Read-only analysis prep for the 50-case acquisition prior-signal study. This does not change classifications, case data, packets, scanner logic, or dashboard logic.

## Executive Summary

- Current distribution: DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE=35, PRIVATE_BACKGROUND_ONLY=8, TRUE_PUBLIC_PRIOR_SIGNAL=3, ASSET_SPECIFIC_RIGHTS_ONLY=2, RIGHTS_LANGUAGE_ONLY=1, DATE_MISSING=1.
- True public prior signals currently cluster around explicit public acquisition pressure: unsolicited proposals, competing/superior proposals, and public sale-process media reports.
- The clearest false-positive families are generic rights language, asset-specific rights, and private transaction-background narratives.
- All 6 POSSIBLE_SIGNAL_NEEDS_REVIEW cases resolved: 3 to PRIVATE_BACKGROUND_ONLY (FTSV, PRNB, TRIL), 2 to DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE (MYOK, ADMS), 1 to ASSET_SPECIFIC_RIGHTS_ONLY (XLRN). True-signal count unchanged.
- True-positive rate: 3/50 (6%). Baseline (no confirmed public signal): 35/50 (70%). Private-background-only: 8/50 (16%).

## Current 50-Case Distribution by Status

| Status | Cases |
| --- | --- |
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 35 |
| PRIVATE_BACKGROUND_ONLY | 8 |
| TRUE_PUBLIC_PRIOR_SIGNAL | 3 |
| ASSET_SPECIFIC_RIGHTS_ONLY | 2 |
| RIGHTS_LANGUAGE_ONLY | 1 |
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
| FTSV | PRIVATE_BACKGROUND_ONLY | private_background_only |  | Signal appears in transaction-background narrative but was not public before announcement. |
| PRNB | PRIVATE_BACKGROUND_ONLY | private_background_only |  | Signal appears in transaction-background narrative but was not public before announcement. |
| TRIL | PRIVATE_BACKGROUND_ONLY | private_background_only |  | Signal appears in transaction-background narrative but was not public before announcement. |
| XLRN | ASSET_SPECIFIC_RIGHTS_ONLY | asset_specific_rights |  | Rights signal appears limited to an asset or program, not a company-level sale process. |

## Possible-Signal Review Priority Table

| Ticker | Category | Edge value | Earliest signal | Days before | Why review |
| --- | --- | --- | --- | --- | --- |
| None |  |  |  |  |  |

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

## Research Questions — Answered After Final Adjudication

**1. Among the six possible-signal cases, how many were genuinely public before announcement?**
Zero. FTSV, PRNB, and TRIL were private-background-only. MYOK and ADMS were baseline candidates with no confirmed public process disclosure. XLRN had an asset-specific right unconnected to the actual acquirer (Merck). The true-signal count did not increase.

**2. Do media-reported sale processes produce materially different timing than SEC-filed acquisition proposals?**
In this batch, the media-sourced signal (TSRO, 17 days before) arrived later than the two SEC-filed signals (DMTX, 39 days; MDVN, 116 days). Directionally consistent with the hypothesis that media reports break at a later stage than SEC-filed ongoing proposals. Sample size (n=3 total) is too small to treat as statistically confirmed.

**3. Are rights-language false positives mostly generic representations, or are company-level ROFR/ROFN rights being missed?**
All confirmed rights-language cases (CPXX, ARRY, XLRN) were generic legal representations or asset-specific rights. No company-level ROFR/ROFN was identified in this batch. Evidence is consistent with the rule: generic and asset-specific rights are noise until scope is confirmed as company-level.

**4. Which filing types produce the best precision?**
8-K has the highest score by a wide margin (score=72 vs. 10-Q=6, NEWS=5). SC 14D-9 and proxy filings are post-announcement and cannot be prior signals. DEF 14A, 10-K, and SC 13D/A produced zero true signals in this batch. Prioritize 8-K, use 10-Q as secondary, require extra scope verification for 10-K/DEF 14A ROFR hits.

**5. Does signal age matter enough to create freshness thresholds?**
True signals ranged from 17 to 116 days before announcement. ARRY's asset-specific right was 496 days before. A lookback window capped at 365 days captures all 3 true signals while excluding clearly stale rights noise. Recommend treating rights-language hits older than 365 days with increased skepticism in the live scanner.

## Outputs

- `data/historical_cases/prior_signal_pattern_prep.csv`
- `data/historical_cases/prior_signal_pattern_prep_report.md`
