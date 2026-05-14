# Case Packet: NPSP - RHC-0001-ACQUIRED-NPSP

## Summary

- Company: NPS Pharmaceuticals, Inc.
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
- Proxy source URL: https://www.sec.gov/Archives/edgar/data/890465/000104746915000380/a2222816zsc14d9.htm
- Prior process signal status: REVIEWED
- Prior process signal: NONE_FOUND
- Prior process signal type: none found
- Prior process signal date: not available
- Observation date candidate: 2015-01-12
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

- `RHC-0001-ACQUIRED-NPSP-SRC-001`
  - type: 8K_MERGER
  - status: VERIFIED
  - filing: 8-K 2015-01-12
  - source: https://www.sec.gov/Archives/edgar/data/890465/000110465915001685/a15-2148_18k.htm
  - supports: deal_announcement_date|acquirer|deal_terms|source_filing_url|source_filing_date|observation_date|signal_type|event_type|process_state_at_signal|signal_quality|deal_date|deal_price_per_share|outcome|corporate_outcome
  - excerpt: On January 11, 2015, NPS Pharmaceuticals, Inc. entered into an Agreement and Plan of Merger with Shire Pharmaceutical Holdings Ireland Limited and Knight Newco 2, Inc.
- `RHC-0001-ACQUIRED-NPSP-SRC-002`
  - type: PROXY_SA_LANGUAGE
  - status: VERIFIED
  - filing: SC 14D9 2015-01-23
  - source: https://www.sec.gov/Archives/edgar/data/890465/000104746915000380/a2222816zsc14d9.htm
  - supports: proxy_or_tender_background|deal_price_per_share|process_timeline
  - excerpt: The Offer is being made pursuant to the Agreement and Plan of Merger, dated as of January 11, 2015.
- `RHC-0001-ACQUIRED-NPSP-SRC-003`
  - type: PROXY_SA_LANGUAGE
  - status: PARTIAL
  - filing: SC 14D9 2015-01-23
  - source: https://www.sec.gov/Archives/edgar/data/890465/000104746915000380/a2222816zsc14d9.htm
  - supports: had_prior_process_signal|notes|observation_date
  - excerpt: October 9, 2014, an executive at a biopharmaceutical company (" Party A ") contacted Francois Nader, the Company's President and Chief Executive Officer, and indicated that Party A wished to explore a possible combination of Party A with the Company. No offer price or other terms of any such transaction were proposed by Party A. Dr. Nader indicated that he would discuss Party A's interest with the Board. Later that day, Dr. Nader informed Peter Tombros, Chairman of the Board, of this...

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=NPSP+%22NPS+Pharmaceuticals%2C+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2015-01-01&enddt=2015-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=NPSP+%22NPS+Pharmaceuticals%2C+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22premium%22&forms=DEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2015-01-01&enddt=2015-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=NPSP+%22NPS+Pharmaceuticals%2C+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22prior+outreach%22+OR+%22competing+bids%22+OR+%22Item+4%22+OR+%22right+of+first+refusal%22+OR+%22right+of+first+negotiation%22&forms=8-K%2C10-Q%2C10-K%2CSC+13D%2CSC+13D%2FA%2CDEFM14A%2CDEF+14A&dateRange=custom&startdt=2015-01-01&enddt=2015-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
