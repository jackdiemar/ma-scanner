"""
acquisition_probability_engine.py — Acquisition probability engine.

Combines all signals into a research probability score and bucket.

IMPORTANT: This is a research priority score, NOT investment advice,
NOT a true statistical probability, and NOT a prediction that any deal
will occur. It is purely an internal research triage tool.

No auto-trading, no broker APIs, no buy/sell signals.
Research actions only: ESCALATE, WATCH, WAIT_FOR_PRICE, DISCARD, NEEDS_HUMAN_REVIEW.
"""
from __future__ import annotations

from typing import Optional

from .acquisition_case_schema import PROBABILITY_BUCKETS
from .acquisition_situation_classifier import classify_acquisition_situation
from .acquisition_case_library import (
    load_completed_acquisition_cases,
    retrieve_completed_deal_analogues,
    build_completed_deal_context_for_prompt,
)
from .external_source_provider import get_external_research_status

# Base rate from 50-case and 86-case historical reviews
# ~3.5-6% of scanner hits are true public prior signals
BASE_RATE_SKEPTICISM: float = 4.0

# Maximum score caps per category
_MAX_SCORE = 95.0  # Never return 100 — always leave room for uncertainty


def compute_acquisition_probability(case: dict) -> dict:
    """
    Main entry point. Combines evidence grade, situation scores, analogues, and base rate.

    Returns a structured dict with probability score, bucket, components, and operator guidance.
    Does NOT call LLM. Is deterministic and fast.

    Returns:
        acquisition_research_probability_score: 0-100 (research triage score, not true probability)
        probability_bucket: P0 through P5
        probability_components: individual contribution dict
        base_rate_anchor: float (starting point)
        upward_adjustments: list[dict]
        downward_adjustments: list[dict]
        confidence_level: LOW/MEDIUM/HIGH
        probability_caveats: list[str]
        what_would_move_score_up: list[str]
        what_would_move_score_down: list[str]
        completed_deal_analogues: list[dict]
        closest_analogue: Optional[dict]
        external_research_status: dict
    """
    ticker = str(case.get('ticker', 'UNKNOWN')).strip()

    # 1. Run situation classifier
    situation_result = classify_acquisition_situation(case)

    # 2. Load completed deal library and retrieve analogues
    completed_cases = load_completed_acquisition_cases()
    analogues = retrieve_completed_deal_analogues(case, completed_cases, max_cases=8)
    closest_analogue = analogues[0] if analogues else None

    # 3. Get external research status
    ext_status = get_external_research_status()

    # 4. Compute probability score
    score = BASE_RATE_SKEPTICISM
    upward_adjustments:   list[dict] = []
    downward_adjustments: list[dict] = []

    # Apply evidence grade adjustment
    score, eq_adjustments = _adjust_for_evidence_grade(score, case)
    for adj in eq_adjustments:
        (upward_adjustments if adj['delta'] > 0 else downward_adjustments).append(adj)

    # Apply situation score adjustments
    score, up_adjs, down_adjs = _adjust_for_situation_scores(score, situation_result)
    upward_adjustments.extend(up_adjs)
    downward_adjustments.extend(down_adjs)

    # Apply analogue adjustments
    score, analogue_adjs = _adjust_for_analogues(score, analogues)
    upward_adjustments.extend(analogue_adjs)

    # Cap and assign bucket
    score, bucket = _cap_and_bucket(score, situation_result)

    # 5. Assess confidence
    confidence_level = _assess_confidence(case, situation_result)

    # 6. Caveats
    caveats = _build_caveats(situation_result, ext_status, case)

    # 7. What would move score
    what_up   = _generate_what_would_move_up(situation_result, case)
    what_down = _generate_what_would_move_down(situation_result, case)

    # 8. Successful deal traits
    successful_traits_present, successful_traits_missing = _assess_deal_traits(
        situation_result, analogues, case
    )

    # 9. Probability components
    components = {
        'base_rate_anchor':          BASE_RATE_SKEPTICISM,
        'evidence_grade_adjustment': sum(a['delta'] for a in eq_adjustments),
        'situation_score_adjustment': sum(a['delta'] for a in up_adjs + down_adjs),
        'analogue_adjustment':        sum(a['delta'] for a in analogue_adjs),
        'final_score':               round(score, 1),
    }

    # 10. Online research gaps
    online_gaps = _identify_research_gaps(situation_result, ext_status, case)

    # 11. Why probability is not higher
    why_not_higher = _explain_why_not_higher(situation_result, score, case)

    # 12. Next source queries
    next_queries = _build_next_source_queries(situation_result, case)

    return {
        'ticker':                               ticker,
        'acquisition_research_probability_score': round(score, 1),
        'probability_bucket':                   bucket,
        'probability_components':               components,
        'base_rate_anchor':                     BASE_RATE_SKEPTICISM,
        'upward_adjustments':                   upward_adjustments,
        'downward_adjustments':                 downward_adjustments,
        'confidence_level':                     confidence_level,
        'probability_caveats':                  caveats,
        'what_would_move_score_up':             what_up,
        'what_would_move_score_down':           what_down,
        'completed_deal_analogues':             analogues,
        'closest_analogue':                     closest_analogue,
        'successful_deal_traits_present':       successful_traits_present,
        'successful_deal_traits_missing':       successful_traits_missing,
        'external_research_status':             ext_status,
        'external_sources_reviewed':            [],
        'online_research_gaps':                 online_gaps,
        'is_explicit_process_signal':           situation_result.get('is_explicit_process_signal', False),
        'is_setup_signal_only':                 situation_result.get('is_setup_signal_only', False),
        'is_probabilistic_watch_case':          situation_result.get('is_probabilistic_watch_case', False),
        'why_probability_not_higher':           why_not_higher,
        'evidence_needed_to_upgrade':           what_up[:3] if what_up else [],
        'next_source_queries':                  next_queries,
        'primary_acquisition_situation':        situation_result.get('primary_acquisition_situation', ''),
        'possible_acquisition_situations':      situation_result.get('possible_acquisition_situations', []),
        'situation_scores':                     situation_result.get('situation_scores', {}),
        'deterministic_reasoning':              situation_result.get('deterministic_reasoning', ''),
    }


def _adjust_for_evidence_grade(score: float, case: dict) -> tuple[float, list[dict]]:
    """Adjust score based on evidence grade."""
    adjustments: list[dict] = []

    eq       = case.get('evidence_quality', {}) or {}
    grade    = str(eq.get('evidence_grade', 'F') or 'F').strip().upper()
    eq_score = int(eq.get('evidence_completeness_score', 0) or 0)

    if grade == 'A':
        delta = +8.0
        adjustments.append({'reason': f'Evidence grade A (score={eq_score})', 'delta': delta})
    elif grade == 'B':
        delta = +5.0
        adjustments.append({'reason': f'Evidence grade B (score={eq_score})', 'delta': delta})
    elif grade == 'C':
        delta = +2.0
        adjustments.append({'reason': f'Evidence grade C (score={eq_score})', 'delta': delta})
    elif grade == 'D':
        delta = -2.0
        adjustments.append({'reason': f'Evidence grade D — limited source text available', 'delta': delta})
    elif grade == 'F':
        delta = -3.0
        adjustments.append({'reason': 'Evidence grade F — no source text; high false-positive risk', 'delta': delta})

    total = sum(a['delta'] for a in adjustments)
    return score + total, adjustments


def _adjust_for_situation_scores(
    score: float,
    situation_result: dict,
) -> tuple[float, list[dict], list[dict]]:
    """Apply upward/downward adjustments from situation classifier."""
    up:   list[dict] = []
    down: list[dict] = []
    sit_scores = situation_result.get('situation_scores', {})

    # Already-announced — hard downgrade
    already = sit_scores.get('already_announced', 0)
    if already >= 70:
        delta = -45.0
        down.append({'reason': f'Strong already-announced signal (score={already:.0f}) — no pre-announcement edge', 'delta': delta})
    elif already >= 50:
        delta = -30.0
        down.append({'reason': f'Likely already-announced deal (score={already:.0f})', 'delta': delta})
    elif already >= 30:
        delta = -15.0
        down.append({'reason': f'Possible already-announced language (score={already:.0f})', 'delta': delta})

    # False positive — downgrade
    fp = sit_scores.get('false_positive', 0)
    if fp >= 60:
        delta = -20.0
        down.append({'reason': f'High false-positive risk (score={fp:.0f}) — boilerplate or routine filing', 'delta': delta})
    elif fp >= 40:
        delta = -10.0
        down.append({'reason': f'Elevated false-positive risk (score={fp:.0f})', 'delta': delta})

    # Explicit process signals — upward adjustments
    active_process = sit_scores.get('active_sale_process', 0)
    if active_process >= 60:
        delta = +45.0
        up.append({'reason': f'Strong active sale process signal (score={active_process:.0f}) — strategic alternatives + advisor', 'delta': delta})
    elif active_process >= 40:
        delta = +30.0
        up.append({'reason': f'Moderate active sale process signal (score={active_process:.0f})', 'delta': delta})
    elif active_process >= 20:
        delta = +10.0
        up.append({'reason': f'Weak process signal (score={active_process:.0f}) — needs corroboration', 'delta': delta})

    unsolicited = sit_scores.get('unsolicited_proposal', 0)
    if unsolicited >= 50:
        delta = +50.0
        up.append({'reason': f'Public unsolicited proposal signal (score={unsolicited:.0f}) — MDVN archetype', 'delta': delta})
    elif unsolicited >= 30:
        delta = +25.0
        up.append({'reason': f'Possible unsolicited proposal language (score={unsolicited:.0f})', 'delta': delta})

    competing = sit_scores.get('competing_bid', 0)
    if competing >= 50:
        delta = +50.0
        up.append({'reason': f'Competing bid / superior proposal signal (score={competing:.0f}) — DMTX archetype', 'delta': delta})
    elif competing >= 30:
        delta = +25.0
        up.append({'reason': f'Possible superior proposal language (score={competing:.0f})', 'delta': delta})

    activist = sit_scores.get('activist_pressure', 0)
    if activist >= 50:
        delta = +20.0
        up.append({'reason': f'Activist 13D with acquisition demand (score={activist:.0f})', 'delta': delta})
    elif activist >= 30:
        delta = +10.0
        up.append({'reason': f'Possible activist pressure signal (score={activist:.0f})', 'delta': delta})

    # Setup signals — smaller upward adjustments
    catalyst = sit_scores.get('catalyst_setup', 0)
    if catalyst >= 40:
        delta = +5.0
        up.append({'reason': f'Pipeline catalyst setup (score={catalyst:.0f}) — increases M&A interest but not process signal', 'delta': delta})

    distressed = sit_scores.get('distressed_sale', 0)
    if distressed >= 40:
        delta = +8.0
        up.append({'reason': f'Distressed / cash runway signal (score={distressed:.0f}) — potential forced sale context', 'delta': delta})

    total = sum(a['delta'] for a in up) + sum(a['delta'] for a in down)
    return score + total, up, down


def _adjust_for_analogues(
    score: float,
    analogues: list[dict],
) -> tuple[float, list[dict]]:
    """If strong analogues with HIGH catchability, slight upward adjustment."""
    adjustments: list[dict] = []
    if not analogues:
        return score, adjustments

    top = analogues[0]
    top_score  = top.get('_relevance_score', 0.0)
    top_catch  = str(top.get('public_catchability', '') or '').upper()
    top_sig    = str(top.get('public_signal_category', '') or '').upper()
    top_ticker = top.get('ticker', '?')

    if top_sig == 'TRUE_PUBLIC_PRIOR_SIGNAL' and top_score >= 0.4 and top_catch == 'HIGH':
        delta = +3.0
        adjustments.append({
            'reason': f'Strong analogue to true-signal case {top_ticker} (relevance={top_score:.2f})',
            'delta':  delta,
        })
    elif top_sig == 'NO_VISIBLE_SIGNAL' and top_score >= 0.5:
        delta = -2.0
        adjustments.append({
            'reason': f'Close analogue to no-signal case {top_ticker} — process may be private',
            'delta':  delta,
        })

    total = sum(a['delta'] for a in adjustments)
    return score + total, adjustments


def _cap_and_bucket(score: float, situation_result: dict) -> tuple[float, str]:
    """Cap score and assign probability bucket."""
    bucket = situation_result.get('probability_bucket', 'P2_MONITOR_ONLY')

    # Apply bucket-based caps for consistency
    if bucket == 'P1_DISCARD_ALREADY_ANNOUNCED':
        score = min(score, 8.0)
    elif bucket == 'P0_NO_ACTION_FALSE_POSITIVE':
        score = min(score, 5.0)
    elif bucket == 'P2_MONITOR_ONLY':
        score = min(score, 20.0)
    elif bucket == 'P3_WATCHLIST_SETUP':
        score = min(score, 35.0)
    elif bucket == 'P4_RESEARCH_PRIORITY':
        score = min(score, 60.0)
    elif bucket == 'P5_HIGH_PRIORITY_PROCESS_SIGNAL':
        score = min(score, _MAX_SCORE)

    # Ensure minimum makes sense
    score = max(1.0, score)

    return round(score, 1), bucket


def _assess_confidence(case: dict, situation_result: dict) -> str:
    """Assess confidence level based on evidence quality and signal clarity."""
    eq    = case.get('evidence_quality', {}) or {}
    grade = str(eq.get('evidence_grade', 'F') or 'F').strip().upper()
    bucket = situation_result.get('probability_bucket', '')

    if grade in ('A', 'B') and bucket in ('P4_RESEARCH_PRIORITY', 'P5_HIGH_PRIORITY_PROCESS_SIGNAL'):
        return 'HIGH'
    elif grade in ('A', 'B', 'C') and bucket in ('P1_DISCARD_ALREADY_ANNOUNCED', 'P0_NO_ACTION_FALSE_POSITIVE'):
        return 'HIGH'
    elif grade in ('C',) and bucket in ('P3_WATCHLIST_SETUP', 'P4_RESEARCH_PRIORITY'):
        return 'MEDIUM'
    elif grade in ('D', 'F'):
        return 'LOW'
    else:
        return 'MEDIUM'


def _build_caveats(situation_result: dict, ext_status: dict, case: dict) -> list[str]:
    """Build probability caveats."""
    caveats: list[str] = [
        'This score is a research triage priority indicator, not a true deal probability or investment advice.',
        'Base rate: ~3.5-6% of EDGAR scanner hits have true public prior process signals.',
    ]

    if not ext_status.get('enabled', False):
        caveats.append(
            'External news research is disabled. TSRO-type media-reported sale processes '
            'cannot be detected in this run. Score may understate probability for companies '
            'with active media-reported sale processes.'
        )

    if situation_result.get('is_already_announced', False):
        caveats.append('This appears to be an already-announced deal. Pre-announcement research edge no longer exists.')

    eq = case.get('evidence_quality', {}) or {}
    grade = str(eq.get('evidence_grade', 'F') or 'F').strip().upper()
    if grade in ('D', 'F'):
        caveats.append(
            f'Evidence grade {grade}: source filing text not available. '
            'Score reflects trigger phrase only, not full filing context. '
            'Human review of primary source recommended before acting.'
        )

    return caveats


def _assess_deal_traits(
    situation_result: dict,
    analogues: list[dict],
    case: dict,
) -> tuple[list[str], list[str]]:
    """
    Assess which successful deal traits are present or missing.
    Compares current case against known true-signal analogues.
    """
    present:  list[str] = []
    missing:  list[str] = []

    # Get true signal cases from analogues
    true_signal_analogues = [
        a for a in analogues
        if a.get('public_signal_category') == 'TRUE_PUBLIC_PRIOR_SIGNAL'
    ]

    sit_scores = situation_result.get('situation_scores', {})
    bucket     = situation_result.get('probability_bucket', '')

    # Check for traits present in true-signal analogues
    if sit_scores.get('unsolicited_proposal', 0) >= 30:
        present.append('Public unsolicited proposal language (MDVN archetype)')
    else:
        missing.append('No named acquirer or explicit public proposal (MDVN-type signal absent)')

    if sit_scores.get('competing_bid', 0) >= 30:
        present.append('Superior proposal / competing bid language (DMTX archetype)')
    else:
        missing.append('No superior proposal or competing bid signal (DMTX-type signal absent)')

    if sit_scores.get('active_sale_process', 0) >= 30:
        present.append('Active sale process signal (strategic alternatives + advisor retention)')
    else:
        missing.append('No explicit strategic alternatives or advisor retention language')

    if sit_scores.get('already_announced', 0) < 20:
        present.append('No already-announced deal language — timing edge potentially open')
    else:
        missing.append('Already-announced deal language present — pre-announcement edge closed')

    # External sources
    from .external_source_provider import get_external_research_status
    ext = get_external_research_status()
    if ext.get('enabled'):
        present.append('External news monitoring enabled (TSRO-type signals detectable)')
    else:
        missing.append('External news monitoring disabled — TSRO-type media-reported sale process cannot be detected')

    # Evidence quality
    eq    = case.get('evidence_quality', {}) or {}
    grade = str(eq.get('evidence_grade', 'F') or 'F').strip().upper()
    if grade in ('A', 'B'):
        present.append(f'Strong source evidence (grade {grade}) available for analysis')
    else:
        missing.append(f'Evidence grade {grade} — full filing text not available for analysis')

    return present, missing


def _generate_what_would_move_up(situation_result: dict, case: dict) -> list[str]:
    """Generate actionable list of what evidence would increase the research probability score."""
    items: list[str] = []
    sit_scores = situation_result.get('situation_scores', {})

    if sit_scores.get('already_announced', 0) < 30:
        # Not already announced — what would confirm a real process?
        if sit_scores.get('unsolicited_proposal', 0) < 30:
            items.append('Named acquirer issuing public acquisition proposal (8-K or press release) → MDVN-type signal')
        if sit_scores.get('competing_bid', 0) < 30:
            items.append('Superior proposal determination disclosed in 8-K → DMTX-type signal')
        if sit_scores.get('active_sale_process', 0) < 30:
            items.append('8-K disclosing strategic alternatives review + financial advisor retention')
        if not situation_result.get('is_explicit_process_signal'):
            items.append('Credible media report (Bloomberg/Reuters) naming company in sale process + potential acquirers')

    items.append('Activist 13D Item 4 filing demanding strategic review or company sale')
    items.append('Follow-on filing with explicit banker engagement or special committee formation')
    items.append('Full SEC filing text confirming trigger phrase in company-level process context')

    return items[:5]


def _generate_what_would_move_down(situation_result: dict, case: dict) -> list[str]:
    """Generate list of what evidence would decrease the research probability score."""
    items: list[str] = []
    sit_scores = situation_result.get('situation_scores', {})

    items.append('Company 8-K explicitly denying M&A process or confirming no proposal received')
    items.append('Filing confirms trigger phrase was boilerplate (risk factor, standard license language)')
    items.append('Source filing is post-announcement proxy — background section only, no pre-deal edge')

    if sit_scores.get('distressed_sale', 0) > 0:
        items.append('Company raises capital successfully, resolving cash runway pressure without M&A')

    items.append('Filing date confirmed as historical — signal is stale (>6 months old)')
    items.append('Full filing text review shows trigger phrase in non-acquisition context')

    return items[:5]


def _explain_why_not_higher(situation_result: dict, score: float, case: dict) -> str:
    """Explain why the probability is not higher."""
    bucket = situation_result.get('probability_bucket', '')
    already = situation_result.get('is_already_announced', False)
    is_fp   = situation_result.get('is_false_positive', False)

    if already:
        return 'Already-announced deal language dominates — pre-announcement research edge does not exist for this case.'

    if is_fp:
        return 'High false-positive score indicates this is likely boilerplate or routine filing language, not a genuine M&A process signal.'

    if bucket == 'P2_MONITOR_ONLY':
        return (
            'No explicit process signal detected (strategic alternatives, unsolicited proposal, or competing bid). '
            'Setup signals (catalyst, distress, ROFR) alone do not constitute evidence of an active acquisition process. '
            f'Base rate is ~4% for true public prior signals. Current evidence does not overcome base rate skepticism.'
        )

    if bucket == 'P3_WATCHLIST_SETUP':
        return (
            'Setup signals detected but no explicit process evidence (banker retention, strategic alternatives 8-K, '
            'unsolicited proposal, or competing bid). Watch for follow-on process disclosures before escalating.'
        )

    eq = case.get('evidence_quality', {}) or {}
    grade = str(eq.get('evidence_grade', 'F') or 'F').strip().upper()
    if grade in ('D', 'F'):
        return (
            f'Evidence grade {grade}: insufficient source text to confirm trigger phrase context. '
            'Score is limited until full filing text is reviewed and confirms company-level process language.'
        )

    return (
        f'Score is constrained by base rate skepticism ({BASE_RATE_SKEPTICISM}%) and absence of '
        'corroborating process evidence. Most alerts in this system are correctly identified as '
        'false positives, already-announced deals, or weak setup signals.'
    )


def _identify_research_gaps(situation_result: dict, ext_status: dict, case: dict) -> list[str]:
    """Identify gaps in current research that limit the probability assessment."""
    gaps: list[str] = []

    if not ext_status.get('enabled', False):
        gaps.append(
            'External news/media research disabled — TSRO-type media-reported sale process signals '
            'are structurally undetectable in EDGAR-only workflow'
        )

    eq = case.get('evidence_quality', {}) or {}
    grade = str(eq.get('evidence_grade', 'F') or 'F').strip().upper()
    if grade in ('D', 'F'):
        gaps.append(f'Full SEC filing text not fetched (evidence grade {grade}) — cannot confirm trigger phrase context')

    if not case.get('source_excerpt', ''):
        gaps.append('No source excerpt available — trigger phrase context unknown')

    if situation_result.get('is_setup_signal_only', False):
        gaps.append('Setup signals only — no company-level process language confirmed in filings')

    return gaps


def _build_next_source_queries(situation_result: dict, case: dict) -> list[str]:
    """Build specific next-step queries for the operator."""
    ticker  = case.get('ticker', '')
    company = case.get('company_name', '')
    queries: list[str] = []

    if ticker and company:
        queries.append(f'EDGAR full-text search: {ticker} "{company}" "strategic alternatives" 8-K')
        queries.append(f'EDGAR full-text search: {ticker} "financial advisor" OR "investment bank" 8-K')
        queries.append(f'EDGAR full-text search: {ticker} "unsolicited proposal" OR "superior proposal" 8-K')
        queries.append(f'SEC EDGAR SC 13D search for {ticker} — check Item 4 for acquisition language')

    if not get_external_research_status().get('enabled', False):
        if ticker:
            queries.append(f'Manual news search: "{ticker}" OR "{company}" acquisition sale merger Bloomberg/Reuters')

    return queries[:5]


# ── Formatting ─────────────────────────────────────────────────────────────────

_BUCKET_LABELS: dict[str, str] = {
    'P0_NO_ACTION_FALSE_POSITIVE':      'P0 — False Positive (No Action)',
    'P1_DISCARD_ALREADY_ANNOUNCED':     'P1 — Discard (Already Announced)',
    'P2_MONITOR_ONLY':                  'P2 — Monitor Only',
    'P3_WATCHLIST_SETUP':               'P3 — Watchlist Setup Signal',
    'P4_RESEARCH_PRIORITY':             'P4 — Research Priority',
    'P5_HIGH_PRIORITY_PROCESS_SIGNAL':  'P5 — High Priority Process Signal',
}


def format_probability_for_prompt(prob_result: dict) -> str:
    """Format probability analysis for LLM prompt inclusion."""
    score     = prob_result.get('acquisition_research_probability_score', 0)
    bucket    = prob_result.get('probability_bucket', '')
    bucket_label = _BUCKET_LABELS.get(bucket, bucket)
    confidence = prob_result.get('confidence_level', 'LOW')
    situation  = prob_result.get('primary_acquisition_situation', '')
    reasoning  = prob_result.get('deterministic_reasoning', '')
    ext_status = prob_result.get('external_research_status', {})

    up_adjs   = prob_result.get('upward_adjustments', [])
    down_adjs = prob_result.get('downward_adjustments', [])

    lines: list[str] = [
        'ACQUISITION PROBABILITY ENGINE:',
        '',
        f'  Research Priority Score : {score}/100',
        f'  Probability Bucket      : {bucket_label}',
        f'  Confidence Level        : {confidence}',
        f'  Primary Situation       : {situation}',
        f'  External Research       : {"ENABLED" if ext_status.get("enabled") else "DISABLED"}',
        f'  Base Rate Anchor        : {BASE_RATE_SKEPTICISM}% (true public prior signal base rate)',
        '',
    ]

    if reasoning:
        lines.append(f'  Deterministic reasoning: {reasoning}')
        lines.append('')

    if up_adjs:
        lines.append('  Upward adjustments:')
        for adj in up_adjs[:5]:
            lines.append(f'    +{adj["delta"]:.0f}  {adj["reason"]}')
        lines.append('')

    if down_adjs:
        lines.append('  Downward adjustments:')
        for adj in down_adjs[:5]:
            lines.append(f'    {adj["delta"]:.0f}  {adj["reason"]}')
        lines.append('')

    caveats = prob_result.get('probability_caveats', [])
    if caveats:
        lines.append('  Important caveats:')
        for c in caveats[:3]:
            lines.append(f'    * {c}')
        lines.append('')

    traits_present = prob_result.get('successful_deal_traits_present', [])
    traits_missing = prob_result.get('successful_deal_traits_missing', [])
    if traits_present:
        lines.append('  Successful deal traits PRESENT:')
        for t in traits_present[:3]:
            lines.append(f'    + {t}')
    if traits_missing:
        lines.append('  Successful deal traits MISSING:')
        for t in traits_missing[:3]:
            lines.append(f'    - {t}')

    return '\n'.join(lines)


def format_probability_summary(prob_result: dict) -> str:
    """Short human-readable summary for email/memo."""
    score    = prob_result.get('acquisition_research_probability_score', 0)
    bucket   = prob_result.get('probability_bucket', '')
    bucket_label = _BUCKET_LABELS.get(bucket, bucket)
    sit      = prob_result.get('primary_acquisition_situation', '')
    closest  = prob_result.get('closest_analogue')
    why_not  = prob_result.get('why_probability_not_higher', '')

    lines: list[str] = [
        f'Research Priority Score: {score}/100 | {bucket_label}',
        f'Situation: {sit}',
    ]

    if closest:
        lines.append(
            f'Closest analogue: {closest.get("ticker", "?")} ({closest.get("acquisition_situation_type", "?")})'
        )

    if why_not:
        lines.append(f'Why not higher: {why_not[:200]}')

    return ' | '.join(lines) if len(lines) == 1 else '\n'.join(lines)
