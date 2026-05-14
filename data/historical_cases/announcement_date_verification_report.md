# Announcement Date Verification Report

Generated: 2026-05-14

---

## Summary

Verified all 22 MEDIUM-confidence acquisition announcement dates against SEC EDGAR 8-K filings (or 6-K for foreign issuers). EDGAR full-text search API used via `efts.sec.gov` with `User-Agent: jack@bscapital.io`.

| Outcome | Count |
| --- | --- |
| MEDIUM → HIGH, date confirmed correct | 10 |
| MEDIUM → HIGH, date corrected | 12 |
| MEDIUM → HIGH, date corrected (DOVA — 1 day shift from prior backfill) | 1 |
| MISSING (PTLA) — no change | 1 |
| **Total MEDIUM cases reviewed** | **23** |

After verification: **22 of 23 MEDIUM cases upgraded to HIGH**. 1 remains MISSING (PTLA).

---

## Confidence Counts — Before vs After

| Confidence | Before Verification | After Verification |
| --- | --- | --- |
| HIGH (pre-existing) | 15 | 15 |
| HIGH (upgraded from MEDIUM) | 0 | 22 |
| MEDIUM | 22 | 0 |
| MISSING | 1 | 1 |
| **Total** | **38** | **38** |

All MEDIUM cases are now resolved. The only remaining uncertainty is PTLA.

---

## Confirmed Correct Dates (10 cases — MEDIUM → HIGH, no date change)

| Ticker | Date | EDGAR Accession | Period | Note |
| --- | --- | --- | --- | --- |
| BOLD | 2019-12-02 | 0001193125-19-304554 | 2019-12-02 | Confirmed exact match |
| FTSV | 2020-03-02 | 0001193125-20-057799 | 2020-03-01 | Period = Sunday; announced Monday 3/2 |
| MNTA | 2020-08-19 | 0001104659-20-096687 | 2020-08-19 | Confirmed exact match |
| MYOK | 2020-10-05 | 0001193125-20-263220 | 2020-10-03 | Period = Saturday; announced Monday 10/5 |
| PGNX | 2019-10-01 | 0001193125-19-260332 | 2019-10-01 | Confirmed; also resolves seed year error (2020 → 2019) |
| PRNB | 2020-08-16 | 0001193125-20-221651 | 2020-08-16 | Confirmed exact match |
| PRVL | 2020-12-14 | 0001193125-20-317624 | 2020-12-14 | Confirmed exact match |
| ADMS | 2021-10-11 | 0001104659-21-124979 | 2021-10-10 | Period = Sunday; announced Monday 10/11 (Columbus Day — equity markets open) |
| GWPH | 2021-02-03 | 0001193125-21-026563 | 2021-02-03 | Confirmed; foreign issuer filed as 8-K (not 6-K) |
| TRIL | 2021-08-23 | 0001104659-21-108359 | 2021-08-20 | Period = Friday; 8-K filed Monday 8/23 = announcement date |

---

## Date Corrections Applied (13 cases — MEDIUM → HIGH, date changed)

| Ticker | Old Date | New Date | Days Off | EDGAR Accession | Period | Error Type |
| --- | --- | --- | --- | --- | --- | --- |
| ACHN | 2020-01-10 | **2020-01-15** | 5 late | 0001193125-20-008486 | 2020-01-15 | Off by 5 days |
| DERM | 2020-01-13 | **2020-01-10** | 3 early | 0001564590-20-000689 | 2020-01-10 | Off by 3 days |
| DOVA | 2019-10-01 | **2019-09-30** | 1 early | 0001104659-19-051883 | 2019-09-30 | Original 8-K filed same-day as period; earliest evidence is Sept 30 |
| DRNA | 2021-11-02 | **2021-11-17** | 15 late | 0001193125-21-333251 | 2021-11-17 | Off by 15 days |
| FPRX | 2021-03-03 | **2021-03-04** | 1 late | 0001193125-21-068593 | 2021-03-04 | Off by 1 day |
| PAND | 2021-02-23 | **2021-02-24** | 1 late | 0001193125-21-055823 | 2021-02-24 | Off by 1 day |
| VIE | 2021-02-08 | **2021-01-31** | 8 early | 0001193125-21-023686 | 2021-01-31 | Off by 8 days |
| XLRN | 2021-09-28 | **2021-09-29** | 1 late | 0001104659-21-120991 | 2021-09-29 | Off by 1 day |
| ATRS | 2022-03-28 | **2022-04-12** | 15 late | 0001140361-22-014261 | 2022-04-12 | Off by 15 days |
| AVEO | 2022-11-03 | **2022-10-18** | 16 early | 0001193125-22-264065 | 2022-10-18 | Off by 16 days; EDGAR name is "AVEO Pharmaceuticals" not "AVEO Oncology" |
| BHVN | 2022-05-10 | **2022-05-09** | 1 early | 0001689813-22-000034 | 2022-05-09 | Off by 1 day |
| CCXI | 2022-08-02 | **2022-08-03** | 1 late | 0001193125-22-211865 | 2022-08-03 | Off by 1 day |
| CMPI | 2022-01-19 | **2022-04-18** | 89 late | 0001193125-22-108777 | 2022-04-18 | **Critical: off by 89 days**; entire prior-signal window would have been wrong |

### Critical Issues

- **CMPI** (Checkmate Pharmaceuticals): 89-day error. Training knowledge had January 2022; EDGAR confirms April 18, 2022. Pfizer filed the merger 8-K in April — the January date appears to have been a rumor or letter-of-intent date. Using the old date would have included 3 months of post-announcement filings in the "prior signal" window.
- **AVEO**: 16-day error. Also note that AVEO files on EDGAR as "AVEO Pharmaceuticals" (CIK 0001325879) — searching "AVEO Oncology" returns no results.
- **DRNA** and **ATRS**: Both 15-day errors — consistent pattern of training knowledge being ~2 weeks early.

---

## PTLA — Still MISSING

- EDGAR full-text search for `"Portola Pharmaceuticals" "agreement and plan of merger"` (8-K form, 2020-01-01 to 2022-12-31) returned **no merger 8-K**.
- Only results: S-8 POS filings from July 2020 (routine equity plan amendments during financial distress period).
- Seed data suggests "Alexion deal ~2021; ~$1.41B; andexanet alfa (Andexxa)" but this deal cannot be confirmed from EDGAR full-text search.
- **Hypothesis**: The Portola/Alexion deal may have been structured as an asset acquisition (of andexanet alfa), not a public-company merger. An asset deal would not generate a merger 8-K with "agreement and plan of merger" language. Need to search for "asset purchase agreement" or "license agreement" forms.
- **Next action**: Search EDGAR for PTLA 8-K with "asset purchase" language 2020-2021, or verify whether Alexion actually acquired Portola as a company vs. licensing/buying the andexanet alfa asset.

---

## Methodology Notes

- All dates verified via EDGAR EFTS full-text search API (`efts.sec.gov/LATEST/search-index`) using `User-Agent: jack@bscapital.io`.
- `period_ending` field in EDGAR JSON = date the merger agreement was executed (triggering event).
- For weekend/holiday deals: `period_ending` = signing date; announcement date = next business day when markets opened. Applied to FTSV, MYOK, ADMS, TRIL.
- `file_date` = date the 8-K was filed (typically 1 business day after announcement).
- Confidence upgraded to HIGH only when `period_ending` directly confirmed the date — or when the filing date and period both converged on the same date.
- GWPH (foreign issuer / GW Pharmaceuticals): searched for 6-K first; found merger announcement filed as 8-K instead. 8-K confirmed.
- TRIL (Canadian foreign issuer): searched for 8-K; found merger announcement filed as 8-K (not SC TO). Filing confirmed.
- AVEO: initial search for "AVEO Oncology" returned no results. Resolved by searching CIK 0001325879 (registered as "AVEO Pharmaceuticals").

---

## Impact on Prior-Signal Windows

Cases where the corrected date materially shifts the prior-signal cutoff (>3 days off):

| Ticker | Old Cutoff | New Cutoff | Impact |
| --- | --- | --- | --- |
| CMPI | 2022-01-19 | 2022-04-18 | **Critical** — 89-day window error; must recollect any prior filings if collected |
| AVEO | 2022-11-03 | 2022-10-18 | 16-day window shift |
| DRNA | 2021-11-02 | 2021-11-17 | 15-day window shift |
| ATRS | 2022-03-28 | 2022-04-12 | 15-day window shift |
| VIE | 2021-02-08 | 2021-01-31 | 8-day window shift; use earlier cutoff (more conservative) |
| ACHN | 2020-01-10 | 2020-01-15 | 5-day window shift |
| DERM | 2020-01-13 | 2020-01-10 | 3-day window shift; use earlier cutoff |

None of these cases have had pre-announcement filing collection run yet (all are in NEEDS_MANUAL_REVIEW), so no prior work is invalidated. Apply corrected dates before running any pre-announcement filing collection.

---

## Files Updated

- `data/historical_cases/acquisition_announcement_dates.csv` — 22 rows updated (date and/or confidence), 1 row unchanged (PTLA)
- `data/historical_cases/announcement_date_verification_issues.csv` — NEW: 13 rows with specific date error details
- `data/historical_cases/acquisition_prior_signal_batch_results.csv` — rerun; counts unchanged (status driven by signal adjudication, not date confidence)
- `data/historical_cases/case_packets/` — regenerated (50 packets, deterministic)
