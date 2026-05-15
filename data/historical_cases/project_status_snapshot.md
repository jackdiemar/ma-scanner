# Project Status Snapshot

Generated: 2026-05-15 11:20:39 CDT

## Git

- Branch: main

### git status --short

```text
?? data/historical_cases/project_status_snapshot.md
?? docs/project_status_snapshot.md
?? scripts/project_status_snapshot.sh
```

### Latest 12 Commits

```text
543cfd3 Fix Batch 51-70 queue hit counts
e52dea8 Adjudicate Batch 51-70 high-priority cases
341658b Add Batch 51-70 queue summary helper
3217b86 Add Batch 51-70 filing collection outputs
d40a6d2 Add FMP candidate discovery stub
f4aab80 Add five-year acquisition universe builder
0863b1e Add Batch 51-70 adjudication playbook
a9ef49a Backfill acquisition announcement dates for Batch 51-70
d134cf1 Document FMP integration opportunities
ebc8121 Add EDGAR source pull helper
46b6e83 Add current project handoff status
25a11f2 Add Batch 51-70 acceleration queues
```

## Batch 51-70 File Check

- PRESENT: `data/historical_cases/batch_51_70_exception_queue.csv`
- PRESENT: `data/historical_cases/batch_51_70_queue_summary.md`
- PRESENT: `data/historical_cases/batch_51_70_filing_collection_report.md`
- PRESENT: `data/historical_cases/batch_51_70_source_evidence_draft.csv`
- PRESENT: `data/historical_cases/batch_51_70_high_priority_adjudication_report.md`
- MISSING: `data/historical_cases/batch_51_70_p6_adjudication_report.md`

## FMP And Universe File Check

- PRESENT: `docs/fmp_integration_opportunities.md`
- PRESENT: `docs/fmp_candidate_discovery_stub.md`
- PRESENT: `src/historical_case_tools/five_year_acquisition_universe_builder.py`
- PRESENT: `data/historical_cases/five_year_acquisition_universe_candidates.csv`
- PRESENT: `src/historical_case_tools/fmp_candidate_discovery_stub.py`
- PRESENT: `data/historical_cases/fmp_candidate_discovery_stub_report.md`

## Current Research Status

- First 50-case prior-signal study: complete.
- First 50 final distribution: TRUE_PUBLIC_PRIOR_SIGNAL 3, DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE 35, PRIVATE_BACKGROUND_ONLY 9, ASSET_SPECIFIC_RIGHTS_ONLY 2, RIGHTS_LANGUAGE_ONLY 1, DATE_MISSING 0.
- Batch 51-70 announcement dates: complete.
- Batch 51-70 filing collection: complete.
- Batch 51-70 high-priority review: complete.
- High-priority review result: 0 TRUE_PUBLIC_PRIOR_SIGNAL.
- Remaining Batch 51-70 work: P6 possible-hit adjudication, no-hit baseline finalization, final batch report.
- FMP integration plan: exists.
- Five-year acquisition universe builder: exists.
- FMP candidate discovery stub: exists, but live API is not enabled.

## Batch 51-70 Queue Summary

## Summary

- Total cases: 20
- Total filing targets: 509
- Total possible hits from queue: 28
- Possible-hit filing rows needing context checks: 21
- Draft source-evidence rows pending review: 5

Possible-hit filing rows are counted from `batch_51_70_pre_announcement_filing_targets.csv` where `recommended_status` is `POSSIBLE_HIT`. The exception queue's `signal_hit_count` is retained as queue metadata, but it is not used to split P6 cases.

## Tier Distribution

- P1: 2
- P3: 3
- P6: 15


## Remaining Known Work

1. Finish Batch 51-70 P6 possible-hit adjudication.
2. Finalize true no-hit P6 baseline cases after coverage check.
3. Build final Batch 51-70 distribution/report.
4. Decide whether the historical factory is fast enough to scale toward 100 cases.
5. Keep FMP as discovery/context only until EDGAR/source-backed evidence confirms candidates.

## Do Not Touch Without Explicit Direction

- Do not edit `source_evidence.csv` while adjudication is active.
- Do not edit active Batch 51-70 adjudication outputs.
- Do not mark `VERIFIED`.
- Do not mark `CALIBRATION_ELIGIBLE`.
- Do not claim alpha.
- Do not pitch this as M&A prediction.
- Do not touch dashboard/frontend.
- Do not run the full scanner for this snapshot.

## Next Recommended Command Sequence

```bash
git status --short
python3 src/historical_case_tools/batch_51_70_queue_summary.py
sed -n '1,220p' data/historical_cases/batch_51_70_queue_summary.md
# After Claude finishes P6 adjudication, review the P6 report and then build the final Batch 51-70 report.
```
