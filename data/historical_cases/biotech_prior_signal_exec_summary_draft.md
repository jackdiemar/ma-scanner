# Biotech Acquisition Prior-Signal Study — Executive Summary

## Working Title

Public Prior Signals in Biotech Acquisitions: A 50-Case Historical Review

## One-Paragraph Thesis

This study evaluates whether public filings and public reports contained observable acquisition-process signals before announced biotech acquisitions. The pattern from 50 cases is not that most acquisitions are predictable. A small subset (3 of 50) had public, source-backed process evidence before announcement. The majority had no confirmed public prior signal. A significant minority (8 of 50) had process-like facts visible only in post-announcement deal background, not available to the market beforehand. The study also identified two distinct false-positive families: generic or asset-specific rights language that should not be counted as company-level sale-process evidence. All six POSSIBLE_SIGNAL_NEEDS_REVIEW cases have been adjudicated; none added to the true-signal count.

## Final Status Distribution

| Status | Count | Notes |
|---|---:|---|
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 35 | No confirmed public prior signal. |
| PRIVATE_BACKGROUND_ONLY | 8 | Process facts appear in deal background but were not public before announcement. |
| TRUE_PUBLIC_PRIOR_SIGNAL | 3 | MDVN, DMTX, TSRO. |
| ASSET_SPECIFIC_RIGHTS_ONLY | 2 | ARRY, XLRN. Rights limited to assets or programs, not company-level sale pathway. |
| RIGHTS_LANGUAGE_ONLY | 1 | CPXX. Generic rights language not treated as process evidence. |
| DATE_MISSING | 1 | PTLA. Announcement date not confirmed; excluded from adjudication. |

## True-Signal Examples

**MDVN — public unsolicited proposal.** Medivation had public pre-announcement acquisition pressure from Sanofi disclosed in SEC filings (8-K, 10-Q, DEF 14A) beginning April 28, 2016, 116 days before Pfizer's announced deal. This is the cleanest example of an ongoing public proposal/process signal detectable in EDGAR filings before announcement.

**DMTX — superior proposal and competing-bid process.** Dimension Therapeutics had public pre-announcement proposal activity disclosed in SEC filings beginning August 25, 2017, 39 days before the final acquisition announcement. Superior-proposal and competing-bid language appeared across DEF 14A and 8-K filings.

**TSRO — public sale-process media report.** TESARO had a public pre-announcement sale-process report on November 16, 2018, 17 days before the GSK deal announcement. This signal is categorized separately from SEC-filed signals because it originated in a media report. Source availability and publication date require independent verification.

## False-Positive and Non-Signal Examples

**CPXX — generic rights language.** Right-of-first-refusal language appeared in CPXX filings 69 days before the acquisition announcement. Adjudicated as RIGHTS_LANGUAGE_ONLY because the language was a generic legal representation, not whole-company process evidence.

**ARRY and XLRN — asset-specific rights.** Both had rights-related language in SEC filings before their acquisition announcements. Both adjudicated as ASSET_SPECIFIC_RIGHTS_ONLY: the rights were limited to specific assets, programs, or therapeutic areas, not a company-level sale pathway. XLRN's BMS right of first negotiation covered sotatercept pulmonary hypertension only; the actual acquirer was Merck.

**FTSV, PRNB, TRIL — private background only.** All three had process-like facts that appear in post-announcement deal background but were not publicly disclosed before announcement. Gilead-FTSV discussions were private under mutual confidentiality since summer 2018. Sanofi's private asset proposal to Principia was never publicly announced. Pfizer's $25M registered direct equity investment in Trillium was a financial investment with no ROFR or acquisition option.

**MYOK, ADMS — no public prior signal.** Supernus's private unsolicited offers to Adamas in October and November 2020 were declined privately with no public SA announcement before the October 2021 deal. No pre-announcement public process disclosure was found for MyoKardia.

## Key Distinction

The core distinction is **public prior signal** versus **private background** versus **rights-language noise**.

- Public prior signals are observable before the announcement in source-backed public filings or reports. They can plausibly support process intelligence.
- Private background facts may explain how a deal developed, but they were not available to the market beforehand. They appear only after the fact in proxy or SC 14D-9 background sections.
- Rights-language noise may be real contract language, but generic or asset-specific ROFR/ROFN language does not imply an active company-level sale process.

## What the Scanner Can Catch

- Public unsolicited acquisition proposals disclosed in SEC filings before final announcement.
- Superior-proposal or competing-bid language filed before the final announcement, confirmed by source date.
- Public sale-process reports when source and publication date are verified.
- Repeated or escalating public process language across multiple filings.
- Clear pre-announcement 8-K language referencing acquisition proposals, strategic alternatives, or public bidder pressure.

## What It Cannot Catch

- Private outreach, negotiations, or board discussions only disclosed later in transaction-background sections.
- Deals with no public process signal before announcement (70% of this batch).
- Generic legal rights language that does not create a company-level transaction pathway.
- Asset-specific rights unless scope clearly affects whole-company acquisition dynamics.
- Unverified media rumors where source timing cannot be confirmed.

## False-Positive Rules (Evidence-Backed)

1. Generic rights language in legal representations is not process evidence.
2. Asset-specific or program-specific ROFR/ROFN is not company-level process evidence.
3. Post-announcement proxy or SC 14D-9 background narrative is not a prior public signal.
4. Equity investments without acquisition options are not process signals.
5. Private unsolicited offers that were declined without public disclosure are not prior public signals.

## Signal Timing Observations

True signals ranged from 17 to 116 days before announcement (median approximately 39 days). The media-sourced signal (TSRO, 17 days) was later-breaking than the SEC-filed signals (DMTX, 39 days; MDVN, 116 days), consistent with media reports tending to break at a later deal stage. False-positive rights-language hits extended to 496 days before announcement (ARRY), suggesting that very stale rights hits are likely noise. A freshness window of 180–365 days is directionally supported by this data.

## Filing Type Findings

8-K is the highest-value filing type for prior-signal detection (score=72 in this batch). 10-Q provides marginal secondary value (score=6). Media reports can carry true signals but require source verification. DEF 14A, 10-K, and SC 13D/A produced zero true signals. SC 14D-9 filings are post-announcement and cannot be prior signals themselves.

## Edge Thesis

The study suggests that biotech acquisition-process intelligence is not about predicting most deals. It is about filtering for the small number of situations where public evidence shows a real process before the market has fully organized around it. For a fund, the value is workflow compression: fewer names, clearer process states, and stronger false-positive controls. Even at a 6% true-signal rate in this batch, distinguishing public process evidence from private background and rights-language noise can improve research quality and reduce wasted diligence on false positives.

## Data Quality Caveats

- PTLA excluded from adjudication due to missing announcement date.
- TSRO true-signal classification relies on a media report; EDGAR-only workflows would not have surfaced it without external news integration.
- The 6% true-signal rate should be interpreted as a lower bound: the baseline candidate group may contain cases where pre-announcement public signals exist but were not captured in this batch's filing coverage.
- This batch is US-listed small-cap biotech acquisitions 2015–2022. Results may not generalize to other sectors, deal sizes, or time periods.

## Next Steps Before Scaling

1. Resolve PTLA announcement date and complete adjudication.
2. Run pattern prep after any future reclassifications.
3. Separate evidence-backed scanner rules from anecdotal observations before live deployment.
4. Verify that live 8-K monitoring would have surfaced MDVN and DMTX signals in real time.
5. Consider whether external news integration is required to catch media-sourced signals like TSRO.
6. Do not scale to 100 cases until current 50-case standards are fully preserved and documented.
