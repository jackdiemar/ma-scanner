# LLM Readiness Report

Date: 2026-05-03

## Production Decision

The user clarified that **PRODUCTION_SCANNER_V12.py is the only production scanner**. V10/V11 scanner files are now legacy-only and should not be loaded or modified during normal work.

## Active Source Files

- `src/PRODUCTION_SCANNER_V12.py`
- `src/hash_dashboard_password.py`
- `src/outcome_tracker.py`
- `src/scanner_cache.py`
- `src/secure_config.py`
- `src/secure_dashboard_server.py`
- `src/send_alert_v12.py`
- `src/trade_logic.py`

## Legacy Scanner Files

- `archive/legacy-scanners/PRODUCTION_SCANNER_V10_6.py`
- `archive/legacy-scanners/PRODUCTION_SCANNER_V10_6_ENHANCED.py`
- `archive/legacy-scanners/PRODUCTION_SCANNER_V11.py`

## LLM Onboarding Files Added

- `README.md`
- `AGENTS.md`
- `docs/LLM_CONTEXT.md`
- `.vscode/extensions.json`

## Runtime Entrypoints

- Production run: `scripts/run_scanner_v12.sh`
- Install dependencies: `scripts/INSTALL.sh`
- Dashboard server: `python3 src/secure_dashboard_server.py`
- Dashboard: `dashboards/dashboard_v12.html`

## Data Locations

- Current V12 scans: `data/scans/`
- Current V12 prediction CSV: `data/predictions/predictions_v12.csv`
- Persistent tracking: `data/tracking/`
- V10/V11 historical scans: `data/legacy-scans/`
- Historical exports/backtests/database: `archive/legacy-data/`

## Cleanup Notes

- V12 was copied in from `/Users/jack/Documents/ma-scanner/PRODUCTION_SCANNER_V12.py`.
- Required V12 dependencies were copied into `src/`: `trade_logic.py`, `scanner_cache.py`, `outcome_tracker.py`.
- V12 output paths were patched to use repo-local `data/` folders.
- V12 secrets were patched to use `secure_config.get_env()`.
- Dashboard FMP calls were routed through `src/secure_dashboard_server.py`; no FMP API key remains in active frontend files.
- Research materials were moved out of the repo to `/Users/jack/Downloads/ma-scanner-research-materials/`.
- Old dashboards, scripts, V10/V11 scanners, and non-V12 datasets were moved under `archive/` or `data/legacy-scans/`.

## Current Top-Level File Counts

- `.Rhistory`: 1 files
- `.gitignore`: 1 files
- `.vscode`: 1 files
- `AGENTS.md`: 1 files
- `README.md`: 1 files
- `archive`: 63 files
- `assets`: 3 files
- `config`: 3 files
- `dashboards`: 2 files
- `data`: 59 files
- `docs`: 9 files
- `logs`: 4 files
- `marketing`: 2 files
- `reports`: 3 files
- `scripts`: 4 files
- `src`: 8 files
