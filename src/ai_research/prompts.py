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
    'sa_type_final': 'ACQUISITION_PROCESS | CAPITAL_RAISE | ASSET_DIVESTITURE | PARTNERSHIP_LICENSING | MERGER_OF_EQUALS | WIND_DOWN | RESTRUCTURING | SHAREHOLDER_RETURN | AMBIGUOUS — your classification of the SA type based on all evidence',
    'sa_type_reasoning': 'Why you classified it as this SA type. Quote specific language.',
    'banker_mandate_final': 'SALE_MANDATE | STRATEGIC_REVIEW | DEFENSE_MANDATE | FAIRNESS_OPINION | CAPITAL_MARKETS | PARTNERSHIP_BANKER | RESTRUCTURING_ADVISOR | UNKNOWN — your classification of the banker mandate',
    'banker_mandate_reasoning': 'Why you classified the banker mandate this way. What specific language confirmed or contradicted the deterministic result? What does the identity of the bank tell you about the likely mandate?',
    'banker_mandate_changes_thesis': 'bool — does the banker mandate classification change your overall research action vs. what SA language alone would suggest? Explain.',
    'distress_assessment': 'DISTRESS_DRIVEN | PROACTIVE | UNCLEAR — was the SA announcement reactive to a stock crash or proactive value maximization?',
    'distress_impact_on_thesis': 'How distress (or absence of it) affects the investment thesis and expected acquirer premium.',
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
    # ── Diligence memo fields (depth=diligence_memo) ──────────────────────────
    'one_sentence_bottom_line': 'Single sentence research verdict. No hedging. E.g.: "XXXX is already-announced — no edge." or "XXXX has credible 8-K process signal — read now."',
    'executive_case_takeaway': '2-3 sentence executive summary: what happened, what the evidence shows, the research verdict.',
    'why_this_case_matters_now': 'Timing and freshness context. Is this fresh (<30 days), stale (>90 days), or recurring noise? Does timing create any edge?',
    'source_evidence_read': 'Precise paraphrase or direct quote of the key filing language driving this decision.',
    'exact_quotes_used': ['list of 1-3 exact quotes from source excerpt or full filing text — the specific strings you relied on. If unavailable, say so explicitly.'],
    'acquisition_situation_read': 'Acquisition situation pattern. E.g.: ALREADY_ANNOUNCED_DEAL, PRE_PROCESS_SETUP, SALE_PROCESS_ACTIVE, CATALYST_ONLY, BOILERPLATE_FP.',
    'completed_deal_analogue_read': 'Which completed deal (MDVN/DMTX/TSRO or other) does this most resemble? State the specific similarity or dissimilarity.',
    'probability_bucket_read': 'Probability bucket with 1-2 sentence justification. Reference the ~3.5% base rate.',
    'what_is_already_known_by_market': 'What market participants likely already know: announcements, proxies, press releases already public.',
    'what_is_not_yet_answered': '2-3 key unanswered questions a diligence analyst would need to resolve before acting.',
    'operator_decision': 'ESCALATE | WATCH | WAIT_FOR_PRICE | DISCARD | NEEDS_HUMAN_REVIEW — restate research_action explicitly here.',
    'immediate_next_steps': ['list of 2-4 specific concrete actions for the next 24-48 hours'],
    'next_sources_to_check': ['list of 2-4 specific sources to check: e.g., "EDGAR 8-K filings for XXXX", "CapIQ advisor retention search", "SEC EDGAR full-text XXXX strategic alternatives"'],
    'what_would_upgrade': 'Single specific piece of evidence that would upgrade the classification to ESCALATE.',
    'what_would_downgrade': 'Evidence that would definitively close or kill this case.',
    'why_this_is_not_actionable_yet': 'For WATCH/DISCARD/NEEDS_HUMAN_REVIEW: the exact gap preventing escalation right now.',
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
- DISTRESS-DRIVEN SA: stock dropped >20% in 30 days BEFORE the SA filing (reactive, not proactive)
- CAPITAL RAISE framed as strategic alternatives (runway extension, PIPE, debt financing)
- PARTNERSHIP/LICENSING for a specific drug or program — not company-level SA
- WIND-DOWN or dissolution announced alongside SA (different risk profile entirely)
- RESTRUCTURING alongside SA without explicit M&A language (cost-cutting, not sale process)

SA TYPE CLASSIFICATION — REQUIRED:
Every case must explicitly identify what TYPE of strategic alternatives process this is:
- ACQUISITION_PROCESS: company-level sale, merger, business combination with named/unnamed acquirer
- CAPITAL_RAISE: financing, equity offering, runway extension, royalty monetization
- ASSET_DIVESTITURE: selling specific programs/assets, not the whole company
- PARTNERSHIP_LICENSING: collaboration or licensing deal (drug or program level)
- MERGER_OF_EQUALS: combination, reverse merger, SPAC
- WIND_DOWN: dissolution, liquidation, cease operations
- RESTRUCTURING: cost reduction, headcount reduction alongside SA language
- SHAREHOLDER_RETURN: buyback, dividend, spin-off
- AMBIGUOUS: genuine uncertainty — requires deeper read of full filing

The pre-provided `sa_type` field gives the deterministic classifier result. Use it as a starting point but override with evidence from the filing text if the classifier is wrong. State your reasoning.

BANKER MANDATE ANALYSIS — REQUIRED:
The pre-provided banker fields show the deterministic classifier result. You must go further:

1. Mandate type matters more than banker presence. "Retained Goldman" is weak. "Engaged Goldman as exclusive financial advisor to assist in exploring strategic alternatives intended to maximize stockholder value" is strong.

2. Banker identity shifts the prior:
   - ELITE boutiques (Evercore, Centerview, Perella, Moelis, Lazard): primary business is M&A advisory. If retained here, default assumption is sale-side mandate unless context says otherwise.
   - Bulge bracket (Goldman, Morgan Stanley, JPMorgan): do both M&A and ECM. Mandate must be confirmed from context.
   - Biotech-focused ECM banks (Leerink, Piper Sandler, Stifel, Cowen, SVB): frequently retained for equity offerings. Presence alone does not indicate M&A mandate — confirm from excerpt.
   - Regional (Needham, HC Wainwright, Oppenheimer): typically capital markets. M&A mandate unlikely without explicit language.

3. Exclusivity is a strong signal. "Exclusive financial advisor" means the board has committed to running a single-advisor process — not just keeping options open.

4. Defense mandates nullify pre-process signal. If banker retained "in connection with the unsolicited proposal" — they are defending, not selling. Classify as DEFENSE_MANDATE, downgrade to WATCH or DISCARD.

5. Fairness opinions are post-process. If retained "to render a fairness opinion" — the deal is already agreed. No edge.

State explicitly: (a) what the banker mandate is, (b) whether the banker identity is consistent with that mandate, (c) whether this changes your classification vs. SA language alone.

DISTRESS FLAG — CHECK REQUIRED:
The pre-provided `distress_driven_sa`, `distress_severity`, and `price_change_30d_pct` fields show price action 30 days before the SA filing. If DISTRESS_DRIVEN_SA=true:
- The SA is likely reactive (board responding to crisis), not proactive (board seeking value maximization)
- Acquirer premium is compressed because stock already crashed — they're buying damaged goods
- The pre-announcement timing edge is partially or fully consumed by the distress event itself
- This is a FUNDAMENTALLY DIFFERENT risk profile — downgrade unless you have evidence the pipeline/IP value is intact despite the stock move
State explicitly whether distress changes your classification and why.

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


# ── Diligence memo extra instructions ────────────────────────────────────────

_DILIGENCE_MEMO_INSTRUCTIONS = """DILIGENCE MEMO DEPTH — REQUIRED ADDITIONAL ANALYSIS:
You are producing a full diligence research memo, not just a classification. Fill ALL fields below.

20. one_sentence_bottom_line: One direct sentence a portfolio manager reads first.
    Bad: "This case warrants monitoring." Good: "SDGR merger agreement already signed — ALREADY_ANNOUNCED_DEAL, no edge."

21. executive_case_takeaway: 2-3 sentences. What happened. What the evidence shows. The research verdict.
    Do NOT hedge. Be direct about whether there is any pre-announcement opportunity.

22. why_this_case_matters_now: Is the signal fresh (<30 days from filing date), stale, or recurring noise?
    Explain timing context. Does the filing date create or eliminate any timing edge?

23. source_evidence_read: Quote or closely paraphrase the specific filing language that drives the decision.
    If filing text is not retrieved, state: "Filing text not retrieved — based on scanner excerpt only."

24. exact_quotes_used: 1-3 exact quotes from source_excerpt or full filing text.
    Format: ["exact language from filing", "second key phrase if distinct"].
    If no text available: ["[Filing text not retrieved — quotes unavailable. Excerpt: <paste excerpt here>]"]

25. acquisition_situation_read: Name the acquisition situation pattern.
    Choices: ALREADY_ANNOUNCED_DEAL | PRE_PROCESS_SETUP | SALE_PROCESS_ACTIVE |
    CREDIBLE_PROCESS_SIGNAL | CATALYST_ONLY | BOILERPLATE_FP | STALE_REPEAT

26. completed_deal_analogue_read: Which completed deal does this most resemble?
    Always reference MDVN, DMTX, or TSRO explicitly — even if to say "unlike all three because..."
    Then add the closest completed analogue from the analogues block if available.

27. probability_bucket_read: State the probability bucket. Example:
    "P1_DISCARD — base rate 3.5%, no public process signal, already-announced merger confirmed."

28. what_is_already_known_by_market: What is already public?
    List specific announcements, press releases, or proxy filings that are already public record.

29. what_is_not_yet_answered: 2-3 specific open questions for a diligence analyst.
    Example: "Is there a banker retained? Has the board formed a special committee? Are there competing bids?"

30. operator_decision: Restate research_action for unambiguous clarity.

31. immediate_next_steps: 2-4 specific 24-48 hour actions. Be concrete.
    DISCARD: "Archive. Flag pattern as [FP archetype]. Suppress unless [specific trigger]."
    WATCH: "Set EDGAR alert for [specific filing type] for [ticker]. Check again in [X] days."
    NEEDS_HUMAN_REVIEW: "Read source filing at [URL]. Answer: is this pre- or post-announcement language?"
    ESCALATE: "Read filing now. Check price action vs. [filing date]. Search news for [company] sale process."

32. next_sources_to_check: 2-4 specific sources.
    Examples: "EDGAR 8-K filings for [ticker]", "SEC full-text search '[company] strategic alternatives'",
    "CapIQ advisor retention for [company]", "Bloomberg/Reuters for [company] M&A rumor"

33. what_would_upgrade: The single specific evidence item that would trigger ESCALATE.
    Be concrete: "An 8-K confirming banker retention for strategic review" not "more evidence."

34. what_would_downgrade: What closes this case permanently.
    Example: "Deal closes and company delists." or "Company files 8-K denying any process."

35. why_this_is_not_actionable_yet: For WATCH/DISCARD/NEEDS_HUMAN_REVIEW only.
    Name the exact gap: "Source is post-announcement proxy background section — process already completed."
    Do not hedge. State the specific structural reason.

36. suggested_follow_up_queries: Provide 4-6 specific search queries the operator should run:
    "{company} strategic alternatives", "{company} acquisition proposal", "{company} sale process",
    "{ticker} 8-K strategic review", "{ticker} banker retention strategic", "{ticker} M&A rumor"
    Use the actual company name and ticker in each query.

ACTION-SPECIFIC REQUIREMENTS:

IF action=DISCARD:
  - exact_quotes_used: Quote the exact phrase that proves already-announced/false-positive
  - why_this_case_matters_now: Explain why the scanner triggered and why this is pattern noise
  - why_this_is_not_actionable_yet: Name the specific FP archetype and why it suppresses the signal
  - what_would_upgrade: What would unsuppress this (new URL, new date, new signal type)

IF action=WATCH:
  - what_is_not_yet_answered: Focus on the exact missing evidence for escalation
  - what_would_upgrade: The specific next filing or catalyst that would trigger ESCALATE
  - immediate_next_steps: Monitoring actions, EDGAR alerts, date-based review

IF action=ESCALATE:
  - source_evidence_read: Quote the explicit process language that justifies escalation
  - exact_quotes_used: The specific phrase(s) from the filing proving a real process
  - immediate_next_steps: "Read [URL] now. Check [ticker] price action. Search [company] sale process in news."
"""


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
    depth: str = 'fast_gate',
    catalyst_context: str = '',
) -> str:
    """
    Build a strategy-calibrated diligence prompt for the investment gate.

    Args:
        case:              Research case dict.
        strategy_features: Output of strategy_classifier.run_strategy_classification(case).
                           If None, prompt runs without deterministic pre-analysis.
        depth:             'fast_gate' (default) or 'diligence_memo' (richer analysis).
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
        # Process history + sequence intelligence
        'State transitions (last 3)': str(case.get('state_history_transitions', []) or 'None yet'),
        'Detected sequences':         str(case.get('detected_sequences', []) or 'None yet'),
        'Has compound sequence':      case.get('has_compound_sequence', False),
        # Banker mandate classification (deterministic pre-classifier)
        'Banker name':                 case.get('banker_name', '') or 'Not detected',
        'Banker tier':                 case.get('banker_tier', 'UNKNOWN'),
        'Banker mandate skew':         case.get('banker_skew', 'UNKNOWN'),
        'Banker mandate type':         case.get('banker_mandate_type', 'UNKNOWN'),
        'Banker mandate strength':     case.get('banker_mandate_strength', 'WEAK'),
        'Banker is exclusive':         case.get('banker_is_exclusive', False),
        'Banker mandate language':     case.get('banker_mandate_language', '') or 'None matched',
        'Banker mandate note':         case.get('banker_mandate_note', ''),
        # SA type classification (deterministic pre-classifier)
        'SA type (deterministic)':     case.get('sa_type', 'UNKNOWN'),
        'SA confidence':               case.get('sa_confidence', 'LOW'),
        'SA is company-level':         case.get('sa_is_company_level', True),
        'SA reasons':                  ', '.join(case.get('sa_reasons', []) or []) or 'None detected',
        'SA asset-level flags':        ', '.join(case.get('sa_asset_level_flags', []) or []) or 'None',
        'SA requires deeper read':     case.get('sa_requires_deeper_read', False),
        # Distress detection (30d price change before filing date)
        'Distress-driven SA':          case.get('distress_driven_sa', False),
        'Distress severity':           case.get('distress_severity', 'UNKNOWN'),
        'Price at filing':             _fmt_optional(case.get('price_at_filing')),
        'Price 30d before filing':     _fmt_optional(case.get('price_30d_before')),
        'Price change 30d pre-filing': f"{case.get('price_change_30d_pct', 'N/A')}%"
                                       if case.get('price_change_30d_pct') is not None else 'N/A',
        'Distress note':               case.get('distress_note', ''),
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
    diligence_instructions_block = _DILIGENCE_MEMO_INSTRUCTIONS if depth == 'diligence_memo' else ''

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

    # Full filing text (injected by run_gate when depth=diligence_memo)
    full_filing_text = case.get('_filing_text', '') or ''
    full_text_block = ''
    if full_filing_text and depth == 'diligence_memo':
        full_text_block = (
            'FULL FILING TEXT (fetched for diligence_memo analysis — use for exact quotes):\n'
            + full_filing_text[:6000]
            + ('\n[... text truncated at 6000 chars ...]' if len(full_filing_text) > 6000 else '')
        )
    elif depth == 'diligence_memo':
        full_text_block = (
            'FULL FILING TEXT: Not retrieved for this run. '
            'Use source_excerpt above and scanner memo only. '
            'exact_quotes_used must note: "[Filing text not retrieved]".'
        )

    # Catalyst context (earnings / PDUFA / Phase 3 readout)
    catalyst_block = catalyst_context.strip() if catalyst_context else ''

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

{full_text_block}

{catalyst_block}

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
{diligence_instructions_block}

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
