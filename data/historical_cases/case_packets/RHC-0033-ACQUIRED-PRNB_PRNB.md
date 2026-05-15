# Case Packet: PRNB - RHC-0033-ACQUIRED-PRNB

## Summary

- Company: Principia Biopharma Inc.
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
  - notes: EDGAR research confirmed: Sanofi License Agreement publicly disclosed but Co-Funding Option belongs to Principia (not Sanofi acquisition option). SC 14D-9 background confirms Sanofi CEO made private asset proposal May 29 2020 (~$1.5B for sotatercept assets); Principia board rejected it; full company acquisition process was entirely private. No public ROFR. Source: PRNB SC 14D-9 acc 0001193125-20-233615.

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

- `RHC-0033-ACQUIRED-PRNB-ADJ-001`
  - type: ADJUDICATION_NOTE
  - status: ADJUDICATED
  - filing: SC 14D-9 2020-08-28
  - source: https://www.sec.gov/Archives/edgar/data/1510487/000119312520233615/d161225dsc14d9.htm
  - supports: had_prior_process_signal
  - excerpt: Principia and Genzyme Corporation, a wholly owned subsidiary of Sanofi, are parties to the Sanofi License Agreement. Under the Sanofi License Agreement, Principia has the option, subject to the satisfaction of certain terms and conditions, to fund a portion of the Phase 3 development costs of PRN2246/SAR442168 in return for...either a profit and loss sharing arrangement...or an additional worldwide royalty

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=PRNB+%22Principia+Biopharma+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CDEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2020-01-01&enddt=2020-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=PRNB+%22Principia+Biopharma+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22S-4%22&forms=DEFM14A%2CDEF+14A%2CS-4%2C424B3&dateRange=custom&startdt=2017-01-01&enddt=2020-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=PRNB+%22Principia+Biopharma+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22review+of+strategic+alternatives%22&forms=8-K%2C10-Q%2C10-K&dateRange=custom&startdt=2017-01-01&enddt=2020-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
