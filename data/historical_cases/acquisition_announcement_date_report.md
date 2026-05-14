# Acquisition Announcement Date Backfill Report

Generated: 2026-05-14

## Summary

This report documents the backfill pass for the 25 DATE_MISSING cases in the 50-case acquisition prior-signal batch.

- DATE_MISSING cases before backfill: **25**
- Dates backfilled (any confidence): **24**
- Remaining MISSING after backfill: **1** (PTLA)
- HIGH confidence dates added: **2** (FLXN, DOVA — source_evidence.csv confirmation)
- MEDIUM confidence dates added: **22** (training knowledge; SEC verification required before cutoff use)
- MISSING confidence (no date): **1** (PTLA)

## Confidence Breakdown

| Confidence | Count | Source |
| --- | --- | --- |
| HIGH | 2 | SEC archive evidence in source_evidence.csv |
| MEDIUM | 22 | Training knowledge; acquirer and approximate date known; SEC verification required |
| MISSING | 1 | Cannot confirm date; must open EDGAR directly |

## HIGH Confidence Backfills

### FLXN — Flexion Therapeutics
- **Date:** 2021-10-11
- **Acquirer:** Pacira BioSciences
- **Source:** source_evidence.csv entry FLXN-2021-001-SRC-002; 8-K acc 0001104659-21-124870; period of report 2021-10-11; acquirer confirmed.
- **Action:** Ready for prior-signal search cutoff.

### DOVA — Dova Pharmaceuticals
- **Date:** 2019-10-01
- **Acquirer:** Swedish Orphan Biovitrum AB (Sobi)
- **Source:** source_evidence.csv entry DOVA-2021-001-SRC-002; 8-K acc 0001104659-19-052965; period of report 2019-09-30; acquirer confirmed. Note: seed had CRITICAL year error (2021 vs actual 2019).
- **Action:** Verify exact press release date; use as prior-signal search cutoff after verification.

## MEDIUM Confidence Backfills (22 cases)

All 22 cases below use training knowledge for the acquirer and approximate announcement date. Each must be verified against a merger 8-K (or 6-K for foreign issuers) on SEC EDGAR before the date is used as a prior-signal search cutoff.

| Case ID | Ticker | Company | Date Backfilled | Acquirer | Notes |
| --- | --- | --- | --- | --- | --- |
| RHC-0026-ACQUIRED-ACHN | ACHN | Achillion Pharmaceuticals | 2020-01-10 | Alexion Pharmaceuticals | ~$930M; ~$6.30/share |
| RHC-0027-ACQUIRED-BOLD | BOLD | Audentes Therapeutics | 2019-12-02 | Astellas Pharma | ~$3B; ~$60/share |
| RHC-0028-ACQUIRED-DERM | DERM | Dermira | 2020-01-13 | Eli Lilly | ~$1.1B; ~$18.75/share |
| RHC-0029-ACQUIRED-FTSV | FTSV | Forty Seven | 2020-03-02 | Gilead Sciences | ~$4.9B; ~$95.50/share |
| RHC-0030-ACQUIRED-MNTA | MNTA | Momenta Pharmaceuticals | 2020-08-19 | Johnson & Johnson | ~$6.5B; ~$52.50/share |
| RHC-0031-ACQUIRED-MYOK | MYOK | MyoKardia | 2020-10-05 | Bristol-Myers Squibb | ~$13.1B; ~$225/share |
| RHC-0032-ACQUIRED-PGNX | PGNX | Progenics Pharmaceuticals | 2019-10-01 | Lantheus Holdings | ~$441M; stock deal; announced ~Oct 2019; closed ~Jun 2020 |
| RHC-0033-ACQUIRED-PRNB | PRNB | Principia Biopharma | 2020-08-16 | Sanofi | ~$3.68B; ~$100/share |
| RHC-0034-ACQUIRED-PRVL | PRVL | Prevail Therapeutics | 2020-12-14 | Eli Lilly | ~$1.04B; ~$22.50 + CVR |
| RHC-0035-ACQUIRED-ADMS | ADMS | Adamas Pharmaceuticals | 2021-10-11 | Supernus Pharmaceuticals | ~$400M; ~$8.10/share |
| RHC-0037-ACQUIRED-DRNA | DRNA | Dicerna Pharmaceuticals | 2021-11-02 | Novo Nordisk | ~$3.3B; ~$38.25/share |
| RHC-0039-ACQUIRED-FPRX | FPRX | Five Prime Therapeutics | 2021-03-03 | Amgen | ~$1.9B; ~$38/share |
| RHC-0040-ACQUIRED-GWPH | GWPH | GW Pharmaceuticals plc | 2021-02-03 | Jazz Pharmaceuticals | ~$7.2B; ~$220/ADS; foreign issuer; may use 6-K |
| RHC-0041-ACQUIRED-PAND | PAND | Pandion Therapeutics | 2021-02-23 | Merck | ~$1.85B; ~$60/share |
| RHC-0043-ACQUIRED-TRIL | TRIL | Trillium Therapeutics | 2021-08-23 | Pfizer | ~$2.26B; ~$18.50/share; foreign issuer (Canadian) |
| RHC-0044-ACQUIRED-VIE | VIE | Viela Bio | 2021-02-08 | Horizon Therapeutics | ~$3.05B; ~$53/share |
| RHC-0045-ACQUIRED-XLRN | XLRN | Acceleron Pharma | 2021-09-28 | Merck | ~$11.5B; ~$180/share |
| RHC-0046-ACQUIRED-ATRS | ATRS | Antares Pharma | 2022-03-28 | Halozyme Therapeutics | ~$960M; ~$5.60/share |
| RHC-0047-ACQUIRED-AVEO | AVEO | AVEO Oncology | 2022-11-03 | LG Chem | ~$566-640M; ~$15/share |
| RHC-0048-ACQUIRED-BHVN | BHVN | Biohaven Pharmaceutical Holding Co. | 2022-05-10 | Pfizer | ~$11.6B; ~$148.50/share; foreign issuer structure |
| RHC-0049-ACQUIRED-CCXI | CCXI | ChemoCentryx | 2022-08-02 | Amgen | ~$3.7B; ~$52/share |
| RHC-0050-ACQUIRED-CMPI | CMPI | Checkmate Pharmaceuticals | 2022-01-19 | Pfizer | ~$2.1B; vidutolimod; ~$10.25/share |

## MISSING — No Date Backfilled

### PTLA — Portola Pharmaceuticals
- **Seed hint:** Alexion Pharmaceuticals; ~$1.41B; andexanet alfa (Andexxa).
- **Problem:** Portola had severe financial difficulties in 2020 and explored strategic alternatives. Cannot confirm from existing sources whether the Alexion merger was announced and on what date. Must open EDGAR directly.
- **Search:** `PTLA "Portola Pharmaceuticals" "agreement and plan of merger" "per share"` in 8-K/SC TO-T forms, 2021-01-01 to 2021-12-31.
- **Action:** PTLA remains DATE_MISSING after this backfill pass.

## Seed Errors Identified

- **DOVA:** resolved_case_candidates.csv listed `likely_outcome_year=2021` but the deal closed in 2019. Source evidence (8-K acc 0001104659-19-052965) confirms 2019-09-30 period of report. The case_id `RHC-0036-ACQUIRED-DOVA` is correctly tagged ACQUIRED but the year in the seed is wrong.
- **PGNX:** resolved_case_candidates.csv lists `likely_outcome_year=2020` (close date). Merger announced approximately October 2019. If verification confirms a 2019 announcement, the seed year needs updating.

## Rules Applied

- Exact dates from SEC archive (HIGH): used directly.
- Dates from training knowledge (MEDIUM): entered as backfill to unblock batch runner; must be verified before cutoff use.
- No date invented: PTLA left MISSING because the exact date and deal structure cannot be confirmed without opening EDGAR.
- Confidence levels follow: HIGH = source-backed exact date; MEDIUM = approximate but from reliable domain knowledge; MISSING = unresolvable without manual EDGAR lookup.
