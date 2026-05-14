# Case Packet: MDVN - RHC-0006-ACQUIRED-MDVN

## Summary

- Company: Medivation, Inc.
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
- Background heading: Background of Offer and Merger
- Proxy source URL: https://www.sec.gov/Archives/edgar/data/1011835/000119312516696911/d234696dsc14d9.htm
- Prior process signal status: REVIEWED
- Prior process signal: FOUND_PUBLIC
- Prior process signal type: outreach / competing bids
- Prior process signal date: 2016-04-28
- Observation date candidate: 2016-04-28
- Observation date reasoning: A public pre-announcement acquisition signal appears in the background section; use the first public signal date as observation_date_candidate pending contemporaneous source confirmation.
- Premium evidence status: MISSING
- Premium evidence source: not available
- Price window status: NOT_STARTED
- Price window notes: not available

## Prior Signal Adjudication

- Adjudication status: TRUE_PUBLIC_PRIOR_SIGNAL
- Confirmation hit status: CONFIRMED_HIT
- Case-level true signal: TRUE
- True prior-signal rows: 9
- False-positive rows: 0
- Classification counts: {"TRUE_PUBLIC_PRIOR_SIGNAL": 9}
- Best source URL: https://www.sec.gov/Archives/edgar/data/1011835/000119312516641659/0001193125-16-641659-index.htm
- Best source excerpt: rminate its consent solicitation. Before entering into the confidentiality agreement with Sanofi, Medivation received from Sanofi, and Medivation’s Board of Directors unanimously rejected as not in the best interests of the company and its stockholders, a new unsolicited proposal to acquire Medivation. The proposal, which was conditional upon the execution of a confidentiality agreement and the receipt of...

### Adjudicated Rows

- 2016-04-28 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal; proposal from|proposal to acquire)
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516563708/0001193125-16-563708-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2016-04-29 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal|unsolicited_proposal; proposal from|unsolicited proposal)
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516569536/0001193125-16-569536-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2016-05-05 10-Q: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal|unsolicited_proposal; proposal from|unsolicited proposal)
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000156459016018012/0001564590-16-018012-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2016-05-05 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal; proposal to acquire)
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516579914/0001193125-16-579914-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2016-05-06 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal|unsolicited_proposal; proposal to acquire|unsolicited proposal)
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516580827/0001193125-16-580827-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2016-05-25 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal; proposal to acquire)
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516602270/0001193125-16-602270-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2016-05-27 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (strategic_alternatives; strategic alternatives)
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516606426/0001193125-16-606426-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2016-06-13 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal; proposal to acquire)
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516620311/0001193125-16-620311-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2016-07-05 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal|unsolicited_proposal; proposal to acquire|unsolicited proposal)
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516641659/0001193125-16-641659-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.

## Missing Fields

- premium extraction
- price-window verification

## Recommended Next Action

Run price_window_fetcher.py or manual delisted-ticker price workflow after confirming premium extraction status.

## Source Evidence Rows

- `RHC-0006-ACQUIRED-MDVN-SRC-001`
  - type: 8K_MERGER
  - status: VERIFIED
  - filing: 8-K 2016-08-22
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516686961/d245915d8k.htm
  - supports: deal_announcement_date|acquirer|deal_terms|source_filing_url|source_filing_date|observation_date|signal_type|event_type|process_state_at_signal|signal_quality|deal_date|deal_price_per_share|outcome|corporate_outcome
  - excerpt: On August 20, 2016, Medivation, Inc. entered into an Agreement and Plan of Merger with Pfizer Inc. and Montreal, Inc.
- `RHC-0006-ACQUIRED-MDVN-SRC-002`
  - type: PROXY_SA_LANGUAGE
  - status: VERIFIED
  - filing: SC 14D9 2016-08-30
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516696911/d234696dsc14d9.htm
  - supports: proxy_or_tender_background|process_timeline|deal_terms
  - excerpt: The Offer is being made pursuant to an Agreement and Plan of Merger, dated as of August 20, 2016, by and among Parent, Purchaser, and Medivation.
- `RHC-0006-ACQUIRED-MDVN-SRC-003`
  - type: PROXY_SA_LANGUAGE
  - status: PARTIAL
  - filing: SC 14D9 2016-08-30
  - source: https://www.sec.gov/Archives/edgar/data/1011835/000119312516696911/d234696dsc14d9.htm
  - supports: had_prior_process_signal|notes|observation_date
  - excerpt: On April 28, 2016, Sanofi issued a press release publicly announcing Sanofi’s $52.50 proposal.

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=MDVN+%22Medivation%2C+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2016-01-01&enddt=2016-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=MDVN+%22Medivation%2C+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22premium%22&forms=DEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2016-01-01&enddt=2016-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=MDVN+%22Medivation%2C+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22prior+outreach%22+OR+%22competing+bids%22+OR+%22Item+4%22+OR+%22right+of+first+refusal%22+OR+%22right+of+first+negotiation%22&forms=8-K%2C10-Q%2C10-K%2CSC+13D%2CSC+13D%2FA%2CDEFM14A%2CDEF+14A&dateRange=custom&startdt=2015-01-01&enddt=2016-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
