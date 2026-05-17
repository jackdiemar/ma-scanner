"""
false_positive_filter.py — Apply the 3-batch historical FP taxonomy as a live suppressor.

Evidence basis:
  - Batch 51-70: 9 FP patterns (binary artifact, PWERM, negation, lock-up exhibit,
    director bio, geographic ROFN, deal-announcement FLS, director bio, redomiciliation)
  - Batch 71-100: 9 FP patterns (S-8 boilerplate, asset-specific ROFN, director bio,
    performance condition award, offering disclaimer, partner equity divestiture,
    wrong-direction acquisition, ROFR warranty negative, anti-takeover provision)

Classifications:
  KEEP_HIGH_PRIORITY   → INVESTIGATE
  KEEP_REVIEW          → INVESTIGATE (with lower confidence)
  DOWNGRADE_WATCH      → WATCH
  SUPPRESS_FALSE_POSITIVE → DISCARD

Conservative design: when in doubt, DOWNGRADE_WATCH rather than SUPPRESS.
"""
from __future__ import annotations

import json
import re

# ─── Excerpt-level false positive patterns ────────────────────────────────────

# S-8 / equity plan boilerplate (MRTX, HZNP batch 71-100; FMTX batch 51-70)
_S8_BOILERPLATE = [
    'form s-8 registration statement',
    'offer or the sale of the company\'s securities to such person',
    'continuous service',
    'treated as a consultant under this plan',
]

# Offering prospectus disclaimer (VSTM, LBPH batch 71-100; ALPN batch 51-70)
_OFFERING_DISCLAIMER = [
    'being made only by means of a written prospectus',
    'meeting the requirements of section 10 of the securities act',
    'qualification under the securities laws of such jurisdiction',
    'sale of the company\'s securities in any state or jurisdiction',
]

# Anti-takeover provision boilerplate (ALBO batch 71-100)
_ANTITAKEOVER = [
    'reduce our vulnerability to an unsolicited',
    'section 203',
    'dgcl',
    'discourage certain tactics that may be used in proxy fights',
    'such provisions also may have the effect of preventing changes',
    'delaware statutory business combinations',
]

# Director biography / prior employer (STML, CHMA batch 71-100; ZYNE batch 51-70)
_DIRECTOR_BIO = [
    'sale of the company to keryx',
    'sale of the company to baxter',
    'served as chief executive',
    'prior to joining',
    'joined our board of directors',
    'sit on our board of directors include his extensive experience',
    'experience providing strategic and financial advisory services',
    'has been chief executive officer and director of',
]

# Performance condition equity award (STML batch 71-100; FMTX batch 51-70)
_PERF_CONDITION = [
    'no expense is recognized',
    'no measurement date can occur',
    'performance conditions, such as obtaining regulatory approval',
    'a change in control or a sale of the company, no expense',
    'probability-weighted expected return',
    'pwerm',
    'prior to our ipo',
]

# Partner equity stake divestiture (SNDX batch 71-100)
_PARTNER_EQUITY = [
    'cash settlement on the sale of the company\'s common stock would be made to make the parties whole',
    'upfront payment of',
    'returned to incyte',
    'make the parties whole',
]

# Wrong-direction acquisition (HZNP batch 71-100)
_WRONG_DIRECTION = [
    'received an option to acquire',
    'the company received an option',
    'the company has an option to acquire',
]

# ROFR warranty negative (VSTM batch 71-100; SRRA batch 51-70)
_ROFR_WARRANTY_NEG = [
    'not subject to any agreement granting',
    'not subject to, any agreement',
    'granting any option, warrant or right of first refusal',
    'no right of first refusal',
]

# Binary / UUEncoded artifact (GBT, RETA batch 51-70; SGEN batch 71-100)
def _is_binary_artifact(excerpt: str) -> bool:
    if not excerpt:
        return False
    # High density of non-ASCII or control characters = encoded binary
    non_printable = sum(1 for c in excerpt if ord(c) > 127 or (ord(c) < 32 and c not in '\n\r\t'))
    return len(excerpt) > 20 and non_printable / len(excerpt) > 0.15


def _excerpt_matches(excerpt: str, patterns: list) -> bool:
    low = excerpt.lower()
    return any(p in low for p in patterns)


# ─── Scope-level checks ───────────────────────────────────────────────────────

_NON_COMPANY_SCOPES = {'asset_specific_likely', 'securities_or_lockup_likely', 'geographic_license_likely'}


def _rofn_is_asset_specific(alert: dict) -> bool:
    rofn_hint = alert.get('rofn_scope_hint', '') or ''
    rofr_hint = alert.get('rofr_scope_hint', '') or ''
    return rofn_hint in _NON_COMPANY_SCOPES or rofr_hint in _NON_COMPANY_SCOPES


def _has_negated_phrases(alert: dict) -> bool:
    raw = alert.get('negated_8k_phrases', '[]') or '[]'
    try:
        phrases = json.loads(raw) if isinstance(raw, str) else raw
        return bool(phrases)
    except Exception:
        return bool(raw and raw != '[]')


# ─── Main classifier ──────────────────────────────────────────────────────────

def classify_alert(alert: dict) -> tuple[str, str, str]:
    """
    Returns (fp_classification, false_positive_risk, recommended_action).

    fp_classification: KEEP_HIGH_PRIORITY / KEEP_REVIEW / DOWNGRADE_WATCH / SUPPRESS_FALSE_POSITIVE
    false_positive_risk: HIGH / MEDIUM / LOW / NONE
    recommended_action: INVESTIGATE / WATCH / DISCARD
    """
    sq      = alert.get('signal_quality', '') or ''
    excerpt = alert.get('signal_source_excerpt', '') or ''
    sq_low  = sq.upper()

    # ── Hard suppression: BOILERPLATE or SCORE_ONLY reaching filter ──
    if sq_low in ('BOILERPLATE', 'SCORE_ONLY'):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── Binary artifact ──
    if _is_binary_artifact(excerpt):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── Offering prospectus disclaimer ──
    if _excerpt_matches(excerpt, _OFFERING_DISCLAIMER):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── S-8 equity plan boilerplate ──
    if _excerpt_matches(excerpt, _S8_BOILERPLATE):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── Anti-takeover provision boilerplate ──
    if _excerpt_matches(excerpt, _ANTITAKEOVER):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── Director biography at prior employer ──
    if _excerpt_matches(excerpt, _DIRECTOR_BIO):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── Performance condition equity award ──
    if _excerpt_matches(excerpt, _PERF_CONDITION):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── Partner equity stake divestiture ──
    if _excerpt_matches(excerpt, _PARTNER_EQUITY):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── Wrong-direction acquisition ──
    if _excerpt_matches(excerpt, _WRONG_DIRECTION):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── ROFR warranty (negative statement) ──
    if _excerpt_matches(excerpt, _ROFR_WARRANTY_NEG):
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    # ── Asset-specific ROFN/ROFR (scope hint) ──
    if _rofn_is_asset_specific(alert) and sq_low == 'ROFR':
        return 'SUPPRESS_FALSE_POSITIVE', 'HIGH', 'DISCARD'

    if _rofn_is_asset_specific(alert) and sq_low not in ('AFFIRM', 'MERGER'):
        # Asset-scope ROFN in a PROCESS signal — downgrade, don't suppress fully
        return 'DOWNGRADE_WATCH', 'MEDIUM', 'WATCH'

    # ── Negated phrases present, no other affirmative signal ──
    if _has_negated_phrases(alert) and sq_low not in ('AFFIRM', 'MERGER'):
        return 'DOWNGRADE_WATCH', 'MEDIUM', 'WATCH'

    # ── Signal quality routing for non-suppressed alerts ──
    if sq_low == 'AFFIRM':
        return 'KEEP_HIGH_PRIORITY', 'LOW', 'INVESTIGATE'

    if sq_low == 'MERGER':
        return 'KEEP_HIGH_PRIORITY', 'NONE', 'INVESTIGATE'

    if sq_low == 'PROCESS':
        # No source URL = we can't verify → downgrade
        if not (alert.get('signal_source_url') or '').strip():
            return 'DOWNGRADE_WATCH', 'MEDIUM', 'WATCH'
        return 'KEEP_REVIEW', 'LOW', 'INVESTIGATE'

    if sq_low == 'ROFR':
        if not (alert.get('signal_source_url') or '').strip():
            return 'DOWNGRADE_WATCH', 'MEDIUM', 'WATCH'
        return 'KEEP_REVIEW', 'MEDIUM', 'WATCH'

    # Default: anything that slipped through
    return 'DOWNGRADE_WATCH', 'MEDIUM', 'WATCH'


def classify_alerts(alerts: list) -> list:
    """Apply FP taxonomy to each alert. Mutates in place and returns list."""
    for a in alerts:
        fp_class, fp_risk, action = classify_alert(a)
        a['fp_classification']  = fp_class
        a['false_positive_risk'] = fp_risk
        a['recommended_action'] = action
    return alerts


def summary_stats(alerts: list) -> dict:
    """Return counts by classification for reporting."""
    counts: dict = {
        'KEEP_HIGH_PRIORITY':    0,
        'KEEP_REVIEW':           0,
        'DOWNGRADE_WATCH':       0,
        'SUPPRESS_FALSE_POSITIVE': 0,
        'total':                 len(alerts),
        'new':                   0,
        'updated':               0,
    }
    for a in alerts:
        fp = a.get('fp_classification', '')
        if fp in counts:
            counts[fp] += 1
        if a.get('status') == 'NEW':
            counts['new'] += 1
        elif a.get('status') == 'UPDATED':
            counts['updated'] += 1
    return counts
