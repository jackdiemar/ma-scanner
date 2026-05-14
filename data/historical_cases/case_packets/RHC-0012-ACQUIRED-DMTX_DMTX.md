# Case Packet: DMTX - RHC-0012-ACQUIRED-DMTX

## Summary

- Company: Dimension Therapeutics, Inc.
- Likely outcome type: ACQUIRED
- Current status: CANDIDATE
- Recommended status: NEEDS_MANUAL_RESEARCH
- Workflow completeness score: 5/100
- Score note: workflow completeness only. Not investment quality and not P(deal).
- Priority: HIGH

## Evidence Status

- Source evidence rows: 0
- Acquisition evidence status: NOT_STARTED
- Background section status: NOT_REVIEWED
- Background heading: not available
- Proxy source URL: not available
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

## Prior Signal Adjudication

- Adjudication status: TRUE_PUBLIC_PRIOR_SIGNAL
- Confirmation hit status: CONFIRMED_HIT
- Case-level true signal: TRUE
- True prior-signal rows: 4
- False-positive rows: 0
- Classification counts: {"TRUE_PUBLIC_PRIOR_SIGNAL": 4}
- Best source URL: https://www.sec.gov/Archives/edgar/data/1592288/000119312517300359/0001193125-17-300359-index.htm
- Best source excerpt: ersigned hereunto duly authorized. DIMENSION THERAPEUTICS, INC. By: /s/ Mary Thistle Name: Mary Thistle Title: Chief Operating Officer Dated: October 2, 2017 EX-99.1 2 d468762dex991.htm EX-99.1 EX-99.1 EXHIBIT 99.1 Dimension Board Determines that Ultragenyx’s Unsolicited Proposal to Acquire Dimension for $6.00 Per Share Constitutes a “Superior Proposal” REGENXBIO Waives Matching Rights CAMBRIDGE, MA – October 2...

### Adjudicated Rows

- 2017-08-25 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal|competing_bid|retained_advisor|rofr_rofn|unsolicited_proposal; acquisition proposal|financial advisor|right of first refusal|superior proposal|unsolicited proposal)
  - source: https://www.sec.gov/Archives/edgar/data/1592288/000119312517267472/0001193125-17-267472-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2017-09-18 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal|retained_advisor|unsolicited_proposal; financial advisor|proposal from|unsolicited proposal)
  - source: https://www.sec.gov/Archives/edgar/data/1592288/000119312517287461/0001193125-17-287461-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2017-09-19 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal|competing_bid|retained_advisor|unsolicited_proposal; financial advisor|proposal from|superior proposal|unsolicited proposal)
  - source: https://www.sec.gov/Archives/edgar/data/1592288/000119312517287894/0001193125-17-287894-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.
- 2017-10-02 8-K: TRUE_PUBLIC_PRIOR_SIGNAL (acquisition_proposal|competing_bid|unsolicited_proposal; proposal to acquire|superior proposal|unsolicited proposal)
  - source: https://www.sec.gov/Archives/edgar/data/1592288/000119312517300359/0001193125-17-300359-index.htm
  - notes: Source text contains public pre-announcement proposal/process language.

## Missing Fields

- core acquisition evidence
- source evidence rows
- background section extraction
- prior process signal review
- observation date candidate
- premium extraction
- price-window verification

## Recommended Next Action

Check EDGAR manually for tender-offer, 6-K, proxy, or foreign-issuer transaction filings before extracting fields.

## Source Evidence Rows

No source evidence rows found.

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=DMTX+%22Dimension+Therapeutics%2C+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2017-01-01&enddt=2017-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=DMTX+%22Dimension+Therapeutics%2C+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22premium%22&forms=DEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2017-01-01&enddt=2017-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=DMTX+%22Dimension+Therapeutics%2C+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22prior+outreach%22+OR+%22competing+bids%22+OR+%22Item+4%22+OR+%22right+of+first+refusal%22+OR+%22right+of+first+negotiation%22&forms=8-K%2C10-Q%2C10-K%2CSC+13D%2CSC+13D%2FA%2CDEFM14A%2CDEF+14A&dateRange=custom&startdt=2015-01-01&enddt=2017-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
