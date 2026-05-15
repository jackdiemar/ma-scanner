# Commercialization Roadmap — Strategic Process Intelligence Tool

Generated: 2026-05-14

This is an internal planning document. Do not treat it as a pitch deck or distribute it. Claims made here are subject to the limitations documented in the 50-case research artifact.

---

## 1. What the Product Actually Sells

**Not alpha signal.** Do not lead with alpha. The 50-case study shows a 6% true-signal rate in a retrospective batch. That rate is a lower bound on detectability, not a forward-looking precision metric. There is no live track record. No fund will pay for alpha you cannot demonstrate.

**Not M&A prediction.** The tool does not predict which companies will be acquired. 70% of the batch had no public prior signal. Even for the 6% that did, the signal is a process indicator, not a probability estimate.

**What it actually sells:**

**Biotech strategic-process state classification + workflow compression.**

Specifically:
- Real-time monitoring of public EDGAR 8-K, 10-Q, and SC 13D filings for acquisition-process language in a defined small-cap biotech universe
- Systematic false-positive suppression: distinguishing public process signals from private-background-only, generic rights language, and asset-specific rights
- Source-backed classification with filing links, phrase excerpts, and historical analogs
- Weekly curated report, not raw alert dumps

The pitch is: "We do the first-pass reading so your analyst doesn't have to. When something looks real, we tell you why and link you to the source."

---

## 2. Realistic Buyer Profile

Ranked by likelihood of paying.

### Tier 1 — Most Likely Buyers

**Small to mid-size biotech/healthcare event-driven funds ($100M–$5B AUM)**
- These funds actively trade biotech M&A and already have acquisition-process theses
- They need faster, more systematic monitoring of early-stage process signals
- They care about false-positive suppression because bad alerts waste analyst time and generate PnL friction
- They can evaluate source-backed evidence; they do not need oversimplified pitch materials
- Realistic price: $3k–$15k/month depending on universe coverage and alert latency
- Key objection: "We have Bloomberg terminals and analysts. Why do we need this?"
- Counter: "Bloomberg surfaces the deal announcement, not the 116-day-earlier unsolicited proposal. We read the 8-K before the story appears."

**Event-driven equity long/short funds with healthcare coverage**
- Broader mandate than pure biotech funds; need pre-synthesized sector signals
- Less likely to have built internal biotech-specific scanning infrastructure
- Realistic price: $2k–$8k/month

### Tier 2 — Secondary Targets

**Healthcare-focused family offices and smaller dedicated funds**
- May pay for a well-packaged subscription; less institutional diligence process
- Harder to find; lower dollar value per account

**Activist investors with biotech holdings**
- Need Item 4 13D parsing specifically (currently a gap in the scanner)
- Potentially high willingness to pay if the tool surfaces opportunities before they file
- Do not approach until Item 4 parsing is complete

### Tier 3 — Difficult or Premature

**Banks and advisory groups**
- Have internal research teams and compliance barriers
- Not realistic near-term buyers for an early-stage external tool

**Fundamental long-only healthcare funds**
- These funds may use the signal opportunistically but are not process-oriented; they care about fundamentals first
- Low near-term willingness to pay

**Independent research platforms (Mosaic, SentiSearch, etc.)**
- Possible data licensing partnership down the road
- Requires proven methodology and structured data output before approaching

---

## 3. What a Buyer Needs to Trust Before Paying

These are not marketing questions. These are diligence questions a sophisticated fund will actually ask.

### Minimum diligence bar

1. **Live alert track record.** Have you flagged any company before a deal announcement? When? What was the filing? What happened after? Without this, the historical 50-case study is illustrative but not commercially compelling. A single confirmed live catch changes the conversation.

2. **Source-backed historical cases with reproducible evidence.** MDVN and DMTX are solid. The source URLs and accession numbers are documented. The phrase excerpts are specific. A fund can independently verify these. This is the strongest existing asset.

3. **Documented false-positive rate and suppression logic.** The 50-case study shows 11 false positives out of 50 cases (22%). That is not inherently disqualifying, but a buyer needs to understand the classification criteria. The documented case packets and adjudication queue do this well.

4. **Coverage universe and consistency.** How many companies are monitored? How often? What is the smallest market cap? What is excluded? A fund cannot trust a tool that monitors 50 names inconsistently.

5. **Alert latency.** How many hours after an 8-K files does the alert arrive? EDGAR filings are public within minutes of filing. If the tool takes 24+ hours, it is not monitoring — it is summarizing.

6. **Audit trail.** For every alert: which filing triggered it, what phrase appeared, what the surrounding context looked like, when the alert was generated relative to the filing date.

7. **Explanation of what competitors provide that this does not.** Bloomberg, Refinitiv, Calcbench, and Visible Alpha all have SEC filing coverage. What does this tool do that they do not? The answer is: systematic false-positive classification, context-aware phrase detection (not just keyword counting), and historical analog matching. That needs to be articulated clearly.

---

## 4. What Cannot Be Claimed Yet

These are hard constraints. Overstating will lose credibility.

- **Cannot claim alpha.** No live PnL track record. No position data. The 50-case study is historical validation, not a forward-return study.
- **Cannot claim 6% signal rate is meaningful.** It is an empirical observation from a specific batch and time period. It has not been validated across different years, deal sizes, or market conditions.
- **Cannot claim complete or consistent coverage.** Many baseline cases in the batch have zero filings searched. The live scanner monitors ~50 names and was not running during MDVN or DMTX.
- **Cannot claim calibration-ready data.** The dataset is explicitly not marked VERIFIED or CALIBRATION_ELIGIBLE.
- **Cannot claim "strategic alternatives" alone predicts a deal.** The scanner score uses ~85-90% deal rate as a rough estimate; this figure is from prior research and not validated in this dataset.
- **Cannot claim the tool caught MDVN or DMTX in real time.** It was not running. The study is retrospective verification that the filing evidence existed and was classifiable. That is valuable — but be precise about what that means.

---

## 5. Minimum Sellable Product

Before approaching any paying customer, the tool needs to have and demonstrate all of the following:

1. **Defined monitored universe** — at least 50 names, clearly specified (sector, size, criteria)
2. **Daily 8-K monitoring** — every 8-K filed by universe names checked within 24 hours of filing
3. **Signal classification output** — per-alert: PROCESS/AFFIRM/ROFR/MERGER/BOILERPLATE, with phrase excerpt and source URL
4. **Historical analog** — for each PROCESS or AFFIRM alert, can you pull the closest historical case? e.g., "This looks like DMTX 2017-08-25 — Dimension Therapeutics unsolicited proposal"
5. **Weekly report** — structured summary of new signals, updated status of live process cases, changes in classification
6. **False-positive suppression** — explicit documentation of what is NOT a signal and why
7. **Alert latency measurement** — internal metric showing average hours from EDGAR filing to alert

---

## 6. Milestones Before Approaching Funds

These are ordered by dependency and importance. Do not skip ahead.

### Phase 1 — Technical Baseline (Weeks 1–4)

**M1: Add unsolicited/superior proposal phrases to scanner.**
Add "unsolicited proposal," "superior proposal," "proposal to acquire," "acquisition proposal" to `_8K_SIGNAL_PHRASES` in V12 at score 30/28/25/25. This is 4 lines of code. Low risk. Run on existing universe for 1 week; verify no regressions.

**M2: Expand n_filings from 4 to 10.**
Reduces risk of missing a filing when multiple 8-Ks are filed in close succession. 1 line of code.

**M3: Build alert latency logging.**
For each alert generated, log the time between EDGAR filing date/time and alert generation time. This is the first latency measurement you will be asked about.

**M4: Fix PTLA announcement date.**
Resolve the one DATE_MISSING case. Does not affect live scanner but closes the only hole in the historical dataset.

### Phase 2 — Live Proof (Weeks 4–8)

**M5: Run 4 weeks of documented live monitoring.**
Every alert generated: save the filing, phrase, date, score, classification, and context. Build a simple log. Even if nothing major surfaces, this proves the system runs and documents what it detects.

**M6: Assess whether any past live alert was a genuine pre-announcement signal.**
Go back through whatever historical live scanner output exists. Did the scanner flag any company in the prior 6–12 months that was subsequently acquired? If yes: that is your first live case study.

**M7: Decide on news integration.**
TSRO (17 days before) was a media report, not EDGAR. A Bloomberg or CNBC/Reuters scraper that feeds pre-announcement sale-process headlines into the classifier would close this gap. This is a meaningful product decision: EDGAR-only is cleaner and more defensible; news integration is broader but messier. Make the decision explicitly rather than by default.

### Phase 3 — Research Depth (Weeks 6–12)

**M8: Expand to 75–100 cases with consistent methodology.**
Use the existing batch runner infrastructure. Keep the same adjudication standards. Do not rush to a round number; 75 good cases is better than 100 sloppy ones.

**M9: Run one complete false-positive audit on live output.**
Take every PROCESS or AFFIRM alert from the live monitoring period and adjudicate it manually. What fraction were genuine? What fraction were noise? This is your live false-positive rate — more commercially important than the retrospective rate.

**M10: Build Item 4 13D parsing.**
This is documented in `CURRENT_PRIORITY.md` as highest ROI next task. Without it, activist-driven processes (one of the most actionable signal types for event-driven funds) are poorly classified.

### Phase 4 — Commercial Prep (Weeks 10–16)

**M11: Write a 2-page methodology brief.**
Not a pitch deck. A document that answers: what does the scanner look for, how does it classify, what are the exclusion criteria, how is false-positive suppression implemented. This is what a fund compliance officer or analyst will want to read.

**M12: Build a coverage universe statement.**
Which names are monitored? Why? What market cap range? What happens when a company enters or exits the range?

**M13: First soft pitch (not revenue-seeking).**
Approach 2–3 biotech event-driven fund analysts you trust. Present the methodology, show 2–3 live case examples, share the 50-case study. Ask for feedback, not for money. The goal is to find out what would make this credible to a buyer.

---

## 7. Pricing Model Options

None of these are commitments. This is a decision to be made after getting market feedback.

| Model | Structure | Realistic range | Pros | Cons |
|---|---|---|---|---|
| Research subscription | Monthly flat fee, universe shared | $2k–$8k/month | Scalable, recurring | Buyers expect competitive product, not early-stage |
| Bespoke alerting | Per-fund universe, dedicated alerts | $5k–$20k/month | Higher ACV, more engagement | Does not scale; service-heavy |
| Consulting engagement | Project-based analysis | $5k–$25k one-time | Low bar to entry | Not recurring; does not build a product |
| Data licensing | CSV/API output | $1k–$5k/month | Product-forward | Requires clean, structured output and track record |
| Internal tool / no sale | Use only for BSC research | $0 external revenue | No sales overhead | No external validation |

The most realistic near-term path, assuming M1–M9 are complete:
- Start with 2–3 consulting engagements or pilot subscriptions at $2k–$3k/month
- Use those to validate the product commercially before building a sales infrastructure
- Do not price around what you think it is worth; price around what a fund will pay for workflow compression without a live alpha track record

---

## 8. Most Credible Near-Term Pitch (3–6 Month Horizon)

If milestones 1–9 are complete:

> "We built a systematic biotech acquisition-process intelligence monitor. The core problem it solves: 70% of public biotech acquisitions show no pre-announcement signal. But 6% show explicit public acquisition-process language in SEC filings — unsolicited proposals, superior proposals, competing bids — and those signals appeared on average 72 days before deal announcement in our 50-case historical study. The challenge is that a similar-looking filing — ROFR language, private-only background in later proxies, asset-specific rights — is noise, not signal. We built the false-positive classification framework to make that distinction systematic."

> "The tool has been running live since [date]. We flagged [N] AFFIRM/PROCESS signals in the past [N] weeks. Here are the filing links and excerpts. We have documented 50 historical cases with source-backed adjudications you can independently verify."

This pitch is credible. It is honest about what is known (base rates, classification framework, source evidence) and does not overstate (no alpha claim, no deal probability, no predictive-power claim).

---

## 9. What Would Make the Pitch Unserious

Do not do these things:

- **Show the 6% true-signal rate as a headline.** Without context, "6% true-signal rate" reads as "fails 94% of the time." Lead with the classification framework and false-positive suppression, not the rate.
- **Claim MDVN and DMTX were caught in real time.** They were not. The retrospective study confirmed the evidence existed; the scanner was not running.
- **Show a raw score list without source links.** Funds will not trust scores they cannot trace. Every claim needs a filing link and an excerpt.
- **Claim "our tool predicts acquisitions."** No. It detects public process signals. The company still has to be in a real process.
- **Pitch to a large fund (>$5B AUM) before milestones 8–13 are complete.** They will ask questions the tool cannot yet answer. One bad meeting with a sophisticated fund poisons the reference pool.
- **Confuse "worth a lot" with "near term revenue."** This may become a high-value asset. But near term, the market will price it as an early-stage research tool until there is a live track record.
- **Price it above what a pilot customer would test.** First customers are buying access and giving feedback. They are not buying a finished product.

---

## 10. What to Build Next (3–6 Month Priority Order)

If the goal is to have a commercially credible pilot by month 6:

| Priority | Task | Effort | Dependency |
|---|---|---|---|
| 1 | Add unsolicited/superior proposal phrases to V12 | 1 hour | None |
| 2 | Expand n_filings from 4 to 10 | 15 min | None |
| 3 | Build alert latency logging | 1–2 days | None |
| 4 | Fix PTLA date | 1–2 hours | EDGAR lookup |
| 5 | Run 4 weeks documented live monitoring | Ongoing | #1–3 complete |
| 6 | Audit historical live output for any prior live catch | 1 day | Prior scan logs exist |
| 7 | Complete Item 4 13D parsing | 2–5 days | V12 existing 13D parsing |
| 8 | Expand to 75–100 historical cases | 2–3 weeks | Batch runner |
| 9 | Run live false-positive audit on 4-week output | 1–2 days | #5 complete |
| 10 | Write 2-page methodology brief | 1 day | #8 complete |
| 11 | Build coverage universe statement | 1 day | #5 complete |
| 12 | First 2–3 soft pitches for fund feedback | 1–2 meetings | #10–11 complete |
| 13 | Price and structure pilot subscription | After feedback | #12 complete |

The single most important task is #5: documented live monitoring. Everything else can be retroactively improved. The live track record cannot be manufactured after the fact.

---

## Appendix: Key Constraints

- Do not mark any historical case VERIFIED or CALIBRATION_ELIGIBLE before documented methodology review.
- Do not scale historical study to 100 cases until current 50-case standards are fully preserved.
- Do not run a full live scanner during working hours without confirming FMP API key and output paths are set.
- Deploy repo is Cloudflare Pages (not Netlify). Do not change dashboard infrastructure for commercialization work.
- All commercial claims must be traceable to source-backed case evidence. No invented statistics.
