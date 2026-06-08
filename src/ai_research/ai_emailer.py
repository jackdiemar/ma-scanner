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
        'subject_prefix':  os.environ.get('AI_EMAIL_SUBJECT_PREFIX', 'Black Starlight MA Scanner').strip()
                           or 'Black Starlight MA Scanner',
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

def build_ai_email_subject(
    decisions: list[dict],
    prefix: str,
    opportunity_queue: dict | None = None,
) -> str:
    """
    Build subject line. If opportunity_queue provided, reflects opportunity state.

    Examples:
      "MA Scanner AI Brief — 1 Escalate / 3 Watch"
      "MA Scanner AI Brief — No New Opportunities / 10 Suppressed"
      "MA Scanner AI Brief — 2 Watch / 1 Review"
    """
    if opportunity_queue is not None:
        no_opp     = opportunity_queue.get('no_opportunity', False)
        suppressed = opportunity_queue.get('total_suppressed_full', 0)
        p0 = len(opportunity_queue.get('P0_ESCALATE_NOW', []))
        p1 = len(opportunity_queue.get('P1_HUMAN_REVIEW', []))
        p2 = len(opportunity_queue.get('P2_WATCHLIST_SETUP', []))
        p3 = len(opportunity_queue.get('P3_MONITOR_CHANGE', []))

        if no_opp:
            return f'{prefix} — No New Opportunities / {suppressed} Suppressed'

        parts: list[str] = []
        if p0:
            parts.append(f'{p0} Escalate')
        if p1:
            parts.append(f'{p1} Human Review')
        if p2:
            parts.append(f'{p2} Watch Setups')
        if p3:
            parts.append(f'{p3} Monitor')
        if suppressed:
            parts.append(f'{suppressed} Suppressed')
        suffix = ' / '.join(parts) if parts else 'No Active Opportunities'
        return f'{prefix} — {suffix}'

    # Legacy path (no opportunity queue)
    escalate = sum(1 for d in decisions if d.get('research_action') == 'ESCALATE')
    watch    = sum(1 for d in decisions if d.get('research_action') in ('WATCH', 'WAIT_FOR_PRICE', 'WATCH_ONLY'))
    discard  = sum(1 for d in decisions if d.get('research_action') == 'DISCARD')
    review   = sum(1 for d in decisions if d.get('research_action') == 'NEEDS_HUMAN_REVIEW')

    parts = []
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

    # Acquisition intelligence fields
    acq_situation   = d.get('primary_acquisition_situation', '')
    prob_bucket     = d.get('probability_bucket', '')
    prob_score      = d.get('acquisition_research_probability_score', 0)
    closest_analogue = d.get('closest_completed_deal_analogue') or {}
    traits_present  = d.get('successful_deal_traits_present', []) or []
    traits_missing  = d.get('successful_deal_traits_missing', []) or []
    why_not_higher  = d.get('why_probability_not_higher', '')
    evidence_needed = d.get('evidence_needed_to_upgrade', []) or []
    ext_status      = d.get('external_research_status', {}) or {}
    is_explicit     = d.get('is_explicit_process_signal', False)
    is_setup        = d.get('is_setup_signal_only', False)
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

    # Acquisition situation + probability bucket (always show if present)
    if acq_situation or prob_bucket:
        html += (
            f'<div style="background:#0f1117;border-left:3px solid #c9a84c;'
            f'padding:6px 10px;border-radius:4px;margin-bottom:8px;">'
            f'<span style="font-size:10px;color:#c9a84c;text-transform:uppercase;'
            f'letter-spacing:0.08em;">Acquisition Situation</span><br>'
        )
        if acq_situation:
            html += f'<span style="font-size:11px;color:#94a3b8;">{_esc(acq_situation)}</span>'
        if prob_bucket:
            bucket_color = '#dc2626' if 'P5' in prob_bucket else (
                '#d97706' if 'P4' in prob_bucket else (
                '#2563eb' if 'P3' in prob_bucket else '#374151'
            ))
            html += (
                f' &nbsp;<span style="display:inline-block;padding:1px 6px;border-radius:3px;'
                f'font-size:10px;font-weight:700;background:{bucket_color};color:#fff;">'
                f'{_esc(prob_bucket.split("_")[0])}</span>'
            )
        if prob_score:
            html += f' &nbsp;<span style="font-size:10px;color:#64748b;">score {prob_score}/100</span>'
        if is_explicit:
            html += f' &nbsp;<span style="font-size:10px;color:#16a34a;">EXPLICIT PROCESS</span>'
        elif is_setup:
            html += f' &nbsp;<span style="font-size:10px;color:#d97706;">SETUP ONLY</span>'
        html += '</div>'

    # Closest completed deal analogue
    if closest_analogue and closest_analogue.get('ticker'):
        html += (
            f'<div style="font-size:11px;color:#64748b;margin-bottom:6px;">'
            f'Closest analogue: <span style="color:#94a3b8;">{_esc(closest_analogue.get("ticker", "?"))} '
            f'({_esc(closest_analogue.get("acquisition_situation_type", "?"))})</span>'
        )
        lesson = closest_analogue.get('operator_lesson', '')
        if lesson:
            html += (
                f'<br><span style="font-size:10px;color:#475569;">{_esc(lesson[:200])}</span>'
            )
        html += '</div>'

    # Successful deal traits (strategic brief only)
    if strategic_brief and (traits_present or traits_missing):
        if traits_present:
            html += '<div style="font-size:11px;color:#16a34a;margin-bottom:4px;">Traits present: '
            html += '; '.join(_esc(t[:80]) for t in traits_present[:2])
            html += '</div>'
        if traits_missing:
            html += '<div style="font-size:11px;color:#dc2626;margin-bottom:4px;">Traits missing: '
            html += '; '.join(_esc(t[:80]) for t in traits_missing[:2])
            html += '</div>'

    # Why probability not higher (strategic brief only)
    if strategic_brief and why_not_higher:
        html += (
            f'<div style="font-size:11px;color:#64748b;margin-bottom:6px;">'
            f'Why not higher: {_esc(why_not_higher[:200])}</div>'
        )

    # Evidence needed to upgrade (strategic brief only)
    if strategic_brief and evidence_needed:
        html += (
            f'<div style="font-size:11px;color:#64748b;margin-bottom:6px;">'
            f'To upgrade: {_esc(evidence_needed[0][:150])}</div>'
        )

    # External research status (compact, strategic brief only)
    if strategic_brief and not ext_status.get('enabled', False):
        html += (
            f'<div style="font-size:10px;color:#374151;margin-bottom:4px;">'
            f'External research: DISABLED — TSRO-type signals not detectable</div>'
        )

    # What would change the decision
    if change_dec:
        html += (
            f'<div style="font-size:11px;color:#475569;font-style:italic;margin-top:8px;">'
            f'Would change if: {_esc(change_dec[:200])}</div>'
        )

    # ── Diligence memo deep fields ────────────────────────────────────────────
    one_liner     = d.get('one_sentence_bottom_line', '')
    exec_takeaway = d.get('executive_case_takeaway', '')
    exact_quotes  = d.get('exact_quotes_used', []) or []
    what_matters  = d.get('why_this_case_matters_now', '')
    not_answered  = d.get('what_is_not_yet_answered', '')
    imm_steps     = d.get('immediate_next_steps', []) or []
    next_sources  = d.get('next_sources_to_check', []) or []
    what_upgrade  = d.get('what_would_upgrade', '')
    what_downgrade = d.get('what_would_downgrade', '')
    not_actionable = d.get('why_this_is_not_actionable_yet', '')
    sugg_queries   = d.get('suggested_follow_up_queries', []) or []

    if strategic_brief and one_liner:
        html += (
            f'<div style="background:#0f1629;border-left:3px solid #c9a84c;'
            f'padding:7px 11px;border-radius:4px;margin-top:8px;margin-bottom:6px;">'
            f'<span style="font-size:12px;font-weight:700;color:#e2e8f0;">{_esc(one_liner[:200])}</span>'
            f'</div>'
        )

    if strategic_brief and exec_takeaway:
        html += (
            f'<div style="background:#0f1117;border-left:3px solid #1e3a5f;'
            f'padding:6px 10px;border-radius:4px;margin-bottom:6px;">'
            f'<span style="font-size:10px;color:#4a7fbf;text-transform:uppercase;'
            f'letter-spacing:0.08em;">Analyst Takeaway</span><br>'
            f'<span style="font-size:12px;color:#94a3b8;line-height:1.5;">'
            f'{_esc(exec_takeaway[:400])}</span>'
            f'</div>'
        )

    if strategic_brief and exact_quotes:
        q_html = ''.join(
            f'<div style="font-size:11px;color:#64748b;font-style:italic;margin:2px 0;">'
            f'&ldquo;{_esc(str(q)[:200])}&rdquo;</div>'
            for q in exact_quotes[:3]
        )
        html += (
            f'<div style="background:#0a0f1a;border-left:3px solid #374151;'
            f'padding:6px 10px;border-radius:4px;margin-bottom:6px;">'
            f'<span style="font-size:10px;color:#374151;text-transform:uppercase;'
            f'letter-spacing:0.08em;">Source Quotes Used</span><br>'
            + q_html
            + '</div>'
        )

    if strategic_brief and not_answered:
        html += (
            f'<div style="font-size:11px;color:#64748b;margin-bottom:5px;">'
            f'<span style="color:#4b5563;">Open questions: </span>{_esc(not_answered[:250])}</div>'
        )

    if strategic_brief and not_actionable and action not in ('ESCALATE',):
        html += (
            f'<div style="font-size:11px;color:#dc2626;margin-bottom:5px;">'
            f'Not actionable: {_esc(not_actionable[:200])}</div>'
        )

    if strategic_brief and imm_steps:
        html += (
            f'<div style="margin-bottom:8px;">'
            f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:3px;">Immediate Steps (24-48h)</div>'
            f'<ol style="margin:0;padding-left:16px;">'
            + ''.join(
                f'<li style="font-size:11px;color:#94a3b8;line-height:1.6;">{_esc(str(s)[:150])}</li>'
                for s in imm_steps
            )
            + '</ol></div>'
        )

    if strategic_brief and (what_upgrade or what_downgrade):
        html += '<div style="margin-bottom:6px;">'
        if what_upgrade:
            html += (
                f'<div style="font-size:11px;color:#16a34a;margin-bottom:2px;">'
                f'Upgrade if: {_esc(what_upgrade[:180])}</div>'
            )
        if what_downgrade:
            html += (
                f'<div style="font-size:11px;color:#dc2626;margin-bottom:2px;">'
                f'Kill if: {_esc(what_downgrade[:180])}</div>'
            )
        html += '</div>'

    if strategic_brief and next_sources:
        html += (
            f'<div style="font-size:11px;color:#374151;margin-bottom:5px;">'
            f'Next sources: '
            + ' &bull; '.join(_esc(str(s)[:80]) for s in next_sources[:3])
            + '</div>'
        )

    if strategic_brief and sugg_queries:
        q_items = ' &nbsp;|&nbsp; '.join(
            f'<span style="font-family:monospace;color:#374151;">{_esc(str(q)[:60])}</span>'
            for q in sugg_queries[:4]
        )
        html += (
            f'<div style="font-size:10px;color:#374151;margin-top:4px;">'
            f'Queries: {q_items}</div>'
        )

    html += '</div>'
    return html


def _catalyst_section_html(catalyst_summary: dict) -> str:
    """
    Render the Catalyst Calendar section for the email.
    Shows: upcoming earnings, PDUFA signals, Phase 3 readouts, conference calendar.
    """
    if not catalyst_summary:
        return ''

    cats        = catalyst_summary.get('catalysts', [])
    confs       = catalyst_summary.get('conferences', [])
    stats       = catalyst_summary.get('stats', {})
    gen_at      = _esc(catalyst_summary.get('generated_at', ''))

    # Priority badge colors
    _CAT_COLORS = {
        'P0_IMMINENT':  '#dc2626',
        'P1_NEAR_TERM': '#d97706',
        'P2_UPCOMING':  '#2563eb',
        'P3_HORIZON':   '#374151',
    }
    _TYPE_ICONS = {
        'EARNINGS':       '📊',
        'PDUFA':          '🏛',
        'PHASE3_READOUT': '🔬',
        'CONFERENCE':     '🗓',
    }

    if not cats and not confs:
        return (
            f'<div style="background:#0a101e;border:1px solid #1f2937;border-radius:8px;'
            f'padding:14px 18px;margin-bottom:16px;">'
            f'<div style="font-size:11px;color:#374151;text-transform:uppercase;'
            f'letter-spacing:0.1em;">Catalyst Calendar — No Events Found</div>'
            f'</div>'
        )

    # ── Ticker-specific catalysts ─────────────────────────────────────────────
    cat_rows_html = ''
    shown_cats = [c for c in cats if c.get('days_until', 999) <= 60][:15]
    for cat in shown_cats:
        ticker    = _esc(cat.get('ticker', '?'))
        ctype     = cat.get('catalyst_type', '')
        du        = cat.get('days_until', 0)
        dt        = _esc(cat.get('date', 'TBD'))
        desc      = _esc(cat.get('description', '')[:110])
        priority  = cat.get('priority', 'P3_HORIZON')
        pcolor    = _CAT_COLORS.get(priority, '#374151')
        icon      = _TYPE_ICONS.get(ctype, '•')
        src_url   = cat.get('source_url', '')
        conf_str  = ''
        if cat.get('confidence') == 'MEDIUM':
            conf_str = ' <span style="font-size:9px;color:#4b5563;">[verify]</span>'

        du_str = f'+{du}d' if du >= 0 else f'{du}d'
        ticker_link = (
            f'<a href="{_esc(src_url)}" style="color:#e2e8f0;text-decoration:none;">{ticker}</a>'
            if src_url else ticker
        )
        cat_rows_html += (
            f'<tr>'
            f'<td style="padding:4px 8px;font-size:12px;font-weight:700;color:#e2e8f0;">'
            f'{ticker_link}</td>'
            f'<td style="padding:4px 8px;">'
            f'<span style="display:inline-block;padding:1px 6px;border-radius:3px;'
            f'font-size:10px;font-weight:700;background:{pcolor};color:#fff;">'
            f'{_esc(ctype.replace("_", " "))}</span></td>'
            f'<td style="padding:4px 8px;font-size:11px;color:#94a3b8;">{dt}</td>'
            f'<td style="padding:4px 8px;font-size:11px;font-weight:600;color:{pcolor};">{du_str}</td>'
            f'<td style="padding:4px 8px;font-size:11px;color:#64748b;">{desc}{conf_str}</td>'
            f'</tr>'
        )

    cat_table_html = ''
    if cat_rows_html:
        hidden_count = max(len([c for c in cats if c.get('days_until', 999) <= 60]) - 15, 0)
        more_txt = f' (+{hidden_count} more beyond 60d)' if hidden_count else ''
        cat_table_html = (
            f'<table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:10px;">'
            f'<tr>'
            f'<th style="font-size:9px;color:#374151;text-align:left;padding:2px 8px;">Ticker</th>'
            f'<th style="font-size:9px;color:#374151;text-align:left;padding:2px 8px;">Type</th>'
            f'<th style="font-size:9px;color:#374151;text-align:left;padding:2px 8px;">Date</th>'
            f'<th style="font-size:9px;color:#374151;text-align:left;padding:2px 8px;">Days</th>'
            f'<th style="font-size:9px;color:#374151;text-align:left;padding:2px 8px;">Event</th>'
            f'</tr>'
            + cat_rows_html
            + f'</table>'
            + (f'<div style="font-size:10px;color:#374151;">{_esc(more_txt)}</div>' if more_txt else '')
        )
    else:
        cat_table_html = (
            '<div style="font-size:12px;color:#374151;margin-bottom:8px;">'
            'No earnings, PDUFA, or Phase 3 events detected in next 60 days for alert tickers.</div>'
        )

    # ── Conference calendar ───────────────────────────────────────────────────
    conf_items_html = ''
    upcoming_confs = [c for c in confs if -3 <= c.get('days_until', 999) <= 180][:6]
    for conf in upcoming_confs:
        name    = _esc(conf.get('name', ''))
        start   = _esc(conf.get('date', ''))
        end     = _esc(conf.get('end_date', ''))
        du      = conf.get('days_until', 0)
        note    = _esc(conf.get('description', '')[:90])
        areas   = ' · '.join(_esc(a) for a in (conf.get('therapeutic_areas') or [])[:4])
        matches = conf.get('matched_tickers', [])
        status  = 'ACTIVE' if du <= 0 else f'+{du}d'
        status_color = '#16a34a' if du <= 0 else ('#d97706' if du <= 14 else '#374151')

        match_str = ''
        if matches:
            match_str = (
                f' <span style="font-size:9px;color:#2563eb;">'
                f'→ {_esc(", ".join(matches[:4]))}</span>'
            )

        conf_items_html += (
            f'<div style="border-top:1px solid #1f2937;padding:5px 0;">'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="font-size:11px;font-weight:600;color:#e2e8f0;">{name}</span>'
            f'<span style="font-size:10px;font-weight:700;color:{status_color};">{status}</span>'
            f'{match_str}'
            f'</div>'
            f'<div style="font-size:10px;color:#4b5563;">{start} → {end} | {areas}</div>'
            + (f'<div style="font-size:10px;color:#374151;">{note}</div>' if note else '')
            + '</div>'
        )

    # ── Stats summary ─────────────────────────────────────────────────────────
    p0 = stats.get('imminent_p0', 0)
    p1 = stats.get('near_term_p1', 0)
    total_cats = stats.get('total_ticker_catalysts', 0)
    stat_parts: list[str] = []
    if p0:
        stat_parts.append(f'<span style="color:#dc2626;font-weight:700;">{p0} imminent (&le;7d)</span>')
    if p1:
        stat_parts.append(f'<span style="color:#d97706;font-weight:700;">{p1} near-term (&le;21d)</span>')
    if total_cats:
        stat_parts.append(f'{total_cats} total events tracked')
    stats_html = ' &nbsp;|&nbsp; '.join(stat_parts) if stat_parts else 'No near-term catalysts'

    return (
        f'<div style="background:#0a0f1e;border:1px solid #1e3a5f;border-radius:8px;'
        f'padding:14px 18px;margin-bottom:16px;">'

        f'<div style="font-size:11px;color:#4a7fbf;text-transform:uppercase;'
        f'letter-spacing:0.12em;margin-bottom:10px;border-bottom:1px solid #1e3a5f;'
        f'padding-bottom:6px;display:flex;justify-content:space-between;align-items:center;">'
        f'<span>Catalyst Calendar</span>'
        f'<span style="font-size:10px;color:#374151;font-weight:400;text-transform:none;">'
        f'Generated {gen_at}</span>'
        f'</div>'

        f'<div style="font-size:11px;color:#64748b;margin-bottom:8px;">{stats_html}</div>'

        + cat_table_html

        + f'<div style="font-size:10px;color:#4a7fbf;text-transform:uppercase;'
        f'letter-spacing:0.08em;margin-top:10px;margin-bottom:6px;">Major Conferences 2026</div>'
        + (conf_items_html or
           '<div style="font-size:11px;color:#374151;">No conferences in range.</div>')

        + f'<div style="font-size:9px;color:#1f2937;margin-top:8px;">'
        f'Earnings: FMP calendar (verified). PDUFA: SEC EDGAR EFTS keyword search (verify date in filing). '
        f'Phase 3: ClinicalTrials.gov (completion date, not readout date — may differ). '
        f'Not investment advice.</div>'

        f'</div>'
    )


def _build_synthesis_html(
    active_decisions: list[dict],
    all_decisions: list[dict],
    run_metadata: dict,
    opportunity_queue: dict | None,
    dominant_fp: str | None,
    escalate: int,
    watch: int,
    review: int,
    total_suppressed: int,
    no_opportunity: bool,
) -> str:
    """
    Research analyst synthesis section — 5 parts:
    A. Executive Read
    B. Changes This Run
    C. Operator Action Queue
    D. Best Research Leads
    E. System Learning
    """
    case_count    = run_metadata.get('case_count', len(all_decisions))
    llm_called    = run_metadata.get('llm_called_count', 0)
    suppressed_ct = run_metadata.get('suppressed_count', total_suppressed)

    # ── A. Executive Read ────────────────────────────────────────────────────
    fp_str = _esc(dominant_fp) if dominant_fp else 'repeated false-positive patterns'
    if no_opportunity:
        exec_read = (
            f'No new acquisition opportunities this run. '
            f'All {_esc(str(case_count))} scanner hits are {fp_str} discards — '
            f'no new process evidence, changed cases, or watchlist setups detected. '
            f'The system is correctly filtering known false-positive noise. '
            f'No operator action required today.'
        )
    elif escalate > 0:
        esc_tickers = _esc(', '.join(
            d.get('ticker', '?') for d in active_decisions
            if d.get('research_action') == 'ESCALATE'
        ))
        exec_read = (
            f'{escalate} alert(s) escalated for immediate review: <strong>{esc_tickers}</strong>. '
            f'{watch + review} additional active case(s) in WATCH/HUMAN_REVIEW. '
            f'{suppressed_ct} repeated discards suppressed. '
            f'Read source filings and corroborate with independent news before any action.'
        )
    elif watch > 0 or review > 0:
        active = watch + review
        exec_read = (
            f'No escalations. {active} active case(s) in WATCH/HUMAN_REVIEW. '
            + (f'{suppressed_ct} repeated discards suppressed. ' if suppressed_ct else '')
            + (f'Dominant false-positive: {fp_str}. ' if dominant_fp else '')
            + 'Monitor for follow-on filings. No immediate action required.'
        )
    else:
        exec_read = (
            f'No actionable opportunities this run. '
            + (f'{suppressed_ct} repeated discards suppressed. ' if suppressed_ct else '')
            + (f'Dominant false-positive: {fp_str}. ' if dominant_fp else '')
            + 'Continue monitoring for new company-level process filings.'
        )

    # ── B. Changes This Run ──────────────────────────────────────────────────
    new_analyzed = llm_called if llm_called else len(active_decisions)
    change_items: list[str] = []
    if new_analyzed:
        change_items.append(
            f'<strong>{new_analyzed}</strong> case(s) analyzed by AI (new or changed evidence)'
        )
    if suppressed_ct:
        change_items.append(
            f'<strong>{suppressed_ct}</strong> suppressed (unchanged repeated discards — skipped LLM)'
        )
    if opportunity_queue is not None:
        p0 = len(opportunity_queue.get('P0_ESCALATE_NOW', []))
        p1 = len(opportunity_queue.get('P1_HUMAN_REVIEW', []))
        p2 = len(opportunity_queue.get('P2_WATCHLIST_SETUP', []))
        p3 = len(opportunity_queue.get('P3_MONITOR_CHANGE', []))
        active_total = p0 + p1 + p2 + p3
        if active_total:
            change_items.append(
                f'{active_total} active case(s) across P0-P3 queues'
            )
    if not change_items:
        change_items.append('No changes detected vs. prior run')

    change_html = ''.join(
        f'<li style="font-size:12px;color:#94a3b8;line-height:1.8;">{item}</li>'
        for item in change_items
    )

    # ── C. Operator Action Queue ─────────────────────────────────────────────
    queue_rows: list[str] = []
    if opportunity_queue is not None:
        tier_labels = [
            ('P0_ESCALATE_NOW',    'P0 — ESCALATE NOW',  '#dc2626'),
            ('P1_HUMAN_REVIEW',    'P1 — HUMAN REVIEW',  '#7c3aed'),
            ('P2_WATCHLIST_SETUP', 'P2 — WATCH SETUP',   '#d97706'),
            ('P3_MONITOR_CHANGE',  'P3 — MONITOR',       '#2563eb'),
        ]
        for tier_key, label, color in tier_labels:
            entries = opportunity_queue.get(tier_key, [])
            if entries:
                tickers_str = _esc(', '.join(
                    str(e.get('ticker', '?')) for e in entries
                ))
                queue_rows.append(
                    f'<div style="margin-bottom:4px;">'
                    f'<span style="display:inline-block;min-width:120px;font-size:11px;'
                    f'font-weight:700;color:{color};">{_esc(label)}</span>'
                    f'<span style="font-size:11px;color:#94a3b8;">'
                    f'({len(entries)}) {tickers_str}</span>'
                    f'</div>'
                )
        if total_suppressed:
            queue_rows.append(
                f'<div style="margin-bottom:4px;">'
                f'<span style="display:inline-block;min-width:120px;font-size:11px;'
                f'font-weight:700;color:#374151;">P4 — SUPPRESSED</span>'
                f'<span style="font-size:11px;color:#374151;">'
                f'({total_suppressed}) archived — no action</span>'
                f'</div>'
            )
    else:
        for d in all_decisions:
            action = d.get('research_action', '')
            ticker = _esc(d.get('ticker', '?'))
            queue_rows.append(
                f'<div style="font-size:11px;color:#94a3b8;margin-bottom:2px;">'
                f'{ticker}: {_esc(action)}</div>'
            )

    queue_html = ''.join(queue_rows) if queue_rows else (
        '<div style="font-size:11px;color:#374151;">No active queue items.</div>'
    )

    # ── D. Best Research Leads ───────────────────────────────────────────────
    actionable = [
        d for d in active_decisions
        if d.get('research_action') in ('WATCH', 'WAIT_FOR_PRICE', 'NEEDS_HUMAN_REVIEW', 'ESCALATE')
        and 'SUPPRESSED_UNCHANGED' not in str(d.get('note', ''))
    ]
    actionable_sorted = sorted(actionable, key=lambda d: d.get('investability_score', 0), reverse=True)

    if no_opportunity or not actionable_sorted:
        # Surface best even among discards
        best_discards = sorted(
            [d for d in all_decisions if 'SUPPRESSED_UNCHANGED' not in str(d.get('note', ''))],
            key=lambda d: d.get('investability_score', 0), reverse=True
        )[:3]
        if best_discards:
            fp_note = f'Top scanner hits are {fp_str} false positives.' if dominant_fp else 'All scanner hits are discards.'
            leads_html = (
                f'<div style="font-size:12px;color:#64748b;margin-bottom:6px;">'
                f'No research leads today. {fp_note}</div>'
            )
            for d in best_discards[:3]:
                t = _esc(d.get('ticker', '?'))
                reason = _esc(str(d.get('discard_reason', '') or d.get('why_this_is_not_actionable_yet', '') or d.get('short_thesis', ''))[:120])
                leads_html += (
                    f'<div style="font-size:11px;color:#374151;margin-bottom:2px;">'
                    f'<strong style="color:#4b5563;">{t}</strong>: {reason}</div>'
                )
        else:
            leads_html = '<div style="font-size:12px;color:#64748b;">No cases to analyze this run.</div>'
    else:
        leads_html = ''
        for d in actionable_sorted[:3]:
            t         = _esc(d.get('ticker', '?'))
            company   = _esc(d.get('company_name', ''))
            action    = d.get('research_action', '')
            score     = d.get('investability_score', 0)
            bottom    = _esc(str(d.get('one_sentence_bottom_line', '') or d.get('short_thesis', ''))[:140])
            what_next = _esc(str((d.get('immediate_next_steps') or d.get('operator_next_steps') or [''])[0])[:120])
            header = f'{t}' + (f' — {company}' if company and company != t else '')
            leads_html += (
                f'<div style="background:#0d1520;border-left:3px solid #2563eb;'
                f'padding:6px 10px;border-radius:4px;margin-bottom:6px;">'
                f'<div style="font-size:12px;font-weight:700;color:#e2e8f0;">{header} '
                f'{_badge_html(action)}</div>'
                + (f'<div style="font-size:11px;color:#94a3b8;margin-top:3px;">{bottom}</div>' if bottom else '')
                + (f'<div style="font-size:11px;color:#64748b;margin-top:2px;">Next: {what_next}</div>' if what_next else '')
                + f'<div style="font-size:10px;color:#374151;margin-top:2px;">Score: {score}/100</div>'
                f'</div>'
            )

    # ── E. System Learning ───────────────────────────────────────────────────
    fp_counts: dict[str, int] = {}
    for d in all_decisions:
        for fp in (d.get('matched_false_positive_archetypes', []) or []):
            fp_counts[fp] = fp_counts.get(fp, 0) + 1
    filing_text_available = sum(1 for d in all_decisions if d.get('filing_text_available'))

    learning_parts: list[str] = []
    if dominant_fp:
        dom_count = fp_counts.get(dominant_fp, 0)
        learning_parts.append(
            f'Dominant pattern: {_esc(dominant_fp)} ({dom_count} of {case_count} cases).'
        )
    if filing_text_available:
        learning_parts.append(f'Filing text fetched for {filing_text_available} case(s).')
    else:
        learning_parts.append(
            'No filing text retrieved this run. '
            'TSRO-type media signals not detectable without external news integration.'
        )
    ts_candidates = [
        d.get('ticker', '') for d in active_decisions
        if d.get('matched_true_signal_archetypes') and d.get('research_action') != 'DISCARD'
    ]
    if ts_candidates:
        learning_parts.append(
            f'True-signal pattern candidates: {_esc(", ".join(ts_candidates))}. Verify with primary source.'
        )
    else:
        learning_parts.append('No MDVN/DMTX/TSRO-like signals detected this run.')

    sys_learning = ' '.join(learning_parts)

    # ── Assemble section ─────────────────────────────────────────────────────
    section_label = (
        lambda letter, text:
        f'<div style="font-size:11px;color:#c9a84c;text-transform:uppercase;'
        f'letter-spacing:0.1em;margin-bottom:5px;margin-top:14px;">{letter}. {_esc(text)}</div>'
    )

    return (
        f'<div style="background:#0a101e;border:1px solid #1e3a5f;border-radius:8px;'
        f'padding:16px 20px;margin-bottom:16px;">'
        f'<div style="font-size:12px;color:#c9a84c;text-transform:uppercase;'
        f'letter-spacing:0.12em;margin-bottom:12px;border-bottom:1px solid #1e3a5f;'
        f'padding-bottom:8px;">Research Analyst Synthesis</div>'

        + section_label('A', 'Executive Read')
        + f'<p style="font-size:12px;color:#e2e8f0;line-height:1.6;margin:0;">{exec_read}</p>'

        + section_label('B', 'Changes This Run')
        + f'<ul style="margin:0;padding-left:18px;">{change_html}</ul>'

        + section_label('C', 'Operator Action Queue')
        + f'<div>{queue_html}</div>'

        + section_label('D', 'Best Research Leads')
        + f'<div>{leads_html}</div>'

        + section_label('E', 'System Learning')
        + f'<p style="font-size:12px;color:#64748b;line-height:1.6;margin:0;">{sys_learning}</p>'

        + '</div>'
    )


def _suppressed_archive_html(suppressed_decisions: list[dict], total_suppressed: int) -> str:
    """Compact archive section for suppressed discards. Not shown as full cards."""
    if not suppressed_decisions and not total_suppressed:
        return ''

    rows = ''
    for d in suppressed_decisions[:5]:
        ticker = _esc(d.get('ticker', '?'))
        cls    = _esc(d.get('classification', '?'))
        note   = _esc(str(d.get('note', '') or d.get('discard_reason', ''))[:80])
        rows += (
            f'<tr>'
            f'<td style="font-size:11px;color:#94a3b8;padding:3px 8px;">{ticker}</td>'
            f'<td style="font-size:11px;color:#64748b;padding:3px 8px;">{cls}</td>'
            f'<td style="font-size:11px;color:#4b5563;padding:3px 8px;">{note}</td>'
            f'</tr>'
        )

    shown    = len(suppressed_decisions)
    hidden   = max(total_suppressed - shown, 0)
    more_txt = f' (+{hidden} more)' if hidden else ''

    return (
        f'<div style="background:#111827;border:1px solid #1f2937;border-radius:6px;'
        f'padding:12px 16px;margin-bottom:16px;">'
        f'<div style="font-size:11px;color:#374151;text-transform:uppercase;'
        f'letter-spacing:0.1em;margin-bottom:8px;">'
        f'Suppressed Repeated Discards — {total_suppressed} total{more_txt}</div>'
        f'<table cellpadding="0" cellspacing="0" width="100%">'
        f'<tr>'
        f'<th style="font-size:10px;color:#374151;text-align:left;padding:2px 8px;">Ticker</th>'
        f'<th style="font-size:10px;color:#374151;text-align:left;padding:2px 8px;">Classification</th>'
        f'<th style="font-size:10px;color:#374151;text-align:left;padding:2px 8px;">Reason</th>'
        f'</tr>'
        f'{rows}'
        f'</table>'
        f'<div style="font-size:10px;color:#374151;margin-top:8px;">'
        f'These cases are suppressed because they are already-announced or repeated false-positive '
        f'discards with no evidence change. They will reappear automatically if evidence changes.</div>'
        f'</div>'
    )


def _no_opportunity_html(
    total_suppressed: int,
    dominant_fp: str | None = None,
    sample_discards: list[dict] | None = None,
    suggested_queries: list[str] | None = None,
) -> str:
    dom_fp_html = ''
    if dominant_fp:
        dom_fp_html = (
            f'<div style="font-size:11px;color:#64748b;margin-top:6px;">'
            f'Dominant false-positive: <span style="color:#94a3b8;">{_esc(dominant_fp)}</span>'
            f'</div>'
        )

    examples_html = ''
    if sample_discards:
        rows = ''
        for d in sample_discards[:3]:
            t      = _esc(d.get('ticker', '?'))
            reason = _esc(str(
                d.get('discard_reason', '') or
                d.get('why_this_is_not_actionable_yet', '') or
                d.get('short_thesis', '') or
                d.get('note', '')
            )[:110])
            what_would = _esc(str(d.get('what_would_upgrade', '') or d.get('what_would_change_the_decision', ''))[:100])
            rows += (
                f'<div style="border-top:1px solid #1f2937;padding:6px 0;">'
                f'<div style="font-size:11px;color:#64748b;font-weight:600;">{t}</div>'
                f'<div style="font-size:11px;color:#4b5563;">{reason}</div>'
                + (f'<div style="font-size:10px;color:#374151;">Reopen if: {what_would}</div>' if what_would else '')
                + '</div>'
            )
        examples_html = (
            f'<div style="margin-top:10px;">'
            f'<div style="font-size:10px;color:#374151;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:4px;">Top suppressed examples</div>'
            + rows
            + '</div>'
        )

    queries_html = ''
    if suggested_queries:
        q_items = ''.join(
            f'<div style="font-size:11px;color:#374151;font-family:monospace;margin:2px 0;">'
            f'&#8250; {_esc(q)}</div>'
            for q in suggested_queries[:6]
        )
        queries_html = (
            f'<div style="margin-top:10px;">'
            f'<div style="font-size:10px;color:#374151;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:4px;">Suggested next research queries</div>'
            + q_items
            + '</div>'
        )

    return (
        f'<div style="background:#1e293b;border:1px solid #c9a84c;border-radius:6px;'
        f'padding:14px 16px;margin-bottom:16px;">'
        f'<div style="font-size:11px;color:#c9a84c;text-transform:uppercase;'
        f'letter-spacing:0.1em;margin-bottom:8px;">No New Acquisition Opportunities</div>'
        f'<p style="font-size:12px;color:#94a3b8;line-height:1.6;margin:0;">'
        f'<strong>{_esc(str(total_suppressed))}</strong> repeated already-announced / '
        f'false-positive cases suppressed. No new process evidence, changed evidence, '
        f'or watchlist setups detected this run.</p>'
        + dom_fp_html
        + examples_html
        + queries_html
        + f'<div style="font-size:11px;color:#374151;margin-top:10px;">'
        f'System will reopen suppressed cases automatically if source URL, filing date, '
        f'or signal type changes. Continue monitoring for new company-level process filings.</div>'
        f'</div>'
    )


def build_ai_email_html(
    decisions: list[dict],
    run_metadata: dict,
    strategic_brief: bool = False,
    opportunity_queue: dict | None = None,
    catalyst_summary: dict | None = None,
) -> str:
    """
    Build the full branded HTML email body. Uses inline styles throughout —
    email clients strip <style> blocks.

    opportunity_queue: if provided, splits decisions into active/suppressed sections.
    """
    run_at    = _esc(run_metadata.get('run_at', _utc_now()))
    model     = _esc(run_metadata.get('model', 'unknown'))
    case_count = int(run_metadata.get('case_count', len(decisions)))
    cache_hits = int(run_metadata.get('cache_hits', 0))
    ai_enabled = run_metadata.get('ai_enabled', False)
    dry_run    = run_metadata.get('dry_run', False)
    opp_mode   = run_metadata.get('opportunity_mode', False)
    suppressed_count = int(run_metadata.get('suppressed_count', 0))

    # Split decisions for opportunity mode
    active_decisions     = decisions
    suppressed_decisions = []
    total_suppressed     = 0
    no_opportunity       = False

    if opportunity_queue is not None:
        total_suppressed = opportunity_queue.get('total_suppressed_full', 0)
        no_opportunity   = opportunity_queue.get('no_opportunity', False)
        # Build sets of active tickers from P0-P3
        active_tickers: set[str] = set()
        for tier in ('P0_ESCALATE_NOW', 'P1_HUMAN_REVIEW', 'P2_WATCHLIST_SETUP', 'P3_MONITOR_CHANGE'):
            for e in opportunity_queue.get(tier, []):
                active_tickers.add(str(e.get('ticker', '')).upper())
        active_decisions     = [d for d in decisions if str(d.get('ticker', '')).upper() in active_tickers]
        suppressed_decisions = [d for d in decisions if str(d.get('ticker', '')).upper() not in active_tickers]

    # Count by action (active only)
    escalate   = sum(1 for d in active_decisions if d.get('research_action') == 'ESCALATE')
    watch      = sum(1 for d in active_decisions if d.get('research_action') in ('WATCH', 'WAIT_FOR_PRICE'))
    discard    = sum(1 for d in active_decisions if d.get('research_action') == 'DISCARD')
    review     = sum(1 for d in active_decisions if d.get('research_action') == 'NEEDS_HUMAN_REVIEW')
    watch_only = sum(1 for d in active_decisions if d.get('research_action') == 'WATCH_ONLY')

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

    # In opportunity mode: render only active decisions as full cards
    decisions_to_render = active_decisions if opportunity_queue is not None else decisions
    cards_html = ''.join(
        _card_html(d, strategic_brief=strategic_brief) for d in decisions_to_render
    ) if decisions_to_render else (
        '' if no_opportunity else
        '<p style="color:#64748b;font-size:13px;">No decisions were made this run.</p>'
    )

    # Sample discards for richer no-opportunity display
    sample_discards = [
        d for d in decisions
        if d.get('research_action') == 'DISCARD'
        and 'SUPPRESSED_UNCHANGED' not in str(d.get('note', ''))
    ][:3] if no_opportunity else []

    # Aggregate suggested queries for no-opportunity display
    all_suggested_queries: list[str] = []
    for d in decisions[:5]:
        for q in (d.get('suggested_follow_up_queries', []) or []):
            if q and q not in all_suggested_queries:
                all_suggested_queries.append(str(q))
    if not all_suggested_queries:
        # Build generic queries from tickers
        for d in decisions[:3]:
            ticker_q = d.get('ticker', '')
            company_q = d.get('company_name', '') or ticker_q
            if company_q:
                all_suggested_queries.append(f'"{company_q}" strategic alternatives')
                all_suggested_queries.append(f'"{company_q}" acquisition proposal')

    no_opportunity_html = (
        _no_opportunity_html(
            total_suppressed,
            dominant_fp=dominant_fp,
            sample_discards=sample_discards,
            suggested_queries=all_suggested_queries[:6],
        )
        if no_opportunity else ''
    )

    # Suppressed archive (opportunity mode)
    suppressed_archive_html = (
        _suppressed_archive_html(suppressed_decisions, total_suppressed)
        if (opportunity_queue is not None and total_suppressed > 0 and not no_opportunity)
        else ''
    )

    # Legacy: check if all top cases are already-announced (non-opportunity mode)
    all_already_announced = (
        opportunity_queue is None
        and decisions
        and all(
            d.get('classification') == 'ALREADY_ANNOUNCED_DEAL'
            or 'ALREADY_ANNOUNCED_MERGER' in (d.get('matched_false_positive_archetypes', []) or [])
            or (d.get('probability_bucket', '') == 'P1_DISCARD_ALREADY_ANNOUNCED')
            for d in decisions
        )
    )
    already_announced_advisory_html = ''
    if all_already_announced and strategic_brief:
        already_announced_advisory_html = (
            '<div style="background:#1e293b;border:1px solid #d97706;border-radius:6px;'
            'padding:14px 16px;margin-bottom:16px;">'
            '<div style="font-size:11px;color:#d97706;text-transform:uppercase;'
            'letter-spacing:0.1em;margin-bottom:8px;">System Note — Useful Negatives</div>'
            '<p style="font-size:12px;color:#94a3b8;line-height:1.6;margin:0;">'
            'All top cases in this batch are already-announced transactions. '
            'This is a useful negative result: the system is correctly identifying already-announced '
            'transaction language, but no current case resembles a pre-announcement setup signal. '
            'Next best improvement is external news/media integration for TSRO-like signals '
            'and training on additional completed acquisition setups. '
            'Continue monitoring for new company-level process filings.</p>'
            '</div>'
        )

    dry_run_banner = ''
    if dry_run:
        dry_run_banner = (
            '<div style="background:#1e293b;border:1px solid #f59e0b;border-radius:6px;'
            'padding:10px 14px;margin-bottom:16px;">'
            '<span style="color:#f59e0b;font-size:12px;font-weight:600;">DRY RUN — LLM was not called. '
            'Decisions shown are placeholders.</span></div>'
        )

    # Catalyst calendar section
    catalyst_html = _catalyst_section_html(catalyst_summary) if catalyst_summary else ''

    # Research analyst synthesis section (always shown when opportunity_mode or strategic_brief)
    synthesis_html = ''
    if (strategic_brief or opportunity_queue is not None) and decisions:
        synthesis_html = _build_synthesis_html(
            active_decisions=active_decisions,
            all_decisions=decisions,
            run_metadata=run_metadata,
            opportunity_queue=opportunity_queue,
            dominant_fp=dominant_fp,
            escalate=escalate,
            watch=watch,
            review=review,
            total_suppressed=total_suppressed,
            no_opportunity=no_opportunity,
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
    {_badge_html('DISCARD', f'{discard} DISCARD') if discard and opportunity_queue is None else ''}
    {f'<span style="font-size:11px;color:#374151;">{total_suppressed} suppressed</span>' if total_suppressed and opportunity_queue is not None else ''}
  </div>
</td></tr>

<!-- BODY -->
<tr><td style="padding:16px 24px;">
  {dry_run_banner}
  {catalyst_html}
  {synthesis_html}
  {strategy_summary_html}
  {already_announced_advisory_html}
  {no_opportunity_html}
  {cards_html}
  {suppressed_archive_html}
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
    opportunity_queue: dict | None = None,
    catalyst_summary: dict | None = None,
) -> str:
    """Plain text fallback. Clean and readable."""
    run_at     = run_metadata.get('run_at', _utc_now())
    model      = run_metadata.get('model', 'unknown')
    case_count = run_metadata.get('case_count', len(decisions))
    dry_run    = run_metadata.get('dry_run', False)
    opp_mode   = run_metadata.get('opportunity_mode', False)

    # For plain text, filter to active decisions in opportunity mode
    render_decisions = decisions
    total_suppressed = 0
    no_opportunity   = False
    if opportunity_queue is not None:
        total_suppressed = opportunity_queue.get('total_suppressed_full', 0)
        no_opportunity   = opportunity_queue.get('no_opportunity', False)
        active_tickers: set[str] = set()
        for tier in ('P0_ESCALATE_NOW', 'P1_HUMAN_REVIEW', 'P2_WATCHLIST_SETUP', 'P3_MONITOR_CHANGE'):
            for e in opportunity_queue.get(tier, []):
                active_tickers.add(str(e.get('ticker', '')).upper())
        render_decisions = [d for d in decisions if str(d.get('ticker', '')).upper() in active_tickers]

    lines: list[str] = [
        'BLACK STARLIGHT CAPITAL',
        'MA Scanner — AI Opportunity Brief',
        '=' * 48,
        f'Run: {run_at}',
        f'Model: {model}',
        f'Cases reviewed: {case_count}',
        f'Dry run: {dry_run}',
        f'Opportunity mode: {opp_mode}',
    ]
    if opportunity_queue is not None:
        lines.append(f'Active cases (P0-P3): {len(render_decisions)}')
        lines.append(f'Suppressed discards : {total_suppressed}')
    lines.append('')

    # Catalyst calendar (plain text)
    if catalyst_summary:
        cats  = catalyst_summary.get('catalysts', [])
        confs = catalyst_summary.get('conferences', [])
        stats = catalyst_summary.get('stats', {})
        lines += ['─' * 48, 'CATALYST CALENDAR', '']
        near = [c for c in cats if c.get('days_until', 999) <= 60][:10]
        if near:
            for c in near:
                ctype = c.get('catalyst_type', '?')
                du    = c.get('days_until', '?')
                dt    = c.get('date', 'TBD')
                desc  = c.get('description', '')[:100]
                lines.append(f'  {c.get("ticker","?"):<8} [{ctype:<15}] {dt} (+{du}d)  {desc}')
        else:
            lines.append('  No ticker-level catalysts in next 60 days.')
        lines.append('')
        upcoming_confs = [c for c in confs if -3 <= c.get('days_until', 999) <= 90]
        if upcoming_confs:
            lines.append('  Upcoming conferences:')
            for conf in upcoming_confs[:5]:
                du   = conf.get('days_until', 0)
                name = conf.get('name', '?')
                dt   = conf.get('date', '?')
                status = 'ACTIVE' if du <= 0 else f'+{du}d'
                lines.append(f'    {status:<10} {dt}  {name}')
        lines += ['', '─' * 48, '']

    if no_opportunity:
        lines += [
            '*** NO NEW ACTIONABLE OPPORTUNITIES ***',
            f'{total_suppressed} repeated already-announced/false-positive cases suppressed.',
            'Continue monitoring for new company-level process filings.',
            '',
        ]
    elif render_decisions:
        # Decision distribution (active decisions only)
        counts: dict[str, int] = {}
        for d in render_decisions:
            a = d.get('research_action', '?')
            counts[a] = counts.get(a, 0) + 1
        lines.append('Decision distribution (active):')
        for a, c in sorted(counts.items()):
            lines.append(f'  {a}: {c}')
        if total_suppressed:
            lines.append(f'  DISCARD (suppressed): {total_suppressed}')
        lines.append('')

        # FP summary if strategic
        if strategic_brief:
            fp_all: dict[str, int] = {}
            for d in render_decisions:
                for fp in (d.get('matched_false_positive_archetypes', []) or []):
                    fp_all[fp] = fp_all.get(fp, 0) + 1
            if fp_all:
                dominant = max(fp_all, key=lambda k: fp_all[k])
                lines.append(f'Dominant false-positive pattern: {dominant}')
                lines.append('')

        for d in render_decisions:
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

        if total_suppressed and not no_opportunity:
            lines += [
                '─' * 48,
                f'Suppressed archive ({total_suppressed} repeated DISCARD cases — not shown above):',
            ]
    else:
        if not no_opportunity:
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
    opportunity_queue: dict | None = None,
    catalyst_summary: dict | None = None,
) -> dict[str, Any]:
    """
    Build and send the branded AI research email.

    opportunity_queue: if provided, email shows P0-P3 in main cards,
    P4 in compact archive, and uses opportunity-aware subject line.

    Returns: {sent, status, error, subject, provider}
    """
    cfg = load_ai_email_config()

    # Check no-opportunity skip behavior
    no_opportunity = opportunity_queue is not None and opportunity_queue.get('no_opportunity', False)
    send_no_opp = _truthy(os.environ.get('AI_EMAIL_SEND_NO_OPPORTUNITY_DIGEST', 'true'), default=True)
    if no_opportunity and not send_no_opp and not force:
        print('  [AI EMAIL] Skipped — no opportunity + AI_EMAIL_SEND_NO_OPPORTUNITY_DIGEST=false')
        return {'sent': False, 'status': 'no_opportunity_skipped', 'error': '', 'subject': ''}

    if not cfg['enabled'] and not force:
        print('  [AI EMAIL] Skipped — AI_EMAILS_ENABLED=false (use force=True to override)')
        return {'sent': False, 'status': 'disabled', 'error': '', 'subject': ''}

    missing = _check_send_config(cfg)
    if missing:
        msg = f'Missing: {", ".join(missing)}'
        print(f'  [AI EMAIL] Cannot send — {msg}')
        return {'sent': False, 'status': 'missing_config', 'error': msg, 'subject': ''}

    subject    = build_ai_email_subject(decisions, cfg['subject_prefix'],
                                        opportunity_queue=opportunity_queue)
    body_html  = build_ai_email_html(decisions, run_metadata,
                                     strategic_brief=strategic_brief,
                                     opportunity_queue=opportunity_queue,
                                     catalyst_summary=catalyst_summary)
    body_plain = build_ai_email_plain(decisions, run_metadata,
                                      strategic_brief=strategic_brief,
                                      opportunity_queue=opportunity_queue,
                                      catalyst_summary=catalyst_summary)

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
