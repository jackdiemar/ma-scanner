# Case Packet: ZSPH - RHC-0003-ACQUIRED-ZSPH

## Summary

- Company: ZS Pharma, Inc.
- Likely outcome type: ACQUIRED
- Current status: PARTIAL
- Recommended status: PARTIAL
- Workflow completeness score: 80/100
- Score note: workflow completeness only. Not investment quality and not P(deal).
- Priority: HIGH

## Evidence Status

- Source evidence rows: 3
- Acquisition evidence status: SOURCE_BACKED
- Background section status: FOUND
- Background heading: Background of the Offer
- Proxy source URL: https://www.sec.gov/Archives/edgar/data/1459266/000119312515380466/d28720dsc14d9.htm
- Prior process signal status: REVIEWED
- Prior process signal: NONE_FOUND
- Prior process signal type: none found
- Prior process signal date: not available
- Observation date candidate: 2015-11-06
- Observation date reasoning: No public pre-announcement process signal was detected in the extracted background section. Private outreach, negotiations, diligence, and bid activity disclosed later are not public t=0 signals, so the acquisition announcement date remains the observation_date_candidate.
- Premium evidence status: MISSING
- Premium evidence source: not available
- Price window status: NOT_STARTED
- Price window notes: not available

## Missing Fields

- premium extraction
- price-window verification

## Recommended Next Action

Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status.

## Source Evidence Rows

- `RHC-0003-ACQUIRED-ZSPH-SRC-001`
  - type: 8K_MERGER
  - status: VERIFIED
  - filing: 8-K 2015-11-06
  - source: https://www.sec.gov/Archives/edgar/data/1459266/000119312515369081/d73329d8k.htm
  - supports: deal_announcement_date|acquirer|deal_price_per_share|deal_terms|source_filing_url|source_filing_date|observation_date|signal_type|event_type|process_state_at_signal|signal_quality|deal_date|outcome|corporate_outcome
  - excerpt: Merger Sub will commence an offer to purchase all outstanding shares of Company common stock at a purchase price of $90.00 per share in cash.
- `RHC-0003-ACQUIRED-ZSPH-SRC-002`
  - type: PROXY_SA_LANGUAGE
  - status: VERIFIED
  - filing: SC 14D9 2015-11-18
  - source: https://www.sec.gov/Archives/edgar/data/1459266/000119312515380466/d28720dsc14d9.htm
  - supports: proxy_or_tender_background|acquirer|process_timeline
  - excerpt: Parent and Purchaser are each indirect subsidiaries of AstraZeneca PLC.
- `RHC-0003-ACQUIRED-ZSPH-SRC-003`
  - type: PROXY_SA_LANGUAGE
  - status: PARTIAL
  - filing: SC 14D9 2015-11-18
  - source: https://www.sec.gov/Archives/edgar/data/1459266/000119312515380466/d28720dsc14d9.htm
  - supports: had_prior_process_signal|notes|observation_date
  - excerpt: July 29, 2015, the Company announced that its NDA had been accepted for filing by the FDA and that the Prescription Drug User Fee Act (“ PDUFA ”) goal date for a decision by the FDA is May 26, 2016. During the summer of 2015, Dr. Alexander was contacted by an investment banker who suggested that a publicly traded pharmaceutical company referred to in this Schedule 14D-9 as “ Party A ” was potentially interested in engaging in a strategic transaction with the Company. At that time, the Company...

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=ZSPH+%22ZS+Pharma%2C+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2015-01-01&enddt=2015-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=ZSPH+%22ZS+Pharma%2C+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22premium%22&forms=DEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2015-01-01&enddt=2015-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=ZSPH+%22ZS+Pharma%2C+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22prior+outreach%22+OR+%22competing+bids%22+OR+%22Item+4%22+OR+%22right+of+first+refusal%22+OR+%22right+of+first+negotiation%22&forms=8-K%2C10-Q%2C10-K%2CSC+13D%2CSC+13D%2FA%2CDEFM14A%2CDEF+14A&dateRange=custom&startdt=2015-01-01&enddt=2015-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
