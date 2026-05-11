# Current Priority

**As of:** 2026-05-11
**Phase:** Historical case library infrastructure complete. Active case verification in progress.

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

## Historical Case Library — Current State (2026-05-11)

**Commit:** `09e1f8a` pushed to `origin/runtime`

**10 priority cases — batch verification complete:**

| Ticker | Status | Key Finding |
|---|---|---|
| IMGO | **PARTIAL** | Acquirer=Merck confirmed. $36/share. 8-K 2022-11-21. No prior SA signal. |
| GNCA | **PARTIAL** | SA=2022-04-28 (seed said 2022-01-27, wrong). Wind-down=2022-05-24. No bankruptcy. |
| SRRA | **PARTIAL** | GSK merger 8-K confirmed 2022-04-12. Pre-deal signal not yet searched. |
| FLXN | **PARTIAL** | Pacira merger 8-K confirmed 2021-10-11. Pre-deal signal not yet searched. |
| PTGX | STUB | Janssen collab 8-K confirmed 2021-07-27. ROFR scope not extracted from exhibit. |
| HARP | STUB | **Major errors.** No standalone AbbVie ROFR 8-K found. Deal = program-level option on HPN217 from Nov 2019 (not 2020). signal_type and rofr_scope need reclassification. |
| MGTA | STUB | **Major errors.** SA=2023-02-02 (not 2022-06). Outcome=Dianthus reverse merger (not wind-down/bankruptcy). |
| DOVA | STUB | **Critical error.** Deal was 2019 (not 2021). case_id wrong — should be DOVA-2019-001. |
| RIGL | STUB | **Likely error.** Zero SC 13D filings in EDGAR 2018-2023. Activist case validity uncertain. |
| CRBP | STUB | Not yet checked. CIK=1595097. |

**Infrastructure built (Phase 2, commit `09e1f8a`):**
- `data/historical_cases/source_evidence_schema.json` — auditability layer
- `data/historical_cases/source_evidence.csv` — 31 rows (9 VERIFIED, 1 PARTIAL, 21 RESEARCH_TARGET)
- `src/historical_case_tools/edgar_evidence_finder.py` — EDGAR CIK/submissions/EFTS locator
- `src/historical_case_tools/exhibit_scope_extractor.py` — ROFR/ROFN scope classifier
- Schema updated: STUB status, CALIBRATION_ELIGIBLE gate, three-way outcome taxonomy (process_event_type / process_outcome / corporate_outcome)

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
- **Built Item 4 parser for SC 13Ds** (`src/item4_parser.py`). Classifies activist intent into 9 buckets (SALE_PROCESS, STRATEGIC_REVIEW, ACTIVIST_ESCALATION, BOARD_CHANGE, CAPITAL_ALLOCATION, GOVERNANCE_ONLY, GENERIC_SHAREHOLDER_PRESSURE, PASSIVE_ACCUMULATION, UNKNOWN). Integrated into Layer 7 scoring with intent-adjusted point weights and a gate that now blocks GOVERNANCE_ONLY, CAPITAL_ALLOCATION, and PASSIVE_ACCUMULATION 13Ds from clearing the process-evidence cap.
- **Built process-state transition tracking** (`src/process_history.py`). Persistent per-ticker state snapshots + transition events across scans. Detects: state upgrades/downgrades, SA/advisor/activist/ROFR introductions, activist intent escalation, intensity upgrades, staleness thresholds (45d/90d), signal withdrawals, score jumps. Stores to `data/tracking/state_history.json`. Adds `process_state` field to scanner output. Enables trajectory intelligence — system now remembers HOW situations change over time.
- **Built Process Sequence Detector** (`src/sequence_detector.py`). Reads transition events from state_history and detects 12 named compound patterns: ESCALATING_ACTIVIST, ADVISOR_THEN_SA, ACTIVIST_THEN_SA, SA_THEN_ACTIVIST, ROFR_THEN_ACTIVIST, ACTIVIST_THEN_ROFR, STALENESS_RESET, MERGER_PRECEDED_BY_SA, MERGER_PRECEDED_BY_ACTIVIST, RAPID_ESCALATION, COMPOUND_LIVE, PROCESS_COLLAPSE. Integrated into V12 main() after state_history save. New output fields: `detected_sequences`, `sequence_type`, `sequence_label`, `sequence_window_days`, `compound_signal_quality`. MVP: label only (no P(deal) adjustments until validated outcomes exist).

## Highest ROI Next Task

**Historical case verification — complete the PARTIAL cases and fix STUB errors.**

Priority order:
1. Pull prices for IMGO and GNCA (yfinance/Stooq) → promote to VERIFIED
2. Search SRRA and FLXN pre-deal 8-Ks → confirm or deny prior process signal
3. Fix HARP (reclassify signal_type; read DEF 14A background section)
4. Fix MGTA case_id (observation_date now 2023-02-02)
5. Fix DOVA case_id to DOVA-2019-001
6. Run exhibit_scope_extractor.py on PTGX Janssen collaboration exhibit
7. Check RIGL SC 13G filings and proxy DEF 14A for activist activity
8. Check CRBP 8-Ks 2022-2023 for SA language

After verification: ROFR/ROFN scope detection gap in the live scanner remains open. And sequence fields still not exposed on dashboard cards.

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
- Item 4 parsing: **built** (`src/item4_parser.py`). 9-bucket classification, intensity scoring, false-positive suppression.
- Process-state history: **built** (`src/process_history.py`). Transition tracking, escalation detection, state memory. Next scan will begin accumulating history.
- Process Sequence Detector: **built** (`src/sequence_detector.py`). 12 named compound patterns. Integrated into V12. Waiting on state_history data from real scans to surface results.
- ROFR/ROFN scope context: not built. Gap after case verification.
- Historical case library: **infrastructure built** (`source_evidence_schema.json`, `edgar_evidence_finder.py`, `exhibit_scope_extractor.py`). 4 cases PARTIAL (IMGO, GNCA, SRRA, FLXN). 6 STUB. 3 confirmed seed errors (MGTA outcome wrong, DOVA year wrong, RIGL 13D unconfirmed).
- Historical analog matching: groundwork laid. Not yet built.

## Biggest Remaining Uncertainty

Whether process-state detection in underfollowed small-cap biotech creates a tradable timing advantage after false positives, liquidity, spreads, and market reaction are accounted for.
