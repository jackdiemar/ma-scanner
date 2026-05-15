# Case Packet: FLXN - RHC-0038-ACQUIRED-FLXN

## Summary

- Company: Flexion Therapeutics
- Likely outcome type: ACQUIRED
- Current status: CANDIDATE
- Recommended status: PARTIAL_READY
- Workflow completeness score: 40/100
- Score note: workflow completeness only. Not investment quality and not P(deal).
- Priority: HIGH

## Evidence Status

- Source evidence rows: 4
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

- background section extraction
- prior process signal review
- observation date candidate
- premium extraction
- price-window verification

## Recommended Next Action

Run acquisition_background_extractor.py or manually capture proxy/Schedule 14D-9 background section.

## Source Evidence Rows

- `FLXN-2021-001-SRC-001`
  - type: 8K_SA
  - status: VERIFY_REQUIRED
  - filing: 8-K
  - source: VERIFY_REQUIRED
  - supports: observation_date|signal_type|had_prior_process_signal
  - excerpt: Expected check: any SA or banker 8-K filed before Pacira merger announcement. If none — signal_type = MERGER_AGREEMENT.
- `FLXN-2021-001-SRC-002`
  - type: 8K_MERGER
  - status: VERIFIED
  - filing: 8-K 2021-10-12
  - source: https://www.sec.gov/Archives/edgar/data/1419600/000110465921124870/tm2129667d2_8k.htm
  - supports: deal_date|acquirer|outcome|source_filing_url|source_filing_date
  - excerpt: Flexion...entered into an Agreement and Plan of Merger with Pacira BioSciences Inc....and Oyster Acquisition Company Inc., a Delaware corporation and wholly owned subsidiary of Parent
- `FLXN-2021-001-SRC-003`
  - type: PRICE_DATA
  - status: VERIFY_REQUIRED
  - filing:
  - source: https://finance.yahoo.com/quote/FLXN/history/
  - supports: price_at_signal|price_30d_after|price_90d_after|price_180d_after
  - excerpt: price_at_signal on confirmed observation_date
- `RHC-0038-ACQUIRED-FLXN-ADJ-001`
  - type: ADJUDICATION_NOTE
  - status: ADJUDICATED
  - filing:
  - source:
  - supports: had_prior_process_signal
  - excerpt: No excerpt.

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=FLXN+%22Flexion+Therapeutics%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CDEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2021-01-01&enddt=2021-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=FLXN+%22Flexion+Therapeutics%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22S-4%22&forms=DEFM14A%2CDEF+14A%2CS-4%2C424B3&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=FLXN+%22Flexion+Therapeutics%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22review+of+strategic+alternatives%22&forms=8-K%2C10-Q%2C10-K&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
