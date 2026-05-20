"""
strategy_knowledge.py — Structured encoding of MA Scanner historical strategy.

Encodes:
  - Historical base rates from 50-case and 86-case reviews
  - True signal archetypes (MDVN, DMTX, TSRO)
  - False-positive taxonomy with deterministic clues
  - True signal requirements for ESCALATE classification

This module has no external dependencies and no I/O.
Import it from strategy_classifier.py and prompts.py.
"""
from __future__ import annotations

from typing import Any


# ── Historical base rates ─────────────────────────────────────────────────────

HISTORICAL_BASE_RATES: dict[str, Any] = {
    'true_public_prior_signal_rate_50_case': 0.06,
    'true_public_prior_signal_count_50_case': 3,
    'total_cases_50_case': 50,
    'expanded_true_signal_rate_86_case': 3 / 86,
    'expanded_true_signal_count': 3,
    'expanded_cases': 86,
    'batch_71_100_true_signal_count': 0,
    'case_distribution_50': {
        'DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE': {'count': 35, 'pct': 0.70},
        'PRIVATE_BACKGROUND_ONLY':              {'count': 8,  'pct': 0.16},
        'TRUE_PUBLIC_PRIOR_SIGNAL':             {'count': 3,  'pct': 0.06},
        'ASSET_SPECIFIC_RIGHTS_ONLY':           {'count': 2,  'pct': 0.04},
        'RIGHTS_LANGUAGE_ONLY':                 {'count': 1,  'pct': 0.02},
        'DATE_MISSING_EXCLUDED':                {'count': 1,  'pct': 0.02},
    },
    'summary': (
        'Only 3 of 50 small-cap biotech acquisitions (2015-2022) had source-backed '
        'public prior process signals before deal announcement. '
        'Expanded 86-case review found no additional true signals (Batches 71-100). '
        'Base rate ~3.5%. Most hits are classifiable false positives.'
    ),
}


# ── True signal archetypes ────────────────────────────────────────────────────

TRUE_SIGNAL_ARCHETYPES: dict[str, dict[str, Any]] = {

    'PUBLIC_UNSOLICITED_PROPOSAL': {
        'example_ticker': 'MDVN',
        'example_company': 'Medivation',
        'example_acquirer': 'Sanofi (initial) → Pfizer (final)',
        'signal_date': '2016-04-28',
        'deal_date': '2016-08-22',
        'days_before_deal': 116,
        'description': (
            'Acquirer files or discloses a public unsolicited acquisition proposal '
            'before a definitive agreement is signed. The target company is under '
            'explicit public acquisition pressure. Company-level strategic process is live.'
        ),
        'characteristics': [
            'Public acquirer proposal disclosed (8-K, press release, or SEC filing)',
            'Company-level acquisition pressure — not asset-specific',
            'Timing advantage: public before definitive deal announcement',
            'Explicit acquisition intent with named acquirer',
            'Target board response expected (fiduciary process begins)',
        ],
        'key_phrases': [
            'unsolicited proposal', 'acquisition proposal', 'board received',
            'rejected offer', 'strategic alternatives', 'financial advisor retained',
            'board committee', 'public offer',
        ],
        'edgar_catchable': True,
        'notes': (
            'MDVN: Sanofi made public unsolicited proposal April 28, 2016. '
            'Pfizer announced acquisition August 22, 2016 — 116 days later. '
            'High-value signal with ample time before final deal.'
        ),
    },

    'SUPERIOR_PROPOSAL_OR_COMPETING_BID': {
        'example_ticker': 'DMTX',
        'example_company': 'Dimension Therapeutics',
        'example_acquirer': 'Ultragenyx',
        'signal_date': '2017-08-25',
        'deal_date': '2017-10-03',
        'days_before_deal': 39,
        'description': (
            'A superior proposal or competing bid is publicly disclosed before '
            'the final definitive agreement is signed. Indicates active fiduciary '
            'process with multiple parties and public pre-announcement evidence.'
        ),
        'characteristics': [
            'Superior proposal language in public filing or proxy',
            'Competing bid activity disclosed publicly before definitive agreement',
            'Active fiduciary sale process with multiple parties',
            'Public pre-announcement evidence of company-level process',
        ],
        'key_phrases': [
            'superior proposal', 'competing bid', 'alternative acquisition proposal',
            'fiduciary out', 'go-shop', 'unsolicited alternative',
            'board determined superior', 'topping bid',
        ],
        'edgar_catchable': True,
        'notes': (
            'DMTX: Superior proposal / competing bid activity began August 25, 2017. '
            'Final Ultragenyx deal announced October 3, 2017 — 39 days later. '
            'Detectable via EDGAR if go-shop or superior proposal language is public before final deal.'
        ),
    },

    'CREDIBLE_MEDIA_SALE_PROCESS_REPORT': {
        'example_ticker': 'TSRO',
        'example_company': 'Tesaro',
        'example_acquirer': 'GlaxoSmithKline',
        'signal_date': '2018-11-16',
        'deal_date': '2018-12-03',
        'days_before_deal': 17,
        'description': (
            'A credible media report of an ongoing sale process or acquisition interest '
            'appears before the final definitive agreement is publicly announced. '
            'The company has not yet filed an EDGAR disclosure of the process.'
        ),
        'characteristics': [
            'External media report of sale process (Reuters, WSJ, Bloomberg)',
            'Credible publication naming specific acquirers or process context',
            'Before final definitive deal announcement',
            'May not appear in EDGAR at time of report',
        ],
        'key_phrases': [
            'sale process', 'exploring strategic alternatives', 'acquisition interest',
            'sources say', 'in talks to acquire', 'considering sale',
            'bankers retained', 'strategic review',
        ],
        'edgar_catchable': False,
        'requires_news_integration': True,
        'notes': (
            'TSRO: Sale process media report November 16, 2018. '
            'GSK announced acquisition December 3, 2018 — 17 days later. '
            'EDGAR-only workflow would not catch this. Requires external news integration. '
            'Shortest lead time of the three true signal examples.'
        ),
    },
}


# ── False-positive taxonomy ───────────────────────────────────────────────────

FALSE_POSITIVE_ARCHETYPES: dict[str, dict[str, Any]] = {

    'ALREADY_ANNOUNCED_MERGER': {
        'description': (
            'A definitive merger agreement, agreement and plan of merger, or '
            'acquisition agreement is already signed and publicly announced. '
            'The pre-deal research window is closed.'
        ),
        'why_not_true_signal': (
            'The deal is already public. Pre-announcement edge no longer exists. '
            'Any strategic process was private until the announcement date. '
            'Post-announcement documents reflect a completed process, not an open one.'
        ),
        'deterministic_clues': [
            'agreement and plan of merger', 'definitive agreement', 'merger agreement',
            'acquisition agreement', 'transaction agreement',
            'to be acquired by', 'entered into agreement', 'definitive merger',
            'pursuant to the merger agreement',
        ],
        'evidence_needed_to_override': (
            'Only if the filing date is provably BEFORE deal announcement date '
            'AND contains forward-looking process language rather than agreement confirmation.'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — definitive merger agreement confirmed in filing text. '
            'Deal already announced; no pre-announcement edge remains.'
        ),
    },

    'POST_ANNOUNCEMENT_PROXY_BACKGROUND': {
        'description': (
            'The document is a post-announcement proxy (DEFM14A, SC 14D-9, or similar) '
            'describing the deal background and "background of the merger" section. '
            'This describes a process that already concluded, not a live process.'
        ),
        'why_not_true_signal': (
            'The background section describes historical events leading to a deal '
            'that has already been announced. The "process" is in the past. '
            'No timing edge exists — the market already knows the outcome.'
        ),
        'deterministic_clues': [
            'background of the merger', 'background of the acquisition',
            'DEFM14A', 'SC 14D-9', 'SC TO-T', 'proxy statement',
            'solicitation / recommendation statement',
            'began to consider strategic alternatives', 'on [date], the board met',
        ],
        'evidence_needed_to_override': 'None — post-announcement proxy background is never a prior signal.',
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — post-announcement proxy background. '
            'Filing describes a completed deal process, not a live or upcoming one.'
        ),
    },

    'ASSET_SPECIFIC_RIGHTS_ONLY': {
        'description': (
            'ROFR, ROFN, ROFO, or similar rights language applies to a specific '
            'asset, product, or license — not to the company as a whole. '
            'This is product-level, not company-level M&A evidence.'
        ),
        'why_not_true_signal': (
            'Asset-specific rights do not constitute evidence that the whole company '
            'is in a strategic review or sale process. A partner right-of-first-refusal '
            'on a specific drug asset is a commercial term, not an M&A signal.'
        ),
        'deterministic_clues': [
            'right of first refusal', 'right of first negotiation', 'ROFR', 'ROFN', 'ROFO',
            'option to acquire', 'co-promotion rights', 'license agreement', 'collaboration agreement',
            'asset purchase', 'field-limited rights', 'territory rights',
        ],
        'evidence_needed_to_override': (
            'Evidence that the ROFR/ROFN is explicitly company-level (i.e., the partner has rights '
            'to acquire the whole company, not just an asset or product).'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — asset-specific ROFR/ROFN language. '
            'Rights apply to a specific asset or collaboration, not the whole company.'
        ),
    },

    'GENERIC_RIGHTS_LANGUAGE': {
        'description': (
            'Generic change-of-control, rights plan, or poison pill language '
            'that is standard anti-takeover boilerplate, not a live process signal.'
        ),
        'why_not_true_signal': (
            'Rights plans and change-of-control provisions are standard corporate '
            'governance tools adopted proactively or defensively. Adoption or existence '
            'of a rights plan does not indicate a live strategic process.'
        ),
        'deterministic_clues': [
            'rights plan', 'shareholder rights plan', 'poison pill', 'rights agreement',
            'change of control', 'CIC provision', 'anti-takeover', 'business combination',
            'advance notice', 'staggered board',
        ],
        'evidence_needed_to_override': (
            'Evidence that the rights plan was adopted in response to a specific '
            'identified acquirer or unsolicited proposal.'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — generic rights plan / change-of-control language. '
            'Standard anti-takeover provision, not a live strategic process signal.'
        ),
    },

    'OFFERING_PROSPECTUS_RISK_FACTOR': {
        'description': (
            'Change-of-control or merger language appears in a prospectus (S-1, S-3, '
            '424B3, 424B4) as a boilerplate risk factor. '
            'This is standard offering language, not a process signal.'
        ),
        'why_not_true_signal': (
            'Every public company offering document includes standard risk factors '
            'about potential change-of-control events. This language is forward-looking '
            'boilerplate required by SEC disclosure rules, not evidence of a live process.'
        ),
        'deterministic_clues': [
            'prospectus', 'S-1', 'S-3', '424B', 'offering memorandum',
            'risk factors', 'if we were acquired', 'in the event of a change of control',
            'a merger could result in',
        ],
        'evidence_needed_to_override': (
            'A concurrent 8-K or independent filing disclosing actual strategic review — '
            'not just the prospectus language itself.'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — offering prospectus risk factor boilerplate. '
            'Standard disclosure language, not evidence of a live sale process.'
        ),
    },

    'S8_EQUITY_PLAN_BOILERPLATE': {
        'description': (
            'Merger or acquisition language appears in an S-8 equity plan filing '
            'or in award agreements as standard vesting / change-of-control provisions.'
        ),
        'why_not_true_signal': (
            'S-8 filings and equity compensation plans routinely include change-of-control '
            'acceleration and vesting provisions. This is compensation boilerplate, '
            'not a strategic process signal.'
        ),
        'deterministic_clues': [
            'S-8', 'Form S-8', 'equity incentive plan', 'stock option plan',
            'restricted stock unit', 'change of control vesting', 'accelerated vesting',
            'double trigger', 'single trigger', 'equity award',
        ],
        'evidence_needed_to_override': 'None — S-8/equity plan boilerplate is always false positive.',
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — S-8 equity plan change-of-control vesting provision. '
            'Standard compensation boilerplate, not an M&A process signal.'
        ),
    },

    'DIRECTOR_BIO_PRIOR_DEAL': {
        'description': (
            'Acquisition or merger language appears in a director biography or '
            '10-K/proxy table referencing a past deal the director was involved in — '
            'not a current process at this company.'
        ),
        'why_not_true_signal': (
            'Director biographies routinely reference prior M&A transactions '
            'to establish experience. The language refers to a historical deal '
            'at a different company or in a prior role, not a current process here.'
        ),
        'deterministic_clues': [
            'director', 'biography', 'biographical information', 'board member',
            'previously served', 'former', 'was involved in', 'led the acquisition of',
            'prior to joining', 'during his/her tenure at',
        ],
        'evidence_needed_to_override': (
            'Evidence that the director biography language refers to THIS company\'s '
            'current strategic situation, not a historical role.'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — director biography reference to prior deal. '
            'Language describes historical M&A experience, not a current process.'
        ),
    },

    'WRONG_DIRECTION_ACQUISITION': {
        'description': (
            'The company in question is the acquirer, not the target. '
            'The scanner fired on outbound M&A language by this company, '
            'not inbound acquisition interest from another party.'
        ),
        'why_not_true_signal': (
            'We are looking for companies being acquired, not companies acquiring others. '
            'A biotech company announcing it has acquired a target is not a target itself '
            'unless there is independent evidence of inbound acquisition interest.'
        ),
        'deterministic_clues': [
            'we acquired', 'we completed the acquisition', 'our acquisition of',
            'completed our merger', 'we consummated', 'we have entered into an agreement to acquire',
            'we intend to acquire', 'our proposed acquisition',
        ],
        'evidence_needed_to_override': (
            'Independent evidence that this company is itself a target — '
            'unsolicited proposal received, activist 13D, or credible media report.'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — company is the acquirer, not the target. '
            'Filing documents outbound M&A activity by this company.'
        ),
    },

    'PRIVATE_BACKGROUND_ONLY': {
        'description': (
            'The strategic process was conducted entirely in private. '
            'The only public evidence is a post-announcement filing disclosing '
            'that private discussions occurred. No pre-announcement public signal existed.'
        ),
        'why_not_true_signal': (
            'Private processes are not catchable before announcement. '
            'The background section reveals what happened behind closed doors — '
            'that information was not public before the announcement date. '
            'This is the most common outcome (16% of 50-case review).'
        ),
        'deterministic_clues': [
            'board met privately', 'management contacted', 'confidential discussions',
            'non-disclosure agreement signed', 'management presentations',
            'due diligence commenced', 'prior to announcement', 'not publicly disclosed',
        ],
        'evidence_needed_to_override': (
            'Evidence that any part of the process was publicly disclosed BEFORE deal announcement — '
            'an 8-K, a media report, or an SEC filing before the merger announcement date.'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — private background only. '
            'Process was conducted confidentially; no public prior signal existed.'
        ),
    },

    'EQUITY_INVESTMENT_NO_ACQUISITION_OPTION': {
        'description': (
            'A third party made an equity investment or minority stake acquisition '
            'without any option, right, or stated intent to acquire the whole company.'
        ),
        'why_not_true_signal': (
            'Equity investments and minority stakes are not M&A signals unless '
            'accompanied by explicit acquisition options, purchase rights, or '
            'public statements of intent to acquire the whole company.'
        ),
        'deterministic_clues': [
            'equity investment', 'minority interest', 'strategic investment',
            'Series A', 'Series B', 'preferred stock purchase', 'convertible note',
            'investor acquired X% of', 'took a minority stake',
        ],
        'evidence_needed_to_override': (
            'An explicit option or right to acquire the full company, '
            'or public statements of acquisition intent from the investor.'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — equity investment without acquisition option. '
            'No company-level acquisition intent or option is evidenced.'
        ),
    },

    'NEGATED_ACQUISITION_LANGUAGE': {
        'description': (
            'The filing contains explicit denial language: no acquisition proposal '
            'has been received, no sale process is underway, or the company '
            'has rejected or declined to pursue M&A interest.'
        ),
        'why_not_true_signal': (
            'Explicit negation of acquisition activity is the opposite of a signal. '
            'Scanner may have fired on the word "acquisition" but the context '
            'actively discredits any strategic process interpretation.'
        ),
        'deterministic_clues': [
            'no acquisition proposal', 'not received any proposal', 'no discussions',
            'declined to engage', 'not exploring', 'no strategic alternatives review',
            'not for sale', 'remains committed to standalone', 'rejected',
        ],
        'evidence_needed_to_override': (
            'A subsequent filing or news report contradicting the negation — '
            'e.g., an activist 13D or media report after the denial.'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — negated acquisition language. '
            'Filing explicitly states no M&A process or proposal exists.'
        ),
    },

    'GENERIC_PARTNERSHIP_OR_LICENSE': {
        'description': (
            'Alert triggered by collaboration, partnership, licensing, co-development, '
            'or co-promotion language. These are commercial agreements, not M&A signals, '
            'unless explicitly tied to company-level strategic alternatives.'
        ),
        'why_not_true_signal': (
            'Partnership and licensing agreements are standard biotech commercial activity. '
            'Collaboration language does not imply company-level sale process '
            'unless the filing explicitly connects the partnership to a strategic review.'
        ),
        'deterministic_clues': [
            'collaboration agreement', 'license agreement', 'co-development',
            'co-promotion', 'strategic collaboration', 'partnership agreement',
            'commercialization rights', 'development collaboration',
        ],
        'evidence_needed_to_override': (
            'Explicit language in the same filing connecting the partnership to '
            'a company-level strategic alternatives review or acquisition process.'
        ),
        'default_action': 'DISCARD',
        'example_language': (
            'Discard — generic partnership or licensing language. '
            'Commercial collaboration without company-level strategic process evidence.'
        ),
    },
}


# ── True signal requirements ──────────────────────────────────────────────────

TRUE_SIGNAL_REQUIREMENTS: dict[str, Any] = {
    'description': (
        'A case may only be classified ESCALATE if ALL of the following conditions are met.'
    ),
    'required_conditions': [
        'Evidence grade is A, B, or C — exact quote or source-backed process language available',
        'Signal is company-level — not merely asset-specific or product-level',
        'Timing is before or plausibly before definitive deal announcement',
        'Filing is NOT post-announcement proxy or background section',
        'Language is NOT generic boilerplate (rights plan, risk factor, S-8, director bio)',
        'Source text or external news source is available and cited',
        'At least one practical operator next action exists',
    ],
    'escalate_confidence_minimum': 0.65,
    'watch_confidence_minimum': 0.40,
    'evidence_grade_for_escalate': ('A', 'B', 'C'),
    'fallback_if_conditions_not_met': 'NEEDS_HUMAN_REVIEW',
    'note': (
        'Historical base rate: ~3.5% of scanner hits are true public prior signals. '
        'Default to skepticism. Require explicit process language, confirmed timing, '
        'and source-backed evidence before escalating.'
    ),
}


# ── Convenience exports ───────────────────────────────────────────────────────

ALL_TRUE_SIGNAL_KEYS = list(TRUE_SIGNAL_ARCHETYPES.keys())
ALL_FALSE_POSITIVE_KEYS = list(FALSE_POSITIVE_ARCHETYPES.keys())

# Flat phrase → archetype lookup for deterministic classification
_FP_PHRASE_MAP: dict[str, str] = {}
for _key, _arch in FALSE_POSITIVE_ARCHETYPES.items():
    for _phrase in _arch.get('deterministic_clues', []):
        _FP_PHRASE_MAP[_phrase.lower()] = _key

_TS_PHRASE_MAP: dict[str, str] = {}
for _key, _arch in TRUE_SIGNAL_ARCHETYPES.items():
    for _phrase in _arch.get('key_phrases', []):
        _TS_PHRASE_MAP[_phrase.lower()] = _key


def phrases_to_false_positive_archetypes(text: str) -> list[str]:
    """Return list of FP archetype keys matched by phrases in text."""
    text_lower = text.lower()
    matched: list[str] = []
    seen: set[str] = set()
    for phrase, key in _FP_PHRASE_MAP.items():
        if phrase in text_lower and key not in seen:
            matched.append(key)
            seen.add(key)
    return matched


def phrases_to_true_signal_archetypes(text: str) -> list[str]:
    """Return list of true-signal archetype keys matched by phrases in text."""
    text_lower = text.lower()
    matched: list[str] = []
    seen: set[str] = set()
    for phrase, key in _TS_PHRASE_MAP.items():
        if phrase in text_lower and key not in seen:
            matched.append(key)
            seen.add(key)
    return matched
