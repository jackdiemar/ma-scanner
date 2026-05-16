# Case Factory: 200-Case Operational Plan

Generated: 2026-05-16

Status: active plan. Updated by orchestrator on each run.

---

## Current Snapshot

| Field | Value |
|---|---|
| Confirmed cases | 70 |
| Target | 200 |
| Remaining | 130 |
| Combined signal rate | 3/70 (4.3%) |
| State file | data/historical_cases/case_factory_state.json |
| Config | configs/case_factory.yaml |

---

## Completed Through Case 70

### First 50 (cases 1–50) — FINALIZED 2026-05-14

| Classification | Count | Pct |
|---|---|---|
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 35 | 70% |
| PRIVATE_BACKGROUND_ONLY | 9 | 18% |
| TRUE_PUBLIC_PRIOR_SIGNAL | 3 | 6% |
| ASSET_SPECIFIC_RIGHTS_ONLY | 2 | 4% |
| RIGHTS_LANGUAGE_ONLY | 1 | 2% |

True signals: MDVN (unsolicited proposal, 116d), DMTX (superior proposal, 39d), TSRO (media report, 17d).

### Batch 51–70 (cases 51–70) — FINALIZED 2026-05-15

| Classification | Count | Pct |
|---|---|---|
| DEAL_ANNOUNCEMENT_BASELINE_CANDIDATE | 11 | 55% |
| RIGHTS_LANGUAGE_ONLY | 7 | 35% |
| ASSET_SPECIFIC_RIGHTS_ONLY | 2 | 10% |
| TRUE_PUBLIC_PRIOR_SIGNAL | 0 | 0% |

Filing coverage: 508 filings across 19 EDGAR-covered cases. BLU (FPI) had no target-form coverage.

---

## Candidate Availability

| Source | Available now | Notes |
|---|---|---|
| Local universe (MAYBE_NEEDS_REVIEW) | 26 | All need date backfill |
| Total needed for 200 | 130 | — |
| **Gap requiring external discovery** | **~104** | FMP or EDGAR expansion |

### Batch 71–100 candidate pool (26 of 30 needed locally)

| Ticker | Year | Needs backfill |
|---|---|---|
| CHMA | 2021 | YES |
| CNST | 2021 | YES |
| LMNX | 2021 | YES |
| STML | 2021 | YES |
| TBIO | 2021 | YES |
| ALBO | 2023 | YES |
| ENLV | 2023 | YES |
| HRMY | 2023 | YES |
| HZNP | 2023 | YES |
| RXDX | 2023 | YES |
| SGEN | 2023 | YES |
| SNDX | 2023 | YES |
| SYNH | 2023 | YES |
| VECT | 2023 | YES |
| FATE | 2024 | YES |
| FUSN | 2024 | YES |
| G1T | 2024 | YES |
| GRCL | 2024 | YES |
| KPTI | 2024 | YES |
| KROS | 2024 | YES |
| KRTX | 2024 | YES |
| LBPH | 2024 | YES |
| MOR | 2024 | YES |
| MORF | 2024 | YES |
| MRTX | 2024 | YES |
| TGTX | 2024 | YES |
| VSTM | 2024 | YES |

4 additional candidates needed from external discovery to complete batch 71–100.

---

## Batch Sequence to 200

| Batch | Cases | Target size | Local available | Gap |
|---|---|---|---|---|
| batch_71_100 | 71–100 | 30 | ~26 | ~4 |
| batch_101_130 | 101–130 | 30 | 0 | 30 (needs discovery) |
| batch_131_160 | 131–160 | 30 | 0 | 30 (needs discovery) |
| batch_161_190 | 161–190 | 30 | 0 | 30 (needs discovery) |
| batch_191_200 | 191–200 | 10 | 0 | 10 (needs discovery) |

---

## Discovery Sources Required

### To close gap for batch 71–100 (4 candidates)

1. Expand `resolved_case_candidates.csv` with additional 2021–2024 acquisitions
2. Run five_year_acquisition_universe_builder.py again
3. If still short: enable `allow_fmp_discovery: true` and run fmp_candidate_discovery_stub.py

### To reach 200 (104 candidates beyond batch_71_100)

FMP live discovery will likely be required. Steps:
1. Set `allow_fmp_discovery: true` in `configs/case_factory.yaml`
2. Ensure `FMP_API_KEY` is in `config/.env`
3. Run `src/historical_case_tools/fmp_candidate_discovery_stub.py`
4. Each FMP-discovered candidate must be confirmed with EDGAR/source evidence

---

## Commands to Start Batch 71–100

```bash
# 1. Check status
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --status

# 2. Select candidates
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --select-next-batch

# 3. Date prefill queue
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --run-step date-prefill --start 71 --limit 30

# [Manual: resolve BLOCKED dates in acquisition_announcement_dates.csv]

# 4. Exception queue
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --run-step exception-queue --start 71 --limit 30

# 5. Review packet
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --write-review-packets --start 71 --limit 30

# [Manual: adjudicate P1/P2/P3/P4 cases following adjudication playbook]
# [Manual: spot-check P6 cases]
# [Manual: write batch_71_100_final_summary.md]
```

---

## Quality Rules

- EDGAR/source-backed evidence is the source of truth.
- FMP = discovery and context only. Not classification.
- No post-announcement proxy background as prior public signal.
- No generic ROFR as process evidence.
- No asset-specific rights as company-level evidence.
- No private offers unless publicly disclosed before announcement.
- No VERIFIED. No CALIBRATION_ELIGIBLE. No alpha claims.

*This file is read-only documentation. No cases adjudicated.*
