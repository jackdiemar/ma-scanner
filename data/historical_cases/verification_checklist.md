# Verification Checklist — Historical Process Intelligence Pipeline

_Version 1.0 | Created 2026-05-09_
_Purpose: Step-by-step process for advancing a case from CANDIDATE → PARTIAL → VERIFIED. Every field in the five-layer schema must pass the relevant check before status upgrades._

---

## Status Definitions

| Status | Meaning | Usable for Calibration | Promoted By |
|--------|---------|----------------------|-------------|
| CANDIDATE | In collection_targets.csv queue only. No cases.csv row yet. | No | Manual research decision |
| STUB | cases.csv row exists. Pre-populated from training knowledge or secondary sources. No primary EDGAR source confirmed. | No | edgar_evidence_finder.py or manual seed |
| PARTIAL | cases.csv row exists. observation_date + source_filing_url confirmed from EDGAR. 1+ VERIFIED source_evidence row. Price or outcome incomplete. | No (structural tests only) | EDGAR confirmation of primary filing |
| VERIFIED | All required fields confirmed against primary sources. | Structural tests only | Full verification checklist passed |
| CALIBRATION_ELIGIBLE | VERIFIED + anti-look-ahead rules confirmed + price window complete. | **YES** | Anti-look-ahead checklist + price completeness |

**Status progression:** CANDIDATE → STUB → PARTIAL → VERIFIED → CALIBRATION_ELIGIBLE

**Only CALIBRATION_ELIGIBLE rows feed P(deal) tables.** VERIFIED rows can be counted but not used for rate calculations.

**STUB rows:** Created by `edgar_evidence_finder.py` or added to `cases_seed.csv` with pre-populated values from secondary sources. Every row in cases_seed.csv starts as STUB (previously labeled VERIFY_REQUIRED). A STUB row has structural value (defines the case) but zero calibration value until promoted to PARTIAL.

**Promoting STUB → PARTIAL requires:**
1. EDGAR filing URL confirmed (source_filing_url = real EDGAR index URL, not search page)
2. observation_date confirmed as EDGAR filing date (not approximation)
3. At least 1 source_evidence.csv row with verification_status=VERIFIED for this case

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

**Delisted Ticker Price Workflow (priority order):**

**Tier 1 — yfinance (free, required attempt for all cases):**
```python
import yfinance as yf, pandas as pd

def get_price_window(ticker: str, obs_date: str) -> dict:
    """Pull price_at_signal and forward prices. Returns dict of field → value."""
    obs = pd.Timestamp(obs_date)
    end = obs + pd.Timedelta(days=400)
    df = yf.download(ticker, start=obs_date, end=end.strftime('%Y-%m-%d'),
                     auto_adjust=True, progress=False)
    if df.empty:
        return {'error': 'No data — ticker may be delisted before obs_date'}
    
    def price_on_or_after(dt):
        sub = df[df.index >= dt]
        return round(float(sub.iloc[0]['Close']), 2) if not sub.empty else None
    
    price_at  = price_on_or_after(obs)
    price_30d = price_on_or_after(obs + pd.Timedelta(days=30))
    price_90d = price_on_or_after(obs + pd.Timedelta(days=90))
    price_180d = price_on_or_after(obs + pd.Timedelta(days=180))
    
    # Max drawdown within 365d
    window = df[(df.index >= obs) & (df.index <= obs + pd.Timedelta(days=365))]
    if price_at and not window.empty:
        trough = float(window['Close'].min())
        drawdown = round((trough - price_at) / price_at, 4)
    else:
        drawdown = None
    
    return {
        'price_at_signal':        price_at,
        'price_30d_after':        price_30d,
        'price_90d_after':        price_90d,
        'price_180d_after':       price_180d,
        'max_drawdown_pct':       drawdown,
        'last_available_date':    str(df.index[-1].date()) if not df.empty else None,
        'source':                 'yfinance (auto_adjust=True)',
    }
```
Use **auto_adjust=True** (handles splits and dividends). If the observation date falls on a non-trading day, use the next trading day close (yfinance `.iloc[0]` handles this automatically).

**Tier 2 — Stooq (free, good coverage for delisted US stocks):**
```
URL: https://stooq.com/q/d/l/?s={TICKER}.us&i=d
Returns CSV: Date, Open, High, Low, Close, Volume
Filter to obs_date window. Use Close column.
```

**Tier 3 — Nasdaq Data Link / Alpha Vantage (API key required):**
```
https://data.nasdaq.com/api/v3/datatables/WIKI/PRICES?ticker={TICKER}&api_key={KEY}
```

**Tier 4 — Bloomberg Terminal (required for VERIFIED status on delisted tickers):**
```
{TICKER} US Equity HP <GO>
Set date range: [obs_date - 5d] to [obs_date + 370d]
Field: PX_LAST (adjusted)
Export to Excel
```

**Data quality rules:**
- yfinance data → data_quality stays PARTIAL even if other fields confirmed
- Stooq data → data_quality stays PARTIAL
- Bloomberg data → acceptable for VERIFIED status
- If ticker delisted before 180d window closes → record `price_180d_after = null` and note delisting date in `notes`
- `max_drawdown_pct_after_signal` must use full 365d window or through delisting date, whichever is earlier

Record price evidence in source_evidence.csv:
```
evidence_type: PRICE_DATA
source_name:   "Yahoo Finance / yfinance" or "Bloomberg Terminal"
supports_field: price_at_signal|price_30d_after|price_90d_after|price_180d_after|max_drawdown_pct_after_signal
```

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

**For BANKRUPT cases (corporate_outcome = BANKRUPT):**
- [ ] Locate the Chapter 7 or Chapter 11 petition on EDGAR or PACER
- [ ] `outcome_date` = EDGAR 8-K filing date announcing the bankruptcy (not the internal filing date)
- [ ] Check PACER for actual petition docket: `https://pacer.gov` → search by company name or CIK
- [ ] Record whether Chapter 7 (liquidation) or Chapter 11 (reorganization) in `notes`
- [ ] `contemporaneous_source_url` = the 8-K announcing the filing (preferred) or PACER docket URL
- [ ] Set `process_event_type = BANKRUPTCY_FILED` and `corporate_outcome = BANKRUPT`

**For WIND_DOWN cases (corporate_outcome = WIND_DOWN):**
- [ ] Locate the wind-down announcement 8-K
- [ ] Confirm company stopped operations (not just paused one program or reduced headcount)
- [ ] **Mandatory PACER check:** Confirm NO Chapter 7 or Chapter 11 petition was filed
  ```
  PACER search: https://pacer.gov → Party Search → Company Name
  If petition found → reclassify corporate_outcome to BANKRUPT
  ```
- [ ] `outcome_date` = EDGAR filing date of wind-down 8-K
- [ ] Set `process_event_type = WIND_DOWN_ANNOUNCED` and `corporate_outcome = WIND_DOWN`

**Distinguishing WIND_DOWN from BANKRUPT (resolves GNCA/MGTA ambiguity):**

| Indicator | corporate_outcome |
|-----------|-----------------|
| Company files Chapter 7 or Chapter 11 with the bankruptcy court | BANKRUPT |
| Company announces dissolution/wind-down but does NOT file bankruptcy | WIND_DOWN |
| Company completes wind-down and dissolves state charter | WIND_DOWN |
| Company files Chapter 11 then converts to Chapter 7 | BANKRUPT |

The presence of a PACER docket number = BANKRUPT. The absence = WIND_DOWN (if 8-K says "wind down").

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

**Step 1 — Find the agreement exhibit (NOT the 8-K body):**
ROFR/ROFN clauses are almost always in Exhibit 10.x of the 8-K (the actual collaboration or license agreement), NOT in the 8-K body text. The 8-K body only announces the collaboration; the exhibit contains the operative legal terms.

```
Procedure:
1. Open the 8-K filing index URL.
2. Look for the exhibit table near the bottom of the index page.
3. Find entries labeled "EX-10.1", "EX-10.2", etc. — these are the agreement exhibits.
4. Click the exhibit link to download the collaboration/license agreement text.
5. Search the exhibit for: "right of first refusal", "right of first negotiation",
   "option to acquire", "change of control" headings.
```

**Step 2 — Run exhibit_scope_extractor.py:**
```bash
python3 src/historical_case_tools/exhibit_scope_extractor.py \
    --file /path/to/exhibit.txt --output json
```
Or pass the EDGAR exhibit URL directly:
```bash
python3 src/historical_case_tools/exhibit_scope_extractor.py \
    --edgar-url https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION}/exhibit10-1.htm
```

**Step 3 — Classify scope from actual clause language:**
- [ ] `rofr_scope = WHOLE_COMPANY`: clause explicitly covers acquisition of the entire company (looks for "merger", "acquisition of the company", "all outstanding shares")
- [ ] `rofr_scope = PROGRAM_SPECIFIC`: clause names a specific compound (e.g., "rusfertide", "HARP-3521") — use the compound name as `affected_asset`
- [ ] `rofr_scope = ASSET_SPECIFIC`: clause covers a defined collaboration asset/program bundle but not a single named compound
- [ ] `rofr_scope = TERRITORY_SPECIFIC`: clause applies only within a named geographic territory

**Step 4 — Anti-look-ahead requirement:**
- [ ] Scope must be derived from the ORIGINAL agreement text at collaboration signing date
- [ ] Do NOT use knowledge of whether the ROFR was later exercised to classify original scope
- [ ] If the agreement was subsequently amended, classify scope from the EARLIEST version

**Step 5 — Record in source_evidence.csv:**
```
evidence_type:  EXHIBIT_AGREEMENT
exhibit_number: 10.1 (or whichever exhibit number)
supports_field: rofr_scope|excerpt_text
excerpt:        verbatim ROFR clause text (max 500 chars)
```

**Calibration note:** exhibit_scope_extractor.py confidence < 0.5 = manual review required before assigning rofr_scope. Do not auto-accept LOW confidence outputs.

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
