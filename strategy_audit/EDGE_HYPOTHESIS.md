# Edge Hypothesis — Strategic Process Intelligence
**Date:** 2026-05-07
**Status:** Working document. Intellectually honest draft. Not a pitch.

---

## What This System Is Not

Before defining the edge, define what this system cannot be:

- Not an M&A prediction engine. P(deal) for score-only names is 3-10%. That is background noise.
- Not a quantitative model. It is a document-parsing and signal-routing workflow with a scoring heuristic attached.
- Not differentiated by the score itself. Any competent analyst can build a "biotech M&A attractiveness" matrix from pipeline quality, valuation discount, and therapeutic hotspot data. That is commoditized.
- Not useful for large-cap names. BMRN ($10.5B mcap), NBIX ($14.8B), LGND ($4.6B), APLS ($5.3B) — these are well-covered, actively modeled by dozens of sell-side desks, and their M&A probability is already partially priced. The system surfacing them as HIGH_CONVICTION is noise, not signal.

The system cannot predict M&A. The system might be able to detect when a deal process is structurally more likely than current price reflects — specifically in small, underfollowed situations where the market has not yet caught up to public filings.

---

## The Actual Edge Hypothesis

**Edge:** Detecting real-process evidence (SEC filings, regulatory disclosures, structural deal rights) in underfollowed small-cap biotech names faster and more systematically than the market prices that evidence.

This is narrow. It is not broad M&A prediction. It is process-state monitoring.

### Why This Might Work

**1. Small-cap filing detection lag**

A 13D filed on a $350M biotech with a known biotech activist demanding a sale is a real signal. On a $5B name, that 13D is covered by every biotech desk within hours. On a $350M name with no sell-side coverage, the 13D may sit in SEC EDGAR for 24-48 hours with no market reaction. That is the detection gap this system can exploit.

The edge is not the filing itself. The edge is automated, systematic parsing of filings across a 500+ name universe — work no human analyst does as a daily routine.

**2. Process-state is not reflected in price until there is news**

When a board files an 8-K affirming a strategic alternatives review (sa_is_affirm=True), they have almost certainly already retained a banker, contacted initial parties, and begun a formal process. The stock often moves on the announcement, but:

- In small-cap names, the announcement may be missed for days
- The probability implied by the move is often still below actual deal frequency for sa_affirm situations (~42% at 12 months based on current calibration)
- The sequencing of what happens next — banker retained, NDAs, management meetings, bid rounds — is not priced in at announcement; only the announcement itself is

**3. Sequencing intelligence is underappreciated**

The market prices the 8-K announcement. It does not price the downstream sequence. If:
- A company files an sa_affirm 8-K (board reviewing strategic alternatives)
- 30 days later files a 13D from a known activist
- 60 days later discloses a ROFR/ROFN clause in a partnership filing

Each event individually is partially known. The sequence as a whole — board + activist + structural deal right — compounds to a meaningfully higher P(deal) that may still not be reflected in price, especially in small-cap illiquid names where institutional ownership is thin.

**4. Institutional constraints create a structural gap**

Institutional funds with real capital cannot hold $200M-$600M mcap biotech M&A situations for several reasons:
- Position limits: a 2% position in a $500M mcap = $10M; meaningful only in sub-$1B AUM funds
- Liquidity constraints: institutional funds need to be able to exit; $300M mcap names may not clear their liquidity screens
- Mandate constraints: many funds exclude pre-commercial names or names below certain market caps entirely
- Research coverage: most institutional research desks do not cover sub-$500M biotech

This means the sweet spot — $200M-$1B mcap names with real process evidence — is systematically underinstitutionalized. Price discovery is slower. Signals persist longer before being priced.

**5. Document parsing is operational, not analytical, work**

Reading 500+ biotech 13D filings, parsing 8-K text for strategic alternatives language, distinguishing AFFIRM from BOILERPLATE, and cross-referencing ROFR/ROFN clauses with named pharma counterparties is tedious operational work. It is not high-status analyst work. Most analysts do not do it systematically. An automated pipeline that does this daily and surfaces the genuine signals has a real workflow advantage, not necessarily an information advantage.

---

## Where the Current System Fails

**1. Fake precision from the score**

The dashboard says "Score: A 0-100 point score estimating acquisition likelihood." This is wrong and misleading. The score estimates M&A attractiveness, not acquisition likelihood. NBIX scores 97.6 and is a $14.8B company. It is not 97.6% likely to be acquired. That framing destroys credibility with any sophisticated reader.

**2. SCORE_ONLY names dominate HIGH_CONVICTION**

Current scan: 14 HIGH_CONVICTION names. Most are score-only or near-score-only, driven by pipeline quality, revenue, and therapeutic hotspot — not process evidence. These names are the exact thing the PM audit identified as not tradeable. Yet the dashboard presents them as the top opportunities.

**3. The HIGH_CONVICTION label for large-cap names**

BMRN ($10.5B), NBIX ($14.8B), LGND ($4.6B): these are well-covered, liquid, widely modeled names. For these names to be acquisition targets, a buyer needs to write a $15-20B check. That happens, but it is not a repeatable underfollowed edge.

**4. 0 BUY decisions in current scan**

The trade_logic.py correctly gates out everything below its thresholds. But this means the system presents a dashboard of "High Conviction" and "Medium Conviction" picks with 0 actionable trade recommendations. That is incoherent. Either the conviction labels need to be recalibrated downward to reflect reality, or the dashboard framing needs to change.

**5. BOILERPLATE not clearly separated from AFFIRM**

The distinction between sa_is_affirm=True (board formally reviewing options) and boilerplate risk-factor language mentioning "strategic alternatives" is the single most important classification in the system. This distinction exists in trade_logic.py but is not visually prominent in the dashboard. A BOILERPLATE flag should be treated as negative signal — it means the scanner found the phrase but the board did not affirm it. It should not appear near the top.

**6. 13D parsing lacks Item 4 analysis**

Any 13D is treated as activist pressure. A 13D filed by a passive strategic holder for ownership restructuring purposes is not an activist signal. A 13D with explicit "sale of the company," "maximize shareholder value," or "business combination" language in Item 4 is a real signal. The current system cannot distinguish these. This is the biggest false-positive risk in Layer 7.

**7. ROFR/ROFN without scope context**

A ROFR on one drug in one territory is structurally different from a company-level acquisition right. Both currently score the same. A product-level ROFR from Pfizer on a single program is meaningful but does not imply whole-company acquisition likelihood. Presenting it as equivalent to a company-level ROFR overstates the signal.

**8. Staleness creates recycled stale picks**

Names that appeared 150 days ago with a now-cold process signal still show on the watchlist with staleness penalties but no clear "this signal is dead" flag. The staleness penalty reduces the score, but a 75-point stale name with a dead 13D from 140 days ago is not a watchlist candidate. It is noise.

---

## What Is Likely Already Priced In

- Any M&A speculation on names with >$2B market cap that has been covered by sell-side research
- Strategic fit logic for names in active M&A hotspots (ADC, obesity, autoimmune) — this is consensus
- Pipeline quality scoring — every biotech analyst models pipeline NPV
- Phase 3 + right mechanism + right size = likely acquisition candidate: widely discussed, not proprietary
- Signed merger agreements: already announced, already priced; scanner should simply track these as resolved
- Any name that appeared in a biotech M&A screener in the last 6 months across Bloomberg, Evaluate, or similar

---

## What May NOT Be Priced In

- Fresh sa_is_affirm 8-K on a $300-600M underfollowed name with no sell-side coverage in the first 24-72 hours
- A 13D with explicit Item 4 sale-pressure language on a $200-500M name from a known biotech activist in the first 24-48 hours
- The signal sequence compounding: sa_affirm + activist 13D + ROFR clause on the same name within a 60-day window
- A ROFR/ROFN clause with a named major pharma counterparty in a recent 8-K that the market has not connected to whole-company acquisition probability
- Staleness reset: a name that went cold 120 days ago and just filed a new 8-K with fresh process language — the market may still be treating it as a stale idea

---

## What the System Should Explicitly Avoid

- **Score-only names in the top tier.** If no real process evidence exists, the name does not belong in HIGH_CONVICTION. It belongs in WATCH at best, with a clear label that the thesis is speculative.
- **Large-cap names as primary signal.** $3B+ market cap names can be tracked as background context, but they should not be the primary surface area.
- **Treating all hotspot exposure as a buy signal.** Being in autoimmune is not a process signal. It is sector exposure.
- **Recycling stale signals without decay.** A process signal older than 180 days with no new filings should be retired, not discounted.
- **Broad acquisition likelihood language.** The system does not know if a company will be acquired. It knows if there is documentable process evidence that a sale process may be underway.
- **Framing the score as a probability.** The score is a composite attractiveness index. It is not P(acquisition).

---

## What Would Make This Genuinely Differentiated

Be specific. These are the capabilities that sophisticated users would respect:

**1. Real-time (daily) process-state classification for 500+ names**

Not "attractiveness score" — a clean status taxonomy:
- `PROCESS_LIVE` — active confirmed process (sa_affirm, signed merger agreement in progress, or fresh activist 13D with Item 4 sale language, ≤45 days)
- `PROCESS_PATHWAY` — specific acquisition pathway (ROFR/ROFN clause with named counterparty, ≤90 days)
- `PROCESS_AGING` — previously live process signal now 46-180 days old
- `PROCESS_DEAD` — signal older than 180 days with no refresh; retire from active monitoring
- `WATCH_NO_PROCESS` — high attractiveness score but no process evidence; speculative only
- `IGNORE` — below attractiveness threshold or disqualifying fundamentals

This taxonomy is directly actionable. It does not pretend to predict deals. It tracks process state.

**2. Item 4 language extraction from 13Ds**

Distinguish governance 13Ds from sale-pressure 13Ds. Extract key language: "maximize shareholder value," "sale of the company," "business combination," "board representation," "formal process." Score the 13D by intent, not just existence.

**3. Sequence detection and compound signal scoring**

Flag when multiple process signals appear within a rolling 60-day window on the same name. sa_affirm + activist = meaningfully stronger than either alone. This sequencing intelligence is not available from a static filing lookup.

**4. Small-cap universe filter as a feature, not a bug**

Explicitly restrict the actionable watchlist to $150M-$1.5B market cap. Above $1.5B, note the name for context but mark it as "institutional coverage reduces edge." Below $150M, bankruptcy risk dominates.

**5. Process evidence excerpts in the output**

For every name with a real process signal, surface the exact filing text that triggered the flag (200-300 character excerpt), the filing date, and the filing URL. This makes the signal verifiable in seconds, which is the difference between a research tool and a dashboard.

**6. Honest P(deal) presentation**

Replace "Score estimates acquisition likelihood" with:
- P(deal within 12 months) based on signal quality tier
- Stated confidence interval ("This estimate is based on historical frequencies for similar signal types, not this company specifically")
- Clear labeling that score-only names have 3-10% P(deal) — which is near background rate

**7. False-positive suppression on ROFR/ROFN**

Only flag ROFR/ROFN as process evidence when the clause appears in a local window with a named major pharma and the clause language suggests company-level application, not just asset/program scope.

**8. Workflow compression for the user**

The value is not a dashboard with 148 names rated WATCH. The value is a daily brief: "2 names entered PROCESS_LIVE status today. 1 name moved from PROCESS_PATHWAY to PROCESS_LIVE. 3 names moved to PROCESS_DEAD." Under 200 words. Actionable in under 2 minutes. This is what a hedge fund analyst actually wants.

---

## Most Believable Moat

If this system becomes genuinely useful, the moat is:

**Operational infrastructure + calibration history.**

The filing-parsing pipeline, staleness tracking, process-state classification, and outcome tracking table are not hard to build once, but they require continuous maintenance: phrase expansion, false-positive correction, calibration updates when deals close. A competitor could replicate the architecture in weeks. They cannot replicate 18 months of outcomes data, calibrated P(deal) tables based on actual deal frequencies, and a tuned false-positive suppression layer.

The moat is not the idea. The moat is the running system with real historical validation.

---

## What Sophisticated Funds Would Respect

- A conservative, calibrated P(deal) table based on actual outcomes (not assumed)
- Explicit false-positive classification: how many AFFIRM signals resulted in a deal vs. no deal
- Clear scope: "we monitor $150M-$1.5B small-cap biotech for process-state signals; we do not claim to predict large-cap M&A"
- The process-state taxonomy (LIVE / PATHWAY / AGING / DEAD) over a vague conviction tier
- Filing excerpts as verification, not just flags
- Honest acknowledgment that the edge is detection speed and operational coverage, not analytical superiority

**What would destroy credibility:**
- A $14B market cap company listed as "HIGH_CONVICTION" acquisition target
- The phrase "our proprietary AI" in connection with a phrase-matching regex parser
- A score labeled "acquisition likelihood" for a name with no process evidence

---

## Recommended Priorities

### Remove or Deprioritize
- Score-only names from the primary dashboard view — they are not actionable
- Large-cap names ($2B+) from the active watchlist — route to a separate "coverage context" section
- "Acquisition likelihood" language everywhere in the dashboard
- The current About section framing ("surface acquisition targets... proprietary frameworks")
- Signed merger agreement names as "opportunities" — these are resolved situations, track separately

### Keep and Strengthen
- Layer 7 real-process-evidence detection — this is the actual system
- sa_is_affirm vs. BOILERPLATE distinction — sharp and correct
- Signal freshness / staleness tracking — directionally right, needs harder decay
- P(deal) table in trade_logic.py — conservative and honest; needs calibration from outcomes
- Process evidence cap at 80 — correct gate; consider lowering to 75

### Make Primary Focus
- Process-state classification (LIVE / PATHWAY / AGING / DEAD) as the top-level output
- Daily delta brief: what changed in process state today
- Small-cap focused actionable list: only names in $150M-$1.5B range with real process evidence
- Item 4 parsing for 13Ds
- Filing excerpt surfacing in the dashboard

### Highest ROI Next Step

**Build the process-state taxonomy into the scan output and dashboard.**

This is a naming and logic change, not a new feature. Rename conviction tiers to process states for names with real evidence. Remove or clearly demote SCORE_ONLY names from the primary table. Add a "process delta" section showing what changed since the last scan.

This one change makes the system intellectually honest and immediately more useful, without touching the backend scoring engine.

---

*This document describes hypotheses, not confirmed edges. All P(deal) estimates are based on assumed historical frequencies and require calibration against actual outcomes before use in sizing decisions.*
