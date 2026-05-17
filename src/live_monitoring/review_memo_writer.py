"""
review_memo_writer.py — Generate data/live_monitoring/latest_review_memo.md

Produces a human-readable weekly review memo from classified alerts.
Top-10 list with source links, excerpts, FP check, and recommended action.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from false_positive_filter import summary_stats


_ACTION_EMOJI = {
    'INVESTIGATE': '🔴',
    'WATCH':       '🟡',
    'DISCARD':     '⚫',
}

_FP_LABEL = {
    'KEEP_HIGH_PRIORITY':      'None detected — review source',
    'KEEP_REVIEW':             'Low — verify source URL',
    'DOWNGRADE_WATCH':         'Medium — scope or source unclear',
    'SUPPRESS_FALSE_POSITIVE': 'High — known FP pattern matched',
}

_SQ_LABEL = {
    'AFFIRM':     'Strategic Alternatives (Affirm)',
    'MERGER':     'Signed Merger Agreement',
    'PROCESS':    'Process Evidence (Banker / Activist)',
    'ROFR':       'ROFR / ROFN',
    'BOILERPLATE':'Boilerplate SA',
    'SCORE_ONLY': 'Score Only',
}


def _rank_alerts(alerts: list) -> list:
    """Sort for memo: INVESTIGATE first, then WATCH; within tier by signal quality."""
    _sq_rank = {'AFFIRM': 0, 'MERGER': 1, 'PROCESS': 2, 'ROFR': 3, 'BOILERPLATE': 9, 'SCORE_ONLY': 10}
    _action_rank = {'INVESTIGATE': 0, 'WATCH': 1, 'DISCARD': 2}
    return sorted(
        alerts,
        key=lambda a: (
            _action_rank.get(a.get('recommended_action', 'DISCARD'), 9),
            _sq_rank.get(a.get('signal_quality', ''), 9),
            a.get('ticker', ''),
        )
    )


def _fmt_excerpt(excerpt: str, max_chars: int = 300) -> str:
    if not excerpt:
        return '_No excerpt available — re-run scanner with Gate 1 patches active._'
    clean = ' '.join(excerpt.split())
    if len(clean) > max_chars:
        clean = clean[:max_chars].rstrip() + '…'
    return f'> {clean}'


def _status_badge(alert: dict) -> str:
    status = alert.get('status', '')
    if status == 'NEW':
        return ' **[NEW]**'
    if status == 'UPDATED':
        return ' **[UPDATED]**'
    if status == 'WATCHLIST':
        return ' **[WATCHLIST]**'
    return ''


def write_memo(
    alerts: list,
    memo_path: Path,
    scan_ts: str,
    total_scanned: int,
    run_mode: str = 'once',
    dry_run: bool = False,
) -> None:
    """Write the latest review memo to disk."""

    stats   = summary_stats(alerts)
    ranked  = _rank_alerts(alerts)
    top10   = [a for a in ranked if a.get('recommended_action') in ('INVESTIGATE', 'WATCH')][:10]
    suppressed = [a for a in ranked if a.get('fp_classification') == 'SUPPRESS_FALSE_POSITIVE']

    memo_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []

    lines.append(f'# Biotech Strategic Process Monitor — Review Memo')
    lines.append(f'')
    dry_tag = ' (DRY RUN — no live scan performed)' if dry_run else ''
    lines.append(f'**Scan timestamp:** {scan_ts}{dry_tag}')
    lines.append(f'**Run mode:** {run_mode}')
    lines.append(f'**Generated:** {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}')
    lines.append(f'')
    lines.append(f'---')
    lines.append(f'')

    # Summary table
    lines.append(f'## Summary')
    lines.append(f'')
    lines.append(f'| Metric | Count |')
    lines.append(f'|---|---|')
    lines.append(f'| Names scanned | {total_scanned} |')
    lines.append(f'| Total alerts (non-SCORE_ONLY) | {stats["total"]} |')
    lines.append(f'| New alerts | {stats["new"]} |')
    lines.append(f'| Updated alerts | {stats["updated"]} |')
    lines.append(f'| High-priority (INVESTIGATE) | {stats["KEEP_HIGH_PRIORITY"]} |')
    lines.append(f'| Review (WATCH) | {stats["KEEP_REVIEW"] + stats["DOWNGRADE_WATCH"]} |')
    lines.append(f'| Suppressed (false positive) | {stats["SUPPRESS_FALSE_POSITIVE"]} |')
    lines.append(f'')
    lines.append(f'---')
    lines.append(f'')

    # Top review list
    if top10:
        lines.append(f'## Top {len(top10)} Cases for Review')
        lines.append(f'')
        lines.append('_Ordered by priority: INVESTIGATE → WATCH. Source links are Gate 1 verified._')
        lines.append('')
        for i, a in enumerate(top10, 1):
            action   = a.get('recommended_action', 'WATCH')
            emoji    = _ACTION_EMOJI.get(action, '⚫')
            sq       = _SQ_LABEL.get(a.get('signal_quality', ''), a.get('signal_quality', ''))
            badge    = _status_badge(a)
            ticker   = a.get('ticker', '')
            company  = a.get('company_name', '') or ticker
            mcap     = a.get('market_cap', '')
            mcap_str = f' | ${mcap}M' if mcap else ''
            price    = a.get('price', '')
            price_str = f' | ${price}' if price else ''
            pif      = a.get('priced_in_flag', '')

            lines.append(f'### {i}. {emoji} {ticker} — {company}{badge}')
            lines.append(f'')
            lines.append(f'| Field | Value |')
            lines.append(f'|---|---|')
            lines.append(f'| Signal quality | {sq} |')
            lines.append(f'| Recommended action | **{action}** |')
            lines.append(f'| Signal type | {a.get("signal_type", "")} |')
            lines.append(f'| Market cap | {mcap_str.strip(" |") or "—"} |')
            lines.append(f'| Price | {price_str.strip(" |") or "—"} |')
            lines.append(f'| Priced-in flag | {pif or "—"} |')
            lines.append(f'| First seen | {a.get("first_seen", "—")} |')
            lines.append(f'| Last seen | {a.get("last_seen", "—")} |')
            lines.append(f'| Filing type | {a.get("signal_source_form", "—")} |')
            lines.append(f'| Filing date | {a.get("signal_source_date", "—")} |')
            lines.append(f'')

            src_url = a.get('signal_source_url', '')
            src_acc = a.get('signal_source_accession', '')
            if src_url:
                lines.append(f'**Source:** [{src_acc or src_url}]({src_url})')
            elif src_acc:
                lines.append(f'**Source accession:** `{src_acc}` — fetch manually via EDGAR.')
            else:
                lines.append(f'**Source:** _Not available — scanner ran without Gate 1 patches or no 8-K hit._')
            lines.append(f'')

            lines.append(f'**Excerpt:**')
            lines.append(f'')
            lines.append(_fmt_excerpt(a.get('signal_source_excerpt', '')))
            lines.append(f'')

            fp_check = _FP_LABEL.get(a.get('fp_classification', ''), '—')
            lines.append(f'**False-positive check:** {fp_check}')
            lines.append(f'')

            top_phrase = a.get('top_8k_phrase', '')
            if top_phrase:
                lines.append(f'**Trigger phrase:** `{top_phrase}`')
                lines.append(f'')

            rofn_hint = a.get('rofn_scope_hint', '')
            if rofn_hint:
                lines.append(f'**ROFN scope hint:** `{rofn_hint}`')
                lines.append(f'')

            flags_str = a.get('flags', '')
            if flags_str:
                lines.append(f'**Scanner flags:** {flags_str}')
                lines.append(f'')

            lines.append(f'---')
            lines.append(f'')
    else:
        lines.append(f'## Top Cases for Review')
        lines.append(f'')
        lines.append('_No actionable alerts in this scan (all suppressed or no process signals above SCORE_ONLY)._')
        lines.append(f'')
        lines.append(f'---')
        lines.append(f'')

    # Suppressed alerts summary
    if suppressed:
        lines.append(f'## Suppressed Alerts ({len(suppressed)} — Known FP Patterns)')
        lines.append(f'')
        lines.append(f'| Ticker | Signal quality | FP risk | Top phrase |')
        lines.append(f'|---|---|---|---|')
        for a in suppressed[:20]:
            lines.append(
                f'| {a.get("ticker","")} | {a.get("signal_quality","")} '
                f'| {a.get("false_positive_risk","")} '
                f'| {a.get("top_8k_phrase","")[:60]} |'
            )
        if len(suppressed) > 20:
            lines.append(f'| _(+ {len(suppressed)-20} more)_ | | | |')
        lines.append(f'')
        lines.append(f'---')
        lines.append(f'')

    # Footer
    lines.append(f'## Notes')
    lines.append(f'')
    lines.append(f'- This memo is for research and monitoring purposes only.')
    lines.append(f'- INVESTIGATE and WATCH are process-signal classifications, not trade recommendations.')
    lines.append(f'- Source links connect directly to SEC EDGAR filings.')
    lines.append(f'- False-positive patterns derived from 86-case historical adjudication study (3/86 true signals).')
    lines.append(f'- Do not act on SCORE_ONLY names.')
    lines.append(f'- Do not treat any output as investment advice.')
    lines.append(f'')

    memo_path.write_text('\n'.join(lines), encoding='utf-8')
