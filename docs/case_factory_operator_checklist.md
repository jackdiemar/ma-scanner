# Case Factory Operator Checklist

Generated: 2026-05-16

## Purpose

This checklist is the operator reference for running the historical case factory from
70 completed cases toward 200+ source-backed cases.

The case factory is for strategic-process evidence collection and historical
classification. It is not an M&A prediction workflow, not a scanner runbook, and not
a dashboard workflow.

## Current Architecture

The case factory moves each batch through a controlled evidence pipeline:

1. **Universe builder**
   - Builds or extends the acquisition universe.
   - Candidate discovery is only the starting point. EDGAR or source evidence must
     support inclusion before a case can move toward review.

2. **Candidate queue**
   - Selects eligible acquired biotech candidates not already covered by earlier
     batches.
   - Writes the batch candidate queue using the `batch_N_M_*` naming convention.

3. **Staging candidates**
   - Converts selected candidates into the staged input used by the orchestrator.
   - This is the batch boundary. Confirm tickers before moving forward.

4. **Date backfill**
   - Finds source-backed acquisition announcement dates.
   - Dates must come from EDGAR or reliable source evidence. Do not invent dates,
     infer dates from deal close dates, or use unsupported press references.

5. **Filing collection**
   - Collects pre-announcement filing coverage only for cases with confirmed dates.
   - Cases without dates should remain blocked or queued for manual date research.

6. **Exception queue**
   - Assigns cases to review tiers based on dates, filing coverage, and evidence
     state.
   - Missing-date cases should stay blocked until source-backed dates exist.

7. **Source evidence draft**
   - Creates draft evidence rows for manual review.
   - Draft rows are not final adjudication and should not be treated as verified.

8. **Review packet**
   - Packages the batch for human review.
   - The operator should use it to adjudicate exceptions and confirm any proposed
     baselines.

9. **Manual adjudication**
   - Human review decides final classifications.
   - Do not automatically mark TRUE_PUBLIC_PRIOR_SIGNAL, VERIFIED, or
     CALIBRATION_ELIGIBLE.

10. **Final summary**
    - Records final batch counts, evidence coverage, known limitations, and next
      actions after review is complete.

## Core Commands

Run commands from the runtime repo:

```bash
cd /Users/jack/Downloads/ma-scanner
```

### Status

Shows current case factory state, completed batches, latest known step, and next
recommended action.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --status
```

Use this first after any restart.

### Plan

Prints the scaling plan toward the configured target case count.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --plan
```

Use this to orient on batch sizes, candidate gaps, and expected sequence.

### Select Next Batch

Selects the next candidate batch from the available acquisition universe.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --select-next-batch
```

Use this only when the prior batch boundary is clear and the repo is clean.

### Prepare Batch

Runs date-prefill and exception-queue preparation for a batch.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --prepare-batch --start 71 --limit 30
```

Use this for a conventional preparation pass. Do not use it if another operator is
actively changing the same batch files.

### Run Step: Date Prefill

Writes the date-prefill queue for manual date research.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --run-step date-prefill --start 71 --limit 30
```

This creates work URLs and research targets. It should not create fake dates.

### Run Step: Exception Queue

Builds the exception queue after dates are known or after missing-date cases are
intentionally left blocked.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --run-step exception-queue --start 71 --limit 30
```

Use this after date changes to move dated cases forward and keep undated cases
blocked.

### Run Batch Package: Dry Run

Prints the planned one-command workflow without running subprocesses or writing
outputs.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml \
  --run-batch-package \
  --start 71 --limit 30 \
  --allow-date-backfill \
  --allow-filing-collection \
  --dry-run
```

Use this before any real package run.

### Run Batch Package: With Date Backfill

Runs the package workflow with source-backed date discovery enabled.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml \
  --run-batch-package \
  --start 71 --limit 30 \
  --allow-date-backfill
```

Use this when the batch has missing announcement dates and the operator intends to
attempt supported date discovery.

### Run Batch Package: With Filing Collection

Runs the package workflow and allows filing collection for cases that already have
confirmed dates.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml \
  --run-batch-package \
  --start 71 --limit 30 \
  --allow-filing-collection
```

If real EDGAR fetching is added behind a separate safety flag, include
`--enable-edgar-fetch` only when intentional and expected.

### Write Review Packets

Generates the manual review packet for the batch.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --write-review-packets --start 71 --limit 30
```

Use this after the exception queue and source evidence draft are current.

## Safety Flags

### `--allow-date-backfill`

Allows the package workflow to attempt source-backed date discovery for candidates
missing acquisition announcement dates.

Should do:
- Search for real announcement-date evidence.
- Write only supported HIGH or MEDIUM confidence dates.
- Leave ambiguous or unsupported cases blocked for manual research.

Should not do:
- Create fake dates.
- Convert close dates into announcement dates without evidence.
- Mark missing-date cases as ready for filing collection.

### `--allow-filing-collection`

Allows filing collection to run for candidates with confirmed announcement dates.

Should do:
- Process only cases with source-backed dates.
- Skip or block cases without dates.
- Keep filing collection separate from final classification.

Should not do:
- Process undated cases.
- Treat filing collection as adjudication.
- Mutate final classifications.

### `--enable-edgar-fetch`

Current status: expected next flag.

As of this checklist, `--enable-edgar-fetch` is not present in the checked CLI
arguments. Claude is working on real EDGAR filing collection for dated Batch 71-100
cases. Once added, this flag should be required before any real EDGAR filing fetches.

Should do:
- Make live EDGAR filing fetches explicit and intentional.
- Pair with `--allow-filing-collection` when real collection is expected.
- Leave dry runs and non-fetch package preparation offline.

Should not do:
- Run live APIs unexpectedly.
- Fetch filings for cases without dates.
- Bypass evidence or review gates.

### `--allow-clean-baseline-autofinalize`

Allows the package workflow to write proposed clean-baseline classifications for
eligible pending or P6 cases.

Should do:
- Write proposed classifications for researcher review.
- Keep proposals separate from final adjudication.
- Preserve the manual review requirement.

Should not do:
- Write final results.
- Mark cases VERIFIED.
- Mark cases CALIBRATION_ELIGIBLE.
- Automatically classify TRUE_PUBLIC_PRIOR_SIGNAL.

### `--dry-run`

Prints planned steps without running subprocesses or writing output files.

Should do:
- Show what the package command would attempt.
- Help confirm flags, batch range, and step order.

Should not do:
- Write batch artifacts.
- Update state.
- Fetch filings.

## Batch 71-100 Current State

As of 2026-05-16:

- 26 candidates selected.
- 16 announcement dates found.
- 10 announcement dates still missing: ENLV, FATE, GRCL, HRMY, KPTI, LMNX, MOR,
  SYNH, TGTX, VECT.
- Filing collection is pending or active for the 16 dated cases while Claude upgrades
  the batch package for real EDGAR collection.
- Manual adjudication has not started.

Do not touch active Batch 71-100 outputs while that work is in progress.

## Standard Restart Procedure

Use this sequence when resuming work:

1. Check repo state.

```bash
git status --short
```

Stop if the repo is dirty with unclear files.

2. Run the status snapshot helper if available.

```bash
bash scripts/project_status_snapshot.sh
```

Use this only as a restart aid. It should not adjudicate cases or run the scanner.

3. Run the case factory status command.

```bash
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --status
```

4. Inspect the latest run manifest for the active batch.

Look for the newest `batch_N_M_run_manifest.json` and confirm:
- Batch range.
- Command flags.
- Date gate result.
- Filing collection status.
- Next recommended step.

5. Identify the next recommended step from status, manifest, and current batch notes.

6. Do not rerun from scratch unless a clean rerun is actually needed.

## Stop Conditions

Stop immediately if any of the following happens:

- Wrong tickers appear in batch outputs.
- Shared files are being overwritten unexpectedly.
- Date evidence is missing or unsupported.
- Live APIs are being used unexpectedly.
- Final classifications are being mutated before review.
- The repo is dirty with unclear files.
- Cases are moving forward without EDGAR or source evidence.
- Any process attempts to mark VERIFIED or CALIBRATION_ELIGIBLE.

## Quality Rules

These rules apply to every batch:

- EDGAR and source evidence are truth.
- No fake dates.
- No VERIFIED.
- No CALIBRATION_ELIGIBLE.
- No alpha claims.
- No dashboard or frontend changes.
- No automatic TRUE_PUBLIC_PRIOR_SIGNAL classification.
- FMP or other discovery tools can suggest candidates, but they do not classify
  process evidence.
- Filing collection is not final adjudication.
- Manual review remains the classification gate.

## End-of-Day Checklist

Before stopping work:

1. Run:

```bash
git status --short
```

2. Confirm the latest commit if the work should be committed.

```bash
git log -1 --oneline
```

3. Update or run the project status snapshot if useful.

```bash
bash scripts/project_status_snapshot.sh
```

4. Record the next step in the relevant status note, handoff doc, or run manifest.

5. Avoid leaving untracked batch artifacts.

6. Do not leave unclear changes in shared historical files.

## Files To Avoid During Batch 71-100 Work

Do not edit these unless Jack explicitly requests it:

- `src/historical_case_tools/case_factory_orchestrator.py`
- `src/historical_case_tools/pre_announcement_filing_collector.py`
- `data/historical_cases/batch_71_100_*`
- `data/historical_cases/acquisition_announcement_dates.csv`
- `data/historical_cases/source_evidence.csv`
- `data/historical_cases/case_factory_state.json`

This checklist is documentation only.
