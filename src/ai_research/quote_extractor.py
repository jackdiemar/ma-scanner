"""
quote_extractor.py — Deterministic keyword quote extraction and evidence quality grading.

extract_quotes(case, filing_text) -> list[dict]
compute_evidence_quality(case, filing_text, quotes) -> dict

Evidence grades:
  A — full filing text fetched from SEC + exact excerpt present
  B — exact excerpt present + SEC source URL (no full text)
  C — exact excerpt (>50 chars) + any source URL
  D — source URL present but excerpt short/missing, or short excerpt without URL
  F — no excerpt, no source URL, no filing text

No auto-trading. No broker APIs. No transaction recommendation language.
"""
from __future__ import annotations

from datetime import datetime, timezone

# Phrases that suggest a real pre-announcement strategic process
_SIGNAL_PHRASES = [
    'strategic alternatives',
    'sale process',
    'banker retained',
    'financial advisor retained',
    'strategic review',
    'board committee',
    'unsolicited proposal',
    'superior proposal',
    'acquisition proposal',
    'going private',
    'exploration of strategic',
    'evaluate strategic',
    'considering strategic',
    'reviewing strategic',
    'formally retained',
    'engaged to explore',
]

# Phrases that suggest a false positive or already-announced deal
_FP_PHRASES = [
    'merger agreement',
    'definitive agreement',
    'change of control',
    'poison pill',
    'rights plan',
    'shareholder rights',
    'right of first refusal',
    'right of first negotiation',
    'rofr',
    'rofn',
    'boilerplate',
    'no acquisition proposal',
    'have not received',
    'has not received',
    'partnership agreement',
    'collaboration agreement',
    'licensing agreement',
    'risk factor',
    'as is customary',
    'in connection with the merger',
]

_CONTEXT_WINDOW = 250  # chars either side of matched phrase


def _find_phrase_contexts(text: str, phrases: list[str]) -> list[dict]:
    """Find all phrase matches in text, return context windows."""
    results: list[dict] = []
    text_lower  = text.lower()
    seen_spans: set[int] = set()

    for phrase in phrases:
        phrase_lower = phrase.lower()
        start = 0
        while True:
            idx = text_lower.find(phrase_lower, start)
            if idx == -1:
                break
            if idx not in seen_spans:
                seen_spans.add(idx)
                ctx_start = max(0, idx - _CONTEXT_WINDOW)
                ctx_end   = min(len(text), idx + len(phrase) + _CONTEXT_WINDOW)
                context   = text[ctx_start:ctx_end].strip()
                results.append({
                    'phrase':      phrase,
                    'char_offset': idx,
                    'char_count':  len(phrase),
                    'context':     context,
                    'source':      'full_filing_text',
                })
            start = idx + 1

    return results


def extract_quotes(case: dict, filing_text: str | None) -> list[dict]:
    """
    Extract evidence quotes using signal and FP phrase matching.
    Also searches source_excerpt from the case dict.

    Returns list of quote dicts (capped at 8):
        phrase, context, reason, char_count, timing_relevance, source
    """
    quotes: list[dict] = []
    trigger_phrase = str(case.get('trigger_phrase', '')).strip()
    source_excerpt = str(case.get('source_excerpt', '')).strip()

    # 1. Trigger phrase in excerpt
    if trigger_phrase and source_excerpt:
        if trigger_phrase.lower() in source_excerpt.lower():
            quotes.append({
                'phrase':           trigger_phrase,
                'context':          source_excerpt[:600],
                'reason':           'trigger phrase confirmed in source_excerpt',
                'char_count':       len(trigger_phrase),
                'timing_relevance': 'filing_date_based',
                'source':           'source_excerpt',
            })

    # 2. Full filing text signal matches
    if filing_text:
        signal_hits = _find_phrase_contexts(filing_text, _SIGNAL_PHRASES)
        fp_hits     = _find_phrase_contexts(filing_text, _FP_PHRASES)

        for hit in signal_hits[:5]:
            quotes.append({
                'phrase':           hit['phrase'],
                'context':          hit['context'],
                'reason':           'signal phrase found in full filing text',
                'char_count':       hit['char_count'],
                'timing_relevance': 'direct',
                'source':           'full_filing_text',
            })

        for hit in fp_hits[:3]:
            quotes.append({
                'phrase':           hit['phrase'],
                'context':          hit['context'],
                'reason':           'false positive indicator phrase in full filing text',
                'char_count':       hit['char_count'],
                'timing_relevance': 'direct',
                'source':           'full_filing_text',
            })

    # 3. Excerpt fallback — present but trigger phrase not found
    if source_excerpt and not quotes:
        quotes.append({
            'phrase':           '(no trigger match)',
            'context':          source_excerpt[:600],
            'reason':           'source_excerpt present; trigger phrase not confirmed',
            'char_count':       len(source_excerpt),
            'timing_relevance': 'filing_date_based',
            'source':           'source_excerpt',
        })

    return quotes[:8]


def compute_evidence_quality(
    case: dict,
    filing_text: str | None,
    quotes: list[dict],
) -> dict:
    """
    Compute the evidence quality object for a research case.

    Args:
        case:        Research case dict.
        filing_text: Full filing text if fetched, else None.
        quotes:      Output of extract_quotes().

    Returns evidence_quality dict with grade, score, gaps, and quotes.
    """
    source_url     = str(case.get('source_url', '')).strip()
    source_excerpt = str(case.get('source_excerpt', '')).strip()
    filing_type    = str(case.get('filing_type', '')).strip()
    filing_date    = str(case.get('filing_date', '')).strip()
    trigger_phrase = str(case.get('trigger_phrase', '')).strip()

    # A constructed EDGAR URL (company filing page) is lower value than a direct filing URL
    url_is_constructed = bool(case.get('source_url_constructed', False))
    scanner_dry_run    = bool(case.get('scanner_dry_run', False))

    has_source_url     = bool(source_url)
    has_real_source_url = has_source_url and not url_is_constructed
    has_filing_type    = bool(filing_type)
    has_filing_date    = bool(filing_date)
    has_trigger_phrase = bool(trigger_phrase)
    has_exact_excerpt  = len(source_excerpt) > 50
    has_full_text      = bool(filing_text and len(filing_text) > 200)
    source_is_sec      = 'sec.gov' in source_url or 'edgar' in source_url.lower()

    excerpt_length   = len(source_excerpt)
    full_text_length = len(filing_text) if filing_text else 0

    evidence_gaps: list[str] = []
    if scanner_dry_run:
        evidence_gaps.append('scanner ran in dry-run mode — Gate 1 EDGAR fetch skipped; re-run scanner live to populate source fields')
    if not has_real_source_url:
        if url_is_constructed:
            evidence_gaps.append('source URL is a constructed EDGAR search URL (not a direct filing link)')
        else:
            evidence_gaps.append('no source URL')
    if not has_exact_excerpt:
        evidence_gaps.append('source excerpt absent or < 50 chars')
    if not has_full_text:
        evidence_gaps.append('full filing text not fetched')
    if not has_filing_date:
        evidence_gaps.append('filing date unknown')
    if not has_filing_type:
        evidence_gaps.append('filing type unknown')
    if not has_trigger_phrase:
        evidence_gaps.append('no trigger phrase identified')

    # ── Grade ─────────────────────────────────────────────────────────────────
    # Constructed EDGAR URLs cap at D — they're search pages, not direct filing text
    if has_full_text and has_exact_excerpt and source_is_sec and has_real_source_url:
        grade = 'A'
    elif has_exact_excerpt and source_is_sec and has_real_source_url:
        grade = 'B'
    elif has_exact_excerpt and has_real_source_url:
        grade = 'C'
    elif has_real_source_url or url_is_constructed or len(source_excerpt) > 20:
        grade = 'D'
    else:
        grade = 'F'

    can_make_confident = grade in ('A', 'B', 'C')

    # Numeric score for sorting / display
    score = 0
    if has_real_source_url: score += 20
    elif url_is_constructed: score += 8  # partial credit
    if has_filing_type:     score += 10
    if has_filing_date:     score += 10
    if has_exact_excerpt:   score += 25
    if has_full_text:       score += 25
    if source_is_sec:       score += 10

    signal_quotes = [q for q in quotes if 'false positive' not in q.get('reason', '')]
    fp_quotes     = [q for q in quotes if 'false positive' in q.get('reason', '')]

    return {
        'has_source_url':              has_source_url,
        'has_filing_type':             has_filing_type,
        'has_filing_date':             has_filing_date,
        'has_trigger_phrase':          has_trigger_phrase,
        'has_exact_excerpt':           has_exact_excerpt,
        'has_full_filing_text':        has_full_text,
        'excerpt_length':              excerpt_length,
        'full_text_length':            full_text_length,
        'source_is_sec':               source_is_sec,
        'evidence_grade':              grade,
        'evidence_completeness_score': score,
        'evidence_gaps':               evidence_gaps,
        'can_make_confident_decision': can_make_confident,
        'signal_quote_count':          len(signal_quotes),
        'fp_indicator_count':          len(fp_quotes),
        'top_evidence_quotes':         quotes,
        'computed_at':                 datetime.now(timezone.utc).isoformat(),
    }
