# Completed Acquisition Learning Engine

## Overview

The completed acquisition learning engine adds a curated library of historical acquisitions to the MA Scanner AI layer. It provides:

1. A structured case library of completed biotech acquisitions with verified signal data
2. A deterministic situation classifier that scores live alerts across 16 acquisition situation types
3. A probability engine that produces a research priority score (0-100) and bucket (P0-P5)
4. A retrieval system that finds the most relevant historical analogues for each live alert
5. An external research abstraction that enables future news/media integration

---

## Why Completed Acquisitions Matter

Most scanner alerts are false positives, boilerplate, or already-announced deals. The edge we are looking for is rare: approximately 3.5-6% of alerts have true public prior process signals — situations where acquisition-relevant evidence was publicly visible before the deal was announced.

By comparing every live alert against verified completed cases, the system can:

- Identify which situation type this most resembles (unsolicited proposal, strategic review, catalyst setup, etc.)
- Determine whether it resembles MDVN (public unsolicited proposal), DMTX (superior proposal), TSRO (media-reported sale process), or none
- Quantify what key traits are present or missing compared to cases that did have catchable signals
- Give the operator a prioritized research bucket so time is allocated to the best signals first

---

## True Process Signal vs. Setup Signal

These are different things and must not be confused.

**True process signal**: Explicit, company-level evidence in a public document (SEC filing, press release, credible media) that an acquisition process is underway or has been initiated. Examples:

- Unsolicited acquisition proposal publicly disclosed in 8-K (MDVN)
- Superior proposal determination disclosed before definitive agreement (DMTX)
- Credible media report naming specific potential acquirers (TSRO)
- 8-K disclosing strategic alternatives review + named financial advisor retention
- Activist 13D Item 4 demanding sale of company

**Setup signal**: Context suggesting the company is an attractive acquisition target, but no explicit process evidence. Examples:

- Strong Phase 3 or regulatory catalyst upcoming
- Commercial-stage company with approved asset in high-demand space
- Going concern / cash runway pressure (distressed potential)
- Asset-specific ROFR or licensing rights in a collaboration agreement

Setup signals are worth monitoring but do not warrant escalation without corroborating process evidence. A company with a Phase 3 readout next quarter is not necessarily in a sale process — it is a setup signal.

The probability engine explicitly separates these: setup signals score P3_WATCHLIST_SETUP while explicit process signals score P4 or P5.

---

## Probability Buckets (P0-P5)

The engine assigns every live alert to one of six research priority buckets.

| Bucket | Label | Meaning |
|--------|-------|---------|
| P0 | No Action — False Positive | Scanner triggered on boilerplate, compensation plan, or routine filing. Discard. |
| P1 | Discard — Already Announced | Definitive merger agreement or tender offer language present. Deal is public. Pre-announcement edge does not exist. Discard. |
| P2 | Monitor Only | Weak or ambiguous signal. No explicit process evidence. Continue monitoring for follow-on filings. |
| P3 | Watchlist Setup Signal | Setup signals only (catalyst, distress, ROFR, activist without acquisition demand). No explicit process language. Watch for process-specific follow-on. |
| P4 | Research Priority | Moderate process signal or multiple credible setup signals. Deserves deeper research. Fetch full filing text and check for corroboration. |
| P5 | High Priority Process Signal | Explicit process evidence: strategic alternatives 8-K, unsolicited proposal, superior proposal, or credible media sale process report. Escalate immediately. |

---

## How This Is NOT Deal Probability

The research priority score (0-100) is not a prediction of deal completion and is not investment advice.

It is a triage instrument. A score of 60 does not mean there is a 60% chance the company gets acquired. It means this alert scores in the top priority tier and warrants immediate deeper research — not that a deal is likely.

Base rate: approximately 3.5-6% of EDGAR scanner alerts have true public prior process signals that were catchable before announcement. The system starts from this skeptical base rate and adjusts only when evidence explicitly supports it.

---

## How Completed Deal Analogues Work

For every live alert, the engine:

1. Loads all completed acquisition cases from `data/training_cases/completed_acquisitions_seed.json`
2. Scores each case's relevance to the live alert on multiple dimensions: signal type match, source phrase overlap, therapeutic area, filing type, catchability type, and situation type
3. Returns the top N most relevant cases sorted by relevance score
4. Includes key lessons, operator guidance, and signal catchability information for each analogue

The three canonical true-signal cases (MDVN, DMTX, TSRO) are in the library as VERIFIED entries. Every alert is compared against them explicitly. If the live alert lacks the traits that made those cases catchable — named acquirer in 8-K, superior proposal in 8-K, credible media report — the system explains why.

---

## External Research Integration

The TSRO case (Tesaro, 2018) is a structural limitation of EDGAR-only scanning. The media report of GSK's sale process appeared in Bloomberg/Reuters on November 16, 2018 — 17 days before the definitive agreement. This signal was **not catchable via SEC EDGAR**. An EDGAR-only scanner produces zero signal for TSRO-type cases.

The `external_source_provider.py` module abstracts this:

- Default: disabled. Runs safely in EDGAR-only mode.
- To enable: set `EXTERNAL_RESEARCH_ENABLED=true` and `NEWS_SEARCH_PROVIDER=serpapi` (or `google_custom` or `brave`) with the corresponding API key.
- When enabled: the engine queries news for each alert and includes results in the probability assessment.

To enable SerpAPI:
```bash
export EXTERNAL_RESEARCH_ENABLED=true
export NEWS_SEARCH_PROVIDER=serpapi
export SERPAPI_API_KEY=your_key_here
```

---

## How to Add More Completed Cases

Add entries to `data/training_cases/completed_acquisitions_seed.json`.

Each case should include:
- `case_id`, `ticker`, `company_name` (required)
- `public_signal_category` — was there a true public prior signal? (required)
- `acquisition_situation_type` — what type of situation was it? (required)
- `public_catchability` — HIGH/MEDIUM/LOW/NONE (required)
- `verification_status` — VERIFIED, NEEDS_VERIFICATION, or TEMPLATE (required)
- `pre_announcement_public_evidence` — list of specific public signals found before announcement
- `true_signal_lessons` — what this case teaches about true signals
- `operator_lesson` — one actionable lesson for the operator

**Important**: Do not hallucinate acquisition facts. If you are not certain of deal details, use `verification_status: NEEDS_VERIFICATION` and leave `acquirer`, `announcement_date`, and `deal_value` as null. Template entries without verified facts are still useful for setup trait documentation.

---

## Model Training / Fine-Tuning

The case library is designed to support eventual fine-tuning:

- Each case has a `model_training_summary` field that captures the most important training information in condensed form
- The `tags` field allows filtering by case type for training set construction
- VERIFIED cases are training-ready; TEMPLATE cases can be used for context but should not be labeled as ground truth
- The `visible_setup_traits` and `invisible_setup_traits` fields capture what was and was not publicly knowable at the time — critical for distinguishing "could we have caught this?" from "could anyone have predicted this?"

---

## Diagnostics

Check library status:
```bash
python3 src/ai_research/run_ai_research.py --completed-acquisition-status
```

Compare a specific ticker to completed deals:
```bash
python3 src/ai_research/run_ai_research.py --compare-completed-deals APLS
```

Run probability audit on latest cases (no LLM):
```bash
python3 src/ai_research/run_ai_research.py --latest --limit 5 --probability-audit
```

Run smoke tests:
```bash
python3 src/ai_research/test_acquisition_learning_smoke.py
```

---

*This document covers internal research tooling only. Nothing here constitutes investment advice or a recommendation to trade any security.*
