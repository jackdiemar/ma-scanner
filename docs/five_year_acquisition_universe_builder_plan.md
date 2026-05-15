# Five-Year Acquisition Universe Builder Plan

Generated: 2026-05-15

## Purpose

Build a review-first acquisition universe for US-listed biotech, biopharma, and life sciences public-company acquisitions from the last five years. This is a candidate-generation layer, not final adjudication.

The goal is to move beyond manual small-batch extension while preserving the first 50-case evidence standard.

## Core Principle

EDGAR and source-backed public records remain the source of truth for:

- acquisition announcement dates
- merger/tender offer structure
- prior public process evidence
- source excerpts
- final classifications

FMP may later add market context, tradability, liquidity, ticker validation, and delisting status. FMP should not classify true process signals.

## Version 1 Scope

The first builder is intentionally offline and conservative. It uses only local files:

- `resolved_case_candidates.csv`
- `acquisition_announcement_dates.csv`
- `source_evidence.csv`

It outputs:

- `data/historical_cases/five_year_acquisition_universe_candidates.csv`
- `data/historical_cases/five_year_acquisition_universe_report.md`

It does not call FMP, scrape EDGAR, mutate source evidence, or change case classifications.

## Candidate Criteria

Include candidates when the local record suggests:

- standard public-company acquisition
- merger
- tender offer
- acquisition announcement within the last five calendar years
- US-listed target, or foreign issuer with EDGAR/6-K evidence available

Exclude or flag for review when the local record suggests:

- pure asset transaction
- license-only or collaboration-only transaction
- reverse merger or SPAC transaction
- bankruptcy, liquidation, or wind-down
- duplicate candidate
- source-blocked candidate

## Output Review Fields

The candidate CSV includes:

- identity fields: candidate ID, ticker, company, acquirer
- date fields: announcement date and year
- source fields: URL, source type, filing type, accession number
- deal-type guess
- inclusion status and reason
- exclusion reason
- confidence
- existing coverage flags for first 50 and Batch 51-70
- date/source confirmation needs
- FMP profile status placeholder
- notes

## Inclusion Classifier

The script classifies each row as one of:

- `INCLUDE_STANDARD_PUBLIC_COMPANY_ACQUISITION`
- `MAYBE_NEEDS_REVIEW`
- `EXCLUDE_ASSET_TRANSACTION`
- `EXCLUDE_LICENSE_ONLY`
- `EXCLUDE_REVERSE_MERGER_OR_SPAC`
- `EXCLUDE_BANKRUPTCY_OR_LIQUIDATION`
- `EXCLUDE_DUPLICATE`
- `SOURCE_BLOCKED`

Version 1 is text-pattern based and conservative. It is designed to triage the candidate universe, not prove deal status.

## Deduping

Version 1 dedupes on:

- ticker
- normalized company name
- likely outcome year
- announcement date
- inferred acquirer

Future versions should also use CIK, accession number, FMP delisting metadata, and finalized source evidence.

## Future External Hooks

Future candidate discovery should add:

- FMP delisted companies or symbol-change data
- FMP company profile validation
- EDGAR submissions by CIK
- SEC form searches for 8-K, SC TO-T, SC 14D-9, DEFM14A, and 6-K
- SEC-filed press release exhibits
- curated news checks for TSRO-type media-sourced process signals

These should be added as optional layers, with offline fallbacks.

## FMP Role Later

FMP should help with:

- identifying delisted biotech tickers
- validating ticker and company identity
- identifying possible acquisition or delisting dates
- filtering by sector and industry
- estimating market cap at announcement
- estimating market cap at signal date
- checking price and volume around filing dates
- identifying tradability and liquidity

FMP should not:

- decide whether a case is a true public prior signal
- replace EDGAR filing links, accession numbers, or excerpts
- mark cases `VERIFIED`
- mark cases `CALIBRATION_ELIGIBLE`
- override source-backed classifications

## Recommended Workflow

1. Run the five-year universe builder.
2. Review new likely eligible candidates not already in the first 50 or Batch 51-70.
3. Move eligible rows into the next date/source confirmation queue.
4. Confirm announcement dates from EDGAR or source-backed press releases.
5. Run pre-announcement filing collection.
6. Build the exception queue.
7. Adjudicate only high-priority exceptions.
8. Update batch distribution only after source-backed decisions.

## Can This Replace Manual Batch Selection?

Not yet. Version 1 can organize and prioritize the known local candidate universe. It cannot guarantee complete coverage of every US-listed biotech acquisition from the last five years until external discovery hooks are added.

It can reduce manual batch-selection friction now, and it defines the structure needed to replace manual selection later.
