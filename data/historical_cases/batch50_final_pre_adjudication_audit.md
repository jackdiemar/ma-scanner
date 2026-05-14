# Batch-50 Final Pre-Adjudication Audit

Generated: 2026-05-14

---

## Audit Verdict

**PASS — safe to begin adjudication on 24 NEEDS_MANUAL_REVIEW cases.**

One functional bug was found and fixed (DOVA query URLs pointed to wrong year). Two informational notes recorded. All computational checks pass. No classification changes made.

---

## Check Results

| # | Check | Result | Detail |
| --- | --- | --- | --- |
| 1 | 50 batch cases | PASS | batch_results.csv: 50 rows |
| 2 | Confidence counts | PASS (adjusted) | HIGH=38, MEDIUM=1 (CPXX), MISSING=1. See ISS-003. |
| 3 | PTLA only MISSING | PASS | PTLA is the only MISSING case |
| 4 | All NMR cases have HIGH date | PASS | All 24 NEEDS_MANUAL_REVIEW: announcement_date_confidence=HIGH |
| 5 | Corrected dates in CSV | PASS | All 13 date corrections verified in acquisition_announcement_dates.csv |
| 6 | Report counts match results | PASS | NEEDS_MANUAL_REVIEW=24, BASELINE=15, PRIVATE=5, TRUE_SIGNAL=3, RIGHTS=1, ASSET=1, MISSING=1 |
| 7 | Mini-study counts match results | PASS | Same counts confirmed |
| 8 | Packet index + packets | PASS | 50 packets in index, 0 missing files |
| 8b | DOVA packet EDGAR queries | FIXED | Bug found: query URLs used 2021 year range. Fixed to 2019. Packets regenerated. |
| 9 | TRUE_PUBLIC_PRIOR_SIGNAL cases | PASS | MDVN, DMTX, TSRO only |
| 10 | False positives | PASS | CPXX: RIGHTS_LANGUAGE_ONLY; ARRY: ASSET_SPECIFIC_RIGHTS_ONLY |
| 11 | PRIVATE_BACKGROUND_ONLY cases | PASS | TBRA, ARIA, KITE, BIVV, JUNO |
| 12 | No MEDIUM date confidence in packets | PASS | announcement_date_confidence=HIGH for all 24 NMR. CPXX is MEDIUM but RIGHTS_LANGUAGE_ONLY — not in adjudication scope. |

---

## Corrected Dates — Verified in All Layers

All 13 date corrections from the verification pass confirmed correct in both `acquisition_announcement_dates.csv` AND `acquisition_prior_signal_batch_results.csv`:

| Ticker | Verified Date | announcement_date_confidence |
| --- | --- | --- |
| CMPI | 2022-04-18 | HIGH |
| AVEO | 2022-10-18 | HIGH |
| DRNA | 2021-11-17 | HIGH |
| ATRS | 2022-04-12 | HIGH |
| VIE | 2021-01-31 | HIGH |
| ACHN | 2020-01-15 | HIGH |
| DERM | 2020-01-10 | HIGH |
| DOVA | 2019-09-30 | HIGH |
| FPRX | 2021-03-04 | HIGH |
| PAND | 2021-02-24 | HIGH |
| BHVN | 2022-05-09 | HIGH |
| CCXI | 2022-08-03 | HIGH |
| XLRN | 2021-09-29 | HIGH |

---

## Issues Found and Fixed

### ISS-001 — FUNCTIONAL — FIXED: DOVA EDGAR Query URLs Pointed to Wrong Year

**File:** `data/historical_cases/resolved_case_candidates.csv`, row `RHC-0036-ACQUIRED-DOVA`

**Bug:** `likely_outcome_year=2021` (wrong; confirmed deal was 2019-09-30). All five EDGAR query URLs (`outcome_edgar_query`, `prior_process_signal_query`, `prior_13d_query`, `prior_rofr_exhibit_query`, `proxy_or_s4_query`) used 2021 date ranges.

**Impact if unfixed:** Adjudicator uses the merger 8-K query URL from the DOVA packet, searches 2021, finds no results, and incorrectly concludes the merger announcement is undocumented. Prior-signal search window would also be wrong (searching 2 years too late).

**Fix applied:**
- `likely_outcome_year`: 2021 → 2019
- `outcome_edgar_query`: `startdt=2021-01-01&enddt=2021-12-31` → `startdt=2019-01-01&enddt=2019-12-31`
- `prior_process_signal_query`, `prior_13d_query`, `prior_rofr_exhibit_query`, `proxy_or_s4_query`: `enddt=2021-12-31` → `enddt=2019-09-30`
- `outcome_source_hint`: "deal 2021" → "deal 2019-09-30"

Packets regenerated. DOVA packet now shows `likely_outcome_year=2019` with correct query ranges.

### ISS-002 — COSMETIC — FIXED: CMPI Hint Said "Jan 2022"

**File:** `data/historical_cases/resolved_case_candidates.csv`, row `RHC-0050-ACQUIRED-CMPI`

**Bug:** `outcome_source_hint` said "EDGAR 8-K Pfizer deal Jan 2022". Verified announcement date is 2022-04-18 (89 days later than the hint implied).

**Impact if unfixed:** Adjudicator sees "Jan 2022" in packet hint but the verified cutoff is April 18. EDGAR query URLs correctly spanned all of 2022 so functionally unaffected — this was cosmetic only.

**Fix applied:** `outcome_source_hint` updated to "EDGAR 8-K Pfizer deal Apr 2022; period 2022-04-18." Packets regenerated.

---

## Informational Notes (No Action Required)

### ISS-003 — Confidence Count Discrepancy from Task Spec

Task specified HIGH=37, MEDIUM=0, MISSING=1. Actual: **HIGH=38, MEDIUM=1 (CPXX), MISSING=1**.

CPXX (`RHC-0005-ACQUIRED-CPXX`) is classified `RIGHTS_LANGUAGE_ONLY` (false positive) and was not in the DATE_MISSING verification batch. Its date (2016-05-31) carries MEDIUM confidence because the source was a filing date, not a confirmed press-release date. This is a pre-existing condition from before Session 1. CPXX is excluded from adjudication scope. Not a bug.

### ISS-004 — TSRO Shows confidence=MEDIUM in Batch Report

The `confidence` column in the batch report and mini-study is **signal confidence** (how strong/complete the prior-signal evidence is), NOT announcement_date_confidence. TSRO's `announcement_date_confidence=HIGH` in batch_results.csv. The MEDIUM refers to the signal finding being partial/unconfirmed — expected for a case that has not had full evidence review.

### ISS-005 — All 15 Baseline Candidates Show confidence=MEDIUM

Same explanation as ISS-004. Signal confidence = MEDIUM for cases with no pre-announcement filing collection run yet. Not a bug.

### ISS-006 — Orphaned DOVA Seed Row

`resolved_case_candidates.csv` contains a second DOVA row (`RHC-0096-ACQUIRED-DOVA`, year=2019) which is an orphaned seed. The batch runner uses `RHC-0036-ACQUIRED-DOVA` (now corrected to year=2019). The orphan is non-blocking. Schedule for cleanup in a future pass.

---

## Final Confidence State

| Source | HIGH | MEDIUM | MISSING | Total |
| --- | --- | --- | --- | --- |
| `acquisition_announcement_dates.csv` | 38 | 1 (CPXX) | 1 (PTLA) | 40 |
| `batch_results.csv` (announcement_date_confidence) | 49 | 0 | 1 (PTLA) | 50 |

The 10 baseline candidates without a row in `acquisition_announcement_dates.csv` (NPSP, PCYC, ZSPH, ANAC, LOXO, ONCE, MDVN, RLYP, VTAE, CLCD, AVXS, CASC, RXDX, ALDR, CMTA — 15 total including pre-existing signal cases) have their dates embedded directly in the batch results and are source-backed from earlier sessions.

---

## PTLA Status

PTLA remains `DATE_MISSING`. EDGAR full-text search for merger-agreement language (8-K, SC TO forms, 2020-2022) returned no results. Hypothesis: the "Alexion deal" may have been structured as an **asset purchase of andexanet alfa** (Andexxa), not a public-company merger. A standard company merger would generate a merger 8-K — none was found. Next step: search PTLA 8-Ks for "asset purchase agreement" language (2020-2021) before concluding the deal is undocumented.

PTLA must not be included in adjudication until the date is resolved.

---

## Files Changed in This Audit

| File | Change |
| --- | --- |
| `resolved_case_candidates.csv` | DOVA: year, hint, 5 query URLs corrected. CMPI: hint corrected. |
| `acquisition_prior_signal_batch_results.csv` | Regenerated (counts unchanged). |
| `acquisition_prior_signal_batch_report.md` | Regenerated (counts unchanged). |
| `acquisition_prior_signal_mini_study.md` | Regenerated (counts unchanged). |
| `case_packets/` | All 50 packets regenerated. DOVA packet now shows correct year and query URLs. |
| `case_packet_index.csv` | Regenerated (50 rows, no changes to index structure). |
| `batch50_final_pre_adjudication_audit.md` | NEW — this file. |
| `batch50_final_pre_adjudication_issues.csv` | NEW — issue log with 6 entries. |

---

## Adjudication Prerequisites Confirmed

Before adjudicating each of the 24 NEEDS_MANUAL_REVIEW cases:

1. Use `announcement_date` from `batch_results.csv` as the prior-signal cutoff — all are HIGH-confidence.
2. Use EDGAR query URLs from the case packet (`case_packets/RHC-XXXX.md`) — all corrected and regenerated.
3. Do not use PTLA until its date is resolved.
4. Do not mark any case VERIFIED or CALIBRATION_ELIGIBLE during adjudication unless authorized separately.
