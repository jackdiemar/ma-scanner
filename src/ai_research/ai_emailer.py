"""
ai_emailer.py — Branded HTML email delivery for AI research briefs.

Sends via the existing Resend or SMTP configuration in config/.env.
Completely separate from the live scanner alert emails.

Environment variables (read from config/.env):
  AI_EMAILS_ENABLED              true/false (default false)
  AI_EMAIL_ON_EVERY_RUN          true/false (default false)
  AI_EMAIL_SUBJECT_PREFIX        string (default "MA Scanner AI Research Brief")
  EMAIL_PROVIDER                 resend | smtp
  RESEND_API_KEY
  RESEND_FROM                    alerts@blackstarlightcapital.com
  EMAIL_RECIPIENT

This email is for internal research monitoring only. It is not investment
advice and does not constitute a recommendation to buy, sell, or hold any security.
"""
from __future__ import annotations

import json
import os
import smtplib
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

ENV_FILE     = REPO / 'config' / '.env'
SUMMARY_PATH = REPO / 'data' / 'ai_research' / 'latest_ai_research_summary.md'

RESEND_ENDPOINT   = 'https://api.resend.com/emails'
RESEND_USER_AGENT = 'ma-scanner-ai-research/1.0'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_env() -> None:
    if not ENV_FILE.exists():
        return
    with ENV_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None or value == '':
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def _esc(text: str) -> str:
    """HTML-escape a string for safe inline use."""
    return (
        str(text)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


# ── Config ────────────────────────────────────────────────────────────────────

def load_ai_email_config() -> dict:
    """
    Load AI email settings from environment (after loading .env).
    Returns a plain dict — avoids import coupling with email_notifier.
    """
    _load_env()
    provider = os.environ.get('EMAIL_PROVIDER', 'resend').strip().lower() or 'resend'
    if provider not in {'smtp', 'resend'}:
        provider = 'resend'

    port_raw = os.environ.get('SMTP_PORT', '587').strip() or '587'
    try:
        smtp_port = int(port_raw)
    except ValueError:
        smtp_port = 587

    recipient = (
        os.environ.get('EMAIL_RECIPIENT', '').strip()
        or os.environ.get('SMTP_RECIPIENT', '').strip()
    )

    return {
        'enabled':         _truthy(os.environ.get('AI_EMAILS_ENABLED'), default=False),
        'on_every_run':    _truthy(os.environ.get('AI_EMAIL_ON_EVERY_RUN'), default=False),
        'subject_prefix':  os.environ.get('AI_EMAIL_SUBJECT_PREFIX', 'MA Scanner AI Research Brief').strip()
                           or 'MA Scanner AI Research Brief',
        'provider':        provider,
        'resend_api_key':  os.environ.get('RESEND_API_KEY', '').strip(),
        'resend_from':     os.environ.get('RESEND_FROM', '').strip(),
        'recipient':       recipient,
        'smtp_host':       os.environ.get('SMTP_HOST', '').strip(),
        'smtp_port':       smtp_port,
        'smtp_user':       os.environ.get('SMTP_USER', '').strip(),
        'smtp_password':   os.environ.get('SMTP_PASSWORD', ''),
        'smtp_from':       os.environ.get('SMTP_FROM', '').strip(),
    }


# ── Subject builder ───────────────────────────────────────────────────────────

def build_ai_email_subject(decisions: list[dict], prefix: str) -> str:
    """
    Build a descriptive subject line from the decision counts.

    Example: "MA Scanner AI Research Brief — 2 ESCALATE / 3 WATCH / 5 DISCARD"
    """
    escalate = sum(1 for d in decisions if d.get('research_action') == 'ESCALATE')
    watch    = sum(1 for d in decisions if d.get('research_action') in ('WATCH', 'WAIT_FOR_PRICE', 'WATCH_ONLY'))
    discard  = sum(1 for d in decisions if d.get('research_action') == 'DISCARD')
    review   = sum(1 for d in decisions if d.get('research_action') == 'NEEDS_HUMAN_REVIEW')

    parts: list[str] = []
    if escalate:
        parts.append(f'{escalate} ESCALATE')
    if watch:
        parts.append(f'{watch} WATCH')
    if discard:
        parts.append(f'{discard} DISCARD')
    if review:
        parts.append(f'{review} REVIEW')

    suffix = ' / '.join(parts) if parts else f'{len(decisions)} cases'
    return f'{prefix} — {suffix}'


# ── HTML builder ──────────────────────────────────────────────────────────────

# Decision badge colors (inline CSS)
_BADGE_STYLES: dict[str, str] = {
    'ESCALATE':          'background:#dc2626;color:#fff',
    'WATCH':             'background:#d97706;color:#fff',
    'WAIT_FOR_PRICE':    'background:#2563eb;color:#fff',
    'DISCARD':           'background:#374151;color:#9ca3af',
    'NEEDS_HUMAN_REVIEW': 'background:#7c3aed;color:#fff',
    'WATCH_ONLY':        'background:#92400e;color:#fde68a',
}

_ACTION_LABEL: dict[str, str] = {
    'ESCALATE':          'ESCALATE',
    'WATCH':             'WATCH',
    'WAIT_FOR_PRICE':    'WAIT FOR PRICE',
    'DISCARD':           'DISCARD',
    'NEEDS_HUMAN_REVIEW': 'HUMAN REVIEW',
    'WATCH_ONLY':        'WATCH ONLY',
}


def _badge_html(action: str, label: str | None = None) -> str:
    style = _BADGE_STYLES.get(action, 'background:#374151;color:#9ca3af')
    text  = label or _ACTION_LABEL.get(action, action)
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'font-size:11px;font-weight:700;letter-spacing:0.05em;{style}">'
        f'{_esc(text)}</span>'
    )


_EVIDENCE_GRADE_STYLES: dict[str, str] = {
    'A': 'background:#166534;color:#bbf7d0',  # green
    'B': 'background:#1e3a5f;color:#93c5fd',  # blue
    'C': 'background:#713f12;color:#fde68a',  # amber
    'D': 'background:#7f1d1d;color:#fca5a5',  # red-dim
    'F': 'background:#1c1917;color:#78716c',  # stone
}


def _evidence_badge_html(grade: str) -> str:
    style = _EVIDENCE_GRADE_STYLES.get(grade.upper(), _EVIDENCE_GRADE_STYLES['F'])
    return (
        f'<span style="display:inline-block;padding:2px 6px;border-radius:4px;'
        f'font-size:10px;font-weight:700;letter-spacing:0.08em;{style}">'
        f'EVIDENCE {_esc(grade.upper())}</span>'
    )


def _score_bar(score: int, label: str) -> str:
    """Compact score bar for strategy scores."""
    if not score:
        return ''
    color = '#16a34a' if score >= 60 else ('#d97706' if score >= 35 else '#dc2626')
    return (
        f'<span style="font-size:10px;color:#64748b;">{_esc(label)}: </span>'
        f'<span style="font-size:10px;font-weight:700;color:{color};">{score}</span>'
    )


def _card_html(d: dict, strategic_brief: bool = False) -> str:
    ticker       = _esc(d.get('ticker', '?'))
    company      = _esc(d.get('company_name', ''))
    cls          = d.get('classification', '')
    action       = d.get('research_action', '')
    confidence   = d.get('confidence', 0.0)
    score        = d.get('investability_score', 0)
    short_thesis = d.get('short_thesis', '')
    evidence_sum = d.get('evidence_summary', '')
    key_reasons  = d.get('key_reasons', []) or []
    op_steps     = d.get('operator_next_steps', []) or []
    discard_r    = d.get('discard_reason', '')
    escalation_r = d.get('escalation_reason', '')
    human_r      = d.get('human_review_reason', '')
    change_dec   = d.get('what_would_change_the_decision', '')
    ev_grade     = str(d.get('evidence_grade', 'F')).strip().upper() or 'F'
    ev_gaps      = d.get('evidence_gaps', []) or []

    # Strategy fields
    bucket       = d.get('strategy_bucket', '')
    analogue     = d.get('historical_analogue', '')
    ts_archetypes = d.get('matched_true_signal_archetypes', []) or []
    fp_archetypes = d.get('matched_false_positive_archetypes', []) or []
    why_fired    = d.get('why_this_fired', '')
    mdvn_compare = d.get('how_it_compares_to_mdvn_dmtx_tsro', '')
    kill_crit    = d.get('kill_criteria', '')
    escalation_crit = d.get('escalation_criteria', '')
    monitoring   = d.get('monitoring_plan', '')

    company_score  = d.get('company_level_process_score', 0)
    fp_score       = d.get('false_positive_similarity_score', 0)
    timing_score   = d.get('timing_edge_score', 0)
    process_score  = d.get('process_specificity_score', 0)

    action_note = escalation_r or discard_r or human_r

    header_name = ticker
    if company and company != ticker:
        header_name += f' — {company}'

    html = (
        f'<div style="background:#1a2035;border-radius:8px;margin:12px 0;padding:16px;">'
        # Card header
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap;">'
        f'<span style="font-size:16px;font-weight:700;color:#e2e8f0;">{header_name}</span>'
        f'{_badge_html(action)}'
        f'{_evidence_badge_html(ev_grade)}'
        f'<span style="font-size:11px;color:#64748b;margin-left:4px;">{_esc(cls)}</span>'
        f'</div>'
        # Confidence + score row
        f'<div style="font-size:12px;color:#94a3b8;margin-bottom:6px;">'
        f'Confidence: <strong style="color:#cbd5e1;">{int(confidence * 100)}%</strong>'
        f' &nbsp;|&nbsp; Score: <strong style="color:#cbd5e1;">{score}/100</strong>'
        f'</div>'
    )

    # Strategy bucket + analogue (strategic brief only)
    if strategic_brief and (bucket or analogue):
        html += (
            f'<div style="font-size:11px;color:#64748b;margin-bottom:8px;">'
        )
        if bucket:
            html += f'Bucket: <span style="color:#94a3b8;">{_esc(bucket)}</span>'
        if analogue:
            html += f'&nbsp; Analogue: <span style="color:#94a3b8;">{_esc(analogue[:80])}</span>'
        html += '</div>'

    # Strategy score row (strategic brief only)
    if strategic_brief and any([company_score, fp_score, timing_score, process_score]):
        scores_html = '&nbsp;&nbsp;'.join(filter(None, [
            _score_bar(company_score, 'company'),
            _score_bar(process_score, 'process'),
            _score_bar(timing_score, 'timing'),
            _score_bar(fp_score, 'fp-risk') if fp_score else '',
        ]))
        if scores_html:
            html += (
                f'<div style="margin-bottom:8px;">{scores_html}</div>'
            )

    # FP/TS archetype tags (strategic brief only)
    if strategic_brief and fp_archetypes:
        tags = ' '.join(
            f'<span style="display:inline-block;padding:1px 6px;border-radius:3px;'
            f'font-size:10px;background:#374151;color:#9ca3af;margin:2px;">'
            f'{_esc(fp)}</span>'
            for fp in fp_archetypes[:4]
        )
        html += f'<div style="margin-bottom:8px;">{tags}</div>'

    if strategic_brief and ts_archetypes:
        tags = ' '.join(
            f'<span style="display:inline-block;padding:1px 6px;border-radius:3px;'
            f'font-size:10px;background:#166534;color:#bbf7d0;margin:2px;">'
            f'{_esc(ts)}</span>'
            for ts in ts_archetypes[:3]
        )
        html += f'<div style="margin-bottom:8px;">{tags}</div>'

    # Evidence gaps warning (show only if D or F)
    if ev_grade in ('D', 'F') and ev_gaps:
        gaps_text = ' · '.join(_esc(g) for g in ev_gaps[:4])
        html += (
            f'<div style="background:#1c1917;border-left:3px solid #78716c;'
            f'padding:6px 10px;border-radius:4px;margin-bottom:10px;">'
            f'<span style="font-size:10px;color:#78716c;text-transform:uppercase;'
            f'letter-spacing:0.08em;">Evidence gaps</span><br>'
            f'<span style="font-size:11px;color:#a8a29e;">{gaps_text}</span>'
            f'</div>'
        )

    # Why this fired (strategic brief only)
    if strategic_brief and why_fired:
        html += (
            f'<div style="background:#0f1117;border-left:3px solid #1e3a5f;'
            f'padding:6px 10px;border-radius:4px;margin-bottom:8px;">'
            f'<span style="font-size:10px;color:#4a7fbf;text-transform:uppercase;'
            f'letter-spacing:0.08em;">Why this fired</span><br>'
            f'<span style="font-size:11px;color:#94a3b8;">{_esc(why_fired[:300])}</span>'
            f'</div>'
        )

    # Short thesis
    if short_thesis:
        html += (
            f'<p style="font-size:13px;color:#cbd5e1;margin:0 0 10px 0;line-height:1.5;">'
            f'{_esc(short_thesis)}</p>'
        )

    # Evidence summary
    if evidence_sum:
        html += (
            f'<div style="background:#0f1117;border-left:3px solid #334155;'
            f'padding:8px 12px;border-radius:4px;margin-bottom:10px;">'
            f'<span style="font-size:11px;color:#64748b;text-transform:uppercase;'
            f'letter-spacing:0.08em;">Evidence</span><br>'
            f'<span style="font-size:12px;color:#94a3b8;line-height:1.5;">'
            f'{_esc(evidence_sum[:400])}</span>'
            f'</div>'
        )

    # MDVN/DMTX/TSRO comparison (strategic brief only)
    if strategic_brief and mdvn_compare:
        html += (
            f'<div style="background:#0f1117;border-left:3px solid #3f3f3f;'
            f'padding:6px 10px;border-radius:4px;margin-bottom:8px;">'
            f'<span style="font-size:10px;color:#64748b;text-transform:uppercase;'
            f'letter-spacing:0.08em;">vs MDVN / DMTX / TSRO</span><br>'
            f'<span style="font-size:11px;color:#94a3b8;">{_esc(mdvn_compare[:400])}</span>'
            f'</div>'
        )

    # Key reasons
    if key_reasons:
        html += (
            f'<div style="margin-bottom:10px;">'
            f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:4px;">Key Reasons</div>'
            f'<ul style="margin:0;padding-left:16px;">'
        )
        for reason in key_reasons:
            html += (
                f'<li style="font-size:12px;color:#94a3b8;line-height:1.6;">'
                f'{_esc(str(reason))}</li>'
            )
        html += '</ul></div>'

    # Operator next steps
    if op_steps:
        html += (
            f'<div style="margin-bottom:10px;">'
            f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:4px;">Next Steps</div>'
            f'<ol style="margin:0;padding-left:16px;">'
        )
        for step in op_steps:
            html += (
                f'<li style="font-size:12px;color:#94a3b8;line-height:1.6;">'
                f'{_esc(str(step))}</li>'
            )
        html += '</ol></div>'

    # Action-specific note
    if action_note:
        html += (
            f'<div style="font-size:12px;color:#f59e0b;margin-bottom:8px;">'
            f'{_esc(action_note[:300])}</div>'
        )

    # Kill / escalation criteria (strategic brief only)
    if strategic_brief:
        if kill_crit:
            html += (
                f'<div style="font-size:11px;color:#475569;margin-top:4px;">'
                f'Kill: {_esc(kill_crit[:200])}</div>'
            )
        if escalation_crit:
            html += (
                f'<div style="font-size:11px;color:#475569;margin-top:4px;">'
                f'Escalate if: {_esc(escalation_crit[:200])}</div>'
            )
        if monitoring:
            html += (
                f'<div style="font-size:11px;color:#475569;margin-top:4px;">'
                f'Monitor: {_esc(monitoring[:200])}</div>'
            )

    # What would change the decision
    if change_dec:
        html += (
            f'<div style="font-size:11px;color:#475569;font-style:italic;margin-top:8px;">'
            f'Would change if: {_esc(change_dec[:200])}</div>'
        )

    html += '</div>'
    return html


def build_ai_email_html(
    decisions: list[dict],
    run_metadata: dict,
    strategic_brief: bool = False,
) -> str:
    """
    Build the full branded HTML email body. Uses inline styles throughout —
    email clients strip <style> blocks.
    """
    run_at    = _esc(run_metadata.get('run_at', _utc_now()))
    model     = _esc(run_metadata.get('model', 'unknown'))
    case_count = int(run_metadata.get('case_count', len(decisions)))
    cache_hits = int(run_metadata.get('cache_hits', 0))
    ai_enabled = run_metadata.get('ai_enabled', False)
    dry_run    = run_metadata.get('dry_run', False)

    # Count by action
    escalate   = sum(1 for d in decisions if d.get('research_action') == 'ESCALATE')
    watch      = sum(1 for d in decisions if d.get('research_action') in ('WATCH', 'WAIT_FOR_PRICE'))
    discard    = sum(1 for d in decisions if d.get('research_action') == 'DISCARD')
    review     = sum(1 for d in decisions if d.get('research_action') == 'NEEDS_HUMAN_REVIEW')
    watch_only = sum(1 for d in decisions if d.get('research_action') == 'WATCH_ONLY')

    # Strategy analysis (strategic brief only)
    fp_counts: dict[str, int] = {}
    ts_candidates: list[str] = []
    already_announced = 0
    for d in decisions:
        for fp in (d.get('matched_false_positive_archetypes', []) or []):
            fp_counts[fp] = fp_counts.get(fp, 0) + 1
        if (d.get('matched_true_signal_archetypes')
                and d.get('research_action') not in ('DISCARD',)):
            ts_candidates.append(d.get('ticker', '?'))
        if 'ALREADY_ANNOUNCED_MERGER' in (d.get('matched_false_positive_archetypes', []) or []):
            already_announced += 1

    dominant_fp = max(fp_counts, key=lambda k: fp_counts[k]) if fp_counts else None

    cards_html = ''.join(
        _card_html(d, strategic_brief=strategic_brief) for d in decisions
    ) if decisions else (
        '<p style="color:#64748b;font-size:13px;">No decisions were made this run.</p>'
    )

    dry_run_banner = ''
    if dry_run:
        dry_run_banner = (
            '<div style="background:#1e293b;border:1px solid #f59e0b;border-radius:6px;'
            'padding:10px 14px;margin-bottom:16px;">'
            '<span style="color:#f59e0b;font-size:12px;font-weight:600;">DRY RUN — LLM was not called. '
            'Decisions shown are placeholders.</span></div>'
        )

    # Strategy summary section (strategic brief only)
    strategy_summary_html = ''
    if strategic_brief and decisions:
        if escalate == 0 and not ts_candidates:
            strategy_read = (
                f'Run reviewed {case_count} alerts. '
                f'No MDVN/DMTX/TSRO-like signal detected. '
                + (f'Dominant false-positive pattern: {_esc(dominant_fp)}. '
                   if dominant_fp else '')
                + 'Source-backed evidence shows no open company-level strategic process in this batch. '
                'False positives filtered correctly. Continue monitoring for new process filings.'
            )
        elif escalate > 0:
            strategy_read = (
                f'{escalate} alert(s) escalated for immediate review. '
                + (f'True-signal candidates: {_esc(", ".join(ts_candidates))}. '
                   if ts_candidates else '')
                + 'Verify source filings and corroborate with independent news sources before acting.'
            )
        else:
            strategy_read = (
                f'Partial signal(s) detected but insufficient for ESCALATE. '
                + (f'True-signal candidates: {_esc(", ".join(ts_candidates))}. '
                   if ts_candidates else '')
                + 'Monitor for follow-on filings.'
            )

        dominant_fp_html = (
            f'<div style="font-size:11px;color:#64748b;margin-top:4px;">'
            f'Dominant FP: <span style="color:#94a3b8;">{_esc(dominant_fp)}</span>'
            f' ({fp_counts.get(dominant_fp, 0)} of {len(decisions)} cases)</div>'
        ) if dominant_fp else ''

        ts_html = (
            f'<div style="font-size:11px;color:#16a34a;margin-top:4px;">'
            f'True-signal candidates: {_esc(", ".join(ts_candidates))}</div>'
        ) if ts_candidates else ''

        strategy_summary_html = (
            f'<div style="background:#111827;border:1px solid #1f2937;border-radius:6px;'
            f'padding:14px 16px;margin-bottom:16px;">'
            f'<div style="font-size:11px;color:#c9a84c;text-transform:uppercase;'
            f'letter-spacing:0.1em;margin-bottom:8px;">Strategy Read</div>'
            f'<p style="font-size:12px;color:#94a3b8;line-height:1.6;margin:0 0 8px 0;">'
            f'{strategy_read}</p>'
            f'{dominant_fp_html}{ts_html}'
            f'</div>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>MA Scanner AI Research Brief</title>
</head>
<body style="margin:0;padding:0;background:#0f1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;min-height:100vh;">
<tr><td align="center" style="padding:20px 0;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

<!-- HEADER -->
<tr><td style="background:#0f1117;border-bottom:2px solid #c9a84c;padding:20px 24px 16px 24px;">
  <div style="font-size:18px;font-weight:700;color:#c9a84c;letter-spacing:0.15em;text-transform:uppercase;">
    Black Starlight Capital
  </div>
  <div style="font-size:13px;color:#94a3b8;margin-top:4px;letter-spacing:0.04em;">
    MA Scanner — AI Research Brief
  </div>
</td></tr>

<!-- RUN METADATA -->
<tr><td style="background:#111827;padding:12px 24px;border-bottom:1px solid #1f2937;">
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="font-size:11px;color:#64748b;">Run: <span style="color:#94a3b8;">{run_at}</span></td>
    <td style="font-size:11px;color:#64748b;text-align:right;">Model: <span style="color:#94a3b8;">{model}</span></td>
  </tr>
  <tr>
    <td style="font-size:11px;color:#64748b;padding-top:2px;">Cases: <span style="color:#94a3b8;">{case_count}</span></td>
    <td style="font-size:11px;color:#64748b;text-align:right;padding-top:2px;">Cache hits: <span style="color:#94a3b8;">{cache_hits}</span></td>
  </tr>
  </table>
</td></tr>

<!-- STATS BAR -->
<tr><td style="background:#111827;padding:12px 24px 16px 24px;border-bottom:1px solid #1f2937;">
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    {_badge_html('ESCALATE', f'{escalate} ESCALATE') if escalate else ''}
    {_badge_html('WATCH', f'{watch} WATCH') if watch else ''}
    {_badge_html('WATCH_ONLY', f'{watch_only} WATCH ONLY') if watch_only else ''}
    {_badge_html('NEEDS_HUMAN_REVIEW', f'{review} REVIEW') if review else ''}
    {_badge_html('DISCARD', f'{discard} DISCARD') if discard else ''}
  </div>
</td></tr>

<!-- BODY -->
<tr><td style="padding:16px 24px;">
  {dry_run_banner}
  {strategy_summary_html}
  {cards_html}
</td></tr>

<!-- FOOTER -->
<tr><td style="padding:16px 24px 24px 24px;border-top:1px solid #1f2937;">
  <p style="font-size:11px;color:#475569;line-height:1.6;margin:0;">
    This email is for internal research monitoring only. It is not investment advice and does not
    constitute a recommendation to buy, sell, or hold any security. All classifications are generated
    by an automated AI research layer and require human analyst review before any action is taken.
  </p>
  <p style="font-size:10px;color:#374151;margin:8px 0 0 0;">
    Black Starlight Capital — MA Scanner AI Research Layer
  </p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""
    return html


# ── Plain text builder ────────────────────────────────────────────────────────

def build_ai_email_plain(
    decisions: list[dict],
    run_metadata: dict,
    strategic_brief: bool = False,
) -> str:
    """Plain text fallback. Clean and readable."""
    run_at     = run_metadata.get('run_at', _utc_now())
    model      = run_metadata.get('model', 'unknown')
    case_count = run_metadata.get('case_count', len(decisions))
    dry_run    = run_metadata.get('dry_run', False)

    lines: list[str] = [
        'BLACK STARLIGHT CAPITAL',
        'MA Scanner — AI Research Brief',
        '=' * 48,
        f'Run: {run_at}',
        f'Model: {model}',
        f'Cases reviewed: {case_count}',
        f'Dry run: {dry_run}',
        '',
    ]

    if decisions:
        # Decision distribution
        counts: dict[str, int] = {}
        for d in decisions:
            a = d.get('research_action', '?')
            counts[a] = counts.get(a, 0) + 1
        lines.append('Decision distribution:')
        for a, c in sorted(counts.items()):
            lines.append(f'  {a}: {c}')
        lines.append('')

        # FP summary if strategic
        if strategic_brief:
            fp_all: dict[str, int] = {}
            for d in decisions:
                for fp in (d.get('matched_false_positive_archetypes', []) or []):
                    fp_all[fp] = fp_all.get(fp, 0) + 1
            if fp_all:
                dominant = max(fp_all, key=lambda k: fp_all[k])
                lines.append(f'Dominant false-positive pattern: {dominant}')
                lines.append('')

        for d in decisions:
            ticker       = d.get('ticker', '?')
            cls          = d.get('classification', '?')
            action       = d.get('research_action', '?')
            confidence   = d.get('confidence', 0.0)
            ev_grade     = d.get('evidence_grade', 'F')
            short_thesis = d.get('short_thesis', '')
            key_reasons  = d.get('key_reasons', []) or []
            op_steps     = d.get('operator_next_steps', []) or []
            bucket       = d.get('strategy_bucket', '')
            analogue     = d.get('historical_analogue', '')
            why_fired    = d.get('why_this_fired', '')
            mdvn_cmp     = d.get('how_it_compares_to_mdvn_dmtx_tsro', '')
            kill_crit    = d.get('kill_criteria', '')

            lines.append(f'── {ticker} ──')
            lines.append(f'Classification : {cls}')
            lines.append(f'Action         : {action}')
            lines.append(f'Confidence     : {int(confidence * 100)}%')
            lines.append(f'Evidence grade : {ev_grade}')

            if bucket:
                lines.append(f'Strategy bucket: {bucket}')
            if analogue:
                lines.append(f'Analogue       : {analogue[:100]}')

            if short_thesis:
                lines.append(f'Thesis         : {short_thesis}')

            if strategic_brief and why_fired:
                lines.append(f'Why fired      : {why_fired}')

            if key_reasons:
                lines.append('Reasons:')
                for r in key_reasons:
                    lines.append(f'  - {r}')

            if op_steps:
                lines.append('Next steps:')
                for i, s in enumerate(op_steps, 1):
                    lines.append(f'  {i}. {s}')

            if strategic_brief and mdvn_cmp:
                lines.append(f'vs MDVN/DMTX/TSRO: {mdvn_cmp[:300]}')

            if strategic_brief and kill_crit:
                lines.append(f'Kill criteria  : {kill_crit}')

            lines.append('')
    else:
        lines.append('No decisions were made this run.')
        lines.append('')

    lines += [
        '─' * 48,
        'This email is for internal research monitoring only.',
        'It is not investment advice and does not constitute a recommendation',
        'to buy, sell, or hold any security.',
    ]

    return '\n'.join(lines)


# ── Send infrastructure ───────────────────────────────────────────────────────

def _send_resend_html(
    subject: str,
    body_text: str,
    body_html: str,
    cfg: dict,
) -> dict[str, Any]:
    """Send via Resend API with both HTML and plain text bodies."""
    payload = {
        'from':    cfg['resend_from'],
        'to':      [cfg['recipient']],
        'subject': subject,
        'text':    body_text,
        'html':    body_html,
    }
    data    = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(
        RESEND_ENDPOINT,
        data=data,
        method='POST',
        headers={
            'Authorization': f'Bearer {cfg["resend_api_key"]}',
            'Content-Type':  'application/json',
            'User-Agent':    RESEND_USER_AGENT,
        },
    )
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            response_body = response.read().decode('utf-8', errors='replace')
            status_code   = getattr(response, 'status', 0)
        if 200 <= status_code < 300:
            return {'sent': True, 'status': 'sent', 'error': '', 'provider': 'resend'}
        return {
            'sent': False, 'status': 'send_failed',
            'error': f'Resend HTTP {status_code}: {response_body[:300]}',
            'provider': 'resend',
        }
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode('utf-8', errors='replace')
        return {
            'sent': False, 'status': 'send_failed',
            'error': f'Resend HTTP {exc.code}: {response_body[:300]}',
            'provider': 'resend',
        }
    except Exception as exc:
        return {'sent': False, 'status': 'send_failed', 'error': str(exc), 'provider': 'resend'}


def _send_smtp_html(
    subject: str,
    body_text: str,
    body_html: str,
    cfg: dict,
) -> dict[str, Any]:
    """SMTP fallback with plain text only (HTML via MIME not yet wired)."""
    from_addr = cfg.get('smtp_from') or cfg.get('smtp_user', '')
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From']    = from_addr
    msg['To']      = cfg['recipient']
    msg.set_content(body_text)
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port'], timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(cfg['smtp_user'], cfg['smtp_password'])
            smtp.send_message(msg)
    except Exception as exc:
        return {'sent': False, 'status': 'send_failed', 'error': str(exc), 'provider': 'smtp'}
    return {'sent': True, 'status': 'sent', 'error': '', 'provider': 'smtp'}


def _check_send_config(cfg: dict) -> list[str]:
    """Return list of missing config items, empty if all good."""
    provider = cfg.get('provider', 'resend')
    if provider == 'resend':
        missing = []
        if not cfg.get('resend_api_key'):
            missing.append('RESEND_API_KEY')
        if not cfg.get('resend_from'):
            missing.append('RESEND_FROM')
        if not cfg.get('recipient'):
            missing.append('EMAIL_RECIPIENT')
        return missing
    # SMTP
    missing = []
    if not cfg.get('smtp_host'):
        missing.append('SMTP_HOST')
    if not cfg.get('smtp_user'):
        missing.append('SMTP_USER')
    if not cfg.get('smtp_password'):
        missing.append('SMTP_PASSWORD')
    if not cfg.get('recipient'):
        missing.append('SMTP_RECIPIENT or EMAIL_RECIPIENT')
    return missing


# ── Public send API ───────────────────────────────────────────────────────────

def send_ai_research_email(
    decisions: list[dict],
    run_metadata: dict,
    force: bool = False,
    strategic_brief: bool = False,
) -> dict[str, Any]:
    """
    Build and send the branded AI research email.

    Returns: {sent, status, error, subject, provider}
    """
    cfg = load_ai_email_config()

    if not cfg['enabled'] and not force:
        print('  [AI EMAIL] Skipped — AI_EMAILS_ENABLED=false (use force=True to override)')
        return {'sent': False, 'status': 'disabled', 'error': '', 'subject': ''}

    missing = _check_send_config(cfg)
    if missing:
        msg = f'Missing: {", ".join(missing)}'
        print(f'  [AI EMAIL] Cannot send — {msg}')
        return {'sent': False, 'status': 'missing_config', 'error': msg, 'subject': ''}

    subject    = build_ai_email_subject(decisions, cfg['subject_prefix'])
    body_html  = build_ai_email_html(decisions, run_metadata, strategic_brief=strategic_brief)
    body_plain = build_ai_email_plain(decisions, run_metadata, strategic_brief=strategic_brief)

    if cfg['provider'] == 'resend':
        result = _send_resend_html(subject, body_plain, body_html, cfg)
    else:
        result = _send_smtp_html(subject, body_plain, body_html, cfg)

    result['subject'] = subject
    if result.get('sent'):
        print(f'  [AI EMAIL] Sent: {subject}')
    else:
        print(f'  [AI EMAIL] Failed: {result.get("error", "")}')
    return result


def send_latest_summary_email(
    summary_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Read the latest AI research summary markdown and send it as a plain text email.
    This is the --email-latest-summary path.
    """
    cfg = load_ai_email_config()
    path = summary_path or SUMMARY_PATH

    if not cfg['enabled'] and not force:
        print('  [AI EMAIL] Skipped — AI_EMAILS_ENABLED=false')
        return {'sent': False, 'status': 'disabled', 'error': '', 'subject': ''}

    if not path.exists():
        msg = f'Summary file not found: {path}'
        print(f'  [AI EMAIL] {msg}')
        return {'sent': False, 'status': 'file_not_found', 'error': msg, 'subject': ''}

    missing = _check_send_config(cfg)
    if missing:
        msg = f'Missing: {", ".join(missing)}'
        print(f'  [AI EMAIL] Cannot send — {msg}')
        return {'sent': False, 'status': 'missing_config', 'error': msg, 'subject': ''}

    body_text  = path.read_text(encoding='utf-8')
    subject    = f'{cfg["subject_prefix"]} — Latest Summary'
    body_html  = (
        f'<html><body style="font-family:monospace;background:#0f1117;color:#94a3b8;'
        f'padding:20px;white-space:pre-wrap;">{_esc(body_text)}</body></html>'
    )

    if cfg['provider'] == 'resend':
        result = _send_resend_html(subject, body_text, body_html, cfg)
    else:
        result = _send_smtp_html(subject, body_text, body_html, cfg)

    result['subject'] = subject
    if result.get('sent'):
        print(f'  [AI EMAIL] Sent summary: {subject}')
    else:
        print(f'  [AI EMAIL] Failed summary: {result.get("error", "")}')
    return result
