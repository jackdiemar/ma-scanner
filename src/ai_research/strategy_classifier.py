"""
strategy_classifier.py — Deterministic pre-LLM strategy feature extraction.

Runs before the LLM investment gate. Produces structured strategy features
that are injected into the prompt and the final decision dict.

No LLM calls. No I/O. Pure deterministic scoring.
"""
from __future__ import annotations

import re
from typing import Any

from ai_research.strategy_knowledge import (
    HISTORICAL_BASE_RATES,
    TRUE_SIGNAL_ARCHETYPES,
    FALSE_POSITIVE_ARCHETYPES,
    TRUE_SIGNAL_REQUIREMENTS,
    phrases_to_false_positive_archetypes,
    phrases_to_true_signal_archetypes,
)


# ── Text helpers ──────────────────────────────────────────────────────────────

def _text_for_case(case: dict) -> str:
    """Collect all text available in the case for phrase scanning."""
    parts = [
        str(case.get('source_excerpt', '') or ''),
        str(case.get('memo_section_excerpt', '') or ''),
        str(case.get('trigger_phrase', '') or ''),
        ' '.join(str(f) for f in (case.get('scanner_flags', []) or [])),
        str(case.get('signal_type', '') or ''),
        str(case.get('fp_classification', '') or ''),
    ]
    return ' '.join(p for p in parts if p.strip())


def _contains_any(text: str, phrases: list[str]) -> bool:
    t = text.lower()
    return any(p.lower() in t for p in phrases)


def _count_phrases(text: str, phrases: list[str]) -> int:
    t = text.lower()
    return sum(1 for p in phrases if p.lower() in t)


# ── Strong signal phrases (company-level) ─────────────────────────────────────

_STRONG_PROCESS_PHRASES = [
    'strategic alternatives', 'retained financial advisor', 'retained investment banker',
    'engaged banker', 'board committee', 'special committee', 'sale process',
    'strategic review', 'exploring strategic', 'unsolicited proposal',
    'unsolicited acquisition', 'superior proposal', 'competing bid',
    'go-shop period', 'fiduciary out', 'no-shop', 'topping bid',
    'strategic alternatives committee', 'review of strategic alternatives',
    'in talks to be acquired', 'acquisition discussions', 'sale of the company',
    'potential acquirers', 'management presentations', 'strategic alternatives review',
]

_ANNOUNCEMENT_PHRASES = [
    'definitive agreement', 'agreement and plan of merger', 'merger agreement',
    'acquisition agreement', 'transaction agreement', 'definitive merger',
    'entered into a definitive', 'to be acquired by', 'announced acquisition',
    'completed the merger', 'consummated the merger',
]

_POST_ANNOUNCEMENT_PHRASES = [
    'background of the merger', 'background of the acquisition',
    'DEFM14A', 'SC 14D-9', 'SC TO-T', 'solicitation / recommendation',
    'recommendation statement', 'background of the transaction',
]

_ASSET_SPECIFIC_PHRASES = [
    'right of first refusal', 'right of first negotiation', 'ROFR', 'ROFN', 'ROFO',
    'collaboration agreement', 'license agreement', 'co-development',
    'co-promotion', 'partnership agreement', 'commercialization rights',
    'asset purchase', 'license to develop',
]

_BOILERPLATE_PHRASES = [
    'risk factor', 'risk factors', 'S-8', 'Form S-8', 'equity incentive plan',
    'restricted stock unit', 'change of control vesting', 'accelerated vesting',
    'director', 'biography', 'previously served', 'rights plan',
    'shareholder rights plan', 'poison pill', 'anti-takeover',
    'advance notice', 'offering prospectus', '424B',
]

_NEGATION_PHRASES = [
    'no acquisition proposal', 'not received any proposal', 'no discussions',
    'declined to engage', 'not exploring', 'no strategic alternatives review',
    'not for sale', 'rejected the', 'remains committed to standalone',
]

_WRONG_DIRECTION_PHRASES = [
    'we acquired', 'we completed the acquisition of', 'our acquisition of',
    'we have entered into an agreement to acquire', 'our proposed acquisition of',
    'we intend to acquire', 'we consummated',
]


# ── Score computations ────────────────────────────────────────────────────────

def _compute_company_level_process_score(text: str, matched_ts: list[str], matched_fp: list[str]) -> int:
    """0-100: how likely is this a company-level strategic process signal?"""
    score = 0

    # Strong process phrases — each adds significant points
    strong_count = _count_phrases(text, _STRONG_PROCESS_PHRASES)
    score += min(strong_count * 20, 60)

    # True signal archetype matches add points
    score += min(len(matched_ts) * 15, 30)

    # Penalty for asset-specific language
    if _contains_any(text, _ASSET_SPECIFIC_PHRASES):
        score -= 20

    # Penalty for announcement/post-announcement
    if _contains_any(text, _ANNOUNCEMENT_PHRASES + _POST_ANNOUNCEMENT_PHRASES):
        score -= 30

    # Penalty for boilerplate
    if _contains_any(text, _BOILERPLATE_PHRASES):
        score -= 15

    # Penalty for negation
    if _contains_any(text, _NEGATION_PHRASES):
        score -= 35

    # Penalty for wrong direction
    if _contains_any(text, _WRONG_DIRECTION_PHRASES):
        score -= 40

    # FP archetype penalties
    if 'ALREADY_ANNOUNCED_MERGER' in matched_fp:
        score -= 50
    if 'POST_ANNOUNCEMENT_PROXY_BACKGROUND' in matched_fp:
        score -= 50
    if 'NEGATED_ACQUISITION_LANGUAGE' in matched_fp:
        score -= 40

    return max(0, min(100, score))


def _compute_false_positive_score(text: str, matched_fp: list[str]) -> int:
    """0-100: how likely is this a false positive?"""
    score = 0

    # Each FP archetype match adds significant points
    fp_count = len(matched_fp)
    score += min(fp_count * 25, 80)

    # Hard false positives
    hard_fps = {
        'ALREADY_ANNOUNCED_MERGER',
        'POST_ANNOUNCEMENT_PROXY_BACKGROUND',
        'S8_EQUITY_PLAN_BOILERPLATE',
        'NEGATED_ACQUISITION_LANGUAGE',
        'WRONG_DIRECTION_ACQUISITION',
    }
    if any(fp in hard_fps for fp in matched_fp):
        score = max(score, 85)

    # Boilerplate phrase penalty
    if _contains_any(text, _BOILERPLATE_PHRASES):
        score += 15

    # Asset-specific penalty
    if _contains_any(text, _ASSET_SPECIFIC_PHRASES):
        score += 20

    # Reduce score if strong process phrases are also present
    strong_count = _count_phrases(text, _STRONG_PROCESS_PHRASES)
    score -= min(strong_count * 10, 30)

    return max(0, min(100, score))


def _compute_announcement_status_score(text: str, matched_fp: list[str]) -> int:
    """
    0-100: how confident are we that a deal is ALREADY ANNOUNCED?
    100 = definitely already announced. 0 = no announcement evidence.
    """
    score = 0

    if _contains_any(text, _ANNOUNCEMENT_PHRASES):
        score += 70
    if _contains_any(text, _POST_ANNOUNCEMENT_PHRASES):
        score += 60
    if 'ALREADY_ANNOUNCED_MERGER' in matched_fp:
        score = max(score, 85)
    if 'POST_ANNOUNCEMENT_PROXY_BACKGROUND' in matched_fp:
        score = max(score, 80)

    return max(0, min(100, score))


def _compute_timing_edge_score(case: dict, matched_fp: list[str], announcement_score: int) -> int:
    """
    0-100: probability that timing edge (pre-announcement window) is still open.
    High = still actionable. Low = window closed or unknown.
    """
    score = 50  # Default uncertain

    # If deal is already announced, window is closed
    if announcement_score > 60:
        return max(0, 10 - (announcement_score - 60) // 10)

    # FP patterns that kill timing edge
    timing_killers = {
        'ALREADY_ANNOUNCED_MERGER',
        'POST_ANNOUNCEMENT_PROXY_BACKGROUND',
        'S8_EQUITY_PLAN_BOILERPLATE',
    }
    if any(fp in timing_killers for fp in matched_fp):
        return 5

    # Recent filing boosts timing edge
    filing_date = str(case.get('filing_date', '') or '')
    if filing_date:
        try:
            from datetime import date
            fd = date.fromisoformat(filing_date[:10])
            today = date.today()
            days_old = (today - fd).days
            if days_old <= 7:
                score += 25
            elif days_old <= 30:
                score += 10
            elif days_old > 90:
                score -= 20
            elif days_old > 180:
                score -= 35
        except Exception:
            pass

    return max(0, min(100, score))


def _compute_process_specificity_score(text: str, matched_ts: list[str]) -> int:
    """0-100: how specific and credible is the process language?"""
    score = 0

    # Specific true-signal phrases
    if _contains_any(text, ['unsolicited proposal', 'unsolicited acquisition']):
        score += 40
    if _contains_any(text, ['superior proposal', 'competing bid', 'topping bid']):
        score += 45
    if _contains_any(text, ['strategic alternatives', 'sale process', 'strategic review']):
        score += 25
    if _contains_any(text, ['retained financial advisor', 'retained investment banker', 'engaged banker']):
        score += 20
    if _contains_any(text, ['special committee', 'board committee', 'strategic alternatives committee']):
        score += 20
    if _contains_any(text, ['go-shop', 'no-shop', 'fiduciary out']):
        score += 30

    # True signal archetype matches
    score += min(len(matched_ts) * 15, 30)

    return max(0, min(100, score))


def _compute_evidence_strength_score(case: dict) -> int:
    """0-100: how strong is the available evidence?"""
    eq = case.get('evidence_quality', {}) or {}
    grade = str(eq.get('evidence_grade', 'F')).strip().upper()
    score_map = {'A': 95, 'B': 75, 'C': 55, 'D': 30, 'F': 5}
    base = score_map.get(grade, 5)

    # Boost if source excerpt is long
    excerpt_len = len(str(case.get('source_excerpt', '') or ''))
    if excerpt_len > 1000:
        base += 10
    elif excerpt_len > 400:
        base += 5

    return max(0, min(100, base))


def _compute_investability_setup_score(
    company_score: int,
    process_score: int,
    evidence_score: int,
    timing_score: int,
    fp_score: int,
) -> int:
    """0-100: composite investability setup score."""
    raw = (
        company_score * 0.30
        + process_score * 0.25
        + evidence_score * 0.20
        + timing_score * 0.15
        - fp_score * 0.20
    )
    return max(0, min(100, int(raw)))


# ── Historical analogue finder ────────────────────────────────────────────────

def _find_historical_analogues(
    text: str,
    matched_ts: list[str],
    matched_fp: list[str],
    company_score: int,
    fp_score: int,
) -> list[str]:
    """Return list of historical case comparators."""
    analogues: list[str] = []

    if 'PUBLIC_UNSOLICITED_PROPOSAL' in matched_ts:
        analogues.append('MDVN (public unsolicited proposal, 116 days before Pfizer deal)')
    if 'SUPERIOR_PROPOSAL_OR_COMPETING_BID' in matched_ts:
        analogues.append('DMTX (superior proposal/competing bid, 39 days before Ultragenyx deal)')
    if 'CREDIBLE_MEDIA_SALE_PROCESS_REPORT' in matched_ts:
        analogues.append('TSRO (media sale process report, 17 days before GSK deal — not EDGAR-catchable)')

    # FP analogues
    if 'ALREADY_ANNOUNCED_MERGER' in matched_fp:
        analogues.append('DEAL_ANNOUNCEMENT_BASELINE (70% of 50-case review — already public, no edge)')
    if 'POST_ANNOUNCEMENT_PROXY_BACKGROUND' in matched_fp:
        analogues.append('POST_ANNOUNCEMENT_PROXY (background section describes completed process)')
    if 'ASSET_SPECIFIC_RIGHTS_ONLY' in matched_fp:
        analogues.append('ASSET_SPECIFIC_RIGHTS_ONLY (4% of 50-case review — product-level, not company-level)')

    # Generic fallback
    if not analogues:
        if company_score >= 50 and fp_score < 40:
            analogues.append('Potential WATCH_ONLY — weak signal, not matching MDVN/DMTX/TSRO archetypes')
        else:
            analogues.append('PRIVATE_BACKGROUND_ONLY archetype (16% of 50-case review — process was not public)')

    return analogues


# ── Strategy bucket assignment ────────────────────────────────────────────────

def _assign_strategy_bucket(
    matched_ts: list[str],
    matched_fp: list[str],
    company_score: int,
    fp_score: int,
    announcement_score: int,
) -> tuple[str, str, str]:
    """
    Returns (primary_bucket, default_research_action, deterministic_reasoning).
    """
    # Hard false positive buckets
    if 'ALREADY_ANNOUNCED_MERGER' in matched_fp or announcement_score >= 75:
        return (
            'ALREADY_ANNOUNCED_DEAL',
            'DISCARD',
            (
                'Filing contains definitive merger agreement language or the deal appears already announced. '
                'Pre-announcement research window is closed. '
                f'Matched FP archetypes: {", ".join(matched_fp) or "none"}.'
            ),
        )

    if 'POST_ANNOUNCEMENT_PROXY_BACKGROUND' in matched_fp:
        return (
            'POST_ANNOUNCEMENT_BACKGROUND',
            'DISCARD',
            'Post-announcement proxy or SC 14D-9 background section detected. '
            'Process described is historical, not live.',
        )

    if 'NEGATED_ACQUISITION_LANGUAGE' in matched_fp:
        return (
            'NEGATED_SIGNAL',
            'DISCARD',
            'Filing explicitly denies acquisition interest or strategic process. '
            'Negation language present — alert is counter-signal.',
        )

    if 'WRONG_DIRECTION_ACQUISITION' in matched_fp:
        return (
            'WRONG_DIRECTION',
            'DISCARD',
            'Company appears to be the acquirer, not the target. '
            'Outbound M&A language detected.',
        )

    if 'S8_EQUITY_PLAN_BOILERPLATE' in matched_fp and not matched_ts:
        return (
            'BOILERPLATE_FALSE_POSITIVE',
            'DISCARD',
            'S-8 equity plan or compensation boilerplate detected. '
            'Standard change-of-control vesting provision, not a strategic process signal.',
        )

    # True signal buckets
    if matched_ts and company_score >= 50:
        primary_ts = matched_ts[0]
        archetype = TRUE_SIGNAL_ARCHETYPES.get(primary_ts, {})
        return (
            f'POTENTIAL_TRUE_SIGNAL:{primary_ts}',
            'WATCH',
            (
                f'Matched true signal archetype: {primary_ts}. '
                f'Historical example: {archetype.get("example_ticker", "unknown")} '
                f'({archetype.get("days_before_deal", "?")} days before deal). '
                f'Company-level process score: {company_score}. '
                f'Requires evidence verification before ESCALATE.'
            ),
        )

    # Asset-specific / partnership
    if ('ASSET_SPECIFIC_RIGHTS_ONLY' in matched_fp
            or 'GENERIC_PARTNERSHIP_OR_LICENSE' in matched_fp):
        if company_score < 30:
            return (
                'ASSET_SPECIFIC_OR_PARTNERSHIP',
                'DISCARD',
                'Asset-specific ROFR/ROFN or generic partnership language. '
                'No company-level strategic process evidence.',
            )
        return (
            'ASSET_SPECIFIC_OR_PARTNERSHIP',
            'WATCH',
            'Possible asset-specific language with some company-level indicators. '
            'Watch for follow-on company-level filings.',
        )

    # Weak signal / unclear
    if company_score >= 35:
        return (
            'WEAK_PROCESS_SIGNAL',
            'WATCH',
            (
                f'Some company-level process language detected (score={company_score}) '
                f'but insufficient for ESCALATE without stronger evidence. '
                f'No match to MDVN/DMTX/TSRO archetypes.'
            ),
        )

    # Default
    return (
        'UNCLEAR_OR_LOW_SIGNAL',
        'DISCARD',
        (
            f'No clear company-level process signal detected. '
            f'Company-level score={company_score}, FP score={fp_score}. '
            f'Matched FP archetypes: {", ".join(matched_fp) or "none"}.'
        ),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def run_strategy_classification(case: dict) -> dict[str, Any]:
    """
    Run deterministic strategy classification on a research case.

    Returns a strategy_features dict to be injected into the prompt and decision.
    Never raises — errors are captured in the returned dict.
    """
    try:
        return _run(case)
    except Exception as exc:
        return {
            'error': f'StrategyClassifier error: {exc}',
            'matched_true_signal_archetypes': [],
            'matched_false_positive_archetypes': [],
            'company_level_process_score': 0,
            'false_positive_score': 50,
            'announcement_status_score': 0,
            'timing_edge_score': 0,
            'evidence_strength_score': 0,
            'process_specificity_score': 0,
            'investability_setup_score': 0,
            'historical_analogues': [],
            'primary_strategy_bucket': 'CLASSIFIER_ERROR',
            'default_research_action': 'NEEDS_HUMAN_REVIEW',
            'deterministic_reasoning': f'Classifier failed: {exc}',
        }


def _run(case: dict) -> dict[str, Any]:
    text = _text_for_case(case)

    matched_ts = phrases_to_true_signal_archetypes(text)
    matched_fp = phrases_to_false_positive_archetypes(text)

    # Dedup preserving order
    seen: set[str] = set()
    matched_ts_dedup: list[str] = []
    for k in matched_ts:
        if k not in seen:
            matched_ts_dedup.append(k)
            seen.add(k)
    seen = set()
    matched_fp_dedup: list[str] = []
    for k in matched_fp:
        if k not in seen:
            matched_fp_dedup.append(k)
            seen.add(k)

    company_score       = _compute_company_level_process_score(text, matched_ts_dedup, matched_fp_dedup)
    fp_score            = _compute_false_positive_score(text, matched_fp_dedup)
    announcement_score  = _compute_announcement_status_score(text, matched_fp_dedup)
    timing_score        = _compute_timing_edge_score(case, matched_fp_dedup, announcement_score)
    evidence_score      = _compute_evidence_strength_score(case)
    process_score       = _compute_process_specificity_score(text, matched_ts_dedup)
    investability_score = _compute_investability_setup_score(
        company_score, process_score, evidence_score, timing_score, fp_score
    )
    analogues = _find_historical_analogues(
        text, matched_ts_dedup, matched_fp_dedup, company_score, fp_score
    )
    bucket, action, reasoning = _assign_strategy_bucket(
        matched_ts_dedup, matched_fp_dedup, company_score, fp_score, announcement_score
    )

    return {
        'matched_true_signal_archetypes':    matched_ts_dedup,
        'matched_false_positive_archetypes': matched_fp_dedup,
        'company_level_process_score':       company_score,
        'false_positive_score':              fp_score,
        'announcement_status_score':         announcement_score,
        'timing_edge_score':                 timing_score,
        'evidence_strength_score':           evidence_score,
        'process_specificity_score':         process_score,
        'investability_setup_score':         investability_score,
        'historical_analogues':              analogues,
        'primary_strategy_bucket':           bucket,
        'default_research_action':           action,
        'deterministic_reasoning':           reasoning,
    }


def format_strategy_features_for_prompt(sf: dict) -> str:
    """Render strategy features as a concise text block for LLM prompt injection."""
    lines = [
        'DETERMINISTIC STRATEGY ANALYSIS (computed before LLM):',
        f'  Primary bucket          : {sf.get("primary_strategy_bucket", "?")}',
        f'  Default action          : {sf.get("default_research_action", "?")}',
        f'  Company-level score     : {sf.get("company_level_process_score", 0)}/100',
        f'  False-positive score    : {sf.get("false_positive_score", 0)}/100',
        f'  Announcement status     : {sf.get("announcement_status_score", 0)}/100',
        f'  Timing edge score       : {sf.get("timing_edge_score", 0)}/100',
        f'  Evidence strength score : {sf.get("evidence_strength_score", 0)}/100',
        f'  Process specificity     : {sf.get("process_specificity_score", 0)}/100',
        f'  Investability setup     : {sf.get("investability_setup_score", 0)}/100',
        '',
        '  Matched TRUE SIGNAL archetypes  : '
        + (', '.join(sf.get('matched_true_signal_archetypes', [])) or 'none'),
        '  Matched FALSE POSITIVE archetypes: '
        + (', '.join(sf.get('matched_false_positive_archetypes', [])) or 'none'),
        '',
        '  Historical analogues:',
    ]
    for a in (sf.get('historical_analogues', []) or ['none']):
        lines.append(f'    - {a}')
    lines += [
        '',
        '  Deterministic reasoning:',
        f'    {sf.get("deterministic_reasoning", "")}',
    ]
    if sf.get('error'):
        lines.append(f'  CLASSIFIER ERROR: {sf["error"]}')
    return '\n'.join(lines)
