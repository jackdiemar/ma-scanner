# Pre-Announcement Filing Collector Audit

Audit target: `src/historical_case_tools/pre_announcement_filing_collector.py` and the generated `pre_announcement_filing_targets.csv` / `pre_announcement_signal_hits.csv` outputs.

## Conclusion

The collector logic is valid for the workflow purpose: it applies a pre-announcement cutoff, uses the intended target-form search window, ties rows to the expected case/ticker CIKs, and does not count post-announcement proxy background language as prior public signal evidence.

The 16 `POSSIBLE_HIT` rows are safe to adjudicate manually, but they are not all safe to treat as true prior public process signals. MDVN and DMTX are the only strong pre-deal process candidates from this pass. CPXX and ARRY are false-positive risks driven by rights language that appears generic or asset-specific rather than whole-company process evidence.

## Mechanical Checks

- Date cutoff: PASS. All 411 collected target rows with filing dates are strictly before their acquisition announcement date. All 16 possible-hit rows are also strictly before announcement.
- Lookback window: PASS. All collected target rows fall inside the script's `announcement_date - 548 days` through `announcement_date - 1 day` window.
- Proxy/background leakage: PASS. No `DEF 14A` or `DEFM14A` row is labeled `POSSIBLE_HIT`. The 18 pre-announcement `DEF 14A` target rows are labeled `LIKELY_NO_HIT`; no post-announcement merger proxy/background row is present in the hit file.
- Source mapping: PASS for target universe. Hit-row CIKs match expected case mappings: MDVN `1011835`, CPXX `1327467`, DMTX `1592288`, ARRY `1100412`.
- Keyword provenance: PASS with a reporting caveat. Keyword hits are generated from fetched primary/complete SEC submission text, not from source hints. The CSV excerpt is only the first matching context, so not every keyword listed in `keyword_hits` appears inside `excerpt_if_available`.
- No prohibited labels: PASS. The collector outputs do not mark rows `VERIFIED` or `CALIBRATION_ELIGIBLE`.

## Possible Hits Review

| Case | Rows | Audit read |
| --- | ---: | --- |
| MDVN | 9 | Strong. The hits are public pre-announcement Sanofi proposal / rejection / strategic-alternatives filings before the 2016-08-22 acquisition announcement. These are safe to adjudicate as true prior public process signals. |
| DMTX | 4 | Strong. The hits capture the public REGENXBIO merger agreement and later Ultragenyx unsolicited / superior-proposal process before the 2017-10-03 final acquisition announcement. These are safe to adjudicate as true prior public process signals. |
| CPXX | 1 | Likely false positive. The excerpt is legal/financing-style rights language about securities not being issued in violation of preemptive/resale/right-of-first-refusal rights. It does not show whole-company process evidence. |
| ARRY | 2 | Likely false positive or at most low-priority pathway context. The excerpts describe a right of first refusal to acquire the 797 Subsidiary or 797 Assets, which is asset/subsidiary-specific, not a public company-wide process signal. |

## Likely No-Hit Cases

The 11 `LIKELY_NO_HIT` case-level labels are defensible as workflow labels, not as final confirmed no-hit determinations. Each had target-form filings collected and fetched successfully, with no `NEEDS_MANUAL_REVIEW` rows caused by missing filing text.

Counts by likely-no-hit case:

| Case | Ticker | Target filings searched | Audit read |
| --- | --- | ---: | --- |
| RHC-0007-ACQUIRED-RLYP | RLYP | 38 | Defensible target-form no-hit. |
| RHC-0009-ACQUIRED-VTAE | VTAE | 18 | Defensible target-form no-hit. |
| RHC-0011-ACQUIRED-CLCD | CLCD | 7 | Defensible target-form no-hit, but small filing count means manual confidence is naturally lower. |
| RHC-0014-ACQUIRED-AVXS | AVXS | 43 | Defensible target-form no-hit. |
| RHC-0016-ACQUIRED-CASC | CASC | 33 | Defensible target-form no-hit. |
| RHC-0018-ACQUIRED-RXDX | RXDX | 37 | Defensible target-form no-hit. CIK correction to Ignyta is reflected in collected source URLs. |
| RHC-0019-ACQUIRED-ALDR | ALDR | 36 | Defensible target-form no-hit after filtering asset-level Vitaeris/CSL purchase-option language. |
| RHC-0021-ACQUIRED-CMTA | CMTA | 3 | Defensible target-form no-hit, but low filing count means manual confidence is lower. |
| RHC-0022-ACQUIRED-LOXO | LOXO | 34 | Defensible target-form no-hit. |
| RHC-0023-ACQUIRED-NITE | NITE | 2 | Defensible target-form no-hit, but low filing count means manual confidence is lower. |
| RHC-0024-ACQUIRED-ONCE | ONCE | 26 | Defensible target-form no-hit. |

## False-Positive Risks

- Generic rights language can still trip `rofr_rofn`, especially legal representations that mention preemptive, resale, or right-of-first-refusal rights.
- Asset/subsidiary-specific ROFR clauses can look like acquisition-pathway evidence even when they do not relate to a company sale.
- Complete submission text improves recall for 8-K exhibits, but it can also surface agreement boilerplate in exhibits.
- `LIKELY_NO_HIT` means target-form text search found no candidate signal. It should not be treated as `CONFIRMED_NO_HIT`.

## Fixes Needed Before Continuing

No blocker exists for using the collector as a manual adjudication queue.

Recommended before promoting any output into calibration data:

1. Add a `scope` classification for ROFR/ROFN hits: whole-company, asset/subsidiary, financing/boilerplate, or unclear.
2. Add another false-positive filter for securities-law representation phrases such as "preemptive right, resale right, right of first refusal or similar right."
3. Keep CPXX and ARRY out of any true-signal count until manually reviewed.
4. Treat DMTX as the best non-MDVN MDVN-like candidate from this pass.

