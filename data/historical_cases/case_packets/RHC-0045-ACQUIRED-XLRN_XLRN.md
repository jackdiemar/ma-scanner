# Case Packet: XLRN - RHC-0045-ACQUIRED-XLRN

## Summary

- Company: Acceleron Pharma Inc.
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

- Adjudication status: ASSET_SPECIFIC_RIGHTS_ONLY
- Confirmation hit status: not available
- Case-level true signal: FALSE
- True prior-signal rows: 0
- False-positive rows: 1
- Classification counts: {"ASSET_SPECIFIC_RIGHTS_ONLY": 1}
- Best source URL: not available
- Best source excerpt: not available

### Adjudicated Rows

-  : ASSET_SPECIFIC_RIGHTS_ONLY (; )
  - notes: EDGAR research confirmed: BMS right of first negotiation publicly disclosed in XLRN 10-K (acc 0001280600-21-000017). However right is ASSET-SPECIFIC -- covers only Acceleron rights to develop/commercialize sotatercept in the pulmonary hypertension (PH) field. Not a company-level acquisition right. Merck acquirer (not BMS) paid $180/share. Asset-specific ROFN does not constitute whole-company process signal. Source: XLRN 10-K 2020 p.85542.

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

- `RHC-0045-ACQUIRED-XLRN-ADJ-001`
  - type: ADJUDICATION_NOTE
  - status: ADJUDICATED
  - filing: 10-K 2021-02-25
  - source: https://www.sec.gov/Archives/edgar/data/1280600/000128060021000017/xlrn-20201231.htm
  - supports: had_prior_process_signal
  - excerpt: We have the right to license, transfer or sell our rights to develop and commercialize sotatercept in the PH field, subject to BMS's right of first negotiation.

## Queue Queries

- Merger 8-K query: https://efts.sec.gov/LATEST/search-index?q=XLRN+%22Acceleron+Pharma+Inc.%22+%22agreement+and+plan+of+merger%22+%22per+share%22&forms=8-K%2CDEFM14A%2CDEF+14A%2CSC+TO-T%2CSC+TO-I&dateRange=custom&startdt=2021-01-01&enddt=2021-12-31
- Proxy query: https://efts.sec.gov/LATEST/search-index?q=XLRN+%22Acceleron+Pharma+Inc.%22+%22background+of+the+merger%22+OR+%22reasons+for+the+merger%22+OR+%22S-4%22&forms=DEFM14A%2CDEF+14A%2CS-4%2C424B3&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31
- Prior process signal query: https://efts.sec.gov/LATEST/search-index?q=XLRN+%22Acceleron+Pharma+Inc.%22+%22strategic+alternatives%22+OR+%22financial+advisor%22+OR+%22review+of+strategic+alternatives%22&forms=8-K%2C10-Q%2C10-K&dateRange=custom&startdt=2018-01-01&enddt=2021-12-31

## Guardrails

- Do not mark VERIFIED from this packet alone.
- Do not mark CALIBRATION_ELIGIBLE from this packet alone.
- Do not use this workflow score as investment quality or P(deal).
