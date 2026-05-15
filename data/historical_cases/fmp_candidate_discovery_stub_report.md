# FMP Candidate Discovery Stub Report

Generated: 2026-05-15

Status: read-only design stub. No historical classifications were changed.

## Run Summary

- Mode: OFFLINE_PLACEHOLDER
- Lookback years requested: 5
- FMP_API_KEY: MISSING
- Live API flag: DISABLED
- Candidate rows written: 0
- Live discovery note: FMP_API_KEY was not found; wrote placeholder outputs without live API calls.

## Local Coverage Loaded

| Local file | Rows loaded |
|---|---:|
| five_year_acquisition_universe_candidates.csv | 62 |
| resolved_case_candidates.csv | 203 |
| acquisition_announcement_dates.csv | 61 |

Unique tickers available for future coverage matching: 191

## Placeholder Result

This run does not pull FMP data by default. The candidate CSV is written with
the expected schema so future live discovery can append FMP-derived candidates
without mutating the five-year universe builder or any adjudication files.

If `FMP_API_KEY` is missing, this behavior is expected. If the key exists, the
script still avoids live calls unless `--enable-live-api` is passed.

## Intended Future Flow

1. Use FMP delisted/profile data to identify possible biotech or biopharma
   companies that disappeared during the lookback window.
2. Mark whether each ticker is already covered by the five-year universe,
   resolved candidate seeds, or announcement-date table.
3. Send new possible acquisitions into the five-year universe builder as
   review candidates.
4. Confirm every candidate with EDGAR, merger filings, tender-offer filings, or
   source-backed press releases before adding it to the acquisition denominator.

## Guardrails

- FMP is for discovery, ticker validation, delisting context, and market data.
- EDGAR/source evidence remains the source of truth for acquisition evidence.
- FMP must not classify prior process signals.
- FMP must not mark cases VERIFIED or CALIBRATION_ELIGIBLE.
- Missing FMP data should not fail the historical case factory.

## Risks

- Survivorship bias in active-company profile data.
- Stale ticker mappings after acquisitions, renamings, or delistings.
- Delisted biotech coverage gaps.
- Paid endpoint and rate-limit constraints.
- Historical market cap and price fields may need date-bound validation.
