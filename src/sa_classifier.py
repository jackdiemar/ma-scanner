"""
sa_classifier.py — Strategic alternatives type classifier + distress detector.

Two functions:
  classify_sa_type(excerpt, trigger_phrase, flags, has_banker) → SA type + confidence
  detect_distress(ticker, filing_date_str) → price change 30d before filing

SA Types:
  ACQUISITION_PROCESS     — sale of company, merger, company-level banker retained
  CAPITAL_RAISE           — financing, equity offering, runway extension
  ASSET_DIVESTITURE       — selling specific program/asset, not whole company
  PARTNERSHIP_LICENSING   — collaboration, co-development, licensing (drug-level)
  MERGER_OF_EQUALS        — combination, merger of equals, consolidation
  WIND_DOWN               — dissolution, liquidation, wind-down, cease operations
  RESTRUCTURING           — workforce reduction, cost cutting alongside SA
  SHAREHOLDER_RETURN      — buyback, dividend, spin-off, capital return
  AMBIGUOUS               — insufficient context to classify

Distress severity (based on price change 30d before filing date):
  SEVERE   — drop > 40%
  MODERATE — drop 20-40%
  MILD     — drop 10-20%
  NONE     — stable or up

Research use only. No investment advice.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

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
