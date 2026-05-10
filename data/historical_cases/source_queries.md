# Source Queries — Historical Process Intelligence Pipeline

_Version 1.0 | Created 2026-05-09_
_Purpose: Repeatable search queries for each case category. Run these to populate collection_targets.csv candidates and locate primary source filings._

---

## 1. EDGAR Full-Text Search (efts.sec.gov)

Base URL: `https://efts.sec.gov/LATEST/search-index?q=%22{PHRASE}%22&dateRange=custom&startdt={START}&enddt={END}&forms={FORM}`

### 1A. Strategic Alternatives — 8-K Filings

```
# SA affirmation in 8-K body
https://efts.sec.gov/LATEST/search-index?q=%22strategic+alternatives%22+%22board+of+directors%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# Narrower: SA + sale process language
https://efts.sec.gov/LATEST/search-index?q=%22strategic+alternatives%22+%22sale+of+the+company%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# Banker retained language
https://efts.sec.gov/LATEST/search-index?q=%22financial+advisor%22+%22strategic+alternatives%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# Merger agreement (deal announced)
https://efts.sec.gov/LATEST/search-index?q=%22merger+agreement%22+%22per+share%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31
```

Filter to biotech SIC codes after retrieval:
- 2836 (Pharmaceutical Preparations)
- 2835 (In Vitro & In Vivo Diagnostic Substances)
- 8731 (Commercial Physical & Biological Research)
- 2830 (Drugs)

### 1B. Activist 13D Filings — Item 4 Language

```
# Sale process intent in Item 4
https://efts.sec.gov/LATEST/search-index?q=%22sale+of+the+company%22+%22Item+4%22&forms=SC+13D,SC+13D%2FA&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# Strategic review language in 13D
https://efts.sec.gov/LATEST/search-index?q=%22explore+strategic+alternatives%22&forms=SC+13D,SC+13D%2FA&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# Board change + activist
https://efts.sec.gov/LATEST/search-index?q=%22board+representation%22+%22maximize+shareholder+value%22&forms=SC+13D,SC+13D%2FA&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# Tender offer letter in 13D
https://efts.sec.gov/LATEST/search-index?q=%22tender+offer%22+%22per+share%22&forms=SC+13D,SC+13D%2FA&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31
```

### 1C. ROFR/ROFN Disclosures

```
# ROFR in 8-K (partnership/licensing disclosures)
https://efts.sec.gov/LATEST/search-index?q=%22right+of+first+refusal%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# ROFN in 8-K
https://efts.sec.gov/LATEST/search-index?q=%22right+of+first+negotiation%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# ROFR in 10-K risk factors or MD&A
https://efts.sec.gov/LATEST/search-index?q=%22right+of+first+refusal%22+%22collaboration%22&forms=10-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31
```

### 1D. Wind-Down and Bankruptcy Filings

```
# Wind-down 8-K
https://efts.sec.gov/LATEST/search-index?q=%22wind+down%22+%22cease+operations%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# Chapter 11 filing announcement
https://efts.sec.gov/LATEST/search-index?q=%22chapter+11%22+%22voluntary+petition%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# Chapter 7
https://efts.sec.gov/LATEST/search-index?q=%22chapter+7%22+%22cease+operations%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31
```

### 1E. Asset Sale Filings

```
# Asset sale 8-K
https://efts.sec.gov/LATEST/search-index?q=%22asset+purchase+agreement%22+%22program%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31

# Program divestiture
https://efts.sec.gov/LATEST/search-index?q=%22sold%22+%22exclusive+license%22+%22upfront%22&forms=8-K&dateRange=custom&startdt=2018-01-01&enddt=2024-12-31
```

### 1F. EDGAR Company Search by SIC — for Batch Scraping

Direct EDGAR company search filtered to biotech SIC:
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=SC+13D&dateb=&owner=include&count=40&search_text=&SIC=8731
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=8-K&dateb=&owner=include&count=40&search_text=&SIC=2836
```

Retrieve CIK → then pull full filing history:
```
https://data.sec.gov/submissions/CIK{XXXXXXXXXX}.json
```

---

## 2. EDGAR Full-Text Search — Direct URL Builder

For retrieving a specific company's 13D filing history:

```
# All SC 13D filings for a given company CIK
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK}&type=SC+13D&dateb=&owner=include&count=40

# All 8-K filings for a given company CIK
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK}&type=8-K&dateb=&owner=include&count=40

# Retrieve filing index by accession number
https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION_NO_DASHES}/

# Example: HARP CIK = 0001800315
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001800315&type=8-K&dateb=&owner=include&count=40
```

---

## 3. Bloomberg Law Queries

### 3A. M&A Deal Database Filter

Navigation: Bloomberg Law → Mergers & Acquisitions → Deal Search

Filter parameters for COMPLETED_DEAL candidates:
```
Deal Type:        Merger/Acquisition (exclude minority stake)
Target Industry:  Biotechnology / Pharmaceuticals
Deal Status:      Completed
Announce Date:    2018-01-01 to 2024-12-31
Deal Value:       $50M minimum (exclude nano-cap noise)
Target Country:   United States
```

Sort by: Announce Date DESC. Export CSV with: Target, Acquirer, Announce Date, Deal Value, Premium.

### 3B. Failed Deal Filter

```
Deal Type:        Merger/Acquisition
Target Industry:  Biotechnology / Pharmaceuticals
Deal Status:      Withdrawn / Terminated
Announce Date:    2018-01-01 to 2024-12-31
Target Country:   United States
```

Look for: Termination Date, Termination Reason field (varies by deal), any press release link.

### 3C. Price Pull for Specific Dates

Bloomberg terminal command for historical price on observation_date:
```
{TICKER} US Equity HP <GO>
Set date range to: [observation_date - 5d] to [observation_date + 180d]
Fields: PX_LAST (closing price)
Export: Excel
```

For batch pull (multiple tickers):
```
XLTP <GO> → Custom template with PX_LAST, date range
```

---

## 4. WhaleWisdom / 13D Monitor Queries

### 4A. WhaleWisdom 13D Search

URL: `https://whalewisdom.com/filer_13d`

Filter by:
- Filing Type: SC 13D (initial only, exclude 13G)
- Date Range: 2018-01-01 to 2024-12-31
- Industry: Biotechnology / Healthcare

Export CSV → cross-reference with collection_targets.csv by ticker.

Key fields: Filer Name, Filing Date, Ownership %, Intent (from Item 4 classification if available).

### 4B. 13D Monitor (Subscription)

Navigation: Search → Filing Type: 13D → Industry: Biotech

Filter for activist intent categories:
- "Seeking Sale" or "Strategic Alternatives" (where platform classifies intent)
- "Board Representation" + "Sale"

Cross-reference result ticker list against:
1. EDGAR full-text for the actual 13D text
2. Yahoo Finance for prices on filing date

---

## 5. BioPharma Catalyst / Biotech Deal Databases

### 5A. BioPharma Catalyst Deal Database

URL: `https://biopharmacat.com`

Filter:
- Type: M&A
- Status: Completed / Failed
- Year: 2018–2024

Export or manually collect: Ticker, Deal Date, Acquirer, Deal Value, Premium.

### 5B. Evaluate Pharma / BCIQ (if available)

Deal search → Biotech → US → Completed → 2018–2024.

Primary use: Cross-check deal premium and deal value against Bloomberg. Not a primary source for EDGAR fields.

### 5C. BioPharmaDive / Endpoints News (Secondary Only)

Use for:
- Finding failure_reason text (contemporaneous reporting at wind-down time)
- Confirming timeline for activist campaigns
- Cross-referencing strategic review announcements

Not a primary source. Must ground all facts in EDGAR filings.

---

## 6. Yahoo Finance — Price Data Pull

For price_at_signal, price_30d/90d/180d_after, max_drawdown_pct_after_signal.

### 6A. Manual Pull (Single Ticker)

```
URL: https://finance.yahoo.com/quote/{TICKER}/history/
Set date range: [observation_date - 5d] to [observation_date + 365d]
Download CSV
```

Key columns: Date, Adj Close (use Adj Close, not Close, for split/dividend adjustment).

### 6B. Python yfinance Pull (Batch)

```python
import yfinance as yf
import pandas as pd

tickers = ['HARP', 'SRRA', 'IMGO']  # list from collection_targets
obs_dates = {'HARP': '2021-09-01', 'SRRA': '2020-06-15', 'IMGO': '2021-11-01'}

for ticker, obs_date in obs_dates.items():
    start = pd.Timestamp(obs_date) - pd.Timedelta(days=5)
    end   = pd.Timestamp(obs_date) + pd.Timedelta(days=370)
    df = yf.download(ticker, start=start, end=end, auto_adjust=True)
    
    # price at signal
    sig_row = df[df.index >= obs_date].iloc[0]
    price_at_signal = round(sig_row['Close'], 2)
    
    # 30d, 90d, 180d
    for days in [30, 90, 180]:
        target_date = pd.Timestamp(obs_date) + pd.Timedelta(days=days)
        future = df[df.index >= target_date]
        if not future.empty:
            price = round(future.iloc[0]['Close'], 2)
        else:
            price = None
        print(f'{ticker} +{days}d: {price}')
    
    # max drawdown: trough within 365 days
    window = df[(df.index >= obs_date)]
    if not window.empty:
        trough = window['Close'].min()
        drawdown = round((trough - price_at_signal) / price_at_signal, 4)
        print(f'{ticker} max_drawdown: {drawdown}')
```

Note: For delisted tickers, yfinance may return partial data. Supplement with Bloomberg or CRSP for VERIFIED status.

---

## 7. Activist Database Cross-Reference

### 7A. ActivistInsight (Subscription)

Campaign search → Industry: Biotech → Start Date: 2018–2024.

Fields to capture: Activist Name, Target Company, Campaign Start, Demands (sale, board seats, other), Campaign Resolution, Resolution Date.

### 7B. 13D Filing Direct Text Retrieval

For any 13D in collection_targets, retrieve Item 4 text directly:

```
# Step 1: Find filing accession number
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK}&type=SC+13D&count=10

# Step 2: Retrieve filing index
https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION}/

# Step 3: Find .htm or .txt exhibit for full filing text
# Item 4 is typically in the main document body
```

Extract verbatim Item 4 text. Paste into language_observations.csv rows (2–8 phrases per filing).

---

## 8. Query Execution Priority

Run in this order to maximize coverage per hour of research:

| Priority | Source | Best For |
|----------|--------|----------|
| 1 | EDGAR EFTS full-text (Section 1A) | SA + merger 8-K cases |
| 2 | Bloomberg Law M&A database (Section 3A/3B) | COMPLETED_DEAL and FAILED_REVIEW |
| 3 | EDGAR 13D full-text (Section 1B) | ACTIVIST cases, Item 4 language |
| 4 | Yahoo Finance yfinance (Section 6B) | Price data for all PARTIAL cases |
| 5 | WhaleWisdom / 13D Monitor (Section 4) | Activist discovery for new candidates |
| 6 | EDGAR ROFR search (Section 1C) | ROFR_CASE category |
| 7 | BioPharma Catalyst / BioPharmaDive (Section 5) | Deal premium cross-check + failure_reason |

---

_All queries return candidates only. Every case must pass verification_checklist.md before status moves from CANDIDATE → PARTIAL → VERIFIED._
