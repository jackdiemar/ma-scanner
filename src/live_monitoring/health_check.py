"""
health_check.py — Quick VPS health check for the live scanner.

Exits 0 if healthy, 1 if any critical check fails.
Prints a one-line status per check — intended for cron/systemd output and
the check_server_status.sh wrapper.

Checks:
  - State file exists and last_run is present
  - Alert log exists and has rows
  - Latest review memo exists
  - Required env vars are present (FMP_API_KEY minimum)
  - Scan result file exists and is not stale (>25h old = warn, not fail)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE    = Path(__file__).resolve().parent
_SRCDIR  = _HERE.parent
REPO     = _SRCDIR.parent

STATE_PATH   = REPO / 'data' / 'live_monitoring' / 'live_scanner_state.json'
ALERT_LOG    = REPO / 'data' / 'live_monitoring' / 'live_alert_log.csv'
MEMO_PATH    = REPO / 'data' / 'live_monitoring' / 'latest_review_memo.md'
SCAN_LATEST  = REPO / 'data' / 'scans' / 'scan_latest.json'
ENV_FILE     = REPO / 'config' / '.env'
ERROR_LOG    = REPO / 'data' / 'live_monitoring' / 'live_scanner_errors.log'

STALE_HOURS  = 25   # warn if scan_latest.json hasn't been updated in this long

_failures = 0
_warnings = 0


def _ok(msg: str) -> None:
    print(f'  [OK]   {msg}')


def _warn(msg: str) -> None:
    global _warnings
    _warnings += 1
    print(f'  [WARN] {msg}')


def _fail(msg: str) -> None:
    global _failures
    _failures += 1
    print(f'  [FAIL] {msg}')


def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def check_env() -> None:
    _load_env_file()
    key = os.environ.get('FMP_API_KEY', '')
    if key and len(key) > 4:
        _ok(f'FMP_API_KEY set ({len(key)} chars)')
    else:
        _fail('FMP_API_KEY missing or empty — scanner will fail on live run')


def check_state_file() -> None:
    if not STATE_PATH.exists():
        _warn('State file not found — scanner has not run yet')
        return
    try:
        state = json.loads(STATE_PATH.read_text())
    except Exception as e:
        _fail(f'State file parse error: {e}')
        return

    last_run = state.get('last_run')
    total    = state.get('total_runs', 0)
    alerts   = state.get('last_alert_count', 0)
    status   = state.get('last_run_status', 'unknown')

    if last_run and last_run != 'null':
        _ok(f'Last run: {last_run} | status: {status} | alerts: {alerts} | total runs: {total}')
    else:
        _warn('State file exists but last_run is null — scanner not yet run')

    if status not in ('ok', None, 'null', ''):
        _warn(f'Last run status was not OK: {status}')
        if status in ('v12_error', 'v12_timeout'):
            last_error = state.get('last_error', '')
            if last_error:
                _warn(f'Last V12 error: {last_error}')
            _warn(f'Read error log: {ERROR_LOG}')
            _warn(f'Read latest memo: {MEMO_PATH}')
            _warn('Inspect service logs: journalctl -u ma-scanner-live.service -n 80 --no-pager')


def check_alert_log() -> None:
    if not ALERT_LOG.exists():
        _warn('Alert log not found — scanner has not produced alerts yet')
        return
    lines = ALERT_LOG.read_text(encoding='utf-8').strip().splitlines()
    row_count = max(0, len(lines) - 1)   # subtract header
    if row_count > 0:
        _ok(f'Alert log: {row_count} rows')
    else:
        _warn('Alert log exists but has no data rows')


def check_memo() -> None:
    if not MEMO_PATH.exists():
        _warn('Review memo not found — scanner has not written a memo yet')
        return
    size = MEMO_PATH.stat().st_size
    _ok(f'Review memo: {size:,} bytes at {MEMO_PATH.name}')


def check_scan_freshness() -> None:
    if not SCAN_LATEST.exists():
        _warn('scan_latest.json not found — no scan has been run')
        return
    mtime = datetime.fromtimestamp(SCAN_LATEST.stat().st_mtime, tz=timezone.utc)
    age   = datetime.now(tz=timezone.utc) - mtime
    age_h = age.total_seconds() / 3600
    if age_h <= STALE_HOURS:
        _ok(f'scan_latest.json age: {age_h:.1f}h (fresh)')
    else:
        _warn(f'scan_latest.json age: {age_h:.1f}h — stale (>{STALE_HOURS}h). Timer may have missed runs.')


def main() -> int:
    print('MA Scanner Health Check')
    print(f'Repo: {REPO}')
    print(f'Time: {datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')
    print()

    check_env()
    check_state_file()
    check_alert_log()
    check_memo()
    check_scan_freshness()

    print()
    if _failures:
        print(f'Result: UNHEALTHY — {_failures} failure(s), {_warnings} warning(s)')
        return 1
    if _warnings:
        print(f'Result: DEGRADED — 0 failures, {_warnings} warning(s)')
        return 0
    print('Result: HEALTHY')
    return 0


if __name__ == '__main__':
    sys.exit(main())
