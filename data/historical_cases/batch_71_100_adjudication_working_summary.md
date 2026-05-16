# Batch 71-100 Adjudication Working Summary

Generated: 2026-05-16
Status: All 16 dated cases adjudicated. 10 blocked cases pending date resolution.

---

## Quick Hit Table — 11 Review Cases

| Ticker | Hits | Form | Filing Date | Phrase Match | Pattern | Verdict |
|---|---|---|---|---|---|---|
| SGEN | 2 | 8-K | 2021-09-21 (x2) | rofn | Binary artifact + defined term in license exhibit | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| TBIO | 1 | 8-K | 2020-06-23 | option to acquire | Asset-specific pathogen license option (removed in filing) | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| VSTM | 2 | 8-K | 2022-11-07, 2023-06-21 | right of first refusal; sale of company | ROFR warranty (negative) + offering prospectus disclaimer | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| LBPH | 2 | 8-K, 10-K | 2024-01-02, 2024-03-12 | sale of company; right of first negotiation | Offering disclaimer + Arena ROFN on LP659 only | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| G1T | 4 | 10-Q (x4) | 2023-05-03 thru 2024-05-01 | right of first negotiation | G1T's own ROFN to re-acquire Incyclix licensed compound | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| HZNP | 3 | 8-K, 10-Q, 8-K | 2022-05-02, 2022-11-02 (x2) | sale of company; option to acquire (x2) | S-8 boilerplate + HZNP acquiring ADX-914 (wrong direction) | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| SNDX | 2 | 10-Q (x2) | 2022-08-08, 2022-11-03 | sale of company | Incyte divesting equity stake (partner termination settlement) | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| STML | 5 | 10-K, 10-Q (x3), 10-K | 2019-03-15 thru 2020-03-16 | sale of company (x5) | Director bio (Keryx sale) + performance condition award boilerplate | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| MRTX | 1 | 8-K | 2022-05-12 | sale of company | S-8 equity plan boilerplate | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| ALBO | 1 | 424B3 | 2022-08-25 | acquisition proposal | Anti-takeover provision Section 203 Delaware disclosure | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| CHMA | 2 | DEF 14A (x2) | 2020-04-28, 2021-04-26 | financial advisor | Director biography (career in financial advisory services) | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |

---

## False-Positive Pattern Summary

| Pattern | Cases | Count |
|---|---|---|
| Securities offering prospectus disclaimer | VSTM, LBPH, MRTX, HZNP | 5 hits |
| Asset-specific ROFN/ROFR (not company-level) | SGEN, TBIO, LBPH, G1T | 7 hits |
| Director biography (prior employer's sale) | STML, CHMA | 3 hits |
| Performance condition equity award boilerplate | STML | 3 hits |
| UUEncoded binary artifact | SGEN | 1 hit |
| ROFR warranty (negative statement) | VSTM | 1 hit |
| Partner equity stake divestiture | SNDX | 2 hits |
| Wrong-direction acquisition (target acquiring asset) | HZNP | 2 hits |
| Anti-takeover provision disclosure | ALBO | 1 hit |
| Total | | 25 hits |

---

## 5 Spot-Check Cases (no hits)

All confirmed DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE based on zero signal hits in filing collection.

| Ticker | Announcement Date | Date Confidence |
|---|---|---|
| CNST | 2021-06-02 | HIGH |
| FUSN | 2024-03-19 | MEDIUM |
| KROS | 2024-12-03 | MEDIUM |
| KRTX | 2023-12-22 | MEDIUM |
| MORF | 2024-07-08 | MEDIUM |

---

## Running Totals

| Metric | Value |
|---|---|
| Cases adjudicated (batch 71-100 dated) | 16 |
| TRUE_PUBLIC_PRIOR_SIGNAL (this batch) | 0 |
| Cumulative true signals (cases 1-86) | 3 |
| Cumulative signal rate | 3/86 (3.5%) |
| Still blocked (no date) | 10 |

Prior signals: MDVN (unsolicited proposal, 116 days), DMTX (superior proposal, 39 days), TSRO (sale-process media report, 17 days).
