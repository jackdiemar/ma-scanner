# Case Packet: CCXI - RHC-0049-ACQUIRED-CCXI

## Summary

- Company: ChemoCentryx, Inc.
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

- `RHC-0049-ACQUIRED-CCXI-ADJ-001`
  - type: ADJUDICATION_NOTE
  - status: ADJUDICATED
  - filing:
  - source:
  - supports: had_prior_process_signal
  - excerpt: No excerpt.

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=CCXI+%22ChemoCentryx%2C+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CDEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2022-01-01&enddt=2022-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=CCXI+%22ChemoCentryx%2C+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22S-4%22&forms=DEFM14A%2CDEF+14A%2CS-4%2C424B3&dateRange=custom&startdt=2019-01-01&enddt=2022-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=CCXI+%22ChemoCentryx%2C+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22review+of+strategic+alternatives%22&forms=8-K%2C10-Q%2C10-K&dateRange=custom&startdt=2019-01-01&enddt=2022-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
