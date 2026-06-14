"""
sa_classifier.py — Strategic alternatives type classifier + banker mandate classifier + distress detector.

Functions:
  classify_banker_mandate(excerpt, trigger_phrase) → banker name, mandate type, exclusivity, strength
  classify_sa_type(excerpt, trigger_phrase, flags, has_banker) → SA type + confidence
  detect_distress(ticker, filing_date_str) → price change 30d before filing

Banker Mandate Types:
  SALE_MANDATE        — exclusive advisor to explore/run a sale of the company
  STRATEGIC_REVIEW    — general evaluation of strategic alternatives, sale is one option
  DEFENSE_MANDATE     — retained in response to unsolicited bid; defending, not selling
  FAIRNESS_OPINION    — retained to opine on an already-agreed deal; no pre-process edge
  CAPITAL_MARKETS     — underwriter, placement agent, financing; not M&A
  PARTNERSHIP_BANKER  — identifying collaboration/licensing partners; not whole-company
  RESTRUCTURING_ADVISOR — financial restructuring, debt advisory
  UNKNOWN             — banker mentioned but mandate unclear from excerpt

Mandate Strength:
  STRONG     — exclusive sale mandate, explicit process language
  MODERATE   — strategic review with acquisition as stated option
  WEAK       — general advisor, mandate unstated
  DEFENSIVE  — mandate is defense, not offense
  IRRELEVANT — fairness opinion, capital markets, financing

SA Types: ACQUISITION_PROCESS | CAPITAL_RAISE | ASSET_DIVESTITURE | PARTNERSHIP_LICENSING |
          MERGER_OF_EQUALS | WIND_DOWN | RESTRUCTURING | SHAREHOLDER_RETURN | AMBIGUOUS

Distress Severity: SEVERE (>40% drop) | MODERATE (20-40%) | MILD (10-20%) | NONE

Research use only. No investment advice.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

# ── Banker mandate constants ──────────────────────────────────────────────────

BM_SALE_MANDATE     = 'SALE_MANDATE'
BM_STRATEGIC_REVIEW = 'STRATEGIC_REVIEW'
BM_DEFENSE          = 'DEFENSE_MANDATE'
BM_FAIRNESS         = 'FAIRNESS_OPINION'
BM_CAPITAL_MARKETS  = 'CAPITAL_MARKETS'
BM_PARTNERSHIP      = 'PARTNERSHIP_BANKER'
BM_RESTRUCTURING    = 'RESTRUCTURING_ADVISOR'
BM_UNKNOWN          = 'UNKNOWN'

MS_STRONG     = 'STRONG'
MS_MODERATE   = 'MODERATE'
MS_WEAK       = 'WEAK'
MS_DEFENSIVE  = 'DEFENSIVE'
MS_IRRELEVANT = 'IRRELEVANT'

# ── Known M&A banks and their typical mandate bias ───────────────────────────
# skew: MA = primarily M&A advisory, ECM = primarily capital markets, BOTH = mixed

_BANKER_REGISTRY: dict[str, dict] = {
    # Pure M&A / process banks
    'lazard':              {'skew': 'MA',  'tier': 'BULGE'},
    'evercore':            {'skew': 'MA',  'tier': 'ELITE'},
    'centerview':          {'skew': 'MA',  'tier': 'ELITE'},
    'perella weinberg':    {'skew': 'MA',  'tier': 'ELITE'},
    'moelis':              {'skew': 'MA',  'tier': 'ELITE'},
    'guggenheim':          {'skew': 'MA',  'tier': 'BOUTIQUE'},
    'houlihan lokey':      {'skew': 'MA',  'tier': 'BOUTIQUE'},
    'rothschild':          {'skew': 'MA',  'tier': 'BOUTIQUE'},
    'qatalyst':            {'skew': 'MA',  'tier': 'BOUTIQUE'},
    # Bulge bracket (both MA and ECM)
    'goldman sachs':       {'skew': 'BOTH', 'tier': 'BULGE'},
    'goldman':             {'skew': 'BOTH', 'tier': 'BULGE'},
    'morgan stanley':      {'skew': 'BOTH', 'tier': 'BULGE'},
    'jp morgan':           {'skew': 'BOTH', 'tier': 'BULGE'},
    'j.p. morgan':         {'skew': 'BOTH', 'tier': 'BULGE'},
    'jpmorgan':            {'skew': 'BOTH', 'tier': 'BULGE'},
    'bank of america':     {'skew': 'BOTH', 'tier': 'BULGE'},
    'bofa':                {'skew': 'BOTH', 'tier': 'BULGE'},
    'citi':                {'skew': 'BOTH', 'tier': 'BULGE'},
    'citigroup':           {'skew': 'BOTH', 'tier': 'BULGE'},
    'barclays':            {'skew': 'BOTH', 'tier': 'BULGE'},
    'ubs':                 {'skew': 'BOTH', 'tier': 'BULGE'},
    'deutsche bank':       {'skew': 'BOTH', 'tier': 'BULGE'},
    'credit suisse':       {'skew': 'BOTH', 'tier': 'BULGE'},
    # Biotech-focused (mixed mandate, frequent ECM)
    'leerink':             {'skew': 'BOTH', 'tier': 'BIOTECH'},
    'leerink partners':    {'skew': 'BOTH', 'tier': 'BIOTECH'},
    'td cowen':            {'skew': 'ECM',  'tier': 'BIOTECH'},
    'cowen':               {'skew': 'ECM',  'tier': 'BIOTECH'},
    'jefferies':           {'skew': 'BOTH', 'tier': 'BIOTECH'},
    'piper sandler':       {'skew': 'ECM',  'tier': 'BIOTECH'},
    'stifel':              {'skew': 'ECM',  'tier': 'BIOTECH'},
    'rbc':                 {'skew': 'BOTH', 'tier': 'BIOTECH'},
    'rbc capital':         {'skew': 'BOTH', 'tier': 'BIOTECH'},
    'bmo':                 {'skew': 'BOTH', 'tier': 'BIOTECH'},
    'raymond james':       {'skew': 'ECM',  'tier': 'REGIONAL'},
    'oppenheimer':         {'skew': 'ECM',  'tier': 'REGIONAL'},
    'needham':             {'skew': 'ECM',  'tier': 'REGIONAL'},
    'william blair':       {'skew': 'BOTH', 'tier': 'REGIONAL'},
    'canaccord':           {'skew': 'ECM',  'tier': 'REGIONAL'},
    'hc wainwright':       {'skew': 'ECM',  'tier': 'REGIONAL'},
    'svb securities':      {'skew': 'ECM',  'tier': 'BIOTECH'},
    'svb':                 {'skew': 'ECM',  'tier': 'BIOTECH'},
}

# ── Mandate phrase patterns ───────────────────────────────────────────────────

_SALE_MANDATE_STRONG = [
    'exclusive financial advisor',
    'as its exclusive financial advisor',
    'as our exclusive financial advisor',
    'sole financial advisor',
    'to explore a sale',
    'to assist in exploring a potential sale',
    'to assist with a potential sale',
    'to solicit interest from potential acquirers',
    'to assist in identifying potential acquirers',
    'to assist the board in exploring strategic alternatives intended to maximize',
    'to assist in conducting a sale process',
    'process to sell the company',
    'auction process',
    'market check',
]

_STRATEGIC_REVIEW_MODERATE = [
    'to assist the board in evaluating strategic alternatives',
    'to evaluate strategic alternatives',
    'to assist in evaluating and pursuing strategic alternatives',
    'to assist management in evaluating',
    'to advise the board',
    'to assist with strategic alternatives',
    'to assist in exploring strategic alternatives',
    'financial advisor to assist',
    'retained as financial advisor in connection with its review of strategic alternatives',
]

_DEFENSE_MANDATE = [
    'in connection with the unsolicited',
    'in response to the proposal',
    'to assist in evaluating the proposal',
    'to assist in responding to',
    'in connection with the hostile',
    'in connection with defending',
    'to assist the board in evaluating the unsolicited',
    'rights plan',
    'shareholder rights plan',
    'poison pill',
]

_FAIRNESS_MANDATE = [
    'to render a fairness opinion',
    'to deliver a fairness opinion',
    'to provide a fairness opinion',
    'to opine as to the fairness',
    'fairness opinion in connection with',
    'financial advisor in connection with the merger',
    'in connection with the proposed merger',
    'in connection with the definitive agreement',
]

_CAPITAL_MARKETS_MANDATE = [
    'as underwriter',
    'as book-running manager',
    'as joint book-runner',
    'as placement agent',
    'to assist with a potential financing',
    'to assist with capital markets',
    'as financial advisor in connection with the offering',
    'in connection with the registered direct',
    'in connection with the public offering',
    'at-the-market offering',
    'atm facility',
    'as sales agent',
]

_PARTNERSHIP_MANDATE = [
    'to identify potential partners',
    'to assist in identifying licensing',
    'to assist with partnership opportunities',
    'to identify potential collaboration',
    'to assist in out-licensing',
    'to assist with business development',
    'bd advisor',
]

_RESTRUCTURING_MANDATE = [
    'restructuring advisor',
    'financial restructuring',
    'debt restructuring',
    'as financial advisor in connection with the restructuring',
    'to assist with the restructuring',
]

_EXCLUSIVITY_MARKERS = [
    'exclusive financial advisor',
    'as its exclusive',
    'as our exclusive',
    'sole financial advisor',
]


def _detect_banker_name(text: str) -> tuple[str, dict]:
    """Return (banker_name_normalized, registry_entry) or ('', {})."""
    low = text.lower()
    # Sort by length descending so longer names match first (e.g. "leerink partners" before "leerink")
    for name, info in sorted(_BANKER_REGISTRY.items(), key=lambda x: -len(x[0])):
        if name in low:
            return name, info
    return '', {}


def classify_banker_mandate(
    excerpt: str,
    trigger_phrase: str = '',
) -> dict[str, Any]:
    """
    Classify the nature of the banker relationship from filing text.

    Returns:
        banker_name:          normalized name from registry, or '' if unknown
        banker_tier:          BULGE | ELITE | BIOTECH | REGIONAL | UNKNOWN
        banker_skew:          MA | ECM | BOTH | UNKNOWN (typical mandate bias for this bank)
        mandate_type:         BM_* constant
        mandate_strength:     MS_* constant
        is_exclusive:         bool
        mandate_language:     first matching phrase from excerpt
        mandate_note:         human-readable explanation
    """
    text = ' '.join(filter(None, [excerpt, trigger_phrase]))

    banker_name, banker_info = _detect_banker_name(text)
    banker_tier = banker_info.get('tier', 'UNKNOWN')
    banker_skew = banker_info.get('skew', 'UNKNOWN')

    is_exclusive = bool(_match_any(text, _EXCLUSIVITY_MARKERS))

    # Defense overrides everything — defending is not selling
    defense_hits = _match_any(text, _DEFENSE_MANDATE)
    if defense_hits:
        return {
            'banker_name':       banker_name,
            'banker_tier':       banker_tier,
            'banker_skew':       banker_skew,
            'mandate_type':      BM_DEFENSE,
            'mandate_strength':  MS_DEFENSIVE,
            'is_exclusive':      is_exclusive,
            'mandate_language':  defense_hits[0],
            'mandate_note': (
                f'Banker retained in DEFENSIVE context — responding to unsolicited proposal, '
                f'not running a sale. This is a defense mandate, not a sell-side mandate. '
                f'No acquisition-initiation signal.'
            ),
        }

    # Fairness opinion = deal already done
    fairness_hits = _match_any(text, _FAIRNESS_MANDATE)
    if fairness_hits:
        return {
            'banker_name':       banker_name,
            'banker_tier':       banker_tier,
            'banker_skew':       banker_skew,
            'mandate_type':      BM_FAIRNESS,
            'mandate_strength':  MS_IRRELEVANT,
            'is_exclusive':      False,
            'mandate_language':  fairness_hits[0],
            'mandate_note': (
                'Banker retained to provide FAIRNESS OPINION on an already-agreed deal. '
                'No pre-process edge — deal terms already set. Discard as pre-announcement signal.'
            ),
        }

    # Capital markets
    cm_hits = _match_any(text, _CAPITAL_MARKETS_MANDATE)
    if cm_hits and not _match_any(text, _SALE_MANDATE_STRONG):
        return {
            'banker_name':       banker_name,
            'banker_tier':       banker_tier,
            'banker_skew':       banker_skew,
            'mandate_type':      BM_CAPITAL_MARKETS,
            'mandate_strength':  MS_IRRELEVANT,
            'is_exclusive':      is_exclusive,
            'mandate_language':  cm_hits[0],
            'mandate_note': (
                'Banker retained for CAPITAL MARKETS work (offering, placement, financing). '
                'Not an M&A mandate. Does not signal sale process unless combined with '
                'explicit strategic alternatives language.'
            ),
        }

    # Partnership/licensing banker
    partner_hits = _match_any(text, _PARTNERSHIP_MANDATE)
    if partner_hits:
        return {
            'banker_name':       banker_name,
            'banker_tier':       banker_tier,
            'banker_skew':       banker_skew,
            'mandate_type':      BM_PARTNERSHIP,
            'mandate_strength':  MS_IRRELEVANT,
            'is_exclusive':      is_exclusive,
            'mandate_language':  partner_hits[0],
            'mandate_note': (
                'Banker retained to find LICENSING or COLLABORATION partners. '
                'Drug/program-level, not company-level M&A mandate.'
            ),
        }

    # Restructuring advisor
    restr_hits = _match_any(text, _RESTRUCTURING_MANDATE)
    if restr_hits:
        return {
            'banker_name':       banker_name,
            'banker_tier':       banker_tier,
            'banker_skew':       banker_skew,
            'mandate_type':      BM_RESTRUCTURING,
            'mandate_strength':  MS_IRRELEVANT,
            'is_exclusive':      is_exclusive,
            'mandate_language':  restr_hits[0],
            'mandate_note': (
                'Banker retained as RESTRUCTURING ADVISOR — financial or operational restructuring. '
                'Not an M&A sell-side mandate unless also accompanied by SA language.'
            ),
        }

    # Strong sale mandate
    sale_hits = _match_any(text, _SALE_MANDATE_STRONG)
    if sale_hits:
        note = (
            f'STRONG SALE MANDATE: {sale_hits[0]}. '
            + ('Exclusive engagement — board has committed to running a sale process.' if is_exclusive else
               'Retained to explore sale — process may be early stage.')
        )
        if banker_name:
            note += (
                f' {banker_name.title()} is a {"primarily M&A advisory" if banker_skew == "MA" else "mixed-mandate"} '
                f'firm — consistent with a sell-side mandate.'
            )
        return {
            'banker_name':       banker_name,
            'banker_tier':       banker_tier,
            'banker_skew':       banker_skew,
            'mandate_type':      BM_SALE_MANDATE,
            'mandate_strength':  MS_STRONG,
            'is_exclusive':      is_exclusive,
            'mandate_language':  sale_hits[0],
            'mandate_note':      note,
        }

    # Moderate strategic review
    review_hits = _match_any(text, _STRATEGIC_REVIEW_MODERATE)
    if review_hits:
        # Assess strength based on banker skew
        if banker_skew == 'MA':
            strength = MS_STRONG
            skew_note = f'{banker_name.title()} primarily does M&A advisory — strategic review with this bank skews toward sale.'
        elif banker_skew == 'ECM':
            strength = MS_WEAK
            skew_note = f'{banker_name.title()} skews toward capital markets — strategic review may mean financing, not sale.'
        else:
            strength = MS_MODERATE
            skew_note = f'{banker_name.title() if banker_name else "Bank"} does both M&A and capital markets — mandate ambiguous without full filing.'

        return {
            'banker_name':       banker_name,
            'banker_tier':       banker_tier,
            'banker_skew':       banker_skew,
            'mandate_type':      BM_STRATEGIC_REVIEW,
            'mandate_strength':  strength,
            'is_exclusive':      is_exclusive,
            'mandate_language':  review_hits[0],
            'mandate_note': (
                f'Retained for STRATEGIC REVIEW — sale is one option but not explicitly the mandate. '
                f'{skew_note}'
            ),
        }

    # Banker mentioned but mandate unclear
    if banker_name:
        note = (
            f'{banker_name.title()} mentioned but mandate not determinable from excerpt. '
        )
        if banker_skew == 'MA':
            note += 'Pure M&A firm — if retained here, likely a sale/process mandate. Read full filing.'
            strength = MS_MODERATE
        elif banker_skew == 'ECM':
            note += 'ECM-skewed firm — could be offering, placement, or financing. Read full filing to confirm.'
            strength = MS_WEAK
        else:
            note += 'Mixed-mandate firm — read full filing to confirm mandate type.'
            strength = MS_WEAK
        return {
            'banker_name':       banker_name,
            'banker_tier':       banker_tier,
            'banker_skew':       banker_skew,
            'mandate_type':      BM_UNKNOWN,
            'mandate_strength':  strength,
            'is_exclusive':      is_exclusive,
            'mandate_language':  '',
            'mandate_note':      note,
        }

    # No banker detected
    return {
        'banker_name':       '',
        'banker_tier':       'UNKNOWN',
        'banker_skew':       'UNKNOWN',
        'mandate_type':      BM_UNKNOWN,
        'mandate_strength':  MS_WEAK,
        'is_exclusive':      False,
        'mandate_language':  '',
        'mandate_note':      'No recognized financial advisor detected in excerpt.',
    }


SA_ACQUISITION        = 'ACQUISITION_PROCESS'
SA_CAPITAL_RAISE      = 'CAPITAL_RAISE'
SA_ASSET_DIVESTITURE  = 'ASSET_DIVESTITURE'
SA_PARTNERSHIP        = 'PARTNERSHIP_LICENSING'
SA_MERGER_EQUALS      = 'MERGER_OF_EQUALS'
SA_WIND_DOWN          = 'WIND_DOWN'
SA_RESTRUCTURING      = 'RESTRUCTURING'
SA_SHAREHOLDER_RETURN = 'SHAREHOLDER_RETURN'
SA_AMBIGUOUS          = 'AMBIGUOUS'


# ── Keyword banks ─────────────────────────────────────────────────────────────

_ACQUISITION_STRONG = [
    'sale of the company',
    'sale of the issuer',
    'selling the company',
    'merger or acquisition',
    'business combination',
    'acquisition of the company',
    'potential acquirer',
    'outreach to potential acquirers',
    'maximize stockholder value',           # company-level + banker = strong
    'maximize shareholder value',
    'going private',
    'take private',
    'take-private',
    'unsolicited proposal',
    'acquisition proposal',
    'tender offer',
    'competing bid',
    'superior proposal',
    'definitive agreement',
    'transaction committee',
    'sale committee',
    'special committee to evaluate',
    'merger discussions',
    'acquisition discussions',
    'strategic alternatives intended to maximize',
]

_ACQUISITION_BANKER = [
    'retained a financial advisor',
    'engaged a financial advisor',
    'financial advisor to assist the board',
    'as its exclusive financial advisor',
    'engaged leerink',
    'engaged lazard',
    'engaged goldman',
    'engaged morgan stanley',
    'engaged jefferies',
    'engaged evercore',
    'engaged centerview',
    'engaged perella',
    'investment bank',
    'financial advisory',
]

_CAPITAL_RAISE = [
    'financing alternatives',
    'capital raise',
    'capital markets',
    'equity financing',
    'debt financing',
    'extend runway',
    'extend our cash runway',
    'additional capital',
    'sources of capital',
    'non-dilutive financing',
    'pipe',
    'registered direct',
    'public offering',
    'at-the-market',
    'atm offering',
    'royalty monetization',
    'royalty financing',
    'venture debt',
]

_ASSET_DIVESTITURE = [
    'divest',
    'divestiture',
    'sell certain assets',
    'monetize',
    'out-license',
    'outlicense',
    'license or sell',
    'disposition of',
    'sale of certain',
    'asset sale',
    'program sale',
    'pipeline sale',
    'sell or license',
]

_PARTNERSHIP = [
    'strategic partnership',
    'strategic collaboration',
    'co-development',
    'co-promotion',
    'licensing agreement',
    'collaboration agreement',
    'partnerships for',
    'partnerships with',
    'commercialization partner',
    'development partner',
    'co-commercialization',
]

_MERGER_EQUALS = [
    'merger of equals',
    'combination of equals',
    'business combination with',
    'combined company',
    'reverse merger',
    'reverse triangular merger',
    'spac',
]

_WIND_DOWN = [
    'wind down',
    'wind-down',
    'dissolution',
    'dissolve',
    'liquidation',
    'liquidate',
    'cease operations',
    'wind up operations',
    'orderly wind',
    'plan of dissolution',
]

_RESTRUCTURING = [
    'workforce reduction',
    'reduction in force',
    'rif',
    'headcount reduction',
    'cost reduction',
    'restructuring plan',
    'strategic restructuring',
    'reduce operating expenses',
    'operational restructuring',
]

_SHAREHOLDER_RETURN = [
    'return capital',
    'share repurchase',
    'buyback',
    'special dividend',
    'spin-off',
    'spinoff',
    'separation of',
    'split-off',
]

# Drug/program-level signals that indicate ASSET or PARTNERSHIP rather than company-level SA
_ASSET_LEVEL_INDICATORS = [
    r'for (?:the )?(?:development|commercialization|licensing) of \b[A-Z][A-Z0-9\-]{2,}\b',
    r'\b[A-Z]{2,}[-\s]?\d+\b',          # compound codes like SGR-1505, BNT322
    r'for (?:mid|late|early)[- ]stage development of',
    r'for (?:its |our )(?:lead |pipeline )?(?:compound|program|asset|candidate|drug)',
    r'right of first (?:negotiation|refusal) (?:on|over|for) (?:a |the )?\w+ (?:program|asset|compound)',
    r'collaboration for (?:the development|commercialization)',
]


def _match_any(text: str, patterns: list[str]) -> list[str]:
    """Return list of matching patterns from text (lowercased)."""
    low = text.lower()
    return [p for p in patterns if p in low]


def _match_any_re(text: str, patterns: list[str]) -> list[str]:
    """Return list of matching regex patterns."""
    return [p for p in patterns if re.search(p, text, re.I)]


def classify_sa_type(
    excerpt: str,
    trigger_phrase: str = '',
    flags: list[str] | None = None,
    has_banker: bool = False,
    signal_quality: str = '',
) -> dict[str, Any]:
    """
    Classify the strategic alternatives type from filing evidence.

    Returns:
        sa_type:            one of the SA_* constants
        sa_confidence:      HIGH / MEDIUM / LOW
        sa_reasons:         list of matching evidence strings
        is_company_level:   bool — is this a company-level process or asset/program level?
        asset_level_flags:  list of patterns suggesting asset/program-level scope
        requires_deeper_read: bool — ambiguous, needs human to read full filing
    """
    text = ' '.join(filter(None, [excerpt, trigger_phrase, ' '.join(flags or [])]))

    acq_strong   = _match_any(text, _ACQUISITION_STRONG)
    acq_banker   = _match_any(text, _ACQUISITION_BANKER)
    cap_raise    = _match_any(text, _CAPITAL_RAISE)
    asset_div    = _match_any(text, _ASSET_DIVESTITURE)
    partnership  = _match_any(text, _PARTNERSHIP)
    merger_eq    = _match_any(text, _MERGER_EQUALS)
    wind_down    = _match_any(text, _WIND_DOWN)
    restructure  = _match_any(text, _RESTRUCTURING)
    sh_return    = _match_any(text, _SHAREHOLDER_RETURN)
    asset_scope  = _match_any_re(text, _ASSET_LEVEL_INDICATORS)

    is_company_level = not bool(asset_scope)
    reasons: list[str] = []

    # Wind-down overrides everything — most specific
    if wind_down:
        return {
            'sa_type': SA_WIND_DOWN,
            'sa_confidence': 'HIGH',
            'sa_reasons': wind_down,
            'is_company_level': True,
            'asset_level_flags': asset_scope,
            'requires_deeper_read': False,
        }

    # Explicit acquisition language
    if acq_strong and (has_banker or acq_banker or signal_quality == 'AFFIRM'):
        reasons = acq_strong + acq_banker
        return {
            'sa_type': SA_ACQUISITION,
            'sa_confidence': 'HIGH' if (acq_strong and (has_banker or acq_banker)) else 'MEDIUM',
            'sa_reasons': reasons,
            'is_company_level': is_company_level,
            'asset_level_flags': asset_scope,
            'requires_deeper_read': bool(asset_scope),
        }

    # Merger of equals
    if merger_eq:
        return {
            'sa_type': SA_MERGER_EQUALS,
            'sa_confidence': 'HIGH',
            'sa_reasons': merger_eq,
            'is_company_level': True,
            'asset_level_flags': asset_scope,
            'requires_deeper_read': False,
        }

    # Capital raise — often alongside SA language
    if cap_raise and not acq_strong:
        reasons = cap_raise
        if restructure:
            reasons += restructure
        return {
            'sa_type': SA_CAPITAL_RAISE,
            'sa_confidence': 'HIGH' if len(cap_raise) >= 2 else 'MEDIUM',
            'sa_reasons': reasons,
            'is_company_level': False,
            'asset_level_flags': asset_scope,
            'requires_deeper_read': bool(acq_strong),
        }

    # Partnership / licensing at program level
    if partnership and asset_scope:
        return {
            'sa_type': SA_PARTNERSHIP,
            'sa_confidence': 'HIGH',
            'sa_reasons': partnership + asset_scope,
            'is_company_level': False,
            'asset_level_flags': asset_scope,
            'requires_deeper_read': False,
        }

    # Asset divestiture
    if asset_div:
        return {
            'sa_type': SA_ASSET_DIVESTITURE,
            'sa_confidence': 'MEDIUM',
            'sa_reasons': asset_div,
            'is_company_level': False,
            'asset_level_flags': asset_scope,
            'requires_deeper_read': True,
        }

    # Restructuring
    if restructure:
        return {
            'sa_type': SA_RESTRUCTURING,
            'sa_confidence': 'MEDIUM',
            'sa_reasons': restructure,
            'is_company_level': True,
            'asset_level_flags': asset_scope,
            'requires_deeper_read': True,
        }

    # Shareholder return
    if sh_return:
        return {
            'sa_type': SA_SHAREHOLDER_RETURN,
            'sa_confidence': 'MEDIUM',
            'sa_reasons': sh_return,
            'is_company_level': True,
            'asset_level_flags': asset_scope,
            'requires_deeper_read': True,
        }

    # Banker present but unclear type
    if has_banker or acq_banker:
        return {
            'sa_type': SA_ACQUISITION,
            'sa_confidence': 'LOW',
            'sa_reasons': acq_banker,
            'is_company_level': is_company_level,
            'asset_level_flags': asset_scope,
            'requires_deeper_read': True,
        }

    return {
        'sa_type': SA_AMBIGUOUS,
        'sa_confidence': 'LOW',
        'sa_reasons': [],
        'is_company_level': is_company_level,
        'asset_level_flags': asset_scope,
        'requires_deeper_read': True,
    }


# ── Distress detector ─────────────────────────────────────────────────────────

def detect_distress(
    ticker: str,
    filing_date_str: str,
    lookback_days: int = 30,
) -> dict[str, Any]:
    """
    Compute price change in the 30 days BEFORE the filing date.
    If the stock dropped materially before the SA announcement, flag as distress-driven.

    Returns:
        price_at_filing:        float or None
        price_30d_before:       float or None
        price_change_30d_pct:   float or None
        distress_driven_sa:     bool
        distress_severity:      SEVERE | MODERATE | MILD | NONE | UNKNOWN
        distress_note:          str — human-readable explanation
    """
    result: dict[str, Any] = {
        'price_at_filing':      None,
        'price_30d_before':     None,
        'price_change_30d_pct': None,
        'distress_driven_sa':   False,
        'distress_severity':    'UNKNOWN',
        'distress_note':        '',
    }

    if not filing_date_str or not ticker:
        return result

    try:
        filing_dt = datetime.fromisoformat(str(filing_date_str).split(' ')[0])
    except (ValueError, TypeError):
        return result

    try:
        import yfinance as yf
        start = (filing_dt - timedelta(days=lookback_days + 5)).strftime('%Y-%m-%d')
        end   = (filing_dt + timedelta(days=2)).strftime('%Y-%m-%d')
        hist  = yf.Ticker(ticker).history(start=start, end=end, interval='1d', auto_adjust=True)

        if hist.empty:
            result['distress_note'] = 'No price history available'
            return result

        # Price on or just before filing date
        filing_date_naive = filing_dt.date()
        hist_dates = [d.date() for d in hist.index]

        # Find closest trading day at or before filing date
        at_filing_dates = [d for d in hist_dates if d <= filing_date_naive]
        before_dates    = [d for d in hist_dates if d <= (filing_date_naive - timedelta(days=lookback_days - 3))]

        if not at_filing_dates or not before_dates:
            result['distress_note'] = 'Insufficient price history'
            return result

        price_at   = float(hist.loc[hist.index[hist_dates.index(at_filing_dates[-1])], 'Close'])
        price_prev = float(hist.loc[hist.index[hist_dates.index(before_dates[0])], 'Close'])

        pct_change = ((price_at - price_prev) / price_prev) * 100

        result['price_at_filing']      = round(price_at, 4)
        result['price_30d_before']     = round(price_prev, 4)
        result['price_change_30d_pct'] = round(pct_change, 2)

        if pct_change <= -40:
            result['distress_driven_sa']  = True
            result['distress_severity']   = 'SEVERE'
            result['distress_note'] = (
                f'Stock dropped {pct_change:.1f}% in 30d before filing. '
                'SA likely reactive to major adverse event — distress-driven, not value-maximizing.'
            )
        elif pct_change <= -20:
            result['distress_driven_sa']  = True
            result['distress_severity']   = 'MODERATE'
            result['distress_note'] = (
                f'Stock dropped {pct_change:.1f}% in 30d before filing. '
                'SA may be reactive to negative news — verify whether distress-driven.'
            )
        elif pct_change <= -10:
            result['distress_driven_sa']  = False
            result['distress_severity']   = 'MILD'
            result['distress_note'] = (
                f'Stock down {pct_change:.1f}% in 30d before filing — mild weakness, not definitive distress.'
            )
        else:
            result['distress_driven_sa']  = False
            result['distress_severity']   = 'NONE'
            result['distress_note'] = (
                f'Stock {pct_change:+.1f}% in 30d before filing — no distress signal.'
            )

    except Exception as exc:
        result['distress_note'] = f'Price fetch failed: {exc}'

    return result
