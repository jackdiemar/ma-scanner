# Current Priority

**As of:** 2026-05-09
**Phase:** Strategic Process Intelligence repositioning complete. Backend false-positive reduction is now the priority.

## Current Strategic Direction

The scanner is not an M&A prediction engine. It is a strategic process intelligence system for underfollowed small-cap biotech. The system should detect, classify, and interpret process evidence from SEC filings, then compress that into a short analyst workflow.

The current edge thesis is narrow:

- process-state intelligence
- sequencing intelligence
- historical retrospective datasets
- false-positive filtering
- underfollowed small-cap process detection
- workflow compression
- proprietary rule-based interpretation

The score is not the moat. The moat, if it develops, will come from running infrastructure plus accumulated process-state history, outcome history, false-positive labels, and interpretation quality.

## What Was Completed Recently

- Repositioned system from broad M&A prediction to Strategic Process Intelligence.
- Deployed process-state taxonomy: LIVE / PATHWAY / SIGNED / SCREENING / AGING.
- Replaced conviction-tier display with process-state display.
- Demoted SCORE_ONLY names from primary signal.
- Added process-state rationale text under state labels.
- Added rule-based Process Interpretation layer on dashboard cards.
- Added lightweight Recent Change text when scan fields support it.
- Cleaned dashboard language to avoid "acquisition likelihood," "proprietary AI," and signal dumping.
- Confirmed deploy workflow: Cloudflare Pages, not Netlify.

## Highest ROI Next Task

**Item 4 parsing for 13Ds** in `src/PRODUCTION_SCANNER_V12.py`.

Goal: distinguish sale-pressure 13Ds from governance, ownership, or passive-control filings.

Why it matters: current PROCESS classification can overstate activist relevance because it treats 13D presence as pressure without enough intent context.

Initial classification targets:

- Sale pressure: "maximize shareholder value," "sale of the company," "business combination," "strategic alternatives," "formal process"
- Governance pressure: board representation, management change, capital allocation
- Non-sale context: ownership restructuring, financing, passive strategic holder

## Secondary Priority

**ROFR/ROFN scope context.**

Distinguish whole-company rights from single-asset, program-specific, or territory-specific rights. Current PATHWAY interpretation can overstate strategic relevance when scope is narrow.

## What Not To Work On Now

- More dashboard sections.
- ML or LLM prediction systems.
- Broad score tuning before Item 4 parsing.
- Compound scoring before cleaner process inputs.
- Large-cap acquisition screens.
- Outcome calibration as a final model input before enough resolved outcomes exist.

## Deployment And Paths

- Runtime repo: `/Users/jack/Downloads/ma-scanner`
- Deploy repo: `/Users/jack/Documents/ma-scanner`
- Production scanner: `src/PRODUCTION_SCANNER_V12.py`
- Runtime dashboard: `dashboards/dashboard_v12.html`
- Live dashboard file: `/Users/jack/Documents/ma-scanner/dashboard.html`
- Strategy audit: `strategy_audit/EDGE_HYPOTHESIS.md`
- Reports: `reports/`
- Legacy backtests: `archive/legacy-data/backtests`
- Deprecated backtest scripts: `archive/deprecated-code/`
- Latest scan: `data/scans/scan_latest.json`
- Partial scan: `data/scans/scan_partial.json`
- Watchlist tracking: `data/tracking/watchlist_tracking.json`
- Outcomes: `data/tracking/outcomes.json`
- Deploy remote: `https://github.com/jackdiemar/bsc-dashboard.git`
- Deploy platform: Cloudflare Pages only. Never Netlify.

## System Health

- V12 scanner: production source of truth.
- Dashboard: process-state and interpretation layer deployed.
- Outcome tracker: early-stage data, not yet enough for calibration.
- Process-state transition history: not fully persisted yet.
- Item 4 parsing: not built, biggest gap.

## Biggest Remaining Uncertainty

Whether process-state detection in underfollowed small-cap biotech creates a tradable timing advantage after false positives, liquidity, spreads, and market reaction are accounted for.
