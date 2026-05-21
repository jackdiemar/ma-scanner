"""
prompts.py — Prompt construction for the AI investment gate.

build_investment_gate_prompt(case: dict, strategy_features: dict | None) -> str

Returns a strategy-calibrated prompt that instructs the model to:
  - Apply our historical base rates and true-signal taxonomy
  - Explicitly compare the case to MDVN, DMTX, TSRO
  - Identify which false-positive archetype applies
  - Use deterministic pre-LLM strategy features
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
    # ── Core classification ────────────────────────────────────────────────
    'ticker': 'string',
    'classification': ' | '.join(_CLASSIFICATION_DESCRIPTIONS.keys()),
    'research_action': ' | '.join(_RESEARCH_ACTION_DESCRIPTIONS.keys()),
    'confidence': 'float 0.0–1.0',
    'investability_score': 'integer 0–100',
    'evidence_strength': 'HIGH | MEDIUM | LOW',
    'priced_in_assessment': 'NOT_PRICED_IN | PARTLY_REPRICED | LIKELY_PRICED_IN | UNKNOWN',
    'time_sensitivity': 'HIGH | MEDIUM | LOW',
    # ── Existing list fields ───────────────────────────────────────────────
    'why_interesting': ['list of strings — facts supporting research value'],
    'why_not': ['list of strings — facts reducing research value or signalling FP'],
    'key_evidence': ['list of strings — specific phrases or facts cited from the source'],
    'missing_information': ['list of strings — what would confirm or deny the thesis'],
    'next_research_steps': ['list of strings — concrete analyst actions'],
    'human_review_questions': ['list of strings — specific questions for a human reviewer'],
    # ── Narrative fields ───────────────────────────────────────────────────
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
    # ── Strategy intelligence fields (NEW) ────────────────────────────────
    'strategy_bucket': 'Which strategy category this falls into — e.g. ALREADY_ANNOUNCED_DEAL, POTENTIAL_TRUE_SIGNAL, etc.',
    'matched_true_signal_archetypes': ['list — which of PUBLIC_UNSOLICITED_PROPOSAL, SUPERIOR_PROPOSAL_OR_COMPETING_BID, CREDIBLE_MEDIA_SALE_PROCESS_REPORT apply'],
    'matched_false_positive_archetypes': ['list — which FP archetypes apply (ALREADY_ANNOUNCED_MERGER, POST_ANNOUNCEMENT_PROXY_BACKGROUND, etc.)'],
    'historical_analogue': 'Which historical case this most resembles — MDVN, DMTX, TSRO, or none',
    'true_signal_similarity_score': 'integer 0–100 — how similar to MDVN/DMTX/TSRO true signal archetypes',
    'false_positive_similarity_score': 'integer 0–100 — how similar to known false-positive archetypes',
    'timing_edge_score': 'integer 0–100 — likelihood pre-announcement timing edge is still open',
    'company_level_process_score': 'integer 0–100 — probability this reflects a company-level strategic process',
    'process_specificity_score': 'integer 0–100 — how specific and credible is the process language',
    'investability_setup_score': 'integer 0–100 — composite research-priority score',
    'deterministic_strategy_summary': 'One paragraph summarizing what the deterministic classifier found and why',
    # ── Practical analysis fields (NEW) ───────────────────────────────────
    'why_this_fired': 'Exact trigger phrase and scanner mechanism that caused this alert',
    'why_this_is_or_is_not_actionable': 'Direct explanation of actionability — do not hedge',
    'why_not_like_true_signal_examples': 'Explicit comparison: why this is or is not like MDVN/DMTX/TSRO',
    'how_it_compares_to_mdvn_dmtx_tsro': 'Named comparison to MDVN (unsolicited), DMTX (superior proposal), TSRO (media report)',
    'what_market_may_already_know': 'What market participants likely already know or have priced in',
    'what_operator_should_check_next': 'Single most important next check for the operator',
    'monitoring_plan': 'What to watch after this — specific filings, dates, or events',
    'kill_criteria': 'What evidence would definitively close this case',
    'escalation_criteria': 'What additional evidence would warrant escalation to ESCALATE',
    'next_filing_or_news_to_watch': 'Specific filing type or news category to monitor',
    'suggested_follow_up_queries': ['list — specific search terms or filing queries for follow-up'],
}


# ── Historical context block ──────────────────────────────────────────────────

_HISTORICAL_CONTEXT = """HISTORICAL BASE RATES (from 50-case and 86-case reviews):
- Only 3 of 50 small-cap biotech acquisitions (2015-2022) had true public prior process signals.
- Base rate: ~6% in 50-case review, ~3.5% in expanded 86-case review.
- Batch 71-100 found ZERO true public prior signals.
- 70% of cases: DEAL_ANNOUNCEMENT_BASELINE — deal already announced when scanner fires.
- 16% of cases: PRIVATE_BACKGROUND_ONLY — process was entirely private before announcement.
- 6%  of cases: TRUE_PUBLIC_PRIOR_SIGNAL — what we are looking for.

IMPLICATION: Default to skepticism. Most alerts are classifiable false positives.
The edge is not predicting every deal. The edge is the rare case with SOURCE-BACKED
PUBLIC process evidence BEFORE the market fully prices it.

TRUE SIGNAL ARCHETYPES (the only 3 historical examples):

1. MDVN (Medivation) — PUBLIC_UNSOLICITED_PROPOSAL:
   - Sanofi made a public unsolicited proposal disclosed April 28, 2016
   - 116 days before Pfizer's final acquisition announcement (August 22, 2016)
   - Key features: named acquirer, public board response, company-level pressure, EDGAR-catchable
   - Signal type: explicit public unsolicited acquisition proposal in 8-K or press release

2. DMTX (Dimension Therapeutics) — SUPERIOR_PROPOSAL_OR_COMPETING_BID:
   - Public superior proposal / competing-bid activity began August 25, 2017
   - 39 days before Ultragenyx announcement (October 3, 2017)
   - Key features: superior proposal clause triggered, competing bid, fiduciary process public
   - Signal type: superior proposal / fiduciary out language publicly disclosed before definitive deal

3. TSRO (Tesaro) — CREDIBLE_MEDIA_SALE_PROCESS_REPORT:
   - External media report of sale process published November 16, 2018
   - 17 days before GSK announcement (December 3, 2018)
   - Key features: credible media outlet, named potential acquirers, before definitive agreement
   - IMPORTANT CAVEAT: EDGAR-only workflow would NOT catch this — requires news integration
   - Shortest lead time of the three examples

FALSE POSITIVE TAXONOMY (what to name explicitly in your analysis):
- ALREADY_ANNOUNCED_MERGER: definitive agreement already signed — no pre-announcement edge
- POST_ANNOUNCEMENT_PROXY_BACKGROUND: proxy/SC 14D-9 background section — process is historical
- ASSET_SPECIFIC_RIGHTS_ONLY: ROFR/ROFN on a specific asset — not company-level
- GENERIC_RIGHTS_LANGUAGE: rights plan, poison pill, change-of-control clause — standard boilerplate
- OFFERING_PROSPECTUS_RISK_FACTOR: S-1/424B risk factor language — required disclosure boilerplate
- S8_EQUITY_PLAN_BOILERPLATE: S-8 vesting / change-of-control acceleration — compensation boilerplate
- DIRECTOR_BIO_PRIOR_DEAL: director biography referencing a historical deal — not current process
- WRONG_DIRECTION_ACQUISITION: this company is the acquirer, not the target
- PRIVATE_BACKGROUND_ONLY: process was private; public evidence only appeared post-announcement
- EQUITY_INVESTMENT_NO_ACQUISITION_OPTION: equity stake without company-level option
- NEGATED_ACQUISITION_LANGUAGE: filing explicitly denies M&A activity
- GENERIC_PARTNERSHIP_OR_LICENSE: collaboration/license deal — commercial, not M&A"""


_STRATEGY_CONTEXT = """OUR RESEARCH STRATEGY:
We are NOT trying to predict every biotech M&A deal.
We ARE trying to identify public, pre-announcement process evidence suggesting a company may be
in or near a strategic process — BEFORE the market fully prices it.

HIGH-VALUE signals (escalate or watch):
- Explicit "strategic alternatives review" or "sale process" language in 8-K before a deal is announced
- Company-level banker or financial advisor retention for strategic alternatives
- Unsolicited acquisition proposal disclosed in 8-K or proxy
- Superior proposal / competing bid language in merger proxy BEFORE definitive deal
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
- S-8 equity plan change-of-control vesting provisions
- Director biography references to prior deals

CALIBRATION:
- "merger agreement" in a filing almost always = ALREADY ANNOUNCED → ALREADY_ANNOUNCED_DEAL → DISCARD
- "change of control" in executive comp = standard boilerplate → FALSE_POSITIVE
- "strategic alternatives" in 10-K risk factor = boilerplate → FALSE_POSITIVE
- "strategic alternatives" in 8-K with banker retention = HIGH VALUE → PRE_PROCESS_OPPORTUNITY

REQUIRED ANALYSIS FORMAT:
You MUST NOT simply say "ALREADY_ANNOUNCED_DEAL → DISCARD" without:
1. Quoting the exact phrase from the filing that proves this
2. Naming which FP archetype applies (e.g., ALREADY_ANNOUNCED_MERGER)
3. Explaining why this kills the pre-process edge
4. Stating what would change the decision
5. Stating what (if anything) to monitor next
6. Explicitly comparing to MDVN/DMTX/TSRO — even if the answer is "unlike all three"
This requirement applies even when the answer is clearly DISCARD."""


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_acquisition_intelligence_prompt(
    case: dict,
    situation_result: dict | None = None,
    prob_result: dict | None = None,
    analogues_context: str = '',
    external_research_context: str = '',
) -> str:
    """
    Assemble a standalone acquisition intelligence context block for LLM injection.
    Can be called independently or used within build_investment_gate_prompt.
    """
    ticker = case.get('ticker', 'UNKNOWN')
    blocks: list[str] = []

    # Situation classification block
    if situation_result:
        try:
            from ai_research.acquisition_situation_classifier import format_situation_classification_for_prompt
            blocks.append(format_situation_classification_for_prompt(situation_result))
        except Exception:
            blocks.append(f'ACQUISITION SITUATION: {situation_result.get("primary_acquisition_situation", "UNKNOWN")}')

    # Probability engine block
    if prob_result:
        try:
            from ai_research.acquisition_probability_engine import format_probability_for_prompt
            blocks.append(format_probability_for_prompt(prob_result))
        except Exception:
            score = prob_result.get('acquisition_research_probability_score', 0)
            bucket = prob_result.get('probability_bucket', '')
            blocks.append(f'PROBABILITY ENGINE: Score={score}/100 | Bucket={bucket}')

    # Completed deal analogues block
    if analogues_context:
        blocks.append(analogues_context)

    # External research block
    if external_research_context:
        blocks.append(external_research_context)

    return '\n\n---\n\n'.join(blocks) if blocks else ''


def build_investment_gate_prompt(
    case: dict,
    strategy_features: dict | None = None,
    situation_result: dict | None = None,
    prob_result: dict | None = None,
    analogues_context: str = '',
) -> str:
    """
    Build a strategy-calibrated diligence prompt for the investment gate.

    Args:
        case:              Research case dict.
        strategy_features: Output of strategy_classifier.run_strategy_classification(case).
                           If None, prompt runs without deterministic pre-analysis.
    """
    ticker       = case.get('ticker', 'UNKNOWN')
    company_name = case.get('company_name', 'Unknown Company')

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
    scanner_flags  = case.get('scanner_flags', [])
    source_excerpt = case.get('source_excerpt', '')
    memo_excerpt   = case.get('memo_section_excerpt', '')

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

    # Evidence quality block
    eq          = case.get('evidence_quality', {})
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

    # Strategy features block
    if strategy_features:
        from ai_research.strategy_classifier import format_strategy_features_for_prompt
        strategy_block = format_strategy_features_for_prompt(strategy_features)
    else:
        strategy_block = 'DETERMINISTIC STRATEGY ANALYSIS: Not available (run strategy_classifier first).'

    # Acquisition intelligence block (situation classifier + probability engine + analogues)
    acq_intel_block = ''
    if situation_result or prob_result or analogues_context:
        acq_intel_block = build_acquisition_intelligence_prompt(
            case,
            situation_result=situation_result,
            prob_result=prob_result,
            analogues_context=analogues_context,
        )

    # Build extra instructions for acquisition intelligence fields
    acq_intel_instructions = ''
    if situation_result or prob_result:
        acq_intel_instructions = """
19. ACQUISITION INTELLIGENCE FIELDS (use the pre-computed values above as your starting point):
    - primary_acquisition_situation: The primary situation type from the deterministic classifier.
    - completed_deal_analogues (in output): Pick at most 2 ticker names from the analogues block.
    - acquisition_research_probability_score: You may adjust ±10 from the engine score based on excerpt context.
    - probability_bucket: Confirm or adjust the pre-computed bucket based on excerpt evidence.
    - is_explicit_process_signal: True only if excerpt contains explicit process language (8-K strategic alternatives, unsolicited proposal, superior proposal, active sale process — NOT catalyst-only or boilerplate).
    - is_setup_signal_only: True if only setup signals (catalyst, distress, ROFR) — no explicit process.
    - why_probability_not_higher: 1-2 sentences explaining what evidence is missing.
    - evidence_needed_to_upgrade: 2-3 specific pieces of evidence that would upgrade the bucket.
    - successful_deal_traits_present: What does this case share with MDVN/DMTX/TSRO?
    - successful_deal_traits_missing: What key traits are absent compared to true-signal examples?
    - what_operator_should_check_next: Most important next action (specific filing or search).
"""

    prompt = f"""You are a biotech M&A research analyst reviewing scanner alerts for potential strategic activity.

IMPORTANT INSTRUCTIONS:
- You are NOT making transaction recommendations or investment advice.
- You are NOT advising anyone to transact in any security.
- Your sole task is to classify whether this scanner alert warrants deeper human research.
- Be skeptical. Most scanner alerts are false positives, already-announced deals, or low-signal noise.
- Base rate: only ~3.5% of scanner hits are true public prior process signals.
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

{_HISTORICAL_CONTEXT}

---

{_STRATEGY_CONTEXT}

---

{strategy_block}

---

{acq_intel_block}

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

3. evidence_summary: Quote the EXACT trigger phrase or key phrase from the source excerpt.
   If excerpt is empty, say so explicitly.

4. source_timing_analysis: State the filing date and assess whether the opportunity window is still open.

5. signal_quality_analysis: Be specific. Name the trigger phrase. Explain whether it is strong
   pre-announcement evidence or generic boilerplate.

6. why_this_fired: Name the exact scanner trigger and why the phrase matched.

7. how_it_compares_to_mdvn_dmtx_tsro: Write 2-3 sentences comparing this case to each of:
   - MDVN (public unsolicited proposal, 116 days edge)
   - DMTX (superior proposal/competing bid, 39 days edge)
   - TSRO (credible media sale process report, 17 days edge)
   Be explicit about whether it resembles any of them and why or why not.

8. why_not_like_true_signal_examples: Explain specifically why this does or does not meet
   the true-signal criteria. Quote the specific phrase that proves your conclusion.

9. historical_analogue: State which historical case this most resembles (MDVN, DMTX, TSRO,
   DEAL_ANNOUNCEMENT_BASELINE, PRIVATE_BACKGROUND_ONLY, ASSET_SPECIFIC_RIGHTS_ONLY) and why.

10. matched_false_positive_archetypes: List all applicable FP archetypes from:
    ALREADY_ANNOUNCED_MERGER | POST_ANNOUNCEMENT_PROXY_BACKGROUND | ASSET_SPECIFIC_RIGHTS_ONLY |
    GENERIC_RIGHTS_LANGUAGE | OFFERING_PROSPECTUS_RISK_FACTOR | S8_EQUITY_PLAN_BOILERPLATE |
    DIRECTOR_BIO_PRIOR_DEAL | WRONG_DIRECTION_ACQUISITION | PRIVATE_BACKGROUND_ONLY |
    EQUITY_INVESTMENT_NO_ACQUISITION_OPTION | NEGATED_ACQUISITION_LANGUAGE | GENERIC_PARTNERSHIP_OR_LICENSE

11. operator_next_steps: Be concrete. If action=DISCARD, write "Discard — [specific reason]."
    If action=ESCALATE, write specific analyst actions. If action=WATCH, write what to monitor.

12. kill_criteria: What evidence would definitively close this case (e.g., "Deal closes and delisted",
    "Company confirms no process in 8-K").

13. escalation_criteria: What additional evidence would upgrade this to ESCALATE.

14. monitoring_plan: Specific next filing type, date, or event to watch.

15. key_reasons: Each item is a standalone fact starting with a verb. 3-5 items.

16. discard_reason / escalation_reason / human_review_reason: Fill the appropriate one.

17. investability_score scoring:
   - 0-10: DISCARD or FALSE_POSITIVE (no research value)
   - 10-40: WATCH_ONLY (weak signal, monitor only)
   - 40-70: WATCH (real signal, monitor actively)
   - 70-100: ESCALATE or PRE_PROCESS_OPPORTUNITY (high priority, read filing now)

18. Strategy score fields (true_signal_similarity_score, false_positive_similarity_score,
    timing_edge_score, company_level_process_score, process_specificity_score,
    investability_setup_score): Use the deterministic analysis above as your starting point,
    then adjust based on the source excerpt content. Do not just copy the deterministic scores —
    adjust if the excerpt shows different evidence.

{acq_intel_instructions}

OUTPUT SCHEMA (output ONLY this JSON, no other text):
{schema_json}

Fill every field. For list fields, provide at least one item if relevant evidence exists.
Set confidence based on how certain you are of your classification (0.0 = no idea, 1.0 = certain).
Cite specific phrases from the source excerpt in key_evidence and evidence_summary.

Produce your JSON assessment now:"""

    return prompt


def _fmt_optional(value) -> str:
    if value is None or str(value).strip() in ('', 'None', 'null'):
        return 'Not available'
    return str(value)
