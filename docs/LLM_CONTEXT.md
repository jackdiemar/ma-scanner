# LLM Context Map

## What This Project Does

M&A Scanner V12 scores biotech/pharma companies for acquisition likelihood. Pulls market and company data, applies V12 scoring/gating logic, persists watchlist/outcome tracking, writes scan outputs, and generates an email report and public dashboard.

---

## Two-Repo Structure

This project uses two local folders. They serve different purposes and must never be confused.

### Runtime Repo — all code lives here
```
/Users/jack/Downloads/ma-scanner
```
- All source code, scanner logic, data history, archive
- This is where V12 runs
- This is the working directory for all coding tasks

### Deploy Repo — Cloudflare Pages site only
```
/Users/jack/Documents/ma-scanner
```
- Remote: `https://github.com/jackdiemar/bsc-dashboard.git`
- Contains only 11 files: dashboard HTML pages, site assets, and 4 data JSON files
- **No source code ever goes here**
- Cloudflare Pages auto-deploys on every push to `main`

**Deploy platform is Cloudflare Pages. NOT Netlify. Not ever Netlify.**

---

## Active Entrypoints

| Task | File/Command |
|------|-------------|
| Run production scan + email | `scripts/run_scanner_v12.sh` |
| Run scanner directly | `python3 src/PRODUCTION_SCANNER_V12.py` |
| Email latest V12 scan | `python3 src/send_alert_v12.py` |
| Dashboard server | `python3 src/secure_dashboard_server.py` |
| Generate dashboard password hash | `python3 src/hash_dashboard_password.py` |

All commands run from `/Users/jack/Downloads/ma-scanner`.

---

## Active Code Map

| File | Purpose |
|------|---------|
| `src/PRODUCTION_SCANNER_V12.py` | Main scoring engine, thresholds, universe, scan persistence |
| `src/trade_logic.py` | Builds position/trade recommendation layer from scanner results |
| `src/scanner_cache.py` | File cache for expensive API/filing requests |
| `src/outcome_tracker.py` | Tracks HIGH/MEDIUM picks and resolved outcomes |
| `src/send_alert_v12.py` | Builds and sends email report from latest V12 scan |
| `src/secure_config.py` | Environment-variable helper for secrets |
| `src/secure_dashboard_server.py` | Serves `dashboards/dashboard_v12.html` and proxies private FMP requests |

---

## Data Map (Runtime Repo)

| Folder | Contents |
|--------|---------|
| `data/scans/` | Current V12 scan JSON files: `scan_latest.json`, `scan_partial.json`, timestamped archives |
| `data/predictions/` | Active V12 prediction CSV: `predictions_v12.csv` |
| `data/tracking/` | Persistent watchlist and outcome tracking |
| `data/legacy-scans/` | V10/V11 outputs — do not load unless asked |
| `archive/legacy-data/` | Historical exports, backtests, old SQLite database — do not load unless asked |

---

## V12 Output Contract

`src/PRODUCTION_SCANNER_V12.py` writes to `/Users/jack/Downloads/ma-scanner`:

- `data/scans/scan_v12_<timestamp>.json`
- `data/scans/scan_latest.json`
- `data/scans/scan_partial.json` — written during interrupted/partial runs
- `data/predictions/predictions_v12.csv`
- `data/tracking/watchlist_tracking.json`
- `data/tracking/outcomes.json`

Always verify `data/scans/scan_latest.json` has today's `scan_date` before publishing.

---

## Publishing Workflow

After a successful V12 run, copy 4 files to the deploy repo and push:

```bash
cp /Users/jack/Downloads/ma-scanner/data/scans/scan_latest.json /Users/jack/Documents/ma-scanner/scan_latest.json
cp /Users/jack/Downloads/ma-scanner/data/scans/scan_partial.json /Users/jack/Documents/ma-scanner/scan_partial.json
cp /Users/jack/Downloads/ma-scanner/data/tracking/watchlist_tracking.json /Users/jack/Documents/ma-scanner/watchlist_tracking.json
cp /Users/jack/Downloads/ma-scanner/data/tracking/outcomes.json /Users/jack/Documents/ma-scanner/outcomes.json

cd /Users/jack/Documents/ma-scanner
git add outcomes.json scan_latest.json scan_partial.json watchlist_tracking.json
git commit -m "Update scanner results for YYYY-MM-DD"
git push origin main
```

Cloudflare Pages deploys automatically. No manual deploy step.

---

## Environment

Private values must come from process environment (stored in `config/.env`, never committed):

- `FMP_API_KEY`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_RECIPIENT`
- `BSC_DASHBOARD_USERS` — if dashboard auth is used

Template: `config/.env.example`

---

## What Not To Load Unless Asked

- `archive/legacy-scanners/`
- `archive/legacy-alerts/`
- `archive/deprecated-code/`
- `data/legacy-scans/`
- `assets/media/`

V12 supersedes all of the above.
