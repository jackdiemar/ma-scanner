# Agent Orientation

This repo is intentionally organized so an LLM can work without loading irrelevant files.

---

## Two-Repo Structure — Read This First

This project uses two local folders with separate purposes. Never mix them up.

| Repo | Path | Purpose |
|------|------|---------|
| **Runtime repo** | `/Users/jack/Downloads/ma-scanner` | All source code, scanner logic, data, archive. Scanner runs here. |
| **Deploy repo** | `/Users/jack/Documents/ma-scanner` | Cloudflare Pages site only. 11 files max. No source code lives here. |

**Deploy platform: Cloudflare Pages. NOT Netlify. Never Netlify.**

Deploy repo remote: `https://github.com/jackdiemar/bsc-dashboard.git`

Cloudflare Pages auto-deploys on every `git push origin main` from the deploy repo.

Deploy repo contains only:
- `index.html`, `dashboard.html`, `email_preview.html` — site pages
- `headshot.jpg`, `og.png`, `og.svg` — assets
- `netlify.toml` — redirect/header rules (CF Pages reads this)
- `scan_latest.json`, `scan_partial.json`, `outcomes.json`, `watchlist_tracking.json` — data files from V12 runs

---

## Source Of Truth

The only production scanner is:

- `src/PRODUCTION_SCANNER_V12.py` — run from `/Users/jack/Downloads/ma-scanner`
- wrapper: `scripts/run_scanner_v12.sh`

Treat V10/V11 code as obsolete. Do not modify archived scanners unless the user explicitly asks for legacy work.

If a scan request says "today", run V12 from `/Users/jack/Downloads/ma-scanner`, then verify `data/scans/scan_latest.json` has today's `scan_date`. A run that scores zero stocks usually means the FMP key was not loaded; fix the runtime environment rather than switching scanners.

Known local issue: V12 imports `backtest` at startup even when `--backtest` is not used. If that import is missing, resolve the startup import and keep using V12.

---

## Publishing Workflow

After a successful V12 run, copy only these 4 generated files into the deploy repo:

```bash
cp /Users/jack/Downloads/ma-scanner/data/scans/scan_latest.json /Users/jack/Documents/ma-scanner/scan_latest.json
cp /Users/jack/Downloads/ma-scanner/data/scans/scan_partial.json /Users/jack/Documents/ma-scanner/scan_partial.json
cp /Users/jack/Downloads/ma-scanner/data/tracking/watchlist_tracking.json /Users/jack/Documents/ma-scanner/watchlist_tracking.json
cp /Users/jack/Downloads/ma-scanner/data/tracking/outcomes.json /Users/jack/Documents/ma-scanner/outcomes.json
```

Then commit and push from `/Users/jack/Documents/ma-scanner`:

```bash
cd /Users/jack/Documents/ma-scanner
git add outcomes.json scan_latest.json scan_partial.json watchlist_tracking.json
git commit -m "Update scanner results for YYYY-MM-DD"
git push origin main
```

Cloudflare Pages handles the deploy after `git push origin main`. No other deploy step.

---

## Strategic Direction (as of 2026-05-09)

This system is Strategic Process Intelligence, not M&A prediction. It detects, classifies, and interprets SEC filing evidence of strategic processes in underfollowed small-cap biotech.

**Key field:** `signal_quality` — AFFIRM / PROCESS / ROFR / MERGER / BOILERPLATE / SCORE_ONLY
**Process states:** LIVE (AFFIRM/PROCESS) → PATHWAY (ROFR) → SIGNED (MERGER) → SCREENING / AGING
**Interpretation:** rule-based dashboard synthesis should explain process context, sequencing, freshness, and reinforcing signals. Do not add ML/LLM generation for this layer.

**Target universe:** $150M-$1.5B mcap. Outside this range, edge degrades.

**Item 4 parsing:** Built 2026-05-09. `src/item4_parser.py` classifies 13D activist intent into 9 buckets. Integrated into Layer 7 — governance/passive 13Ds no longer clear the process-evidence gate.

**Process Sequence Detector:** Built 2026-05-09. `src/sequence_detector.py` reads transition events from state_history and detects 12 named compound patterns (ESCALATING_ACTIVIST, ADVISOR_THEN_SA, COMPOUND_LIVE, RAPID_ESCALATION, MERGER_PRECEDED_BY_SA, etc.). Integrated into V12 main() after state_history save. New output fields: `sequence_type`, `sequence_label`, `sequence_window_days`, `compound_signal_quality`. MVP label-only — no P(deal) adjustments until outcomes validate.

Next gap: ROFR/ROFN scope context. See `CURRENT_PRIORITY.md`.

---

## Load Order For Coding Tasks

1. `CURRENT_PRIORITY.md` — what to focus on
2. `strategy_audit/EDGE_HYPOTHESIS.md` — strategic framing
3. `src/PRODUCTION_SCANNER_V12.py`
4. `src/item4_parser.py` — SC 13D Item 4 classification (read if touching activist/13D logic)
5. `src/process_history.py` — process-state transition tracking (read if touching history, escalation, or state fields)
5. `src/sequence_detector.py` — compound sequence pattern detection (read if touching sequence_type, compound_signal_quality, or multi-event logic)
5. `src/trade_logic.py`
6. `src/scanner_cache.py`
7. `src/outcome_tracker.py`
8. `src/send_alert_v12.py` — only if task touches email/reporting
9. `dashboards/dashboard_v12.html` and `src/secure_dashboard_server.py` — only if task touches the dashboard

---

## Ignore By Default

- `archive/` — obsolete scanners, diagnostics, one-off backtests, old mailers
- `data/legacy-scans/` — historical V10/V11 outputs
- `assets/` — media files
- `logs/` — runtime logs
- `data/cache/` — generated API cache

---

## Security Rules

- Never put API keys, SMTP passwords, dashboard passwords, tokens, or private credentials in frontend files.
- Use `secure_config.get_env()` for runtime secrets.
- Dashboard API calls that require FMP must go through `src/secure_dashboard_server.py`; browser code must not contain API key query parameters.

---

## Verification

Run these after code changes:

```bash
python3 -m py_compile src/*.py
bash -n scripts/*.sh
rg -n "([a]pikey=|SMTP_PASSWORD\s*=\s*['\"]|FMP_API_KEY\s*=\s*['\"])" src dashboards scripts config docs
```
