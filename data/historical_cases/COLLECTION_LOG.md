# Historical Case Library — Collection Log

**Created:** 2026-05-09  
**Current count:** 15 seed cases (all VERIFY_REQUIRED)  
**Verified:** 0  
**Phase 1 target:** 25 cases, 60% verified

---

## Verification Queue (Phase 1 Priority)

Work through in order. Each case needs: Bloomberg price pull, EDGAR filing URL,
deal terms from press release or 8-K. Estimated 2–3 hours per case.

| Priority | Ticker | Case ID | Signal | What to Verify | Status |
|---|---|---|---|---|---|
| 1 | GNCA | GNCA-2022-001 | SA_AFFIRM → bankruptcy | EDGAR 8-K date for SA announcement; price at announcement; wind-down date | TODO |
| 2 | HARP | HARP-2023-001 | ROFR → acquired | Date ROFR first disclosed in AbbVie collaboration 8-K; price on that date; deal premium | TODO |
| 3 | SRRA | SRRA-2022-001 | Banker → acquired | 8-K date for banker/process signal; price; GSK deal premium | TODO |
| 4 | CRBP | CRBP-2022-001 | SA_AFFIRM → no deal | Exact 8-K date; price; outcome date | TODO |
| 5 | MGTA | MGTA-2022-001 | SA_AFFIRM → wind-down | Exact 8-K date; wind-down announcement date | TODO |
| 6 | RIGL | RIGL-2020-001 | Activist → no deal | 13D filer; filing date; Item 4 text | TODO |
| 7 | VNDA | VNDA-2021-001 | Activist → no deal | 13D filer; dates; Item 4 text | TODO |
| 8 | PTGX | PTGX-2022-001 | ROFR, program scope | J&J collaboration 8-K; ROFN scope language; whether exercised | TODO |
| 9 | ACHN | ACHN-2020-001 | Score-only → acquired | Price before deal; confirm deal terms | TODO |
| 10 | INBX | INBX-2024-001 | Asset sale | Sanofi deal 8-K; structure of spin-out; deal value breakdown | TODO |

---

## Phase 1 Gap Cases to Add

These 10 additional cases are needed to reach 25 total and balance the outcome mix.
Research needed before adding to cases_seed.csv.

| Target Type | What to Find |
|---|---|
| ACTIVIST_THEN_SA (deal resulted) | Activist 13D → SA 8-K → acquisition. Search 2019–2024. |
| ADVISOR_THEN_SA (deal resulted) | Banker retained → SA confirmed → acquisition. |
| ROFR_TRIGGERED (whole company) | ROFR partner exercised rights in whole-company deal. |
| ROFR_NO_TRIGGER (asset level) | ROFR disclosed; partner did not exercise; no deal. |
| CAPITAL_RAISE instead of deal | SA review → equity offering, no acquisition. |
| Activist escalation (no deal) | 13D with BOARD_CHANGE intent → SALE_PROCESS escalation → no deal. |
| Large cap (out of range, reference) | $3B+ mcap deal for calibrating "above range" cases. |
| Pre-2019 deal (cycle data) | 2015–2018 biotech acquisition for longer time series. |
| Quick deal (< 30d signal to deal) | SA or 13D filed, deal announced within 30 days. |
| Long process (> 365d signal to deal) | Extended review before eventual deal. |

---

## Research Sources

**For completed deals:**
- BioPharma Catalyst: biopharmacatalyst.com/buyouts
- Evaluate Pharma deal database
- Endpoints News / STAT News M&A coverage
- SEC EDGAR: search company 8-K for "Agreement and Plan of Merger"

**For SA signals:**
- SEC EDGAR full-text search: "strategic alternatives" + SIC 2836/2835
- URL: https://efts.sec.gov/LATEST/search-index?q=%22strategic+alternatives%22&dateRange=custom&startdt=2019-01-01&enddt=2025-01-01&forms=8-K

**For 13D filings:**
- SEC EDGAR 13D search by company ticker
- WhaleWisdom.com for activist history
- 13dmonitor.com for activist biotech filings

**For price data:**
- Yahoo Finance historical prices (free)
- Bloomberg Terminal (accurate, use for VERIFIED cases)
- Macrotrends for historical adjusted prices

**For deal terms:**
- Form 8-K "Agreement and Plan of Merger" filing
- Press release linked in EDGAR
- Deal announcement article from Reuters/Bloomberg

---

## Completed Verifications

None yet.

---

## Notes

- Do not use cases_seed.csv for any quantitative work until cases are moved to cases_verified.csv
- Move case to cases_verified.csv only after all required fields are confirmed against primary sources
- Add source_filing_url as EDGAR direct link (not press release)
- Price data should use closing prices from Yahoo Finance at minimum; Bloomberg for VERIFIED
