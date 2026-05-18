"""
live_scanner_runner.py — Main entry point for 24/7 biotech process-signal monitoring.

Modes:
  --once                  Run one scan cycle (call V12 → normalize → FP filter → dedup → write outputs)
  --once --dry-run        Validate directory structure; use existing scan_latest.json if present; skip V12
  --daemon --interval-minutes N   Loop forever with N-minute sleep between runs
  --status                Print state from live_scanner_state.json

Output paths (all relative to repo root):
  data/live_monitoring/live_alert_log.csv          append-only run history
  data/live_monitoring/latest_alerts.json          current dedup state
  data/live_monitoring/latest_review_memo.md       human-readable weekly memo
  data/live_monitoring/live_scanner_state.json     last-run metadata
  data/live_monitoring/runs/run_<ts>.json          per-run snapshot
  data/live_monitoring/live_scanner_errors.log     error log
  live_scanner.lock                                PID lock (repo root)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# ── Repo root: two levels up from src/live_monitoring/ ──────────────────────
_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

# ── Path constants ────────────────────────────────────────────────────────────
SCAN_LATEST    = REPO / 'data' / 'scans' / 'scan_latest.json'
LIVE_DATA      = REPO / 'data' / 'live_monitoring'
ALERT_LOG      = LIVE_DATA / 'live_alert_log.csv'
LATEST_ALERTS  = LIVE_DATA / 'latest_alerts.json'
MEMO_PATH      = LIVE_DATA / 'latest_review_memo.md'
STATE_PATH     = LIVE_DATA / 'live_scanner_state.json'
RUNS_DIR       = LIVE_DATA / 'runs'
ERROR_LOG      = LIVE_DATA / 'live_scanner_errors.log'
LOCK_PATH      = REPO / 'live_scanner.lock'
V12_SCRIPT     = _SRCDIR / 'PRODUCTION_SCANNER_V12.py'
ENV_FILE       = REPO / 'config' / '.env'
DEFAULT_V12_TIMEOUT_SECONDS = 900

# ── Logging ───────────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    LIVE_DATA.mkdir(parents=True, exist_ok=True)
    fmt = '%(asctime)s %(levelname)s %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(ERROR_LOG),
            logging.StreamHandler(sys.stdout),
        ],
    )

log = logging.getLogger(__name__)


# ── .env loader ───────────────────────────────────────────────────────────────

def _load_env() -> None:
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ── Lock file ─────────────────────────────────────────────────────────────────

def _acquire_lock() -> bool:
    if LOCK_PATH.exists():
        try:
            pid = int(LOCK_PATH.read_text().strip())
            os.kill(pid, 0)   # raises if process not running
            log.warning('Lock held by PID %s — scanner already running.', pid)
            return False
        except (ProcessLookupError, ValueError):
            LOCK_PATH.unlink(missing_ok=True)
    LOCK_PATH.write_text(str(os.getpid()))
    return True


def _release_lock() -> None:
    LOCK_PATH.unlink(missing_ok=True)


# ── State file ────────────────────────────────────────────────────────────────

def _read_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {}


def _write_state(state: dict) -> None:
    LIVE_DATA.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


def _send_email_updates(state: dict) -> dict:
    """Send optional email notifications. Never fail the scanner for email."""
    try:
        sys.path.insert(0, str(_HERE))
        from email_notifier import maybe_send_after_run
        updates = maybe_send_after_run(state)
    except Exception as exc:
        log.exception('Email notification failed: %s', exc)
        updates = {
            'last_email_status': 'send_failed',
            'last_email_error': str(exc),
        }
    if updates:
        state.update(updates)
        _write_state(state)
    return state


# ── V12 subprocess call ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class V12RunResult:
    ok: bool
    status: str
    returncode: int | None
    elapsed_seconds: float
    stdout_tail: str = ''
    stderr_tail: str = ''
    error: str = ''
    output_exists: bool = False
    output_path: str = str(SCAN_LATEST)


def _tail(text: str, max_chars: int = 4000) -> str:
    if not text:
        return ''
    return text[-max_chars:]


def _tail_lines(text: str, max_lines: int = 20) -> str:
    """Return the last max_lines lines of text."""
    if not text:
        return ''
    lines = text.splitlines()
    return '\n'.join(lines[-max_lines:])


def _last_progress_line(text: str) -> str:
    """
    Scan stdout for the most recent LIVE_PROGRESS or PHASE_ line.
    Returns the line, or empty string if none found.
    """
    if not text:
        return ''
    for line in reversed(text.splitlines()):
        if 'LIVE_PROGRESS' in line or 'PHASE_START' in line or 'PHASE_END' in line:
            return line.strip()
    return ''


def _output_mtime(path: Path) -> str | None:
    """Return ISO-formatted mtime of path, or None if missing."""
    if not path.exists():
        return None
    import datetime as _dt
    mtime = _dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.timezone.utc)
    return mtime.strftime('%Y-%m-%d %H:%M:%S UTC')


def _run_v12(timeout_seconds: int = DEFAULT_V12_TIMEOUT_SECONDS,
             extra_args: list | None = None) -> V12RunResult:
    """Call V12 via subprocess with a hard timeout."""
    cmd = [sys.executable, str(V12_SCRIPT)] + (extra_args or [])
    env = os.environ.copy()
    start = time.monotonic()
    start_wall = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    # Record output mtime before the run so we can detect if it changed
    output_mtime_before = _output_mtime(SCAN_LATEST)

    log.info('Running V12 scanner subprocess.')
    log.info('V12 command: %s', ' '.join(cmd))
    log.info('V12 cwd: %s', REPO)
    log.info('V12 timeout seconds: %s', timeout_seconds)
    log.info('V12 start time: %s', start_wall)
    log.info('V12 expected output: %s', SCAN_LATEST)
    log.info('V12 output mtime before run: %s', output_mtime_before or 'file absent')

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        log.error('V12 timed out after %.1fs. Terminating process %s.', elapsed, proc.pid)
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            log.error('V12 did not terminate cleanly. Killing process %s.', proc.pid)
            proc.kill()
            stdout, stderr = proc.communicate()

        stdout = stdout or ''
        stderr = stderr or ''
        output_exists = SCAN_LATEST.exists()
        output_mtime_after = _output_mtime(SCAN_LATEST)
        output_changed = (output_mtime_before != output_mtime_after)
        last_progress = _last_progress_line(stdout)

        log.error('V12 timeout diagnostics:')
        log.error('  command:            %s', ' '.join(cmd))
        log.error('  timeout_seconds:    %s', timeout_seconds)
        log.error('  elapsed_seconds:    %.1f', elapsed)
        log.error('  output_path:        %s', SCAN_LATEST)
        log.error('  output_exists:      %s', output_exists)
        log.error('  output_mtime_before: %s', output_mtime_before or 'absent')
        log.error('  output_mtime_after:  %s', output_mtime_after or 'absent')
        log.error('  output_changed:     %s', output_changed)
        if last_progress:
            log.error('  last_progress_line: %s', last_progress)
        if stdout:
            log.error('V12 stdout (last 20 lines):\n%s', _tail_lines(stdout, 20))
        if stderr:
            log.error('V12 stderr (last 20 lines):\n%s', _tail_lines(stderr, 20))

        return V12RunResult(
            ok=False,
            status='v12_timeout',
            returncode=proc.returncode,
            elapsed_seconds=elapsed,
            stdout_tail=_tail_lines(stdout, 20),
            stderr_tail=_tail_lines(stderr, 20),
            error=(
                f'V12 timed out after {timeout_seconds}s. '
                f'Last progress: {last_progress or "none"}. '
                f'Output changed: {output_changed}.'
            ),
            output_exists=output_exists,
        )

    elapsed = time.monotonic() - start
    stdout = stdout or ''
    stderr = stderr or ''
    output_exists = SCAN_LATEST.exists()
    output_mtime_after = _output_mtime(SCAN_LATEST)
    log.info('V12 elapsed seconds: %.1f', elapsed)
    log.info('V12 return code: %s', proc.returncode)
    log.info('V12 output exists after run: %s (%s)', output_exists, SCAN_LATEST)
    log.info('V12 output mtime after run: %s', output_mtime_after or 'absent')

    if proc.returncode != 0:
        log.error('V12 failed with return code %s.', proc.returncode)
        if stdout:
            log.error('V12 stdout (last 20 lines):\n%s', _tail_lines(stdout, 20))
        if stderr:
            log.error('V12 stderr (last 20 lines):\n%s', _tail_lines(stderr, 20))
        return V12RunResult(
            ok=False,
            status='v12_error',
            returncode=proc.returncode,
            elapsed_seconds=elapsed,
            stdout_tail=_tail_lines(stdout, 20),
            stderr_tail=_tail_lines(stderr, 20),
            error=f'V12 exited with return code {proc.returncode}',
            output_exists=output_exists,
        )

    log.info('V12 complete.')
    return V12RunResult(
        ok=True,
        status='ok',
        returncode=proc.returncode,
        elapsed_seconds=elapsed,
        stdout_tail=_tail_lines(stdout, 20),
        stderr_tail=_tail_lines(stderr, 20),
        output_exists=output_exists,
    )


# ── Scan results loader ───────────────────────────────────────────────────────

def _load_scan_results() -> list:
    if not SCAN_LATEST.exists():
        log.warning('scan_latest.json not found at %s', SCAN_LATEST)
        return []
    try:
        data = json.loads(SCAN_LATEST.read_text(encoding='utf-8'))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # some scan formats wrap list in a key
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []
    except Exception as e:
        log.error('Failed to parse scan_latest.json: %s', e)
        return []


# ── Per-run snapshot ──────────────────────────────────────────────────────────

def _write_run_snapshot(ts: str, alerts: list, stats: dict, dry_run: bool) -> None:
    try:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        log.warning('Run snapshot skipped — cannot create runs dir: %s', exc)
        return
    safe_ts = ts.replace(':', '').replace(' ', '_')
    path = RUNS_DIR / f'run_{safe_ts}.json'
    snapshot = {
        'run_timestamp': ts,
        'dry_run':       dry_run,
        'alert_count':   len(alerts),
        'stats':         stats,
        'alerts':        alerts,
    }
    try:
        path.write_text(json.dumps(snapshot, indent=2, default=str), encoding='utf-8')
        log.info('Run snapshot → %s', path.name)
    except OSError as exc:
        log.warning('Run snapshot write failed — continuing: %s', exc)


def _write_failure_memo(scan_ts: str, run_mode: str, result: V12RunResult) -> None:
    MEMO_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Extract last progress line from stdout_tail if available
    last_progress = _last_progress_line(result.stdout_tail) if result.stdout_tail else ''

    lines = [
        '# Biotech Strategic Process Monitor — Run Failure',
        '',
        f'**Scan timestamp:** {scan_ts}',
        f'**Run mode:** {run_mode}',
        f'**Status:** {result.status}',
        f'**Elapsed seconds:** {result.elapsed_seconds:.1f}',
        f'**Timeout setting:** {DEFAULT_V12_TIMEOUT_SECONDS}s',
        f'**V12 return code:** {result.returncode}',
        f'**Expected V12 output:** `{result.output_path}`',
        f'**Output file exists after run:** {result.output_exists}',
    ]
    if last_progress:
        lines.append(f'**Last progress log line:** `{last_progress}`')
    lines.extend([
        '',
        'No alert processing was performed for this run. The runner did not',
        'process existing `scan_latest.json` as fresh data after the V12 failure.',
        '',
        '## Operator Checks',
        '',
        '- Service logs: `journalctl -u ma-scanner-live.service -n 80 --no-pager`',
        f'- Error log: `{ERROR_LOG}`',
        f'- State file: `{STATE_PATH}`',
        '- Check for hung processes: `pgrep -la PRODUCTION_SCANNER`',
        '- Clear stale lock (if no scanner running): `python3 src/live_monitoring/live_scanner_runner.py --clear-stale-lock`',
        '',
    ])
    if result.error:
        lines.extend(['## Error Detail', '', result.error, ''])
    if result.stderr_tail:
        lines.extend(['## stderr (last 20 lines)', '', '```text', result.stderr_tail, '```', ''])
    if result.stdout_tail:
        lines.extend(['## stdout (last 20 lines)', '', '```text', result.stdout_tail, '```', ''])
    MEMO_PATH.write_text('\n'.join(lines), encoding='utf-8')
    log.info('Failure memo written to %s', MEMO_PATH)


# ── Self-healing dirs + write preflight ───────────────────────────────────────

def _ensure_live_dirs() -> None:
    """Create all required output dirs. Logs a warning if a dir cannot be created."""
    for d in [LIVE_DATA, RUNS_DIR, SCAN_LATEST.parent]:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            log.warning('Cannot create dir %s: %s', d, exc)


def _preflight_write_check() -> bool:
    """
    Verify LIVE_DATA is writable before V12 starts.
    Returns True if OK. On failure, logs remediation command and returns False.
    """
    test_path = LIVE_DATA / '.write_check'
    try:
        LIVE_DATA.mkdir(parents=True, exist_ok=True)
        test_path.write_text('ok')
        test_path.unlink(missing_ok=True)
        return True
    except PermissionError:
        log.error(
            'Write permission denied on %s. '
            'Fix: sudo chown -R $USER %s && chmod -R 755 %s',
            LIVE_DATA, LIVE_DATA.parent, LIVE_DATA.parent,
        )
        return False


# ── Directory structure validation (dry-run) ──────────────────────────────────

def _validate_dirs() -> bool:
    required = [
        REPO / 'data' / 'scans',
        REPO / 'data' / 'live_monitoring',
        REPO / 'src' / 'live_monitoring',
        REPO / 'config',
    ]
    ok = True
    for d in required:
        exists = d.exists()
        status = 'OK' if exists else 'MISSING'
        print(f'  [{status}] {d.relative_to(REPO)}')
        if not exists:
            ok = False
    print(f'  [{"OK" if V12_SCRIPT.exists() else "MISSING"}] {V12_SCRIPT.relative_to(REPO)}')
    print(f'  [{"OK" if ENV_FILE.exists() else "MISSING (scanner will use env vars)"}] config/.env')
    print(f'  [{"OK" if SCAN_LATEST.exists() else "MISSING (dry-run will use empty list)"}] data/scans/scan_latest.json')
    return ok


# ── Core scan cycle ───────────────────────────────────────────────────────────

def run_once(dry_run: bool = False, v12_timeout_seconds: int = DEFAULT_V12_TIMEOUT_SECONDS) -> dict:
    """
    Execute one full scan cycle.
    Returns state dict with run metadata.
    """
    _ensure_live_dirs()
    if not _preflight_write_check():
        scan_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        state = _read_state()
        state.update({
            'last_run': scan_ts,
            'last_run_status': 'preflight_failed',
            'last_run_mode': 'dry-run' if dry_run else 'once',
            'last_error': f'Write permission denied on {LIVE_DATA}',
            'total_runs': state.get('total_runs', 0) + 1,
            'last_alert_count': 0,
            'last_new_count': 0,
            'last_investigate_count': 0,
            'last_watch_count': 0,
        })
        return state

    # Import here to avoid circular issues and keep startup fast
    sys.path.insert(0, str(_HERE))
    from alert_normalizer import (
        normalize_scan_results, load_alert_log,
        deduplicate, append_to_alert_log, write_latest_alerts,
    )
    from false_positive_filter import classify_alerts, summary_stats
    from review_memo_writer import write_memo

    scan_ts    = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    run_mode   = 'dry-run' if dry_run else 'once'
    v12_result = V12RunResult(
        ok=True,
        status='ok',
        returncode=0,
        elapsed_seconds=0.0,
        output_exists=SCAN_LATEST.exists(),
    )

    if not dry_run:
        v12_result = _run_v12(timeout_seconds=v12_timeout_seconds)
        if not v12_result.ok:
            log.error('V12 failed with status=%s — skipping alert processing for this run.', v12_result.status)
            last_progress = _last_progress_line(v12_result.stdout_tail) if v12_result.stdout_tail else ''
            _write_failure_memo(scan_ts, run_mode, v12_result)
            state = _read_state()
            state.update({
                'last_run':             scan_ts,
                'last_run_status':      v12_result.status,
                'last_run_mode':        run_mode,
                'last_error':           v12_result.error,
                'last_v12_returncode':  v12_result.returncode,
                'last_v12_elapsed_sec': round(v12_result.elapsed_seconds, 1),
                'last_v12_timeout_sec': v12_timeout_seconds,
                'last_v12_output_path': str(SCAN_LATEST),
                'last_v12_output_exists': v12_result.output_exists,
                'last_v12_last_progress': last_progress,
                'last_v12_stdout_tail': v12_result.stdout_tail[-500:] if v12_result.stdout_tail else '',
                'last_v12_stderr_tail': v12_result.stderr_tail[-500:] if v12_result.stderr_tail else '',
                'last_total_scanned':   0,
                'total_runs':           state.get('total_runs', 0) + 1,
                'last_alert_count':     0,
                'last_new_count':       0,
                'last_investigate_count': 0,
                'last_watch_count':     0,
                'state_path':           str(STATE_PATH),
                'memo_path':            str(MEMO_PATH),
                'alert_log_path':       str(ALERT_LOG),
            })
            _write_state(state)
            state = _send_email_updates(state)
            return state

    raw_results = _load_scan_results()
    total_scanned = len(raw_results)
    log.info('Loaded %d raw scan results.', total_scanned)

    alerts  = normalize_scan_results(raw_results, scan_ts)
    alerts  = classify_alerts(alerts)
    existing = load_alert_log(ALERT_LOG)
    alerts  = deduplicate(alerts, existing, scan_ts)

    stats = summary_stats(alerts)
    log.info(
        'Alerts: %d total | %d INVESTIGATE | %d WATCH | %d suppressed | %d new',
        stats['total'],
        stats['KEEP_HIGH_PRIORITY'] + stats.get('KEEP_REVIEW', 0),
        stats['DOWNGRADE_WATCH'],
        stats['SUPPRESS_FALSE_POSITIVE'],
        stats['new'],
    )

    LIVE_DATA.mkdir(parents=True, exist_ok=True)
    append_to_alert_log(alerts, ALERT_LOG)
    write_latest_alerts(alerts, LATEST_ALERTS)
    write_memo(
        alerts      = alerts,
        memo_path   = MEMO_PATH,
        scan_ts     = scan_ts,
        total_scanned = total_scanned,
        run_mode    = run_mode,
        dry_run     = dry_run,
    )
    try:
        _write_run_snapshot(scan_ts, alerts, stats, dry_run)
    except Exception as exc:
        log.warning('Run snapshot unexpectedly failed — continuing: %s', exc)

    state = _read_state()
    state.update({
        'last_run':          scan_ts,
        'last_run_status':   'ok',
        'last_run_mode':     run_mode,
        'last_error':        '',
        'last_v12_returncode': v12_result.returncode,
        'last_v12_elapsed_sec': round(v12_result.elapsed_seconds, 1),
        'last_v12_timeout_sec': v12_timeout_seconds,
        'last_v12_output_path': str(SCAN_LATEST),
        'last_v12_output_exists': v12_result.output_exists,
        'last_v12_last_progress': '',
        'last_total_scanned': total_scanned,
        'total_runs':        state.get('total_runs', 0) + 1,
        'total_alerts_ever': state.get('total_alerts_ever', 0) + len(alerts),
        'last_alert_count':  len(alerts),
        'last_new_count':    stats['new'],
        'last_investigate_count': stats['KEEP_HIGH_PRIORITY'] + stats.get('KEEP_REVIEW', 0),
        'last_watch_count':  stats['DOWNGRADE_WATCH'],
        'state_path':        str(STATE_PATH),
        'memo_path':         str(MEMO_PATH),
        'alert_log_path':    str(ALERT_LOG),
    })
    _write_state(state)
    state = _send_email_updates(state)
    return state


# ── Status printer ────────────────────────────────────────────────────────────

def _is_scanner_running() -> tuple[bool, int | None]:
    """Check if any scanner process is running. Returns (is_running, pid_or_None)."""
    if LOCK_PATH.exists():
        try:
            pid = int(LOCK_PATH.read_text().strip())
            os.kill(pid, 0)
            return True, pid
        except (ProcessLookupError, ValueError, OSError):
            pass
    return False, None


def print_status() -> None:
    state = _read_state()
    running, running_pid = _is_scanner_running()

    print('Live Scanner Status')
    print('=' * 50)

    # Running indicator
    if running:
        print(f'  Running       : YES (PID {running_pid})')
    else:
        print('  Running       : no')

    # Lock file
    if LOCK_PATH.exists():
        pid_str = LOCK_PATH.read_text().strip()
        stale_note = ' (STALE — process not found)' if not running else ''
        print(f'  Lock file     : present (PID {pid_str}){stale_note}')
    else:
        print('  Lock file     : absent')

    if not state:
        print()
        print('  No state file found — scanner has not run yet.')
        print(f'  State file location: {STATE_PATH}')
        return

    last_run      = state.get('last_run', 'never')
    last_status   = state.get('last_run_status', 'unknown')
    last_alerts   = state.get('last_alert_count', 0)
    last_new      = state.get('last_new_count', 0)
    last_invst    = state.get('last_investigate_count', 0)
    last_watch    = state.get('last_watch_count', 0)
    last_scanned  = state.get('last_total_scanned', 0)
    total_runs    = state.get('total_runs', 0)
    elapsed       = state.get('last_v12_elapsed_sec', '')
    timeout_sec   = state.get('last_v12_timeout_sec', DEFAULT_V12_TIMEOUT_SECONDS)
    last_error    = state.get('last_error', '')
    last_progress = state.get('last_v12_last_progress', '')
    memo_path     = state.get('memo_path', str(MEMO_PATH))
    alert_log     = state.get('alert_log_path', str(ALERT_LOG))

    print(f'  Last run      : {last_run}')
    print(f'  Status        : {last_status}')
    print(f'  Total runs    : {total_runs}')
    if elapsed:
        print(f'  V12 elapsed   : {elapsed}s (timeout: {timeout_sec}s)')

    if last_status == 'ok':
        print(f'  Alerts        : {last_alerts} total | {last_new} new | {last_invst} investigate | {last_watch} watch')
        print(f'  Names scanned : {last_scanned}')
    else:
        print(f'  Last error    : {last_error or "(none recorded)"}')
        if last_progress:
            print(f'  Last progress : {last_progress}')

    email_status  = state.get('last_email_status', '')
    email_sent_at = state.get('last_email_sent_at', '')
    if email_status:
        print(f'  Email         : {email_status}  sent_at={email_sent_at or "not sent"}')

    print()
    print(f'  Latest memo   : {memo_path}')
    print(f'  Alert log     : {alert_log}')
    print(f'  State file    : {STATE_PATH}')

    # Recovery suggestions
    if last_status in ('v12_timeout', 'v12_error'):
        print()
        print('  RECOVERY:')
        print('    journalctl -u ma-scanner-live.service -n 80 --no-pager')
        print(f'    tail -50 {ERROR_LOG}')
        if not running:
            print(f'    python3 {__file__} --clear-stale-lock')
        print(f'    python3 {__file__} --once --dry-run')


# ── Daemon loop ───────────────────────────────────────────────────────────────

def run_daemon(interval_minutes: int, v12_timeout_seconds: int = DEFAULT_V12_TIMEOUT_SECONDS) -> None:
    log.info('Daemon mode: interval=%d min. Press Ctrl+C to stop.', interval_minutes)

    def _handle_sigterm(sig, frame):
        log.info('SIGTERM received — shutting down.')
        _release_lock()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    while True:
        if not _acquire_lock():
            log.warning('Could not acquire lock — skipping cycle.')
        else:
            try:
                run_once(dry_run=False, v12_timeout_seconds=v12_timeout_seconds)
            except Exception as e:
                log.exception('Scan cycle error: %s', e)
            finally:
                _release_lock()
        log.info('Sleeping %d minutes until next run.', interval_minutes)
        time.sleep(interval_minutes * 60)


# ── Clear stale lock ──────────────────────────────────────────────────────────

def clear_stale_lock() -> int:
    """
    Remove the lock file only if no scanner process is currently running.
    Returns 0 on success, 1 if a live process was found (lock not removed).
    """
    if not LOCK_PATH.exists():
        print('Lock file not present — nothing to clear.')
        return 0
    running, pid = _is_scanner_running()
    if running:
        print(f'WARNING: Scanner process IS running (PID {pid}). Lock NOT removed.')
        print('Only run --clear-stale-lock when no scanner is active.')
        return 1
    LOCK_PATH.unlink(missing_ok=True)
    print(f'Stale lock file removed: {LOCK_PATH}')
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description='Live biotech process-signal monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--once',             action='store_true', help='Run one scan cycle and exit')
    mode.add_argument('--daemon',           action='store_true', help='Run continuously')
    mode.add_argument('--status',           action='store_true', help='Print last-run state and exit')
    mode.add_argument('--smoke-v12',        action='store_true',
                      help='Compile/check V12 entrypoint without running a live scan')
    mode.add_argument('--clear-stale-lock', action='store_true',
                      help='Remove lock file if no scanner process is running')

    p.add_argument('--dry-run', action='store_true',
                   help='(--once only) Skip V12 call; use existing scan_latest.json')
    p.add_argument('--interval-minutes', type=int, default=60,
                   help='(--daemon only) Minutes between scans (default: 60)')
    p.add_argument('--v12-timeout-seconds', type=int, default=DEFAULT_V12_TIMEOUT_SECONDS,
                   help='Hard timeout for the V12 subprocess (default: 900)')
    # --sample-size is NOT passed to V12 because V12 does not accept --limit or
    # --ticker-limit arguments. Implementing it cleanly would require V12 changes
    # that touch the universe logic; the safer approach is --quick in V12 itself
    # (first 50 tickers). See V12 --quick flag for testing.
    return p.parse_args(argv)


def main(argv=None) -> int:
    _setup_logging()
    _load_env()
    args = _parse_args(argv)

    if args.status:
        print_status()
        return 0

    if args.clear_stale_lock:
        return clear_stale_lock()

    if args.smoke_v12:
        print('V12 smoke check')
        print(f'  Repo: {REPO}')
        print(f'  V12 script: {V12_SCRIPT}')
        print(f'  V12 exists: {V12_SCRIPT.exists()}')
        result = subprocess.run([sys.executable, '-m', 'py_compile', str(V12_SCRIPT)], cwd=str(REPO))
        if result.returncode == 0:
            print('  py_compile: OK')
        return result.returncode

    if args.once:
        if args.dry_run:
            print('Dry-run: validating directory structure ...')
            _validate_dirs()
            print()

        if not _acquire_lock():
            log.error('Scanner already running — exiting.')
            return 1
        try:
            state = run_once(dry_run=args.dry_run, v12_timeout_seconds=args.v12_timeout_seconds)
            log.info('Run complete. Alerts: %d | New: %d',
                     state['last_alert_count'], state['last_new_count'])
            return 0 if state.get('last_run_status') == 'ok' else 1
        except Exception as e:
            log.exception('Run failed: %s', e)
            return 1
        finally:
            _release_lock()

    if args.daemon:
        if not _acquire_lock():
            log.error('Scanner already running — exiting.')
            return 1
        try:
            run_daemon(args.interval_minutes, v12_timeout_seconds=args.v12_timeout_seconds)
        except KeyboardInterrupt:
            log.info('Keyboard interrupt — stopping daemon.')
        finally:
            _release_lock()
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
