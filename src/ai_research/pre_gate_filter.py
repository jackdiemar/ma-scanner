"""
pre_gate_filter.py — Pre-LLM routing layer.

Runs BEFORE the LLM gate on every research case. Catches cases that are clearly
irrelevant (wrong banker mandate type, non-M&A SA type, severe distress, stale)
and either fast-discards them (no LLM call) or downgrades their recommended action.

This is the first real connectivity tissue: SA classifier + banker mandate + distress
detector feed directly into routing, not just into prompt context.

Returns:
  skip_llm: bool       — if True, use auto_decision instead of calling LLM
  action:   str        — PRE_GATE_DISCARD | PRE_GATE_DOWNGRADE | PASS
  reason:   str        — human-readable explanation
  auto_decision: dict  — pre-built decision dict if skip_llm=True, else None
  signal_strength_score: int — composite signal quality score (0-100) for queue ranking

Research use only. No investment advice.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any


# ── Signal strength scoring weights ──────────────────────────────────────────
# Used for within-tier queue ranking in opportunity_selector.

_SA_TYPE_SCORE = {
    'ACQUISITION_PROCESS': 40,
    'AMBIGUOUS':           15,
    'ASSET_DIVESTITURE':   10,
    'MERGER_OF_EQUALS':     8,
    'PARTNERSHIP_LICENSING': 0,
    'CAPITAL_RAISE':         0,
    'WIND_DOWN':            -10,
    'RESTRUCTURING':        -10,
    'SHAREHOLDER_RETURN':    0,
    'UNKNOWN':               5,
}

_BANKER_MANDATE_SCORE = {
    'SALE_MANDATE':        30,
    'STRATEGIC_REVIEW':    15,
    'UNKNOWN':              5,  # non-zero if it's a known M&A bank
    'DEFENSE_MANDATE':    -20,
    'FAIRNESS_OPINION':   -40,
    'CAPITAL_MARKETS':    -40,
    'PARTNERSHIP_BANKER': -20,
    'RESTRUCTURING_ADVISOR': -20,
}

_BANKER_STRENGTH_SCORE = {
    'STRONG':     15,
    'MODERATE':    8,
    'WEAK':        0,
    'DEFENSIVE': -10,
    'IRRELEVANT': -20,
}

_BANKER_SKEW_BONUS = {
    'MA':   10,
    'BOTH':  3,
    'ECM':  -5,
    'UNKNOWN': 0,
}

_DISTRESS_SCORE = {
    'NONE':     10,
    'MILD':      0,
    'MODERATE': -15,
    'SEVERE':   -35,
    'UNKNOWN':   0,
}

_SIGNAL_QUALITY_SCORE = {
    'AFFIRM':     20,
    'PROCESS':    10,
    'ROFR':        5,
    'MERGER':    -30,
    'BOILERPLATE': -20,
    'SCORE_ONLY': -25,
}


def compute_signal_strength_score(case: dict) -> int:
    """
    Composite signal quality score (0-100 nominal, can exceed or go negative).
    Used to rank cases within the same opportunity queue priority tier.
    Higher = better. Does not map to deal probability.
    """
    sa_type          = case.get('sa_type', 'UNKNOWN')
    mandate_type     = case.get('banker_mandate_type', 'UNKNOWN')
    mandate_strength = case.get('banker_mandate_strength', 'WEAK')
    banker_skew      = case.get('banker_skew', 'UNKNOWN')
    distress         = case.get('distress_severity', 'UNKNOWN')
    signal_quality   = str(case.get('signal_quality', '')).upper()
    is_exclusive     = bool(case.get('banker_is_exclusive', False))

    score = (
        _SA_TYPE_SCORE.get(sa_type, 5)
        + _BANKER_MANDATE_SCORE.get(mandate_type, 0)
        + _BANKER_STRENGTH_SCORE.get(mandate_strength, 0)
        + _BANKER_SKEW_BONUS.get(banker_skew, 0)
        + _DISTRESS_SCORE.get(distress, 0)
        + _SIGNAL_QUALITY_SCORE.get(signal_quality, 0)
        + (10 if is_exclusive else 0)
    )

    # Staleness penalty: -1 per day after 30 days
    filing_date_str = str(case.get('filing_date', '') or '')
    if filing_date_str:
        try:
            filing_dt  = datetime.fromisoformat(filing_date_str.split(' ')[0])
            now_date   = datetime.now(timezone.utc).date()
            days_old   = (now_date - filing_dt.date()).days
            if days_old > 30:
                score -= min((days_old - 30), 40)  # cap at -40
        except (ValueError, TypeError):
            pass

    return max(-50, min(score, 100))


# ── Pre-gate routing ──────────────────────────────────────────────────────────

def _fast_discard(ticker: str, reason: str, classification: str = 'FALSE_POSITIVE') -> dict:
    """Build a fast-discard decision dict (no LLM needed)."""
    from datetime import datetime, timezone
    return {
        'ticker':                              ticker,
        'classification':                      classification,
        'research_action':                     'DISCARD',
        'confidence':                          0.95,
        'investability_score':                 0,
        'evidence_strength':                   'LOW',
        'priced_in_assessment':                'UNKNOWN',
        'time_sensitivity':                    'LOW',
        'why_interesting':                     [],
        'why_not':                             [reason],
        'key_evidence':                        [],
        'missing_information':                 [],
        'next_research_steps':                 [],
        'human_review_questions':              [],
        'short_thesis':                        f'PRE-GATE DISCARD: {reason}',
        'why_this_matters':                    '',
        'why_now':                             '',
        'evidence_summary':                    reason,
        'source_timing_analysis':              '',
        'signal_quality_analysis':             '',
        'priced_in_analysis':                  '',
        'false_positive_risk':                 reason,
        'key_reasons':                         [reason],
        'operator_next_steps':                 [],
        'what_would_change_the_decision':      'New filing with explicit M&A language and appropriate banker mandate',
        'watch_triggers':                      [],
        'discard_reason':                      reason,
        'escalation_reason':                   '',
        'human_review_reason':                 '',
        'strategy_bucket':                     'pre_gate_filtered',
        'matched_true_signal_archetypes':      [],
        'matched_false_positive_archetypes':   ['PRE_GATE_FILTER'],
        'historical_analogue':                 '',
        'true_signal_similarity_score':        0,
        'false_positive_similarity_score':     90,
        'timing_edge_score':                   0,
        'company_level_process_score':         0,
        'process_specificity_score':           0,
        'investability_setup_score':           0,
        'deterministic_strategy_summary':      reason,
        'why_this_fired':                      '',
        'why_this_is_or_is_not_actionable':    reason,
        'why_not_like_true_signal_examples':   '',
        'how_it_compares_to_mdvn_dmtx_tsro':  'Unlike all three — not a company-level M&A process signal.',
        'what_market_may_already_know':        '',
        'what_operator_should_check_next':     '',
        'monitoring_plan':                     '',
        'kill_criteria':                       '',
        'escalation_criteria':                 '',
        'next_filing_or_news_to_watch':        '',
        'suggested_follow_up_queries':         [],
        'one_sentence_bottom_line':            f'Pre-gate filter: {reason}',
        'executive_case_takeaway':             reason,
        'why_this_case_matters_now':           '',
        'source_evidence_read':                '',
        'exact_quotes_used':                   [],
        'acquisition_situation_read':          '',
        'completed_deal_analogue_read':        'None — pre-gate filtered before LLM.',
        'probability_bucket_read':             'P5_NO_SIGNAL',
        'what_is_already_known_by_market':     '',
        'what_is_not_yet_answered':            '',
        'operator_decision':                   'DISCARD',
        'immediate_next_steps':                [],
        'next_sources_to_check':               [],
        'what_would_upgrade':                  'Explicit M&A banker mandate and company-level SA language in new filing',
        'what_would_downgrade':                '',
        'why_this_is_not_actionable_yet':      reason,
        'note':                                f'PRE_GATE_FILTER: {reason}',
        'ran_at':                              datetime.now(timezone.utc).isoformat(),
        'primary_acquisition_situation':       '',
        'possible_acquisition_situations':     [],
        'completed_deal_analogues':            [],
        'closest_completed_deal_analogue':     None,
        'acquisition_research_probability_score': 0,
        'probability_bucket':                  'P5_NO_SIGNAL',
        'probability_components':              {},
        'base_rate_anchor':                    4.0,
        'upward_probability_factors':          [],
        'downward_probability_factors':        [reason],
        'successful_deal_traits_present':      [],
        'successful_deal_traits_missing':      ['company-level M&A mandate', 'acquisition-process SA type'],
        'external_research_status':            {},
        'external_sources_reviewed':           [],
        'online_research_gaps':                [],
        'is_explicit_process_signal':          False,
        'is_setup_signal_only':                False,
        'is_probabilistic_watch_case':         False,
        'why_probability_not_higher':          reason,
        'evidence_needed_to_upgrade':          [],
        'next_source_queries':                 [],
        'sa_type_final':                       '',
        'sa_type_reasoning':                   reason,
        'banker_mandate_final':                '',
        'banker_mandate_reasoning':            reason,
        'banker_mandate_changes_thesis':       False,
        'distress_assessment':                 '',
        'distress_impact_on_thesis':           '',
    }


def run_pre_gate_filter(case: dict) -> dict[str, Any]:
    """
    Pre-gate routing for a research case. Returns routing decision.

    Returns:
        skip_llm: bool
        action:   PRE_GATE_DISCARD | PRE_GATE_DOWNGRADE | PASS
        reason:   str
        auto_decision: dict | None (set if skip_llm=True)
        signal_strength_score: int
    """
    ticker           = str(case.get('ticker', 'UNKNOWN')).upper()
    mandate_type     = case.get('banker_mandate_type', 'UNKNOWN')
    mandate_strength = case.get('banker_mandate_strength', 'WEAK')
    sa_type          = case.get('sa_type', 'UNKNOWN')
    sa_company_level = bool(case.get('sa_is_company_level', True))
    distress_sev     = case.get('distress_severity', 'UNKNOWN')
    distress_driven  = bool(case.get('distress_driven_sa', False))
    signal_quality   = str(case.get('signal_quality', '')).upper()
    banker_skew      = case.get('banker_skew', 'UNKNOWN')

    sss = compute_signal_strength_score(case)

    # ── FAST DISCARD: fairness opinion — deal already agreed ─────────────────
    if mandate_type == 'FAIRNESS_OPINION':
        reason = (
            f'Banker retained for FAIRNESS OPINION — deal already agreed. '
            f'No pre-announcement edge. Fast discard, no LLM needed.'
        )
        return {
            'skip_llm': True, 'action': 'PRE_GATE_DISCARD', 'reason': reason,
            'auto_decision': _fast_discard(ticker, reason, 'ALREADY_ANNOUNCED_DEAL'),
            'signal_strength_score': sss,
        }

    # ── FAST DISCARD: capital markets banker + no explicit SA ─────────────────
    if mandate_type == 'CAPITAL_MARKETS' and sa_type not in ('ACQUISITION_PROCESS', 'AMBIGUOUS'):
        reason = (
            f'Banker retained for CAPITAL MARKETS work ({case.get("banker_name", "unknown firm")}). '
            f'SA type classified as {sa_type}. Not an M&A mandate. Fast discard.'
        )
        return {
            'skip_llm': True, 'action': 'PRE_GATE_DISCARD', 'reason': reason,
            'auto_decision': _fast_discard(ticker, reason, 'FALSE_POSITIVE'),
            'signal_strength_score': sss,
        }

    # ── FAST DISCARD: capital raise framed as strategic alternatives ──────────
    if sa_type == 'CAPITAL_RAISE' and signal_quality != 'AFFIRM':
        reason = (
            f'SA classified as CAPITAL_RAISE — financing/runway extension, not M&A. '
            f'Signal quality {signal_quality} without AFFIRM-level language. Fast discard.'
        )
        return {
            'skip_llm': True, 'action': 'PRE_GATE_DISCARD', 'reason': reason,
            'auto_decision': _fast_discard(ticker, reason, 'FALSE_POSITIVE'),
            'signal_strength_score': sss,
        }

    # ── FAST DISCARD: drug/program-level partnership, not company-level ───────
    if sa_type == 'PARTNERSHIP_LICENSING' and not sa_company_level:
        reason = (
            f'SA classified as PARTNERSHIP_LICENSING at asset/program level — '
            f'not a company-level M&A process. Fast discard.'
        )
        return {
            'skip_llm': True, 'action': 'PRE_GATE_DISCARD', 'reason': reason,
            'auto_decision': _fast_discard(ticker, reason, 'GENERIC_PARTNERSHIP_LANGUAGE'),
            'signal_strength_score': sss,
        }

    # ── FAST DISCARD: defense mandate ────────────────────────────────────────
    if mandate_type == 'DEFENSE_MANDATE':
        reason = (
            f'Banker retained in DEFENSIVE context — responding to unsolicited bid, '
            f'not running a sale. Defense mandate does not constitute a sell-side process signal.'
        )
        return {
            'skip_llm': True, 'action': 'PRE_GATE_DISCARD', 'reason': reason,
            'auto_decision': _fast_discard(ticker, reason, 'FALSE_POSITIVE'),
            'signal_strength_score': sss,
        }

    # ── DOWNGRADE: severe distress — thesis compromised ──────────────────────
    if distress_sev == 'SEVERE':
        pct = case.get('price_change_30d_pct')
        pct_str = f'{pct:.1f}%' if pct is not None else '?%'
        reason = (
            f'SEVERE distress: stock dropped {pct_str} in 30 days before SA filing. '
            f'SA is reactive to crisis, not proactive value maximization. '
            f'Acquirer premium is compressed — thesis fundamentally different from MDVN/DMTX/TSRO. '
            f'Downgrading to NEEDS_HUMAN_REVIEW — human must confirm pipeline value intact before escalating.'
        )
        return {
            'skip_llm': False, 'action': 'PRE_GATE_DOWNGRADE', 'reason': reason,
            'auto_decision': None,
            'signal_strength_score': sss,
            'downgrade_note': reason,
        }

    # ── DOWNGRADE: ECM-skewed banker + no explicit sale mandate language ──────
    if banker_skew == 'ECM' and mandate_type not in ('SALE_MANDATE',) and signal_quality != 'AFFIRM':
        banker_name = case.get('banker_name', 'unknown')
        reason = (
            f'{banker_name.title() if banker_name else "Banker"} skews toward capital markets. '
            f'Mandate type: {mandate_type}. Without explicit sale mandate language, '
            f'this bank retention may indicate financing, not M&A. Flagged for human review.'
        )
        return {
            'skip_llm': False, 'action': 'PRE_GATE_DOWNGRADE', 'reason': reason,
            'auto_decision': None,
            'signal_strength_score': sss,
            'downgrade_note': reason,
        }

    # ── PASS: let LLM run ─────────────────────────────────────────────────────
    return {
        'skip_llm': False, 'action': 'PASS', 'reason': 'Passed pre-gate filter.',
        'auto_decision': None,
        'signal_strength_score': sss,
    }
