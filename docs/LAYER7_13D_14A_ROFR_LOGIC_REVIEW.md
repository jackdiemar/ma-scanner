# Layer 7 Filing Logic Review: 13D, 14A, ROFR / ROFN

Date: 2026-04-29
Scanner reviewed: `PRODUCTION_SCANNER_V12.py`

This document explains the current coding logic behind the scanner's deal-process layer: activist `SC 13D`, 8-K process language including `ROFR` / `ROFN`, and proxy `DEF 14A` change-of-control provisions. It also lists the main failure modes and practical improvements.

## What Layer 7 Is Trying To Do

Layer 7 is different from the rest of the model.

Most scanner layers infer M&A attractiveness from things like pipeline quality, valuation, analyst upside, commercial revenue, strategic fit, and acquirer need. Layer 7 tries to detect whether a real transaction process or specific acquisition pathway may already exist.

The current sources are:

- `SC 13D`: activist ownership / sale-pressure signal
- Recent `8-K`: strategic alternatives, ROFR, ROFN, ROFO, merger agreement, exclusive license, collaboration language
- `DEF 14A`: executive change-of-control economics

## Current Data Flow

1. At scan start, the scanner preloads recent `SC 13D` filings for the whole universe.
2. For each ticker, after bankruptcy screening, the scanner fetches recent 8-K filings and the latest proxy.
3. The scanner parses filing text with phrase matching.
4. Detected signals are passed into `calculate_ma_score`.
5. Layer 7 adds deal-process points and human-readable flags.
6. The new process-evidence cap checks whether the company has a real process signal before allowing a score above 80.

## SC 13D Logic

Code path:

- `FMPClient.get_13d_filings`
- `preload_activist_signals`
- `calculate_ma_score`

The scanner calls FMP's `sec-filings-search/form-type` endpoint for `SC 13D` filings from the last 60 days. It pages through up to 5 pages of 100 filings, so up to 500 recent 13D filings.

Each filing is checked against the scanner universe. If the filing ticker is in the universe, the scanner records:

- ticker
- filer name
- filing date
- whether the filer matches a known activist list
- points

Scoring:

- Known biotech activist: `20` points
- Other 13D filer: `12` points

Known activist names currently include firms such as Sarissa, Caligan, Starboard, Elliott, Third Point, JANA, Engaged Capital, Deerfield, Baker Brothers, Avoro, Foresite, Perceptive, BVF, and related names.

How it affects output:

- Adds a `DealProcess` signal
- Adds an `ACTIVIST 13D` flag
- Allows the company to clear the real-process-evidence cap
- Can override some quality gates in conviction-tier logic if market cap and runway pass

## 13D Interpretation

A 13D is meaningful because it means an investor owns more than 5% and is not filing passively. It does not automatically mean the investor is demanding a sale, but it is more process-like than analyst upside or general M&A speculation.

Current scanner assumption:

Any recent `SC 13D` on a universe ticker is treated as activist pressure. Known activist filers get stronger points.

## 13D Weaknesses

The scanner does not yet read the actual Item 4 text of the 13D. That is the biggest limitation.

A 13D can be filed for many reasons:

- board discussions
- financing negotiations
- ordinary activist pressure
- strategic review demands
- sale demands
- governance disputes
- ownership restructuring

The current code treats all 13D filings as process evidence. That is directionally useful but too broad.

Possible false positives:

- A 13D filer has no sale agenda
- A non-activist strategic holder files 13D for technical reasons
- The filer wants board seats, not a sale
- The filing is stale or amended without new pressure

Possible false negatives:

- Activist pressure appears in `13D/A`, not initial `SC 13D`
- Filer name does not match the known activist list
- Sale language exists in an attachment but is not parsed

## 8-K ROFR / ROFN / Strategic Alternatives Logic

Code path:

- `FMPClient.get_sec_filings_symbol`
- `fetch_8k_text_signals`
- `_fetch_doc_text`
- `_8K_SIGNAL_PHRASES`
- `calculate_ma_score`

The scanner pulls SEC filings for the ticker from the last 365 days, filters to recent `8-K` filings, and reads the last 4 document bodies.

The scanner then searches lowercase filing text for exact phrases.

Current 8-K phrases and points:

| Phrase | Internal flag | Points |
|---|---|---:|
| `strategic alternatives` | `strategic_alternatives` | 30 |
| `exploring strategic` | `strategic_alternatives` | 30 |
| `right of first negotiation` | `rofn` | 18 |
| `right of first refusal` | `rofr` | 15 |
| `right of first offer` | `rofo` | 14 |
| `merger agreement` | `merger_agreement` | 12 |
| `exclusive worldwide license` | `exclusive_license` | 8 |
| `exclusive license agreement` | `exclusive_license` | 8 |
| `collaboration and license` | `collaboration` | 5 |
| `co-development agreement` | `collaboration` | 5 |

The scanner also looks for named major pharma partners in the same filing text. If a major pharma name appears with a structural clause like ROFN, ROFR, or exclusive license, the code adds a small extra confidence bonus.

Detected pharma names include Pfizer, AbbVie, AstraZeneca, BMS, Eli Lilly, Novartis, Roche, Genentech, Sanofi, Merck, Gilead, Amgen, Novo Nordisk, J&J, Janssen, Takeda, Biogen, Regeneron, and Vertex.

## ROFR / ROFN Interpretation

ROFR, ROFN, and ROFO are not the same as a live sale process.

But they are real process evidence because they create a specific acquisition pathway with a specific counterparty:

- `ROFR`: right of first refusal. A partner may have the right to match or accept terms before another buyer can close.
- `ROFN`: right of first negotiation. A partner gets the first negotiation window before the company can fully shop the asset.
- `ROFO`: right of first offer. A partner gets the first opportunity to make an offer.

These clauses matter because they can make an eventual sale more likely to involve the named partner, or at least constrain the buyer universe.

Current scanner assumption:

If a recent 8-K contains ROFR / ROFN / ROFO language, the company has a specific acquisition pathway and clears the process-evidence cap.

## Strategic Alternatives Logic

If the scanner sees `strategic alternatives` or `exploring strategic`, it treats that as the strongest Layer 7 signal.

Current behavior:

- Adds `30` Layer 7 points
- Sets `strategic_alt = True`
- Adds a flag saying the board hired a banker
- Allows conviction-tier override to `HIGH_CONVICTION` if market cap passes
- Clears the process-evidence cap

This is the strongest current filing signal because "strategic alternatives" often means the board has started a formal review, hired advisors, or is considering sale / merger / partnership options.

## 8-K Weaknesses

The 8-K parser is phrase-based. It does not understand context.

Possible false positives:

- The phrase appears in boilerplate risk factors
- ROFR/ROFN applies only to a single asset, not the whole company
- The named pharma appears elsewhere in the document but is not the clause counterparty
- A collaboration agreement is treated as deal-process-like even if it is just ordinary licensing
- `merger agreement` may refer to historical, terminated, or unrelated language

Possible false negatives:

- The filing says "review of strategic options" instead of "strategic alternatives"
- The filing says "retained advisor", "engaged financial advisor", "investment bank", or "sale process" without the exact phrases
- The relevant agreement is attached as an exhibit and not captured in the main 8-K text window
- The agreement uses legal wording like "first right to negotiate", "matching right", "acquisition right", "option to acquire", or "change of control notice"

## DEF 14A Change-of-Control Logic

Code path:

- `FMPClient.get_proxy_filings`
- `fetch_proxy_signal`
- `_COC_PHRASES`
- `calculate_ma_score`

The scanner gets the most recent `DEF 14A` proxy filing. If the direct query fails, it falls back to all filings from roughly the last 400 days and filters for `DEF 14A` / `DEF14A`.

It fetches up to 600 KB of text from the proxy and searches for change-of-control phrases:

- `change in control`
- `change of control`
- `termination following a change`
- `double trigger`
- `single trigger`
- `accelerated vesting upon`
- `golden parachute`
- `parachute payment`

If any phrase appears, `has_coc_provisions` becomes true.

Then it tries to estimate executive payout size:

1. Find each nearby `change in/of control` phrase.
2. Scan the next 800 characters.
3. Extract dollar amounts like `$1,000,000`.
4. Extract text amounts like `1.5 million`.
5. Keep only values above `$500K`.
6. Use the largest amount found.

Scoring:

- `$10M+` estimated payout: `10` points
- `$5M+` estimated payout: `7` points
- `$1M+` estimated payout: `4` points
- CoC language but no payout estimate: `2` points

## 14A Interpretation

Change-of-control provisions are useful but weak.

They show management has economics that could vest or pay out if a sale happens. That can make management more aligned with a transaction, but it does not prove a process is underway.

Current scanner treatment after the process-evidence cap:

- CoC provisions still add Layer 7 points.
- CoC provisions still appear in flags.
- CoC provisions do not clear the real-process-evidence cap by themselves.

That is the correct direction. CoC is supportive evidence, not a binary process signal.

## 14A Weaknesses

Possible false positives:

- Most public companies have standard CoC language.
- The parser may grab unrelated dollar values near CoC text.
- It only captures the largest local amount, not the true total executive payout.
- It may mistake severance examples or table footnotes for actual payout values.
- CoC economics can be defensive boilerplate rather than sale motivation.

Possible false negatives:

- Golden parachute tables may be farther than 800 characters from the phrase.
- Amounts may be in HTML tables that flatten poorly into text.
- Values may appear as columns without dollar signs.
- Equity acceleration value may be described separately from cash severance.
- Older proxy filings may be needed if the latest proxy has different formatting.

## How Layer 7 Interacts With Final Score

Layer 7 can contribute up to 35 points to the score.

The total score uses:

```text
raw_total = layer1 + layer2 + layer3 + layer4 + layer5 + layer6 + layer7
final_score = min(max(raw_total - penalties, 0), 100)
```

Then the process-evidence cap is applied:

```text
if no real process evidence and final_score > 80:
    final_score = 80
```

Real process evidence currently includes:

- activist 13D
- strategic alternatives
- ROFN
- ROFR
- ROFO
- merger agreement

Real process evidence currently excludes:

- change-of-control provisions
- insider buying
- analyst upside
- valuation discount
- strategic fit
- acquirer need
- platform attractiveness
- acquisition-pattern matching

## Main Things That Need Improvement

1. Parse actual 13D Item 4 text

The model should distinguish a generic 13D from a sale-pressure 13D.

Better 13D terms to detect:

- `strategic alternatives`
- `sale of the company`
- `maximize shareholder value`
- `business combination`
- `merger`
- `tender offer`
- `board representation`
- `engaged with management`
- `review strategic options`

Suggested scoring:

- 13D with explicit sale / merger language: strongest
- 13D with strategic review language: strong
- 13D with only governance language: moderate
- Unknown / technical 13D: weak

2. Add 13D/A support

Activist campaigns often evolve through amendments. The scanner should include `SC 13D/A`, not only initial `SC 13D`.

3. Add banker / advisor phrase detection

The PM requirement includes banker/advisor hired for sale process. The current code infers this from strategic-alternatives language but does not directly detect advisor language.

Useful phrases:

- `retained financial advisor`
- `engaged financial advisor`
- `hired an investment bank`
- `retained Goldman Sachs`
- `retained J.P. Morgan`
- `retained Morgan Stanley`
- `retained Centerview`
- `retained Evercore`
- `retained Lazard`
- `sale process`
- `formal review`
- `review of strategic options`

4. Make ROFR / ROFN context-aware

The scanner should identify what the clause applies to:

- whole company
- product asset
- license territory
- manufacturing rights
- collaboration program
- change-of-control transaction

A ROFR on one asset should score lower than a company-level acquisition right.

5. Link named pharma to the clause, not the whole document

Currently, if a pharma name appears anywhere in the filing, it may be paired with the clause. Better logic would inspect a local text window around the ROFR / ROFN phrase and only assign the pharma partner if it appears nearby.

6. Improve 14A payout extraction

Instead of scanning 800 characters after "change of control", the scanner should parse golden parachute tables more deliberately.

Better fields:

- cash severance
- equity acceleration
- benefits
- excise tax gross-up
- total named executive officer payout
- CEO payout
- total NEO payout

7. Separate "supportive signal" from "process signal"

Current Layer 7 contains both:

- process evidence: 13D, strategic alternatives, ROFR / ROFN
- supportive governance evidence: CoC provisions

For clarity, the scanner could split this into:

- `process_evidence_score`
- `governance_alignment_score`

That would make the process cap easier to audit.

8. Add evidence excerpts

The output should include a short filing excerpt around the matched phrase. This would make it easier to verify whether the signal is real.

Example fields:

- `process_evidence_phrase`
- `process_evidence_excerpt`
- `process_evidence_filing_url`
- `process_evidence_filing_date`

9. Add filing date decay

A ROFR from a 300-day-old agreement is less meaningful than a strategic alternatives filing from last week.

Potential decay:

- 0-30 days: full points
- 31-90 days: 75%
- 91-180 days: 50%
- 181-365 days: 25%

10. Avoid hard-coded phrase brittleness

The current phrase list is short. It should be expanded and grouped by signal type, with tests.

## Suggested Priority Order

1. Add `SC 13D/A` and parse Item 4 sale-pressure language.
2. Add banker/advisor/financial-advisor language to 8-K detection.
3. Add local-window pharma matching around ROFR / ROFN phrases.
4. Split process evidence from governance alignment in the output.
5. Add excerpts and filing URLs to the JSON output.
6. Improve 14A table extraction.
7. Add date decay for old process signals.
8. Add unit tests with SEC filing text fixtures.

## Bottom Line

The current Layer 7 logic is directionally strong because it moves beyond generic M&A attractiveness and looks for filings that can indicate a real process. The strongest parts are strategic alternatives detection, activist 13D detection, and ROFR / ROFN pathway detection.

The biggest weakness is context. The parser currently detects phrases, not legal meaning. It needs better 13D Item 4 parsing, banker/advisor language, local context around ROFR / ROFN clauses, and cleaner 14A payout extraction.

The latest process-evidence cap makes this more important: if a filing clears the cap, the scanner should be confident that the filing really shows a live process or specific acquisition pathway.
