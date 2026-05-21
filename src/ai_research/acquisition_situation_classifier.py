"""
acquisition_situation_classifier.py — Deterministic acquisition situation classifier.

Scores live cases across acquisition situation types without requiring an LLM.
All scoring is keyword-based and deterministic.

Usage:
    from ai_research.acquisition_situation_classifier import classify_acquisition_situation
    result = classify_acquisition_situation(case)
"""
from __future__ import annotations

from .acquisition_case_schema import ACQUISITION_SITUATION_TYPES, PROBABILITY_BUCKETS

# ── Keyword lists ─────────────────────────────────────────────────────────────

ALREADY_ANNOUNCED_KEYWORDS = [
    "agreement and plan of merger",
    "definitive merger agreement",
    "tender offer agreement",
    "merger consideration",
    "go-shop period",
    "no-shop provision",
    "sc 14d-9",
    "proxy statement",
    "definitive agreement",
    "completion of the merger",
    "closing of the merger",
    "per share merger consideration",
    "cash merger consideration",
    "merger sub",
    "merger agreement has been signed",
    "entered into an agreement",
    "transactions contemplated by",
    "recommendation statement",
    "solicitation/recommendation statement",
    "acquisition agreement",
    "tender offer has commenced",
    "tender offer is conditioned",
]

ACTIVE_SALE_PROCESS_KEYWORDS = [
    "strategic alternatives",
    "sale process",
    "special committee",
    "retained financial advisor",
    "board of directors has determined",
    "explore strategic options",
    "reviewing strategic alternatives",
    "evaluate strategic alternatives",
    "soliciting acquisition proposals",
    "retained an investment bank",
    "retained a financial advisor",
    "engaged financial advisors",
    "engaged investment bankers",
    "banker has been retained",
    "formed a special committee",
    "board has formed",
    "explore a potential sale",
    "maximize shareholder value",
    "all strategic alternatives",
    "including a potential sale",
]

UNSOLICITED_PROPOSAL_KEYWORDS = [
    "unsolicited proposal",
    "unsolicited offer",
    "unsolicited bid",
    "reject",
    "rejected proposal",
    "board rejected",
    "not in the best interest",
    "publicly announced proposal",
    "public proposal to acquire",
    "unsolicited acquisition proposal",
    "unsolicited takeover",
]

COMPETING_BID_KEYWORDS = [
    "superior proposal",
    "competing proposal",
    "competing bid",
    "go-shop",
    "alternative acquisition proposal",
    "topping bid",
    "higher offer",
    "superior offer",
    "constitutes a superior proposal",
    "determines to be a superior proposal",
    "regenxbio waives",
    "waives matching rights",
    "matching right",
    "fiduciary out",
    "fiduciary exception",
    "intervening event",
]

MEDIA_SALE_PROCESS_KEYWORDS = [
    "bloomberg reports",
    "reuters reports",
    "wsj reports",
    "wall street journal reports",
    "exploring strategic alternatives",
    "fielding acquisition interest",
    "exploring a potential sale",
    "media reports suggest",
    "reportedly exploring",
    "reportedly in talks",
    "deal talks",
    "acquisition talks",
    "sale process reported",
]

DISTRESSED_KEYWORDS = [
    "going concern",
    "substantial doubt",
    "cash runway",
    "liquidity concerns",
    "exploring strategic alternatives to address",
    "restructuring",
    "workforce reduction",
    "limited cash resources",
    "insufficient funds",
    "inability to continue",
    "may not have sufficient",
    "require additional capital",
    "12 months",
    "operating losses",
    "accumulated deficit",
    "need to raise capital",
]

CATALYST_KEYWORDS = [
    "phase 3",
    "phase iii",
    "pivotal trial",
    "fda approval",
    "nda submission",
    "bla submission",
    "regulatory approval",
    "breakthrough therapy",
    "clinical milestone",
    "pdufa",
    "advisory committee",
    "adcom",
    "phase 2 data",
    "phase 2b",
    "registration trial",
    "confirmatory trial",
]

PARTNERSHIP_KEYWORDS = [
    "collaboration agreement",
    "license agreement",
    "option to acquire",
    "right of first refusal",
    "right of first negotiation",
    "right of first offer",
    "change of control provision",
    "co-promotion",
    "co-development",
    "rofr",
    "rofn",
    "rofo",
    "collaboration and license",
    "licensing and collaboration",
]

ACTIVIST_KEYWORDS = [
    "schedule 13d",
    "sc 13d",
    "item 4",
    "purpose of transaction",
    "acquisition proposal",
    "demand strategic review",
    "board reconstitution",
    "activist investor",
    "13d/a",
    "beneficial ownership",
    "extraordinary transaction",
    "sale of the company",
    "item 4. purpose of",
    "intent to propose",
]

FALSE_POSITIVE_KEYWORDS = [
    "routine",
    "annual report",
    "proxy statement for annual meeting",
    "director election",
    "executive compensation",
    "shareholder vote on compensation",
    "say-on-pay",
    "say on pay",
    "form s-8",
    "equity incentive plan",
    "amendment to equity",
    "stock option plan",
    "2024 equity incentive",
    "2023 equity incentive",
    "2022 equity incentive",
    "employee stock purchase",
    "our chief executive officer",
    "annual meeting of stockholders",
    "at the annual meeting",
    "director bio",
    "director biography",
    "biographical information",
]

# Negative context — these phrases before/near strategic language reduce the score
NEGATION_KEYWORDS = [
    "no proposal has been received",
    "not currently exploring",
    "does not intend to",
    "is not for sale",
    "we do not have",
    "have not received",
    "no unsolicited proposal",
    "boilerplate",
    "risk factor",
    "if we were to be acquired",
    "in the event of",
    "could include a change of control",
]


# ── Text extraction ───────────────────────────────────────────────────────────

def _extract_text_from_case(case: dict) -> str:
    """Extract all text fields from case for keyword matching."""
    text_parts = [
        str(case.get('trigger_phrase', '') or ''),
        str(case.get('source_excerpt', '') or ''),
        str(case.get('memo_section_excerpt', '') or ''),
        str(case.get('signal_type', '') or ''),
        str(case.get('fp_classification', '') or ''),
        str(case.get('short_thesis', '') or ''),
        str(case.get('evidence_summary', '') or ''),
    ]
    for flag in (case.get('scanner_flags', []) or []):
        text_parts.append(str(flag))
    eq = case.get('evidence_quality', {}) or {}
    for q in (eq.get('top_evidence_quotes', []) or []):
        text_parts.append(str(q.get('context', '') or ''))
        text_parts.append(str(q.get('phrase', '') or ''))
    return ' '.join(text_parts).lower()


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count how many keywords appear in text (case-insensitive)."""
    return sum(1 for kw in keywords if kw.lower() in text)


def _has_any_keyword(text: str, keywords: list[str]) -> bool:
    """Return True if any keyword appears in text."""
    return any(kw.lower() in text for kw in keywords)


# ── Individual scorers ────────────────────────────────────────────────────────

def _score_already_announced(case: dict) -> float:
    """Score 0-100. High if definitive merger agreement / tender offer / proxy language present."""
    text = _extract_text_from_case(case)
    hits = _count_keyword_hits(text, ALREADY_ANNOUNCED_KEYWORDS)
    filing_type = str(case.get('filing_type', '') or '').lower()

    score = 0.0

    # Strongest signals
    if 'agreement and plan of merger' in text:
        score += 60.0
    elif 'definitive merger agreement' in text:
        score += 60.0
    elif 'definitive agreement' in text and 'merger' in text:
        score += 55.0
    elif 'tender offer agreement' in text:
        score += 60.0

    # Secondary signals
    if 'merger consideration' in text:
        score += 20.0
    if 'sc 14d-9' in text or 'sc14d-9' in filing_type:
        score += 25.0
    if 'proxy statement' in text and 'merger' in text:
        score += 20.0
    if 'go-shop period' in text or 'no-shop provision' in text:
        score += 25.0
    if 'completion of the merger' in text or 'closing of the merger' in text:
        score += 20.0

    # Filing type signals
    if filing_type in ('defm14a', 'defc14a', 'sc 14d-9', 'sc14d9', 'prem14a'):
        score += 40.0
    elif filing_type in ('sc to-t', 'sc to-i', 'sc tot', 'sc toi'):
        score += 40.0

    # Extra hits add marginal score
    score += min(hits * 3.0, 15.0)

    return min(score, 100.0)


def _score_active_public_sale_process(case: dict) -> float:
    """Score 0-100. High for strategic alternatives + special committee + advisor language."""
    text = _extract_text_from_case(case)

    score = 0.0

    if 'strategic alternatives' in text:
        score += 25.0
        # Evaluate context: is this boilerplate or real?
        if any(kw in text for kw in ['special committee', 'financial advisor retained', 'retained an investment', 'formed a special']):
            score += 30.0
        elif any(kw in text for kw in ['10-k', 'risk factor', 'annual report', 'if we were']):
            score -= 20.0  # Likely boilerplate
        elif '8-k' in str(case.get('filing_type', '') or '').lower():
            score += 15.0  # 8-K strategic alternatives = more credible

    if 'special committee' in text:
        score += 25.0
    if 'sale process' in text:
        score += 20.0
    if 'retained financial advisor' in text or 'engaged financial advisors' in text:
        score += 20.0
    if 'soliciting acquisition proposals' in text:
        score += 25.0
    if 'explore strategic options' in text or 'explore a potential sale' in text:
        score += 15.0

    # Penalize negation language
    if _has_any_keyword(text, NEGATION_KEYWORDS):
        score -= 15.0

    return max(0.0, min(score, 100.0))


def _score_public_unsolicited_proposal(case: dict) -> float:
    """Score 0-100 for public unsolicited proposal scenarios."""
    text = _extract_text_from_case(case)

    score = 0.0

    if 'unsolicited proposal' in text or 'unsolicited offer' in text or 'unsolicited bid' in text:
        score += 50.0
    if 'publicly announced proposal' in text or 'public proposal to acquire' in text:
        score += 40.0
    if 'board rejected' in text or 'rejected proposal' in text:
        score += 20.0
    if 'not in the best interest' in text:
        score += 10.0

    # Penalize if this is in a background section (post-announcement context)
    if 'proxy' in str(case.get('filing_type', '') or '').lower():
        score -= 20.0
    if 'background of the' in text and 'sc 14d-9' in text:
        score -= 20.0

    return max(0.0, min(score, 100.0))


def _score_competing_bid(case: dict) -> float:
    """Score 0-100 for competing bid / superior proposal scenarios."""
    text = _extract_text_from_case(case)

    score = 0.0

    if 'superior proposal' in text:
        score += 50.0
        if 'constitutes a superior proposal' in text or 'determines to be a superior proposal' in text:
            score += 20.0
    if 'competing proposal' in text or 'competing bid' in text:
        score += 35.0
    if 'go-shop' in text or 'go shop' in text:
        score += 20.0
    if 'alternative acquisition proposal' in text:
        score += 20.0
    if 'fiduciary out' in text or 'fiduciary exception' in text:
        score += 15.0
    if 'topping bid' in text or 'higher offer' in text or 'superior offer' in text:
        score += 15.0
    if 'waives matching rights' in text or 'matching right' in text:
        score += 20.0

    return max(0.0, min(score, 100.0))


def _score_media_sale_process(case: dict) -> float:
    """
    Score 0-100 for media-reported sale process.
    Returns low score if external research is disabled (EDGAR-only workflow).
    Media signals cannot be detected in EDGAR filings.
    """
    text = _extract_text_from_case(case)

    # Check if external research is enabled
    import os
    external_enabled = os.environ.get('EXTERNAL_RESEARCH_ENABLED', 'false').lower() == 'true'

    score = 0.0

    # Only score media signals if external sources are available
    if external_enabled:
        hits = _count_keyword_hits(text, MEDIA_SALE_PROCESS_KEYWORDS)
        score = min(hits * 15.0, 60.0)
        if 'reportedly exploring' in text or 'reportedly in talks' in text:
            score += 20.0
        if 'acquisition talks' in text or 'deal talks' in text:
            score += 15.0
    else:
        # EDGAR-only: media signals cannot be detected
        # Return minimal score to reflect structural limitation
        score = 0.0

    return max(0.0, min(score, 100.0))


def _score_distressed_sale(case: dict) -> float:
    """
    Score 0-100 for distressed/cash-runway-driven sale scenarios.
    Distress alone is not enough — needs strategic alternatives or sale process language too.
    """
    text = _extract_text_from_case(case)

    score = 0.0
    distress_hits = _count_keyword_hits(text, DISTRESSED_KEYWORDS)

    if distress_hits == 0:
        return 0.0

    # Distress signals
    if 'going concern' in text:
        score += 30.0
    if 'substantial doubt' in text:
        score += 20.0
    if 'cash runway' in text or 'limited cash resources' in text:
        score += 15.0

    # Distress alone is not sufficient — needs process signal too
    has_process = _has_any_keyword(text, ACTIVE_SALE_PROCESS_KEYWORDS)
    if has_process:
        score += 30.0  # Distress + process = higher confidence
    else:
        score *= 0.5   # Distress without process = setup signal only

    score += min(distress_hits * 3.0, 10.0)

    return max(0.0, min(score, 100.0))


def _score_catalyst_takeout_setup(case: dict) -> float:
    """
    Score 0-100 for pipeline catalyst / regulatory-driven takeout setup.
    This is a SETUP signal (P3_WATCHLIST_SETUP), not a PROCESS signal.
    High catalyst score alone does not imply active M&A process.
    """
    text = _extract_text_from_case(case)

    score = 0.0
    hits = _count_keyword_hits(text, CATALYST_KEYWORDS)

    if hits == 0:
        return 0.0

    if 'phase 3' in text or 'phase iii' in text:
        score += 20.0
    if 'pivotal trial' in text:
        score += 20.0
    if 'fda approval' in text or 'nda submission' in text or 'bla submission' in text:
        score += 25.0
    if 'breakthrough therapy' in text:
        score += 15.0
    if 'pdufa' in text:
        score += 15.0

    score += min(hits * 5.0, 15.0)

    # This is a setup signal — cap at 60 to prevent false escalation
    return max(0.0, min(score, 60.0))


def _score_partnership_rights(case: dict) -> float:
    """
    Score 0-100 for partnership/ROFR scenarios.
    Asset-specific ROFR/ROFN usually stays low — only escalate if company-level language present.
    """
    text = _extract_text_from_case(case)

    score = 0.0
    hits = _count_keyword_hits(text, PARTNERSHIP_KEYWORDS)

    if hits == 0:
        return 0.0

    # Base score for partnership keywords
    score = min(hits * 10.0, 30.0)

    # Detect if this is asset-specific vs company-level
    asset_specific_signals = [
        'with respect to the product', 'for this program', 'for the licensed compound',
        'for the collaboration compound', 'asset', 'specific product', 'licensed product',
    ]
    company_level_signals = [
        'acquisition of the company', 'of all outstanding shares', 'company-level',
        'sale of the company', 'company as a whole', 'acquire the company',
    ]

    is_asset_specific = _has_any_keyword(text, asset_specific_signals)
    is_company_level  = _has_any_keyword(text, company_level_signals)

    if is_asset_specific and not is_company_level:
        score *= 0.4  # Penalize asset-specific
    elif is_company_level:
        score *= 1.5  # Boost company-level

    # Cap partnership signals — they rarely lead to acquisitions without other signals
    return max(0.0, min(score, 50.0))


def _score_activist_pressure(case: dict) -> float:
    """
    Score 0-100 for activist investor / 13D Item 4 acquisition pressure.
    Activist alone without acquisition demand stays low.
    """
    text = _extract_text_from_case(case)
    filing_type = str(case.get('filing_type', '') or '').lower()

    score = 0.0

    if 'schedule 13d' in text or 'sc 13d' in text or '13d' in filing_type:
        score += 20.0
        if 'item 4' in text:
            score += 15.0

    if 'acquisition proposal' in text and 'item 4' in text:
        score += 30.0
    if 'demand strategic review' in text:
        score += 20.0
    if 'sale of the company' in text and ('item 4' in text or '13d' in text):
        score += 25.0
    if 'extraordinary transaction' in text:
        score += 15.0
    if 'board reconstitution' in text:
        score += 10.0

    return max(0.0, min(score, 100.0))


def _score_false_positive(case: dict) -> float:
    """
    Score 0-100 for false positive likelihood.
    High score indicates this is likely a routine filing, not a real process signal.
    """
    text = _extract_text_from_case(case)
    filing_type = str(case.get('filing_type', '') or '').lower()

    score = 0.0

    # Strong FP signals
    if 'annual report' in text or '10-k' in filing_type:
        score += 20.0
    if 'proxy statement for annual meeting' in text or 'annual meeting of stockholders' in text:
        score += 25.0
    if 'form s-8' in text or 's-8' in filing_type or 's8' in filing_type:
        score += 30.0
    if 'executive compensation' in text and 'say-on-pay' in text:
        score += 25.0
    if 'director election' in text or 'election of directors' in text:
        score += 15.0

    # FP archetypes
    fp_class = str(case.get('fp_classification', '') or '').lower()
    fp_archetypes = [
        'already_announced_merger', 'post_announcement_proxy', 'asset_specific_rights',
        'generic_rights_language', 'offering_prospectus', 's8_equity_plan',
        'director_bio_prior_deal', 'negated_acquisition', 'generic_partnership',
    ]
    for archetype in fp_archetypes:
        if archetype in fp_class:
            score += 20.0

    # Negation language
    hits = _count_keyword_hits(text, NEGATION_KEYWORDS)
    score += min(hits * 10.0, 20.0)

    # FP keywords
    fp_hits = _count_keyword_hits(text, FALSE_POSITIVE_KEYWORDS)
    score += min(fp_hits * 5.0, 20.0)

    return max(0.0, min(score, 100.0))


# ── Probability bucket computation ────────────────────────────────────────────

def _compute_probability_bucket(scores: dict, case: dict) -> str:
    """
    Map scores to probability bucket. Start skeptical.

    P1_DISCARD_ALREADY_ANNOUNCED → already-announced dominant
    P0_NO_ACTION_FALSE_POSITIVE  → false positive dominant, low everything else
    P2_MONITOR_ONLY              → no strong signal
    P3_WATCHLIST_SETUP           → setup signals only (catalyst, distress without process, ROFR)
    P4_RESEARCH_PRIORITY         → multiple setup signals or moderate process signal
    P5_HIGH_PRIORITY_PROCESS_SIGNAL → explicit process evidence (public sale process, unsolicited, competing bid)
    """
    already_score    = scores.get('already_announced', 0)
    process_score    = scores.get('active_sale_process', 0)
    unsolicited_score = scores.get('unsolicited_proposal', 0)
    competing_score  = scores.get('competing_bid', 0)
    distressed_score = scores.get('distressed_sale', 0)
    catalyst_score   = scores.get('catalyst_setup', 0)
    partnership_score = scores.get('partnership_rights', 0)
    activist_score   = scores.get('activist_pressure', 0)
    fp_score         = scores.get('false_positive', 0)
    media_score      = scores.get('media_sale_process', 0)

    # Maximum explicit process signal
    max_process = max(process_score, unsolicited_score, competing_score, media_score)
    # Maximum setup signal
    max_setup   = max(catalyst_score, distressed_score, activist_score, partnership_score)

    # P1: Already announced — highest priority identification
    if already_score >= 50:
        return 'P1_DISCARD_ALREADY_ANNOUNCED'

    # P0: False positive dominant + no meaningful process signal
    if fp_score >= 50 and max_process < 20 and already_score < 30:
        return 'P0_NO_ACTION_FALSE_POSITIVE'

    # P5: Explicit, strong process signal
    if max_process >= 50:
        return 'P5_HIGH_PRIORITY_PROCESS_SIGNAL'

    # P4: Moderate process signal OR multiple credible setup signals
    if max_process >= 30:
        return 'P4_RESEARCH_PRIORITY'
    if max_setup >= 40 and max_process >= 15:
        return 'P4_RESEARCH_PRIORITY'
    if activist_score >= 40:
        return 'P4_RESEARCH_PRIORITY'

    # P3: Setup signals without explicit process
    if max_setup >= 25 and fp_score < 40:
        return 'P3_WATCHLIST_SETUP'
    if catalyst_score >= 30 and fp_score < 30:
        return 'P3_WATCHLIST_SETUP'

    # P2: Weak signal or ambiguous
    if max_process >= 10 or max_setup >= 15:
        return 'P2_MONITOR_ONLY'

    # Default: no meaningful signal
    return 'P2_MONITOR_ONLY'


# ── Main classifier ───────────────────────────────────────────────────────────

def classify_acquisition_situation(case: dict) -> dict:
    """
    Main entry point. Takes a live case dict (from scanner/evidence audit).
    Returns classification dict with all scores, situation types, and probability bucket.

    Does not require LLM. All scoring is deterministic keyword-matching.
    """
    ticker = str(case.get('ticker', 'UNKNOWN')).strip()

    # Run all scorers
    scores = {
        'already_announced':     _score_already_announced(case),
        'active_sale_process':   _score_active_public_sale_process(case),
        'unsolicited_proposal':  _score_public_unsolicited_proposal(case),
        'competing_bid':         _score_competing_bid(case),
        'media_sale_process':    _score_media_sale_process(case),
        'distressed_sale':       _score_distressed_sale(case),
        'catalyst_setup':        _score_catalyst_takeout_setup(case),
        'partnership_rights':    _score_partnership_rights(case),
        'activist_pressure':     _score_activist_pressure(case),
        'false_positive':        _score_false_positive(case),
    }

    # Sort situations by score
    situation_score_map = {
        'ALREADY_ANNOUNCED_DEAL':          scores['already_announced'],
        'ACTIVE_PUBLIC_SALE_PROCESS':      scores['active_sale_process'],
        'PUBLIC_UNSOLICITED_PROPOSAL':     scores['unsolicited_proposal'],
        'COMPETING_BID_OR_SUPERIOR_PROPOSAL': scores['competing_bid'],
        'MEDIA_REPORTED_SALE_PROCESS':     scores['media_sale_process'],
        'DISTRESSED_OR_CASH_RUNWAY_SALE':  scores['distressed_sale'],
        'PIPELINE_CATALYST_DRIVEN_TAKEOUT': scores['catalyst_setup'],
        'PARTNERSHIP_RIGHTS_CONVERTED_TO_ACQUISITION': scores['partnership_rights'],
        'ACTIVIST_PRESSURE_OR_13D':        scores['activist_pressure'],
        'FALSE_POSITIVE_ONLY':             scores['false_positive'],
    }

    # Sort by score descending
    sorted_situations = sorted(
        situation_score_map.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    primary_situation = sorted_situations[0][0] if sorted_situations else 'INSUFFICIENT_EVIDENCE'
    primary_score     = sorted_situations[0][1] if sorted_situations else 0.0

    # Secondary situations (score > 15 and not primary)
    possible_situations = [
        sit for sit, score in sorted_situations[1:]
        if score >= 15 and sit != primary_situation
    ][:3]

    # Compute probability bucket
    bucket = _compute_probability_bucket(scores, case)

    # Determine if this is an explicit process signal or setup-only
    is_explicit_process = any([
        scores['active_sale_process'] >= 40,
        scores['unsolicited_proposal'] >= 40,
        scores['competing_bid'] >= 40,
        scores['media_sale_process'] >= 40,
    ])
    is_setup_only = (
        not is_explicit_process
        and max(scores['catalyst_setup'], scores['distressed_sale'], scores['activist_pressure']) >= 25
    )
    is_already_announced = scores['already_announced'] >= 50

    # Build deterministic reasoning summary
    reasoning_parts: list[str] = []
    if is_already_announced:
        reasoning_parts.append(f'Already-announced deal language detected (score={scores["already_announced"]:.0f}). This is a baseline case — no pre-announcement edge.')
    elif is_explicit_process:
        top_process = max([
            ('ACTIVE_PUBLIC_SALE_PROCESS', scores['active_sale_process']),
            ('PUBLIC_UNSOLICITED_PROPOSAL', scores['unsolicited_proposal']),
            ('COMPETING_BID_OR_SUPERIOR_PROPOSAL', scores['competing_bid']),
            ('MEDIA_REPORTED_SALE_PROCESS', scores['media_sale_process']),
        ], key=lambda x: x[1])
        reasoning_parts.append(f'Explicit process signal detected: {top_process[0]} (score={top_process[1]:.0f}). Warrants escalated research.')
    elif is_setup_only:
        reasoning_parts.append(f'Setup signal detected (no explicit process): catalyst={scores["catalyst_setup"]:.0f}, distressed={scores["distressed_sale"]:.0f}, activist={scores["activist_pressure"]:.0f}. Monitor for follow-on process disclosures.')
    else:
        reasoning_parts.append(f'No strong acquisition signal detected. FP score={scores["false_positive"]:.0f}. Continue routine monitoring.')

    if scores['false_positive'] >= 40:
        reasoning_parts.append(f'High false-positive risk (score={scores["false_positive"]:.0f}). Likely boilerplate or already-announced merger language.')

    deterministic_reasoning = ' '.join(reasoning_parts)

    return {
        'ticker':                       ticker,
        'primary_acquisition_situation': primary_situation,
        'primary_situation_score':       round(primary_score, 1),
        'possible_acquisition_situations': possible_situations,
        'situation_scores':              {k: round(v, 1) for k, v in scores.items()},
        'probability_bucket':            bucket,
        'is_explicit_process_signal':    is_explicit_process,
        'is_setup_signal_only':          is_setup_only,
        'is_probabilistic_watch_case':   is_setup_only and not is_explicit_process,
        'is_already_announced':          is_already_announced,
        'is_false_positive':             scores['false_positive'] >= 50,
        'deterministic_reasoning':       deterministic_reasoning,
        'company_level_process_score':   round(max(
            scores['active_sale_process'],
            scores['unsolicited_proposal'],
            scores['competing_bid'],
        ), 1),
        'process_specificity_score':     round(max(
            scores['active_sale_process'],
            scores['unsolicited_proposal'],
            scores['competing_bid'],
        ), 1),
        'investability_setup_score':     round(max(
            scores['active_sale_process'],
            scores['unsolicited_proposal'],
            scores['competing_bid'],
            scores['activist_pressure'] * 0.8,
            scores['catalyst_setup'] * 0.5,
        ), 1),
        'false_positive_score':          round(scores['false_positive'], 1),
        'timing_edge_score':             round(
            max(0, 100 - max(scores['already_announced'], scores['false_positive']))
            * (1.0 if is_explicit_process else 0.4 if is_setup_only else 0.1),
            1
        ),
    }


def format_situation_classification_for_prompt(result: dict) -> str:
    """Format situation classification result for inclusion in LLM prompt."""
    lines: list[str] = [
        'DETERMINISTIC ACQUISITION SITUATION ANALYSIS:',
        '',
        f'  Primary situation    : {result.get("primary_acquisition_situation", "?")} (score={result.get("primary_situation_score", 0):.0f})',
        f'  Probability bucket   : {result.get("probability_bucket", "?")}',
        f'  Explicit process     : {result.get("is_explicit_process_signal", False)}',
        f'  Setup signal only    : {result.get("is_setup_signal_only", False)}',
        f'  Already announced    : {result.get("is_already_announced", False)}',
        f'  False positive risk  : {result.get("is_false_positive", False)}',
        '',
        '  Situation scores:',
    ]

    for sit, score in sorted(
        result.get('situation_scores', {}).items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        bar = '#' * int(score / 10)
        lines.append(f'    {sit:<40} {score:>5.0f}  {bar}')

    lines += [
        '',
        f'  Reasoning: {result.get("deterministic_reasoning", "")}',
    ]

    possible = result.get('possible_acquisition_situations', [])
    if possible:
        lines.append(f'  Also possible: {", ".join(possible)}')

    return '\n'.join(lines)
