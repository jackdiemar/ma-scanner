# Batch 51-70 Queue Summary Helper

Status: read-only helper.

## Purpose

`src/historical_case_tools/batch_51_70_queue_summary.py` summarizes the Batch 51-70 exception queue and filing-collection workload after filing collection has run.

It is meant to answer one operational question: what should be reviewed first?

The helper does not adjudicate cases, edit `source_evidence.csv`, change classifications, regenerate packets, or mark anything `VERIFIED` or `CALIBRATION_ELIGIBLE`.

## Command

```bash
python3 src/historical_case_tools/batch_51_70_queue_summary.py
```

The command prints a compact terminal summary and writes:

```text
data/historical_cases/batch_51_70_queue_summary.md
```

## Inputs

The script reads:

- `data/historical_cases/batch_51_70_exception_queue.csv`
- `data/historical_cases/batch_51_70_source_evidence_draft.csv`
- `data/historical_cases/batch_51_70_pre_announcement_filing_targets.csv`

## Output Sections

The markdown report includes:

- Total cases.
- Total filing targets.
- Total possible hits from the queue.
- Possible-hit filing rows needing context checks.
- Tier distribution.
- P1/P3 case list.
- P6 cases with low-value or non-adjudicated hits.
- P6 true no-hit cases.
- Recommended review order.
- Warning that the script does not adjudicate.

## Review Use

Use the output as a queue-control view before manual review:

1. Review P1 cases first.
2. Review P3 Item 4 cases next.
3. Use P6 hit counts only as workload flags, not as signal classifications.
4. Promote evidence into `source_evidence.csv` only after source-backed human review.

The helper is intentionally narrow so it can be rerun during Batch 51-70 review without interfering with Claude's adjudication work.
