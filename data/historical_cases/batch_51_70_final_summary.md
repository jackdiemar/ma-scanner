# Batch 51–70 Final Adjudication Summary

Generated: 2026-05-15 | Status: Final (all 20 cases adjudicated)

---

## 1. Scope and Method

**Cases:** 20 US-listed small-cap biotech acquisitions (RHC-0051 through RHC-0071, excluding RHC-0065 which is not in this batch).

**Announcement date range:** 2022-04-13 (SRRA) through 2024-04-29 (DCPH).

**Review window:** 18 months pre-announcement per case.

**Filing types collected:** 8-K, 10-Q, 10-K, DEF 14A, SC 13D, SC 13D/A, 424B3, S-4.

**Data source:** SEC EDGAR full-text filing archives, fetched and reviewed against primary HTML documents (not complete submission .txt wrappers) for adjudication.

**Adjudication method:** Three-phase review. (1) Collection phase: automated signal-phrase scan producing 21 POSSIBLE_HIT rows across 13 cases. (2) High-priority adjudication (P1 and P3): manual EDGAR review of 5 cases (OYST, DICE, IMGO, SRRA, ALPN) with the highest-priority queue scores. (3) P6 adjudication: manual EDGAR review of 8 P6 cases with POSSIBLE_HIT rows (EPZM, GBT, TPTX, RETA, FMTX, CINC, ZYNE, AMAM). Seven P6 true no-hit cases (BLU, CTIC, HARP, ISEE, CBAY, CERE, DCPH) confirmed as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE based on filing coverage.

**Scope constraints:** US-listed issuers only. BLU (BELLUS Health) is a Canadian foreign private issuer (6-K filer); no target-form filings were available in EDGAR for the 18-month collection window.

**Rules applied throughout:** No case classified TRUE_PUBLIC_PRIOR_SIGNAL. No case marked VERIFIED. No case marked CALIBRATION_ELIGIBLE. First-50 classifications not altered.

---

## 2. Filing Collection Statistics

| Metric | Value |
|---|---|
| Cases in scope | 20 |
| Filing target rows collected | 509 |
| POSSIBLE_HIT rows flagged by collector | 21 |
| Cases with at least one POSSIBLE_HIT row | 13 |
| True no-hit cases (zero hits) | 7 |
| Blocked cases / source errors | 0 |
| Malformed rows | 0 |

**Filing type breakdown:**

| Form type | Count |
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

*(BLU contributed 0 filings; all other 19 cases have EDGAR coverage.)*

**Cases by filing volume (top 5):** GBT (42), TPTX (36), ISEE (31), EPZM (30), HARP (28).

---

## 3. Final Classification Distribution

| Classification | Count | Pct |
|---|---:|---:|
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 11 | 55% |
| RIGHTS_LANGUAGE_ONLY | 7 | 35% |
| ASSET_SPECIFIC_RIGHTS_ONLY | 2 | 10% |
| TRUE_PUBLIC_PRIOR_SIGNAL | 0 | 0% |
| **Total** | **20** | **100%** |

**PRIVATE_BACKGROUND_ONLY** was not assigned in Batch 51–70. Post-announcement deal backgrounds (SC 14D-9, proxy) were not reviewed in this phase. Cases with no pre-announcement public signal default to DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

---

## 4. Case-Level Classification Table

All 20 cases. Case IDs from filing collection phase.

| Case ID | Ticker | Company | Announcement | Prior Tier | Classification | Signal Type Flagged | Disposition |
|---|---|---|---|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM | EPZM | Epizyme | 2023-06-26 | P6 | ASSET_SPECIFIC_RIGHTS_ONLY | rofr_rofn | Geographic license ROFN (Eisai Japan/Asia) — product and territory specific |
| RHC-0052-ACQUIRED-FMTX | FMTX | Forma Therapeutics | 2022-05-02 | P6 | RIGHTS_LANGUAGE_ONLY | sale_process | CIC vesting clause (proxy) + pre-IPO PWERM valuation disclosure (3× 10-Q) |
| RHC-0053-ACQUIRED-GBT | GBT | Global Blood Therapeutics | 2022-08-08 | P6 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | rofr_rofn | UUEncoded binary artifact in complete submission .txt — no ROFR in primary document |
| RHC-0054-ACQUIRED-IMGO | IMGO | Imago BioSciences | 2022-11-21 | P3 | RIGHTS_LANGUAGE_ONLY | strategic_alternatives | VC/PE investor self-reservation boilerplate in IPO-era SC 13D — not company-level |
| RHC-0055-ACQUIRED-OYST | OYST | Oyster Point Pharma | 2022-11-08 | P1 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | acquisition_proposal | Deal announcement 8-K (same day); "acquisition proposal" in FLS boilerplate only |
| RHC-0056-ACQUIRED-SRRA | SRRA | Sierra Oncology | 2022-04-13 | P3 | RIGHTS_LANGUAGE_ONLY | rofr_rofn | ROFR in lock-up agreement exhibit — employment termination share repurchase right |
| RHC-0057-ACQUIRED-TPTX | TPTX | Turning Point Therapeutics | 2022-04-04 | P6 | ASSET_SPECIFIC_RIGHTS_ONLY | rofr_rofn | Geographic license ROFN (Zai Lab Greater China) — product and territory specific |
| RHC-0058-ACQUIRED-BLU | BLU | BELLUS Health | 2023-04-18 | P6 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | — | FPI (6-K filer); no EDGAR target-form coverage available |
| RHC-0059-ACQUIRED-CINC | CINC | CinCor Pharma | 2023-01-09 | P6 | RIGHTS_LANGUAGE_ONLY | sale_process | Pre-IPO PWERM stock compensation valuation disclosure (3× 10-Q, identical language) |
| RHC-0060-ACQUIRED-CTIC | CTIC | CTI BioPharma | 2023-05-10 | P6 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | — | No signal hits; 22 filings reviewed |
| RHC-0061-ACQUIRED-DICE | DICE | DICE Therapeutics | 2023-06-20 | P1 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | acquisition_proposal | "No plan or proposal to acquire" — negation false positive in passive holder SC 13D/A |
| RHC-0062-ACQUIRED-HARP | HARP | Harpoon Therapeutics | 2024-01-08 | P6 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | — | No signal hits; 28 filings reviewed |
| RHC-0063-ACQUIRED-ISEE | ISEE | IVERIC bio | 2023-05-01 | P6 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | — | No signal hits; 31 filings reviewed |
| RHC-0064-ACQUIRED-RETA | RETA | Reata Pharmaceuticals | 2023-07-14 | P6 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | rofr_rofn | UUEncoded binary artifact in complete submission .txt — no ROFR in primary document |
| RHC-0066-ACQUIRED-ZYNE | ZYNE | Zynerba Pharmaceuticals | 2023-10-18 | P6 | RIGHTS_LANGUAGE_ONLY | sale_process | Director biography (prior company sale at a different organization) — 2× proxy |
| RHC-0067-ACQUIRED-ALPN | ALPN | Alpine Immune Sciences | 2024-04-10 | P3 | RIGHTS_LANGUAGE_ONLY | sale_process | "Sale of the Company's securities" in offering lock-up exhibit — investor share-sale restriction |
| RHC-0068-ACQUIRED-AMAM | AMAM | Ambrx Biopharma | 2024-01-08 | P6 | RIGHTS_LANGUAGE_ONLY | option_to_acquire | BVI→Delaware redomiciliation equity conversion; "Merger Agreement" = internal domestication document |
| RHC-0069-ACQUIRED-CBAY | CBAY | CymaBay Therapeutics | 2024-02-12 | P6 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | — | No signal hits; 20 filings reviewed |
| RHC-0070-ACQUIRED-CERE | CERE | Cerevel Therapeutics | 2023-12-07 | P6 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | — | No signal hits; 28 filings reviewed |
| RHC-0071-ACQUIRED-DCPH | DCPH | Deciphera Pharmaceuticals | 2024-04-29 | P6 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | — | No signal hits; 20 filings reviewed |

---

## 5. True Signal Result

**TRUE_PUBLIC_PRIOR_SIGNAL: 0 of 20 cases.**

No case in Batch 51–70 produced a confirmed public prior process signal. All 21 POSSIBLE_HIT rows reviewed against primary EDGAR documents were disposed as false positives or non-signal artifacts. Zero source evidence rows were added to `source_evidence.csv` from this batch.

---

## 6. False-Positive Lessons

Nine distinct false-positive patterns were identified across Batch 51–70. The two highest-volume patterns (binary artifacts and PWERM disclosures) are engineering-level and directly addressable in the collector.

### Pattern 1 — UUEncoded binary artifacts (GBT, RETA; 2 cases, 2 POSSIBLE_HIT rows)

EDGAR complete submission .txt files bundle all exhibits as UUEncoded binary. Signal phrases matched within encoded binary content in the complete submission wrapper, not in any human-readable filing text. Both cases were routine earnings 8-Ks (Q1 2022 earnings for GBT; FY2021 earnings for RETA) with no process language in the primary HTML documents. This pattern is likely present in other batches that fetched complete submission .txt files.

**Engineering fix:** Do not run phrase matching against complete submission .txt files. Parse only primary HTML documents and named exhibit files. Alternatively, strip UUEncoded sections before phrase scanning.

### Pattern 2 — Pre-IPO PWERM valuation disclosures (FMTX, CINC; 2 cases, 7 POSSIBLE_HIT rows)

Post-IPO 10-Qs disclose the PWERM (Probability-Weighted Expected Returns Method) used to value pre-IPO stock option grants. These footnotes enumerate liquidity scenarios including "sale of the Company" alongside IPO, delayed IPO, and remain-private scenarios. The language is required accounting disclosure about a past option-grant valuation model — it carries no information about a current or future strategic process. FMTX produced four hits (one proxy CIC clause + three identical 10-Q PWERM notes); CINC produced three identical 10-Q PWERM notes.

**Engineering fix:** Exclude "sale of the Company" phrases appearing in stock-compensation accounting footnotes describing PWERM or Monte Carlo valuation models. Key co-occurrence signals: "PWERM," "probability-weighted," "expected return method," "prior to our IPO," "pre-IPO."

### Pattern 3 — Negative phrase context (DICE; 1 case, 1 POSSIBLE_HIT row)

The collector matched "proposal to acquire" in RA Capital's SC 13D/A. The full sentence: "currently have **no** plan or **proposal to acquire** any additional Issuer securities." The phrase was caught without negation context. RA Capital was a passive healthcare investor filing a routine amendment after DICE's October 2022 IPO.

**Engineering fix:** Apply negation lookback window (minimum 10 tokens) before matching acquisition-pressure phrases. Phrases in "no [plan/proposal/intent] to [acquire/effect/pursue]" constructions should be excluded.

### Pattern 4 — VC/PE investor self-reservation boilerplate in IPO-era 13Ds (IMGO; 1 case)

Blackstone/Clarus Lifesciences III filed an initial SC 13D at Imago's IPO because it crossed 10% as a pre-IPO VC investor. Item 4 contained standard VC/PE boilerplate reserving the right to "evaluate strategic alternatives as they may become available" regarding the investor's own investment position — not company-level strategic alternatives. The filing explicitly disclaimed any current plan or proposal.

**Engineering fix:** Item 4 intent classification should distinguish investor self-reservation language (subject = reporting person's investment) from company-level process language (subject = issuer). IPO-triggering 13D filings by pre-IPO investors are high-false-positive candidates.

### Pattern 5 — Lock-up agreement exhibits (SRRA, ALPN; 2 cases)

"Right of first refusal" (SRRA) and "sale of the Company's securities" (ALPN) both appeared in Exhibit 99.3 (Form of Lock-Up Agreement) attached to follow-on offering materials. The SRRA ROFR was an employment-termination share repurchase right; the ALPN phrase described OrbiMed's restriction on selling its investment shares. Neither was company-level acquisition language.

**Engineering fix:** Exclude signal phrases from lock-up agreement exhibits and offering restriction schedules. Exhibit file name patterns: "Lock-Up," "lock-up agreement," "lock_up."

### Pattern 6 — Asset-specific geographic license ROFN (EPZM, TPTX; 2 cases)

Both cases had legitimate "right of first negotiation" language in public filings, but the rights were limited to specific products in specific geographic territories: Eisai's ROFN for tazemetostat in Japan and rest of Asia (EPZM), and Zai Lab's ROFN for drug candidates in Greater China (TPTX). These are standard collaboration-agreement disclosures.

**Rule reinforcement (from first 50):** ROFN must be classified for scope — whole company, single asset, or territory — before being treated as acquisition pathway evidence.

### Pattern 7 — Deal announcement 8-K FLS boilerplate (OYST; 1 case)

The deal announcement 8-K itself (filed the same day as the public announcement) contained "acquisition proposal" in forward-looking statements boilerplate: "the possibility that competing offers or acquisition proposals for OP will be made." This is standard deal-announcement FLS language, not a pre-announcement disclosure.

**Engineering fix:** Exclude signal phrases appearing in deal-announcement 8-Ks (Items 1.01 with Merger Agreement exhibits, or same-day announcement filings). Consider filtering FLS boilerplate sections more broadly.

### Pattern 8 — Director biography at prior employer (ZYNE; 1 case, 2 POSSIBLE_HIT rows)

"Sale of the company" appeared in both the 2022 and 2023 proxy statements for Zynerba in the biography of a director who had previously served as CEO of Prism Pharmaceuticals (acquired by Baxter International). Identical text in both years because the same director remained on the board.

**Engineering fix:** Exclude "sale of the company" phrases from director biography and career history sections (typically under "director since," "background," "professional experience" subsections in DEF 14A).

### Pattern 9 — Internal redomiciliation equity disclosures (AMAM; 1 case)

Ambrx's 10-Q used "Merger Agreement" and "option to acquire ordinary shares" throughout the equity compensation footnote, but these referred to the BVI→Delaware domestication transaction (a corporate conversion, not an M&A process). The domestication required recalibrating Cayman equity awards into Delaware-equivalent instruments at a 7:1 conversion ratio.

**Engineering fix:** Distinguish M&A Merger Agreements from domestication/redomiciliation agreements. Context signals: "domestication," "conversion," "redomiciliation," "Cayman," "BVI," "ordinary shares converted to common stock."

---

## 7. Comparison to First 50-Case Study

| Dimension | First 50 Cases | Batch 51–70 |
|---|---|---|
| Announcement dates | 2015–2022 | 2022–2024 |
| Cases reviewed | 50 | 20 |
| TRUE_PUBLIC_PRIOR_SIGNAL | 3 (6%) | 0 (0%) |
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 35 (70%) | 11 (55%) |
| PRIVATE_BACKGROUND_ONLY | 9 (18%) | not assessed |
| ASSET_SPECIFIC_RIGHTS_ONLY | 2 (4%) | 2 (10%) |
| RIGHTS_LANGUAGE_ONLY | 1 (2%) | 7 (35%) |
| POSSIBLE_HIT rows reviewed | not reported | 21 |
| Binary artifact false positives | not identified | 2 cases |
| PWERM false positives | not identified | 5 cases / 7 rows |

**Key difference:** Batch 51–70 produced a substantially higher RIGHTS_LANGUAGE_ONLY rate (35% vs. 2%). This reflects improved coverage of DEF 14A, 10-Q, and SC 13D/A filings — form types that generate higher false-positive density from compensation plan language, lock-up exhibits, and VC/PE boilerplate. The first 50-case study reached fewer of these secondary filings.

**No true signals found in Batch 51–70** despite the higher total filing volume (509 vs. the first 50's coverage) and more recent deal vintage (2022–2024). This is consistent with but does not prove that the base rate of public prior signals in small-cap biotech acquisitions is low.

**PRIVATE_BACKGROUND_ONLY** was assigned in the first 50 based on review of post-announcement proxy and SC 14D-9 deal backgrounds. This review was not conducted for Batch 51–70. The DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE classification in Batch 51–70 does not imply those deals had public processes — it reflects the absence of confirmed pre-announcement public evidence in EDGAR.

---

## 8. Combined 70-Case Implication

| Classification | First 50 | Batch 51–70 | Combined 70 | Combined Pct |
|---|---:|---:|---:|---:|
| TRUE_PUBLIC_PRIOR_SIGNAL | 3 | 0 | 3 | 4.3% |
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 35 | 11 | 46 | 65.7% |
| PRIVATE_BACKGROUND_ONLY | 9 | 0* | 9 | 12.9% |
| ASSET_SPECIFIC_RIGHTS_ONLY | 2 | 2 | 4 | 5.7% |
| RIGHTS_LANGUAGE_ONLY | 1 | 7 | 8 | 11.4% |
| **Total** | **50** | **20** | **70** | **100%** |

*PRIVATE_BACKGROUND_ONLY not assessed in Batch 51–70. The 9 combined cases are from the first 50 only.

**Combined public prior signal rate: 3 of 70 (4.3%).**

This is lower than the first 50's 6% rate. The combination of 3 true signals across 70 cases is consistent with a base rate in the range of 4–8% for US-listed small-cap biotech acquisitions, but the sample is too small and the two batches differ in methodology to establish a calibrated estimate.

The false-positive surface continues to be the dominant challenge. Of the 21 POSSIBLE_HIT rows reviewed in Batch 51–70, zero produced a true signal. All 21 were classifiable into identifiable, engineering-addressable false-positive patterns.

---

## 9. Engineering Improvements Recommended

The following changes to the collector and exception queue are supported by evidence from this batch. Prioritized by estimated false-positive reduction impact.

| Priority | Improvement | Evidence | Estimated impact |
|---|---|---|---|
| 1 | Exclude phrase matching from UUEncoded sections in complete submission .txt files | GBT, RETA | Eliminates binary artifact hits across all batches |
| 2 | Exclude PWERM/stock-comp valuation footnote sections from sale_process matching | FMTX (4 rows), CINC (3 rows) | Eliminates a recurring multi-hit false positive for post-IPO companies with pre-IPO option grants |
| 3 | Add negation lookback window (≥10 tokens) for acquisition-pressure phrases | DICE | Eliminates negation false positives |
| 4 | Exclude signal phrases from lock-up agreement exhibits | SRRA, ALPN | Reduces offering-related exhibit false positives |
| 5 | Exclude sale_process phrases from DEF 14A director biography sections | ZYNE | Eliminates cross-entity career history false positives |
| 6 | Classify 13D filing context: IPO-triggering vs. post-IPO activist filing | IMGO | Reduces VC/PE IPO-era SC 13D false positives |
| 7 | Distinguish domestication/redomiciliation Merger Agreements from M&A agreements | AMAM | Prevents corporate-conversion document false positives |
| 8 | Exclude FLS boilerplate sections from deal-announcement 8-Ks | OYST | Prevents same-day announcement 8-K hits |
| 9 | Enforce scope classification for ROFN/ROFR before promoting to exception queue | EPZM, TPTX | Prevents asset-level rights from clearing company-level gate |

Items 1 and 2 are highest priority because they affect multiple hits per case and are repeatable across batches. Item 3 (negation) and Item 4 (lock-up exhibits) are lower implementation cost and also repeatable.

---

## 10. Caveats

- **No case marked VERIFIED or CALIBRATION_ELIGIBLE.** All classifications remain at working-adjudication status.
- **PRIVATE_BACKGROUND_ONLY not assessed.** Post-announcement SC 14D-9 and proxy backgrounds were not reviewed for Batch 51–70. Some DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE cases may contain private process facts not captured here.
- **BLU excluded from EDGAR coverage.** BELLUS Health (FPI) files 6-K, not 8-K or 10-Q. The 18-month collection window found no target-form filings on EDGAR. BLU is classified DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE but without the filing coverage depth of domestic-issuer cases.
- **4.3% combined rate is not a calibrated estimate.** The 70-case sample covers 2015–2024 with variable methodology between the first 50 and Batch 51–70. Coverage depth, filing type distribution, and adjudication standards differ between phases. Do not treat 4.3% as a statistical base rate without further validation.
- **Collector vocabulary gaps remain.** The exception queue builder's P2 and P4 signal-type sets do not fully match the collector's output vocabulary (e.g., `rofr_rofn` vs. `rofr`/`rofn`; `retained_advisor` vs. `advisor_retained`; `sale_process` unmapped). Eight Batch 51–70 cases were P6 because of this mismatch. The vocabulary gap may misroute future cases.
- **Announcement dates may contain minor errors.** A discrepancy was noted between the filing collection report (EPZM: 2022-06-27) and the P6 adjudication report (EPZM: 2023-06-26). The adjudication report date (2023-06-26) is consistent with the filing's days-before-announcement calculation. The collection report date may be a transcription error.
- **No alpha claim is made.** These findings describe the historical presence or absence of public process signals in SEC filings. They do not establish that detecting such signals would have produced tradeable returns. Trading feasibility, spread costs, and position-sizing constraints are not assessed here.

---

## 11. Next Recommended Step

**Batch 51–70 adjudication is complete.** The following actions are available in priority order.

**Immediate (documentation complete):**
- Update `data/historical_cases/project_status_snapshot.md` to reflect completed Batch 51–70 status.
- Optionally: backfill PRIVATE_BACKGROUND_ONLY review for the 11 DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE cases in Batch 51–70 to establish full parity with the first 50-case methodology.

**Engineering (highest ROI):**
- Implement collector improvement items 1 and 2 (binary artifact exclusion, PWERM section exclusion) before running Batch 71–90 collection. These two changes would have eliminated 9 of the 21 POSSIBLE_HIT rows in Batch 51–70.
- Align exception queue vocabulary with collector output (`rofr_rofn`, `sale_process`, `retained_advisor`) to eliminate the P6 vocabulary-gap bucket.

**Research (next batch):**
- Proceed to Batch 71–90 using the improved collector after engineering fixes are implemented.
- Consider limiting Batch 71–90 to announcement dates through 2022 to maintain consistency with the first 50-case vintage before extending into 2023–2024.

**Validation (longer term):**
- Run spot checks on the highest-filing-count DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE cases in Batch 51–70 (GBT 42, TPTX 36, ISEE 31, EPZM 30) to confirm no missed prior signals before treating the combined 70-case dataset as a stable baseline.
- Do not scale to 100+ cases until the collector improvements above are implemented and the vocabulary gap is resolved.

---

## Source Files

| File | Role |
|---|---|
| `data/historical_cases/batch_51_70_filing_collection_report.md` | Filing collection stats, POSSIBLE_HIT rows, initial tier distribution |
| `data/historical_cases/batch_51_70_queue_summary.md` | Workload view and recommended review order |
| `data/historical_cases/batch_51_70_high_priority_adjudication_report.md` | P1/P3 adjudication: OYST, DICE, IMGO, SRRA, ALPN |
| `data/historical_cases/batch_51_70_p6_adjudication_report.md` | P6 adjudication: EPZM, GBT, TPTX, RETA, FMTX, CINC, ZYNE, AMAM |
| `data/historical_cases/biotech_prior_signal_50_case_final_summary.md` | First 50-case final summary (comparison basis) |

Committed in: `d7a3ca0` (P6 adjudication).
