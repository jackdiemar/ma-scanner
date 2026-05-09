# Claude Notes

Read this before working in this folder.

---

## Strategic Direction (as of 2026-05-09)

**This system is NOT an M&A prediction engine.** It is a Strategic Process Intelligence system: it detects, classifies, and interprets strategic-process evidence from SEC filings in underfollowed small-cap biotech names.

**Primary signal discriminator:** `signal_quality` field — AFFIRM / PROCESS / ROFR / MERGER / BOILERPLATE / SCORE_ONLY
**Process-state taxonomy:** LIVE (AFFIRM/PROCESS) / PATHWAY (ROFR) / SIGNED (MERGER) / SCREENING (SCORE_ONLY/BOILERPLATE) / AGING (stale)
**Interpretation layer:** dashboard cards synthesize process context from state, sequencing, freshness, activist pressure, advisor involvement, and transaction rights. It is rule-based only, not ML/LLM generation.

**Do not:** call the score "acquisition likelihood," claim broad M&A prediction, surface SCORE_ONLY names as primary opportunities, or treat any 13D as activist pressure without Item 4 context.

**Target universe:** $150M-$1.5B small-cap biotech. Above $1.5B = institutional coverage reduces edge. Below $150M = bankruptcy risk.

**Biggest open gap:** Item 4 parsing for 13Ds (distinguishes sale-pressure from governance). See `CURRENT_PRIORITY.md`.

**Moat direction:** running process-state infrastructure plus retrospective outcomes data, false-positive filtering, sequencing history, and proprietary interpretation workflows. Dashboard language should read like process interpretation and workflow compression, not signal dumping.

---

## Two-Repo Structure — Read This First

This project lives in **two separate local folders with different purposes**. Do not confuse them.

| Repo | Path | Purpose |
|------|------|---------|
| **Runtime repo** | `/Users/jack/Downloads/ma-scanner` | All source code, scanner logic, data history, archive. This is where V12 runs. |
| **Deploy repo** | `/Users/jack/Documents/ma-scanner` | Cloudflare Pages site only. 11 files: dashboard HTML + 4 data files + site assets. No source code. |

**Deploy platform: Cloudflare Pages. NOT Netlify. Never Netlify.**

Deploy repo remote: `https://github.com/jackdiemar/bsc-dashboard.git`

Cloudflare Pages auto-deploys on every push to `main` of that remote.

---

## Production Scanner

All scanner work happens from **`/Users/jack/Downloads/ma-scanner`** only.

The only production scanner is:

```bash
python3 src/PRODUCTION_SCANNER_V12.py
```

The wrapper is:

```bash
scripts/run_scanner_v12.sh
```

Do not run V10, V11, `DUAL_SCANNER.py`, `mreit_scanner.py`, or files under `archive/` unless the user explicitly asks for legacy analysis.

Required runtime secrets (environment variables):

- `FMP_API_KEY`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_RECIPIENT`

If `config/.env` is missing, the normal scanner can fail or produce a zero-result scan because FMP calls are unauthenticated. Fix the environment first; do not commit secrets.

Known local issue: `src/PRODUCTION_SCANNER_V12.py` imports `backtest` at startup even when not running `--backtest`. If `ModuleNotFoundError: No module named 'backtest'` appears, resolve the import before running the normal scan path. Do not switch to an older scanner.

---

## Output Contract

A successful V12 run writes these files inside **`/Users/jack/Downloads/ma-scanner`**:

- `data/scans/scan_v12_<timestamp>.json`
- `data/scans/scan_latest.json`
- `data/scans/scan_partial.json`
- `data/predictions/predictions_v12.csv`
- `data/tracking/watchlist_tracking.json`
- `data/tracking/outcomes.json`

Always verify `data/scans/scan_latest.json` has today's `scan_date` before publishing.

---

## Publishing to the Live Dashboard

**Step 1 — Copy 4 data files from runtime repo to deploy repo:**

```bash
cp /Users/jack/Downloads/ma-scanner/data/scans/scan_latest.json /Users/jack/Documents/ma-scanner/scan_latest.json
cp /Users/jack/Downloads/ma-scanner/data/scans/scan_partial.json /Users/jack/Documents/ma-scanner/scan_partial.json
cp /Users/jack/Downloads/ma-scanner/data/tracking/watchlist_tracking.json /Users/jack/Documents/ma-scanner/watchlist_tracking.json
cp /Users/jack/Downloads/ma-scanner/data/tracking/outcomes.json /Users/jack/Documents/ma-scanner/outcomes.json
```

**Step 2 — Commit and push from the deploy repo:**

```bash
cd /Users/jack/Documents/ma-scanner
git add outcomes.json scan_latest.json scan_partial.json watchlist_tracking.json
git commit -m "Update scanner results for YYYY-MM-DD"
git push origin main
```

Cloudflare Pages deploys automatically after the push. No manual deploy step needed.

**Deploy repo contains only these 11 files — nothing else should ever be added:**

- `index.html` — site landing page
- `dashboard.html` — main dashboard
- `email_preview.html` — email template preview
- `headshot.jpg`, `og.png`, `og.svg` — site assets
- `netlify.toml` — redirect/header config (Cloudflare Pages reads this for redirect rules)
- `scan_latest.json`, `scan_partial.json`, `outcomes.json`, `watchlist_tracking.json` — V12 data outputs

Do not add source code, scripts, archive files, or documentation to the deploy repo.
