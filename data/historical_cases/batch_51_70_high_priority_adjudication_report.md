# Batch 51–70 High-Priority Adjudication Report

Generated: 2026-05-15

Scope: P1 and P3 cases only (OYST, DICE, IMGO, SRRA, ALPN).
P6 cases not adjudicated here.

---

## Summary

| Case | Ticker | Tier | Classification | Signal Found |
|---|---|---|---|---|
| RHC-0055-ACQUIRED-OYST | OYST | P1 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | No |
| RHC-0061-ACQUIRED-DICE | DICE | P1 | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | No |
| RHC-0054-ACQUIRED-IMGO | IMGO | P3 | RIGHTS_LANGUAGE_ONLY | No |
| RHC-0056-ACQUIRED-SRRA | SRRA | P3 | RIGHTS_LANGUAGE_ONLY | No |
| RHC-0067-ACQUIRED-ALPN | ALPN | P3 | RIGHTS_LANGUAGE_ONLY | No |

No case classified TRUE_PUBLIC_PRIOR_SIGNAL. No case marked VERIFIED or CALIBRATION_ELIGIBLE.

---

## Case-by-Case Adjudication

---

### RHC-0055-ACQUIRED-OYST — Oyster Point Pharma

**Tier:** P1
**Announcement date:** 2022-11-08
**Classification:** DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE

#### Flagged filing

| Field | Value |
|---|---|
| Filing | 8-K, Items 8.01 / 9.01 |
| Filing date | 2022-11-07 |
| Accession | 0001193125-22-278560 |
| Days before announcement | 1 |
| Source URL | https://www.sec.gov/Archives/edgar/data/1720725/000119312522278560/d409438d8k.htm |
| Signal type flagged | acquisition_proposal |

#### Finding

The 8-K filed 2022-11-07 (one day before the recorded announcement date of 2022-11-08) **is the merger announcement itself**. The 8-K announces execution of the Merger Agreement dated November 7, 2022, via press release (Exhibit 99.1). The "acquisition proposal" phrase appears in standard forward-looking statements boilerplate: *"the possibility that competing offers or acquisition proposals for OP will be made."* This language is from the deal announcement, not a pre-announcement process disclosure.

The announcement_date in acquisition_announcement_dates.csv (2022-11-08) refers to the next-day 8-K with Item 1.01 filing the actual Merger Agreement document. The public announcement occurred November 7, 2022 — the same day as this filing. There is no true pre-announcement gap.

#### Other OYST hits reviewed

| Filing | Date | Signal | Disposition |
|---|---|---|---|
| 10-Q 2021-08-05 | 0001720725-21-000075 | rofr_rofn / sale_process | ASSET_SPECIFIC — "right of first negotiation" with Ji Xing for nAChR agonist in specific geographic territory. License agreement ROFN, not company-level. |
| DEF 14A 2022-04-22 | 0001720725-22-000036 | retained_advisor | FALSE_POSITIVE — "financial advisor" appears in director compensation table: fees paid to Versant Venture Management (Ozawa) and Invus Financial Advisors (Tsai) for board member fund affiliates. Not an engagement of strategic advisor. |

#### False-positive check

The 8-K hit: The "acquisition proposal" phrase is FLS boilerplate in the deal announcement, not a prior public proposal received by the company before announcement.

#### Conclusion

No pre-announcement public process signal. DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

---

### RHC-0061-ACQUIRED-DICE — DICE Therapeutics

**Tier:** P1
**Announcement date:** 2023-06-20
**Classification:** DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE

#### Flagged filing

| Field | Value |
|---|---|
| Filing | SC 13D/A, Amendment No. 1 |
| Filed by | RA Capital Management, L.P. (14.4% holder) |
| Filing date | 2022-10-19 |
| Accession | 0001104659-22-110002 |
| Days before announcement | 244 |
| Source URL | https://www.sec.gov/Archives/edgar/data/1645569/000110465922110002/tm2228586d1_sc13da.htm |
| Signal type flagged | acquisition_proposal |

#### Finding

Item 4 of the SC 13D/A reads verbatim:

> *"The Reporting Persons acquired the Common Stock reported herein for investment purposes and not with an intent, purpose or effect of changing control of the Issuer. Although the Reporting Persons currently have **no plan or proposal to acquire any additional Issuer securities** or to dispose of any of the Issuer securities reported herein, the Reporting Persons may acquire additional Issuer securities from time to time or dispose of Issuer securities they beneficially own, on the open market or in private transactions or otherwise..."*

The collector flagged "proposal to acquire" because the phrase appears in the NEGATIVE context: "**no** plan or proposal to acquire." This is a false positive.

RA Capital is a passive healthcare investor filing an amendment after purchasing additional shares in DICE's IPO (October 2022). There is no acquisition pressure, strategic alternatives language, or company-level process language anywhere in the filing.

#### False-positive check

The phrase "proposal to acquire" appears in the sentence: "currently have no plan or **proposal to acquire** any additional Issuer securities." The collector's signal detection matched the phrase without considering negation. This is a confirmed false positive.

#### Conclusion

No pre-announcement public process signal. DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

---

### RHC-0054-ACQUIRED-IMGO — Imago BioSciences

**Tier:** P3
**Announcement date:** 2022-11-21
**Classification:** RIGHTS_LANGUAGE_ONLY

#### Flagged filing

| Field | Value |
|---|---|
| Filing | SC 13D, initial filing |
| Filed by | Clarus Lifesciences III, L.P. / Blackstone (10.5% holder, IPO-era filing) |
| Filing date | 2021-07-30 |
| Accession | 0001193125-21-231566 |
| Days before announcement | 479 |
| Source URL | https://www.sec.gov/Archives/edgar/data/1623715/000119312521231566/d190730dsc13d.htm |
| Signal type flagged | strategic_alternatives |

#### Finding

Clarus Lifesciences III (a Blackstone entity) filed its initial SC 13D at Imago's IPO on July 20, 2021 as a crossing-10% reporting obligation. Item 4 contains standard VC/PE investor boilerplate:

> *"The Reporting Persons intend to review their investment in the Issuer on an ongoing basis and, in the course of their review, may take actions... including... evaluating strategic alternatives as they may become available. Such discussions and other actions may relate to various alternative courses of action, including, without limitation, those related to an extraordinary corporate transaction (including, but not limited to a merger, reorganization or liquidation)... Such discussions and actions may be preliminary and exploratory in nature, and not rise to the level of a plan or proposal."*

This is the standard VC/PE boilerplate reserving the right to engage in strategic activity regarding the investor's own investment. The phrase "evaluating strategic alternatives" modifies the **investor's position**, not the company's. The filing explicitly disclaimed any current plan or proposal and was filed solely because Clarus crossed 10% at IPO.

There is no evidence the company (Imago BioSciences) had initiated, announced, or disclosed a strategic alternatives process.

#### False-positive check

"Strategic alternatives" appears in the context of investor self-reservation language, not company-level process announcement. The filing was triggered by an IPO crossing event, not a change in activist stance. Blackstone/Clarus had a pre-IPO investment and was the company's founding investor — this is a passive IPO-era 13D.

#### Conclusion

No company-level process language. Standard PE/VC investor SC 13D boilerplate. RIGHTS_LANGUAGE_ONLY.

---

### RHC-0056-ACQUIRED-SRRA — Sierra Oncology

**Tier:** P3
**Announcement date:** 2022-04-13
**Classification:** RIGHTS_LANGUAGE_ONLY

#### Flagged filing

| Field | Value |
|---|---|
| Filing | SC 13D/A, Amendment No. 2 |
| Filed by | OrbiMed Advisors LLC (15.3% holder) |
| Filing date | 2022-02-02 |
| Accession | 0000947871-22-000128 |
| Days before announcement | 70 |
| Source URL | https://www.sec.gov/Archives/edgar/data/1290149/000094787122000128/ss772256_sc13da.htm |
| Signal type flagged | rofr_rofn |

#### Finding

OrbiMed Advisors filed Amendment No. 2 to update its 13D position after exercising Series B Warrants in SRRA's follow-on offering (Rule 424(b)(5) Prospectus filed January 27, 2022). Item 4 is entirely passive investment language:

> *"The Shares were initially acquired by the Reporting Persons for the purpose of making an investment in the Issuer and not with the intention of acquiring control of the Issuer's business... Except as set forth in this Schedule 13D, the Reporting Persons have not formulated any plans or proposals which relate to or would result in: (a) the acquisition by any person of additional securities... (b) an extraordinary corporate transaction, such as a merger, reorganization or liquidation..."*

The "right of first refusal" phrase flagged by the collector does not appear in the primary SC 13D/A document at all. It appears in Exhibit 99.3 (Form of Lock-Up Agreement) from the follow-on offering, in the context of share repurchase rights upon termination of service — standard lock-up provision language about the company's right to repurchase shares held by a departing employee or service provider. The original collector excerpt begins with "ermination of employment," confirming it is employment-termination repurchase ROFR, not company-level acquisition ROFR.

#### False-positive check

ROFR language in lock-up agreement exhibit refers to share repurchase rights upon employee termination. This is a standard shareholder rights provision in offering lock-ups, not company-level acquisition process evidence. OrbiMed is a passive healthcare investor with no stated acquisition intent.

#### Conclusion

No company-level ROFR or process language. RIGHTS_LANGUAGE_ONLY.

---

### RHC-0067-ACQUIRED-ALPN — Alpine Immune Sciences

**Tier:** P3
**Announcement date:** 2024-04-10
**Classification:** RIGHTS_LANGUAGE_ONLY

#### Flagged filing

| Field | Value |
|---|---|
| Filing | SC 13D/A, Amendment No. 7 |
| Filed by | OrbiMed Advisors LLC (7.3% holder) |
| Filing date | 2023-11-13 |
| Accession | 0000947871-23-001055 |
| Days before announcement | 149 |
| Source URL | https://www.sec.gov/Archives/edgar/data/1626199/000094787123001055/ss2696773_sc13da.htm |
| Signal type flagged | sale_process |

#### Finding

OrbiMed Advisors filed Amendment No. 7 to update its 13D position after participating in ALPN's underwritten follow-on offering (Rule 424(b)(5) Prospectus filed November 8, 2023). Item 4 is entirely passive investment language with no strategic alternatives, acquisition proposals, or sale process language:

> *"The Reporting Persons from time to time intend to review their investment in the Issuer... Except as set forth in this Schedule 13D, the Reporting Persons have not formulated any plans or proposals which relate to or would result in: (a) the acquisition by any person of additional securities... (b) an extraordinary corporate transaction, such as a merger, reorganization or liquidation..."*

The "sale of the Company's securities" phrase that triggered the collector does not appear in the primary SC 13D/A document. It appears in Exhibit 99.3 (Form of Lock-Up Agreement), in the context of lock-up restrictions on when OrbiMed may sell "the Company's securities" it acquired in the offering. This refers to OrbiMed selling its ALPN shares — not ALPN being sold as a company.

The original collector excerpt: *"all be made voluntarily in connection with subsequent sales of Common Stock or other securities acquired in the Public Offering or such open market transactions; (5) the sale of the Company's securiti[es]"* confirms this is about securities sale restrictions in a lock-up agreement, not a strategic process announcement.

#### False-positive check

"Sale of the Company's securities" in a lock-up agreement means the holder selling their investment shares, not the company pursuing a sale. OrbiMed participates in follow-on offerings as a passive holder and was filing routine ownership updates.

#### Conclusion

No company-level process language. Lock-up agreement artifact. RIGHTS_LANGUAGE_ONLY.

---

## Source Evidence Updates

No `source_evidence.csv` rows added. Classifications are:
- OYST: DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE — no source evidence row warranted (no prior signal found)
- DICE: DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE — no source evidence row warranted
- IMGO: RIGHTS_LANGUAGE_ONLY — no source evidence row warranted
- SRRA: RIGHTS_LANGUAGE_ONLY — no source evidence row warranted
- ALPN: RIGHTS_LANGUAGE_ONLY — no source evidence row warranted

The draft placeholder rows in `batch_51_70_source_evidence_draft.csv` for all 5 cases remain DRAFT_PENDING_REVIEW and should not be promoted to `source_evidence.csv`.

---

## Queue Impact

All 5 previously P1/P3 cases are now confirmed as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE or RIGHTS_LANGUAGE_ONLY. The revised effective distribution for Batch 51–70:

| Tier | Count | Cases |
|---|---|---|
| TRUE_PUBLIC_PRIOR_SIGNAL | 0 | — |
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 2 | OYST, DICE |
| RIGHTS_LANGUAGE_ONLY | 3 | IMGO, SRRA, ALPN |
| P6 (POSSIBLE_HIT rows, unreviewed) | 8 | EPZM, FMTX, GBT, TPTX, CINC, RETA, ZYNE, AMAM |
| P6 (confirmed no-hit) | 7 | BLU, CTIC, HARP, ISEE, CBAY, CERE, DCPH |

---

## Unresolved Cases

None from the P1/P3 group. All 5 cases reached a clear determination without ambiguity. No case requires further escalation or POSSIBLE_SIGNAL_NEEDS_REVIEW status.

---

## Next Steps

1. Mark OYST and DICE as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE in the prior signal adjudication queue (when that workflow is run).
2. Mark IMGO, SRRA, ALPN as RIGHTS_LANGUAGE_ONLY in the adjudication queue.
3. Review the 8 P6 cases with POSSIBLE_HIT rows before marking them as baselines:
   - EPZM, GBT, TPTX, RETA: rofr_rofn hits — verify company-level vs asset-level scope
   - FMTX, CINC, ZYNE: sale_process hits — likely compensation-plan language in 10-Q/DEF14A
   - AMAM: option_to_acquire hit — verify company-level vs asset/IP scope
4. The 7 confirmed no-hit P6 cases (BLU, CTIC, HARP, ISEE, CBAY, CERE, DCPH) can be marked DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE at any time.

---

## Rules Applied

- No case classified TRUE_PUBLIC_PRIOR_SIGNAL.
- No case marked VERIFIED.
- No case marked CALIBRATION_ELIGIBLE.
- First-50 classifications not touched.
- Source text verified from EDGAR archive before adjudication.
- No ambiguous case forced to a classification.
