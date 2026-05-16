# Batch 71–100 Adjudication Queue

Generated: 2026-05-16
Status: Review preparation only. No classifications made. No cases adjudicated.

---

## 1. Queue Summary

| Category | Count |
|---|---|
| Total candidates | 26 |
| Dated cases processed (EDGAR API) | 16 |
| Filing target rows collected | 427 |
| Possible signal hit rows | 25 |
| Cases flagged for manual review | 11 |
| Likely clean no-hit cases | 5 |
| Blocked (missing date) | 10 |

Combined true prior signal rate through case 70: **3/70 (4.3%)**

---

## 2. False-Positive Decision Tree (apply before any classification)

1. **Was the filing date before the acquisition announcement date?**
   - NO → not `TRUE_PUBLIC_PRIOR_SIGNAL`

2. **Is this equity plan / S-8 / 424B3 boilerplate?**
   - Look for: "Form S-8 Registration Statement... offer or the sale of the Company's securities to such person"
   - Or: anti-takeover provisions / defensive disclosure sections
   - YES → `RIGHTS_LANGUAGE_ONLY` (BOILERPLATE)

3. **Is this a director biography referencing a prior employer's sale?**
   - YES → `RIGHTS_LANGUAGE_ONLY`

4. **Is this a performance condition in equity award accounting language?**
   - "a change in control or a sale of the company, no expense is recognized..."
   - YES → `RIGHTS_LANGUAGE_ONLY`

5. **Is this a UUEncoded binary artifact in a complete submission .txt?**
   - Garbled binary text with keywords embedded in encoding → not in primary document
   - YES → false positive — discard

6. **Is the target the one acquiring (not being acquired)?**
   - e.g., Target company exercising its own option to acquire another entity
   - YES → not process evidence — discard

7. **Is the ROFR/ROFN asset-specific (product, territory, program) not company-level?**
   - YES → `ASSET_SPECIFIC_RIGHTS_ONLY`

8. **Is the "sale of Company" language about an equity stake sale by a partner, not the company itself?**
   - e.g., Partner terminating collaboration and selling equity investment
   - YES → `RIGHTS_LANGUAGE_ONLY`

9. **Is it a warranty that ROFR/ROFN does NOT apply?**
   - "not subject to any agreement granting a right of first refusal..."
   - YES → `RIGHTS_LANGUAGE_ONLY`

10. **Is it explicit pre-announcement proposal, strategic alternatives, or sale process language with source URL + excerpt?**
    - YES → possible `TRUE_PUBLIC_PRIOR_SIGNAL`; requires all evidence fields before upgrading

---

## 3. Ranked Review Cases

### PRIORITY 1 — Manual source pull recommended

---

#### P1-A: SGEN (Seagen Inc.)

| Field | Value |
|---|---|
| case_id | RHC-0106-ACQUIRED-SGEN |
| Announcement date | 2023-03-13 |
| Acquirer | Pfizer |
| Date confidence | HIGH |
| Hit count | 2 |
| Signal types | rofr_rofn |
| Keywords | "rofn" |
| Filing type | 8-K (×2) |
| Filing dates | 2021-09-21 (both) |
| Days before announcement | ~538 days |

**Hit 1 — Accession 0001193125-21-277501**
- URL: https://www.sec.gov/Archives/edgar/data/1060736/000119312521277501/0001193125-21-277501-index.htm
- Excerpt: Garbled binary artifact (UUEncoded .txt embedding): "9$ZA&]P7H:!HF[9I MF)91LG))]4@::A0R.6[3H;)..."
- Classification clue: This matches the **UUEncoded binary artifact** false-positive pattern from the first-50 playbook. The "ROFN" characters appear in encoded binary data, not in the primary filing document.

**Hit 2 — Accession 0001193125-21-278354**
- URL: https://www.sec.gov/Archives/edgar/data/1060736/000119312521278354/0001193125-21-278354-index.htm
- Excerpt: "RemeGen Continuing Technology Transfer 2.12(a) RemeGen Initial Technology Transfer 2.12(a) ROFN Notice 2.5 Royalty Floor 8.5(c)(v) Rules 15.5(a) Safety Auditing Party 5.5 Seagen Preamble Seagen [ * ] Technology Transfer 2.12(b)(ii)"
- Classification clue: "ROFN Notice 2.5" is a defined term in the Seagen-RemeGen licensing collaboration agreement. This is a **licensing agreement ROFN in a defined-terms table**, not a company-acquisition ROFN.

**Background:** September 2021 is when Pfizer-Seagen M&A discussions reportedly ended (Merck had also reportedly discussed an offer earlier that year). The two 8-Ks appear to be the Seagen-RemeGen antibody licensing agreement filing, not related to company acquisition discussions.

**Likely false-positive pattern:** ASSET_SPECIFIC_RIGHTS_ONLY (ROFN defined term in licensing agreement) + binary artifact in Hit 1.

**Next inspection action:**
1. Open accession 0001193125-21-278354-index.htm — confirm it is the Seagen-RemeGen collaboration filing
2. Check whether "ROFN" appears in primary filing document or only in exhibits/encoded attachments
3. Confirm scope is asset/program-specific (RemeGen compound licensing), not company-level
4. If confirmed licensing ROFN → classify ASSET_SPECIFIC_RIGHTS_ONLY; source evidence not required for non-TRUE classifications

```bash
python3 src/historical_case_tools/edgar_source_pull_helper.py \
  --url "https://www.sec.gov/Archives/edgar/data/1060736/000119312521278354/0001193125-21-278354-index.htm" \
  --case-id "RHC-0106-ACQUIRED-SGEN" \
  --ticker "SGEN" \
  --filing-type "8-K" \
  --find "right of first negotiation" \
  --find "acquire" \
  --find "company-level"
```

---

#### P1-B: TBIO (Translate Bio)

| Field | Value |
|---|---|
| case_id | RHC-0132-ACQUIRED-TBIO |
| Announcement date | 2021-08-03 |
| Acquirer | Sanofi |
| Date confidence | HIGH |
| Hit count | 1 |
| Signal types | option_to_acquire |
| Keywords | "option to acquire" |
| Filing type | 8-K |
| Filing date | 2020-06-23 |
| Days before announcement | 406 days |

**Hit — Accession 0001193125-20-175955**
- URL: https://www.sec.gov/Archives/edgar/data/1693415/000119312520175955/0001193125-20-175955-index.htm
- Excerpt: "the license option in the Agreement, under which Sanofi Pasteur had an option to acquire licenses to additional pathogens from the Company, has been removed from the Agreement under the Amendment. Pursuant to the Amendment, Sanofi Pasteur agreed to concurrently enter into the Securities Purchase Agreement..."

**Classification clue:** The option described is **Sanofi Pasteur's option to acquire licenses to additional pathogens** — an asset-specific option in a vaccine collaboration. This is not an option to acquire TBIO as a company. The option was also **removed** (not exercised).

**Context:** This 8-K was filed during COVID-19 mRNA vaccine collaboration expansion between Translate Bio and Sanofi Genzyme. Sanofi eventually acquired Translate Bio (the whole company) 13 months later for its mRNA platform. The eventual acquirer is Sanofi's parent organization.

**Likely false-positive pattern:** ASSET_SPECIFIC_RIGHTS_ONLY. The option was for licenses to additional pathogen programs, not for company acquisition. Option was removed, not exercised.

**Next inspection action:**
1. Open accession 0001193125-20-175955-index.htm
2. Confirm the option is for pathogen licenses, not company acquisition
3. Confirm no separate mention of strategic discussions or sale-of-company process
4. If asset-specific license option only → ASSET_SPECIFIC_RIGHTS_ONLY

```bash
python3 src/historical_case_tools/edgar_source_pull_helper.py \
  --url "https://www.sec.gov/Archives/edgar/data/1693415/000119312520175955/0001193125-20-175955-index.htm" \
  --case-id "RHC-0132-ACQUIRED-TBIO" \
  --ticker "TBIO" \
  --filing-type "8-K" \
  --find "option to acquire" \
  --find "strategic" \
  --find "sale of the company"
```

---

### PRIORITY 2 — Review excerpt context; likely false positive

---

#### P2-A: VSTM (Verastem Oncology)

| Field | Value |
|---|---|
| case_id | RHC-0140-ACQUIRED-VSTM |
| Announcement date | 2024-01-08 |
| Acquirer | Pfizer |
| Date confidence | MEDIUM |
| Hit count | 2 |
| Signal types | rofr_rofn, sale_process |
| Keywords | "right of first refusal", "sale of the company" |
| Filing types | 8-K (×2) |
| Filing dates | 2022-11-07 (~427 days before), 2023-06-21 (~201 days before) |

**Hit 1 — 2022-11-07, Accession 0001104659-22-115103**
- URL: https://www.sec.gov/Archives/edgar/data/1526119/000110465922115103/0001104659-22-115103-index.htm
- Keywords: "right of first refusal"
- Excerpt: "not subject to, any agreement, understanding or other arrangement (i) granting any option, warrant or right of first refusal with respect to such Shares to any person, (ii) restricting its right to surrender and exchange such Shares..."
- **Classification clue:** This is a **warranty that ROFR does NOT exist** — the text explicitly states the shares are NOT subject to ROFR. This is a standard representation in a share exchange agreement. Not a process signal.

**Hit 2 — 2023-06-21, Accession 0001104659-23-073116**
- URL: https://www.sec.gov/Archives/edgar/data/1526119/000110465923073116/0001104659-23-073116-index.htm
- Keywords: "sale of the company"
- Excerpt: "nor shall there be any sale of the Company's securities in any state or jurisdiction in which such offer, solicitation or sale would be unlawful prior to registration..."
- **Classification clue:** Standard **securities offering prospectus / registration statement** disclaimer. Not a process signal.

**Likely false-positive pattern:** Hit 1 = ROFR warranty (negative); Hit 2 = securities offering boilerplate.

**Next inspection action:**
1. Confirm filing 2022-11-07 is a share exchange or similar transaction (not M&A-related)
2. Confirm filing 2023-06-21 is a securities registration or offering
3. If confirmed → RIGHTS_LANGUAGE_ONLY (both hits)

---

#### P2-B: LBPH (Longboard Pharmaceuticals)

| Field | Value |
|---|---|
| case_id | RHC-0077-ACQUIRED-LBPH |
| Announcement date | 2024-10-15 |
| Acquirer | UCB |
| Date confidence | HIGH |
| Hit count | 2 |
| Signal types | sale_process, rofr_rofn |
| Keywords | "sale of the company", "right of first negotiation" |
| Filing types | 8-K, 10-K |
| Filing dates | 2024-01-02 (~287 days before), 2024-03-12 (~217 days before) |

**Hit 1 — 2024-01-02, 8-K, Accession 0001193125-24-000675**
- URL: https://www.sec.gov/Archives/edgar/data/1832168/000119312524000675/0001193125-24-000675-index.htm
- Keywords: "sale of the company"
- Excerpt: "securities of the Company, which is being made only by means of a written prospectus meeting the requirements of Section 10 of the Securities Act nor shall there be any sale of the Company's securities in any state or jurisdiction..."
- **Classification clue:** Standard **securities offering prospectus** disclaimer (same pattern as VSTM Hit 2). Not a process signal.

**Hit 2 — 2024-03-12, 10-K, Accession 0000950170-24-029952**
- URL: https://www.sec.gov/Archives/edgar/data/1832168/000095017024029952/0000950170-24-029952-index.htm
- Keywords: "right of first negotiation"
- Excerpt: "provide Arena a right of first negotiation to acquire certain development and commercial rights to LP659 products"
- **Classification clue:** Arena (now part of Pfizer post-2022 acquisition) holds ROFN on specific development/commercial rights to LP659 — **asset-specific ROFN on a drug program**. Acquirer was UCB, not Arena/Pfizer.

**Likely false-positive pattern:** Hit 1 = prospectus boilerplate; Hit 2 = asset-specific ROFN (Arena on LP659 rights; UCB was acquirer).

**Next inspection action:**
1. Confirm 8-K (2024-01-02) is a prospectus filing, not a process disclosure
2. Confirm LP659 ROFN is asset-specific (commercial rights to program only, not whole company)
3. Confirm acquirer UCB had no prior ROFN or preferential arrangement
4. If confirmed → Hit 1 = BOILERPLATE; Hit 2 = ASSET_SPECIFIC_RIGHTS_ONLY

---

#### P2-C: G1T (G1 Therapeutics)

| Field | Value |
|---|---|
| case_id | RHC-0074-ACQUIRED-G1T |
| Announcement date | 2024-08-07 |
| Acquirer | Boehringer Ingelheim |
| Date confidence | HIGH |
| Hit count | 4 |
| Signal types | rofr_rofn, sale_process |
| Keywords | "right of first negotiation", "sale of the company" |
| Filing types | 10-Q (×4) |
| Filing dates | 2023-05-03, 2023-08-02, 2023-11-01, 2024-05-01 |

**All 4 hits — same excerpt repeated across quarterly filings:**
- Accessions: 0001628280-23-015220, 0001628280-23-026769, 0001628280-23-035947, 0001628280-24-019622
- Excerpt (all identical): "The Company has right of first negotiation to re-acquire these assets. In the first quarter of 2022, Incyclix announced a new round of financing which the Company did not participate. Following the financing, the Company's equity interest is now approximately 6."
- **Classification clue:** G1T holds ROFN to **re-acquire assets it licensed out** to Incyclix (G1T's own compound, rintodestrant, licensed to a spinout). This is G1T's own right over its outbound-licensed compound. It is not anyone's right to acquire G1T. Acquirer was Boehringer Ingelheim.

**Likely false-positive pattern:** ASSET_SPECIFIC_RIGHTS_ONLY (G1T ROFN to re-acquire its own licensed compound from Incyclix). 4 identical hits = same boilerplate disclosure repeated in consecutive quarterly filings.

**Next inspection action:**
1. Confirm ROFN is G1T's right over its own licensed compound, not a right held by acquirer BI
2. Confirm "sale of the company" phrase is in same passage as the Incyclix ROFN, not in a separate strategic-alternatives context
3. If confirmed → ASSET_SPECIFIC_RIGHTS_ONLY

---

### PRIORITY 3 — Likely boilerplate / wrong-direction; spot-check

---

#### P3-A: HZNP (Horizon Therapeutics)

| Field | Value |
|---|---|
| case_id | RHC-0105-ACQUIRED-HZNP |
| Announcement date | 2022-12-12 |
| Acquirer | Amgen |
| Date confidence | MEDIUM |
| Hit count | 3 |
| Signal types | sale_process, option_to_acquire (×2) |
| Keywords | "sale of the company", "option to acquire" |
| Filing types | 8-K, 10-Q, 8-K |
| Filing dates | 2022-05-02, 2022-11-02, 2022-11-02 |

**Hit 1 — 2022-05-02, 8-K, Accession 0001193125-22-134596**
- Excerpt: "Form S-8 Registration Statement under the Securities Act is available to register either the offer or the sale of the Company's securities to such person" — S-8 equity plan boilerplate. Not a process signal.

**Hits 2–3 — 2022-11-02, 10-Q + 8-K, Accessions 0000950170-22-020973, 0001193125-22-275395**
- Excerpt: "the Company received an option to acquire the ADX-914 program, exercisable through a period of time following completion of certain planned Phase 2a trials"
- **Classification clue:** HZNP acquired an option to buy ADX-914 from Q32 Bio — **HZNP is the acquirer of an asset, not a target**. Wrong direction. Not evidence of someone proposing to acquire HZNP.

**Likely false-positive pattern:** Hit 1 = S-8 equity plan boilerplate; Hits 2–3 = HZNP acquiring ADX-914 (wrong direction, asset-level).

**Next inspection action:** Confirm filing types match S-8/equity plan (Hit 1) and ADX-914 acquisition option (Hits 2–3). If confirmed → RIGHTS_LANGUAGE_ONLY (Hit 1); irrelevant (Hits 2–3). Classify HZNP as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

---

#### P3-B: SNDX (Syndax Pharmaceuticals)

| Field | Value |
|---|---|
| case_id | RHC-0107-ACQUIRED-SNDX |
| Announcement date | 2023-12-15 |
| Acquirer | Incyte |
| Date confidence | MEDIUM |
| Hit count | 2 |
| Signal types | sale_process (×2) |
| Keywords | "sale of the company" |
| Filing types | 10-Q, 10-Q |
| Filing dates | 2022-08-08, 2022-11-03 |

**Both hits — same context repeated:**
- Accessions: 0000950170-22-015523, 0000950170-22-021848
- Excerpt: "Incyte to terminate the Incyte Agreement under circumstances under which the upfront payment of $117 million would be returned to Incyte and a cash settlement on the sale of the Company's common stock would be made to make the parties whole"
- **Classification clue:** "Sale of the Company's common stock" = Incyte selling its **equity stake in SNDX** as part of a collaboration termination settlement. This is a partner selling shares — not a company sale process. Note: Incyte later acquired SNDX in 2023. The termination described was of a prior Incyte-Syndax collaboration.

**Likely false-positive pattern:** "sale of Company's common stock" = partner equity stake divestiture in collaboration termination, not company-level sale process.

**Next inspection action:** Confirm context is Incyte-Syndax collaboration termination settlement. Classify SNDX as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

---

### PRIORITY 4 — Near-certain false positive; confirm and close

---

#### P4-A: STML (Stemline Therapeutics)

| Field | Value |
|---|---|
| case_id | RHC-0103-ACQUIRED-STML |
| Announcement date | 2020-05-04 |
| Acquirer | Menarini Group |
| Date confidence | MEDIUM |
| Hit count | 5 |
| Signal types | sale_process (×5) |
| Keywords | "sale of the company" |
| Filing types | 10-K, 10-Q, 10-Q, 10-Q, 10-K |
| Filing dates | 2019-03-15, 2019-05-10, 2019-08-06, 2019-11-12, 2020-03-16 |

**Hits 1 and 5 — Director bio in 10-K:**
- Excerpt: "responsible for the acquisition and development of the company's clinical stage assets and ultimately the sale of the company to Keryx Biopharmaceuticals, Inc."
- **Classification clue:** Director biography describing a prior employer's (not STML's) acquisition. Director bio false positive — established first-50 pattern.

**Hits 2–4 — Performance condition boilerplate in 10-Q:**
- Excerpt: "For awards with performance conditions, such as obtaining regulatory approval on a developed product, capital raises, a change in control or a sale of the company, no expense is recognized, and no measurement date can occur, until the occurrence of the event is probable."
- **Classification clue:** Standard equity award performance condition accounting language (GAAP disclosure). Not a process signal.

**Next inspection action:** Confirm both patterns exist without checking further. Classify STML as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

---

#### P4-B: MRTX (Mirati Therapeutics)

| Field | Value |
|---|---|
| case_id | RHC-0079-ACQUIRED-MRTX |
| Announcement date | 2023-10-10 |
| Acquirer | Bristol-Myers Squibb |
| Date confidence | HIGH |
| Hit count | 1 |
| Signal types | sale_process |
| Keywords | "sale of the company" |
| Filing type | 8-K |
| Filing date | 2022-05-12 |
| Days before announcement | ~516 days |

**Hit — Accession 0001628280-22-014127**
- URL: https://www.sec.gov/Archives/edgar/data/1576263/000162828022014127/0001628280-22-014127-index.htm
- Excerpt: "Form S-8 Registration Statement under the Securities Act is available to register either the offer or the sale of the Company's securities to such person. (q) "Continuous Service" means that the Participant's service with the Company..."
- **Classification clue:** Identical S-8 equity compensation plan boilerplate to HZNP Hit 1 and MRTX pattern. Routine equity plan filing.

**Next inspection action:** Confirm 8-K is an equity plan filing (S-8 or plan amendment). Classify MRTX as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

---

#### P4-C: ALBO (Albireo Pharma)

| Field | Value |
|---|---|
| case_id | RHC-0104-ACQUIRED-ALBO |
| Announcement date | 2023-01-09 |
| Acquirer | Ipsen |
| Date confidence | HIGH |
| Hit count | 1 |
| Signal types | acquisition_proposal, unsolicited_proposal |
| Keywords | "acquisition proposal", "unsolicited acquisition proposal" |
| Filing type | 424B3 |
| Filing date | 2022-08-25 |
| Days before announcement | 137 days |

**Hit — Accession 0001104659-22-094468**
- URL: https://www.sec.gov/Archives/edgar/data/1322505/000110465922094468/0001104659-22-094468-index.htm
- Excerpt: "reduce our vulnerability to an unsolicited acquisition proposal and to discourage certain tactics that may be used in proxy fights. Such provisions are designed to reduce our vulnerability... Delaware Statutory Business Combinations Provision We are subject to"
- **Classification clue:** **Anti-takeover provisions section** in a prospectus (424B3). Describes defensive mechanisms designed to reduce vulnerability to unsolicited proposals. This is standard boilerplate in prospectus filings disclosing anti-takeover measures — not an actual acquisition proposal against Albireo.

**Next inspection action:** Confirm filing is a 424B3 prospectus with standard anti-takeover provision disclosure. Classify ALBO as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

---

#### P4-D: CHMA (Chiasma)

| Field | Value |
|---|---|
| case_id | RHC-0101-ACQUIRED-CHMA |
| Announcement date | 2021-05-05 |
| Acquirer | Strongbridge Biopharma |
| Date confidence | HIGH |
| Hit count | 2 |
| Signal types | retained_advisor (×2) |
| Keywords | "financial advisor" |
| Filing types | DEF 14A, DEF 14A |
| Filing dates | 2020-04-28, 2021-04-26 |

**Both hits — Director biographies in proxy statements:**
- Accessions: 0001193125-20-123025, 0001193125-21-131446
- Excerpt (2020): "his financial expertise and his years of experience providing strategic and financial advisory services to biopharmaceutical organizations"
- Excerpt (2021): similar director bio language
- **Classification clue:** "Financial advisor" keyword hit in director bios describing a board member's prior career. Not evidence of M&A advisor retention in connection with a sale process.

**Next inspection action:** Confirm both filings are DEF 14A proxy statements with director biography sections. Classify CHMA as DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE.

---

## 4. Likely Clean No-Hit Cases

These 5 cases had confirmed dates and received filing collection but no possible signal hits. No manual review required. Proposed: `DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE`.

| Ticker | case_id | Announcement date | Date confidence | Acquirer |
|---|---|---|---|---|
| CNST | RHC-0102-ACQUIRED-CNST | 2021-06-02 | HIGH | MorphoSys |
| FUSN | RHC-0073-ACQUIRED-FUSN | 2024-03-19 | MEDIUM | AstraZeneca |
| KROS | RHC-0138-ACQUIRED-KROS | 2024-12-03 | MEDIUM | AstraZeneca |
| KRTX | RHC-0076-ACQUIRED-KRTX | 2023-12-22 | MEDIUM | Bristol-Myers Squibb |
| MORF | RHC-0078-ACQUIRED-MORF | 2024-07-08 | MEDIUM | AbbVie |

These require researcher spot-check only. Final classification pending source review. Do not mark VERIFIED without manual confirmation.

---

## 5. Blocked Missing-Date Cases

Keep all 10 BLOCKED until dates are confirmed in `acquisition_announcement_dates.csv` with `confidence=HIGH` or `MEDIUM`. Do not attempt filing collection without confirmed dates.

| Ticker | case_id | Year | Backfill status |
|---|---|---|---|
| ENLV | RHC-0134-ACQUIRED-ENLV | 2023 | No Item 1.01 8-K found |
| FATE | RHC-0072-ACQUIRED-FATE | 2024 | LOW confidence only — skipped |
| GRCL | RHC-0075-ACQUIRED-GRCL | 2024 | No Item 1.01 8-K found |
| HRMY | RHC-0135-ACQUIRED-HRMY | 2023 | LOW confidence only — skipped |
| KPTI | RHC-0137-ACQUIRED-KPTI | 2024 | LOW confidence only — skipped |
| LMNX | RHC-0131-ACQUIRED-LMNX | 2021 | CIK not found |
| MOR | RHC-0109-ACQUIRED-MOR | 2024 | No Item 1.01 8-K found (FPI) |
| SYNH | RHC-0136-ACQUIRED-SYNH | 2023 | LOW confidence only — skipped |
| TGTX | RHC-0139-ACQUIRED-TGTX | 2024 | LOW confidence only — skipped |
| VECT | RHC-0108-ACQUIRED-VECT | 2023 | No Item 1.01 8-K found |

EDGAR work queue: `batch_71_100_date_prefill_queue.csv` (EDGAR search URLs for each).

---

## 6. Adjudication Execution Order

```
Phase 1 (manual source pull — use edgar_source_pull_helper.py):
  1. SGEN — confirm ROFN is in licensing agreement (RemeGen collaboration), not company-level
  2. TBIO — confirm option is for pathogen licenses (not company acquisition)

Phase 2 (excerpt context check — open filing index, read context):
  3. VSTM — confirm ROFR warranty (negative) + offering prospectus
  4. LBPH — confirm Arena ROFN is LP659-specific; UCB was acquirer
  5. G1T  — confirm G1T's own ROFN to re-acquire Incyclix compound

Phase 3 (confirm and close — verify filing type only):
  6. HZNP — S-8 boilerplate + ADX-914 acquisition option (HZNP as buyer)
  7. SNDX — Incyte equity stake termination settlement

Phase 4 (confirm and close — known patterns):
  8. STML — director bio + performance condition boilerplate
  9. MRTX — S-8 equity plan boilerplate
  10. ALBO — 424B3 anti-takeover provision disclosure
  11. CHMA — proxy director bio
```

After each confirmed false positive → write no source evidence row. Classify as indicated. Update `acquisition_prior_signal_batch_results.csv` after all Phase 1–4 decisions are made.

---

## 7. What Qualifies as TRUE_PUBLIC_PRIOR_SIGNAL

Based on the 70-case standard:

| Requirement | Must satisfy |
|---|---|
| Public filing | SEC filing (8-K, 10-Q, 10-K, DEF 14A, SC 13D) — not post-announcement SC 14D-9 |
| Filing date | Before acquisition announcement date |
| Scope | Company-level — not asset, program, or territory-specific |
| Language | Explicit: "unsolicited proposal," "superior proposal," "acquisition proposal," "strategic alternatives" with banker/advisor context, "sale of the company" in a sale-process context |
| Source evidence | source_url + accession_number + verbatim excerpt + days_before_announcement |
| Not boilerplate | Not anti-takeover disclosure, not equity plan, not performance condition clause |
| Not proxy background | Not disclosed for the first time in SC 14D-9 or proxy deal background section |

Expected base rate in this batch: 0–1 case (consistent with 4.3% rate through case 70).

---

*This document is review preparation only. No cases adjudicated. All classification decisions require manual researcher review.*
