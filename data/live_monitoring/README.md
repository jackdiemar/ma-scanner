# Live Monitoring — Practical Guide

Runs the Strategic Process Intelligence scanner on a recurring basis and writes structured alerts.

---

## Quick Start

```bash
# One-time run (calls V12, processes alerts, writes memo)
bash scripts/run_live_scanner_once.sh

# Dry-run (validates dirs, uses existing scan_latest.json, no V12 call)
python3 src/live_monitoring/live_scanner_runner.py --once --dry-run

# Check last-run state
python3 src/live_monitoring/live_scanner_runner.py --status

# Daemon mode (60-minute interval)
bash scripts/run_live_scanner_daemon.sh

# Daemon with custom interval
INTERVAL_MINUTES=30 bash scripts/run_live_scanner_daemon.sh
```

---

## Output Files

| File | Description |
|------|-------------|
| `latest_review_memo.md` | Human-readable weekly review — Top 10 INVESTIGATE/WATCH cases |
| `latest_alerts.json` | Current dedup state keyed by `alert_hash` |
| `live_alert_log.csv` | Append-only run history (one row per alert per run) |
| `live_scanner_state.json` | Last-run metadata (timestamp, counts, run mode) |
| `runs/run_<ts>.json` | Per-run snapshot with full alert list |
| `live_scanner_errors.log` | Error log (Python logging output) |
| `live_scanner_stdout.log` | Shell script stdout/stderr when run via shell wrappers |

---

## Deduplication

Each alert gets a stable 16-char hex ID: `SHA256(ticker|signal_quality|source_accession)[:16]`

Status rules (set each run):

| Status | Meaning |
|--------|---------|
| `NEW` | Hash not seen before |
| `UPDATED` | Signal quality changed since last seen |
| `WATCHLIST` | Manually marked; preserved across runs |
| `SEEN` | Same hash and quality as before |

The `live_alert_log.csv` is append-only. Every run adds a row for each alert. Do not delete rows.

---

## Signal Quality Taxonomy

| Value | Meaning | Default Action |
|-------|---------|----------------|
| `AFFIRM` | Strategic alternatives affirmed in filing | INVESTIGATE |
| `MERGER` | Signed merger agreement | INVESTIGATE |
| `PROCESS` | Banker retained or activist 13D | INVESTIGATE / WATCH |
| `ROFR` | Right of first refusal / ROFN | WATCH |
| `BOILERPLATE` | S-8 / equity plan language | DISCARD |
| `SCORE_ONLY` | Score signal only, no process evidence | DISCARD (not logged) |

---

## False-Positive Filter

14 patterns from 3-batch historical adjudication study (86 cases, 3.5% true signal rate).

Conservative design: ambiguous cases → WATCH (not DISCARD).

Patterns: S-8 boilerplate, offering disclaimer, anti-takeover provision, director biography, performance condition award, partner equity divestiture, wrong-direction acquisition, ROFR warranty negative, binary artifact, asset-specific ROFN/ROFR scope.

---

## Stopping the Daemon

```bash
# If running in foreground: Ctrl+C

# If running in background:
kill $(cat live_scanner.lock)

# Lock file cleans up on graceful exit. If stale:
rm live_scanner.lock
```

---

## launchd (Mac — run at login)

```bash
# Generate plist (does NOT install)
bash scripts/install_live_scanner_launchd.sh

# Then install manually:
cp /tmp/com.blackstarlightcapital.livescanner.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.blackstarlightcapital.livescanner.plist

# Verify:
launchctl list | grep livescanner

# Uninstall:
launchctl unload ~/Library/LaunchAgents/com.blackstarlightcapital.livescanner.plist
rm ~/Library/LaunchAgents/com.blackstarlightcapital.livescanner.plist
```

---

## Safety Constraints

- No trade execution. No broker API connections.
- `INVESTIGATE` / `WATCH` / `DISCARD` are process-signal classifications only — not investment advice.
- Historical files (`source_evidence.csv`, `acquisition_announcement_dates.csv`) are never modified.
- V12 scanner behavior is unchanged — runner calls it via subprocess.
