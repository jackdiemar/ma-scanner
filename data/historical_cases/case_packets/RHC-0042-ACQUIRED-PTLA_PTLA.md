# Case Packet: PTLA - RHC-0042-ACQUIRED-PTLA

## Summary

- Company: Portola Pharmaceuticals
- Likely outcome type: ACQUIRED
- Current status: CANDIDATE
- Recommended status: KEEP_CANDIDATE
- Workflow completeness score: 20/100
- Score note: workflow completeness only. Not investment quality and not P(deal).
- Priority: HIGH

## Evidence Status

- Source evidence rows: 2
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

- core acquisition evidence
- background section extraction
- prior process signal review
- observation date candidate
- premium extraction
- price-window verification

## Recommended Next Action

Open primary acquisition evidence, then run date and pre-announcement signal workflows.

## Source Evidence Rows

- `RHC-0042-ACQUIRED-PTLA-SRC-001`
  - type: 8K_MERGER
  - status: SOURCE_BACKED
  - filing: 8-K 2020-05-05
  - source: https://www.sec.gov/Archives/edgar/data/899866/000110465920056508/tm2018594d2_ex99-1.htm
  - supports: deal_announcement_date|source_filing_type|source_filing_date|source_filing_url|deal_price_per_share|acquirer|outcome
  - excerpt: entered into a definitive merger agreement for Alexion to acquire Portola
- `RHC-0042-ACQUIRED-PTLA-ADJ-001`
  - type: PROXY_SA_LANGUAGE
  - status: ADJUDICATED
  - filing: SC 14D-9 2020-05-27
  - source: https://www.sec.gov/Archives/edgar/data/1269021/000104746920003216/a2241700zsc14d9.htm
  - supports: proxy_or_tender_background|process_timeline
  - excerpt: On May 5 2020 Alexion and Portola announced the entry into the Merger Agreement

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=PTLA+%22Portola+Pharmaceuticals%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CDEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2021-01-01&enddt=2021-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=PTLA+%22Portola+Pharmaceuticals%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22S-4%22&forms=DEFM14A%2CDEF+14A%2CS-4%2C424B3&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=PTLA+%22Portola+Pharmaceuticals%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22review+of+strategic+alternatives%22&forms=8-K%2C10-Q%2C10-K&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
