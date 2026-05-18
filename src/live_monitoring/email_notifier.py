#!/usr/bin/env python3
"""
email_notifier.py — Optional email notifications for the live scanner.

Standard-library only. Secrets are loaded from config/.env or environment
variables and are never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import smtplib
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO = _SRCDIR.parent

ENV_FILE = REPO / 'config' / '.env'
LIVE_DATA = REPO / 'data' / 'live_monitoring'
STATE_PATH = LIVE_DATA / 'live_scanner_state.json'
MEMO_PATH = LIVE_DATA / 'latest_review_memo.md'
ALERT_LOG = LIVE_DATA / 'live_alert_log.csv'
ERROR_LOG = LIVE_DATA / 'live_scanner_errors.log'
RESEND_ENDPOINT = 'https://api.resend.com/emails'
RESEND_USER_AGENT = 'ma-scanner-live/1.0'


# ── Env / helpers ─────────────────────────────────────────────────────────────

def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    with ENV_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None or value == '':
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _clip(value: str, limit: int = 1200) -> str:
    text = str(value or '')
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + '\n...'


# ── Memo parsing ──────────────────────────────────────────────────────────────

def _parse_memo_metrics() -> dict[str, int]:
    """Extract summary counts from the ## Summary table in latest_review_memo.md."""
    defaults: dict[str, int] = {
        'names_scanned': 0,
        'total_alerts':  0,
        'new_alerts':    0,
        'updated_alerts': 0,
        'investigate':   0,
        'watch':         0,
        'suppressed':    0,
    }
    if not MEMO_PATH.exists():
        return defaults

    _label_map = {
        'names scanned':  'names_scanned',
        'total alerts':   'total_alerts',
        'new alerts':     'new_alerts',
        'updated alerts': 'updated_alerts',
        'high-priority':  'investigate',
        'review':         'watch',
        'suppressed':     'suppressed',
    }

    in_summary = False
    result = dict(defaults)
    for line in MEMO_PATH.read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith('## Summary'):
            in_summary = True
            continue
        if in_summary and line.startswith('## ') and 'Summary' not in line:
            break
        if in_summary and line.startswith('|'):
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2:
                label = parts[0].lower()
                raw = parts[1].replace('*', '').strip()
                for substr, field in _label_map.items():
                    if substr in label:
                        try:
                            result[field] = int(raw)
                        except ValueError:
                            pass
                        break
    return result


def _parse_case_table(lines: list[str]) -> dict[str, str]:
    """Parse | Field | Value | rows from a case section."""
    fields: dict[str, str] = {}
    _field_map = {
        'signal quality':     'signal_quality',
        'recommended action': 'action',
        'signal type':        'signal_type',
        'market cap':         'market_cap',
        'priced-in flag':     'priced_in',   # must be before 'price' to avoid substring match
        'filing type':        'filing_type',
        'filing date':        'filing_date',
        'price':              'price',
    }
    for line in lines:
        if not line.startswith('|'):
            continue
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) >= 2:
            label = parts[0].lower()
            value = re.sub(r'\*+', '', parts[1]).strip()
            for substr, key in _field_map.items():
                if substr in label:
                    fields[key] = value
                    break
    return fields


def _parse_memo_top_cases(limit: int = 5) -> list[dict[str, str]]:
    """
    Parse top-N case sections from latest_review_memo.md.
    Returns list of dicts with ticker, company, action, signal_quality, etc.
    """
    if not MEMO_PATH.exists():
        return []

    lines = MEMO_PATH.read_text(encoding='utf-8', errors='replace').splitlines()
    cases: list[dict[str, str]] = []
    i = 0
    case_header_re = re.compile(r'^### \d+\. [^\s]+ (.+?) — (.+?)(?:\s+\*\*\[.+?\]\*\*)?$')

    while i < len(lines) and len(cases) < limit:
        line = lines[i]
        if line.startswith('## ') and 'Top' not in line and cases:
            break
        m = case_header_re.match(line)
        if not m:
            i += 1
            continue

        ticker  = m.group(1).strip()
        company = m.group(2).strip()

        section: list[str] = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if nxt.startswith('### ') or (nxt.startswith('## ') and j > i + 1):
                break
            section.append(nxt)
            j += 1

        case: dict[str, str] = {'ticker': ticker, 'company': company}
        case.update(_parse_case_table(section))

        for sl in section:
            tm = re.search(r'\*\*Trigger phrase:\*\*\s+`(.+?)`', sl)
            if tm:
                case['trigger'] = tm.group(1)
                break

        cases.append(case)
        i = j

    return cases


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EmailConfig:
    enabled: bool
    provider: str
    host: str
    port: int
    user: str
    password: str
    recipient: str
    sender: str
    resend_api_key: str
    resend_from: str
    on_every_run: bool
    on_new_alerts: bool
    daily_digest: bool

    @property
    def smtp_ready(self) -> bool:
        return bool(self.host and self.port and self.user and self.password and self.recipient)

    @property
    def resend_ready(self) -> bool:
        return bool(self.resend_api_key and self.resend_from and self.recipient)


def load_config() -> EmailConfig:
    _load_env_file()
    provider = os.environ.get('EMAIL_PROVIDER', 'smtp').strip().lower() or 'smtp'
    if provider not in {'smtp', 'resend'}:
        provider = 'smtp'
    host = os.environ.get('SMTP_HOST', '').strip()
    port_raw = os.environ.get('SMTP_PORT', '587').strip() or '587'
    try:
        port = int(port_raw)
    except ValueError:
        port = 587
    user = os.environ.get('SMTP_USER', '').strip()
    recipient = (
        os.environ.get('EMAIL_RECIPIENT', '').strip()
        or os.environ.get('SMTP_RECIPIENT', '').strip()
    )
    sender = os.environ.get('SMTP_FROM', '').strip() or user
    resend_from = os.environ.get('RESEND_FROM', '').strip()
    return EmailConfig(
        enabled=_truthy(os.environ.get('EMAIL_ALERTS_ENABLED'), default=False),
        provider=provider,
        host=host,
        port=port,
        user=user,
        password=os.environ.get('SMTP_PASSWORD', ''),
        recipient=recipient,
        sender=sender,
        resend_api_key=os.environ.get('RESEND_API_KEY', ''),
        resend_from=resend_from,
        on_every_run=_truthy(os.environ.get('EMAIL_ON_EVERY_RUN'), default=False),
        on_new_alerts=_truthy(os.environ.get('EMAIL_ON_NEW_ALERTS'), default=True),
        daily_digest=_truthy(os.environ.get('EMAIL_DAILY_DIGEST'), default=True),
    )


def status_dict() -> dict[str, Any]:
    cfg = load_config()
    state = _read_json(STATE_PATH)
    return {
        'email_alerts_enabled':  cfg.enabled,
        'email_provider':        cfg.provider,
        'resend_api_key_set':    bool(cfg.resend_api_key),
        'resend_from_set':       bool(cfg.resend_from),
        'recipient_set':         bool(cfg.recipient),
        'smtp_host_set':         bool(cfg.host),
        'smtp_port':             cfg.port,
        'smtp_user_set':         bool(cfg.user),
        'smtp_password_set':     bool(cfg.password),
        'smtp_recipient_set':    bool(os.environ.get('SMTP_RECIPIENT', '').strip()),
        'smtp_from_set':         bool(cfg.sender),
        'email_on_every_run':    cfg.on_every_run,
        'email_on_new_alerts':   cfg.on_new_alerts,
        'email_daily_digest':    cfg.daily_digest,
        'last_email_type':       state.get('last_email_type', ''),
        'last_email_status':     state.get('last_email_status', ''),
        'last_email_sent_at':    state.get('last_email_sent_at', ''),
        'last_email_subject':    state.get('last_email_subject', ''),
        'last_daily_digest_date': state.get('last_daily_digest_date', ''),
        'env_file_exists':       ENV_FILE.exists(),
    }


# ── Email formatting ──────────────────────────────────────────────────────────

_STATUS_LABEL = {
    'ok':          'OK',
    'v12_error':   'ERROR (V12 failed)',
    'v12_timeout': 'ERROR (V12 timeout)',
    'dry-run':     'DRY RUN',
    'manual_test': 'OK (manual test)',
    'unknown':     'unknown',
}


def _metrics_from_state_or_memo(state: dict[str, Any]) -> dict[str, int]:
    """Return metrics. Prefer state fields; fall back to parsing the memo."""
    memo = _parse_memo_metrics()

    def _int(key: str) -> int | None:
        v = state.get(key)
        if v is not None and str(v).strip() not in ('', 'None', 'null'):
            try:
                return int(float(v))
            except (ValueError, TypeError):
                pass
        return None

    investigate = _int('last_investigate_count') or memo['investigate']
    watch       = _int('last_watch_count')       or memo['watch']
    total       = _int('last_alert_count')       or memo['total_alerts']
    new_alerts  = _int('last_new_count')         if _int('last_new_count') is not None else memo['new_alerts']
    scanned     = _int('last_total_scanned')     or memo['names_scanned']

    return {
        'investigate': investigate,
        'watch':       watch,
        'total':       total,
        'new':         new_alerts,
        'scanned':     scanned,
        'updated':     memo['updated_alerts'],
        'suppressed':  memo['suppressed'],
    }


def _subject(kind: str, state: dict[str, Any], is_test: bool = False) -> str:
    run_status = state.get('last_run_status', 'unknown')
    prefix = '[TEST] ' if is_test else ''

    if kind == 'error' or run_status in ('v12_error', 'v12_timeout'):
        return f'{prefix}MA Scanner ERROR: {run_status}'

    m = _metrics_from_state_or_memo(state)

    if kind == 'daily':
        return (
            f'{prefix}MA Scanner Daily Digest: '
            f'{m["total"]} alerts | {m["investigate"]} investigate | {m["watch"]} watch'
        )
    return (
        f'{prefix}MA Scanner: '
        f'{m["total"]} alerts | {m["investigate"]} investigate | {m["watch"]} watch | {m["new"]} new'
    )


def _format_top_cases(limit: int = 5) -> str:
    cases = _parse_memo_top_cases(limit=limit)
    if not cases:
        return 'No actionable cases in this scan.'

    lines: list[str] = []
    for i, c in enumerate(cases, 1):
        ticker  = c.get('ticker', '?')
        company = c.get('company', '')
        sq      = c.get('signal_quality', '')
        action  = re.sub(r'\*+', '', c.get('action', '')).strip()
        ftype   = c.get('filing_type', '')
        fdate   = c.get('filing_date', '')
        trigger = c.get('trigger', '')
        priced  = c.get('priced_in', '')
        mcap    = c.get('market_cap', '')
        price   = c.get('price', '')

        filing_str = ', '.join(filter(None, [ftype, fdate]))

        lines.append(f'{i}. {ticker} — {company}')
        if sq:
            lines.append(f'   Signal:    {sq}')
        if action:
            lines.append(f'   Action:    {action}')
        if filing_str:
            lines.append(f'   Filing:    {filing_str}')
        if trigger:
            lines.append(f'   Trigger:   {trigger}')
        if priced:
            lines.append(f'   Priced-in: {priced}')
        if mcap or price:
            # mcap and price come pre-formatted from the memo (e.g. "$966.0M", "$27.45", "—")
            mstr = mcap  if (mcap  and mcap  != '—') else ''
            pstr = price if (price and price != '—') else ''
            parts_mkt = list(filter(None, [mstr, pstr]))
            if parts_mkt:
                lines.append('   Market:    ' + ' | '.join(parts_mkt))
        lines.append('')

    return '\n'.join(lines).rstrip()


def _body(kind: str, state: dict[str, Any], is_test: bool = False) -> str:
    run_ts     = state.get('last_run', 'unknown')
    run_status = state.get('last_run_status', 'unknown')
    status_str = _STATUS_LABEL.get(run_status, run_status.upper())
    m          = _metrics_from_state_or_memo(state)
    elapsed    = state.get('last_v12_elapsed_sec', '')

    title = 'MA Scanner Daily Brief' if kind != 'error' else 'MA Scanner — Run Error'

    lines: list[str] = []
    lines.append(title)
    lines.append('=' * len(title))
    lines.append(f'Generated  : {_utc_now()}')
    lines.append(f'Latest scan: {run_ts}')
    lines.append(f'Status     : {status_str}')
    if elapsed:
        lines.append(f'V12 elapsed: {elapsed}s')
    if is_test:
        lines.append('Email type : TEST (real scanner state preserved)')
    lines.append('')

    lines.append('Summary')
    lines.append('-------')
    lines.append(f'Names scanned : {m["scanned"]}')
    lines.append(f'Total alerts  : {m["total"]}')
    lines.append(f'New alerts    : {m["new"]}')
    lines.append(f'Updated       : {m["updated"]}')
    lines.append(f'High-priority : {m["investigate"]}')
    lines.append(f'Watch         : {m["watch"]}')
    lines.append(f'Suppressed    : {m["suppressed"]}')
    lines.append('')

    if kind == 'error':
        last_error = state.get('last_error', '')
        lines.append('Error Detail')
        lines.append('------------')
        lines.append(f'Status : {run_status}')
        if last_error:
            lines.append(f'Error  : {last_error}')
        lines.append('')
        lines.append('Operator checks')
        lines.append('  journalctl -u ma-scanner-live.service -n 80 --no-pager')
        lines.append(f'  tail -50 {ERROR_LOG}')
        lines.append('')
    else:
        lines.append('Top Cases')
        lines.append('---------')
        lines.append(_format_top_cases(limit=5))
        lines.append('')

    lines.append('Notes')
    lines.append('-----')
    lines.append(f'  Full memo : {MEMO_PATH}')
    lines.append(f'  Alert log : {ALERT_LOG}')
    lines.append(f'  Error log : {ERROR_LOG}')
    lines.append('  Research monitoring only. Not investment advice.')

    return '\n'.join(lines)


# ── Send infrastructure ───────────────────────────────────────────────────────

def _missing_provider_config(cfg: EmailConfig) -> list[str]:
    if cfg.provider == 'resend':
        missing = []
        if not cfg.resend_api_key:
            missing.append('RESEND_API_KEY')
        if not cfg.resend_from:
            missing.append('RESEND_FROM')
        if not cfg.recipient:
            missing.append('EMAIL_RECIPIENT or SMTP_RECIPIENT')
        return missing
    missing = []
    if not cfg.smtp_ready:
        if not cfg.host:
            missing.append('SMTP_HOST')
        if not cfg.user:
            missing.append('SMTP_USER')
        if not cfg.password:
            missing.append('SMTP_PASSWORD')
        if not cfg.recipient:
            missing.append('SMTP_RECIPIENT')
    return missing


def _format_resend_error(status_code: int, response_body: str) -> str:
    response_body = response_body.strip()
    fields: dict[str, Any] = {}
    if response_body:
        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            source = parsed.get('error') if isinstance(parsed.get('error'), dict) else parsed
            fields = {
                key: source.get(key)
                for key in ('code', 'message', 'name')
                if source.get(key)
            }
    if 'code' not in fields and response_body:
        match = re.search(r'\berror code:\s*([A-Za-z0-9_-]+)', response_body, re.IGNORECASE)
        if match:
            fields['code'] = match.group(1)
    if 'message' not in fields and response_body:
        fields['message'] = _clip(response_body, 500)
    parts = [f'Resend HTTP {status_code}']
    for key in ('code', 'name', 'message'):
        if fields.get(key):
            parts.append(f'{key}={fields[key]}')
    return ' | '.join(parts)


def _send_resend(subject: str, body: str, cfg: EmailConfig, html: str | None = None) -> dict[str, Any]:
    payload = {
        'from': cfg.resend_from,
        'to': [cfg.recipient],
        'subject': subject,
        'text': body,
    }
    if html:
        payload['html'] = html
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        RESEND_ENDPOINT,
        data=data,
        method='POST',
        headers={
            'Authorization': f'Bearer {cfg.resend_api_key}',
            'Content-Type': 'application/json',
            'User-Agent': RESEND_USER_AGENT,
        },
    )
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            response_body = response.read().decode('utf-8', errors='replace')
            status_code = getattr(response, 'status', 0)
        if 200 <= status_code < 300:
            return {'sent': True, 'status': 'sent', 'error': '', 'provider': 'resend'}
        return {
            'sent': False,
            'status': 'send_failed',
            'error': _format_resend_error(status_code, response_body),
            'provider': 'resend',
        }
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode('utf-8', errors='replace')
        return {
            'sent': False,
            'status': 'send_failed',
            'error': _format_resend_error(exc.code, response_body),
            'provider': 'resend',
        }
    except Exception as exc:
        return {'sent': False, 'status': 'send_failed', 'error': str(exc), 'provider': 'resend'}


def _send_smtp(subject: str, body: str, cfg: EmailConfig) -> dict[str, Any]:
    sender = cfg.sender or cfg.user
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = cfg.recipient
    msg.set_content(body)
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg.host, cfg.port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(cfg.user, cfg.password)
            smtp.send_message(msg)
    except Exception as exc:
        return {'sent': False, 'status': 'send_failed', 'error': str(exc), 'provider': 'smtp'}
    return {'sent': True, 'status': 'sent', 'error': '', 'provider': 'smtp'}


def send_email(
    subject: str,
    body: str,
    cfg: EmailConfig | None = None,
    force: bool = False,
    html: str | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_config()
    if not cfg.enabled and not force:
        return {'sent': False, 'status': 'disabled', 'error': '', 'provider': cfg.provider}
    missing = _missing_provider_config(cfg)
    if missing:
        return {
            'sent': False,
            'status': 'missing_config',
            'error': f'Missing: {", ".join(missing)}',
            'provider': cfg.provider,
        }
    if cfg.provider == 'resend':
        return _send_resend(subject, body, cfg, html=html)
    return _send_smtp(subject, body, cfg)


def send_for_state(
    state: dict[str, Any],
    kind: str,
    force: bool = False,
    is_test: bool = False,
    html: str | None = None,
) -> dict[str, Any]:
    cfg     = load_config()
    subject = _subject(kind, state, is_test=is_test)
    body    = _body(kind, state, is_test=is_test)
    result  = send_email(subject, body, cfg, force=force, html=html)
    result['subject'] = subject
    result['kind']    = kind
    if result.get('sent'):
        result['sent_at'] = _utc_now()
    return result


def maybe_send_after_run(state: dict[str, Any]) -> dict[str, Any]:
    cfg = load_config()
    if not cfg.enabled:
        return {'last_email_status': 'disabled'}
    if state.get('last_run_mode') == 'dry-run':
        return {'last_email_status': 'skipped_dry_run'}

    run_status = state.get('last_run_status', '')
    new_alerts = int(state.get('last_new_count') or 0)
    today = _today_utc()
    kind  = ''

    if run_status in ('v12_error', 'v12_timeout'):
        kind = 'error'
    elif cfg.on_every_run:
        kind = 'summary'
    elif cfg.on_new_alerts and new_alerts > 0:
        kind = 'alerts'
    elif cfg.daily_digest and state.get('last_daily_digest_date') != today:
        kind = 'daily'
    else:
        return {'last_email_status': 'skipped_no_trigger'}

    result = send_for_state(state, kind, is_test=False)
    updates: dict[str, Any] = {
        'last_email_type':    kind,
        'last_email_status':  result.get('status', ''),
        'last_email_subject': result.get('subject', ''),
        'last_email_error':   result.get('error', ''),
    }
    if result.get('sent'):
        updates['last_email_sent_at'] = result.get('sent_at', _utc_now())
        if kind == 'daily':
            updates['last_daily_digest_date'] = today
    return updates


# ── State writer (email fields only) ─────────────────────────────────────────

def _write_email_state_only(result: dict[str, Any], kind: str) -> None:
    """Write only email-tracking fields to state. Never touches scanner run fields."""
    if not STATE_PATH.exists():
        return
    try:
        state = json.loads(STATE_PATH.read_text(encoding='utf-8'))
    except Exception:
        return
    state['last_email_type']    = kind
    state['last_email_status']  = result.get('status', '')
    state['last_email_subject'] = result.get('subject', '')
    state['last_email_error']   = result.get('error', '')
    if result.get('sent'):
        state['last_email_sent_at'] = result.get('sent_at', _utc_now())
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding='utf-8')


# ── Status printer ────────────────────────────────────────────────────────────

def _print_status() -> None:
    status = status_dict()
    print('MA Scanner Email Notifier Status')
    provider = status.get('email_provider', 'smtp')
    for key, value in status.items():
        if key.startswith('smtp_') and provider != 'smtp':
            continue
        print(f'  {key}: {value}')


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Live scanner email notifier')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--status',          action='store_true', help='Print config status without secrets')
    mode.add_argument('--test',            action='store_true', help='Send a test email (never corrupts scanner state)')
    mode.add_argument('--send-latest',     action='store_true', help='Send latest memo/status email now')
    mode.add_argument('--dry-run-preview', action='store_true', help='Print subject and body preview; do not send')
    args = parser.parse_args(argv)

    if args.status:
        _print_status()
        return 0

    # Load real state — never mutate it for test or preview sends
    state = _read_json(STATE_PATH)
    if not state:
        state = {
            'last_run':               _utc_now(),
            'last_run_status':        'unknown',
            'last_alert_count':       0,
            'last_new_count':         0,
            'last_investigate_count': 0,
            'last_watch_count':       0,
            'last_total_scanned':     0,
        }

    if args.dry_run_preview:
        subject = _subject('summary', state, is_test=False)
        body    = _body('summary', state, is_test=False)
        print(f'Subject: {subject}')
        print()
        print(body)
        return 0

    if args.test:
        # is_test=True adds [TEST] prefix and "Email type: TEST" note.
        # Real scanner state fields are NEVER overwritten.
        result = send_for_state(state, kind='test', force=True, is_test=True)
        _write_email_state_only(result, kind='test')
    else:
        # --send-latest
        result = send_for_state(state, kind='summary', force=True, is_test=False)
        _write_email_state_only(result, kind='summary')

    print(f'Email status : {result.get("status")}')
    print(f'Subject      : {result.get("subject")}')
    if result.get('error'):
        print(f'Error        : {result.get("error")}')
    return 0 if result.get('sent') else 1


if __name__ == '__main__':
    raise SystemExit(main())
