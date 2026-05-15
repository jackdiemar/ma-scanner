# Project Status Snapshot Helper

Status: lightweight end-of-day helper.

## Purpose

`scripts/project_status_snapshot.sh` prints and writes a concise project restart note for the MA Scanner historical case workflow.

It is designed for end-of-day handoff, especially while Batch 51-70 adjudication is active.

## Command

```bash
bash scripts/project_status_snapshot.sh
```

The script writes:

```text
data/historical_cases/project_status_snapshot.md
```

## What It Reports

- Current git branch.
- `git status --short`.
- Latest 12 commits.
- Whether key Batch 51-70 files exist.
- Whether key FMP and universe-builder files exist.
- Current Batch 51-70 queue summary, if available.
- First 50-case study status.
- Batch 51-70 status.
- High-priority adjudication status.
- Remaining known work.
- Warnings about files and workflows not to touch.
- Next recommended command sequence.

## Guardrails

The helper does not run the scanner, edit classifications, edit `source_evidence.csv`, or touch dashboard/frontend files.

It only writes:

- `data/historical_cases/project_status_snapshot.md`

Use the snapshot as a restart aid, not as an adjudication record.
