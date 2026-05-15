# Batch 51–70 Date Backfill Report

Generated: 2026-05-14

---

## Summary

All 20 Batch 51–70 cases now have EDGAR-verified HIGH-confidence acquisition announcement dates.

| Metric | Value |
|---|---|
| Cases in scope | 20 |
| Dates found | 20 |
| Dates still missing | 0 |
| Confidence | HIGH (all 20) |
| Source type | merger 8-K EDGAR verified (19), merger 6-K EDGAR verified (1) |
| Files updated | acquisition_announcement_dates.csv, source_evidence.csv |
| Queue status after backfill | PENDING_FILING_COLLECTION (all 20) |

---

## Verification Method

For each case:
1. Found company CIK via EDGAR company search (`/cgi-bin/browse-edgar`).
2. Retrieved EDGAR submissions JSON (`data.sec.gov/submissions/CIK{padded}.json`).
3. Located 8-K (or 6-K for BLU) with item **1.01** (Entry into Material Agreement) in the relevant year window.
4. Confirmed by matching merger closing 8-K (items 2.01, 3.01, 3.03, 5.01–5.03) filed approximately 4–14 weeks after.
5. Built EDGAR archive source URL per filing.

All 20 accession numbers verified in EDGAR submissions. No dates were invented or assumed without filing evidence.

---

## EFTS False Hit Corrections

The EDGAR EFTS full-text search returned false early dates for 4 companies because another filer's document mentioned the company name and "agreement and plan of merger" in the same text. Corrected via EDGAR submissions JSON:

| Ticker | EFTS False Date | Correct EDGAR Date | Reason for False Hit |
|---|---|---|---|
| CTIC | 2022-06-22 | 2023-05-10 | Different company's 8-K mentioned CTI BioPharma |
| RETA | 2022-09-23 | 2023-07-31 | Different company's 8-K (GBT) mentioned Reata |
| ALPN | 2023-03-06 | 2024-04-10 | Different company's 8-K mentioned Alpine Immune Sciences |
| ZYNE | 2022-09-02 | 2023-08-14 | Different company's 8-K mentioned Zynerba |

---

## All 20 Dates — EDGAR Verified

| Case ID | Ticker | Company | Announcement Date | Accession | Items | Acquirer Note |
|---|---|---|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM | EPZM | Epizyme, Inc. | 2022-06-27 | 0001193125-22-182030 | 1.01,5.03,7.01,9.01 | Ipsen ~$7.46/share |
| RHC-0052-ACQUIRED-FMTX | FMTX | Forma Therapeutics Holdings, Inc. | 2022-09-01 | 0001193125-22-235789 | 1.01,8.01,9.01 | Novo Nordisk |
| RHC-0053-ACQUIRED-GBT | GBT | Global Blood Therapeutics, Inc. | 2022-08-08 | 0000950157-22-000902 | 1.01,5.03,8.01,9.01 | Pfizer $68.50/share |
| RHC-0054-ACQUIRED-IMGO | IMGO | Imago BioSciences, Inc. | 2022-11-21 | 0001193125-22-289491 | 1.01,8.01,9.01 | Merck $36/share |
| RHC-0055-ACQUIRED-OYST | OYST | Oyster Point Pharma, Inc. | 2022-11-08 | 0001193125-22-280282 | 1.01,9.01 | Viatris |
| RHC-0056-ACQUIRED-SRRA | SRRA | Sierra Oncology, Inc. | 2022-04-13 | 0001193125-22-103561 | 1.01,8.01,9.01 | GSK $55/share |
| RHC-0057-ACQUIRED-TPTX | TPTX | Turning Point Therapeutics, Inc. | 2022-06-03 | 0001193125-22-167430 | 1.01,5.02,9.01 | BMS $76/share |
| RHC-0058-ACQUIRED-BLU | BLU | BELLUS Health Inc. | 2023-04-18 | 0001104659-23-046369 | 6-K | GSK $14.75/share |
| RHC-0059-ACQUIRED-CINC | CINC | CinCor Pharma, Inc. | 2023-01-09 | 0001193125-23-004258 | 1.01,5.02,8.01,9.01 | AstraZeneca |
| RHC-0060-ACQUIRED-CTIC | CTIC | CTI BioPharma Corp | 2023-05-10 | 0001193125-23-140076 | 1.01,5.03,8.01,9.01 | SOBI |
| RHC-0061-ACQUIRED-DICE | DICE | DICE Therapeutics, Inc. | 2023-06-20 | 0001193125-23-169553 | 1.01,8.01,9.01 | Eli Lilly $48/share |
| RHC-0062-ACQUIRED-HARP | HARP | Harpoon Therapeutics, Inc. | 2024-01-08 | 0001193125-24-003927 | 1.01,5.02,7.01,9.01 | Acquirer TBD* |
| RHC-0063-ACQUIRED-ISEE | ISEE | IVERIC bio, Inc. | 2023-05-01 | 0001104659-23-053477 | 1.01,5.03,8.01,9.01 | Astellas $40/share |
| RHC-0064-ACQUIRED-RETA | RETA | Reata Pharmaceuticals, Inc. | 2023-07-31 | 0001193125-23-198543 | 1.01,8.01,9.01 | Biogen $172.50/share |
| RHC-0066-ACQUIRED-ZYNE | ZYNE | Zynerba Pharmaceuticals, Inc. | 2023-08-14 | 0001104659-23-090913 | 1.01,5.02,7.01,9.01 | Acquirer TBD* |
| RHC-0067-ACQUIRED-ALPN | ALPN | Alpine Immune Sciences, Inc. | 2024-04-10 | 0001193125-24-091936 | 1.01,8.01,9.01 | Vertex $65/share |
| RHC-0068-ACQUIRED-AMAM | AMAM | Ambrx Biopharma Inc. | 2024-01-08 | 0001193125-24-003916 | 1.01,7.01,9.01 | J&J |
| RHC-0069-ACQUIRED-CBAY | CBAY | CymaBay Therapeutics, Inc. | 2024-02-12 | 0001193125-24-031185 | 1.01,5.03,7.01,9.01 | Gilead $32.50/share |
| RHC-0070-ACQUIRED-CERE | CERE | Cerevel Therapeutics Holdings, Inc. | 2023-12-07 | 0001193125-23-290340 | 1.01,7.01,8.01,9.01 | AbbVie $45/share |
| RHC-0071-ACQUIRED-DCPH | DCPH | Deciphera Pharmaceuticals, Inc. | 2024-04-29 | 0001193125-24-119762 | 1.01,8.01,9.01 | ONO $25.60/share |

*Acquirer identity not recorded — EDGAR date confirmed; acquirer name should be verified from the 8-K text before annotation.

---

## HARP Date Discrepancy

HARP (Harpoon Therapeutics) is listed in source data as `likely_outcome_year=2023`, but EDGAR submissions confirm the merger agreement (item 1.01) was filed **2024-01-08**, with closing on 2024-03-11. The 2023 outcome year in resolved_case_candidates.csv may be a data entry approximation. The EDGAR-verified announcement date is 2024-01-08.

---

## BLU (BELLUS Health) — Foreign Private Issuer

BELLUS Health is a Canadian company (files 6-K, not 8-K). The merger announcement date is taken from the 6-K exhibit 99.1 filed 2023-04-18, which contains the press release: "GSK reaches agreement to acquire... BELLUS Health" at US$14.75/share. The source evidence row uses evidence_type=6K_MERGER.

---

## Files Changed

| File | Change |
|---|---|
| `data/historical_cases/acquisition_announcement_dates.csv` | +20 rows (RHC-0051 through RHC-0071, skipping 0065) |
| `data/historical_cases/source_evidence.csv` | +20 rows (one SRC-001 per case) |
| `data/historical_cases/batch_51_70_date_prefill_queue.csv` | Regenerated: 0 cases need backfill, 20 date confirmed |
| `data/historical_cases/batch_51_70_date_prefill_report.md` | Regenerated |
| `data/historical_cases/batch_51_70_exception_queue.csv` | Regenerated: all 20 PENDING_FILING_COLLECTION |
| `data/historical_cases/batch_51_70_exception_queue_report.md` | Regenerated |
| `data/historical_cases/batch_51_70_source_evidence_draft.csv` | Regenerated: 0 draft rows (no BLOCKED or P1–P4 cases) |
| `data/historical_cases/batch_51_70_source_evidence_draft_report.md` | Regenerated |

---

## Queue Status After Backfill

All 20 cases: **PENDING_FILING_COLLECTION**

The blocker (missing announcement dates) is cleared. Filing collection can now begin.

### Next Step

Run the pre-announcement filing collector for all 20 cases:
```
python3 src/historical_case_tools/pre_announcement_filing_collector.py --start 51 --limit 20
```

After filing collection, re-run:
```
python3 src/historical_case_tools/exception_queue_builder.py --start 51 --limit 20
python3 src/historical_case_tools/source_evidence_autofill.py
```

Cases with P1 or P2 hits will then surface for manual adjudication.

---

## Rules Followed

- No cases adjudicated.
- No case classified as TRUE_PUBLIC_PRIOR_SIGNAL.
- No case marked VERIFIED or CALIBRATION_ELIGIBLE.
- First-50 classifications not touched.
- No speculative dates — all 20 from EDGAR submissions item 1.01 confirmation.
- EFTS false hits corrected by verifying against company-specific submission history.
