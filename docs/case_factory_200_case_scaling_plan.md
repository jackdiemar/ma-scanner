# Case Factory: 200-Case Scaling Plan

Generated: 2026-05-16

## Purpose

This document describes the architecture, current state, candidate availability, and
batch sequence for scaling the historical prior-signal study from 70 confirmed cases
to 200 cases using the unified case factory orchestration system.

---

## Strategic Context

This system is a **Strategic Process Intelligence** dataset, not an M&A prediction engine.
It detects and classifies pre-announcement process evidence from SEC filings in small-cap
biotech acquisitions. The 200-case target builds calibration depth for the signal discriminator
(`signal_quality`: AFFIRM / PROCESS / ROFR / MERGER / BOILERPLATE / SCORE_ONLY).

The combined 70-case true prior signal rate is **3/70 (4.3%)**, establishing a baseline for
false-positive filtering and signal rarity calibration.

---

## Current State (as of 2026-05-16)

| Metric | Value |
|---|---|
| Confirmed cases | 70 |
| Cases needed to reach 200 | 130 |
| True prior signal cases | 3 (4.3%) |
| Finalized batches | first_50, batch_51_70 |
| Local candidates available | ~26 (from five_year_acquisition_universe_candidates.csv) |
| Discovery gap | ~104 candidates needed from external sources |
| State file | data/historical_cases/case_factory_state.json |
| Config file | configs/case_factory.yaml |

### What is complete through case 70

- **First 50 (cases 1–50):** Full adjudication complete. 3 TRUE_PUBLIC_PRIOR_SIGNAL, 35
  DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE, 9 PRIVATE_BACKGROUND_ONLY, 2 ASSET_SPECIFIC_RIGHTS_ONLY,
  1 RIGHTS_LANGUAGE_ONLY. All dates source-backed.

- **Batch 51–70 (cases 51–70):** Full adjudication complete. 0 TRUE_PUBLIC_PRIOR_SIGNAL,
  11 DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE, 7 RIGHTS_LANGUAGE_ONLY, 2 ASSET_SPECIFIC_RIGHTS_ONLY.
  Filing coverage: 508 filings across 19 EDGAR-covered cases. BLU (FPI, 6-K filer) had no
  EDGAR target-form coverage.

---

## Candidate Availability

### Local universe (five_year_acquisition_universe_candidates.csv)

| Bucket | Count |
|---|---|
| Already covered (first_50 or batch_51_70) | 34 |
| Excluded (EXCLUDE_DUPLICATE) | 1 |
| Known batch_51_70 tickers not flagged in universe | 1 (DCPH) |
| MAYBE_NEEDS_REVIEW (new, needs date backfill) | 26 |
| **Available for next batch** | **~26** |

The 26 MAYBE_NEEDS_REVIEW candidates span:
- 2021 acquisitions: CHMA, CNST, STML, LMNX, TBIO (5)
- 2023 acquisitions: RXDX, ALBO, HZNP, SGEN, SNDX, VECT, ENLV, HRMY, SYNH (9)
- 2024 acquisitions: FATE, FUSN, G1T, GRCL, KRTX, LBPH, MORF, MRTX, MOR, KPTI, KROS, TGTX, VSTM (13)

All 26 require date backfill before filing collection. None have HIGH-confidence dates yet.

### Discovery gap to reach 200

| Phase | Cases needed | Local available | Gap |
|---|---|---|---|
| Cases 71–200 | 130 | ~26 | ~104 |

**~104 candidates must come from external discovery:**
1. EDGAR universe expansion (add 2024–2025 acquisitions to resolved_case_candidates.csv)
2. FMP live discovery (enable `allow_fmp_discovery: true` in config — requires FMP_API_KEY)
3. Lookback extension (earlier years before 2021 or later years into 2025)

---

## Recommended Batch Sequence

| Batch | Cases | Size | Source | Notes |
|---|---|---|---|---|
| batch_71_100 | 71–100 | 30 | Local universe (26) + 4 from discovery | All need date backfill |
| batch_101_130 | 101–130 | 30 | EDGAR expansion or FMP | Enable FMP discovery if needed |
| batch_131_160 | 131–160 | 30 | EDGAR expansion or FMP | — |
| batch_161_190 | 161–190 | 30 | EDGAR expansion or FMP | — |
| batch_191_200 | 191–200 | 10 | EDGAR expansion or FMP | Final partial batch |

---

## System Architecture

### Config layer

`configs/case_factory.yaml` — single source of truth for:
- Scale targets (target_case_count, batch_size)
- Evidence requirements (require_source_backed_dates, require_edgar_or_source_url)
- Safety flags (all default false: allow_fmp_discovery, allow_live_api, collect_filings,
  adjudicate_automatically, mark_verified, mark_calibration_eligible, run_full_live_scanner)
- Filing collection limits (max_filings_per_case, eight_k_scan_depth)
- Manual review tiers (P1, P2, P3, P4, P6_WITH_HITS)

### State tracking

`data/historical_cases/case_factory_state.json` — tracks across sessions:
- Batch records with status, case range, signal counts, and summary file pointers
- Step completion counts (dates_backfilled, exception_queues_created, etc.)
- Last completed step and next recommended step
- Combined signal rate across all finalized batches

### Orchestrator CLI

`src/historical_case_tools/case_factory_orchestrator.py` — unified entry point:

```bash
# Check status
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --status

# See scaling plan
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --plan

# Select candidates for next batch
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --select-next-batch

# Full batch preparation (date prefill + exception queue)
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --prepare-batch --start 71 --limit 30

# Individual steps
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --run-step date-prefill --start 71 --limit 30

python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --run-step exception-queue --start 71 --limit 30

# Manual review packet
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --write-review-packets --start 71 --limit 30
```

### Batch naming convention

All outputs use consistent naming: `batch_{start}_{end}_{artifact}.{ext}`

- `batch_71_100_candidate_queue.csv`
- `batch_71_100_date_prefill_queue.csv`
- `batch_71_100_exception_queue.csv`
- `batch_71_100_source_evidence_draft.csv`
- `batch_71_100_review_packet.md`
- `batch_71_100_final_summary.md`

For the final partial batch:
- `batch_191_200_candidate_queue.csv`
- `batch_191_200_final_summary.md`

### Module structure

```
src/historical_case_tools/
  case_factory_config.py       # YAML loader, CaseFactoryConfig dataclass
  case_factory_state.py        # StateManager, read/write case_factory_state.json
  case_factory_batch_selector.py  # Candidate selection from universe CSV
  case_factory_orchestrator.py # Main CLI, step dispatch, review packet generation

  # Existing scripts called by orchestrator (not modified):
  merger_date_prefiller.py     # Date prefill work queue
  exception_queue_builder.py   # Priority tier assignment
  source_evidence_autofill.py  # Draft evidence placeholder rows
  pre_announcement_filing_collector.py  # Filing collection (EDGAR)
  edgar_source_pull_helper.py  # Filing text retrieval
```

---

## Step Pipeline Per Batch

```
select_candidates
  → date_prefill_queue         (merger_date_prefiller.py)
  → [manual: resolve BLOCKED cases in acquisition_announcement_dates.csv]
  → exception_queue            (exception_queue_builder.py)
  → source_evidence_draft      (source_evidence_autofill.py)
  → write_review_packet        (orchestrator)
  → [manual: adjudicate P1/P2/P3/P4 cases]
  → [manual: spot-check P6 cases]
  → [manual: write final_summary.md]
  → update state.json          (orchestrator)
```

Filing collection is a separate opt-in step:
```bash
# Only run if collect_filings: true in config
python3 src/historical_case_tools/pre_announcement_filing_collector.py --no-api
```

---

## One-Command Batch Package Workflow

`--run-batch-package` runs the full pipeline in a single command and writes all outputs.

### Flags

| Flag | Effect |
|---|---|
| `--allow-date-backfill` | Proceed past the date gate even when candidates lack confirmed dates. Exception queue will mark them BLOCKED. Manual EDGAR research still required. |
| `--allow-filing-collection` | Run `pre_announcement_filing_collector --no-api` for candidates that have confirmed dates. Skipped automatically if 0 candidates have dates. |
| `--allow-clean-baseline-autofinalize` | Write `batch_N_M_proposed_clean_baselines.csv` for PENDING_FILING_COLLECTION and P6 tier cases. Researcher must confirm before finalizing. |
| `--dry-run` | Print planned steps without running subprocesses or writing output files. |

### Pipeline steps

1. Validate candidate queue exists
2. Run date-prefill queue (`merger_date_prefiller.py` — generates EDGAR work URLs, does NOT fetch dates)
3. Check date gate: read `acquisition_announcement_dates.csv`, count HIGH/MEDIUM confidence dates
   - All dates present → PASS
   - Partial dates + `--allow-date-backfill` → PARTIAL, continue
   - Missing dates + no flag → BLOCKED, write package report and exit cleanly
4. Run exception queue (`exception_queue_builder.py` — missing-date cases marked BLOCKED)
5. Run filing collection (`pre_announcement_filing_collector --no-api`) if `--allow-filing-collection` and at least one candidate has a date
6. Run source evidence draft (`source_evidence_autofill.py`)
7. Write review packet
8. Write proposed clean baselines (if `--allow-clean-baseline-autofinalize`)
9. Write `batch_N_M_package_report.md`
10. Write `batch_N_M_run_manifest.json`
11. Update `case_factory_state.json`

### Outputs

| File | When written |
|---|---|
| `batch_N_M_date_prefill_queue.csv` | Always |
| `batch_N_M_exception_queue.csv` | After date gate (PASS or PARTIAL) |
| `batch_N_M_source_evidence_draft.csv` | After exception queue |
| `batch_N_M_review_packet.md` | After source evidence |
| `batch_N_M_filing_targets.csv` / `batch_N_M_signal_hits.csv` | If `--allow-filing-collection` and dates exist |
| `batch_N_M_proposed_clean_baselines.csv` | If `--allow-clean-baseline-autofinalize` |
| `batch_N_M_package_report.md` | Always |
| `batch_N_M_run_manifest.json` | Always (except dry-run) |

### Example: batch 71–100 (pre-date-backfill state)

```bash
# Dry run first — prints planned steps, no file writes
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml \
  --run-batch-package \
  --start 71 --limit 30 \
  --allow-date-backfill \
  --allow-filing-collection \
  --dry-run

# Real run (proceeds past date gate; 26 cases will be BLOCKED in exception queue)
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml \
  --run-batch-package \
  --start 71 --limit 30 \
  --allow-date-backfill \
  --allow-filing-collection
```

**What `--allow-date-backfill` actually does:**
1. Identifies candidates missing confirmed dates.
2. Resolves each company's SEC CIK via `company_tickers.json` or EDGAR company search.
3. Fetches the EDGAR submissions JSON for each company.
4. Finds 8-K filings with Item 1.01 (Material Definitive Agreement) in a ±2-year window.
5. Checks the filing index for EX-2.x (merger/acquisition agreement) exhibits.
6. Writes HIGH or MEDIUM confidence dates to `acquisition_announcement_dates.csv`.
7. Writes source evidence rows to `source_evidence.csv`.
8. Reports all results in `batch_N_M_date_backfill_report.md`.
9. Re-checks the date gate — dated cases proceed, remaining BLOCKED cases get manual EDGAR URLs.

**Confidence levels:**
- `HIGH`: Single Item 1.01 8-K in expected year + EX-2.x confirmed
- `MEDIUM`: Item 1.01 8-K with EX-2.x but multiple candidates or year−1 filing
- `LOW`: Skipped — not written (too ambiguous)

Cases that the automated backfill cannot resolve remain BLOCKED in the exception queue.
Resolve them manually using EDGAR URLs in `batch_N_M_date_prefill_queue.csv`.

### After date backfill (re-run to unlock filing collection)

Once dates are recorded in `acquisition_announcement_dates.csv` with `confidence=HIGH`:

```bash
# Re-run exception queue (cases will move from BLOCKED to PENDING_FILING_COLLECTION)
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml \
  --run-step exception-queue --start 71 --limit 30

# Re-run full package (filing collection will now run for dated candidates)
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml \
  --run-batch-package \
  --start 71 --limit 30 \
  --allow-filing-collection
```

---

## Risks and Stop Conditions

### Stop conditions (do not proceed if any apply)

- A case is being classified based on post-announcement SC 14D-9 / proxy background only.
- A case is classified TRUE_PUBLIC_PRIOR_SIGNAL without a verified source URL, filing date,
  excerpt, and days-before calculation.
- FMP data is being used as classification evidence (it is context only).
- Any case is marked VERIFIED or CALIBRATION_ELIGIBLE.
- The scanner is being run for historical classification (run_full_live_scanner must stay false).

### Known risks

| Risk | Mitigation |
|---|---|
| Local universe covers only ~26 new candidates | Must expand before batch_101_130 |
| MAYBE_NEEDS_REVIEW candidates may not all confirm as standard acquisitions | Date backfill step filters non-standard deals |
| BLU-style FPI cases (6-K filers) have no EDGAR target-form coverage | Flag as baseline, note coverage gap |
| Ticker staleness (renamed, delisted, ticker reuse) | Verify via EDGAR company search before filing collection |
| FMP discovery may surface non-standard deals (SPAC, asset-only) | FMP is discovery only; EDGAR/source evidence confirms inclusion |

---

## Next Commands

```bash
# 1. Verify current state
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --status

# 2. See full plan
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --plan

# 3. Select batch 71-100 candidates
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --select-next-batch

# 4. Prepare batch (date prefill + exception queue)
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --prepare-batch --start 71 --limit 30
```

---

## Discovery Gap Resolution

To close the 104-candidate gap after batch_71_100:

### Option 1: EDGAR expansion (preferred)

Run the five-year acquisition universe builder with a broader seed or extended date range,
adding 2024–2025 acquisitions to `resolved_case_candidates.csv`:

```bash
python3 src/historical_case_tools/five_year_acquisition_universe_builder.py
```

Then re-run `--select-next-batch` for the next batch.

### Option 2: FMP live discovery

1. Set `allow_fmp_discovery: true` in `configs/case_factory.yaml`
2. Ensure `FMP_API_KEY` is in `config/.env`
3. Run the FMP candidate discovery stub:

```bash
python3 src/historical_case_tools/fmp_candidate_discovery_stub.py
```

> **Important:** FMP discovery surfaces candidates only. Every candidate must be confirmed
> with EDGAR/source evidence before filing collection. FMP does not classify process signals.

### Option 3: Manual seed

Add confirmed public-company acquisition rows directly to `resolved_case_candidates.csv`
with `likely_outcome_type=ACQUIRED` and a verified source URL.

---

*This plan is read-only documentation. No cases adjudicated. No files mutated.*
