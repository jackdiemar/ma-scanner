# FMP Candidate Discovery Stub

Status: design scaffold only. It does not make live FMP calls by default.

## Purpose

`src/historical_case_tools/fmp_candidate_discovery_stub.py` creates the first read-only scaffold for using FMP as a future acquisition candidate discovery layer.

FMP should help identify possible biotech acquisitions, validate ticker/company identity, surface delisting context, and add market context. It should not decide whether a deal belongs in the acquisition denominator, and it should not classify true prior process signals.

EDGAR filings, merger agreements, tender-offer filings, press releases, and source-backed evidence remain the source of truth.

## Basic Command

```bash
python3 src/historical_case_tools/fmp_candidate_discovery_stub.py --lookback-years 5
```

This command does not require `FMP_API_KEY`. If the key is missing, the script writes placeholder outputs and exits cleanly.

## Future Live Mode

```bash
FMP_API_KEY="your_key" python3 src/historical_case_tools/fmp_candidate_discovery_stub.py \
  --lookback-years 5 \
  --enable-live-api
```

The flag is intentionally explicit. Even with an API key, live calls are skipped unless `--enable-live-api` is present. The current live discovery function is still a placeholder, so the command is safe as a scaffold.

## Outputs

The script writes:

- `data/historical_cases/fmp_candidate_discovery_stub_candidates.csv`
- `data/historical_cases/fmp_candidate_discovery_stub_report.md`

The CSV uses the future FMP candidate schema:

- `ticker`
- `company`
- `fmp_exchange`
- `fmp_sector`
- `fmp_industry`
- `delisted_date`
- `ipo_date`
- `last_price_date`
- `possible_acquisition_flag`
- `possible_biotech_flag`
- `needs_edgar_confirmation`
- `existing_case_id_if_any`
- `already_in_universe`
- `notes`

## Local Coverage Matching

The stub reads these local files to prepare coverage matching:

- `data/historical_cases/five_year_acquisition_universe_candidates.csv`
- `data/historical_cases/resolved_case_candidates.csv`
- `data/historical_cases/acquisition_announcement_dates.csv`

Future FMP-derived candidates should be marked against this local coverage before entering the five-year universe workflow.

## Future FMP Sources

The likely endpoint categories to research later are:

- Delisted companies.
- Company profile.
- Sector and industry classification.
- Historical price or last trading date.
- Market cap history.
- Symbol changes, if available.

Exact endpoint names should be verified against current FMP documentation before implementation.

## Flow Into The Five-Year Builder

1. FMP identifies possible delisted or acquired biotech tickers.
2. The stub marks whether each ticker already exists in the five-year universe, resolved candidates, or announcement-date table.
3. New candidates flow into the five-year acquisition universe builder as review candidates.
4. EDGAR/source evidence confirms whether the company was actually acquired in a standard public-company merger, tender offer, or acquisition.
5. Only source-backed confirmed deals should enter the acquisition denominator.

## Guardrails

- Do not use FMP as source-truth classification evidence.
- Do not use FMP to mark `VERIFIED`.
- Do not use FMP to mark `CALIBRATION_ELIGIBLE`.
- Do not let FMP override EDGAR/source-backed dates.
- Do not mutate existing historical classifications from this stub.
- Treat FMP discovery as optional context. Missing FMP data should not block the historical case factory.

## Risks

- Survivorship bias from active-company endpoints.
- Stale tickers after acquisitions, renamings, or delistings.
- Delisted biotech coverage gaps.
- Paid endpoint limits and rate limits.
- Historical market cap and price data may need careful date-bound checks.
- FMP can identify candidates, but cannot prove a public-company acquisition by itself.
