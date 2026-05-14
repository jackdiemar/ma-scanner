# Case Packet: TSRO - RHC-0025-ACQUIRED-TSRO

## Summary

- Company: TESARO, Inc.
- Likely outcome type: ACQUIRED
- Current status: CANDIDATE
- Recommended status: PARTIAL_READY
- Workflow completeness score: 40/100
- Score note: workflow completeness only. Not investment quality and not P(deal).
- Priority: HIGH

## Evidence Status

- Source evidence rows: 3
- Acquisition evidence status: SOURCE_BACKED
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
- Confirmation hit status: not available
- Case-level true signal: TRUE
- True prior-signal rows: 1
- False-positive rows: 0
- Classification counts: {"TRUE_PUBLIC_PRIOR_SIGNAL": 1}
- Best source URL: not available
- Best source excerpt: not available

### Adjudicated Rows

- 2018-11-16 NEWS: TRUE_PUBLIC_PRIOR_SIGNAL (public_review_process; explore potential sale)
  - source: https://www.sec.gov/Archives/edgar/data/1491576/000104746918007661/a2237269zsc14d9.htm
  - notes: Public signal was a pre-announcement news report, not private proxy-only negotiations. Further manual review should locate the original Bloomberg article or an archival copy.

## Missing Fields

- background section extraction
- prior process signal review
- observation date candidate
- premium extraction
- price-window verification

## Recommended Next Action

Run acquisition_background_extractor.py or manually capture proxy/Schedule 14D-9 background section.

## Source Evidence Rows

- `RHC-0025-ACQUIRED-TSRO-SRC-001`
  - type: 8K_MERGER
  - status: PARTIAL
  - filing: 8-K/A 2018-12-03
  - source: https://www.sec.gov/Archives/edgar/data/1491576/000110465918071114/a18-41016_18ka.htm
  - supports: deal_announcement_date|acquirer|deal_terms|source_filing_url|source_filing_date|deal_price_per_share|outcome|corporate_outcome
  - excerpt: On December 3, 2018, TESARO, Inc. entered into an Agreement and Plan of Merger with GlaxoSmithKline plc and Adriatic Acquisition Corporation at $75.00 per Share in cash.
- `RHC-0025-ACQUIRED-TSRO-SRC-002`
  - type: PROXY_SA_LANGUAGE
  - status: PARTIAL
  - filing: SC 14D9 2018-12-14
  - source: https://www.sec.gov/Archives/edgar/data/1491576/000104746918007661/a2237269zsc14d9.htm
  - supports: proxy_or_tender_background|process_timeline|prior_process_signal_search|had_prior_process_signal
  - excerpt: Background of the Offer. On November 16, 2018, Bloomberg News Wire published an article titled Cancer Drugmaker Tesaro is Said to Explore Potential Sale, before the December 3, 2018 acquisition announcement.
- `RHC-0025-ACQUIRED-TSRO-SRC-003`
  - type: PUBLIC_MEDIA_REPORT
  - status: PARTIAL
  - filing: NEWS 2018-11-16
  - source: https://www.cnbc.com/2018/11/16/cancer-drug-company-tesaro-shares-rise-30percent-following-report-that-it-will-explore-sale.html
  - supports: prior_process_signal_search|had_prior_process_signal|public_pre_announcement_signal
  - excerpt: Cancer drug company Tesaro shares rise following report that it will explore sale.

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=TSRO+%22TESARO%2C+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2019-01-01&enddt=2019-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=TSRO+%22TESARO%2C+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22premium%22&forms=DEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2019-01-01&enddt=2019-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=TSRO+%22TESARO%2C+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22prior+outreach%22+OR+%22competing+bids%22+OR+%22Item+4%22+OR+%22right+of+first+refusal%22+OR+%22right+of+first+negotiation%22&forms=8-K%2C10-Q%2C10-K%2CSC+13D%2CSC+13D%2FA%2CDEFM14A%2CDEF+14A&dateRange=custom&startdt=2016-01-01&enddt=2019-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
