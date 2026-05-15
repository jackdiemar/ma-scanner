# Batch 51–70 Filing Collection Report

Generated: 2026-05-15

---

## Summary

| Metric | Value |
|---|---|
| Cases in scope | 20 |
| Total filing target rows collected | 509 |
| Possible signal hit rows | 21 |
| Possible-hit cases | 13 |
| No-hit cases | 7 |
| Blocked / source errors | 0 |
| Malformed rows | 0 |
| Cases remaining PENDING_FILING_COLLECTION | 0 |

All 20 cases promoted out of PENDING_FILING_COLLECTION.

---

## Filing Counts by Ticker

| Ticker | Case ID | Announcement Date | Filings Collected | POSSIBLE_HIT Rows |
|---|---|---|---|---|
| EPZM | RHC-0051-ACQUIRED-EPZM | 2022-06-27 | 30 | 1 |
| FMTX | RHC-0052-ACQUIRED-FMTX | 2022-09-01 | 28 | 4 |
| GBT | RHC-0053-ACQUIRED-GBT | 2022-08-08 | 42 | 1 |
| IMGO | RHC-0054-ACQUIRED-IMGO | 2022-11-21 | 32 | 1 |
| OYST | RHC-0055-ACQUIRED-OYST | 2022-11-08 | 26 | 3 |
| SRRA | RHC-0056-ACQUIRED-SRRA | 2022-04-13 | 33 | 1 |
| TPTX | RHC-0057-ACQUIRED-TPTX | 2022-06-03 | 36 | 1 |
| BLU | RHC-0058-ACQUIRED-BLU | 2023-04-18 | 0 | 0 |
| CINC | RHC-0059-ACQUIRED-CINC | 2023-01-09 | 18 | 3 |
| CTIC | RHC-0060-ACQUIRED-CTIC | 2023-05-10 | 22 | 0 |
| DICE | RHC-0061-ACQUIRED-DICE | 2023-06-20 | 27 | 1 |
| HARP | RHC-0062-ACQUIRED-HARP | 2024-01-08 | 28 | 0 |
| ISEE | RHC-0063-ACQUIRED-ISEE | 2023-05-01 | 31 | 0 |
| RETA | RHC-0064-ACQUIRED-RETA | 2023-07-31 | 24 | 1 |
| ZYNE | RHC-0066-ACQUIRED-ZYNE | 2023-08-14 | 28 | 2 |
| ALPN | RHC-0067-ACQUIRED-ALPN | 2024-04-10 | 29 | 1 |
| AMAM | RHC-0068-ACQUIRED-AMAM | 2024-01-08 | 6 | 1 |
| CBAY | RHC-0069-ACQUIRED-CBAY | 2024-02-12 | 20 | 0 |
| CERE | RHC-0070-ACQUIRED-CERE | 2023-12-07 | 28 | 0 |
| DCPH | RHC-0071-ACQUIRED-DCPH | 2024-04-29 | 20 | 0 |
| **Total** | | | **509** | **21** |

**BLU note:** BELLUS Health is a Canadian foreign private issuer (files 6-K, not 8-K). No target-form filings found in EDGAR for the 18-month pre-announcement window. Expected — not a source error.

---

## Filing Types Collected

| Form Type | Count |
|---|---|
| 8-K | 329 |
| 10-Q | 76 |
| SC 13D/A | 35 |
| 10-K | 30 |
| DEF 14A | 27 |
| SC 13D | 6 |
| 424B3 | 4 |
| S-4 | 1 |
| **Total** | **508** |

*(BLU has 0 filings; all other 19 cases have coverage.)*

---

## Exception Queue Distribution

All 20 cases promoted from PENDING_FILING_COLLECTION. Final tier distribution:

| Tier | Count | Cases |
|---|---|---|
| P1 | 2 | OYST, DICE |
| P3 | 3 | IMGO, SRRA, ALPN |
| P6 (with POSSIBLE_HIT rows) | 8 | EPZM, FMTX, GBT, TPTX, CINC, RETA, ZYNE, AMAM |
| P6 (confirmed no-hit) | 7 | BLU, CTIC, HARP, ISEE, CBAY, CERE, DCPH |
| P2 | 0 | — |
| P4 | 0 | — |
| P5 | 0 | — |
| BLOCKED | 0 | — |

**Note on P6 / vocabulary gap:** The exception queue builder's P2 and P4 signal-type sets do not match the collector's output vocabulary (`rofr_rofn` vs `rofr`/`rofn`, `retained_advisor` vs `advisor_retained`, `sale_process` not mapped). Eight P6 cases have POSSIBLE_HIT rows that warrant manual inspection before marking as baselines. See section below.

---

## POSSIBLE_HIT Detail

| Ticker | Filing Date | Filing Type | Signal Type | Keywords |
|---|---|---|---|---|
| OYST | 2022-11-07 | 8-K | acquisition_proposal | acquisition proposal |
| OYST | 2021-08-05 | 10-Q | rofr_rofn\|sale_process | right of first negotiation\|sale of the company |
| OYST | 2022-04-22 | DEF 14A | retained_advisor | financial advisor |
| DICE | 2022-10-19 | SC 13D/A | acquisition_proposal | proposal to acquire |
| IMGO | 2021-07-30 | SC 13D | strategic_alternatives | strategic alternatives |
| SRRA | 2022-02-02 | SC 13D/A | rofr_rofn | right of first refusal |
| ALPN | 2023-11-13 | SC 13D/A | sale_process | sale of the company |
| EPZM | 2022-05-10 | 10-Q | rofr_rofn | right of first negotiation |
| FMTX | 2021-04-21 | DEF 14A | sale_process | sale of the company |
| FMTX | 2021-05-14 | 10-Q | sale_process | sale of the company |
| FMTX | 2021-08-13 | 10-Q | sale_process | sale of the company |
| FMTX | 2021-11-12 | 10-Q | sale_process | sale of the company |
| GBT | 2022-05-04 | 8-K | rofr_rofn | rofr |
| TPTX | 2021-03-01 | 10-K | rofr_rofn | right of first negotiation |
| CINC | 2022-05-10 | 10-Q | sale_process | sale of the company |
| CINC | 2022-08-08 | 10-Q | sale_process | sale of the company |
| CINC | 2022-11-03 | 10-Q | sale_process | sale of the company |
| RETA | 2022-02-28 | 8-K | rofr_rofn | rofr |
| ZYNE | 2022-04-25 | DEF 14A | sale_process | sale of the company |
| ZYNE | 2023-04-21 | DEF 14A | sale_process | sale of the company |
| AMAM | 2023-11-13 | 10-Q | option_to_acquire | option to acquire |

---

## Source Evidence Draft

`source_evidence_autofill.py` generated 5 ADJUDICATION_NOTE placeholder rows (for P1 and P3 cases only):

| Case | Tier |
|---|---|
| RHC-0055-ACQUIRED-OYST | P1 |
| RHC-0061-ACQUIRED-DICE | P1 |
| RHC-0054-ACQUIRED-IMGO | P3 |
| RHC-0056-ACQUIRED-SRRA | P3 |
| RHC-0067-ACQUIRED-ALPN | P3 |

15 cases skipped (P6 — no draft rows until manual review clears or elevates them).

---

## Cases Needing Manual Review

### Priority 1 — Adjudicate first

| Case | Ticker | Tier | Why |
|---|---|---|---|
| RHC-0055-ACQUIRED-OYST | OYST | P1 | 8-K 2022-11-07 contains "acquisition proposal" language — verify if public before announcement |
| RHC-0061-ACQUIRED-DICE | DICE | P1 | SC 13D/A 2022-10-19 contains "proposal to acquire" — verify Item 4 context |

### Priority 2 — SC 13D review

| Case | Ticker | Tier | Why |
|---|---|---|---|
| RHC-0054-ACQUIRED-IMGO | IMGO | P3 | SC 13D 2021-07-30 has "strategic alternatives" in Item 4 — verify acquisition-pressure vs governance |
| RHC-0056-ACQUIRED-SRRA | SRRA | P3 | SC 13D/A 2022-02-02 has ROFR language — verify scope |
| RHC-0067-ACQUIRED-ALPN | ALPN | P3 | SC 13D/A 2023-11-13 has "sale of the company" — verify Item 4 context |

### Priority 3 — P6 with POSSIBLE_HIT rows (manual verification before marking baseline)

| Case | Ticker | Signal Hits | Note |
|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM | EPZM | rofr_rofn (10-Q 2022-05-10) | Verify if ROFR is company-level vs asset-level |
| RHC-0053-ACQUIRED-GBT | GBT | rofr_rofn (8-K 2022-05-04) | Verify ROFR scope |
| RHC-0057-ACQUIRED-TPTX | TPTX | rofr_rofn (10-K 2021-03-01) | Verify ROFR scope |
| RHC-0064-ACQUIRED-RETA | RETA | rofr_rofn (8-K 2022-02-28) | Verify ROFR scope |
| RHC-0052-ACQUIRED-FMTX | FMTX | sale_process (4× 10-Q/DEF14A) | Likely compensation-plan language — verify before marking baseline |
| RHC-0059-ACQUIRED-CINC | CINC | sale_process (3× 10-Q) | Likely compensation-plan language — verify before marking baseline |
| RHC-0066-ACQUIRED-ZYNE | ZYNE | sale_process (2× DEF14A) | Verify context — proxy change-in-control clause vs public process language |
| RHC-0068-ACQUIRED-AMAM | AMAM | option_to_acquire (10-Q 2023-11-13) | Verify if option is company-level vs asset/IP-level |

### Priority 4 — True no-hit P6 (DEAL_ANNOUNCEMENT_BASELINE candidates)

No POSSIBLE_HIT rows. Confirm filing coverage is adequate, then mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

| Case | Ticker | Filings Collected | Note |
|---|---|---|---|
| RHC-0060-ACQUIRED-CTIC | CTIC | 22 | No signal hits |
| RHC-0062-ACQUIRED-HARP | HARP | 28 | No signal hits |
| RHC-0063-ACQUIRED-ISEE | ISEE | 31 | No signal hits |
| RHC-0069-ACQUIRED-CBAY | CBAY | 20 | No signal hits |
| RHC-0070-ACQUIRED-CERE | CERE | 28 | No signal hits |
| RHC-0071-ACQUIRED-DCPH | DCPH | 20 | No signal hits |
| RHC-0058-ACQUIRED-BLU | BLU | 0 | FPI (6-K filer) — cannot assess via EDGAR target-form collection; manual review required for pre-announcement 6-K filings |

---

## Files Changed

| File | Change |
|---|---|
| `data/historical_cases/batch_51_70_confirmation_input.csv` | New — 20-row collector input (validated clean against acquisition_announcement_dates.csv) |
| `data/historical_cases/batch_51_70_pre_announcement_filing_targets.csv` | New — 509 filing target rows for Batch 51–70 |
| `data/historical_cases/batch_51_70_pre_announcement_signal_hits.csv` | New — 21 POSSIBLE_HIT rows for Batch 51–70 |
| `data/historical_cases/batch_51_70_pre_announcement_filing_report.md` | New — collector run report |
| `data/historical_cases/pre_announcement_filing_targets.csv` | Appended — 509 Batch 51–70 rows (411 existing + 509 new = 920 total) |
| `data/historical_cases/pre_announcement_signal_hits.csv` | Appended — 28 Batch 51–70 rows (16 existing + 28 new = 44 total; 21 POSSIBLE_HIT + 7 no-hit sentinels) |
| `data/historical_cases/batch_51_70_exception_queue.csv` | Rebuilt — all 20 cases now assigned tiers |
| `data/historical_cases/batch_51_70_exception_queue_report.md` | Rebuilt |
| `data/historical_cases/batch_51_70_source_evidence_draft.csv` | Rebuilt — 5 ADJUDICATION_NOTE draft rows |
| `data/historical_cases/batch_51_70_source_evidence_draft_report.md` | Rebuilt |
| `data/historical_cases/batch_51_70_filing_collection_report.md` | New — this file |

---

## Rules Applied

- No cases adjudicated.
- No case classified as TRUE_PUBLIC_PRIOR_SIGNAL.
- No case marked VERIFIED or CALIBRATION_ELIGIBLE.
- First-50 classifications not touched.
- Collector ran only for Batch 51–70 cases.
- Full live scanner not run.
- Dashboard/frontend not touched.
