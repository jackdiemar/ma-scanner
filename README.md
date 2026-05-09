# M&A Scanner

Active production version: **V12 only**.

---

## Two-Repo Structure

| Repo | Path | Purpose |
|------|------|---------|
| **Runtime repo** | `/Users/jack/Downloads/ma-scanner` | All code, data, history. Scanner runs here. |
| **Deploy repo** | `/Users/jack/Documents/ma-scanner` | Cloudflare Pages site only. 11 files. No source code. |

**Deploy platform: Cloudflare Pages. NOT Netlify.**
Remote: `https://github.com/jackdiemar/bsc-dashboard.git`

---

## Quick Start

```bash
scripts/INSTALL.sh
scripts/run_scanner_v12.sh
```

Required private environment variables (stored in `config/.env`, never committed):

- `FMP_API_KEY`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_RECIPIENT`

Use `config/.env.example` as the template.

---

## Active Runtime Files

| File | Purpose |
|------|---------|
| `src/PRODUCTION_SCANNER_V12.py` | Production scanner — the only one |
| `src/trade_logic.py` | Trade recommendation logic |
| `src/scanner_cache.py` | Repo-local API cache |
| `src/outcome_tracker.py` | Outcome persistence/calibration tracking |
| `src/send_alert_v12.py` | V12 email report |
| `src/secure_dashboard_server.py` | Local dashboard/API proxy |
| `dashboards/dashboard_v12.html` | Active dashboard |

---

## Runtime Data (all in this repo)

- `data/scans/` — V12 scan JSON, including `scan_latest.json`
- `data/predictions/` — `predictions_v12.csv`
- `data/tracking/` — `watchlist_tracking.json` and `outcomes.json`
- `data/cache/` — API response cache
- `data/legacy-scans/` — V10/V11 outputs, retained for history only
- `logs/` — run logs

---

## Publishing to the Live Site

After a successful V12 run, copy 4 data files to the deploy repo and push:

```bash
cp data/scans/scan_latest.json /Users/jack/Documents/ma-scanner/scan_latest.json
cp data/scans/scan_partial.json /Users/jack/Documents/ma-scanner/scan_partial.json
cp data/tracking/watchlist_tracking.json /Users/jack/Documents/ma-scanner/watchlist_tracking.json
cp data/tracking/outcomes.json /Users/jack/Documents/ma-scanner/outcomes.json

cd /Users/jack/Documents/ma-scanner
git add outcomes.json scan_latest.json scan_partial.json watchlist_tracking.json
git commit -m "Update scanner results for YYYY-MM-DD"
git push origin main
```

Cloudflare Pages auto-deploys on push.

---

## For LLMs

Start with `AGENTS.md`, then `docs/LLM_CONTEXT.md`. Do not load `archive/`, `assets/`, or historical V10/V11 outputs unless the task explicitly asks for legacy analysis.
