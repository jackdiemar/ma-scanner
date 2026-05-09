# Codex Notes

Read `CLAUDE.md` first. It is the primary local workflow note for this folder.

Critical reminders:

- Production scanner: `src/PRODUCTION_SCANNER_V12.py`
- Normal wrapper: `scripts/run_scanner_v12.sh`
- Runtime working folder: `/Users/jack/Downloads/ma-scanner`
- Git-backed Netlify site folder: `/Users/jack/Documents/ma-scanner`
- Site remote: `https://github.com/jackdiemar/bsc-dashboard.git`
- Publish via Netlify by committing/pushing the generated JSON files in `/Users/jack/Documents/ma-scanner`
- Netlify is the only deploy target for this dashboard.
- Do not commit API keys, SMTP credentials, dashboard passwords, or local `.env` files.

When asked to run today's scanner and push to the site:

1. Run the V12 production scanner from `/Users/jack/Downloads/ma-scanner`.
2. Confirm `data/scans/scan_latest.json` has today's `scan_date`.
3. Copy `scan_latest.json`, `scan_partial.json`, `watchlist_tracking.json`, and `outcomes.json` into `/Users/jack/Documents/ma-scanner`.
4. Commit only those result files.
5. Push `main` to `origin`.
