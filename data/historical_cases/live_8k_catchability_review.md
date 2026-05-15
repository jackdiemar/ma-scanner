# Live 8-K Catchability Review — MDVN and DMTX

Generated: 2026-05-14

Scope: Would the current production scanner (V12) have surfaced MDVN or DMTX from public EDGAR filings before deal announcement, if running live at the time?

This review does not change scanner logic, case classifications, or dashboard output.

---

## Summary Verdicts

| Ticker | Earliest signal | Days before | Catchability verdict | Primary blocker |
|---|---|---|---|---|
| MDVN | 2016-04-28 | 116 | NOT_CATCHABLE_WITH_CURRENT_LOGIC | Universe gap + missing phrase list entries |
| DMTX | 2017-08-25 | 39 | CATCHABLE_WITH_SMALL_RULE_UPDATE | Missing phrase list entries (partial rofr catch possible) |

---

## MDVN (Medivation) — Detailed Analysis

### Signal Facts

- Announcement date: 2016-08-22
- Earliest public signal: 2016-04-28 8-K
- Accession: 0001193125-16-563708
- Signal type: Sanofi issued a press release publicly announcing its $52.50/share unsolicited acquisition proposal; Medivation board rejected it
- Phrases in filing: "proposal from," "proposal to acquire," "unsolicited proposal"
- Second wave (later filings): "strategic alternatives" first appeared in 2016-05-27 8-K (86 days before announcement)

### Universe Coverage

MDVN's market capitalization at signal date was approximately $7–9B (Sanofi's $52.50/share bid was a premium above the then-prevailing price of ~$45/share on ~160M shares outstanding). The production scanner's target universe is $150M–$1.5B. MDVN was well above the cap.

**This is the primary blocker.** The scanner would not have processed MDVN even if every phrase had matched.

### Phrase Detection Gap

The scanner's `_8K_SIGNAL_PHRASES` list (lines 1494–1507 of `src/PRODUCTION_SCANNER_V12.py`) does not include:

| Phrase present in MDVN 8-K | Scanner coverage |
|---|---|
| `unsolicited proposal` | **Not in scanner** |
| `proposal to acquire` | **Not in scanner** |
| `proposal from` | **Not in scanner** |
| `acquisition proposal` | **Not in scanner** |
| `strategic alternatives` | In scanner (score 30) — but only appeared in 2016-05-27 8-K, not the earliest signal |

The `_ADVISOR_PHRASES` list (lines 1512–1524) would not have matched either. The 2016-04-28 8-K is Sanofi's public rejection notice, not a banker-retained announcement.

### What Would Have Been Caught

If the universe filter were extended to include large-cap targets:
- 2016-04-28 8-K: **NOT caught** — phrases absent from scanner
- 2016-05-27 8-K "strategic alternatives": **CAUGHT** — would score 30 pts, sa_is_affirm=True (84 days before announcement)
- All 8 subsequent 8-Ks through 2016-07-05: would continue triggering the strategic alternatives flag

The scanner would have first flagged MDVN at the May 27 8-K, not the April 28 original signal. That is 32 days later than the true earliest signal.

### Catchability Verdict

**NOT_CATCHABLE_WITH_CURRENT_LOGIC** for the earliest signal (116 days before).

Would become **CATCHABLE_WITH_SMALL_RULE_UPDATE** for the subsequent SA signal (84 days before), but universe gap remains the first-order blocker.

---

## DMTX (Dimension Therapeutics) — Detailed Analysis

### Signal Facts

- Announcement date: 2017-10-03
- Earliest public signal: 2017-08-25 8-K
- Accession: 0001193125-17-267472
- Signal type: Board disclosed it had received an unsolicited acquisition proposal from REGENXBIO; retained financial advisor; REGENXBIO had a right of first refusal under a prior agreement
- Phrases in filing: "acquisition proposal," "financial advisor," "right of first refusal," "superior proposal," "unsolicited proposal"

### Universe Coverage

Dimension Therapeutics was a small gene therapy company. Market cap at signal date was approximately $80–150M based on the REGENXBIO proposal of $6.00/share on ~21M shares. This is at or below the scanner's $150M floor. **Universe coverage is borderline.** Scanner may not have included it.

### Phrase Detection Analysis

| Phrase present in DMTX 8-K | Scanner coverage | Would fire |
|---|---|---|
| `unsolicited proposal` | **Not in scanner** | No |
| `acquisition proposal` | **Not in scanner** | No |
| `superior proposal` | **Not in scanner** | No |
| `right of first refusal` | In scanner (rofr, score 15) | **Yes** |
| `financial advisor` partial | In `_ADVISOR_PHRASES` if exact phrasing matches | Maybe |

The 2017-08-25 8-K would have triggered the `rofr` flag (score 15) via "right of first refusal." This is a partial catch — the scanner would have flagged DMTX as a potential ROFR signal, but:
1. The signal_quality would be ROFR, not PROCESS or AFFIRM
2. The interpretation would likely be "ROFR signal — needs scope verification" rather than "active acquisition proposal in progress"
3. The actual acquisition-proposal context would be invisible to the scanner

If the `_ADVISOR_PHRASES` patterns matched the specific phrasing in the 8-K (e.g., "as its financial advisor in connection"), the banker_retained flag would also fire, adding 20–22 pts. This depends on exact phrasing not yet verified.

### What Would Have Been Caught

With current logic: **ROFR flag fires (15 pts).** The DMTX alert would appear in the scanner output as a rights-language signal, requiring manual review to identify it as an active proposal. Given the false-positive rate for rofr (CPXX, ARRY, XLRN were also rofr flags without true signals), this might be deprioritized.

The critical signal phrases — "unsolicited proposal," "superior proposal," "acquisition proposal" — fire zero points. The scanner would miss the most important context entirely.

### Catchability Verdict

**CATCHABLE_WITH_SMALL_RULE_UPDATE.** Adding "unsolicited proposal," "superior proposal," and "acquisition proposal" to `_8K_SIGNAL_PHRASES` at high score weight (25–30 pts each) would have surfaced the 2017-08-25 8-K with the correct signal type. The partial rofr catch currently understates the signal quality significantly.

---

## Missing Phrases — Recommended Additions

These are the high-precision phrases absent from the scanner that would have improved MDVN and DMTX detection:

| Phrase | Scanner dict | Recommended score | Signal type key | Precision in this batch |
|---|---|---|---|---|
| `unsolicited proposal` | Missing | 30 | `unsolicited_proposal` | HIGH (present in both MDVN and DMTX) |
| `superior proposal` | Missing | 28 | `superior_proposal` | HIGH (DMTX; indicates active competing bid) |
| `proposal to acquire` | Missing | 25 | `acquisition_proposal` | HIGH (MDVN) |
| `acquisition proposal` | Missing | 25 | `acquisition_proposal` | HIGH (DMTX) |
| `consent solicitation` | Missing | 20 | `shareholder_pressure` | MEDIUM (appears in MDVN history) |

These phrases have much higher precision than ROFR language. "Unsolicited proposal" and "superior proposal" are terms of art that appear almost exclusively in actual acquisition processes.

**Implementation note:** Add these to `_8K_SIGNAL_PHRASES` in `src/PRODUCTION_SCANNER_V12.py` at lines 1494–1507, before the existing rofr/rofn phrases. These should score above ROFR signals and below the "strategic alternatives" cap.

---

## Universe Coverage Gap

The most important structural finding: **MDVN was out of scope.** The scanner's $1.5B cap is justified for edge (institutional coverage reduces alpha above that), but it also means the tool cannot benchmark against the cleanest EDGAR-caught true signal in this dataset.

Options:
1. **Keep the cap, accept the limitation.** MDVN is an illustrative historical case, not a live target. The tool's claim is "we would catch DMTX-type signals within our universe," not "we catch everything."
2. **Run MDVN as an out-of-sample validation case.** Use it to verify the phrase list works, then remove from live universe.
3. **Track large-cap signals as a separate tier.** No alpha claim, but useful for methodology validation.

Recommendation: keep the cap, document the limitation clearly in any pitch or methodology note.

---

## FMP API vs. EDGAR EFTS — Data Source Gap

The production scanner retrieves 8-K documents via FMP's `get_sec_filings_symbol` (line 1736), limited to the last 365 days and 4 filings. EDGAR EFTS full-text search (`efts.sec.gov/LATEST/search-index`) is used only by the batch runner historical workflow, not by the live scanner.

For live monitoring, this means:
- The scanner only reads the most recent 4 8-Ks, not all filings in a lookback period
- If multiple 8-Ks file in rapid succession (as in MDVN), earlier ones may be missed
- EDGAR EFTS full-text search would be more reliable for phrase detection across all 8-Ks in a date range

This is a secondary gap — important for production reliability but not the first thing to fix.

---

## Minimal Code Changes Needed (Not Implemented)

Do not implement until validated in a non-production test run.

1. **Add 4 phrases to `_8K_SIGNAL_PHRASES`** (lines 1494–1507 in `PRODUCTION_SCANNER_V12.py`):
   ```python
   ('unsolicited proposal',              'unsolicited_proposal',   30),
   ('superior proposal',                 'superior_proposal',      28),
   ('proposal to acquire',               'acquisition_proposal',   25),
   ('acquisition proposal',              'acquisition_proposal',   25),
   ```
   These should be inserted before the existing rofr/rofn entries. Low implementation risk; 4-line addition.

2. **Adjust n_filings parameter** in `fetch_8k_text_signals` from 4 to 8–12. This increases coverage without changing logic.

3. **Optionally switch live 8-K retrieval to EDGAR EFTS** for more reliable full-text search. Higher implementation effort; defer until after phrase list fix is validated.

---

## Summary

| Case | Universe | Earliest phrase detected by current logic | Catchability |
|---|---|---|---|
| MDVN | OUT OF SCOPE ($7–9B vs $1.5B cap) | "strategic alternatives" in May 27 8-K, 84 days before — not earliest signal | NOT_CATCHABLE_WITH_CURRENT_LOGIC |
| DMTX | BORDERLINE ($80–150M vs $150M floor) | "right of first refusal" in Aug 25 8-K, 39 days before — wrong signal type | CATCHABLE_WITH_SMALL_RULE_UPDATE |

Adding "unsolicited proposal" and "superior proposal" to the phrase list is the single highest-ROI code change for improving prior-signal detection quality within the existing universe. The MDVN universe gap is a separate structural issue.
