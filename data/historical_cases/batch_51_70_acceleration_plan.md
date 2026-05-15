# Batch 51–70 Acceleration Plan

Generated: 2026-05-14

Read-only planning document. No historical case data changed. No packets generated.

---

## Candidate Pool

53 fresh ACQUIRED candidates are pre-seeded in `resolved_case_candidates.csv` beyond the first 50, starting at RHC-0051. Batch 51–70 covers exactly the first 20 of these:

| # | case_id | ticker | company |
|---|---|---|---|
| 51 | RHC-0051-ACQUIRED-EPZM | EPZM | Epizyme |
| 52 | RHC-0052-ACQUIRED-FMTX | FMTX | Forma Therapeutics |
| 53 | RHC-0053-ACQUIRED-GBT | GBT | Global Blood Therapeutics |
| 54 | RHC-0054-ACQUIRED-IMGO | IMGO | Imago BioSciences |
| 55 | RHC-0055-ACQUIRED-OYST | OYST | Oyster Point Pharma |
| 56 | RHC-0056-ACQUIRED-SRRA | SRRA | Sierra Oncology |
| 57 | RHC-0057-ACQUIRED-TPTX | TPTX | Turning Point Therapeutics |
| 58 | RHC-0058-ACQUIRED-BLU | BLU | BELLUS Health |
| 59 | RHC-0059-ACQUIRED-CINC | CINC | CinCor Pharma |
| 60 | RHC-0060-ACQUIRED-CTIC | CTIC | CTI BioPharma |
| 61 | RHC-0061-ACQUIRED-DICE | DICE | DICE Therapeutics |
| 62 | RHC-0062-ACQUIRED-HARP | HARP | Harpoon Therapeutics |
| 63 | RHC-0063-ACQUIRED-ISEE | ISEE | IVERIC bio |
| 64 | RHC-0064-ACQUIRED-RETA | RETA | Reata Pharmaceuticals |
| 65 | RHC-0066-ACQUIRED-ZYNE | ZYNE | Zynerba Pharmaceuticals |
| 66 | RHC-0067-ACQUIRED-ALPN | ALPN | Alpine Immune Sciences |
| 67 | RHC-0068-ACQUIRED-AMAM | AMAM | Ambrx Biopharma |
| 68 | RHC-0069-ACQUIRED-CBAY | CBAY | CymaBay Therapeutics |
| 69 | RHC-0070-ACQUIRED-CERE | CERE | Cerevel Therapeutics |
| 70 | RHC-0071-ACQUIRED-DCPH | DCPH | Deciphera Pharmaceuticals |

Note: RHC-0065 is skipped in the seed (gap in numbering); the resolver jumps to ZYNE at RHC-0066.

---

## 1. Current Pipeline Map

Every step in the first-50 pipeline is already scripted. This section maps each step to its script, input, output, and mode (auto vs. needs-human).

### Step 1 — Candidate Selection

**Script:** `acquisition_prior_signal_batch_runner.py --limit 70`

Reads `resolved_case_candidates.csv`, filters for `likely_outcome_type == ACQUIRED`, sorts by `target_priority()` score (evidence exists, date confidence, filing targets), and takes the first N rows not already in the batch results. For batch 51–70, run with `--limit 70` and the runner selects the next 20 automatically.

**Mode:** Fully automated.

### Step 2 — Announcement Date Backfill

**Script:** `acquisition_announcement_date_backfiller.py`

Reads three sources in priority order:
1. `CURATED_DATE_EVIDENCE` dict hardcoded in the backfiller (fastest, highest confidence)
2. `source_evidence.csv` for rows with `8K_MERGER` evidence type (derives date from filing)
3. Falls back to LOW-confidence estimate from `resolved_case_candidates.csv`

**Mode:** Mostly automated, but new cases (RHC-0051+) are not in `CURATED_DATE_EVIDENCE`. If no merger 8-K exists in `source_evidence.csv`, the date falls back to LOW confidence and blocks prior-signal analysis.

**Bottleneck:** Each of the 20 new cases needs either a `CURATED_DATE_EVIDENCE` entry or a source_evidence merger 8-K row. This is the first hard gate.

### Step 3 — Pre-Announcement Filing Collection

**Script:** `pre_announcement_filing_collector.py`

For each case with a HIGH or MEDIUM confidence announcement date, fetches all EDGAR filings within a 548-day lookback window from the EDGAR submissions API, screened against `TARGET_FORMS` (8-K, 10-Q, 10-K, SC 13D, SC 13D/A, DEF 14A, S-4, 424B3). Downloads filing text and runs `signal_matches()` for phrase hits. Writes to `pre_announcement_filing_targets.csv` and `pre_announcement_signal_hits.csv`.

**Mode:** Fully automated but slow (0.15s sleep between EDGAR requests, 548-day window, multiple form types). Expect 5–15 minutes per case when downloading fresh filing text.

### Step 4 — Hit Classification

**Script:** `prior_signal_adjudicator.py`

Reads `pre_announcement_signal_hits.csv` and auto-classifies each hit row using `classify_hit()`. Checks for private-background markers, false-positive markers, rights-language patterns, and date ordering. Outputs `prior_signal_adjudication_queue.csv`.

**Mode:** Mostly automated. Auto-classifies most ROFR/private-background hits correctly. Sets `NEEDS_MORE_REVIEW` for hits where context is ambiguous. Genuine process phrases (`unsolicited proposal`, `superior proposal`) now score high enough that any hit on these should be manually reviewed.

**Bottleneck:** Any row where `adjudication_classification == NEEDS_MORE_REVIEW` requires human/Claude adjudication via EDGAR SC 14D-9 background review.

### Step 5 — Batch Runner Aggregation

**Script:** `acquisition_prior_signal_batch_runner.py --limit 70`

Aggregates per-case status from adjudication queue + source evidence, assigns final status per `status_from_case()`. Calls the packet generator as a subprocess.

**Mode:** Fully automated.

### Step 6 — Packet Generation

**Script:** `case_packet_generator.py`

Generates `.md` and `.json` packets for each case. Mostly automated; pulls from source_evidence, adjudication queue, and dates.

**Mode:** Fully automated.

### Step 7 — Manual Adjudication

For any case in `POSSIBLE_SIGNAL_NEEDS_REVIEW` or with high-priority hits, a human/Claude must:
1. Read the source filing (usually SC 14D-9 background section) for the hit
2. Classify as public-before-announcement vs. private-background vs. rights-language vs. asset-specific
3. Add ADJUDICATION_NOTE row to `source_evidence.csv`
4. Update `prior_signal_adjudication_queue.csv` with final `adjudication_classification`

**Mode:** Human/Claude. Cannot be automated without LLM inference on filing text. This is where 80% of the per-case research time was spent in batch 1–50.

---

## 2. Speed Bottlenecks

### Bottleneck 1 — Merger 8-K Date Not in Source Evidence (HIGH IMPACT)

The date backfiller cannot assign HIGH confidence dates for RHC-0051 through RHC-0070 without either a `CURATED_DATE_EVIDENCE` entry or a source_evidence merger 8-K row. Missing dates block the filing collector from running with a valid cutoff window.

**Fix:** Add merger 8-K dates for all 20 cases to `CURATED_DATE_EVIDENCE` in `acquisition_announcement_date_backfiller.py` before running the filing collector. This is a one-time ~1-hour EDGAR lookup (find merger 8-K for each ticker, extract filing date). Or: build a small script that does this EDGAR lookup automatically via the submissions API.

### Bottleneck 2 — Filing Text Fetch Rate Limits (MEDIUM IMPACT)

EDGAR enforces 10 req/sec. The collector sleeps 0.15s per request. For 20 cases × ~30 average filings × fetch cost = ~90–120 minutes of wall-clock time for fresh collection.

**Fix:** Already minimal. No API key needed. Can run overnight. Do not try to optimize this.

### Bottleneck 3 — Manual SC 14D-9 Adjudication for Phrase Hits (HIGH IMPACT, LOW VOLUME)

From 50-case base rates: approximately 12–18% of cases have ROFR or process phrase hits that need manual review. For 20 cases, expect 3–5 cases requiring EDGAR reading. These take 15–30 minutes each.

**Fix:** The exception queue (see below) concentrates manual work. Do not open SC 14D-9s for baseline candidates.

### Bottleneck 4 — source_evidence.csv Manual Rows for Non-Baseline Cases (MEDIUM IMPACT)

Every non-baseline case needs at least one source_evidence row documenting why it was adjudicated. In batch 1–50, writing these rows manually was time-consuming.

**Fix:** Build a `source_evidence_autofill.py` helper (see below) that pre-generates ADJUDICATION_NOTE rows from the adjudication queue output, requiring only human fill-in of the excerpt and notes fields.

### What No Longer Needs Time

- Taxonomy design: done
- False-positive classification rules: documented
- Script debugging and data format fixes: resolved
- CRLF whitespace issues: fixed with `lineterminator='\n'` everywhere
- case_id format reconciliation: resolved
- Packet template debugging: resolved

---

## 3. Exception-First Review Queue Design

The core principle: sort cases by how much human time they need, not by case number. Review high-priority hits first. Auto-baseline zero-hit cases last.

### Priority Tiers

| Priority | Condition | Action |
|---|---|---|
| P1-PROCESS | `unsolicited proposal`, `superior proposal`, `acquisition proposal`, `strategic alternatives` (affirm context) hit in pre-announcement filing | EDGAR adjudication required: read source filing, check date ordering, adjudicate PUBLIC vs PRIVATE |
| P1-COMPETING | `competing bid`, `competing proposal`, `consent solicitation` hit | Same as P1-PROCESS |
| P2-ADVISOR | `retained advisor`, `as its financial advisor`, `engaged a financial advisor` hit (no P1 phrase present) | Read source filing; check if SA announcement accompanied or if advisor language is boilerplate |
| P2-ROFR-SCOPE | `right of first refusal`, `right of first negotiation`, `right of first offer` hit | Scope check required: read exhibit or agreement to classify asset-specific vs. company-level |
| P3-DATE-LOW | Announcement date confidence is LOW or missing | Backfill date before any filing analysis; block from prior-signal queue until resolved |
| P4-NO-HIT | No phrase hits in pre-announcement filing window | Auto-baseline candidate; spot-check one SC 14D-9 to confirm private-only |
| P5-PRIVATE | Adjudicator auto-classified PRIVATE_BACKGROUND | Confirm in packet; no further EDGAR work unless source URL is missing |

### Rule: Don't Adjudicate Before Classifying

Before opening any SC 14D-9, check the exception queue tier. P4 and P5 cases do not need SC 14D-9 reads. In batch 1–50, this was not always followed — it cost time.

---

## 4. Exception Queue CSV — Proposed Fields

File: `data/historical_cases/batch_51_70_exception_queue.csv`

```
case_id
ticker
company
announcement_date
date_confidence
pre_announcement_filings_checked
highest_value_hit
filing_type
filing_date
days_before_announcement
phrase_hit
process_category_guess
likely_classification
false_positive_risk
review_priority
recommended_next_action
source_url
excerpt
notes
```

Field explanations:

- `highest_value_hit`: the highest-scoring phrase found in pre-announcement filings (blank if none). Scored by signal strength: `unsolicited proposal` > `superior proposal` > `strategic alternatives (affirm)` > `acquisition proposal` > `retained advisor` > `rofr/rofn` > none.
- `process_category_guess`: auto-assigned from phrase type — unsolicited_proposal / strategic_alternatives / advisor_retained / rofr_rofn / competing_bid / none.
- `likely_classification`: pre-adjudication guess — TRUE_PUBLIC_PRIOR_SIGNAL / POSSIBLE_SIGNAL_NEEDS_REVIEW / ROFR_SCOPE_CHECK / DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE / PRIVATE_BACKGROUND_ONLY.
- `false_positive_risk`: LOW / MEDIUM / HIGH. HIGH = ROFR hit with no process context; MEDIUM = advisor phrase only; LOW = explicit proposal language.
- `review_priority`: P1 / P2 / P3 / P4 / P5 from tier table above.
- `recommended_next_action`: one-line instruction — e.g., "Read source 8-K, check date ordering vs announcement date, adjudicate public vs private."

---

## 5. Recommended Automation Improvements

These are small scripts (50–150 lines each) that would cut total batch time materially. None require broad code changes.

### 5a. `batch_51_70_case_selector.py`

**Input:** `resolved_case_candidates.csv`, `acquisition_prior_signal_batch_results.csv`

**Output:** `batch_51_70_selected_cases.csv` — 20 rows, one per case, pre-populated with: `case_id`, `ticker`, `company_name`, `likely_outcome_year`, merger EDGAR query URL, prior-signal EDGAR query URL.

**Purpose:** Confirms the exact 20 cases selected, generates the EDGAR query URLs needed for date backfill, removes ambiguity about which cases are in scope.

**Effort:** ~1 hour.

### 5b. `exception_queue_builder.py`

**Input:** `pre_announcement_signal_hits.csv`, `prior_signal_adjudication_queue.csv`, `acquisition_announcement_dates.csv`

**Output:** `batch_51_70_exception_queue.csv` with all fields above, sorted by `review_priority`.

**Logic:**
- For each of the 20 cases, find the highest-scoring phrase hit in the signal hits file
- Assign `process_category_guess` from phrase type
- Assign `likely_classification` and `false_positive_risk` from phrase + context
- Assign `review_priority` tier
- Sort: P1 first, P4/P5 last

**Purpose:** Replaces manual triage. Run it after the filing collector completes. Output tells you exactly which 3–5 cases need EDGAR reads and which 15–17 can be auto-baselined.

**Effort:** ~2–3 hours.

### 5c. `merger_date_prefiller.py`

**Input:** List of 20 case tickers (batch_51_70_selected_cases.csv)

**Output:** CURATED_DATE_EVIDENCE entries (formatted for copy-paste into `acquisition_announcement_date_backfiller.py`) or directly writes to `acquisition_announcement_dates.csv`

**Logic:** For each ticker, hits EDGAR submissions API (`data.sec.gov/submissions/CIK{CIK}.json`), finds the earliest 8-K with "agreement and plan of merger" in the filing index, extracts the `filed` date.

**Purpose:** Eliminates the date bottleneck without manual EDGAR lookups.

**Effort:** ~2 hours (mostly reuses existing EDGAR API patterns from the backfiller).

### 5d. `source_evidence_autofill.py`

**Input:** `prior_signal_adjudication_queue.csv` (after manual adjudication is complete)

**Output:** Scaffolded source_evidence rows for ADJUDICATION_NOTE entries — pre-filled with case_id, ticker, evidence_type, source_url, filing_type, filing_date, accession_number from adjudication queue. Human only needs to fill: excerpt, notes.

**Purpose:** Cuts source_evidence row entry time by 60%. Most fields can be derived from the adjudication queue; only the excerpt and notes are judgment calls.

**Effort:** ~1.5 hours.

### 5e. Existing scripts — no changes needed

The following scripts are already adequate for batch 51–70 and should not be modified:
- `prior_signal_adjudicator.py` — auto-classification is good enough; manual EDGAR review handles the rest
- `case_packet_generator.py` — working; do not rebuild
- `acquisition_prior_signal_batch_runner.py` — working; just change `--limit 70`
- `prior_signal_pattern_prep.py` — regenerates CSV + report; run at end

---

## 6. Research Standard Guardrails

These rules apply to every case in batch 51–70 without exception. They are the same rules that produced the clean 50-case dataset.

**G1 — Public-before-announcement is the only gate for TRUE_PUBLIC_PRIOR_SIGNAL.**
The signal must be observable in a publicly filed document or verifiable public report before the acquisition announcement date. SC 14D-9 background sections are post-announcement. They can confirm or deny, but cannot be the signal source.

**G2 — Post-announcement SC 14D-9 is confirmation only.**
Use it to verify whether a process was public. Do not use it as a prior signal source. Phrase hits from SC 14D-9 text should be excluded from consideration as prior public signals.

**G3 — Generic ROFR language does not pass without scope classification.**
Any ROFR/ROFN/ROFO hit requires reading the underlying agreement or exhibit to classify scope. If scope is asset-specific → ASSET_SPECIFIC_RIGHTS_ONLY. If generic legal representation → RIGHTS_LANGUAGE_ONLY. Only company-level, whole-company acquisition rights pass.

**G4 — Private unsolicited offers do not count.**
An offer disclosed privately and declined privately, later appearing only in SC 14D-9 background, is PRIVATE_BACKGROUND_ONLY. Even if Sanofi called the CEO — if it was under confidentiality and not publicly disclosed, it does not count. (ADMS is the reference case.)

**G5 — Source evidence rows required for every non-baseline classification.**
Every case classified as TRUE_PUBLIC_PRIOR_SIGNAL, PRIVATE_BACKGROUND_ONLY, RIGHTS_LANGUAGE_ONLY, or ASSET_SPECIFIC_RIGHTS_ONLY must have at least one ADJUDICATION_NOTE row in source_evidence.csv with: source_url, filing_type, filing_date, accession_number, excerpt, and notes containing `[NONE_FOUND]` / `[FOUND_PUBLIC]` / `[ASSET_SPECIFIC]` / `[PRIVATE_BACKGROUND]` as appropriate.

**G6 — Days-before calculation must use verified announcement date.**
Do not compute days-before-announcement until the date has HIGH or MEDIUM confidence. LOW-confidence dates should not be used in timing calculations.

**G7 — Do not mark VERIFIED or CALIBRATION_ELIGIBLE.**
No case is VERIFIED or CALIBRATION_ELIGIBLE until a separate methodology review approves the batch. This applies to all 20 new cases.

**G8 — Do not count as TRUE_PUBLIC unless source date precedes announcement date.**
A filing on the same day as the announcement is the announcement, not a prior signal. The source filing date must be strictly before the announcement date.

---

## 7. Fastest Batch 51–70 Workflow

### Phase A — Setup (1–2 hours, mostly automated)

```bash
# Step 1: Confirm exactly which 20 cases are in scope
# (manual or run batch_51_70_case_selector.py if built)
python3 src/historical_case_tools/acquisition_prior_signal_batch_runner.py \
    --limit 70 --dry-run

# Step 2: Backfill merger announcement dates for the 20 new cases
# Option A: Add CURATED_DATE_EVIDENCE entries to backfiller manually (fast, high confidence)
# Option B: Run merger_date_prefiller.py if built
python3 src/historical_case_tools/acquisition_announcement_date_backfiller.py

# Verify no DATE_MISSING blockers in acquisition_announcement_dates.csv
python3 -c "
import csv
rows = list(csv.DictReader(open('data/historical_cases/acquisition_announcement_dates.csv')))
new = [r for r in rows if r['case_id'].split('-')[1].isdigit() and int(r['case_id'].split('-')[1]) >= 51]
low = [r for r in new if r['confidence'] == 'LOW']
print(f'New cases: {len(new)}, LOW confidence: {len(low)}')
for r in low: print(r['case_id'], r['ticker'], r['confidence'])
"
```

### Phase B — Filing Collection (5–10 hours wall-clock, unattended)

```bash
# Run pre-announcement filing collection for new cases only
# The collector skips cases already in pre_announcement_filing_targets.csv
python3 src/historical_case_tools/pre_announcement_filing_collector.py

# This runs unattended. Start it and let it complete.
# Check output:
wc -l data/historical_cases/pre_announcement_filing_targets.csv
wc -l data/historical_cases/pre_announcement_signal_hits.csv
```

### Phase C — Exception Queue (30 minutes)

```bash
# Run adjudicator on the new hits
python3 src/historical_case_tools/prior_signal_adjudicator.py

# Build exception queue (manually or run exception_queue_builder.py if built)
# Review output: how many P1/P2 cases need EDGAR reading?
grep -c "P1\|P2" data/historical_cases/batch_51_70_exception_queue.csv
```

### Phase D — Manual EDGAR Adjudication (1–3 hours, depends on hit count)

For each P1 and P2 case (expected 2–5 out of 20):
1. Open the source filing URL from the exception queue
2. If process phrase found in pre-announcement filing: verify filing date < announcement date
3. Read context: is this public-before-announcement or private-background-only?
4. Open SC 14D-9 background section to confirm (confirmation only, not the signal source)
5. Add ADJUDICATION_NOTE row to source_evidence.csv
6. Update `adjudication_classification` in `prior_signal_adjudication_queue.csv`

For each P2-ROFR case:
1. Read the agreement exhibit
2. Classify scope: company-level vs. asset-specific
3. Add row to source_evidence.csv with `[ASSET_SPECIFIC]` or `[COMPANY_LEVEL]` in notes

For P4/P5 cases (expected 15–17 out of 20):
1. Spot-check one SC 14D-9 per case (5 minutes each) to confirm private-only
2. Add ADJUDICATION_NOTE with `[NONE_FOUND]` to source_evidence.csv
3. No further EDGAR work needed

### Phase E — Batch Run and Validation (30 minutes)

```bash
# Run full batch with updated limit
python3 src/historical_case_tools/acquisition_prior_signal_batch_runner.py --limit 70

# Regenerate pattern prep
python3 src/historical_case_tools/prior_signal_pattern_prep.py

# Check for whitespace
git diff --check

# Verify no POSSIBLE_SIGNAL_NEEDS_REVIEW left
python3 -c "
import csv
rows = list(csv.DictReader(open('data/historical_cases/acquisition_prior_signal_batch_results.csv')))
pending = [r for r in rows if r['adjudication_status'] == 'POSSIBLE_SIGNAL_NEEDS_REVIEW']
print('POSSIBLE_SIGNAL_NEEDS_REVIEW remaining:', len(pending))
for r in pending: print(r['case_id'], r['ticker'])
"

# Commit
git add data/historical_cases/ && git commit -m "Adjudicate batch 51-70 ..."
```

---

## 8. Success Criteria for Batch 51–70

Batch 51–70 is done when all of the following are true:

**Date coverage:**
- All 20 cases have announcement date confidence of HIGH or MEDIUM
- Zero cases in DATE_MISSING status

**Filing coverage:**
- All 20 cases have at least one pre-announcement filing check documented in `pre_announcement_filing_targets.csv`
- `filings_checked_count` > 0 for all 20 cases (no case is unchecked)

**Adjudication completeness:**
- Zero cases in POSSIBLE_SIGNAL_NEEDS_REVIEW or NEEDS_MANUAL_REVIEW
- Every case has a final adjudication_status in the batch results

**Source evidence completeness:**
- Every non-baseline case (any status other than DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE) has at least one source_evidence ADJUDICATION_NOTE row with source_url, filing_date, and notes
- Every TRUE_PUBLIC_PRIOR_SIGNAL case has the full set of rows: merger 8-K, SC 14D-9 background, and at least one pre-announcement signal row with source_url and excerpt

**Distribution update:**
- `acquisition_prior_signal_mini_study.md` updated to reflect 70-case totals
- `prior_signal_pattern_prep.csv` and `prior_signal_pattern_prep_report.md` regenerated via `prior_signal_pattern_prep.py`

**No regressions:**
- None of the first 50 cases changed classification
- `git diff --check` passes
- Batch runner runs cleanly with `--limit 70`

---

## 9. Time Estimate

| Phase | Time | Notes |
|---|---|---|
| A — Date backfill for 20 cases | 1–2 hours | EDGAR lookup per ticker; can be scripted |
| B — Filing collection | 5–10 hours wall-clock | Unattended; start overnight |
| C — Exception queue build | 30 min | Manual triage or scripted |
| D — EDGAR adjudication (P1/P2 only) | 1–3 hours | ~3–5 cases × 20–40 min each |
| D — Spot-check baselines (P4/P5) | 1–2 hours | ~15 cases × 5 min each |
| E — Batch run, validation, commit | 30 min | Automated |
| **Total active work** | **4–8 hours** | vs. ~25–40 hours for batch 1–50 |

The primary saving is that taxonomy, scripts, format fixes, and false-positive rules are all done. The 4–8 hour estimate assumes no unexpected hits requiring novel adjudication categories. If a new true-signal case appears, add 1–2 hours for full EDGAR research.

### Is Batch 51–70 materially faster than Batch 1–50?

**Yes, by approximately 4–6×.** The first 50 required:
- Building and debugging all pipeline scripts
- Designing the adjudication taxonomy from scratch
- Fixing CRLF, case_id, and source_evidence format issues
- 24 NEEDS_MANUAL_REVIEW cases adjudicated under an incomplete framework
- 6 POSSIBLE_SIGNAL_NEEDS_REVIEW cases requiring novel EDGAR research paths

None of those costs apply to batch 51–70. The bottleneck is now purely: (1) date backfill for new cases, and (2) manual EDGAR adjudication for any cases with genuine phrase hits. Both are well-bounded.

---

## 10. Recommended Scripts to Build Next (Priority Order)

| Priority | Script | Estimated effort | Benefit |
|---|---|---|---|
| 1 | `merger_date_prefiller.py` | 2 hours | Eliminates date bottleneck entirely; reuses EDGAR API patterns from backfiller |
| 2 | `exception_queue_builder.py` | 2–3 hours | Concentrates manual work; replaces manual triage; generates review priorities automatically |
| 3 | `source_evidence_autofill.py` | 1.5 hours | Pre-scaffolds ADJUDICATION_NOTE rows; cuts source_evidence entry time ~60% |
| 4 | `batch_51_70_case_selector.py` | 1 hour | Confirms selected cases, generates EDGAR query URLs; useful but not blocking |

Build them in priority order. Scripts 1 and 2 together would cut total active work from 4–8 hours to 2–4 hours for this batch and all subsequent batches.
