# Case Factory Integration Smoke Test Report

Generated: 2026-05-16
Orchestrator commit under test: 12fe9f7
Fix commit: (see below)

---

## 1. CLI Flag Audit

Verified argparse flags for all scripts called by the orchestrator.

| Script | Flags verified | Orchestrator uses |
|---|---|---|
| `merger_date_prefiller.py` | `--start`, `--limit`, `--candidates`, `--dates`, `--batch-results`, `--output`, `--report` | `--candidates`, `--start`, `--limit`, `--output`, `--report` |
| `exception_queue_builder.py` | `--start`, `--limit`, `--candidates`, `--dates`, `--batch-results`, `--signal-hits`, `--adj-queue`, `--output`, `--report` | `--candidates`, `--start`, `--limit`, `--output`, `--report` |
| `source_evidence_autofill.py` | `--exception-queue`, `--output`, `--report` | `--exception-queue`, `--output`, `--report` |
| `pre_announcement_filing_collector.py` | `--acquisition-dates`, `--targets-output`, `--hits-output`, `--report`, `--no-api` | not called (collect_filings=false) |

**Result:** All flags exist. No missing or unsupported flags.

---

## 2. Smoke Tests

### --status

```
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --status
```

**Result: PASS**

Output showed:
- 70/200 confirmed, 130 remaining
- 3/70 (4.3%) combined signal rate
- Both finalized batches listed with correct case ranges and signal counts
- All safety flags False

---

### --plan

```
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --plan
```

**Result: PASS**

Output showed:
- 5 planned batches: batch_71_100 through batch_191_200
- 26 local candidates available
- Discovery gap: 104 (correct)
- Correct next commands printed

---

### --select-next-batch

```
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --select-next-batch
```

**Result: PASS**

Output:
- 26 of 30 candidates selected
- 36 excluded (already covered or filtered)
- Gap: 4 additional candidates needed
- batch_71_100_candidate_queue.csv written correctly

---

### --prepare-batch (pre-fix)

```
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --prepare-batch --start 71 --limit 30
```

**Result: FAILED (candidate misalignment)**

**Root cause:** The existing step scripts (`merger_date_prefiller.py`,
`exception_queue_builder.py`) use an index-window approach:
```python
idx_start = start - 51  # → 71-51 = 20
batch = acquired[idx_start : idx_start + limit]  # → [20:50]
```

This window operates on the full `resolved_case_candidates.csv` filtered by
`acquisition_prior_signal_batch_results.csv`. Three structural problems caused
the window to include the wrong candidates:

**Problem 1 — batch_51_70 tickers not in batch_results:**
Batch 51–70 was adjudicated outside the batch-runner pipeline, so those 20
tickers (EPZM…DCPH) are not in `acquisition_prior_signal_batch_results.csv`.
The prefiller treats them as "unprocessed", placing them at indices 0–19.
The window `[20:50]` correctly skips them, but only by accident.

**Problem 2 — 2020 acquisitions in resolved_case_candidates:**
Candidates RHC-0095 through RHC-0100 (ARMO, SYNTX, AIMT, AKCA, ARQL) and
RHC-0130 (MDCO) are 2020 acquisitions. They predate the five-year universe
builder's 2021 start year and are NOT in the universe candidates CSV. But they
DO fall inside the [20:50] window, so they were incorrectly included.

**Problem 3 — 3 valid candidates outside window:**
KROS (index 50), TGTX (index 51), VSTM (index 52) fall at indices 50–52,
just past the [20:50] window, so they were NOT included despite being valid
batch 71–100 candidates.

**Problem 4 — DCPH duplicate:**
DCPH appears twice in resolved_case_candidates (RHC-0071 and RHC-0133). The
second entry falls at index 45, inside the window, so DCPH was incorrectly
queued again.

**Pre-fix misalignment:**

| Prefill had (wrong) | Candidate queue was missing |
|---|---|
| ARMO, SYNTX, AIMT, AKCA, ARQL | KROS, TGTX, VSTM |
| MDCO | — |
| DCPH (already done) | — |

---

## 3. Fix Applied

**File modified:** `src/historical_case_tools/case_factory_orchestrator.py`

**Change:** Added `_write_staging_candidates_csv()` helper and updated
`cmd_run_step` for the `date-prefill` and `exception-queue` steps.

When a `batch_{start}_{end}_candidate_queue.csv` exists for the batch being
prepared, the orchestrator now:

1. Reads the candidate queue (the batch selector's authoritative output)
2. Writes a staging CSV in `resolved_case_candidates` format containing
   exactly those candidates (`batch_71_100_staging_candidates.csv`)
3. Calls each step script with:
   ```
   --candidates staging_path --start 51 --limit N
   ```
   where `--start 51` → `idx_start = 51-51 = 0`, taking all N rows from
   the beginning of the staging file (which only contains our candidates)
4. Falls back to the original index-window behavior if no candidate queue
   exists (backward-compatible)

**Also fixed:** Added `sys.stdout.flush()` before each `subprocess.run()` call
so the orchestrator's header lines appear before subprocess stdout in the
terminal (buffering artifact).

---

### --prepare-batch (post-fix)

```
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --prepare-batch --start 71 --limit 30
```

**Result: PASS**

Output:
```
=== Preparing batch batch_71_100 (cases 71–100) ===

  Using staging candidates: batch_71_100_staging_candidates.csv (26 rows)
Running step 'date-prefill' for batch_71_100...
...
Cases in scope:        26
Needs date backfill:   26
Date already present:  0
...
  Using staging candidates: batch_71_100_staging_candidates.csv (26 rows)
Running step 'exception-queue' for batch_71_100...
...
Cases in scope: 26
  BLOCKED: 26
...
Batch preparation complete for batch_71_100.
```

**Alignment check (post-fix):**

| File | Rows | Tickers match candidate queue |
|---|---|---|
| `batch_71_100_candidate_queue.csv` | 26 | — (reference) |
| `batch_71_100_date_prefill_queue.csv` | 26 | YES |
| `batch_71_100_exception_queue.csv` | 26 | YES |
| `batch_71_100_staging_candidates.csv` | 26 | YES |

No ticker mismatches. All three pipeline files cover the same 26 cases.

---

## 4. Exception Queue Status

All 26 batch_71_100 cases are `BLOCKED` in the exception queue.
This is expected and correct: all 26 candidates have `confidence=LOW` and
`needs_date_backfill=TRUE`. None have a HIGH/MEDIUM announcement date in
`acquisition_announcement_dates.csv`.

| Tier | Count | Meaning |
|---|---|---|
| BLOCKED | 26 | No HIGH/MEDIUM date — must resolve before filing collection |

Filing collection cannot run until dates are backfilled. This is the correct
pre-work gate.

---

## 5. Compile Validation

```
python3 -m py_compile src/historical_case_tools/case_factory_orchestrator.py  → OK
python3 -m py_compile src/historical_case_tools/case_factory_batch_selector.py → OK
python3 -m py_compile src/historical_case_tools/case_factory_config.py         → OK
python3 -m py_compile src/historical_case_tools/case_factory_state.py          → OK
```

---

## 6. Can Batch 71–100 Proceed to Date Prefill?

**YES — with the fix applied.**

The date prefill queue (`batch_71_100_date_prefill_queue.csv`) now contains
exactly the 26 correct candidates, each with:
- EDGAR company search URL
- EDGAR merger 8-K query URL
- EDGAR SC 14D-9 query URL
- `needs_date_backfill=TRUE`
- `date_confidence` empty (no date confirmed yet)

**Step to execute:**
1. Open `data/historical_cases/batch_71_100_date_prefill_queue.csv`
2. For each ticker, find the merger 8-K via the EDGAR query URL
3. Record the announcement date in `data/historical_cases/acquisition_announcement_dates.csv`
   with `confidence=HIGH` and a source URL
4. Re-run `--run-step exception-queue` after dates are resolved
5. Check that BLOCKED cases move to PENDING_FILING_COLLECTION or higher tiers

---

## 7. Remaining Blockers

| Blocker | Type | Resolution |
|---|---|---|
| All 26 batch_71_100 cases have no confirmed date | Date gap | Manual backfill via EDGAR query URLs in prefill queue |
| 4 candidates short of 30-case batch target | Universe gap | Expand resolved_case_candidates.csv OR enable allow_fmp_discovery |
| ~104 candidates needed for batches 101–200 | Universe gap | FMP live discovery or EDGAR expansion required |

---

## 8. Files Written by This Smoke Test

| File | Status |
|---|---|
| `data/historical_cases/batch_71_100_date_prefill_queue.csv` | Written — 26 rows, all BLOCKED |
| `data/historical_cases/batch_71_100_date_prefill_report.md` | Written |
| `data/historical_cases/batch_71_100_exception_queue.csv` | Written — 26 rows, all BLOCKED |
| `data/historical_cases/batch_71_100_exception_queue_report.md` | Written |
| `data/historical_cases/batch_71_100_staging_candidates.csv` | Written — internal staging file |
| `data/historical_cases/case_factory_state.json` | Updated — step completion counts |
| `src/historical_case_tools/case_factory_orchestrator.py` | Fixed — staging candidates + buffering |

---

## 9. Safety Constraints Verified

- No cases adjudicated.
- No classifications changed.
- `source_evidence.csv` not touched.
- No VERIFIED flag set.
- No CALIBRATION_ELIGIBLE flag set.
- No live API calls made.
- No filing collection triggered.
- No live scanner run.
- Dashboard/frontend not touched.
