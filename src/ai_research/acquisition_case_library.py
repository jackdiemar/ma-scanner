"""
acquisition_case_library.py — Completed acquisition case library.

Loads curated training cases and provides retrieval for live alert comparison.
Used by acquisition_probability_engine and investment_gate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .acquisition_case_schema import (
    ACQUISITION_SITUATION_TYPES,
    PUBLIC_SIGNAL_CATEGORIES,
    PUBLIC_CATCHABILITY,
    VERIFICATION_STATUSES,
    PROBABILITY_BUCKETS,
    REQUIRED_CASE_FIELDS,
)

_HERE       = Path(__file__).resolve().parent
_REPO       = _HERE.parent.parent
CASES_PATH  = _REPO / 'data' / 'training_cases' / 'completed_acquisitions_seed.json'

# Fallback: allow override via env var
_CASES_PATH_OVERRIDE = os.environ.get('ACQUISITION_CASES_PATH', '')
if _CASES_PATH_OVERRIDE:
    CASES_PATH = Path(_CASES_PATH_OVERRIDE)


# ── Load ──────────────────────────────────────────────────────────────────────

def load_completed_acquisition_cases() -> list[dict]:
    """Load all completed acquisition training cases from seed file."""
    if not CASES_PATH.exists():
        return []
    try:
        raw = CASES_PATH.read_text(encoding='utf-8')
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return data
    except Exception:
        return []


# ── Validation ────────────────────────────────────────────────────────────────

def validate_completed_acquisition_cases(cases: list[dict]) -> dict:
    """
    Validate cases against schema.
    Returns summary dict with counts and any errors.
    """
    errors: list[str] = []
    valid_count   = 0
    invalid_count = 0

    for case in cases:
        case_id = case.get('case_id', 'UNKNOWN')
        case_errors: list[str] = []

        # Check required fields
        for field in REQUIRED_CASE_FIELDS:
            if field not in case or case[field] is None or case[field] == '':
                case_errors.append(f'Missing required field: {field}')

        # Check enum values
        sig_cat = case.get('public_signal_category', '')
        if sig_cat and sig_cat not in PUBLIC_SIGNAL_CATEGORIES:
            case_errors.append(f'Invalid public_signal_category: {sig_cat!r}')

        sit_type = case.get('acquisition_situation_type', '')
        if sit_type and sit_type not in ACQUISITION_SITUATION_TYPES:
            case_errors.append(f'Invalid acquisition_situation_type: {sit_type!r}')

        catch = case.get('public_catchability', '')
        if catch and catch not in PUBLIC_CATCHABILITY:
            case_errors.append(f'Invalid public_catchability: {catch!r}')

        vstatus = case.get('verification_status', '')
        if vstatus and vstatus not in VERIFICATION_STATUSES:
            case_errors.append(f'Invalid verification_status: {vstatus!r}')

        if case_errors:
            for e in case_errors:
                errors.append(f'{case_id}: {e}')
            invalid_count += 1
        else:
            valid_count += 1

    return {
        'total':         len(cases),
        'valid':         valid_count,
        'invalid':       invalid_count,
        'errors':        errors,
        'has_errors':    bool(errors),
    }


# ── Filter functions ──────────────────────────────────────────────────────────

def filter_by_situation_type(cases: list[dict], situation_type: str) -> list[dict]:
    """Return cases matching the given acquisition situation type."""
    return [c for c in cases if c.get('acquisition_situation_type') == situation_type]


def get_public_prior_signal_cases(cases: list[dict]) -> list[dict]:
    """Return cases with TRUE_PUBLIC_PRIOR_SIGNAL category."""
    return [c for c in cases if c.get('public_signal_category') == 'TRUE_PUBLIC_PRIOR_SIGNAL']


def get_no_public_signal_cases(cases: list[dict]) -> list[dict]:
    """Return cases with no public prior signal."""
    no_signal_cats = {'NO_VISIBLE_SIGNAL', 'PRIVATE_ONLY', 'POST_ANNOUNCEMENT_ONLY'}
    return [c for c in cases if c.get('public_signal_category') in no_signal_cats]


def get_false_positive_completed_cases(cases: list[dict]) -> list[dict]:
    """Return cases classified as false positives."""
    return [c for c in cases if c.get('public_signal_category') == 'FALSE_POSITIVE']


def get_verified_cases(cases: list[dict]) -> list[dict]:
    """Return only VERIFIED cases (not TEMPLATE or NEEDS_VERIFICATION)."""
    return [c for c in cases if c.get('verification_status') == 'VERIFIED']


def get_template_cases(cases: list[dict]) -> list[dict]:
    """Return TEMPLATE cases."""
    return [c for c in cases if c.get('verification_status') == 'TEMPLATE']


# ── Retrieval scoring ─────────────────────────────────────────────────────────

def _score_relevance(live_case: dict, completed_case: dict) -> float:
    """
    Score relevance of a completed case to a live alert.
    Returns 0.0 to 1.0 float.

    Scoring dimensions:
    1. Signal type match (highest weight)
    2. Public catchability match
    3. Situation type match
    4. Therapeutic area / sector match
    5. Source phrases overlap (keyword matching)
    6. Filing type match
    7. Already-announced detection
    8. Market cap range match
    """
    score = 0.0

    live_text = _extract_text_for_matching(live_case).lower()
    completed_phrases = [p.lower() for p in (completed_case.get('source_quotes', []) or [])]
    completed_evidence = [e.lower() for e in (completed_case.get('pre_announcement_public_evidence', []) or [])]
    all_completed_text = ' '.join(completed_phrases + completed_evidence).lower()

    # 1. Signal type / situation type match (weight: 0.30)
    live_signal_type = str(live_case.get('signal_type', '') or '').lower()
    live_fp_class    = str(live_case.get('fp_classification', '') or '').lower()
    completed_sit    = str(completed_case.get('acquisition_situation_type', '') or '').lower()
    completed_sig    = str(completed_case.get('public_signal_category', '') or '').lower()

    # Map live signal types to completed case patterns
    if 'unsolicited' in live_text and 'unsolicited' in all_completed_text:
        score += 0.25
    elif 'superior_proposal' in live_signal_type or 'competing_bid' in live_signal_type:
        if 'competing_bid' in completed_sit or 'superior_proposal' in completed_sit:
            score += 0.25
    elif 'strategic_alternative' in live_text and 'active_public_sale' in completed_sit:
        score += 0.20
    elif 'media' in live_signal_type and 'media_reported' in completed_sit:
        score += 0.20

    # 2. Public catchability match (weight: 0.15)
    completed_catch = str(completed_case.get('public_catchability', '') or '').upper()
    if completed_catch == 'HIGH':
        # High catchability cases are most instructive for live signals
        score += 0.10
    elif completed_catch == 'NONE' and 'private_background' in completed_sit:
        # Private-only cases are instructive negative examples
        score += 0.05

    # 3. Therapeutic area match (weight: 0.15)
    live_ta = str(live_case.get('company_name', '') + ' ' + str(live_case.get('signal_type', ''))).lower()
    completed_ta = str(completed_case.get('modality_or_therapeutic_area', '') or '').lower()
    completed_sector = str(completed_case.get('sector', '') or '').lower()
    for ta_keyword in ['oncology', 'rare disease', 'gene therapy', 'cardiovascular', 'immunology', 'neurology']:
        if ta_keyword in live_ta and ta_keyword in completed_ta + completed_sector:
            score += 0.10
            break

    # 4. Source phrase overlap (weight: 0.20)
    # Check if key phrases from completed case appear in live text
    matching_phrases = 0
    key_phrases = [
        'strategic alternatives', 'unsolicited proposal', 'superior proposal',
        'sale process', 'financial advisor', 'special committee', 'tender offer',
        'merger agreement', 'going concern', 'banker', 'board of directors',
    ]
    for phrase in key_phrases:
        if phrase in live_text and phrase in all_completed_text:
            matching_phrases += 1
    if matching_phrases >= 3:
        score += 0.20
    elif matching_phrases >= 2:
        score += 0.12
    elif matching_phrases >= 1:
        score += 0.05

    # 5. Filing type match (weight: 0.10)
    live_filing = str(live_case.get('filing_type', '') or '').lower()
    completed_docs = ' '.join(completed_case.get('source_documents', []) or []).lower()
    if live_filing and live_filing in completed_docs:
        score += 0.08
    elif '8-k' in live_filing and '8-k' in completed_docs:
        score += 0.05

    # 6. Verify-and-penalize: already-announced cases are useful negative examples
    already_keywords = ['merger agreement', 'definitive agreement', 'tender offer agreement']
    is_already_announced = any(kw in live_text for kw in already_keywords)
    if is_already_announced and 'already_announced' in completed_sit:
        score += 0.15  # Strong match: both already-announced
    elif is_already_announced and 'true_public_prior_signal' in completed_sig:
        score -= 0.10  # Penalize: live is announced but comparing to true-signal case

    # 7. True-signal archetype match (weight: 0.10)
    live_true_archetypes = live_case.get('matched_true_signal_archetypes', []) or []
    completed_tags = completed_case.get('tags', []) or []
    if live_true_archetypes and 'true_signal' in completed_tags:
        score += 0.10

    # Normalize to [0, 1]
    return max(0.0, min(1.0, score))


def _extract_text_for_matching(case: dict) -> str:
    """Extract all relevant text fields from a live case for keyword matching."""
    text_parts = [
        str(case.get('signal_type', '') or ''),
        str(case.get('trigger_phrase', '') or ''),
        str(case.get('source_excerpt', '') or ''),
        str(case.get('fp_classification', '') or ''),
        str(case.get('memo_section_excerpt', '') or ''),
        str(case.get('short_thesis', '') or ''),
        str(case.get('evidence_summary', '') or ''),
    ]
    for flag in (case.get('scanner_flags', []) or []):
        text_parts.append(str(flag))
    eq = case.get('evidence_quality', {}) or {}
    for q in (eq.get('top_evidence_quotes', []) or []):
        text_parts.append(str(q.get('context', '')))
    return ' '.join(text_parts)


def retrieve_completed_deal_analogues(
    live_case: dict,
    cases: list[dict],
    max_cases: int = 8,
) -> list[dict]:
    """
    Score and retrieve the most relevant completed deal analogues for a live alert.

    Returns top max_cases sorted by relevance score (highest first).
    Includes the score and relevance_reason in each returned case dict.
    """
    if not cases:
        return []

    scored: list[tuple[float, dict]] = []
    for completed in cases:
        relevance_score = _score_relevance(live_case, completed)
        annotated = dict(completed)
        annotated['_relevance_score'] = round(relevance_score, 3)
        annotated['_relevance_reason'] = _build_relevance_reason(live_case, completed, relevance_score)
        scored.append((relevance_score, annotated))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [case for _, case in scored[:max_cases]]


def _build_relevance_reason(live_case: dict, completed: dict, score: float) -> str:
    """Build a brief explanation of why this completed case is relevant."""
    reasons: list[str] = []

    sit = completed.get('acquisition_situation_type', '')
    sig = completed.get('public_signal_category', '')
    catch = completed.get('public_catchability', '')
    ticker = completed.get('ticker', '?')
    vstatus = completed.get('verification_status', '')

    if sig == 'TRUE_PUBLIC_PRIOR_SIGNAL':
        reasons.append(f'{ticker} is a verified true public prior signal case ({sit})')
    elif sig == 'NO_VISIBLE_SIGNAL':
        reasons.append(f'{ticker} is a confirmed no-signal / private background case')
    elif vstatus == 'TEMPLATE':
        reasons.append(f'{ticker} is a template reference (setup context only)')

    if catch == 'HIGH':
        days = completed.get('days_before_announcement')
        if days:
            reasons.append(f'Publicly catchable {days} days before announcement')
    elif catch == 'NONE':
        reasons.append('Not catchable via EDGAR — process was private')

    if score >= 0.5:
        reasons.append(f'Relevance score: {score:.2f} (high match)')
    elif score >= 0.3:
        reasons.append(f'Relevance score: {score:.2f} (moderate match)')
    else:
        reasons.append(f'Relevance score: {score:.2f} (low match — contextual only)')

    return '; '.join(reasons) if reasons else f'Score: {score:.2f}'


# ── Prompt context builder ────────────────────────────────────────────────────

def build_completed_deal_context_for_prompt(
    live_case: dict,
    max_cases: int = 6,
) -> str:
    """
    Build a structured text block summarizing the most relevant completed deals.
    For inclusion in LLM prompt context.
    """
    cases = load_completed_acquisition_cases()
    if not cases:
        return 'COMPLETED DEAL ANALOGUES: Library not loaded or empty.'

    analogues = retrieve_completed_deal_analogues(live_case, cases, max_cases=max_cases)
    if not analogues:
        return 'COMPLETED DEAL ANALOGUES: No relevant analogues found.'

    lines: list[str] = [
        'COMPLETED DEAL ANALOGUES (sorted by relevance to this live alert):',
        '',
    ]

    for i, case in enumerate(analogues, 1):
        ticker   = case.get('ticker', '?')
        company  = case.get('company_name', '')
        sit_type = case.get('acquisition_situation_type', '')
        sig_cat  = case.get('public_signal_category', '')
        catch    = case.get('public_catchability', '')
        vstatus  = case.get('verification_status', '')
        days     = case.get('days_before_announcement')
        acquirer = case.get('acquirer', '')
        score    = case.get('_relevance_score', 0.0)
        reason   = case.get('_relevance_reason', '')

        lines.append(f'  [{i}] {ticker} — {company}')
        lines.append(f'      Situation type  : {sit_type}')
        lines.append(f'      Signal category : {sig_cat}')
        lines.append(f'      Catchability    : {catch}')
        lines.append(f'      Verification    : {vstatus}')
        if acquirer:
            lines.append(f'      Acquirer        : {acquirer}')
        if days is not None:
            lines.append(f'      Days before deal: {days}')
        lines.append(f'      Relevance score : {score:.2f}')
        lines.append(f'      Why relevant    : {reason}')

        # Include key lessons
        true_lessons = case.get('true_signal_lessons', []) or []
        if true_lessons:
            lines.append('      Key lessons:')
            for lesson in true_lessons[:2]:
                lines.append(f'        - {lesson}')

        fp_lessons = case.get('false_positive_lessons', []) or []
        if fp_lessons:
            lines.append('      False-positive lessons:')
            for lesson in fp_lessons[:1]:
                lines.append(f'        - {lesson}')

        operator_lesson = case.get('operator_lesson', '')
        if operator_lesson:
            lines.append(f'      Operator lesson : {operator_lesson[:200]}')

        lines.append('')

    return '\n'.join(lines)


# ── Summary stats ─────────────────────────────────────────────────────────────

def build_library_stats(cases: list[dict]) -> dict:
    """Return summary statistics about the library."""
    if not cases:
        return {'total': 0}

    situation_counts: dict[str, int] = {}
    signal_counts: dict[str, int] = {}
    verification_counts: dict[str, int] = {}
    catchability_counts: dict[str, int] = {}

    for c in cases:
        s = c.get('acquisition_situation_type', 'UNKNOWN')
        situation_counts[s] = situation_counts.get(s, 0) + 1

        sg = c.get('public_signal_category', 'UNKNOWN')
        signal_counts[sg] = signal_counts.get(sg, 0) + 1

        v = c.get('verification_status', 'UNKNOWN')
        verification_counts[v] = verification_counts.get(v, 0) + 1

        ch = c.get('public_catchability', 'UNKNOWN')
        catchability_counts[ch] = catchability_counts.get(ch, 0) + 1

    true_signal_cases = get_public_prior_signal_cases(cases)
    no_signal_cases   = get_no_public_signal_cases(cases)
    verified_cases    = get_verified_cases(cases)
    template_cases    = get_template_cases(cases)

    tickers = [c.get('ticker', '?') for c in cases]

    return {
        'total':                    len(cases),
        'true_public_prior_signal': len(true_signal_cases),
        'no_public_signal':         len(no_signal_cases),
        'verified':                 len(verified_cases),
        'template':                 len(template_cases),
        'situation_type_counts':    situation_counts,
        'signal_category_counts':   signal_counts,
        'verification_counts':      verification_counts,
        'catchability_counts':      catchability_counts,
        'tickers':                  tickers,
    }


def print_library_status() -> None:
    """Print a human-readable library status summary."""
    cases = load_completed_acquisition_cases()
    stats = build_library_stats(cases)
    validation = validate_completed_acquisition_cases(cases)

    print('Completed Acquisition Library Status')
    print('=====================================')
    print(f'  Total cases          : {stats.get("total", 0)}')
    print(f'  Verified             : {stats.get("verified", 0)}')
    print(f'  Template             : {stats.get("template", 0)}')
    print(f'  True public signal   : {stats.get("true_public_prior_signal", 0)}')
    print(f'  No public signal     : {stats.get("no_public_signal", 0)}')
    print()

    print('  Situation type coverage:')
    for sit, count in sorted(stats.get('situation_type_counts', {}).items()):
        print(f'    {sit}: {count}')
    print()

    print('  Signal category coverage:')
    for sig, count in sorted(stats.get('signal_category_counts', {}).items()):
        print(f'    {sig}: {count}')
    print()

    print('  Verification status:')
    for v, count in sorted(stats.get('verification_counts', {}).items()):
        print(f'    {v}: {count}')
    print()

    print('  Tickers: ' + ', '.join(stats.get('tickers', [])))
    print()

    if validation['has_errors']:
        print(f'  Validation: {validation["valid"]}/{validation["total"]} valid, {validation["invalid"]} with errors')
        for err in validation['errors'][:10]:
            print(f'    - {err}')
    else:
        print(f'  Validation: ALL PASS ({validation["total"]} cases)')
