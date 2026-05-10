# Verification Checklist — Historical Process Intelligence Pipeline

_Version 1.0 | Created 2026-05-09_
_Purpose: Step-by-step process for advancing a case from CANDIDATE → PARTIAL → VERIFIED. Every field in the five-layer schema must pass the relevant check before status upgrades._

---

## Status Definitions

| Status | Meaning | Usable for Calibration |
|--------|---------|----------------------|
| CANDIDATE | In collection_targets.csv queue only. No data populated yet. | No |
| PARTIAL | cases.csv row exists. 1+ key fields unconfirmed or missing. | No |
| VERIFIED | All required fields confirmed against primary sources. | Yes |

**Only VERIFIED=TRUE rows count in any calibration query.** This is enforced in all `_calibration_tables` SQL templates.

---

## Pre-Work: Confirm the Case Exists

Before opening any schema file, confirm these three things:

1. **Company was publicly traded in the US** during the event window (NYSE, NASDAQ, or OTC).
2. **At least one SEC filing exists** that constitutes a process signal (8-K with SA language, SC 13D with sale-pressure Item 4, merger agreement, etc.).
3. **You have the correct ticker** — confirm against EDGAR company search, not memory. Tickers change after mergers and delistings.

```
EDGAR company search: https://www.sec.gov/cgi-bin/browse-edgar?company={COMPANY_NAME}&CIK=&type=&dateb=&owner=include&count=10&search_text=&action=getcompany
```

If the company does not appear in EDGAR or never had qualifying SEC filings, mark EXCLUDE in collection_targets.csv and stop.

---

## Phase 1: CANDIDATE → PARTIAL

### Step 1. Locate Primary Signal Filing on EDGAR

For each case, identify the **first qualifying process signal filing** (this sets `first_observation_date`):

| Signal Type | Filing Type to Find |
|-------------|-------------------|
| SA_AFFIRM / SA_BOILERPLATE | 8-K (Item 1.01 or press release exhibit) |
| BANKER_RETAINED | 8-K announcing financial advisor engagement |
| ACTIVIST_13D | SC 13D (initial filing, not 13D/A) |
| ROFR_ROFN | 8-K disclosing collaboration/licensing with ROFR clause |
| MERGER_AGREEMENT | 8-K Item 1.01 announcing execution of merger agreement |

```
EDGAR search:
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK}&type={FORM_TYPE}&dateb=&owner=include&count=40
```

**Record:**
- `source_filing_type` (exact EDGAR form type: "8-K", "SC 13D", etc.)
- `source_filing_date` (EDGAR-reported filing date, not press release date)
- `source_filing_url` (full EDGAR index URL: `https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION}/`)
- `accession_number` (format: `XXXXXXXXXX-YY-ZZZZZZ`)

**Anti-look-ahead check:** The `first_observation_date` must be the date the signal was publicly observable (EDGAR filing date). Do NOT set it to an earlier date when the board may have internally decided to run a process.

### Step 2. Pull Price on first_observation_date

Using Yahoo Finance or Bloomberg:

```python
# yfinance minimal pull
import yfinance as yf
obs = '2022-03-15'  # observation date
df = yf.download(ticker, start=obs, end='...', auto_adjust=True)
price_at_signal = df.iloc[0]['Close']
```

- Use **adjusted closing price** (accounts for splits and dividends)
- If the observation date falls on a non-trading day, use the **next trading day's open**
- Record in `cases.csv`: `price_at_signal`
- Record in `outcomes.csv`: `price_at_signal`

### Step 3. Extract Key Signal Excerpt

Open the primary filing HTML on EDGAR. Find the passage that establishes the signal.

For 8-K (SA): Find the press release exhibit (EX-99.1) or Item 1.01. Copy verbatim.
For SC 13D: Navigate to Item 4 ("Purpose of Transaction"). Copy verbatim.
For merger agreement 8-K: Find the consideration terms (price per share) in Item 1.01.

Record in `cases.csv`: `excerpt_text` (max 500 chars verbatim).
Record in `filing_events.csv`: `excerpt` (same or related verbatim text).

**Do not paraphrase.** Verbatim only.

### Step 4. Populate cases.csv Row (Required Fields)

These fields must be filled before PARTIAL status:

```
case_id             TICKER-YYYY-NNN format (e.g., HARP-2021-001)
ticker              Confirmed against EDGAR
company_name        Legal entity name from EDGAR filings
first_observation_date  Earliest public signal date (EDGAR filing date)
signal_type         enum value from schema
event_type          enum value from schema
process_state_at_signal  LIVE / PATHWAY / SIGNED / SCREENING (rule-based)
signal_quality      AFFIRM / PROCESS / ROFR / MERGER / BOILERPLATE / SCORE_ONLY
source_filing_type  Exact EDGAR form type
source_filing_date  EDGAR filing date
source_filing_url   Full EDGAR index URL
price_at_signal     Confirmed closing price
data_quality        Set to PARTIAL
```

Set `data_quality = PARTIAL` and `verified = false`.

---

## Phase 2: PARTIAL → VERIFIED

Complete all of the following checks. All must pass for `data_quality` to become `VERIFIED`.

### Check A. EDGAR URL Confirmation

Open the `source_filing_url`. Confirm:
- [ ] URL resolves to a real EDGAR index page
- [ ] Filing date on EDGAR matches `source_filing_date`
- [ ] Filing type matches `source_filing_type`
- [ ] Company name on EDGAR matches `company_name`
- [ ] Accession number formatted correctly: `XXXXXXXXXX-YY-ZZZZZZ`

If the URL returns 404 or redirects to an index page without the expected filing, find the correct accession number via:
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK}&type={FORM_TYPE}&count=40
```

### Check B. Price Data Confirmation

- [ ] `price_at_signal` confirmed as **adjusted close** on `first_observation_date`
- [ ] `price_30d_after_signal`: confirmed or null with reason documented
- [ ] `price_90d_after_signal`: confirmed or null
- [ ] `price_180d_after_signal`: confirmed or null

For VERIFIED status, Yahoo Finance (yfinance) is acceptable for price_at_signal and 30/90/180d prices. Bloomberg is required only if:
- The stock was delisted before the end of the price window, or
- A stock split occurred during the window and yfinance data appears unadjusted.

For `max_drawdown_pct_after_signal` in VERIFIED outcomes: pull full daily price series from `first_observation_date` to `first_observation_date + 365d`. Calculate:
```python
max_drawdown = (trough_price - price_at_signal) / price_at_signal
# Result must be negative (e.g., -0.42 = -42% drawdown)
```

### Check C. Outcome Confirmation

**For ACQUIRED cases:**
- [ ] Locate deal announcement 8-K on EDGAR (contemporaneous, not Wikipedia/news)
- [ ] `deal_price_per_share` matches the "per share" consideration in the filing text
- [ ] `deal_premium_pct` is calculated as premium to **30-day average price before announcement**, NOT to price_at_signal
- [ ] `outcome_date` = date the 8-K was filed (not the deal close date)
- [ ] `acquirer` and `acquirer_type` confirmed from the 8-K text
- [ ] `contemporaneous_source_url` = the deal announcement 8-K URL on EDGAR

**For DEAL_FAILED / REVIEW_ABANDONED cases:**
- [ ] Locate the termination announcement filing (8-K, press release, or proxy statement)
- [ ] `failure_reason` grounded in contemporaneous public evidence (board statement, press release quote)
- [ ] `failure_mode` assigned from the enum — must be based on what was publicly stated at the time
- [ ] `contemporaneous_source_url` = the termination filing URL

**Anti-look-ahead check for failure_reason:** The failure_reason must reflect what was publicly known at `outcome_date`. Do NOT incorporate knowledge of events that occurred after the outcome was announced (pipeline results, future trials, post-outcome financings).

**For BANKRUPT cases:**
- [ ] Locate the Chapter 7 or Chapter 11 petition on EDGAR or PACER
- [ ] `outcome_date` = petition date (not the wind-down announcement)
- [ ] `contemporaneous_source_url` = the 8-K announcing the filing (or PACER docket if no 8-K)

**For WIND_DOWN cases:**
- [ ] Locate the wind-down announcement 8-K
- [ ] Confirm company stopped operations (not just paused one program)
- [ ] `outcome_date` = date of wind-down 8-K

**For ONGOING cases:**
- [ ] Confirm ticker is still actively traded as of verification date
- [ ] `outcome_date` = null
- [ ] `time_to_resolution_days` = null

### Check D. Item 4 / Activist Fields (13D Cases Only)

If `signal_type = ACTIVIST_13D`:
- [ ] `item4_intent` derived from verbatim Item 4 text, not from outcome or activism outcome databases
- [ ] `item4_confidence_score` assigned if item4_parser has been run on the filing text
- [ ] `activist_filer` confirmed from EDGAR filer name (exact legal entity, not abbreviated)
- [ ] `activist_ownership_pct` confirmed from Item 5 of the 13D

### Check E. ROFR/ROFN Scope (ROFR Cases Only)

If `signal_type = ROFR_ROFN`:
- [ ] `rofr_scope` confirmed from the collaboration/licensing agreement text
  - WHOLE_COMPANY: rights apply to an acquisition of the full company
  - ASSET_SPECIFIC: rights apply to a specific asset or program
  - PROGRAM_SPECIFIC: rights apply to a named drug/compound
  - TERRITORY_SPECIFIC: rights apply only to a geographic territory
- [ ] Source text for the ROFR clause found and excerpted in `filing_events.csv`

### Check F. Market Cap Confirmation

- [ ] `mcap_at_signal_M` = shares outstanding × price_at_signal (from EDGAR or yfinance)
- [ ] `mcap_band` assigned correctly based on `mcap_at_signal_M`:

| mcap_at_signal_M | mcap_band |
|-----------------|-----------|
| < 100 | NANO_sub100M |
| 100–399.99 | SMALL_100_400M |
| 400–999.99 | MID_400M_1B |
| 1000–1999.99 | UPPER_1B_2B |
| ≥ 2000 | ABOVE_2B |

- [ ] `in_target_range` = true if `mcap_at_signal_M` is between 150 and 1500. All others = false. This does NOT exclude the case from the library — it flags whether it would have been in the scanner universe.

### Check G. Language Observations Layer (Optional for PARTIAL, Required for VERIFIED)

For VERIFIED status, at least 2 language_observations rows must exist for the case's primary signal filing:

- [ ] Each row has a verbatim `phrase` (max 200 chars)
- [ ] Each row has `surrounding_context` (50–100 words from the filing)
- [ ] `section_source` assigned (ITEM_4, ITEM_5, BODY, EXHIBIT, etc.)
- [ ] `is_downgrade_marker` set for each phrase (true/false)
- [ ] `later_outcome` left as ONGOING (filled retrospectively only after outcome is known)
- [ ] `phrase_was_predictive` left as null (filled retrospectively only)

### Check H. Final Status Update

Once all checks above pass:

```
cases.csv:         data_quality → VERIFIED, verified → true
filing_events.csv: data_quality → VERIFIED, verified → true
outcomes.csv:      verified → true
transitions.csv:   verified → true (for each transition row)
```

If any check fails, document the gap in `notes` field and keep `data_quality = PARTIAL`.

---

## Anti-Look-Ahead Rule Checklist (Run on Every Row)

Before setting `verified = true`, confirm no anti-look-ahead violations:

- [ ] `first_observation_date` = EDGAR filing date of first public signal (not board decision date, not news article date)
- [ ] `price_at_signal` = closing price on `first_observation_date` (not the day before, not a pre-announcement estimate)
- [ ] `item4_intent` = derived from Item 4 text only, not from knowledge of what the activist later did
- [ ] `sequence_type` = the sequence observable at `first_observation_date` only (not what the full case arc shows)
- [ ] `failure_reason` = what was publicly stated at `outcome_date` (no post-outcome evidence)
- [ ] `deal_premium_pct` = premium to 30-day pre-announcement average (not to `price_at_signal`)
- [ ] `later_outcome` in language_observations = filled only AFTER outcome is confirmed (not during initial labeling)
- [ ] `phrase_was_predictive` = filled only after outcome is confirmed and only in a retrospective batch update
- [ ] `eventual_outcome` in transitions = filled only AFTER outcome is confirmed
- [ ] No field infers private information (board minutes, confidential negotiations, insider knowledge)

---

## Common Errors — Stop and Fix Before Proceeding

| Error | How to Fix |
|-------|-----------|
| `first_observation_date` is a news article date, not EDGAR date | Replace with EDGAR filing date |
| `deal_premium_pct` calculated vs. `price_at_signal` | Recalculate: use 30-day average BEFORE announcement 8-K |
| `failure_reason` includes post-outcome pipeline data | Strip out all post-outcome evidence |
| `source_filing_url` is a search page, not a direct index URL | Find the direct accession index URL |
| `item4_intent` copied from activism database, not filing text | Open the 13D on EDGAR and re-derive from Item 4 text |
| `price_at_signal` is unadjusted close (pre-split) | Re-pull with `auto_adjust=True` in yfinance |
| ROFR scope labeled WHOLE_COMPANY without reading the agreement | Open the partnership agreement filing, confirm scope explicitly |
| `mcap_band` assigned from memory, not confirmed calculation | Pull shares outstanding from EDGAR, multiply by price |

---

## Verification Queue Management

After completing verification:

1. Update `collection_targets.csv`: change `verification_status` from CANDIDATE → PARTIAL or VERIFIED.
2. Add a row to `COLLECTION_LOG.md` under the verified cases section with: ticker, case_id, verification date, primary source URL, and any open gaps.
3. If the case was a false-positive (signal appeared but no deal, no strategic action): document in `failure_reason` and `failure_mode`. These are equally important as deal cases for calibration.

**Minimum verified cases before calibration use:**

| Calibration Output | Minimum VERIFIED Rows |
|-------------------|----------------------|
| P(deal) by signal_type table | 100 cases |
| P(deal) by sequence_type table | 100 cases |
| Median deal premium | 50 ACQUIRED cases |
| Failure drawdown distribution | 50 DEAL_FAILED + REVIEW_ABANDONED cases |
| Phrase weight recalibration | 500 language_observations from 80 cases |
| Analog matching | 100 cases |

Until minimums are met, no calibration output should be surfaced in the scanner or dashboard.

---

_This checklist supersedes any informal verification approach. Every VERIFIED=TRUE row must have passed all applicable checks._
