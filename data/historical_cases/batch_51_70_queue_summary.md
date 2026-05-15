# Batch 51-70 Queue Summary

Generated: 2026-05-15

Status: read-only workload summary. This script does not adjudicate cases, edit `source_evidence.csv`, or change classifications.

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

## P1/P3 Case List

| tier | case_id | ticker | company | signal_hit_count | reason |
| --- | --- | --- | --- | --- | --- |
| P1 | RHC-0061-ACQUIRED-DICE | DICE | DICE Therapeutics, Inc. | 1 | Explicit process language: acquisition_proposal. |
| P1 | RHC-0055-ACQUIRED-OYST | OYST | Oyster Point Pharma | 3 | Explicit process language: acquisition_proposal. |
| P3 | RHC-0067-ACQUIRED-ALPN | ALPN | Alpine Immune Sciences, Inc. | 1 | SC 13D filing found - verify Item 4 for acquisition-pressure language. |
| P3 | RHC-0054-ACQUIRED-IMGO | IMGO | Imago BioSciences | 1 | SC 13D filing found - verify Item 4 for acquisition-pressure language. |
| P3 | RHC-0056-ACQUIRED-SRRA | SRRA | Sierra Oncology | 1 | SC 13D filing found - verify Item 4 for acquisition-pressure language. |

## P6 Cases With Hits

These are still P6 cases. The possible-hit rows indicate low-value or non-adjudicated phrase workload, not a true prior signal.

| case_id | ticker | company | signal_phrase_types | signal_hit_count | possible_hit_rows | next_action |
| --- | --- | --- | --- | --- | --- | --- |
| RHC-0051-ACQUIRED-EPZM | EPZM | Epizyme | rofr_rofn | 1 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0052-ACQUIRED-FMTX | FMTX | Forma Therapeutics Holdings, Inc. | sale_process | 4 | 4 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0053-ACQUIRED-GBT | GBT | Global Blood Therapeutics, Inc. | rofr_rofn | 1 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0057-ACQUIRED-TPTX | TPTX | Turning Point Therapeutics, Inc. | rofr_rofn | 1 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0059-ACQUIRED-CINC | CINC | CinCor Pharma, Inc. | sale_process | 3 | 3 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0064-ACQUIRED-RETA | RETA | Reata Pharmaceuticals, Inc. | rofr_rofn | 1 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0066-ACQUIRED-ZYNE | ZYNE | Zynerba Pharmaceuticals, Inc. | sale_process | 2 | 2 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0068-ACQUIRED-AMAM | AMAM | Ambrx Biopharma Inc. | option_to_acquire | 1 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |

## P6 True No-Hit Cases

| case_id | ticker | company | next_action |
| --- | --- | --- | --- |
| RHC-0058-ACQUIRED-BLU | BLU | BELLUS Health Inc. | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0060-ACQUIRED-CTIC | CTIC | CTI BioPharma | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0062-ACQUIRED-HARP | HARP | Harpoon Therapeutics | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0063-ACQUIRED-ISEE | ISEE | IVERIC bio, Inc. | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0069-ACQUIRED-CBAY | CBAY | CymaBay Therapeutics, Inc. | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0070-ACQUIRED-CERE | CERE | Cerevel Therapeutics Holdings, Inc. | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| RHC-0071-ACQUIRED-DCPH | DCPH | Deciphera Pharmaceuticals, Inc. | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |

## Recommended Review Order

| tier | ticker | case_id | filing_targets | possible_hit_rows | next_action |
| --- | --- | --- | --- | --- | --- |
| P1 | DICE | RHC-0061-ACQUIRED-DICE | 27 | 1 | Open filing links. Verify phrase context. Adjudicate case_level_true_signal. |
| P1 | OYST | RHC-0055-ACQUIRED-OYST | 26 | 3 | Open filing links. Verify phrase context. Adjudicate case_level_true_signal. |
| P3 | ALPN | RHC-0067-ACQUIRED-ALPN | 29 | 1 | Read SC 13D Item 4. Classify as acquisition pressure or governance. Adjudicate. |
| P3 | IMGO | RHC-0054-ACQUIRED-IMGO | 32 | 1 | Read SC 13D Item 4. Classify as acquisition pressure or governance. Adjudicate. |
| P3 | SRRA | RHC-0056-ACQUIRED-SRRA | 33 | 1 | Read SC 13D Item 4. Classify as acquisition pressure or governance. Adjudicate. |
| P6 | AMAM | RHC-0068-ACQUIRED-AMAM | 6 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | BLU | RHC-0058-ACQUIRED-BLU | 1 | 0 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | CBAY | RHC-0069-ACQUIRED-CBAY | 20 | 0 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | CERE | RHC-0070-ACQUIRED-CERE | 28 | 0 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | CINC | RHC-0059-ACQUIRED-CINC | 18 | 3 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | CTIC | RHC-0060-ACQUIRED-CTIC | 22 | 0 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | DCPH | RHC-0071-ACQUIRED-DCPH | 20 | 0 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | EPZM | RHC-0051-ACQUIRED-EPZM | 30 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | FMTX | RHC-0052-ACQUIRED-FMTX | 28 | 4 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | GBT | RHC-0053-ACQUIRED-GBT | 42 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | HARP | RHC-0062-ACQUIRED-HARP | 28 | 0 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | ISEE | RHC-0063-ACQUIRED-ISEE | 31 | 0 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | RETA | RHC-0064-ACQUIRED-RETA | 24 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | TPTX | RHC-0057-ACQUIRED-TPTX | 36 | 1 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |
| P6 | ZYNE | RHC-0066-ACQUIRED-ZYNE | 28 | 2 | No signal found. Mark DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE if filing coverage confirmed. |

## Warning

This summary is a workload view only. It does not classify cases, does not promote draft evidence into `source_evidence.csv`, and does not determine whether any case is `TRUE_PUBLIC_PRIOR_SIGNAL`.
