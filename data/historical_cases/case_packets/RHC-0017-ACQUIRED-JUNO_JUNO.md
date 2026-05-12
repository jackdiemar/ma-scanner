# Case Packet: JUNO - RHC-0017-ACQUIRED-JUNO

## Summary

- Company: Juno Therapeutics, Inc.
- Likely outcome type: ACQUIRED
- Current status: CANDIDATE
- Recommended status: PARTIAL_READY
- Workflow completeness score: 55/100
- Score note: workflow completeness only. Not investment quality and not P(deal).
- Priority: HIGH

## Evidence Status

- Source evidence rows: 2
- Acquisition evidence status: SOURCE_BACKED
- Background section status: FOUND
- Background heading: Background of the Transaction
- Proxy source URL: https://www.sec.gov/Archives/edgar/data/1594864/000119312518030824/d514862dsc14d9.htm
- Prior process signal status: NOT_REVIEWED
- Prior process signal: not reviewed
- Prior process signal type: not available
- Prior process signal date: not available
- Observation date candidate: not available
- Observation date reasoning: not available
- Premium evidence status: MISSING
- Premium evidence source: not available
- Price window status: NOT_STARTED
- Price window notes: not available

## Missing Fields

- prior process signal review
- observation date candidate
- premium extraction
- price-window verification

## Recommended Next Action

Review background section and contemporaneous pre-announcement filings for public process signal.

## Source Evidence Rows

- `RHC-0017-ACQUIRED-JUNO-SRC-001`
  - type: 8K_MERGER
  - status: PARTIAL
  - filing: 8-K 2018-01-22
  - source: https://www.sec.gov/Archives/edgar/data/1594864/000119312518015255/d531432d8k.htm
  - supports: deal_announcement_date|acquirer|deal_terms|source_filing_url|source_filing_date|deal_price_per_share|outcome|corporate_outcome
  - excerpt: On January 21, 2018, Celgene Corporation entered into an Agreement and Plan of Merger with Juno Therapeutics, Inc. and Blue Magpie Corporation. Purchaser will commence a tender offer for all outstanding Juno Shares at a purchase price of $87.00 per Juno Share in cash.
- `RHC-0017-ACQUIRED-JUNO-SRC-002`
  - type: PROXY_SA_LANGUAGE
  - status: PARTIAL
  - filing: SC 14D9 2018-02-02
  - source: https://www.sec.gov/Archives/edgar/data/1594864/000119312518030824/d514862dsc14d9.htm
  - supports: proxy_or_tender_background|process_timeline|prior_process_signal_search
  - excerpt: Background of the Transaction. Juno and Celgene are parties to a number of agreements, including the Collaboration Agreement and the Voting and Standstill Agreement and certain other agreements as described more fully in Arrangements with Celgene and Purchaser and their Affiliates.

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=JUNO+%22Juno+Therapeutics%2C+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2018-01-01&enddt=2018-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=JUNO+%22Juno+Therapeutics%2C+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22premium%22&forms=DEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2018-01-01&enddt=2018-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=JUNO+%22Juno+Therapeutics%2C+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22prior+outreach%22+OR+%22competing+bids%22+OR+%22Item+4%22+OR+%22right+of+first+refusal%22+OR+%22right+of+first+negotiation%22&forms=8-K%2C10-Q%2C10-K%2CSC+13D%2CSC+13D%2FA%2CDEFM14A%2CDEF+14A&dateRange=custom&startdt=2015-01-01&enddt=2018-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
