# Case Packet: TBRA - RHC-0008-ACQUIRED-TBRA

## Summary

- Company: Tobira Therapeutics, Inc.
- Likely outcome type: ACQUIRED
- Current status: CANDIDATE
- Recommended status: PARTIAL_READY
- Workflow completeness score: 80/100
- Score note: workflow completeness only. Not investment quality and not P(deal).
- Priority: HIGH

## Evidence Status

- Source evidence rows: 2
- Acquisition evidence status: SOURCE_BACKED
- Background section status: FOUND
- Background heading: Background of the Transaction
- Proxy source URL: https://www.sec.gov/Archives/edgar/data/1311596/000119312516729446/d264761dsc14d9.htm
- Prior process signal status: REVIEWED
- Prior process signal: NONE_FOUND
- Prior process signal type: none found
- Prior process signal date: not available
- Observation date candidate: 2016-09-20
- Observation date reasoning: No source-backed public pre-announcement process signal was found in the available background excerpt. Private negotiations disclosed after announcement are not used as observation dates, so default to the acquisition announcement date pending manual no-hit confirmation.
- Premium evidence status: MISSING
- Premium evidence source: not available
- Price window status: NOT_STARTED
- Price window notes: not available

## Missing Fields

- premium extraction
- price-window verification

## Recommended Next Action

Promote only after primary-source evidence supports the PARTIAL checklist.

## Source Evidence Rows

- `RHC-0008-ACQUIRED-TBRA-SRC-001`
  - type: 8K_MERGER
  - status: PARTIAL
  - filing: 8-K 2016-09-20
  - source: https://www.sec.gov/Archives/edgar/data/1311596/000119312516714192/d249853d8k.htm
  - supports: deal_announcement_date|acquirer|deal_terms|source_filing_url|source_filing_date|deal_price_per_share|outcome|corporate_outcome
  - excerpt: On September 19, 2016, Tobira Therapeutics, Inc. entered into an Agreement and Plan of Merger with Allergan Holdco US, Inc. and Sapphire Acquisition Corp. Purchaser will commence a tender offer to acquire all outstanding shares at a purchase price of $28.35 per Share in cash plus one contingent value right per Share.
- `RHC-0008-ACQUIRED-TBRA-SRC-002`
  - type: PROXY_SA_LANGUAGE
  - status: PARTIAL
  - filing: SC 14D9 2016-10-03
  - source: https://www.sec.gov/Archives/edgar/data/1311596/000119312516729446/d264761dsc14d9.htm
  - supports: proxy_or_tender_background|process_timeline|prior_process_signal_search
  - excerpt: Background of the Transaction. The Tobira Board regularly reviews and evaluates with the assistance of senior management potential collaborations and other strategic opportunities to advance the clinical development of CVC and other product candidates and preclinical programs, finance the Company clinical development efforts and enhance value for the Company stockholders.

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=TBRA+%22Tobira+Therapeutics%2C+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2016-01-01&enddt=2016-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=TBRA+%22Tobira+Therapeutics%2C+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22premium%22&forms=DEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2016-01-01&enddt=2016-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=TBRA+%22Tobira+Therapeutics%2C+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22prior+outreach%22+OR+%22competing+bids%22+OR+%22Item+4%22+OR+%22right+of+first+refusal%22+OR+%22right+of+first+negotiation%22&forms=8-K%2C10-Q%2C10-K%2CSC+13D%2CSC+13D%2FA%2CDEFM14A%2CDEF+14A&dateRange=custom&startdt=2015-01-01&enddt=2016-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
