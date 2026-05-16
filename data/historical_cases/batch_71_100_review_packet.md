# Batch 71 100 Manual Review Packet

Generated: 2026-05-16

Manual review only. No cases adjudicated by this system.
All classifications must be made by a human researcher following the decision tree below.

---

## 1. Scope

| Metric | Value |
|---|---|
| Cases in scope | 71–100 (30 target) |
| Candidate rows available | 26 |
| Exception queue rows | 26 |
| Review packet generated | 2026-05-16 |

---

## 2. Review Order

| Priority | Tier | Review trigger |
|---|---|---|
| 1st | P1 | Explicit acquisition-process phrases (unsolicited / superior / competing proposals) |
| 2nd | P2 | Strategic alternatives + advisor retention language |
| 3rd | P3 | SC 13D Item 4 acquisition pressure |
| 4th | P4 | ROFR/ROFN language requiring company-vs-asset scope check |
| 5th | BLOCKED | Date or source missing — resolve before any filing collection |
| Last | P6_WITH_HITS | Signal phrase hit but low-confidence type |

---

## 3. Classification Decision Tree

1. Was the source public **before** the announcement date?
   - **NO** → not `TRUE_PUBLIC_PRIOR_SIGNAL`
2. Is the evidence company-level (not asset / product / territory-specific)?
   - **NO** → `ASSET_SPECIFIC_RIGHTS_ONLY`
3. Is it generic legal rights language (boilerplate ROFR, lock-up, CIC clause)?
   - **YES** → `RIGHTS_LANGUAGE_ONLY`
4. Does the process appear only in post-announcement SC 14D-9 or proxy background?
   - **YES** → `PRIVATE_BACKGROUND_ONLY`
5. Is there explicit pre-announcement proposal or process language with source URL, filing date, and excerpt?
   - **YES** → possible `TRUE_PUBLIC_PRIOR_SIGNAL` (requires all evidence fields)
6. No public process evidence confirmed → `DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE`

If evidence is unclear: leave as `POSSIBLE_SIGNAL_NEEDS_REVIEW`. Do not force.

---

## 4. False-Positive Rules (from 70-case study)

| Pattern | Correct classification |
|---|---|
| Deal-announcement 8-K flagged same day as announcement | DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE |
| Negation: 'no plan or proposal to acquire' | False positive — ignore |
| UUEncoded binary artifact in complete submission .txt | False positive — not in primary doc |
| PWERM stock comp valuation (pre-IPO) in 10-Q | RIGHTS_LANGUAGE_ONLY |
| CIC vesting clause in proxy | RIGHTS_LANGUAGE_ONLY |
| Director biography: prior sale at a different organization | RIGHTS_LANGUAGE_ONLY |
| VC/PE investor self-reservation in SC 13D (IPO-era) | RIGHTS_LANGUAGE_ONLY |
| Geographic license ROFN (product + territory specific) | ASSET_SPECIFIC_RIGHTS_ONLY |
| Product-level ROFR (not company-level) | ASSET_SPECIFIC_RIGHTS_ONLY |
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

## 6. Exception Queue Summary

| Tier | Count |
|---|---|
| BLOCKED | 10 |
| PENDING_FILING_COLLECTION | 16 |

### Cases By Tier

#### BLOCKED

| case_id | ticker | priority_reason | next_action |
|---|---|---|---|
| RHC-0072-ACQUIRED-FATE | FATE | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |
| RHC-0075-ACQUIRED-GRCL | GRCL | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |
| RHC-0108-ACQUIRED-VECT | VECT | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |
| RHC-0109-ACQUIRED-MOR | MOR | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |
| RHC-0131-ACQUIRED-LMNX | LMNX | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |
| RHC-0134-ACQUIRED-ENLV | ENLV | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |
| RHC-0135-ACQUIRED-HRMY | HRMY | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |
| RHC-0136-ACQUIRED-SYNH | SYNH | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |
| RHC-0137-ACQUIRED-KPTI | KPTI | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |
| RHC-0139-ACQUIRED-TGTX | TGTX | No HIGH/MEDIUM announcement date — run merger_date_prefiller first. | Add announcement date (HIGH or MEDIUM confidence)  |

#### PENDING_FILING_COLLECTION

| case_id | ticker | priority_reason | next_action |
|---|---|---|---|
| RHC-0073-ACQUIRED-FUSN | FUSN | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0074-ACQUIRED-G1T | G1T | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0076-ACQUIRED-KRTX | KRTX | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0077-ACQUIRED-LBPH | LBPH | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0078-ACQUIRED-MORF | MORF | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0079-ACQUIRED-MRTX | MRTX | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0101-ACQUIRED-CHMA | CHMA | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0102-ACQUIRED-CNST | CNST | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0103-ACQUIRED-STML | STML | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0104-ACQUIRED-ALBO | ALBO | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0105-ACQUIRED-HZNP | HZNP | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0106-ACQUIRED-SGEN | SGEN | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0107-ACQUIRED-SNDX | SNDX | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0132-ACQUIRED-TBIO | TBIO | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0138-ACQUIRED-KROS | KROS | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |
| RHC-0140-ACQUIRED-VSTM | VSTM | Date confirmed; filing collector has not yet run for this case. | Run pre_announcement_filing_collector.py for this  |

---

## 7. Candidate Cases

| # | ticker | company | year | confidence | needs_backfill | source_url |
|---|---|---|---|---|---|---|
| 71 | ALBO | Albireo Pharma | 2023 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=ALBO+%22Albireo+P |
| 72 | CHMA | Chiasma | 2021 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=CHMA+%22Chiasma%2 |
| 73 | CNST | Constellation Pharmaceuticals | 2021 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=CNST+%22Constella |
| 74 | ENLV | Enliven Therapeutics | 2023 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=ENLV+%22Enliven+T |
| 75 | FATE | Fate Therapeutics | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=FATE+%22Fate+Ther |
| 76 | FUSN | Fusion Pharmaceuticals Inc. | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=FUSN+%22Fusion+Ph |
| 77 | G1T | G1 Therapeutics | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=G1T+%22G1+Therape |
| 78 | GRCL | Gracell Biotechnologies | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=GRCL+%22Gracell+B |
| 79 | HRMY | Harmony Biosciences | 2023 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=HRMY+%22Harmony+B |
| 80 | HZNP | Horizon Therapeutics plc | 2023 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=HZNP+%22Horizon+T |
| 81 | KPTI | Karyopharm Therapeutics | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=KPTI+%22Karyophar |
| 82 | KROS | Keros Therapeutics | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=KROS+%22Keros+The |
| 83 | KRTX | Karuna Therapeutics, Inc. | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=KRTX+%22Karuna+Th |
| 84 | LBPH | Longboard Pharmaceuticals, Inc | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=LBPH+%22Longboard |
| 85 | LMNX | Luminex Corporation | 2021 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=LMNX+%22Luminex+C |
| 86 | MOR | MorphoSys AG | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=MOR+%22MorphoSys+ |
| 87 | MORF | Morphic Holding, Inc. | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=MORF+%22Morphic+H |
| 88 | MRTX | Mirati Therapeutics, Inc. | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=MRTX+%22Mirati+Th |
| 89 | SGEN | Seagen Inc. | 2023 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=SGEN+%22Seagen+In |
| 90 | SNDX | Syndax Pharmaceuticals | 2023 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=SNDX+%22Syndax+Ph |
| 91 | STML | Stemline Therapeutics | 2021 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=STML+%22Stemline+ |
| 92 | SYNH | Syneos Health, Inc. | 2023 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=SYNH+%22Syneos+He |
| 93 | TBIO | Translate Bio | 2021 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=TBIO+%22Translate |
| 94 | TGTX | TG Therapeutics | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=TGTX+%22TG+Therap |
| 95 | VECT | VectivBio Holding | 2023 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=VECT+%22VectivBio |
| 96 | VSTM | Verastem Oncology | 2024 | LOW | TRUE | https://efts.sec.gov/LATEST/search-index?q=VSTM+%22Verastem+ |

---

## 8. Unresolved Blockers

Cases that cannot proceed without external resolution:

- **FATE** (RHC-0072-ACQUIRED-FATE): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.
- **GRCL** (RHC-0075-ACQUIRED-GRCL): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.
- **VECT** (RHC-0108-ACQUIRED-VECT): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.
- **MOR** (RHC-0109-ACQUIRED-MOR): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.
- **LMNX** (RHC-0131-ACQUIRED-LMNX): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.
- **ENLV** (RHC-0134-ACQUIRED-ENLV): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.
- **HRMY** (RHC-0135-ACQUIRED-HRMY): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.
- **SYNH** (RHC-0136-ACQUIRED-SYNH): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.
- **KPTI** (RHC-0137-ACQUIRED-KPTI): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.
- **TGTX** (RHC-0139-ACQUIRED-TGTX): No HIGH/MEDIUM announcement date — run merger_date_prefiller first.

---

## 9. Inspector Commands

```bash
# View EDGAR filings for a specific ticker (replace TICKER)
python3 src/historical_case_tools/edgar_source_pull_helper.py --ticker TICKER

# Date prefill work queue
cat data/historical_cases/batch_71_100_date_prefill_queue.csv

# Exception queue
cat data/historical_cases/batch_71_100_exception_queue.csv

# Source evidence draft
cat data/historical_cases/batch_71_100_source_evidence_draft.csv
```

---

## 10. Safety Constraints

- No automatic adjudication.
- No VERIFIED flag.
- No CALIBRATION_ELIGIBLE flag.
- No alpha claims.
- No M&A prediction framing.
- EDGAR/source-backed evidence is the source of truth.
- FMP is market context only — not classification evidence.
- Post-announcement SC 14D-9 background is NOT prior public signal.
- Generic ROFR is not process evidence.
- Asset-specific rights are not company-level process evidence.
- Private offers are not public signals unless publicly disclosed before announcement.
