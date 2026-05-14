# Pipeline Sanity Snapshot

Run date: 2026-05-14

Fast read-only snapshot of whether the historical case factory pieces line up logically. Adjudication files are intentionally not read because Claude is working that queue.

## Status

- Sanity status: **WARN**
- Anything appears to threaten the 50-case study: NO
- Pipeline order coherent through hits stage: YES

## Core Counts

- Acquisition candidates: 105
- Cases with announcement dates: 41
- Cases with source evidence: 37
- Cases with pre-announcement filing targets: 15
- Cases with possible pre-announcement hits: 4

## Announcement Confidence

| Confidence | Cases |
|---|---:|
| HIGH | 39 |
| MEDIUM | 1 |
| MISSING | 65 |

## Alignment Risks

| Risk | Cases |
|---|---:|
| announcement_date_without_evidence | 21 |
| evidence_without_announcement_date | 9 |

## Pipeline Order

| Stage | Case count | Note |
|---|---:|---|
| candidate | 105 | Acquired rows in resolved_case_candidates.csv |
| announcement date | 41 | Cases with date rows |
| filing targets | 15 | Cases with pre-announcement filing target rows |
| hits | 4 | Cases with possible signal-hit rows |
| adjudication | not inspected | Protected while Claude adjudicates NEEDS_MANUAL_REVIEW cases |

## Biggest Alignment Risks

- announcement_date_without_evidence: 21
- evidence_without_announcement_date: 9

## Cases Needing Attention

| Case ID | Ticker | Status | Risks | Threatens 50-case study |
|---|---|---|---|---|
| RHC-0001-ACQUIRED-NPSP | NPSP | WARN | evidence_without_announcement_date | FALSE |
| RHC-0002-ACQUIRED-PCYC | PCYC | WARN | evidence_without_announcement_date | FALSE |
| RHC-0003-ACQUIRED-ZSPH | ZSPH | WARN | evidence_without_announcement_date | FALSE |
| RHC-0004-ACQUIRED-ANAC | ANAC | WARN | evidence_without_announcement_date | FALSE |
| RHC-0005-ACQUIRED-CPXX | CPXX | WARN | announcement_date_without_evidence | FALSE |
| RHC-0007-ACQUIRED-RLYP | RLYP | WARN | announcement_date_without_evidence | FALSE |
| RHC-0008-ACQUIRED-TBRA | TBRA | WARN | evidence_without_announcement_date | FALSE |
| RHC-0009-ACQUIRED-VTAE | VTAE | WARN | announcement_date_without_evidence | FALSE |
| RHC-0010-ACQUIRED-ARIA | ARIA | WARN | evidence_without_announcement_date | FALSE |
| RHC-0011-ACQUIRED-CLCD | CLCD | WARN | announcement_date_without_evidence | FALSE |
| RHC-0012-ACQUIRED-DMTX | DMTX | WARN | announcement_date_without_evidence | FALSE |
| RHC-0013-ACQUIRED-KITE | KITE | WARN | evidence_without_announcement_date | FALSE |
| RHC-0014-ACQUIRED-AVXS | AVXS | WARN | announcement_date_without_evidence | FALSE |
| RHC-0015-ACQUIRED-BIVV | BIVV | WARN | evidence_without_announcement_date | FALSE |
| RHC-0016-ACQUIRED-CASC | CASC | WARN | announcement_date_without_evidence | FALSE |
| RHC-0017-ACQUIRED-JUNO | JUNO | WARN | evidence_without_announcement_date | FALSE |
| RHC-0018-ACQUIRED-RXDX | RXDX | WARN | announcement_date_without_evidence | FALSE |
| RHC-0019-ACQUIRED-ALDR | ALDR | WARN | announcement_date_without_evidence | FALSE |
| RHC-0020-ACQUIRED-ARRY | ARRY | WARN | announcement_date_without_evidence | FALSE |
| RHC-0021-ACQUIRED-CMTA | CMTA | WARN | announcement_date_without_evidence | FALSE |
| RHC-0022-ACQUIRED-LOXO | LOXO | WARN | announcement_date_without_evidence | FALSE |
| RHC-0023-ACQUIRED-NITE | NITE | WARN | announcement_date_without_evidence | FALSE |
| RHC-0024-ACQUIRED-ONCE | ONCE | WARN | announcement_date_without_evidence | FALSE |
| RHC-0029-ACQUIRED-FTSV | FTSV | WARN | announcement_date_without_evidence | FALSE |
| RHC-0031-ACQUIRED-MYOK | MYOK | WARN | announcement_date_without_evidence | FALSE |
| RHC-0033-ACQUIRED-PRNB | PRNB | WARN | announcement_date_without_evidence | FALSE |
| RHC-0035-ACQUIRED-ADMS | ADMS | WARN | announcement_date_without_evidence | FALSE |
| RHC-0042-ACQUIRED-PTLA | PTLA | WARN | announcement_date_without_evidence | FALSE |
| RHC-0043-ACQUIRED-TRIL | TRIL | WARN | announcement_date_without_evidence | FALSE |
| RHC-0045-ACQUIRED-XLRN | XLRN | WARN | announcement_date_without_evidence | FALSE |

## Outputs

- `data/historical_cases/pipeline_sanity_snapshot.csv`
- `data/historical_cases/pipeline_sanity_snapshot.md`
