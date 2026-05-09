# M&A Scanner Cleanup Report

Date: 2026-05-03
Workspace: `/Users/jack/Downloads/ma-scanner`

## Goal

Make the project easier to navigate, reduce root-directory clutter, separate active code from generated outputs, and keep deprecated experiments available without letting them obscure the current scanner workflow.

## Final Top-Level Structure

| Folder | Purpose |
| --- | --- |
| `src/` | Active Python scanner, alert, security, dashboard-server, and data-client code. |
| `dashboards/` | Dashboard HTML files and email preview UI. |
| `marketing/` | Shareable/product ad HTML assets. |
| `scripts/` | Shell runners, install script, and launchd plist. |
| `config/` | Safe config templates and non-secret config JSON. |
| `data/scans/` | Historical scan result JSON files. |
| `data/exports/` | Legacy exported scanner result JSON files. |
| `data/predictions/` | Prediction tracking CSV files. |
| `data/backtests/` | Backtest and analysis result JSON files. |
| `data/database/` | SQLite scanner cache/database files. |
| `assets/images/` | Image assets. |
| `assets/media/` | Video/media assets. |
| `docs/` | Documentation and dependency list. |
| `logs/` | Runtime logs. |
| `archive/deprecated-code/` | Older experiments, diagnostics, test scripts, and one-off mailers retained for reference. |
| `archive/generated-cache/` | Generated local cache/system files retained out of the working path. |
| `/Users/jack/Downloads/ma-scanner-research-materials/` | PitchBook/math/research PDFs and zip material moved out of this repo. |
| `reports/cleanup-2026-05-03/` | This rationale plus the exact move inventory. |

## Rationale

- Active runtime code was moved into `src/` so the root is no longer a mix of scripts, generated JSON, dashboards, logs, and media.
- Historical scanner outputs were consolidated into `data/` by type. This keeps runtime results inspectable without hiding them in code folders.
- Older diagnostics, backtests, alternate model attempts, and one-off email campaigns were moved to `archive/deprecated-code/`. They are not deleted because they may contain useful research history, but they no longer compete with the active V10.6/V11 path.
- PitchBook/math/research material was moved out to `/Users/jack/Downloads/ma-scanner-research-materials/` because it is large and not part of the scanner runtime.
- Generated Python cache files and `.DS_Store` were removed from the active tree. New cache/log output is ignored by `.gitignore`.
- Shell scripts and launchd config were updated to the new layout so the daily scanner points at `src/`, writes logs to `logs/`, and reads scans from `data/scans/`.
- Scanner output paths were updated: V10.6 writes scan JSON to `data/scans/` and predictions to `data/predictions/`; V11 writes scan JSON to `data/scans/` and prediction CSV to `data/predictions/`.
- The secure dashboard server now serves dashboard files from `dashboards/`, keeping Python/config/runtime files unavailable through the static file handler.

## Files Moved

Moved `126` top-level files/folders. See `move-inventory.csv` in this same folder for the full source-to-destination list.

## Current File Counts

- `root metadata files`: 1 files
- `archive`: 106 files
- `assets`: 3 files
- `config`: 2 files
- `dashboards`: 4 files
- `data`: 60 files
- `docs`: 3 files
- `logs`: 4 files
- `marketing`: 2 files
- `reports`: 2 files
- `scripts`: 8 files
- `src`: 14 files

## Functional Patches After Moving

- `src/PRODUCTION_SCANNER_V10_6.py`
- `src/PRODUCTION_SCANNER_V10_6_ENHANCED.py`
- `src/PRODUCTION_SCANNER_V11.py`
- `src/send_alert_v11.py`
- `src/secure_dashboard_server.py`
- `scripts/run_daily_scan.sh`
- `scripts/run_daily_scan_CRONPROOF.sh`
- `scripts/run_daily_scan_TRACKED (1).sh`
- `scripts/run_daily_scan_V10_6.sh`
- `scripts/run_scanner_v11.sh`
- `scripts/install_launchd.sh`
- `scripts/com.blackstarlightcapital.mascanner.plist`
- `scripts/INSTALL.sh`
- `config/config_personal.json`
- `.gitignore`

## Checks Run

- `python3 -m py_compile src/*.py`
- `bash -n scripts/run_daily_scan.sh scripts/run_daily_scan_CRONPROOF.sh scripts/run_daily_scan_V10_6.sh scripts/run_scanner_v11.sh scripts/install_launchd.sh scripts/INSTALL.sh`
- Frontend secret/key scan over `*.html`
- Known exposed credential scan across the repo

## Notes

The cleanup intentionally archived questionable/older files instead of permanently deleting them. That gives you a cleaner working project while preserving prior analysis and one-off scripts for later review.
