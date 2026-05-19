"""
prompts.py — Prompt construction for the AI investment gate.

build_investment_gate_prompt(case: dict) -> str

Returns a prompt that instructs the model to:
  - Classify whether the alert deserves deeper human research
  - Be skeptical and identify false positives
  - Cite the source excerpt provided
  - Separate facts from inference
  - Fill every field in the expanded output schema
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
    # ── Existing fields ─────────────────────────────────────────────────────
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
    # ── New fields ──────────────────────────────────────────────────────────
    'short_thesis': '1-2 sentence direct statement of what this case is and whether it is actionable',
    'why_this_matters': 'Why this signal type is or is not strategically significant',
    'why_now': 'Timing context — is the signal fresh, stale, post-announcement?',
    'evidence_summary': 'What evidence was actually found — quote or paraphrase from excerpt',
    'source_timing_analysis': 'Filing date vs today — is opportunity window still open?',
    'signal_quality_analysis': 'Is the trigger phrase strong pre-announcement evidence or generic boilerplate? Be specific.',
    'priced_in_analysis': 'Is market likely aware? What does price/mcap data suggest?',
    'false_positive_risk': 'Main false positive risk for this specific case',
    'key_reasons': ['list of 3-5 verb-led facts driving the decision'],
    'operator_next_steps': ['list of 2-4 concrete specific actions for operator'],
    'what_would_change_the_decision': 'What new evidence/event would change classification',
    'watch_triggers': ['if action=WATCH, specific events to watch for'],
    'discard_reason': 'Required if action=DISCARD — single clearest reason to discard. Else empty string.',
    'escalation_reason': 'Required if action=ESCALATE — what makes this urgent. Else empty string.',
    'human_review_reason': 'Required if action=NEEDS_HUMAN_REVIEW — what human should look for. Else empty string.',
}


# ── Strategy context ──────────────────────────────────────────────────────────

_STRATEGY_CONTEXT = """OUR RESEARCH STRATEGY:
We are NOT trying to predict every biotech M&A deal.
We ARE trying to identify public, pre-announcement process evidence suggesting a company may be in or near a strategic process — BEFORE the market fully prices it.

HIGH-VALUE signals (escalate or watch):
- Explicit "strategic alternatives review" or "sale process" language in 8-K before a deal is announced
- Company-level banker or financial advisor retention for strategic alternatives
- Unsolicited acquisition proposal disclosed in 8-K or proxy
- Superior proposal / competing bid language in merger proxy
- Credible activist 13D Item 4 acquisition pressure citing company-level strategic value
- Board committee specifically formed to evaluate strategic alternatives

LOW-VALUE / DISCARD signals:
- Already-announced merger agreement or acquisition (deal is public, opportunity gone)
- Post-announcement proxy (background section describes process that already happened)
- Generic rights agreement or poison pill (anti-takeover, not a process signal)
- Asset-specific ROFR, ROFN, or ROFO (product/asset level, not company level)
- Equity investment or minority stake without acquisition option at company level
- Stale signal (filing is months or years old)
- Offering prospectus boilerplate change-of-control risk factor language
- Negated language: "no acquisition proposal has been received"

CALIBRATION:
- "merger agreement" in a filing almost always = ALREADY ANNOUNCED → ALREADY_ANNOUNCED_DEAL → DISCARD
- "change of control" in executive comp = standard boilerplate → FALSE_POSITIVE unless tied to actual process
- "strategic alternatives" in 10-K risk factor = boilerplate → FALSE_POSITIVE unless it's an 8-K disclosure of an actual review"""


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_investment_gate_prompt(case: dict) -> str:
    """
    Build a structured diligence prompt for the investment gate.

    The model is instructed to classify whether the alert warrants deeper
    human research. It is NOT asked to make transaction recommendations.
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

    # Build evidence quality block
    eq = case.get('evidence_quality', {})
    eq_grade    = eq.get('evidence_grade', 'F') if eq else 'F'
    eq_score    = eq.get('evidence_completeness_score', 0) if eq else 0
    eq_gaps     = eq.get('evidence_gaps', []) if eq else []
    eq_quotes   = eq.get('top_evidence_quotes', []) if eq else []
    eq_can      = eq.get('can_make_confident_decision', False) if eq else False
    eq_sec      = eq.get('source_is_sec', False) if eq else False

    gaps_block = '\n'.join(f'  - {g}' for g in eq_gaps) if eq_gaps else '  None.'
    quotes_block_lines: list[str] = []
    for q in eq_quotes[:5]:
        phrase  = q.get('phrase', '')
        context = q.get('context', '')
        reason  = q.get('reason', '')
        src     = q.get('source', '')
        quotes_block_lines.append(
            f'  [{src}] phrase="{phrase}" reason="{reason}"\n  context: {context[:300]}'
        )
    quotes_block = '\n\n'.join(quotes_block_lines) if quotes_block_lines else '  No quotes extracted.'

    d_or_f_warning = ''
    if eq_grade in ('D', 'F'):
        d_or_f_warning = (
            '\nEVIDENCE WARNING: Evidence grade is ' + eq_grade + '. '
            'Source excerpt is absent or very short. Full filing text was not fetched. '
            'You MUST return NEEDS_HUMAN_REVIEW for any actionable classification (PRE_PROCESS_OPPORTUNITY, '
            'REAL_STRATEGIC_REVIEW, ESCALATE) unless the signal is clearly already a signed merger agreement '
            'or obviously a false positive. Set confidence <= 0.40.'
        )

    prompt = f"""You are a biotech M&A research analyst reviewing scanner alerts for potential strategic activity.

IMPORTANT INSTRUCTIONS:
- You are NOT making transaction recommendations or investment advice.
- You are NOT advising anyone to transact in any security.
- Your sole task is to classify whether this scanner alert warrants deeper human research.
- Be skeptical. Most scanner alerts are false positives, already-announced deals, or low-signal noise.
- Do not hype vague or aspirational language in filings.
- Penalize heavily: signed merger agreements (already public, no edge), generic strategic partnership language, asset-specific ROFR/licensing unless company-level process is evidenced.
- Elevate only: explicit company-level strategic review, banker retention confirmed, unsolicited acquisition proposal, superior proposal clause, formal sale process, board committee language suggesting real process underway.
- A signed "merger agreement" in a filing usually means the deal is ALREADY ANNOUNCED — classify as ALREADY_ANNOUNCED_DEAL unless you have specific evidence otherwise.
- Separate facts from inference. Every claim in your output must cite the source excerpt or a specific scanner flag.
- You may ONLY reference evidence that appears in the source excerpt, extracted quotes, or scanner flags below.
- Do NOT infer or hallucinate details not present in the provided evidence.
- If the source excerpt is unavailable, acknowledge this limitation and lower your confidence accordingly.
- Output ONLY valid JSON. No markdown code fences. No preamble. No explanation outside the JSON.{d_or_f_warning}

---

{_STRATEGY_CONTEXT}

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

EVIDENCE QUALITY ASSESSMENT:
  Grade          : {eq_grade}  (A=best, F=worst — determines confidence ceiling)
  Score          : {eq_score}/100
  Source is SEC  : {eq_sec}
  Can be confident: {eq_can}

Evidence gaps (what is missing):
{gaps_block}

Extracted evidence quotes (from excerpt and/or full filing text):
{quotes_block}

---

CLASSIFICATION DEFINITIONS:
{classifications_ref}

---

FIELD-BY-FIELD INSTRUCTIONS (fill every field — do not skip any):

1. CLASSIFY using exactly one classification from the list. Most alerts are ALREADY_ANNOUNCED_DEAL,
   FALSE_POSITIVE, or GENERIC_PARTNERSHIP_LANGUAGE. Default to skepticism.

2. short_thesis: Write 1-2 direct sentences saying what this case is and whether it is actionable.
   Example: "APLS has a signed merger agreement with Apellis Pharmaceuticals announced publicly.
   This is a completed deal; there is no pre-announcement edge."

3. evidence_summary: Quote or paraphrase the actual trigger phrase or evidence from the source excerpt.
   If excerpt is empty, say so explicitly: "No source excerpt was provided."

4. source_timing_analysis: State the filing date and today's approximate date. Assess whether the
   opportunity window (if any) is still open. A filing from months ago with a signed merger agreement
   means the window closed long ago.

5. signal_quality_analysis: Be specific. Name the trigger phrase. Explain whether it is strong
   pre-announcement evidence (e.g., an actual 8-K disclosing a strategic review) or generic boilerplate
   (e.g., a change-of-control clause in an employment agreement or a 10-K risk factor).

6. operator_next_steps: Be concrete. If action=DISCARD, write "Discard — [specific reason]."
   If action=ESCALATE, write specific analyst actions. If action=WATCH, write what to monitor.

7. key_reasons: Each item is a standalone fact starting with a verb. 3-5 items.
   Example: ["Contains signed merger agreement dated X", "Deal publicly announced on Y", "No pre-announcement edge remains"]

8. discard_reason: Fill if action=DISCARD. Leave as "" otherwise.
   escalation_reason: Fill if action=ESCALATE. Leave as "" otherwise.
   human_review_reason: Fill if action=NEEDS_HUMAN_REVIEW. Leave as "" otherwise.

9. investability_score: Use these ranges:
   - 0-10: DISCARD or FALSE_POSITIVE (no research value)
   - 10-40: WATCH_ONLY (weak signal, monitor only)
   - 40-70: WATCH (real signal, monitor actively)
   - 70-100: ESCALATE or PRE_PROCESS_OPPORTUNITY (high priority, read filing now)

10. watch_triggers: Only fill if action=WATCH. List specific events that would trigger escalation.
    Example: ["Follow-on 8-K disclosing banker retention", "Price movement >15% without news"]

11. what_would_change_the_decision: What new evidence or event would change your classification?

OUTPUT SCHEMA (output ONLY this JSON, no other text):
{schema_json}

Fill every field. For list fields, provide at least one item if relevant evidence exists; use [] only if truly nothing applies.
Set confidence based on how certain you are of your classification (0.0 = no idea, 1.0 = certain).
Cite specific phrases from the source excerpt in key_evidence and evidence_summary where available.

Produce your JSON assessment now:"""

    return prompt


def _fmt_optional(value) -> str:
    if value is None or str(value).strip() in ('', 'None', 'null'):
        return 'Not available'
    return str(value)
