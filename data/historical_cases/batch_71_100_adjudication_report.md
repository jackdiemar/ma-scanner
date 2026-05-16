# Batch 71-100 Adjudication Report

Generated: 2026-05-16
Adjudicated by: Human researcher + source-pull tool assistance
Cases adjudicated: 16 (11 review + 5 spot-check)
Blocked: 10 (pending date resolution)

---

## Summary

Zero TRUE_PUBLIC_PRIOR_SIGNAL cases found in Batch 71-100 dated cases.

All 11 review cases resolved as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE after source inspection.
All 5 spot-check (likely-clean) cases confirmed as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

| Metric | Value |
|---|---|
| Cases adjudicated (this batch) | 16 |
| TRUE_PUBLIC_PRIOR_SIGNAL (this batch) | 0 |
| Cumulative signals (cases 1–86) | 3 |
| Cumulative rate | 3/86 (3.5%) |
| Blocked (date missing) | 10 |

---

## Case-by-Case Adjudications

### P1 — Manual Source Pull

#### SGEN — RHC-0106-ACQUIRED-SGEN
- Announcement: 2023-03-13
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hit 1 (8-K 0001193125-21-277501, 2021-09-21): UUEncoded binary artifact in complete submission .txt. Garbled ASCII text surrounds the "rofn" match. Pattern: BINARY_ARTIFACT. → FALSE_POSITIVE.
- Hit 2 (8-K 0001193125-21-278354, 2021-09-21): Same filing date, different accession. The hit is "ROFN Notice 2.5" — a defined term appearing in the defined terms index of Exhibit 2.1, the Seagen-RemeGen RC48 licensing agreement. ROFN is an abbreviation for a contract term in the collaboration license, not an ROFN over Seagen as a company. → ASSET_SPECIFIC_RIGHTS_ONLY.
- Source manually pulled: YES (both filings). No acquisition process evidence found.

#### TBIO — RHC-0132-ACQUIRED-TBIO
- Announcement: 2021-08-03
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hit 1 (8-K 0001193125-20-175955, 2020-06-23): Sanofi Pasteur had an option to acquire licenses to additional infectious disease pathogens from Translate Bio (not an option to acquire the company). The filing reports the license option was REMOVED from the agreement under the Amendment and replaced with a broader grant. Also includes a standstill clause in the related equity investment agreement — not an acquisition process clause. → ASSET_SPECIFIC_RIGHTS_ONLY.
- Source manually pulled: YES. No acquisition process evidence found.

---

### P2 — Context Check

#### VSTM — RHC-0140-ACQUIRED-VSTM
- Announcement: 2024-01-08
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hit 1 (8-K 0001104659-22-115103, 2022-11-07): BVF Partners exchange of 10M common shares for 1M preferred stock. "Not subject to any agreement granting option, warrant or right of first refusal." This is a ROFR warranty — a negative statement confirming no ROFR exists. → RIGHTS_LANGUAGE_ONLY.
- Hit 2 (8-K 0001104659-23-073116, 2023-06-21): Underwritten public offering. "Sale of the Company's securities...being made only by means of a written prospectus meeting the requirements of Section 10 of the Securities Act." Standard securities offering disclaimer. → RIGHTS_LANGUAGE_ONLY.
- Source manually pulled: YES (both filings). No acquisition process evidence found.

#### LBPH — RHC-0077-ACQUIRED-LBPH
- Announcement: 2024-10-15
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hit 1 (8-K 0001193125-24-000675, 2024-01-02): "Sale of the Company's securities...being made only by means of a written prospectus." Standard securities offering disclaimer. → RIGHTS_LANGUAGE_ONLY.
- Hit 2 (10-K 0000950170-24-029952, 2024-03-12): Arena (Pfizer) has "right of first negotiation to acquire certain development and commercial rights to LP659 products." Explicitly limited to LP659, a specific drug program. UCB (the actual acquirer) had no pre-announcement ROFN over Longboard Pharmaceuticals as a company. → ASSET_SPECIFIC_RIGHTS_ONLY.
- Source context inspected via excerpt. No acquisition process evidence found.

#### G1T — RHC-0074-ACQUIRED-G1T
- Announcement: 2024-08-07
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hits 1-4 (10-Q x4: 2023-05-03, 2023-08-02, 2023-11-01, 2024-05-01): Identical disclosure across four quarterly filings. "The Company has right of first negotiation to re-acquire these assets." G1T licensed lerociclib to Incyclix and retained an ROFN to re-acquire the licensed compound. This is G1T's own ROFN over its outbound-licensed asset to a spinout — not a third-party ROFN over G1T as a company. → ASSET_SPECIFIC_RIGHTS_ONLY (own compound re-acquisition right).
- Hit on 2024-05-01 (97 days before announcement) is same boilerplate quarterly disclosure. No change in process language.
- Source context inspected via excerpt. No acquisition process evidence found.

---

### P3 — Confirm and Close

#### HZNP — RHC-0105-ACQUIRED-HZNP
- Announcement: 2022-12-12
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hit 1 (8-K 0001193125-22-134596, 2022-05-02): 2020 Equity Incentive Plan amendment. S-8 registration boilerplate defining consultant eligibility: "offer or the sale of the Company's securities to such person." → RIGHTS_LANGUAGE_ONLY.
- Hit 2 (10-Q 0000950170-22-020973, 2022-11-02): Horizon received an option to acquire the ADX-914 program from Q32 Bio. Horizon is the acquiring party in this transaction. → WRONG_DIRECTION (not relevant to Horizon's own acquisition by AstraZeneca).
- Hit 3 (8-K 0001193125-22-275395, 2022-11-02): 8-K announcing the same ADX-914 option from Q32 Bio. Same wrong-direction acquisition. → WRONG_DIRECTION.
- Source manually pulled: YES (hits 1 and 3). No acquisition process evidence found.

#### SNDX — RHC-0107-ACQUIRED-SNDX
- Announcement: 2023-12-15
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hits 1-2 (10-Q x2: 2022-08-08, 2022-11-03): Incyte terminated the Incyte Agreement. "Cash settlement on the sale of the Company's common stock would be made to make the parties whole." Incyte was divesting its equity stake in Syndax as part of the collaboration termination settlement — a partner selling equity, not evidence of Syndax running a sale process. → RIGHTS_LANGUAGE_ONLY.
- Source context inspected via excerpt. No acquisition process evidence found.

---

### P4 — Known Pattern

#### STML — RHC-0103-ACQUIRED-STML
- Announcement: 2020-05-04
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hit 1 (10-K 0001104659-19-015293, 2019-03-15): Director biography. "ultimately the sale of the company to Keryx Biopharmaceuticals" describes a board member's prior role at a different company. Not Stemline's process. → RIGHTS_LANGUAGE_ONLY.
- Hits 2-4 (10-Q x3: 2019-05-10, 2019-08-06, 2019-11-12): Identical performance condition equity award boilerplate. "A change in control or a sale of the company, no expense is recognized." Standard accounting disclosure for performance-condition grants. → RIGHTS_LANGUAGE_ONLY.
- Hit 5 (10-K 0001104659-20-034154, 2020-03-16, 49 days before): Same director bio re-filed in the 2019 annual report. Biographical language only; no change from prior year. → RIGHTS_LANGUAGE_ONLY.
- Source context inspected via excerpt. No acquisition process evidence found.

#### MRTX — RHC-0079-ACQUIRED-MRTX
- Announcement: 2023-10-10
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hit 1 (8-K 0001628280-22-014127, 2022-05-12): 2022 Equity Incentive Plan approval at Annual Meeting. S-8 registration boilerplate: "offer or the sale of the Company's securities to such person." Identical pattern to HZNP hit 1. → RIGHTS_LANGUAGE_ONLY.
- Source manually pulled: YES. No acquisition process evidence found.

#### ALBO — RHC-0104-ACQUIRED-ALBO
- Announcement: 2023-01-09
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hit 1 (424B3 0001104659-22-094468, 2022-08-25): Prospectus anti-takeover provisions section. "Reduce our vulnerability to an unsolicited acquisition proposal" is boilerplate risk-factor disclosure under Delaware Section 203. Standard prospectus language describing existing anti-takeover defenses, not an actual acquisition proposal. → RIGHTS_LANGUAGE_ONLY.
- Source manually pulled: YES. No acquisition process evidence found.

#### CHMA — RHC-0101-ACQUIRED-CHMA
- Announcement: 2021-05-05
- Final: **DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE** | Confidence: HIGH
- Hit 1 (DEF 14A 0001193125-20-123025, 2020-04-28): Proxy statement director biography. "Years of experience providing strategic and financial advisory services to biopharmaceutical organizations." Describes the director's career as a financial advisor — not Chiasma's sale process. → RIGHTS_LANGUAGE_ONLY.
- Hit 2 (DEF 14A 0001193125-21-131446, 2021-04-26, 9 days before announcement): Annual proxy re-filing of same director bio. "Mr. Stack has confirmed to our Board of Directors that he is fully committed to continuing to dedicate the required amount of time." Boilerplate director commitment language in annual proxy. Close timing (9 days) noted; content is clearly biographical, not process. → RIGHTS_LANGUAGE_ONLY.
- Source context inspected via excerpt. No acquisition process evidence found.

---

### Spot-Check — 5 Likely Clean Cases

All five confirmed DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE. No signal hits detected in the 427-filing EDGAR pre-announcement search.

| Ticker | Announcement Date | Date Confidence | Result |
|---|---|---|---|
| CNST | 2021-06-02 | HIGH | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| FUSN | 2024-03-19 | MEDIUM | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| KROS | 2024-12-03 | MEDIUM | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| KRTX | 2023-12-22 | MEDIUM | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| MORF | 2024-07-08 | MEDIUM | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |

MEDIUM-confidence announcement dates noted. Classifications stand but should be revisited if dates are later corrected.

---

## False-Positive Pattern Distribution (25 hits, 11 cases)

| Pattern | Hits | Cases |
|---|---|---|
| Securities offering prospectus disclaimer | 5 | VSTM, LBPH, MRTX, HZNP |
| Asset-specific ROFN/ROFR (program, compound, territory) | 7 | SGEN, TBIO, LBPH, G1T |
| Director biography (prior employer's sale) | 3 | STML, CHMA |
| Performance condition equity award boilerplate | 3 | STML |
| Partner equity stake divestiture | 2 | SNDX |
| Wrong-direction acquisition (target acquiring asset) | 2 | HZNP |
| Anti-takeover provision disclosure | 1 | ALBO |
| ROFR warranty (negative statement) | 1 | VSTM |
| UUEncoded binary artifact | 1 | SGEN |
| **Total** | **25** | |

---

## 10 Blocked Cases

These 10 cases remain BLOCKED. Filing collection was not attempted. Resolve announcement dates using EDGAR URLs in `batch_71_100_date_prefill_queue.csv` before proceeding.

ENLV, FATE, GRCL, HRMY, KPTI, LMNX, MOR, SYNH, TGTX, VECT

---

## Running Totals After Batch 71-100 Adjudication

| Metric | Value |
|---|---|
| Total cases finalized | 86 |
| TRUE_PUBLIC_PRIOR_SIGNAL | 3 |
| Signal rate | 3/86 (3.5%) |
| Still blocked | 10 |
| Target | 200 |
| Remaining (excl. blocked) | 104 |

Prior signals (cases 1-70): MDVN (unsolicited proposal, 116 days before), DMTX (superior proposal, 39 days), TSRO (sale-process media report, 17 days).

---

## Calibration Notes

- Batch 71-100 dated cases (n=16): 0 true signals. Rate consistent with 4.3% historical base.
- All 25 hits resolved as false positives. Major sources: offering prospectus disclaimers (most common), asset-specific ROFN language, equity plan S-8 boilerplate.
- Asset-specific ROFN pattern emerging as a persistent false-positive category: SGEN, TBIO, LBPH, G1T all hit on ROFN language that is explicitly program-level or compound-level.
- Timing note: CHMA DEF 14A hit was 9 days before announcement. Biographical language at close timing still correctly classified as false positive.
- G1T 4-hit pattern (identical quarterly disclosure) illustrates how boilerplate text amplifies hit count without adding information.

---

## Next Steps

1. Resolve 10 blocked cases (ENLV, FATE, GRCL, HRMY, KPTI, LMNX, MOR, SYNH, TGTX, VECT) via manual EDGAR date lookup.
2. Proceed to Batch 101-130 candidate selection and pipeline run.
3. Update case_factory_state.json to reflect finalized_cases = 86.
