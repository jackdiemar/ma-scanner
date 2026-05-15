# FMP Integration Opportunities

Generated: 2026-05-15

Status: design note only. No API calls implemented.

## Executive Summary

FMP should strengthen market context, universe construction, tradability checks, and price-reaction analysis. It should not decide whether a filing is a true process signal.

The first 50-case study established the core evidence standard: process classifications must come from source-backed EDGAR filings or source-backed public media in TSRO-type cases. FMP belongs around that evidence layer, not inside the classification gate.

## System Separation

| Source | Best role | Should not do |
|---|---|---|
| EDGAR | Source evidence, process facts, filing text, excerpts, accession links | Market reaction or tradability by itself |
| FMP | Market context, universe construction, price reaction, liquidity, profile validation | Decide true-signal status |
| ClinicalTrials.gov | Catalyst context, pipeline phase, readout framing | Classify acquisition-process evidence |
| News | Media-sourced process signals, especially TSRO-style sale-process reports | Replace source review or filing links |

The product should stay framed as strategic-process intelligence and workflow compression. FMP can make the workflow more useful to investors, but EDGAR remains the evidence source of truth for process classifications.

## Best FMP Use Cases

| Use case | Value | Priority |
|---|---|---|
| Market cap at signal date | Confirms whether a historical case fit the intended live universe when the signal appeared | P0 |
| Historical price before and after signal | Measures whether the signal was visible to the market and whether the move was tradable | P0 |
| Volume spike around filing date | Helps identify whether a filing changed market attention | P0 |
| Current market cap and enterprise value | Keeps live universe current and avoids stale size buckets | P0 |
| Ticker/company profile validation | Reduces stale ticker, renamed company, and delisted-company confusion | P0 |
| 52-week low/high and priced-in filter | Helps avoid alerts where the signal may already be fully reflected | P1 |
| Float and liquidity filters | Prevents wasting time on names that are not institutionally tradable | P1 |
| Sector and industry classification | Keeps the universe biotech/healthcare-focused | P1 |
| Delisting or acquisition status confirmation | Helps historical cleanup, but should be cross-checked with EDGAR/source evidence | P1 |
| Institutional ownership | Useful only if coverage is reliable and time-stamped enough | P2 |
| Analyst estimate changes | Helpful market-context layer, but not core process evidence | P2 |
| M&A announcement date cross-check | Useful as a weak cross-check, not canonical evidence | P2 |

## Historical Case Factory Improvements

FMP can speed Batch 51-70 and later batches by adding context columns that do not mutate classifications.

High-value historical uses:

- Validate ticker identity before filing collection.
- Check whether a ticker was active during the acquisition year.
- Estimate market cap at announcement date and earliest signal date.
- Flag cases outside the current live universe cap, such as MDVN-like large-cap examples.
- Identify low-liquidity cases where a signal may not have been institutionally tradable.
- Prioritize cases where a public signal had a measurable price or volume response.
- Add market-context columns to exception queues without changing adjudication status.

The exception queue should still rank process evidence first. FMP fields should answer: "Is this worth an analyst's time after we know a source-backed signal exists?"

## Live Scanner Improvements

FMP is already present in `PRODUCTION_SCANNER_V12.py` for quote, profile, historical price, enterprise value, analyst estimates, SEC filing search, insider data, and technical indicators. The opportunity is to make those fields serve the process-evidence workflow more directly.

Best live improvements:

- Daily universe filtering by current market cap, sector, industry, price, and liquidity.
- Alert priority based on process evidence plus tradability context.
- Price and volume reaction checks after a filing lands.
- "Already priced in" checks using 52-week range and recent move.
- Signal freshness combined with market movement.
- Abnormal move detection after 8-K or 13D filing.
- Exclusion or demotion of names that are too illiquid for serious event-driven monitoring.
- Live monitoring log enrichment with market cap, price, volume, and reaction fields.

This should not become a score-first product again. The flow should be:

1. Source-backed process evidence fires.
2. FMP adds market context.
3. Analyst sees whether the alert is actionable, stale, already repriced, or not tradable.

## Fields To Add Later

Recommended future columns for exception queues, live logs, and reports:

- `market_cap_current`
- `market_cap_at_signal`
- `enterprise_value_current`
- `price_at_signal`
- `price_1d_after_signal`
- `price_5d_after_signal`
- `volume_at_signal`
- `avg_30d_volume`
- `signal_day_return`
- `five_day_return`
- `price_vs_52w_low`
- `liquidity_bucket`
- `universe_bucket`
- `priced_in_flag`
- `fmp_profile_checked`
- `fmp_price_checked`
- `fmp_market_cap_confidence`

Suggested buckets:

- `liquidity_bucket`: `INSTITUTIONAL`, `THIN`, `MICRO_LIQUIDITY`, `UNKNOWN`
- `universe_bucket`: `TARGET_UNIVERSE`, `BELOW_FLOOR`, `ABOVE_CAP`, `OUT_OF_SECTOR`, `UNKNOWN`
- `priced_in_flag`: `NOT_PRICED_IN`, `PARTLY_REPRICED`, `ALREADY_REPRICED`, `UNKNOWN`

## API Design, Not Implementation

Do not add live API calls to the historical factory yet. The smallest durable design is one wrapper plus one read-only enrichment script.

Potential modules:

- `src/utils/fmp_client.py`: shared wrapper for FMP calls, later refactoring the scanner's current embedded `FMPClient`.
- `src/historical_case_tools/fmp_context_builder.py`: read-only historical enrichment tool that takes an exception queue and writes a new context CSV.

Environment variable:

- `FMP_API_KEY`

Caching:

- Use `~/.ma_scanner_cache/fmp/` for historical-case and tooling cache.
- Cache by endpoint/category, ticker, date range, and normalized params.
- Do not mix API keys into cache keys.
- Cache profile/identity data longer than price data.

Rate limits and retries:

- Use a small global throttle.
- Retry transient network errors with short backoff.
- Record errors per row.
- Never fail the whole pipeline because FMP is unavailable.

Offline fallback:

- If FMP is unavailable, write blank market-context fields and set confidence to `MISSING`.
- Preserve the EDGAR queue and source-evidence workflow.
- Treat FMP enrichment as optional context, not a blocker.

## Endpoint Categories To Research Later

The production scanner already uses several FMP endpoint categories. For historical and live-monitoring design, research these categories before implementation:

- Company profile.
- Quote or current market data.
- Historical daily prices.
- Historical chart or full price history.
- Market capitalization history, if available.
- Enterprise value.
- Delisted companies or symbol changes, if available.
- SEC filings by symbol, as a convenience layer.
- Financial statements and key metrics, where useful for live universe construction.
- Institutional ownership, only if reliable enough and date-stamped.
- Analyst estimates, only as market context.

Do not make endpoint-specific design depend on exact names until the API docs and existing scanner methods are reconciled.

## Prioritization

### P0: Must-Have Before Live Selling

- Market cap current and at signal date.
- Price at signal date and 1-day/5-day post-signal returns.
- Volume at signal date and 30-day average volume.
- Company profile validation.
- Liquidity bucket.
- Universe bucket.
- Priced-in flag.
- Live monitoring log enrichment for accepted and rejected alerts.

These fields support the buyer's first diligence questions: was the name in universe, was it tradable, did the filing move the stock, and was the alert timely?

### P1: Useful For Internal Analyst Workflow

- Enterprise value current.
- 52-week high/low context.
- Delisting or acquisition status cross-check.
- Historical market cap around announcement.
- Exception queue enrichment.
- Alert priority modifiers based on process evidence plus market context.

### P2: Nice To Have Later

- Institutional ownership.
- Analyst estimate revisions.
- Deeper financial statement context.
- Broader M&A announcement cross-checks.
- Acquirer-side context.

## Risks And Caveats

- Survivorship bias: current profiles and quote availability may overrepresent surviving tickers.
- Stale ticker mappings: renamed, acquired, or delisted biotech tickers can break historical joins.
- Delisted biotech coverage gaps: the highest-value historical cases may have weaker market data.
- Historical market cap accuracy: share counts and split adjustments need careful handling.
- Rate limits and paid endpoint limits can make full-batch enrichment brittle.
- FMP data should not override EDGAR source evidence.
- FMP should not decide whether something is `TRUE_PUBLIC_PRIOR_SIGNAL`.
- Current market context can contaminate historical interpretation if not date-bound.
- Price reaction does not prove causality. It only helps triage and commercial interpretation.

## Recommended Next Implementation

The smallest next coding step is not a full FMP overhaul.

Build a read-only `src/historical_case_tools/fmp_context_builder.py` that:

1. Reads an exception queue CSV.
2. Looks up ticker/profile identity.
3. Pulls historical price and volume around announcement date or signal date where available.
4. Adds market cap, price, return, volume, liquidity, and universe-bucket fields.
5. Writes a new CSV, such as `data/historical_cases/batch_51_70_fmp_context.csv`.
6. Does not mutate source evidence, announcement dates, adjudication statuses, or batch results.
7. Marks all unavailable FMP fields as `MISSING` rather than failing the run.

This creates useful context for Batch 51-70 while preserving the current evidence standard.

## What Not To Use FMP For

- Do not use FMP to classify true process signals.
- Do not use FMP to mark `VERIFIED` or `CALIBRATION_ELIGIBLE`.
- Do not let FMP replace SEC filing links, accession numbers, or source excerpts.
- Do not use FMP estimates or price targets as acquisition-process evidence.
- Do not use current market cap as historical market cap.
- Do not block historical adjudication because FMP is unavailable.
