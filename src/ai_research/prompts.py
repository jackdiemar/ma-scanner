"""
prompts.py — Prompt construction for the AI investment gate.

build_investment_gate_prompt(case: dict) -> str

Returns a prompt that instructs the model to:
  - Classify whether the alert deserves deeper human research
  - Be skeptical and identify false positives
  - Cite the source excerpt provided
  - Separate facts from inference
  - Output ONLY valid JSON matching the gate schema
"""
from __future__ import annotations

import json


# ── Classification reference ──────────────────────────────────────────────────

_CLASSIFICATION_DESCRIPTIONS = {
    'PRE_PROCESS_OPPORTUNITY': (
        'Company-level strategic review, banker retention, unsolicited proposal, '
        'superior proposal, sale process, or board committee language BEFORE a deal is signed. '
        'The deal, if it happens, is not yet public. High research priority.'
    ),
    'REAL_STRATEGIC_REVIEW': (
        'Board or management is explicitly reviewing strategic alternatives '
        'or has engaged advisors for a sale process. Confirmed, ongoing process. '
        'Not yet a signed agreement.'
    ),
    'ALREADY_ANNOUNCED_DEAL': (
        'A definitive merger agreement, acquisition agreement, or plan of merger '
        'is already signed and publicly announced. Pre-deal edge no longer exists. '
        'Low value unless merger arb, which is out of scope.'
    ),
    'GENERIC_PARTNERSHIP_LANGUAGE': (
        'Alert triggered by strategic partnership, collaboration, licensing, '
        'or co-development language that does not imply company-level sale process. '
        'Partnerships do not constitute M&A process signals unless '
        'explicitly tied to strategic alternatives at the company level.'
    ),
    'ASSET_SPECIFIC_ONLY': (
        'ROFR, ROFN, licensing, or option language is asset-specific or '
        'product-level, not company-level. Insufficient evidence that the whole '
        'company is in play.'
    ),
    'FALSE_POSITIVE': (
        'Trigger phrase matched but the context is clearly not an M&A process signal. '
        'May be boilerplate, legal standard language, prior-period reference, '
        'or a phrase used in a non-deal context.'
    ),
    'WATCH_ONLY': (
        'Signal is real but evidence is weak, circumstantial, or early. '
        'Worth monitoring for follow-on filings but not escalating today.'
    ),
    'DISCARD': (
        'Alert should be removed from active monitoring. Signal is noise, '
        'the situation has resolved, or the thesis is clearly broken.'
    ),
    'NEEDS_HUMAN_REVIEW': (
        'Model is uncertain. The case has material ambiguity that requires '
        'a human analyst to review the primary source document before classifying.'
    ),
}

_RESEARCH_ACTION_DESCRIPTIONS = {
    'ESCALATE': (
        'Alert deserves immediate deeper diligence by a human analyst. '
        'Read the primary filing, check recent price action, look for corroborating signals.'
    ),
    'WATCH': (
        'Monitor for follow-on filings, price action, or news. '
        'No immediate action required.'
    ),
    'WAIT_FOR_PRICE': (
        'Signal may be valid but price has already moved significantly. '
        'Watch for a pullback or for confirmation before escalating.'
    ),
    'DISCARD': (
        'Remove from active monitoring.'
    ),
    'NEEDS_HUMAN_REVIEW': (
        'Human analyst must review source documents before a classification can be made.'
    ),
}

_OUTPUT_SCHEMA = {
    'ticker': 'string',
    'classification': ' | '.join(_CLASSIFICATION_DESCRIPTIONS.keys()),
    'research_action': ' | '.join(_RESEARCH_ACTION_DESCRIPTIONS.keys()),
    'confidence': 'float 0.0–1.0',
    'investability_score': 'integer 0–100',
    'evidence_strength': 'HIGH | MEDIUM | LOW',
    'priced_in_assessment': 'NOT_PRICED_IN | PARTLY_REPRICED | LIKELY_PRICED_IN | UNKNOWN',
    'time_sensitivity': 'HIGH | MEDIUM | LOW',
    'why_interesting': ['list of strings — facts supporting research value'],
    'why_not': ['list of strings — facts reducing research value or signalling FP'],
    'key_evidence': ['list of strings — specific phrases or facts cited from the source'],
    'missing_information': ['list of strings — what would confirm or deny the thesis'],
    'next_research_steps': ['list of strings — concrete analyst actions'],
    'human_review_questions': ['list of strings — specific questions for a human reviewer'],
}


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_investment_gate_prompt(case: dict) -> str:
    """
    Build a structured diligence prompt for the investment gate.

    The model is instructed to classify whether the alert warrants deeper
    human research. It is NOT asked to make trade recommendations.
    """
    ticker       = case.get('ticker', 'UNKNOWN')
    company_name = case.get('company_name', 'Unknown Company')

    # Build the case summary block
    case_summary_fields = {
        'Ticker':              ticker,
        'Company':             company_name,
        'Signal quality':      case.get('signal_quality', ''),
        'Signal type':         case.get('signal_type', ''),
        'Scanner action':      case.get('recommended_scanner_action', ''),
        'Conviction tier':     case.get('conviction_tier', ''),
        'Scanner score':       case.get('score', ''),
        'P(deal) estimate':    case.get('p_deal', ''),
        'Market cap':          _fmt_optional(case.get('market_cap')),
        'Price':               _fmt_optional(case.get('price')),
        'Priced-in flag':      case.get('priced_in_flag', ''),
        'Filing type':         case.get('filing_type', '') or 'Not available',
        'Filing date':         case.get('filing_date', '') or 'Not available',
        'Source URL':          case.get('source_url', '') or 'Not available',
        'Trigger phrase':      case.get('trigger_phrase', '') or 'Not available',
        'False positive risk': case.get('false_positive_risk', ''),
        'FP classification':   case.get('fp_classification', ''),
        'First seen':          case.get('first_seen', ''),
        'Last seen':           case.get('last_seen', ''),
    }
    scanner_flags = case.get('scanner_flags', [])
    source_excerpt = case.get('source_excerpt', '')
    memo_excerpt = case.get('memo_section_excerpt', '')

    case_block = '\n'.join(
        f'  {k}: {v}' for k, v in case_summary_fields.items() if str(v).strip()
    )

    flags_block = (
        '\n'.join(f'  - {f}' for f in scanner_flags)
        if scanner_flags else '  None.'
    )

    excerpt_block = (
        source_excerpt.strip()
        if source_excerpt
        else 'No source excerpt available. The scanner did not retrieve filing text for this alert.'
    )

    memo_block = memo_excerpt.strip() if memo_excerpt else 'No memo section available.'

    classifications_ref = '\n'.join(
        f'  {name}: {desc}'
        for name, desc in _CLASSIFICATION_DESCRIPTIONS.items()
    )
    schema_json = json.dumps(_OUTPUT_SCHEMA, indent=2)

    prompt = f"""You are a biotech M&A research analyst reviewing scanner alerts for potential strategic activity.

IMPORTANT INSTRUCTIONS:
- You are NOT making trade recommendations or investment advice.
- You are NOT advising anyone to buy or sell any security.
- Your sole task is to classify whether this scanner alert warrants deeper human research.
- Be skeptical. Most scanner alerts are false positives, already-announced deals, or low-signal noise.
- Do not hype vague or aspirational language in filings.
- Penalize heavily: signed merger agreements (already public, no edge), generic strategic partnership language, asset-specific ROFR/licensing unless company-level process is evidenced.
- Elevate only: explicit company-level strategic review, banker retention confirmed, unsolicited acquisition proposal, superior proposal clause, formal sale process, board committee language suggesting real process underway.
- A signed "merger agreement" in a filing usually means the deal is ALREADY ANNOUNCED — classify as ALREADY_ANNOUNCED_DEAL unless you have specific evidence otherwise.
- Separate facts from inference. Every claim in your output must cite the source excerpt or a specific scanner flag.
- If the source excerpt is unavailable, acknowledge this limitation and lower your confidence accordingly.
- Output ONLY valid JSON. No markdown code fences. No preamble. No explanation outside the JSON.

---

ALERT CASE SUMMARY: {ticker} — {company_name}

{case_block}

Scanner flags:
{flags_block}

Source excerpt (verbatim from filing or scanner, may be empty):
{excerpt_block}

Scanner memo section (context):
{memo_block}

---

CLASSIFICATION DEFINITIONS:
{classifications_ref}

---

OUTPUT SCHEMA (output ONLY this JSON, no other text):
{schema_json}

Fill every field. For list fields, provide at least one item if relevant evidence exists; use an empty list [] only if truly nothing applies.
Set confidence based on how certain you are of your classification (0.0 = no idea, 1.0 = certain).
Set investability_score 0–100 based on likelihood this is a genuine pre-deal research opportunity (not a trade signal — a research-worth signal).
Cite specific phrases from the source excerpt in key_evidence where available.

Produce your JSON assessment now:"""

    return prompt


def _fmt_optional(value) -> str:
    if value is None or str(value).strip() in ('', 'None', 'null'):
        return 'Not available'
    return str(value)
