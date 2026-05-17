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


def _memo_top_cases(limit: int = 5) -> str:
    if not MEMO_PATH.exists():
        return 'Latest memo not found yet.'
    lines = MEMO_PATH.read_text(encoding='utf-8', errors='replace').splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        if line.startswith('## Top '):
            capture = True
            continue
        if capture and line.startswith('## '):
            break
        if capture and line.startswith('### '):
            out.append(line.replace('### ', '').strip())
            if len(out) >= limit:
                break
    if out:
        return '\n'.join(f'- {line}' for line in out)
    return 'No top cases listed in the latest memo.'


def _memo_summary(limit_chars: int = 3000) -> str:
    if not MEMO_PATH.exists():
        return 'Latest memo not found yet.'
    lines = MEMO_PATH.read_text(encoding='utf-8', errors='replace').splitlines()
    summary: list[str] = []
    capture = False
    for line in lines:
        if line.startswith('## Summary'):
            capture = True
        if capture:
            if line.startswith('## ') and summary and not line.startswith('## Summary'):
                break
            summary.append(line)
    return _clip('\n'.join(summary).strip() or '\n'.join(lines[:80]), limit_chars)


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
    recipient = os.environ.get('EMAIL_RECIPIENT', '').strip() or os.environ.get('SMTP_RECIPIENT', '').strip()
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
        'email_alerts_enabled': cfg.enabled,
        'email_provider': cfg.provider,
        'resend_api_key_set': bool(cfg.resend_api_key),
        'resend_from_set': bool(cfg.resend_from),
        'recipient_set': bool(cfg.recipient),
        'smtp_host_set': bool(cfg.host),
        'smtp_port': cfg.port,
        'smtp_user_set': bool(cfg.user),
        'smtp_password_set': bool(cfg.password),
        'smtp_recipient_set': bool(os.environ.get('SMTP_RECIPIENT', '').strip()),
        'smtp_from_set': bool(cfg.sender),
        'email_on_every_run': cfg.on_every_run,
        'email_on_new_alerts': cfg.on_new_alerts,
        'email_daily_digest': cfg.daily_digest,
        'last_email_status': state.get('last_email_status', ''),
        'last_email_sent_at': state.get('last_email_sent_at', ''),
        'last_email_subject': state.get('last_email_subject', ''),
        'last_daily_digest_date': state.get('last_daily_digest_date', ''),
        'env_file_exists': ENV_FILE.exists(),
    }


def _subject(kind: str, state: dict[str, Any]) -> str:
    status = state.get('last_run_status', 'unknown')
    total = int(state.get('last_alert_count') or 0)
    new = int(state.get('last_new_count') or 0)
    investigate = int(state.get('last_investigate_count') or 0)
    watch = int(state.get('last_watch_count') or 0)
    if kind == 'error' or status in {'v12_error', 'v12_timeout'}:
        return f'MA Scanner ERROR: {status}'
    if kind == 'daily':
        return f'MA Scanner Daily Digest: {total} alerts | status {status}'
    return f'MA Scanner: {new} new alerts | {investigate} investigate | {watch} watch'


def _body(kind: str, state: dict[str, Any]) -> str:
    lines = [
        'MA Scanner Live Monitor',
        '',
        f'Scan timestamp: {state.get("last_run", "")}',
        f'Run status: {state.get("last_run_status", "")}',
        f'Raw names scanned: {state.get("last_total_scanned", "")}',
        f'Total alerts: {state.get("last_alert_count", 0)}',
        f'New alerts: {state.get("last_new_count", 0)}',
        f'Investigate count: {state.get("last_investigate_count", 0)}',
        f'Watch count: {state.get("last_watch_count", 0)}',
        f'V12 elapsed seconds: {state.get("last_v12_elapsed_sec", "")}',
        '',
        f'Latest memo path: {MEMO_PATH}',
        f'Alert log path: {ALERT_LOG}',
        f'Error log path: {ERROR_LOG}',
        '',
        'Health / status:',
        f'- last_run_status: {state.get("last_run_status", "")}',
        f'- last_error: {state.get("last_error", "") or "none"}',
        '',
        'Top cases:',
        _memo_top_cases(limit=5),
        '',
        'Memo summary:',
        _memo_summary(),
        '',
        'Reminder: research monitoring only. This is not investment advice.',
    ]
    return '\n'.join(lines)


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


def _send_resend(subject: str, body: str, cfg: EmailConfig) -> dict[str, Any]:
    payload = {
        'from': cfg.resend_from,
        'to': [cfg.recipient],
        'subject': subject,
        'text': body,
    }
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        RESEND_ENDPOINT,
        data=data,
        method='POST',
        headers={
            'Authorization': f'Bearer {cfg.resend_api_key}',
            'Content-Type': 'application/json',
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
            'error': f'Resend HTTP {status_code}: {_clip(response_body, 500)}',
            'provider': 'resend',
        }
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode('utf-8', errors='replace')
        return {
            'sent': False,
            'status': 'send_failed',
            'error': f'Resend HTTP {exc.code}: {_clip(response_body, 500)}',
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


def send_email(subject: str, body: str, cfg: EmailConfig | None = None, force: bool = False) -> dict[str, Any]:
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
        return _send_resend(subject, body, cfg)
    return _send_smtp(subject, body, cfg)


def send_for_state(state: dict[str, Any], kind: str, force: bool = False) -> dict[str, Any]:
    cfg = load_config()
    subject = _subject(kind, state)
    body = _body(kind, state)
    result = send_email(subject, body, cfg, force=force)
    result['subject'] = subject
    result['kind'] = kind
    if result.get('sent'):
        result['sent_at'] = _utc_now()
    return result


def maybe_send_after_run(state: dict[str, Any]) -> dict[str, Any]:
    cfg = load_config()
    if not cfg.enabled:
        return {'last_email_status': 'disabled'}
    if state.get('last_run_mode') == 'dry-run':
        return {'last_email_status': 'skipped_dry_run'}

    status = state.get('last_run_status', '')
    new_alerts = int(state.get('last_new_count') or 0)
    today = _today_utc()
    kind = ''

    if status in {'v12_error', 'v12_timeout'}:
        kind = 'error'
    elif cfg.on_every_run:
        kind = 'summary'
    elif cfg.on_new_alerts and new_alerts > 0:
        kind = 'alerts'
    elif cfg.daily_digest and state.get('last_daily_digest_date') != today:
        kind = 'daily'
    else:
        return {'last_email_status': 'skipped_no_trigger'}

    result = send_for_state(state, kind)
    updates = {
        'last_email_status': result.get('status', ''),
        'last_email_subject': result.get('subject', ''),
        'last_email_error': result.get('error', ''),
    }
    if result.get('sent'):
        updates['last_email_sent_at'] = result.get('sent_at', _utc_now())
        if kind == 'daily':
            updates['last_daily_digest_date'] = today
    return updates


def _print_status() -> None:
    status = status_dict()
    print('MA Scanner Email Notifier Status')
    provider = status.get('email_provider', 'smtp')
    for key, value in status.items():
        if key.startswith('smtp_') and provider != 'smtp':
            continue
        if key == 'smtp_password_set':
            print(f'  {key}: {bool(value)}')
        else:
            print(f'  {key}: {value}')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Live scanner email notifier')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--status', action='store_true', help='Print email configuration status without secrets')
    mode.add_argument('--test', action='store_true', help='Send a test email using configured SMTP settings')
    mode.add_argument('--send-latest', action='store_true', help='Send the latest memo/status email now')
    args = parser.parse_args(argv)

    if args.status:
        _print_status()
        return 0

    state = _read_json(STATE_PATH)
    if not state:
        state = {
            'last_run': _utc_now(),
            'last_run_status': 'manual_test',
            'last_alert_count': 0,
            'last_new_count': 0,
            'last_investigate_count': 0,
            'last_watch_count': 0,
        }

    kind = 'test' if args.test else 'summary'
    if args.test:
        state = dict(state)
        state['last_run_status'] = 'test_email'

    result = send_for_state(state, kind, force=args.test or args.send_latest)
    print(f'Email status: {result.get("status")}')
    print(f'Subject: {result.get("subject")}')
    if result.get('error'):
        print(f'Error: {result.get("error")}')
    return 0 if result.get('sent') else 1


if __name__ == '__main__':
    raise SystemExit(main())
