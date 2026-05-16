# Batch 71–100 Manual Review Packet

Generated: 2026-05-16 (updated post-EDGAR filing collection)
Updated: 2026-05-16 (adjudication complete for 16 dated cases)
Status: ADJUDICATION COMPLETE — 16 dated cases finalized. 10 blocked cases pending date resolution.

---

## 1. Scope

| Metric | Value |
|---|---|
| Cases in scope | 71–100 (30 target) |
| Candidates available | 26 |
| Dated cases (EDGAR filing collection ran) | 16 |
| Blocked cases (date missing) | 10 |
| Filing target rows collected | 427 |
| Possible signal hit rows | 25 |
| Cases flagged for manual review | 11 |
| Likely clean no-hit cases | 5 |
| True prior signal rate through case 70 | 3/70 (4.3%) |
| TRUE_PUBLIC_PRIOR_SIGNAL (this batch) | 0 |
| Cumulative signal rate (cases 1–86) | 3/86 (3.5%) |
| Adjudication status | COMPLETE (dated cases) |

---

## 2. Review Order

| Priority | Tier | Cases | Review trigger |
|---|---|---|---|
| 1st | P1 (manual source pull) | SGEN, TBIO | ROFN / option-to-acquire requiring filing text inspection |
| 2nd | P2 (excerpt context check) | VSTM, LBPH, G1T | ROFR/ROFN / offering language scope check |
| 3rd | P3 (confirm and close) | HZNP, SNDX | Likely boilerplate / wrong-direction acquisition |
| 4th | P4 (known pattern) | STML, MRTX, ALBO, CHMA | Director bio, equity plan, anti-takeover boilerplate |
| 5th | Spot-check | CNST, FUSN, KROS, KRTX, MORF | 5 likely-clean no-hit cases |
| Last | BLOCKED | 10 cases | Resolve dates before any filing collection |

See `batch_71_100_adjudication_queue.md` for full per-case detail, source URLs, and next actions.

---

## 3. Classification Decision Tree

1. Was the source public **before** the acquisition announcement date?
   - **NO** → not `TRUE_PUBLIC_PRIOR_SIGNAL`

2. Is it equity plan / S-8 / 424B3 / prospectus boilerplate?
   - "Form S-8... offer or the sale of the Company's securities to such person"
   - Anti-takeover provisions section in prospectus
   - Securities offering disclaimer language
   - **YES** → `RIGHTS_LANGUAGE_ONLY`

3. Is it a director biography referencing a prior employer's sale?
   - **YES** → `RIGHTS_LANGUAGE_ONLY`

4. Is it performance condition language in equity award accounting?
   - "a change in control or a sale of the company, no expense is recognized..."
   - **YES** → `RIGHTS_LANGUAGE_ONLY`

5. Is the keyword in a UUEncoded binary artifact / complete submission .txt?
   - Garbled encoding around the keyword hit
   - **YES** → false positive — discard

6. Is the target the acquiring party (not the acquisition target)?
   - Target company buying a drug program or other company
   - **YES** → not process evidence — discard

7. Is the ROFR/ROFN asset-specific (program, territory, product)?
   - Not the whole company
   - **YES** → `ASSET_SPECIFIC_RIGHTS_ONLY`

8. Is the "sale of Company's stock/securities" language about a partner selling equity?
   - Partner terminating and divesting equity stake
   - **YES** → `RIGHTS_LANGUAGE_ONLY`

9. Is it a warranty that ROFR does NOT apply?
   - "not subject to any agreement granting a right of first refusal..."
   - **YES** → `RIGHTS_LANGUAGE_ONLY`

10. Is there explicit pre-announcement proposal or process language?
    - "unsolicited proposal," "superior proposal," "acquisition proposal," "strategic alternatives" + banker context
    - **YES** → possible `TRUE_PUBLIC_PRIOR_SIGNAL` — requires all evidence fields

If unclear: leave as `POSSIBLE_SIGNAL_NEEDS_REVIEW`. Do not force.

---

## 4. False-Positive Rules (from 70-case study)

| Pattern | Correct classification |
|---|---|
| Deal-announcement 8-K flagged same day as announcement | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| Negation: "no plan or proposal to acquire" | False positive — ignore |
| UUEncoded binary artifact in complete submission .txt | False positive — discard |
| PWERM stock comp valuation (pre-IPO) in 10-Q | RIGHTS_LANGUAGE_ONLY |
| CIC vesting clause in proxy | RIGHTS_LANGUAGE_ONLY |
| Director biography: prior sale at a different organization | RIGHTS_LANGUAGE_ONLY |
| Performance condition equity award boilerplate | RIGHTS_LANGUAGE_ONLY |
| Anti-takeover provisions section in 424B3 / prospectus | RIGHTS_LANGUAGE_ONLY |
| S-8 equity plan: "offer or sale of Company's securities to such person" | RIGHTS_LANGUAGE_ONLY |
| Securities offering prospectus disclaimer | RIGHTS_LANGUAGE_ONLY |
| Partner sells equity stake in collaboration termination | RIGHTS_LANGUAGE_ONLY |
| ROFR warranty stating ROFR does not apply | RIGHTS_LANGUAGE_ONLY |
| Target acquiring another entity (wrong direction) | Not relevant — discard |
| Geographic license ROFN (product + territory specific) | ASSET_SPECIFIC_RIGHTS_ONLY |
| Product-level ROFR/ROFN (not company-level) | ASSET_SPECIFIC_RIGHTS_ONLY |
| Company's own ROFN to re-acquire outbound-licensed compound | ASSET_SPECIFIC_RIGHTS_ONLY |
| ROFN defined term in licensing collaboration agreement | ASSET_SPECIFIC_RIGHTS_ONLY |
| BVI→Delaware redomiciliation merger agreement | False positive — internal doc |
| Lock-up employment-termination share repurchase right | RIGHTS_LANGUAGE_ONLY |
| FPI 6-K filer — no EDGAR target-form coverage | Baseline; note coverage gap |

---

## 5. Evidence Requirements for Non-Baseline Cases

Each non-baseline or upgraded case requires all of:

| Field | Required |
|---|---|
| case_id | yes |
| ticker | yes |
| announcement_date | yes |
| source_url | yes |
| filing_type | yes |
| filing_date | yes |
| accession_number | if available |
| excerpt (verbatim) | yes |
| days_before_announcement | yes |
| classification | yes |
| reason | yes |
| false_positive_check | yes |

---

## 6. 11 Cases Flagged for Manual Review

| Rank | Ticker | case_id | Hit count | Signal types | Priority | Likely pattern |
|---|---|---|---|---|---|---|
| 1 | SGEN | RHC-0106-ACQUIRED-SGEN | 2 | rofr_rofn | P1 (source pull) | Licensing agreement ROFN; binary artifact |
| 2 | TBIO | RHC-0132-ACQUIRED-TBIO | 1 | option_to_acquire | P1 (source pull) | Asset-specific option to acquire licenses |
| 3 | VSTM | RHC-0140-ACQUIRED-VSTM | 2 | rofr_rofn, sale_process | P2 (context check) | ROFR warranty (negative) + offering boilerplate |
| 4 | LBPH | RHC-0077-ACQUIRED-LBPH | 2 | sale_process, rofr_rofn | P2 (context check) | Asset-specific ROFN (Arena on LP659) + offering boilerplate |
| 5 | G1T | RHC-0074-ACQUIRED-G1T | 4 | rofr_rofn, sale_process | P2 (context check) | G1T's own ROFN to re-acquire licensed compound |
| 6 | HZNP | RHC-0105-ACQUIRED-HZNP | 3 | sale_process, option_to_acquire | P3 (confirm) | S-8 boilerplate + wrong-direction acquisition |
| 7 | SNDX | RHC-0107-ACQUIRED-SNDX | 2 | sale_process | P3 (confirm) | Partner equity stake termination settlement |
| 8 | STML | RHC-0103-ACQUIRED-STML | 5 | sale_process | P4 (known pattern) | Director bio + performance condition boilerplate |
| 9 | MRTX | RHC-0079-ACQUIRED-MRTX | 1 | sale_process | P4 (known pattern) | S-8 equity plan boilerplate |
| 10 | ALBO | RHC-0104-ACQUIRED-ALBO | 1 | acquisition_proposal | P4 (known pattern) | 424B3 anti-takeover provision disclosure |
| 11 | CHMA | RHC-0101-ACQUIRED-CHMA | 2 | retained_advisor | P4 (known pattern) | Proxy director bio |

---

## 7. 5 Likely Clean No-Hit Cases

No signal hits detected. Proposed classification: `DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE`.
Require researcher spot-check before finalizing.

| Ticker | case_id | Announcement date | Date confidence |
|---|---|---|---|
| CNST | RHC-0102-ACQUIRED-CNST | 2021-06-02 | HIGH |
| FUSN | RHC-0073-ACQUIRED-FUSN | 2024-03-19 | MEDIUM |
| KROS | RHC-0138-ACQUIRED-KROS | 2024-12-03 | MEDIUM |
| KRTX | RHC-0076-ACQUIRED-KRTX | 2023-12-22 | MEDIUM |
| MORF | RHC-0078-ACQUIRED-MORF | 2024-07-08 | MEDIUM |

---

## 8. 10 Blocked Missing-Date Cases

All 10 remain BLOCKED. Do not attempt filing collection. Use EDGAR URLs in `batch_71_100_date_prefill_queue.csv` to resolve dates manually.

| Ticker | case_id | Year | Backfill result |
|---|---|---|---|
| ENLV | RHC-0134-ACQUIRED-ENLV | 2023 | No Item 1.01 8-K found |
| FATE | RHC-0072-ACQUIRED-FATE | 2024 | LOW confidence — skipped |
| GRCL | RHC-0075-ACQUIRED-GRCL | 2024 | No Item 1.01 8-K found |
| HRMY | RHC-0135-ACQUIRED-HRMY | 2023 | LOW confidence — skipped |
| KPTI | RHC-0137-ACQUIRED-KPTI | 2024 | LOW confidence — skipped |
| LMNX | RHC-0131-ACQUIRED-LMNX | 2021 | CIK not found |
| MOR | RHC-0109-ACQUIRED-MOR | 2024 | No Item 1.01 8-K (FPI) |
| SYNH | RHC-0136-ACQUIRED-SYNH | 2023 | LOW confidence — skipped |
| TGTX | RHC-0139-ACQUIRED-TGTX | 2024 | LOW confidence — skipped |
| VECT | RHC-0108-ACQUIRED-VECT | 2023 | No Item 1.01 8-K found |

---

## 9. What Qualifies as TRUE_PUBLIC_PRIOR_SIGNAL

Based on 70-case standard:
- SEC filing (8-K, 10-Q, 10-K, DEF 14A, SC 13D) — not post-announcement SC 14D-9
- Filed before acquisition announcement date
- Company-level scope — not asset, program, or territory-specific
- Explicit language: "unsolicited proposal," "superior proposal," "acquisition proposal," "strategic alternatives" + banker retention context
- All evidence fields populated (source_url, accession_number, verbatim excerpt, days_before_announcement)

Prior TRUE_PUBLIC_PRIOR_SIGNAL cases for reference: MDVN (unsolicited proposal, 116 days), DMTX (superior proposal, 39 days), TSRO (sale-process media report, 17 days).

Expected rate in this batch: 0–1 case based on 4.3% historical base rate.

---

## 10. What Should Each Case Be Classified As

| Result | Classification | Trigger |
|---|---|---|
| Confirmed public process evidence | TRUE_PUBLIC_PRIOR_SIGNAL | Explicit proposal/process language, source-backed, company-level |
| No public process evidence | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Clean review or likely-no-hit |
| Process only in SC 14D-9 / proxy background | PRIVATE_BACKGROUND_ONLY | Background exists but was never public pre-announcement |
| Company-level ROFR/ROFN (not asset-specific) | RIGHTS_LANGUAGE_ONLY | Generic rights clause, not sale-process evidence |
| Asset-specific ROFR/ROFN | ASSET_SPECIFIC_RIGHTS_ONLY | Rights limited to program, territory, or licensed compound |
| Missing date confirmed unresolvable | BLOCKED | No HIGH/MEDIUM date; manual EDGAR research needed |

---

## 11. EDGAR Source Pull Helper

For SGEN and TBIO manual source pulls:

```bash
python3 src/historical_case_tools/edgar_source_pull_helper.py \
  --url "<SEC_ARCHIVE_URL>" \
  --case-id "RHC-XXXX" \
  --ticker "TICKER" \
  --filing-type "8-K" \
  --find "unsolicited proposal" \
  --find "superior proposal" \
  --find "acquisition proposal" \
  --find "strategic alternatives" \
  --find "right of first"
```

---

## 12. Stop Conditions

Do not proceed if any of these apply:
- Classifying from post-announcement SC 14D-9 / proxy background only
- Marking TRUE_PUBLIC_PRIOR_SIGNAL without verified source URL, filing date, excerpt, and days-before
- Using FMP data as classification evidence (context only)
- Marking VERIFIED or CALIBRATION_ELIGIBLE
- Changing any of the first 70 classifications
- Running the full live scanner

---

## 13. Adjudication Outcomes (2026-05-16)

All 16 dated cases adjudicated. Zero TRUE_PUBLIC_PRIOR_SIGNAL.

| Ticker | Final Classification | False-Positive Pattern |
|---|---|---|
| SGEN | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Binary artifact + defined term in license exhibit |
| TBIO | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Asset-specific license option (pathogen licenses) |
| VSTM | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | ROFR warranty (negative) + offering disclaimer |
| LBPH | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Offering disclaimer + asset-specific ROFN (LP659) |
| G1T | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | G1T's own ROFN on outbound-licensed compound |
| HZNP | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | S-8 boilerplate + wrong-direction acquisition |
| SNDX | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Partner equity stake divestiture |
| STML | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Director bio + performance condition boilerplate |
| MRTX | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | S-8 equity plan boilerplate |
| ALBO | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Anti-takeover provision prospectus disclosure |
| CHMA | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | Director biography (advisory career) |
| CNST | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | No signal hits |
| FUSN | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | No signal hits |
| KROS | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | No signal hits |
| KRTX | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | No signal hits |
| MORF | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | No signal hits |

Full per-hit detail: `batch_71_100_adjudication_results.csv`
Narrative: `batch_71_100_adjudication_report.md`
