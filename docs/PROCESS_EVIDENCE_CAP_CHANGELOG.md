# Process Evidence Cap Change

Date: 2026-04-29
Change: PM Change #1 only — Binary Gate for Process Evidence

## What Changed

The scanner now applies a hard post-score cap:

If a company has no real process evidence, its final M&A attractiveness score cannot exceed 80.

The normal scoring model still runs first. Strategic value, acquirability, financial health, catalyst signals, acquisition-pattern matching, institutional signals, deal-process points, and penalties are calculated the same way. The cap is applied only after the normal final score is computed.

## Why It Was Added

V12.3 could rank companies above 80 based on inferred M&A logic: strong pipeline, valuation discount, analyst upside, strategic fit, acquirer need, insider buying, or platform attractiveness. Those signals can make a company interesting, but they do not prove a live or specific transaction process.

The cap prevents inferred takeout candidates from ranking like confirmed process names.

## What Qualifies As Real Process Evidence

The gate is intentionally narrow. A company clears the cap only when filings indicate a real transaction path, including:

- Strategic alternatives or formal review language
- Activist SC 13D or clear activist sale pressure
- ROFN, ROFR, or ROFO clause creating a specific acquisition pathway
- Explicit merger agreement language

The current implementation checks the existing Layer 7 inputs:

- `activist_signal`
- `text_signals.strategic_alternatives`
- `text_signals.rofn`
- `text_signals.rofr`
- `text_signals.rofo`
- `text_signals.merger_agreement`

## What Does Not Qualify

These signals do not clear the process-evidence gate:

- Analyst upside
- Change-of-control provisions
- Insider buying
- Valuation discount
- Strategic fit
- Platform attractiveness
- Acquirer need or patent-cliff alignment
- General M&A speculation
- Commercial quality or profitability alone
- Acquisition-pattern matching alone

## Implementation Brief

Files changed:

- `PRODUCTION_SCANNER_V12.py`
- `PROCESS_EVIDENCE_CAP_CHANGELOG.md`

Functions changed:

- `calculate_ma_score`

Functions added:

- `has_real_process_evidence`

Exact logic added:

```python
real_process_evidence = has_real_process_evidence(
    activist_signal=activist_signal,
    text_signals=text_signals,
)

if not real_process_evidence and final_score > PROCESS_EVIDENCE_SCORE_CAP:
    final_score = PROCESS_EVIDENCE_SCORE_CAP
```

Constants added:

```python
PROCESS_EVIDENCE_SCORE_CAP = 80
```

Tests:

- No automated tests existed for this scanner path.
- No tests were added because the request was a surgical production patch and the scanner is primarily a live-data script.
- Verification performed with Python syntax compilation.

Assumptions:

- `PRODUCTION_SCANNER_V12.py` is the active production scanner for V12.3.
- Existing Layer 7 filing detection is the source of truth for process evidence.
- Change-of-control proxy provisions remain scored as a deal-process signal, but they do not satisfy the new binary cap by themselves.

Risks and edge cases:

- A real process may be missed if the relevant filing language is not captured by the existing `text_signals` parser.
- Banker or advisor language is currently captured indirectly through strategic-alternatives/formal-review phrasing. A future parser enhancement could add explicit advisor-retention detection.
- Names capped at 80 can still be `MEDIUM_CONVICTION` if they meet the existing medium gate, but they cannot score above 80 without real process evidence.

Future improvements not implemented:

- Add a dedicated filing parser for retained banker/advisor language.
- Add unit tests with fixture-based `text_signals` and `activist_signal` cases.
- Surface `real_process_evidence` as an explicit output field in scan JSON.
