# Verification Notes — Historical Process Intelligence Pipeline

_Created: 2026-05-10_
_Scope: 10 priority cases from COLLECTION_LOG.md verification queue_
_Status: Pre-EDGAR research pass. All 10 cases = NEEDS_RESEARCH. No PARTIAL or VERIFIED cases assigned — primary source confirmation unavailable in this session._

---

## Summary

| Ticker | Case ID | Seeded | Recommended Status | Priority | Seed Error |
|--------|---------|--------|--------------------|----------|-----------|
| HARP | HARP-2023-001 | YES | NEEDS_RESEARCH | 1 | case_id year mismatch |
| SRRA | SRRA-2022-001 | YES | NEEDS_RESEARCH | 2 | signal_type unconfirmed |
| IMGO | IMGO-2022-001 | YES | NEEDS_RESEARCH | 3 | **CRITICAL: acquirer name suspect** |
| GNCA | GNCA-2022-001 | YES | NEEDS_RESEARCH | 4 | event_type/outcome mismatch |
| MGTA | MGTA-2022-001 | YES | NEEDS_RESEARCH | 5 | event_type/outcome mismatch |
| PTGX | PTGX-2022-001 | YES | NEEDS_RESEARCH | 6 | rofr_scope unconfirmed |
| RIGL | RIGL-2020-001 | YES | NEEDS_RESEARCH | 7 | item4_intent unresolved |
| CRBP | CRBP-2022-001 | YES | NEEDS_RESEARCH | 8 | outcome_type uncertain |
| FLXN | NOT SEEDED | NO | NEEDS_RESEARCH | 9 | N/A — not yet seeded |
| DOVA | NOT SEEDED | NO | NEEDS_RESEARCH | 10 | N/A — not yet seeded |

**Verified:** 0  
**PARTIAL:** 0  
**NEEDS_RESEARCH:** 10

All 10 cases require live EDGAR access for primary source confirmation before any field can move to PARTIAL status. Training knowledge used as research starting point only — not as primary source.

---

## Anti-Look-Ahead Status Across All 10 Cases

The following fields must NOT be pre-filled without primary source:
- `observation_date` — must be EDGAR filing date, not approximate
- `price_at_signal` — must be adjusted close on confirmed observation_date
- `item4_intent` — must come from verbatim Item 4 text, not from outcome knowledge
- `rofr_scope` — must come from actual agreement text, not from deal structure
- `failure_reason` — must come from contemporaneous public statement at outcome_date

Current seed rows violate none of these rules (all are VERIFY_REQUIRED), but three structural errors exist (see Seed Errors below).

---

## SEED ERRORS DISCOVERED

### Error 1 — CRITICAL: IMGO acquirer name suspect

**File:** `cases_seed.csv`, row IMGO-2022-001  
**Field:** `acquirer`  
**Current value:** `Merck & Co. Inc.`  
**Issue:** Training knowledge indicates BMS (Bristol-Myers Squibb Inc.) acquired Imago BioSciences for ~$36/share in late 2022. The seed compound identifier "MK-3543" uses Merck naming convention but bomedemstat is associated with BMS. The acquirer field is factually disputed.  
**Resolution required:** Open the EDGAR 8-K for Imago BioSciences filed Nov-Dec 2022. Read Item 1.01 verbatim. Confirm acquirer name. Update `acquirer` and `acquirer_type` to match.  
**Do NOT use IMGO row for any analysis until acquirer confirmed.**

### Error 2 — case_id year inconsistency: HARP

**File:** `cases_seed.csv`, row HARP-2023-001  
**Field:** `case_id`  
**Issue:** Schema says case_id format is `TICKER-YYYY-NNN` where YYYY = observation year. Observation_date is `2020-09-15` (AbbVie collaboration). Case_id `HARP-2023-001` uses the deal year (2023), not the observation year (2020). This creates a structural inconsistency — case_id year doesn't match observation_date year.  
**Resolution:** After confirming the AbbVie collaboration 8-K date, rename case_id to `HARP-2020-001` (or correct year of collaboration filing). Update all foreign keys in filing_events and transitions.

### Error 3 — event_type vs outcome mismatch: GNCA, MGTA

**File:** `cases_seed.csv`, rows GNCA-2022-001 and MGTA-2022-001  
**Field:** `event_type` vs `outcome`  
**Issue:** Both rows have `event_type = BANKRUPTCY` but `outcome = WIND_DOWN`. These are different schema values.  
- If company filed Chapter 7/11: `outcome = BANKRUPT` and `event_type = BANKRUPTCY`  
- If company simply dissolved without bankruptcy filing: `outcome = WIND_DOWN` and `event_type` should be a different value  
**Resolution:** Confirm via EDGAR 8-K whether Genocea or Magenta filed a formal bankruptcy petition. If yes → change `outcome` to `BANKRUPT`. If no → change `event_type` to a non-bankruptcy value (or add DISSOLUTION as an event_type option — see Schema Gaps below).

---

## Per-Case Research Playbooks

### Case 1: HARP — Harpoon Therapeutics (Priority 1)

**What training knowledge says:**
- AbbVie and Harpoon Therapeutics signed a collaboration agreement (likely late 2020 or early 2021) that included ROFR/option rights for AbbVie on Harpoon's TriTAC programs
- AbbVie announced full acquisition of Harpoon in February 2023 at approximately $23/share (~$680M total)
- This is a textbook ROFR_THEN_MERGER sequence: collaboration with embedded ROFR → acquirer exercises/buys remaining company
- Training knowledge confidence: HIGH for deal outcome; MEDIUM for collaboration date

**Seed status:**
- case_id: HARP-2023-001 (year mismatch — should be HARP-2020-001 or HARP-2021-001)
- observation_date: 2020-09-15 (estimate, VERIFY_REQUIRED)
- deal_date: 2023-02-27 (estimate, VERIFY_REQUIRED)
- acquirer: AbbVie Inc. (consistent with training knowledge)
- deal_value_M: 680 (estimate, VERIFY_REQUIRED)
- rofr_scope: WHOLE_COMPANY (unconfirmed — derived from deal structure, not agreement text)

**EDGAR research steps:**

Step 1 — Find the AbbVie collaboration 8-K:
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=harpoon+therapeutics&CIK=&type=8-K&dateb=&owner=include&count=40&search_text=&action=getcompany
```
Look for 8-K filed August–November 2020 disclosing AbbVie collaboration. This sets `observation_date` and `source_filing_date`.

Step 2 — Open the 8-K exhibit:
Find Exhibit 10.x (collaboration and option agreement). Navigate to the ROFR/option clause. Extract verbatim text confirming:
- Whether rights apply to whole company or specific programs
- Option/ROFR terms (price, trigger conditions)
Record as `excerpt_text` and in `language_observations.csv`.

Step 3 — Set rofr_scope:
Only after reading the agreement text. Do not assume WHOLE_COMPANY based on deal outcome alone.

Step 4 — Find the merger agreement 8-K (Feb 2023):
Confirm `deal_date` = actual EDGAR filing date. Record `deal_price_per_share` from Item 1.01.

Step 5 — Price pull:
```python
import yfinance as yf
obs = 'CONFIRMED_DATE'  # replace after Step 1
df = yf.download('HARP', start=obs, periods=370, auto_adjust=True)
price_at_signal = df.iloc[0]['Close']
```
Note: HARP delisted after AbbVie acquisition. Pull only through ~Feb 2023.

**Fields to fill from these steps:**
observation_date, source_filing_date, source_filing_url, excerpt_text, rofr_scope, price_at_signal, price_30d_after, deal_date, deal_price_per_share, deal_premium_pct, days_signal_to_deal, mcap_at_signal_M

**Anti-look-ahead check:**
- rofr_scope MUST come from the 2020 agreement text — do not derive from the fact that AbbVie ultimately bought the whole company
- deal_premium_pct = premium to 30-day average before Feb 2023 8-K, NOT premium to price_at_signal from 2020

---

### Case 2: SRRA — Sierra Oncology (Priority 2)

**What training knowledge says:**
- GSK (GlaxoSmithKline) acquired Sierra Oncology for momelotinib (JAK1/2/ACVR1 inhibitor for myelofibrosis) in April 2022
- Deal approximately $55/share, total approximately $1.9B
- Whether there was a prior public SA or banker-retained announcement BEFORE the merger agreement is uncertain from training knowledge

**Seed status:**
- signal_type: BANKER_RETAINED (estimate — no confirmed pre-deal filing)
- observation_date: 2021-10-01 (estimate, VERIFY_REQUIRED)
- deal_date: 2022-04-12 (estimate, likely close to correct)

**EDGAR research steps:**

Step 1 — Check for pre-announcement process signals:
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=sierra+oncology&CIK=&type=8-K&dateb=&owner=include&count=40
```
Search 8-K filings from 2021-01-01 to 2022-04-01. Look for any press release mentioning:
- Strategic alternatives, strategic review
- Financial advisor retained, investment banker
- Sale process, maximize shareholder value

If a pre-deal signal exists → observation_date = that 8-K date, signal_type = SA_AFFIRM or BANKER_RETAINED.
If NO pre-deal signal → observation_date = merger agreement 8-K date, signal_type = MERGER_AGREEMENT, signal_quality = MERGER, process_state_at_signal = SIGNED.

Step 2 — Find merger agreement 8-K (April 2022):
Confirm exact EDGAR filing date for `deal_date`. Extract deal_price_per_share from Item 1.01.

Step 3 — Price pull:
Pull adjusted close from confirmed observation_date through ~April 2022 (delisting). For VERIFIED status, Bloomberg needed for delisted ticker price verification.

**Critical decision point:**
If no prior SA/banker signal → SRRA becomes a SCORE_ONLY/MERGER_AGREEMENT case (no observable process precursor). This changes the calibration value: it calibrates "deal without prior signal" not "P(deal) given banker_retained signal."

---

### Case 3: IMGO — Imago BioSciences (Priority 3 — CRITICAL ACQUIRER ERROR)

**What training knowledge says:**
- Imago BioSciences (bomedemstat, LSD1 inhibitor for myeloproliferative neoplasms including MF, ET, PV) was acquired in late 2022
- Training knowledge suggests acquirer = Bristol-Myers Squibb (NOT Merck as listed in seed)
- Deal approximately $36/share, total approximately $1.35B
- Whether there was a prior SA or banker signal is uncertain — may have been a direct merger announcement

**CRITICAL seed error:**
Seed row lists acquirer = "Merck & Co. Inc." Training knowledge says BMS. Cannot proceed with any analysis until acquirer confirmed from 8-K text.

**EDGAR research steps:**

Step 1 — Find merger announcement 8-K (Nov-Dec 2022):
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=imago+biosciences&CIK=&type=8-K&dateb=&owner=include&count=40
```
Read Item 1.01 of merger agreement 8-K. Confirm acquirer name verbatim. This resolves the acquirer dispute.

Step 2 — Check for pre-announcement signals (same as SRRA):
Search 8-K filings Jan-Oct 2022 for any SA or banker language before the merger announcement.

Step 3 — If acquirer = BMS: update seed row acquirer field, acquirer_type = LARGE_PHARMA.
If acquirer = Merck: seed row is correct.

Step 4 — Price pull from confirmed observation_date.

---

### Case 4: GNCA — Genocea Biosciences (Priority 4)

**What training knowledge says:**
- Genocea announced a strategic review after clinical failures (ATLAS-2 neoantigen vaccine trial did not meet endpoints)
- Company wound down operations in 2022
- Whether formal Chapter 7/11 bankruptcy was filed or company simply dissolved is uncertain from training knowledge

**Seed status:**
- observation_date: 2022-01-27 (specific estimate — plausible for Jan 2022 SA announcement)
- event_type: BANKRUPTCY (needs confirmation — may be WIND_DOWN)
- outcome: BANKRUPT (consistent with event_type, but which is correct?)

**EDGAR research steps:**

Step 1 — Confirm SA announcement 8-K:
Search EDGAR for GNCA 8-K filings December 2021 – February 2022. Look for 8-K with "strategic alternatives" or "exploring potential transactions." If found on 2022-01-27 — seed date is likely correct.

Step 2 — Find outcome filing:
Search for subsequent GNCA 8-K filings in 2022. Look for:
- Wind-down announcement (company ceasing operations without bankruptcy)
- Chapter 11 petition announcement
- Dissolution plan filed with SEC

If no bankruptcy filing found → outcome = WIND_DOWN, event_type should NOT be BANKRUPTCY.
If Chapter 11 filed → outcome = BANKRUPT, event_type = BANKRUPTCY is correct.

Step 3 — Pull adjusted price on confirmed SA 8-K date.
Note: GNCA was delisted. Yahoo Finance may have incomplete data; Bloomberg needed for VERIFIED status.

**failure_reason constraint:**
"Pipeline failed, clinical trial halted, company had insufficient cash" is acceptable if contemporaneous press release or 8-K said this at time of wind-down. Do not include subsequent clinical information from after the wind-down announcement.

---

### Case 5: MGTA — Magenta Therapeutics (Priority 5)

**What training knowledge says:**
- Magenta Therapeutics had programs in stem cell mobilization and gene therapy conditioning (MGTA-145, MGTA-456)
- Announced strategic alternatives in 2022 after program setbacks
- Wound down operations

**Seed status:**
- observation_date: 2022-06-01 (rough estimate)
- event_type: BANKRUPTCY (needs confirmation — same issue as GNCA)
- outcome: WIND_DOWN

**EDGAR research steps:**
Same procedure as GNCA:

Step 1 — Find SA announcement 8-K in mid-2022.
Step 2 — Find wind-down or bankruptcy filing.
Step 3 — Resolve event_type/outcome mismatch.
Step 4 — Price pull on confirmed SA date.

**Same failure_reason constraint as GNCA.**

---

### Case 6: PTGX — Protagonist Therapeutics (Priority 6)

**What training knowledge says:**
- Protagonist had a major collaboration agreement with Janssen (Johnson & Johnson) for rusfertide (PTG-300/izokibep, peptide thrombopoietin receptor mimetic for polycythemia vera)
- Collaboration gave Janssen option/ROFN rights for global development
- These rights appear to be program-specific (rusfertide), not whole-company acquisition rights
- Protagonist was still trading as of training knowledge cutoff

**Seed status:**
- observation_date: 2022-01-01 (rough estimate — collaboration may have been signed 2021)
- rofr_scope: PROGRAM_SPECIFIC (preliminary label, needs text confirmation)
- outcome: ONGOING (consistent with training knowledge)

**EDGAR research steps:**

Step 1 — Find the Janssen collaboration 8-K:
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=protagonist+therapeutics&CIK=&type=8-K&dateb=&owner=include&count=40
```
Search 2020-2022 for any 8-K mentioning Janssen or Johnson & Johnson collaboration.

Step 2 — Open collaboration agreement (Exhibit 10.x):
Find ROFR/ROFN clause. Read verbatim. Classify scope:
- If rights apply to rusfertide only → PROGRAM_SPECIFIC (confirms seed label)
- If rights apply to all Protagonist programs → ASSET_SPECIFIC or WHOLE_COMPANY

Step 3 — Confirm PTGX is still trading (check current ticker status).

Step 4 — Pull price on confirmed collaboration 8-K date (Protagonist is not delisted — Yahoo Finance sufficient for price pull).

**Anti-look-ahead risk: HIGH**
If Janssen later exercised its option/ROFN, do NOT use that as evidence of the original scope. Scope must come from 2021 agreement text only.

---

### Case 7: RIGL — Rigel Pharmaceuticals (Priority 7)

**What training knowledge says:**
- Rigel Pharmaceuticals had activist investor pressure approximately 2019-2021, demanding strategic review or sale
- No acquisition resulted as of training knowledge cutoff
- Potential activist: possibly Voce Capital Management (UNCONFIRMED — this must NOT be entered without EDGAR confirmation)
- Company still operating (Tavalisse/fostamatinib on market for ITP)

**Seed status:**
- observation_date: 2020-01-01 (very rough estimate — actual 13D date unknown)
- item4_intent: VERIFY_REQUIRED (correct — must come from Item 4 text)
- outcome: ONGOING (may be stale — confirm current status)

**EDGAR research steps:**

Step 1 — Find initial SC 13D against Rigel:
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=rigel+pharmaceuticals&CIK=&type=SC+13D&dateb=&owner=include&count=40
```
Identify earliest SC 13D filing (initial, not 13D/A amendments). Note:
- Filing date → observation_date
- Filer name (Item 1) → activist_filer
- Item 5 → activist_ownership_pct

Step 2 — Extract Item 4 text verbatim:
Open the 13D document. Navigate to "Item 4. Purpose of Transaction." Copy the complete Item 4 text (max 500 chars for excerpt_text; full text for item4_parser analysis).

Step 3 — Run item4_parser classification:
From `src/item4_parser.py`: pass Item 4 text. Record item4_intent, item4_confidence_score.

Step 4 — Confirm current outcome:
Check if RIGL is still trading. If still trading → outcome = ONGOING. If delisted → research what happened.

Step 5 — Price pull on 13D filing date.

**Anti-look-ahead: CRITICAL**
- item4_intent must come from INITIAL 13D text only
- Do not use knowledge of what activist demanded in later 13D/A amendments to classify original intent
- If first 13D says "passive accumulation" but later 13D/A escalates to "sale pressure" — the initial case classification = PASSIVE_ACCUMULATION (or whatever the initial text says)

---

### Case 8: CRBP — Corbus Pharmaceuticals (Priority 8)

**What training knowledge says:**
- Corbus Pharmaceuticals had lenabasum (cannabinoid receptor agonist) fail in multiple Phase 3 trials (dermatomyositis DETERMINE trial, IPF, SLE)
- Announced strategic alternatives review approximately 2022
- No acquisition occurred — company pivoted to oncology focus
- Whether a formal end-of-review announcement was made is uncertain

**Seed status:**
- observation_date: 2022-03-01 (rough estimate)
- outcome: REVIEW_ABANDONED (may need to be CAPITAL_RAISE or ONGOING)

**EDGAR research steps:**

Step 1 — Find SA announcement 8-K in 2022.

Step 2 — Find subsequent outcome announcement:
Options:
- 8-K announcing formal end of strategic review → outcome = REVIEW_ABANDONED, date = that 8-K date
- 8-K announcing equity offering / capital raise → outcome = CAPITAL_RAISE
- No formal announcement (review just ended quietly) → outcome = REVIEW_ABANDONED with outcome_date estimated from last strategic-related 8-K

Step 3 — Pull price on SA announcement date.

**failure_reason constraint:**
Must reflect what was publicly stated at the time of outcome announcement. Lenabasum Phase 3 failures are public record, so "pipeline failure in lenabasum led to inability to attract acquirer" is acceptable if this language (or close paraphrase) appears in contemporaneous filings.

---

### Case 9: FLXN — Flexion Therapeutics (Priority 9, NOT SEEDED)

**What training knowledge says:**
- Flexion Therapeutics (Zilretta — extended-release triamcinolone acetonide for knee OA pain) was acquired by Pacira BioSciences
- Deal approximately $8.50/share + CVR of up to $8.00/share additional contingent payments
- Deal announced October/November 2021
- Whether a prior SA or banker announcement preceded the merger is uncertain from training knowledge

**Not yet in cases_seed.csv. Do NOT add to seed until at minimum merger 8-K date is confirmed.**

**EDGAR research steps:**

Step 1 — Search for any pre-announcement process signals:
```
https://efts.sec.gov/LATEST/search-index?q=%22flexion%22+%22strategic+alternatives%22&forms=8-K&dateRange=custom&startdt=2020-01-01&enddt=2021-10-01
```
If found → observation_date = that 8-K date, signal_type = SA_AFFIRM or BANKER_RETAINED.

Step 2 — Find merger agreement 8-K (Oct-Nov 2021):
```
https://efts.sec.gov/LATEST/search-index?q=%22flexion%22+%22merger+agreement%22+%22pacira%22&forms=8-K&dateRange=custom&startdt=2021-01-01&enddt=2022-01-01
```
Confirm EDGAR filing date and deal_price_per_share from Item 1.01.

Step 3 — If no prior signal found: set observation_date = merger 8-K date, signal_type = MERGER_AGREEMENT, process_state_at_signal = SIGNED.

Step 4 — Pull adjusted price on confirmed observation_date.

**Case ID to assign:** FLXN-2021-001

---

### Case 10: DOVA — Dova Pharmaceuticals (Priority 10, NOT SEEDED)

**What training knowledge says:**
- Dova Pharmaceuticals had avatrombopag (thrombopoietin receptor agonist, branded as Doptelet) for immune thrombocytopenia (ITP) and thrombocytopenia in liver disease
- Swedish Orphan Biovitrum (Sobi) acquired Dova Pharmaceuticals
- Estimated deal approximately $27.50/share
- Approximate deal year: 2021

**Not yet in cases_seed.csv. Do NOT add to seed until merger 8-K date is confirmed.**

**EDGAR research steps:**

Step 1 — Search for pre-announcement signals:
```
https://efts.sec.gov/LATEST/search-index?q=%22dova%22+%22strategic+alternatives%22&forms=8-K&dateRange=custom&startdt=2020-01-01&enddt=2021-12-31
```

Step 2 — Find merger agreement 8-K:
```
https://efts.sec.gov/LATEST/search-index?q=%22dova%22+%22merger+agreement%22+%22sobi%22&forms=8-K&dateRange=custom&startdt=2020-01-01&enddt=2022-01-01
```
Confirm Sobi as acquirer and exact deal price from 8-K text.

Step 3 — Pull adjusted price on confirmed observation_date.

**Case ID to assign:** DOVA-2021-001

---

## Schema Gaps Discovered

### Gap 1: No intermediate status between CANDIDATE and PARTIAL

**Issue:** Current statuses: CANDIDATE (no data) → PARTIAL (some confirmed) → VERIFIED (all confirmed). There is no status for "pre-populated from training knowledge but no primary source confirmation." This session created pre-populated rows (e.g., deal values, approximate dates) that are better than CANDIDATE but should not reach PARTIAL.

**Proposed fix:** Add `STUB` status to data_quality enum: "Row has estimated values from secondary sources (training knowledge, news, databases) but no primary EDGAR source confirmed. Not usable for calibration. Research required."

Current workaround: Keep all pre-seeded rows at VERIFY_REQUIRED until EDGAR confirmation.

### Gap 2: MERGER_AGREEMENT-only cases have limited calibration value for P(deal)

**Issue:** Cases like FLXN, DOVA, IMGO (if no prior signal), PAND, ACHN, ALDR — where the scanner would only see MERGER_AGREEMENT at observation_date — do not contribute to P(deal) calibration because there was no observable process precursor. They calibrate a different question: "given we see a merger announcement, what are deal characteristics?" 

**Proposed fix:** Add a field `had_prior_process_signal` (boolean) to cases.csv. True if any observable process event preceded the merger_agreement signal. False if merger was the first observable signal. This partitions the calibration dataset correctly.

### Gap 3: event_type BANKRUPTCY vs outcome WIND_DOWN ambiguity

**Issue:** Cases GNCA and MGTA have `event_type=BANKRUPTCY` but `outcome=WIND_DOWN`. The schema uses these as separate concepts but the seeding mixed them. Need clearer guidance:
- BANKRUPT = formal Chapter 7 or Chapter 11 filing with PACER docket
- WIND_DOWN = company dissolves without formal bankruptcy petition
- These have different contemporaneous_source_url requirements

**Proposed fix:** Add to verification_checklist.md a mandatory check: "For WIND_DOWN outcomes, confirm no bankruptcy filing exists on PACER before assigning. If bankruptcy petition found → change to BANKRUPT."

### Gap 4: Delisted ticker price data guidance insufficient

**Issue:** 8 of 10 priority cases involve companies that were delisted after their process resolved. Yahoo Finance (yfinance) returns incomplete or unavailable data for delisted tickers. The verification_checklist.md only notes "Bloomberg required if delisted before end of price window" but doesn't specify a workflow.

**Proposed fix:** Add to verification_checklist.md:
- For delisted tickers: use yfinance only through the delisting date; use Bloomberg or CRSP for VERIFIED status
- If only Yahoo Finance data available → data_quality stays PARTIAL even if other fields confirmed
- CRSP WRDS access: preferred academic source for adjusted historical prices including delisted securities

### Gap 5: rofr_scope derivation from exhibits, not 8-K body

**Issue:** For ROFR cases (HARP, PTGX), the ROFR clause is typically in Exhibit 10.x (the actual collaboration/option agreement), not in the 8-K body text. The verification_checklist.md instructs researchers to "find the source text for the ROFR clause" but doesn't specify to look in exhibits vs. body.

**Proposed fix:** Add to Check E in verification_checklist.md: "ROFR scope text is typically in Exhibit 10.x attached to the 8-K, not in the 8-K body. Open the exhibit index and download the collaboration agreement document."

---

## Checklist Issues Discovered

### Issue 1: No PACER check for WIND_DOWN vs BANKRUPT resolution
**Add to Check C (Outcome Confirmation):** For WIND_DOWN and BANKRUPT cases, check PACER (court records) for any Chapter 7 or Chapter 11 filing. EDGAR 8-K may announce the intent; PACER has the actual petition. If EDGAR 8-K says "filed for bankruptcy protection" → PACER docket number should be captured in `notes`.

### Issue 2: item4_intent derivation — initial 13D vs amendments
**Add to Check D (Item 4 / Activist):** Explicitly state: "item4_intent must be derived from the INITIAL SC 13D filing only. If the initial 13D shows PASSIVE_ACCUMULATION but a later 13D/A shows escalation to SALE_PROCESS, record two separate events in filing_events.csv: one for the initial 13D (PASSIVE) and one for the first 13D/A that changes intent (ESCALATING). Do not backdate the initial classification."

### Issue 3: No guidance for cases with no prior process signal
**Add to Verification Queue Management:** "If EDGAR search reveals no pre-announcement process signal for an acquired company, document this explicitly in notes: 'No observable process precursor found — case added as MERGER_AGREEMENT signal_type for deal-characteristics calibration only.' Set had_prior_process_signal=FALSE (pending Gap 2 schema fix)."

---

## Next 5 Manual Research Actions

**Action 1 (Highest priority):**
Open EDGAR, find Imago BioSciences merger announcement 8-K (Nov-Dec 2022). Read Item 1.01 verbatim. Confirm acquirer name. Correct seed row IMGO-2022-001 if Merck is wrong.
```
https://www.sec.gov/cgi-bin/browse-edgar?company=imago+biosciences&CIK=&type=8-K&dateb=&owner=include&count=40&search_text=&action=getcompany
```

**Action 2:**
Find Harpoon Therapeutics AbbVie collaboration 8-K (2020). Confirm filing date. Open collaboration agreement exhibit. Read ROFR clause. Classify scope. This sets observation_date for HARP and resolves the case_id year mismatch.
```
https://www.sec.gov/cgi-bin/browse-edgar?company=harpoon+therapeutics&CIK=&type=8-K&dateb=&owner=include&count=40&search_text=&action=getcompany
```

**Action 3:**
Run yfinance price pull for HARP, SRRA, GNCA, MGTA using estimated observation_dates from seed. Store as PARTIAL price data. Bloomberg verification needed for VERIFIED status (all delisted).
```python
import yfinance as yf
cases = {
    'HARP': '2020-09-15',
    'SRRA': '2021-10-01',
    'GNCA': '2022-01-27',
    'MGTA': '2022-06-01',
}
for ticker, obs in cases.items():
    df = yf.download(ticker, start=obs, auto_adjust=True, progress=False)
    if not df.empty:
        print(f"{ticker}: price_at_signal = {df.iloc[0]['Close']:.2f}")
    else:
        print(f"{ticker}: no data (likely delisted before or on this date)")
```

**Action 4:**
Search EDGAR for Rigel Pharmaceuticals SC 13D filings. Find initial filing (not 13D/A). Confirm activist filer from EDGAR header. Extract Item 4 text verbatim. Run item4_parser on the text.
```
https://www.sec.gov/cgi-bin/browse-edgar?company=rigel+pharmaceuticals&CIK=&type=SC+13D&dateb=&owner=include&count=40&search_text=&action=getcompany
```

**Action 5:**
Search EDGAR for FLXN and DOVA merger agreement 8-K filings. Confirm Pacira as FLXN acquirer and Sobi as DOVA acquirer from 8-K text. Set observation_date and deal_date for both. Add confirmed stubs to cases_seed.csv with data_quality=VERIFY_REQUIRED.

---

_This document supersedes training knowledge. All field values require EDGAR primary source confirmation before any case advances to PARTIAL or VERIFIED._
