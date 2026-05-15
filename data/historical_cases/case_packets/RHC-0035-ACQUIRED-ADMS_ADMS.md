# Case Packet: ADMS - RHC-0035-ACQUIRED-ADMS

## Summary

- Company: Adamas Pharmaceuticals
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

- Adjudication status: DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE
- Confirmation hit status: not available
- Case-level true signal: FALSE
- True prior-signal rows: 0
- False-positive rows: 1
- Classification counts: {"DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE": 1}
- Best source URL: not available
- Best source excerpt: not available

### Adjudicated Rows

-  : DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE (; )
  - notes: EDGAR research confirmed: no public SA announcement. SC 14D-9 background confirms Supernus made unsolicited private offer Oct 14 2020 ($6.82/share, declined), second offer Nov 12 2020 ($7.25/share, declined), further offers through 2021 -- all private. No Lazard/banker public announcement. No SA review 8-K found. Source: ADMS SC 14D-9 acc 0001104659-21-129362.

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

- `RHC-0035-ACQUIRED-ADMS-ADJ-001`
  - type: ADJUDICATION_NOTE
  - status: ADJUDICATED
  - filing: SC 14D-9 2021-10-25
  - source: https://www.sec.gov/Archives/edgar/data/1328143/000110465921129362/tm2129361-8_sc14d9.htm
  - supports: had_prior_process_signal
  - excerpt: On October 14, 2020, Supernus submitted an unsolicited, non-binding indication of interest to acquire the Company for $6.82 per Share in cash...On November 2, 2020, Mr. McFarlane responded...declining the offer

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=ADMS+%22Adamas+Pharmaceuticals%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CDEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2021-01-01&enddt=2021-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=ADMS+%22Adamas+Pharmaceuticals%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22S-4%22&forms=DEFM14A%2CDEF+14A%2CS-4%2C424B3&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=ADMS+%22Adamas+Pharmaceuticals%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22review+of+strategic+alternatives%22&forms=8-K%2C10-Q%2C10-K&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
