# Current Project Handoff Status

Generated: 2026-05-15

## Current Research Milestone

The first 50-case biotech acquisition prior-signal study is complete.

Final distribution:

| Status | Count |
|---|---:|
| TRUE_PUBLIC_PRIOR_SIGNAL | 3 |
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 35 |
| PRIVATE_BACKGROUND_ONLY | 9 |
| ASSET_SPECIFIC_RIGHTS_ONLY | 2 |
| RIGHTS_LANGUAGE_ONLY | 1 |
| DATE_MISSING | 0 |

## Key Commits

- `e5f701b` Fix PTLA acquisition year in resolved candidates
- `335003c` Add live monitoring protocol and starter log
- `72f50af` Add 8-K catchability review and commercialization roadmap
- `c88bc21` Add Batch 51-70 acceleration plan
- `25a11f2` Add Batch 51-70 acceleration queues
- `5c346ed` Add unsolicited/superior proposal phrases to 8-K signal detection

## What The First 50 Proved

- Public prior process signals exist, but they are rare.
- The evidence-backed true-signal cases are MDVN, DMTX, and TSRO.
- False-positive rules are now grounded in source-reviewed historical cases.
- The project should be framed as strategic-process intelligence and workflow compression, not M&A prediction.

## Batch 51-70 Current State

- Batch 51-70 acceleration scripts exist.
- All 20 cases were initially blocked because acquisition announcement dates were missing.
- Claude is working on acquisition announcement date backfill.
- After date backfill, rerun the queue scripts, then run pre-announcement filing collection.

## Next Steps

1. Finish Batch 51-70 date backfill.
2. Rerun queue scripts.
3. Run the pre-announcement filing collector.
4. Build the exception queue.
5. Adjudicate only high-priority exceptions.
6. Update the batch distribution.
7. Decide whether the factory is fast enough to scale to 100.

## Do Not Do Yet

- Do not scale to 100.
- Do not mark cases `VERIFIED`.
- Do not mark cases `CALIBRATION_ELIGIBLE`.
- Do not claim alpha.
- Do not pitch this as M&A prediction.
- Do not overhaul the dashboard before live monitoring proof exists.

## Practical Resume Point

- Built a source-backed biotech strategic-process intelligence workflow that converts SEC filings and historical acquisition evidence into auditable process-signal classifications, false-positive rules, and daily monitoring infrastructure.
