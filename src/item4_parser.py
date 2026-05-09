"""
item4_parser.py — SC 13D Item 4 contextual process-intelligence parser.

Classifies activist intent from Item 4 text of SC 13D filings.
Rule-based, regex/pattern-driven. No LLM, no embeddings, no vector DB.

Classification hierarchy (highest priority wins):
  SALE_PROCESS > STRATEGIC_REVIEW > ACTIVIST_ESCALATION >
  BOARD_CHANGE > CAPITAL_ALLOCATION > GOVERNANCE_ONLY >
  GENERIC_SHAREHOLDER_PRESSURE > PASSIVE_ACCUMULATION > UNKNOWN

Intensity levels:
  STRONG_PROCESS_SIGNAL   — explicit, specific transaction language
  MODERATE_PROCESS_SIGNAL — clear strategic review or escalation pressure
  WEAK_PROCESS_SIGNAL     — directional but not transaction-specific
  GENERIC_ACTIVISM        — governance, capital, board-level pressure
  PASSIVE                 — passive investment purposes

Each result includes triggering phrases, a primary excerpt, and a contextual
rationale so the UI can explain: "Why was this interpreted as sale-process pressure?"
"""

import re

# ── Item 4 section extraction ─────────────────────────────────────────────────

_ITEM4_PATTERNS = [
    re.compile(r'item\s+4[\.\s:–—]+(?:purpose|plans|proposals)', re.I),
    re.compile(r'item\s+4[\.\s:–—]+', re.I),
    re.compile(r'\bitem\s+4\b', re.I),
]

ITEM4_WINDOW = 5000   # chars to extract after Item 4 heading
ITEM5_LOOKAHEAD = 10000  # search range for Item 5 boundary


# ── HIGH-SIGNAL: explicit transaction / sale-process language ─────────────────

_SALE_PROCESS_PHRASES = [
    # Explicit sale demands / exploration
    ('explore a sale',                       95),
    ('sale of the company',                  95),
    ('sale of the issuer',                   95),
    ('selling the company',                  95),
    ('potential sale of the company',        95),
    ('explore a potential sale',             92),
    ('explore strategic alternatives',       90),
    ('strategic alternatives',               85),   # scored lower — needs affirm context
    ('business combination',                 80),
    ('merger or acquisition',                80),
    ('acquisition proposal',                 88),
    ('tender offer',                         88),
    ('going private',                        92),
    ('take private',                         92),
    ('take-private',                         92),
    ('explore a transaction',                88),
    ('potential acquisition',                80),
    # Advisor / banker language
    ('retained a financial advisor',         88),
    ('engaged a financial advisor',          88),
    ('retain a financial advisor',           85),
    ('engage a financial advisor',           85),
    ('retained an investment bank',          88),
    ('engaged an investment bank',           88),
    ('as its exclusive financial advisor',   90),
    ('financial advisor to the company',     85),
    ('financial advisor in connection',      85),
    ('financial advisor',                    68),   # standalone — lower weight
    # Transaction committee / process mechanics
    ('transaction committee',                92),
    ('special committee',                    85),
    ('sale committee',                       92),
    ('explore a merger',                     90),
    ('outreach to potential acquirers',      95),
    ('contact potential acquirers',          92),
    ('solicit interest',                     88),
    ('canvas the market',                    88),
    ('merger discussions',                   92),
    ('acquisition discussions',              90),
    ('negotiations with',                    80),
    ('strategic discussions',                75),
    ('discussions with strategic parties',   82),
    ('explore all strategic',                88),
    ('liquidation',                          80),
    ('wind down',                            75),
    # Explicit board refusal / frustration language (escalation toward sale)
    ('board has refused',                    90),
    ('board has rejected',                   88),
    ('board failed to',                      85),
    ('failure of the board',                 85),
    ('unwilling to pursue',                  90),
    ('dismissed our request',                90),
    ('ignored our proposal',                 90),
    ('declined to engage',                   85),
    ('refused to engage',                    90),
    ('rejected our proposal',                88),
    # Process dissatisfaction language
    ('no process has been initiated',        88),
    ('failure to initiate a process',        88),
    ('inadequate process',                   80),
    ('alternative transaction',              78),
]

# ── STRATEGIC REVIEW: formal review but not yet explicit sale demand ──────────

_STRATEGIC_REVIEW_PHRASES = [
    ('strategic review',                     80),
    ('review of strategic',                  75),
    ('evaluation of strategic',              75),
    ('review all strategic options',         85),
    ('comprehensive review',                 70),
    ('evaluate strategic options',           80),
    ('assess strategic alternatives',        80),
    ('explore value-enhancing',              75),
    ('value-enhancing transaction',          80),
    ('unlock value',                         70),
    ('maximize stockholder value',           62),   # lower — common boilerplate
    ('maximize shareholder value',           62),   # lower — common boilerplate
    ('enhance shareholder value',            58),
    ('value creation alternatives',          70),
    ('consider strategic alternatives',      78),
]

# ── ACTIVIST ESCALATION: proxy mechanics, board replacement ──────────────────

_ESCALATION_PHRASES = [
    ('call a special meeting',               90),
    ('special meeting of stockholders',      90),
    ('special meeting of shareholders',      90),
    ('special meeting',                      80),
    ('proxy contest',                        95),
    ('proxy fight',                          95),
    ('solicitation of proxies',              90),
    ('withhold votes',                       85),
    ('withhold authority',                   80),
    ('vote against',                         78),
    ('remove the board',                     95),
    ('replace the board',                    92),
    ('remove directors',                     92),
    ('replace directors',                    90),
    ('seek to remove',                       88),
    ('oust management',                      90),
    ('demand for shareholder vote',          90),
    ('seek shareholder vote',                85),
    ('written consent',                      80),
    ('consent solicitation',                 88),
    ('dissident slate',                      92),
    ('alternative slate',                    88),
    ('short slate',                          88),
    ('vote no campaign',                     90),
]

# ── BOARD CHANGE: director nominations, board composition ────────────────────

_BOARD_CHANGE_PHRASES = [
    ('board representation',                 75),
    ('board seat',                           75),
    ('director nomination',                  75),
    ('nominate directors',                   72),
    ('nominate candidates',                  70),
    ('appoint directors',                    70),
    ('board refreshment',                    65),
    ('board composition',                    60),
    ('independent directors',                55),
    ('new directors',                        60),
    ('additional directors',                 60),
    ('expand the board',                     65),
    ('change in board',                      68),
    ('board reconstitution',                 78),
    ('board declassification',               65),
]

# ── CAPITAL ALLOCATION: buybacks, dividends, cash deployment ─────────────────

_CAPITAL_ALLOCATION_PHRASES = [
    ('share repurchase',                     55),
    ('stock repurchase',                     55),
    ('buyback',                              55),
    ('return capital',                       60),
    ('return cash',                          60),
    ('return of capital',                    60),
    ('dividend',                             50),
    ('capital allocation',                   55),
    ('excess cash',                          55),
    ('deploy capital',                       55),
    ('cash return',                          55),
    ('capital return',                       55),
    ('share buyback',                        55),
]

# ── GOVERNANCE ONLY: compensation, operations, structure ─────────────────────

_GOVERNANCE_PHRASES = [
    ('corporate governance',                 40),
    ('governance improvements',              40),
    ('executive compensation',               40),
    ('management compensation',              40),
    ('say on pay',                           40),
    ('compensation structure',               40),
    ('operational efficiency',               35),
    ('operational improvements',             35),
    ('operational performance',              35),
    ('cost reduction',                       35),
    ('reduce costs',                         35),
    ('management team',                      30),
    ('strategic direction',                  38),
    ('business strategy',                    35),
]

# ── PASSIVE: investment purposes, no activist intent ─────────────────────────

_PASSIVE_PHRASES = [
    ('investment purposes',                  20),
    ('for investment purposes',              20),
    ('no present intention',                 15),
    ('no current intention',                 15),
    ('do not have any plans',                10),
    ('does not have any plans',              10),
    ('passive investment',                   10),
    ('passive holder',                       10),
    ('for investment',                       15),
    ('monitor the investment',               15),
    ('continue to monitor',                  15),
    ('hold for investment',                  10),
    ('no plans to acquire',                  12),
    ('no plans to take',                     12),
]

# ── DOWNGRADE MARKERS: boilerplate / hedging that suppresses confidence ───────

_DOWNGRADE_MARKERS = [
    ('may explore',                          -20),
    ('could consider',                       -20),
    ('might consider',                       -20),
    ('may consider',                         -20),
    ('no assurance',                         -15),
    ('there can be no assurance',            -20),
    ('cannot guarantee',                     -15),
    ('from time to time',                    -10),
    ('depending on market conditions',       -15),
    ('subject to market conditions',         -15),
    ('subject to various factors',           -12),
    ('does not intend',                      -25),
    ('do not intend',                        -25),
    ('no present plans',                     -25),
    ('no current plans',                     -25),
    ('depending on circumstances',           -12),
    ('in the ordinary course',               -10),
    ('forward-looking',                      -10),
    ('safe harbor',                          -10),
    ('in the past',                          -8),
]

# ── Classification registry (priority order) ─────────────────────────────────

INTENT_BUCKETS = [
    ('SALE_PROCESS',                 _SALE_PROCESS_PHRASES),
    ('STRATEGIC_REVIEW',             _STRATEGIC_REVIEW_PHRASES),
    ('ACTIVIST_ESCALATION',          _ESCALATION_PHRASES),
    ('BOARD_CHANGE',                 _BOARD_CHANGE_PHRASES),
    ('CAPITAL_ALLOCATION',           _CAPITAL_ALLOCATION_PHRASES),
    ('GOVERNANCE_ONLY',              _GOVERNANCE_PHRASES),
    ('GENERIC_SHAREHOLDER_PRESSURE', []),
    ('PASSIVE_ACCUMULATION',         _PASSIVE_PHRASES),
    ('UNKNOWN',                      []),
]

# Buckets that represent genuine process pressure (clear evidence gate)
PROCESS_PRESSURE_BUCKETS = ('SALE_PROCESS', 'STRATEGIC_REVIEW', 'ACTIVIST_ESCALATION')

# Buckets that are false-positive candidates (do NOT clear evidence gate)
FALSE_POSITIVE_BUCKETS = (
    'BOARD_CHANGE', 'CAPITAL_ALLOCATION', 'GOVERNANCE_ONLY',
    'GENERIC_SHAREHOLDER_PRESSURE', 'PASSIVE_ACCUMULATION', 'UNKNOWN',
)


# ── Intensity thresholds ──────────────────────────────────────────────────────

def _score_to_intensity(score, classification):
    if classification == 'SALE_PROCESS':
        if score >= 80:
            return 'STRONG_PROCESS_SIGNAL'
        if score >= 60:
            return 'MODERATE_PROCESS_SIGNAL'
        return 'WEAK_PROCESS_SIGNAL'
    if classification == 'STRATEGIC_REVIEW':
        if score >= 65:
            return 'MODERATE_PROCESS_SIGNAL'
        return 'WEAK_PROCESS_SIGNAL'
    if classification == 'ACTIVIST_ESCALATION':
        if score >= 70:
            return 'MODERATE_PROCESS_SIGNAL'
        return 'WEAK_PROCESS_SIGNAL'
    if classification in ('BOARD_CHANGE',):
        return 'WEAK_PROCESS_SIGNAL'
    if classification == 'PASSIVE_ACCUMULATION':
        return 'PASSIVE'
    return 'GENERIC_ACTIVISM'


# ── Core extraction ───────────────────────────────────────────────────────────

def extract_item4_text(doc_text):
    """
    Extract Item 4 section from SC 13D document text (lowercased).

    Tries heading patterns from most specific to least specific.
    Bounds extraction to Item 5 if found within window, else uses ITEM4_WINDOW.
    Falls back to first ITEM4_WINDOW chars if no section found.

    Returns: (item4_text: str, found_section: bool)
    """
    for pattern in _ITEM4_PATTERNS:
        m = pattern.search(doc_text)
        if m:
            start = m.end()
            search_range = doc_text[start: start + ITEM5_LOOKAHEAD]
            next_item = re.search(r'\bitem\s+5\b', search_range, re.I)
            if next_item and next_item.start() < ITEM4_WINDOW:
                end = start + next_item.start()
            else:
                end = start + ITEM4_WINDOW
            return doc_text[start:end], True

    return doc_text[:ITEM4_WINDOW], False


def _find_phrases(text, phrase_list):
    """Return list of (phrase, score, position) for all matches in text."""
    matches = []
    for phrase, score in phrase_list:
        idx = text.find(phrase)
        if idx >= 0:
            matches.append((phrase, score, idx))
    return matches


def _extract_excerpt(text, phrase, window=150):
    """Extract surrounding context (±window chars) around a matched phrase."""
    idx = text.find(phrase)
    if idx < 0:
        return ''
    start = max(0, idx - window)
    end = min(len(text), idx + len(phrase) + window)
    excerpt = text[start:end].strip()
    return re.sub(r'\s+', ' ', excerpt)


# ── Classification ────────────────────────────────────────────────────────────

def classify_item4(item4_text):
    """
    Classify intent in Item 4 text.

    Returns dict:
      classification       — one of 9 buckets
      intensity            — STRONG/MODERATE/WEAK_PROCESS_SIGNAL, GENERIC_ACTIVISM, PASSIVE
      confidence_score     — 0-100 internal score
      triggering_phrases   — matched phrases (up to 5, descending score)
      primary_excerpt      — ~300-char excerpt around primary match
      contextual_rationale — human-readable interpretation
      is_sale_pressure     — bool: clears process-evidence gate
      is_generic_activism  — bool: governance/passive/capital-only
      downgrade_applied    — bool
      downgrade_phrases    — list of suppression phrases found
      all_bucket_scores    — full score breakdown for inspection
    """
    if not item4_text or not item4_text.strip():
        return _unknown_result('Empty Item 4 text')

    text = item4_text.lower()

    # Compute downgrade factor — proportional to hedge density
    downgrade_score = 0
    downgrade_phrases = []
    for phrase, penalty in _DOWNGRADE_MARKERS:
        if phrase in text:
            downgrade_score += penalty
            downgrade_phrases.append(phrase)
    # Capped raw downgrade — prevents total score going deeply negative
    downgrade_score = max(downgrade_score, -60)

    # Hedge density factor: more hedging markers → more downgrade applied to process buckets.
    # 0 markers = 10%, 1 = 20%, 2 = 40%, 3 = 60%, 4 = 80%, 5+ = 100%
    n_hedge = len(downgrade_phrases)
    hedge_factor = min(1.0, max(0.1, n_hedge * 0.2))

    # Score each bucket
    bucket_scores = {}
    bucket_triggers = {}
    bucket_excerpts = {}

    for bucket_name, phrase_list in INTENT_BUCKETS:
        if not phrase_list:
            continue
        matches = _find_phrases(text, phrase_list)
        if not matches:
            continue

        # Score: primary phrase weight + diminishing returns on secondary matches
        sorted_matches = sorted(matches, key=lambda x: x[1], reverse=True)
        primary_score = sorted_matches[0][1]
        secondary_bonus = sum(m[1] for m in sorted_matches[1:4]) * 0.08
        raw_score = primary_score + secondary_bonus

        # Apply downgrade scaled by hedge density
        if bucket_name in FALSE_POSITIVE_BUCKETS:
            # False-positive buckets: full downgrade applied
            adjusted_score = max(0, raw_score + downgrade_score)
        else:
            # Process-pressure buckets: downgrade proportional to hedge density
            # Heavy hedging (5+ markers) → full downgrade; clean text → minimal downgrade
            adjusted_score = max(0, raw_score + downgrade_score * hedge_factor)

        bucket_scores[bucket_name] = adjusted_score
        bucket_triggers[bucket_name] = [m[0] for m in sorted_matches[:5]]
        bucket_excerpts[bucket_name] = _extract_excerpt(text, sorted_matches[0][0])

    if not bucket_scores:
        return _unknown_result('No classifiable phrases found in Item 4')

    # Priority-first classification: walk hierarchy, take first bucket with score > 0
    # Exception: a dramatically higher-scoring lower-priority bucket can override
    best_classification = None
    best_score = 0

    hierarchy_order = [b[0] for b in INTENT_BUCKETS
                       if b[0] not in ('GENERIC_SHAREHOLDER_PRESSURE', 'UNKNOWN')]

    for bucket in hierarchy_order:
        if bucket not in bucket_scores:
            continue
        score = bucket_scores[bucket]
        if score < 30:
            continue  # too weak to classify
        if best_classification is None:
            best_classification = bucket
            best_score = score
            continue
        # Allow a higher-scoring lower-priority bucket to win if gap > 20
        priority_diff = hierarchy_order.index(bucket) - hierarchy_order.index(best_classification)
        if score > best_score + (priority_diff * 15):
            best_classification = bucket
            best_score = score
        else:
            break  # hierarchy wins

    # Fallback: no bucket cleared threshold — pick highest raw score
    if not best_classification:
        if bucket_scores:
            best_classification = max(bucket_scores, key=lambda k: bucket_scores[k])
            best_score = bucket_scores[best_classification]
        else:
            return _unknown_result('All bucket scores below threshold')

    intensity = _score_to_intensity(best_score, best_classification)

    is_sale_pressure = (
        best_classification in ('SALE_PROCESS',) and
        intensity in ('STRONG_PROCESS_SIGNAL', 'MODERATE_PROCESS_SIGNAL')
    ) or (
        best_classification == 'STRATEGIC_REVIEW' and
        intensity == 'MODERATE_PROCESS_SIGNAL'
    )

    is_generic_activism = best_classification in FALSE_POSITIVE_BUCKETS

    triggering_phrases = bucket_triggers.get(best_classification, [])
    primary_excerpt = bucket_excerpts.get(best_classification, '')
    rationale = _build_rationale(best_classification, intensity, triggering_phrases, downgrade_phrases)

    return {
        'classification':       best_classification,
        'intensity':            intensity,
        'confidence_score':     min(100, round(best_score)),
        'triggering_phrases':   triggering_phrases,
        'primary_excerpt':      primary_excerpt,
        'contextual_rationale': rationale,
        'is_sale_pressure':     is_sale_pressure,
        'is_generic_activism':  is_generic_activism,
        'downgrade_applied':    len(downgrade_phrases) > 0,
        'downgrade_phrases':    downgrade_phrases[:5],
        'all_bucket_scores':    {k: round(v) for k, v in bucket_scores.items()},
    }


def _unknown_result(reason):
    return {
        'classification':       'UNKNOWN',
        'intensity':            'GENERIC_ACTIVISM',
        'confidence_score':     0,
        'triggering_phrases':   [],
        'primary_excerpt':      '',
        'contextual_rationale': reason,
        'is_sale_pressure':     False,
        'is_generic_activism':  True,
        'downgrade_applied':    False,
        'downgrade_phrases':    [],
        'all_bucket_scores':    {},
    }


def _build_rationale(classification, intensity, triggers, downgrade_phrases):
    """Produce a human-readable interpretation for dashboard display."""
    rationale_map = {
        'SALE_PROCESS': (
            'Activist explicitly pressuring for sale, merger, or take-private transaction. '
            'Transaction-specific language indicates genuine process pressure.'
        ),
        'STRATEGIC_REVIEW': (
            'Activist pushing for formal strategic review or alternatives evaluation. '
            'Language suggests board-level process pressure — specific transaction demand not yet explicit.'
        ),
        'ACTIVIST_ESCALATION': (
            'Activist escalating via proxy contest, special meeting demand, or board removal. '
            'High confrontation level — transaction intent not yet stated.'
        ),
        'BOARD_CHANGE': (
            'Activist seeking board seats or director nominations. '
            'Governance-level pressure — potential precursor to strategic review, but no transaction demand.'
        ),
        'CAPITAL_ALLOCATION': (
            'Activist focused on capital return: buybacks, dividends, or cash deployment. '
            'No strategic review or transaction pressure detected.'
        ),
        'GOVERNANCE_ONLY': (
            'Governance or operational criticism only. '
            'No sale, strategic review, or capital return language found.'
        ),
        'GENERIC_SHAREHOLDER_PRESSURE': (
            'General shareholder pressure with no specific identifiable demand. '
            'Boilerplate language or intent unclear from available text.'
        ),
        'PASSIVE_ACCUMULATION': (
            'Passive investment purposes stated. No activist intent declared in Item 4.'
        ),
        'UNKNOWN': (
            'Intent unclear from Item 4 text. Insufficient language to classify.'
        ),
    }

    base = rationale_map.get(classification, 'Classification uncertain.')

    if triggers:
        top_triggers = triggers[:3]
        base += f' Key language: {", ".join(repr(t) for t in top_triggers)}.'

    if downgrade_phrases:
        top_dn = downgrade_phrases[:2]
        base += (
            f' Confidence reduced: boilerplate/hedging detected '
            f'({", ".join(repr(d) for d in top_dn)}).'
        )

    return base


# ── Main entry point ──────────────────────────────────────────────────────────

def parse_13d_item4(doc_text):
    """
    Parse SC 13D document text and classify Item 4 intent.

    Args:
        doc_text: raw lowercased document text (from _fetch_doc_text)

    Returns:
        dict with classification, intensity, excerpts, rationale,
        and explainability fields for every result.
        Always returns a valid dict (never raises).
    """
    if not doc_text:
        return _unknown_result('Empty document')

    try:
        item4_text, found_section = extract_item4_text(doc_text)
        result = classify_item4(item4_text)
        result['item4_section_found'] = found_section
        result['item4_excerpt_len'] = len(item4_text)
        return result
    except Exception as e:
        r = _unknown_result(f'Parse error: {str(e)[:80]}')
        r['item4_section_found'] = False
        r['item4_excerpt_len'] = 0
        return r
