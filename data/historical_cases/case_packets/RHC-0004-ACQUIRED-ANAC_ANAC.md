# Case Packet: ANAC - RHC-0004-ACQUIRED-ANAC

## Summary

- Company: Anacor Pharmaceuticals, Inc.
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
- Background heading: Background of the Proposed Transaction
- Proxy source URL: https://www.sec.gov/Archives/edgar/data/1411158/000119312516603880/d319707dsc14d9.htm
- Prior process signal status: REVIEWED
- Prior process signal: NONE_FOUND
- Prior process signal type: none found
- Prior process signal date: not available
- Observation date candidate: 2016-05-16
- Observation date reasoning: No public pre-announcement process signal was detected in the extracted background section. Private outreach, negotiations, diligence, and bid activity disclosed later are not public t=0 signals, so the acquisition announcement date remains the observation_date_candidate.
- Premium evidence status: MISSING
- Premium evidence source: not available
- Price window status: NOT_STARTED
- Price window notes: not available

## Prior Signal Adjudication

- Adjudication status: NOT_ADJUDICATED
- Confirmation hit status: not available
- Case-level true signal: FALSE
- True prior-signal rows: 0
- False-positive rows: 0
- Classification counts: {}
- Best source URL: not available
- Best source excerpt: not available

### Adjudicated Rows

- none

## Missing Fields

- premium extraction
- price-window verification

## Recommended Next Action

Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status.

## Source Evidence Rows

- `RHC-0004-ACQUIRED-ANAC-SRC-001`
  - type: 8K_MERGER
  - status: VERIFIED
  - filing: 8-K 2016-05-16
  - source: https://www.sec.gov/Archives/edgar/data/1411158/000095010316013361/dp65732_8k.htm
  - supports: deal_announcement_date|acquirer|deal_terms|source_filing_url|source_filing_date|observation_date|signal_type|event_type|process_state_at_signal|signal_quality|deal_date|deal_price_per_share|outcome|corporate_outcome
  - excerpt: On May 14, 2016, Anacor Pharmaceuticals, Inc. entered into an Agreement and Plan of Merger with Pfizer Inc. and Quattro Merger Sub Inc.
- `RHC-0004-ACQUIRED-ANAC-SRC-002`
  - type: PROXY_SA_LANGUAGE
  - status: VERIFIED
  - filing: SC 14D9 2016-05-26
  - source: https://www.sec.gov/Archives/edgar/data/1411158/000119312516603880/d319707dsc14d9.htm
  - supports: proxy_or_tender_background|process_timeline|deal_terms
  - excerpt: The Offer is being made pursuant to an Agreement and Plan of Merger, dated as of May 14, 2016, by and among the Company, Pfizer and the Offeror.
- `RHC-0004-ACQUIRED-ANAC-SRC-003`
  - type: PROXY_SA_LANGUAGE
  - status: PARTIAL
  - filing: SC 14D9 2016-05-26
  - source: https://www.sec.gov/Archives/edgar/data/1411158/000119312516603880/d319707dsc14d9.htm
  - supports: had_prior_process_signal|notes|observation_date
  - excerpt: August 10, 2015, Mr. Berns met with the Chief Executive Officer of Party A (the “ Party A CEO ”). At such meeting, the Party A CEO informed Mr. Berns that Party A was interested in conducting due diligence and exploring a potential acquisition of the Company. The Party A CEO further indicated that, subject to Party A’s review of limited, confidential due diligence information regarding the Company, Party A could be in a position to provide an indicative valuation range in the near term. That...

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=ANAC+%22Anacor+Pharmaceuticals%2C+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2016-01-01&enddt=2016-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=ANAC+%22Anacor+Pharmaceuticals%2C+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22premium%22&forms=DEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2016-01-01&enddt=2016-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=ANAC+%22Anacor+Pharmaceuticals%2C+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22prior+outreach%22+OR+%22competing+bids%22+OR+%22Item+4%22+OR+%22right+of+first+refusal%22+OR+%22right+of+first+negotiation%22&forms=8-K%2C10-Q%2C10-K%2CSC+13D%2CSC+13D%2FA%2CDEFM14A%2CDEF+14A&dateRange=custom&startdt=2015-01-01&enddt=2016-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
