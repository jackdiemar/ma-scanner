# Batch 51–70 P6 Possible-Hit Adjudication Report

Generated: 2026-05-15

Scope: P6 cases with POSSIBLE_HIT rows only (EPZM, GBT, TPTX, RETA, FMTX, CINC, ZYNE, AMAM).
The 7 confirmed no-hit P6 cases (BLU, CTIC, HARP, ISEE, CBAY, CERE, DCPH) are not adjudicated here — they can be marked DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE directly.

---

## Summary

| Case | Ticker | Classification | Signal Type Flagged | Disposition |
|---|---|---|---|---|
| RHC-0051-ACQUIRED-EPZM | EPZM | ASSET_SPECIFIC_RIGHTS_ONLY | rofr_rofn | Geographic license ROFN — product/territory-specific, not company-level |
| RHC-0053-ACQUIRED-GBT | GBT | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | rofr_rofn | Garbled binary artifact in complete submission .txt — no ROFR in actual filing |
| RHC-0057-ACQUIRED-TPTX | TPTX | ASSET_SPECIFIC_RIGHTS_ONLY | rofr_rofn | Geographic license ROFN with Zai Lab — product/territory-specific, not company-level |
| RHC-0064-ACQUIRED-RETA | RETA | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | rofr_rofn | Garbled binary artifact in complete submission .txt — no ROFR in actual filing |
| RHC-0058-ACQUIRED-FMTX | FMTX | RIGHTS_LANGUAGE_ONLY | sale_process | CIC vesting clause + pre-IPO PWERM stock comp valuation |
| RHC-0060-ACQUIRED-CINC | CINC | RIGHTS_LANGUAGE_ONLY | sale_process | Pre-IPO PWERM stock comp valuation in 10-Q disclosures |
| RHC-0063-ACQUIRED-ZYNE | ZYNE | RIGHTS_LANGUAGE_ONLY | sale_process | Director biography — prior company sale at a different organization |
| RHC-0068-ACQUIRED-AMAM | AMAM | RIGHTS_LANGUAGE_ONLY | option_to_acquire | Internal redomiciliation (BVI→Delaware) stock option conversion |

**TRUE_PUBLIC_PRIOR_SIGNAL found: 0**
**Source evidence rows added: 0**
No case marked VERIFIED or CALIBRATION_ELIGIBLE.

---

## Case-by-Case Adjudication

---

### RHC-0051-ACQUIRED-EPZM — Epizyme

**Tier:** P6
**Announcement date:** 2023-06-26
**Classification:** ASSET_SPECIFIC_RIGHTS_ONLY

#### Flagged filing

| Field | Value |
|---|---|
| Filing | 10-Q (Q1 2022) |
| Filing date | 2022-05-10 |
| Accession | 0000950170-22-008721 |
| Days before announcement | 412 |
| Signal type flagged | rofr_rofn |

#### Excerpt

> *"retaining development and commercialization rights in Japan, as well as a right to elect to manufacture tazemetostat and any other EZH2 product candidates in Japan, and a right of first negotiation for the rest of Asia."*

#### Finding

The ROFN in this filing is a geographic license right held by Epizyme's partner (Eisai Co.) for specific products (tazemetostat, EZH2 candidates) in specific territories (Japan + rest of Asia). This language describes the terms of an existing license/collaboration agreement, not a company-level strategic process. The right applies to a named product class in a named territory — the clearest form of asset-specific rights.

There is no board-level process language, no retained financial advisor disclosure, no "strategic alternatives" language, and no indication the company had initiated a company-level sale process. The 10-Q is a routine quarterly report.

#### Conclusion

ASSET_SPECIFIC_RIGHTS_ONLY. Geographic license ROFN for specific product/territory. No company-level process evidence.

---

### RHC-0053-ACQUIRED-GBT — Global Blood Therapeutics

**Tier:** P6
**Announcement date:** 2022-08-08
**Classification:** DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE

#### Flagged filing

| Field | Value |
|---|---|
| Filing | 8-K (Q1 2022 Earnings) |
| Filing date | 2022-05-04 |
| Accession | 0001171843-22-003218 |
| Days before announcement | 96 |
| Signal type flagged | rofr_rofn |

#### Finding

The collector flagged "ROFR" in the complete submission .txt file (EDGAR's multi-document bundle). The complete submission file embeds all exhibits in UUEncoded binary format; the collector matched "ROFR" within that encoded binary, not within any readable filing text.

The primary document (f8k_050422.htm, confirmed from EDGAR index) is a standard Q1 2022 Earnings 8-K (Items 2.02 and 9.01) announcing financial results for the quarter ended March 31, 2022. The full text contains no ROFR, strategic alternatives, merger, or process language. The filing was signed by CFO Jeffrey Farrow and is an earnings announcement only.

#### False-positive check

The "ROFR" match originated in UUEncoded binary content in the complete submission wrapper, not in human-readable filing text. This is a known artifact when the collector processes old-format EDGAR complete submission .txt files. The primary HTML document has no process signal.

#### Conclusion

DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE. Garbled binary artifact — no process signal in actual filing.

---

### RHC-0057-ACQUIRED-TPTX — Turning Point Therapeutics

**Tier:** P6
**Announcement date:** 2022-04-04
**Classification:** ASSET_SPECIFIC_RIGHTS_ONLY

#### Flagged filing

| Field | Value |
|---|---|
| Filing | 10-K (FY2020) |
| Filing date | 2021-03-01 |
| Accession | 0001564590-21-009849 |
| Days before announcement | 399 |
| Signal type flagged | rofr_rofn |

#### Excerpt

> *"Zai has exercised its right of first negotiation with respect to one of [drug candidates in Zai Territory]"*

#### Finding

The ROFN language describes rights held by Zai Lab under an existing collaboration agreement with Turning Point Therapeutics. Zai Lab has a right of first negotiation to license specific drug candidates in specific territories (the "Zai Territory" — defined as Greater China and certain other Asian countries). This is geographic/product-specific license ROFN embedded in collaboration agreement disclosures, not a company-level acquisition process right.

The 10-K is a routine annual report. There is no company-level board process, no retained financial advisor, and no strategic alternatives language. The Zai collaboration was a pre-existing commercial partnership standard in oncology licensing.

#### Conclusion

ASSET_SPECIFIC_RIGHTS_ONLY. Geographic license ROFN with Zai Lab for specific territories/candidates. No company-level process evidence.

---

### RHC-0064-ACQUIRED-RETA — Reata Pharmaceuticals

**Tier:** P6
**Announcement date:** 2023-07-14
**Classification:** DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE

#### Flagged filing

| Field | Value |
|---|---|
| Filing | 8-K (FY2021 Earnings + Slides) |
| Filing date | 2022-02-28 |
| Accession | 0001564590-22-007336 |
| Days before announcement | 501 |
| Signal type flagged | rofr_rofn |

#### Finding

Same artifact as GBT. The complete submission .txt file (EDGAR multi-document bundle) contains UUEncoded binary attachments. The collector matched "ROFR" within that encoded binary, not within any readable filing text.

The primary document (reta-8k_20220228.htm, confirmed from EDGAR index) is a standard FY2021 Earnings 8-K (Items 2.02, 7.01, 9.01) announcing financial results for the twelve months ended December 31, 2021, plus investor presentation slides for the February 28, 2022 earnings call. The full text contains no ROFR, strategic alternatives, merger, or process language. The filing was signed by COO/CFO/President Manmeet S. Soni and is an earnings announcement only.

#### False-positive check

Identical mechanism to GBT: "ROFR" appeared in UUEncoded binary in the complete submission wrapper. Primary HTML document is an earnings 8-K with no process signal.

#### Conclusion

DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE. Garbled binary artifact — no process signal in actual filing.

---

### RHC-0058-ACQUIRED-FMTX — Formation Metals (Forma Therapeutics)

**Tier:** P6
**Announcement date:** 2022-05-02
**Classification:** RIGHTS_LANGUAGE_ONLY

#### Flagged filings

| Filing | Date | Accession | Signal |
|---|---|---|---|
| DEF 14A (2021 Proxy) | 2021-04-21 | 0001628280-21-008135 | sale_process |
| 10-Q (Q1 2022) | 2022-05-10 | — | sale_process |
| 10-Q (Q2 2022) | 2022-08-08 | — | sale_process |
| 10-Q (Q3 2022) | 2022-11-07 | — | sale_process |

#### Finding

**DEF 14A:** "Sale of the Company" appears in the Change-in-Control (CIC) vesting provision of the director and officer equity award section. Language: *"subject to full accelerated vesting upon the sale of the Company, subject to such director's continued service."* This is standard CIC equity acceleration boilerplate in every public company proxy statement — it is not a disclosure that the company had initiated a sale process.

**10-Qs (all three, identical language):** "IPO, a delayed IPO, a sale of the Company and a remain private scenario" appears in the stock-based compensation footnote describing the Probability-Weighted Expected Returns Method (PWERM) used to value pre-IPO stock options. Forma Therapeutics completed its IPO in April 2020; these 10-Qs were filed post-IPO. The PWERM language is a legacy disclosure from when options were granted pre-IPO and the footnote continued to describe the original valuation methodology used at grant date.

Neither the CIC vesting clause nor the PWERM disclosure reflects a company-level process initiated by the board.

#### Conclusion

RIGHTS_LANGUAGE_ONLY. CIC vesting boilerplate and pre-IPO PWERM valuation disclosure. No company-level process evidence.

---

### RHC-0060-ACQUIRED-CINC — CinCor Pharma

**Tier:** P6
**Announcement date:** 2023-01-09
**Classification:** RIGHTS_LANGUAGE_ONLY

#### Flagged filings

| Filing | Date | Accession | Signal |
|---|---|---|---|
| 10-Q (Q1 2022) | 2022-05-12 | — | sale_process |
| 10-Q (Q2 2022) | 2022-08-10 | — | sale_process |
| 10-Q (Q3 2022) | 2022-11-10 | — | sale_process |

#### Excerpt (identical across all three filings)

> *"probability analysis of various liquidity events at that time, such as a public offering or sale of the Company, under differing scenarios"*

#### Finding

All three hits are in the stock-based compensation accounting note, describing the PWERM (Probability-Weighted Expected Returns Method) used to value equity awards granted when CinCor was a private company. CinCor completed its IPO on January 12, 2022. The Q1–Q3 2022 10-Qs disclose the valuation methodology applied to pre-IPO grants.

"Sale of the Company" in a PWERM disclosure is a required accounting disclosure about a valuation scenario used in a Monte Carlo or probability-weighted model — it is standard post-IPO disclosure for any company that granted pre-IPO options. It does not reflect a board-initiated strategic process.

#### Conclusion

RIGHTS_LANGUAGE_ONLY. Pre-IPO PWERM stock compensation valuation disclosure (three identical hits). No company-level process evidence.

---

### RHC-0063-ACQUIRED-ZYNE — Zynerba Pharmaceuticals

**Tier:** P6
**Announcement date:** 2023-10-18
**Classification:** RIGHTS_LANGUAGE_ONLY

#### Flagged filings

| Filing | Date | Accession | Signal |
|---|---|---|---|
| DEF 14A (2022 Proxy) | 2022-04-25 | — | sale_process |
| DEF 14A (2023 Proxy) | 2023-04-21 | — | sale_process |

#### Excerpt (identical across both filings)

> *"was the chief executive officer of Prism Pharmaceuticals, Inc., a venture-backed, specialty pharmaceutical company that he led from inception in September 2004 until the sale of the company to Baxter International in May"*

#### Finding

The phrase "sale of the company" appears in a director biography section describing a board member's prior professional history. The director previously served as CEO of Prism Pharmaceuticals, which was acquired by Baxter International. This sentence describes a past event at a different company, not any process at Zynerba.

Identical language appears in both the 2022 and 2023 proxy statements because the same director remained on the board. This is a false positive caused by matching "sale of the company" without entity context.

#### Conclusion

RIGHTS_LANGUAGE_ONLY. Director biography — prior company sale at a different organization. No Zynerba-level process evidence.

---

### RHC-0068-ACQUIRED-AMAM — Ambrx Biopharma

**Tier:** P6
**Announcement date:** 2024-01-08
**Classification:** RIGHTS_LANGUAGE_ONLY

#### Flagged filing

| Field | Value |
|---|---|
| Filing | 10-Q (Q3 2023) |
| Period | 2023-09-30 |
| Filing date | 2023-11-13 |
| Accession | 0000950170-23-062916 |
| Days before announcement | 56 |
| Signal type flagged | option_to_acquire |

#### Excerpt (from collector)

> *"option to acquire ordinary shares... Merger Agreement"*

#### Finding

The primary document (confirmed 479,823 chars) uses "Merger Agreement" and "option to acquire" throughout the stock option and equity award footnote — but these phrases describe an internal redomiciliation, not the J&J acquisition.

Ambrx Biopharma converted from a Cayman Islands BVI entity to a Delaware corporation in December 2022 via a statutory conversion (the "Domestication"). The conversion required recalibrating all pre-existing Cayman equity awards into Delaware-equivalent instruments. The 10-Q discloses: options originally granted as the right to acquire ordinary shares (Cayman) became options to acquire common stock (Delaware) at a 7:1 conversion ratio per the Merger Agreement governing the Domestication.

The "Merger Agreement" referenced throughout is the Domestication Merger Agreement (BVI→Delaware conversion), not any M&A transaction with an acquirer. The J&J acquisition was announced January 8, 2024 — approximately 56 days after this filing. There is no public disclosure of J&J's approach, a board process, or a retained financial advisor in this 10-Q.

#### False-positive check

"Option to acquire" + "Merger Agreement" co-occurrence came from internal redomiciliation equity conversion disclosures, not an external acquisition process. The Merger Agreement is a corporate governance document for the BVI→Delaware conversion.

#### Conclusion

RIGHTS_LANGUAGE_ONLY. Internal redomiciliation (BVI→Delaware) stock option conversion. No company-level M&A process evidence.

---

## Source Evidence Updates

No `source_evidence.csv` rows added. All 8 cases are false positives or baselines:

| Case | Classification | Source Evidence Row |
|---|---|---|
| EPZM | ASSET_SPECIFIC_RIGHTS_ONLY | Not warranted |
| GBT | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Not warranted |
| TPTX | ASSET_SPECIFIC_RIGHTS_ONLY | Not warranted |
| RETA | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Not warranted |
| FMTX | RIGHTS_LANGUAGE_ONLY | Not warranted |
| CINC | RIGHTS_LANGUAGE_ONLY | Not warranted |
| ZYNE | RIGHTS_LANGUAGE_ONLY | Not warranted |
| AMAM | RIGHTS_LANGUAGE_ONLY | Not warranted |

---

## Queue Impact

Revised effective distribution for Batch 51–70 (complete):

| Tier | Count | Cases |
|---|---|---|
| TRUE_PUBLIC_PRIOR_SIGNAL | 0 | — |
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 9 | OYST, DICE, GBT, RETA, BLU, CTIC, HARP, ISEE, CBAY, CERE, DCPH (11 total — see note) |
| RIGHTS_LANGUAGE_ONLY | 8 | IMGO, SRRA, ALPN, FMTX, CINC, ZYNE, AMAM, EPZM (EPZM = ASSET_SPECIFIC) |
| ASSET_SPECIFIC_RIGHTS_ONLY | 2 | EPZM, TPTX |

Note: DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE includes 2 from P1/P2 adjudication (OYST, DICE), 2 garbled-artifact P6 cases (GBT, RETA), and 7 confirmed no-hit P6 cases (BLU, CTIC, HARP, ISEE, CBAY, CERE, DCPH) = 11 cases.

**TRUE_PUBLIC_PRIOR_SIGNAL across all of Batch 51–70: 0**

---

## Pattern Notes

Two systematic false-positive patterns identified in this batch:

### 1. UUEncoded binary artifacts (GBT, RETA)
The collector processed EDGAR complete submission .txt files, which bundle all exhibits in old-format UUEncoding. Signal phrases (here: "ROFR") matched within encoded binary content, not readable filing text. Both GBT and RETA are routine earnings 8-Ks with no process language in the primary HTML documents. This pattern is likely present in other batches where complete submission .txt files were fetched.

### 2. Pre-IPO PWERM valuation disclosures (FMTX, CINC)
Post-IPO 10-Q stock compensation footnotes routinely describe the PWERM methodology used to value pre-IPO grants, including "sale of the Company" as one of the modeled liquidity scenarios. This phrase has zero informational content about a current strategic process — it is required accounting disclosure about past option valuation. FMTX had three 10-Q hits plus one proxy CIC clause; CINC had three identical 10-Q hits.

### 3. Director biography (ZYNE)
"Sale of the company" in a proxy biography section describes the director's prior employment history at a different company, not any process at the named issuer. Appeared in both annual proxies because the director remained on the board.

### 4. Asset-specific license ROFN (EPZM, TPTX)
Geographic/product license ROFN in collaboration agreements is not company-level acquisition process evidence. Both EPZM (Eisai Japan/Asia rights) and TPTX (Zai Lab Greater China rights) are standard biotech licensing ROFN provisions with named partners, named territories, and named product classes.

---

## Rules Applied

- No case classified TRUE_PUBLIC_PRIOR_SIGNAL.
- No case marked VERIFIED.
- No case marked CALIBRATION_ELIGIBLE.
- First-50 classifications not touched.
- Source text verified from EDGAR primary documents before adjudication.
- Binary/encoding artifacts distinguished from readable filing content.
- Asset-specific ROFN not treated as company-level process evidence.
- PWERM valuation disclosures not treated as strategic process disclosures.
- Director biographies at other companies not treated as issuer-level process evidence.
- Internal redomiciliation agreements not treated as M&A process evidence.
