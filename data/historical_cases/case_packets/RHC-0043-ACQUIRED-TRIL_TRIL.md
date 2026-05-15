# Case Packet: TRIL - RHC-0043-ACQUIRED-TRIL

## Summary

- Company: Trillium Therapeutics Inc.
- Likely outcome type: ACQUIRED
- Current status: CANDIDATE
- Recommended status: KEEP_CANDIDATE
- Workflow completeness score: 20/100
- Score note: workflow completeness only. Not investment quality and not P(deal).
- Priority: HIGH

## Evidence Status

- Source evidence rows: 1
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

- Adjudication status: PRIVATE_BACKGROUND_ONLY
- Confirmation hit status: not available
- Case-level true signal: FALSE
- True prior-signal rows: 0
- False-positive rows: 1
- Classification counts: {"PRIVATE_BACKGROUND_ONLY": 1}
- Best source URL: not available
- Best source excerpt: not available

### Adjudicated Rows

-  : PRIVATE_BACKGROUND_ONLY (; )
  - notes: EDGAR research confirmed: Pfizer $25M registered direct equity investment (Sept 8 2020 acc 0001062993-20-004396) publicly disclosed; Pfizer CSO joined SAB. No ROFR, no acquisition option, no strategic collaboration agreement with company-level rights -- plain financial investment. Acquisition process was entirely private. Source: TRIL 6-K acc 0001062993-20-004396.

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

- `RHC-0043-ACQUIRED-TRIL-ADJ-001`
  - type: ADJUDICATION_NOTE
  - status: ADJUDICATED
  - filing: 6-K 2020-09-09
  - source: https://www.sec.gov/Archives/edgar/data/1616212/000106299320004396/exhibit99-1.htm
  - supports: had_prior_process_signal
  - excerpt: TRILLIUM THERAPEUTICS ANNOUNCES $25 MILLION EQUITY INVESTMENT FROM PFIZER INC. Pfizer invests $25 million in Trillium common shares at $10.88 per share...The common shares were offered and sold to Pfizer Inc. in a registered direct offering conducted without an underwriter or placement agent.

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=TRIL+%22Trillium+Therapeutics+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CDEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2021-01-01&enddt=2021-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=TRIL+%22Trillium+Therapeutics+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22S-4%22&forms=DEFM14A%2CDEF+14A%2CS-4%2C424B3&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=TRIL+%22Trillium+Therapeutics+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22review+of+strategic+alternatives%22&forms=8-K%2C10-Q%2C10-K&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
