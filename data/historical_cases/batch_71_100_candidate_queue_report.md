# Batch 71 100 Candidate Queue Report

Generated: 2026-05-16

Candidate selection only. No cases adjudicated. No classifications changed.
No cases marked VERIFIED or CALIBRATION_ELIGIBLE.

---

## Summary

| Metric | Value |
|---|---|
| Target case count | 200 |
| Current confirmed cases | 70 |
| Cases needed to reach 200 | 130 |
| This batch target | 30 cases (cases 71–100) |
| Candidates selected from local universe | 26 |
| Candidates excluded (already covered or filtered) | 36 |
| Gap — additional candidates needed from external discovery | 4 |
| Cases still needed after this batch completes | 104 |
| Projected completion after batch | 96/200 (48.0%) |

---

## Discovery Gap

**Local universe provides 26 of 30 candidates needed for this batch.**
4 additional candidate(s) must come from one of:

1. **EDGAR universe expansion** — add 2024–2025 acquisitions to `resolved_case_candidates.csv`
2. **FMP live discovery** — set `allow_fmp_discovery: true` in `configs/case_factory.yaml`
3. **Manual seed** — add confirmed public-company acquisitions from external M&A databases

> **Do not enable FMP live discovery until EDGAR/source evidence confirms each candidate.**
> **Do not add candidates that are asset transactions, SPAC mergers, or reverse mergers.**

---

## Selected Candidates

| # | candidate_id | ticker | company | year | confidence | needs_backfill | action |
|---|---|---|---|---|---|---|---|
| 71 | RHC-0104-ACQUIRED-ALBO | ALBO | Albireo Pharma | 2023 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 72 | RHC-0101-ACQUIRED-CHMA | CHMA | Chiasma | 2021 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 73 | RHC-0102-ACQUIRED-CNST | CNST | Constellation Pharmaceuticals | 2021 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 74 | RHC-0134-ACQUIRED-ENLV | ENLV | Enliven Therapeutics | 2023 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 75 | RHC-0072-ACQUIRED-FATE | FATE | Fate Therapeutics | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 76 | RHC-0073-ACQUIRED-FUSN | FUSN | Fusion Pharmaceuticals Inc. | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 77 | RHC-0074-ACQUIRED-G1T | G1T | G1 Therapeutics | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 78 | RHC-0075-ACQUIRED-GRCL | GRCL | Gracell Biotechnologies | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 79 | RHC-0135-ACQUIRED-HRMY | HRMY | Harmony Biosciences | 2023 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 80 | RHC-0105-ACQUIRED-HZNP | HZNP | Horizon Therapeutics plc | 2023 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 81 | RHC-0137-ACQUIRED-KPTI | KPTI | Karyopharm Therapeutics | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 82 | RHC-0138-ACQUIRED-KROS | KROS | Keros Therapeutics | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 83 | RHC-0076-ACQUIRED-KRTX | KRTX | Karuna Therapeutics, Inc. | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 84 | RHC-0077-ACQUIRED-LBPH | LBPH | Longboard Pharmaceuticals, Inc. | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 85 | RHC-0131-ACQUIRED-LMNX | LMNX | Luminex Corporation | 2021 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 86 | RHC-0109-ACQUIRED-MOR | MOR | MorphoSys AG | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 87 | RHC-0078-ACQUIRED-MORF | MORF | Morphic Holding, Inc. | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 88 | RHC-0079-ACQUIRED-MRTX | MRTX | Mirati Therapeutics, Inc. | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 89 | RHC-0106-ACQUIRED-SGEN | SGEN | Seagen Inc. | 2023 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 90 | RHC-0107-ACQUIRED-SNDX | SNDX | Syndax Pharmaceuticals | 2023 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 91 | RHC-0103-ACQUIRED-STML | STML | Stemline Therapeutics | 2021 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 92 | RHC-0136-ACQUIRED-SYNH | SYNH | Syneos Health, Inc. | 2023 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 93 | RHC-0132-ACQUIRED-TBIO | TBIO | Translate Bio | 2021 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 94 | RHC-0139-ACQUIRED-TGTX | TGTX | TG Therapeutics | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 95 | RHC-0108-ACQUIRED-VECT | VECT | VectivBio Holding | 2023 | LOW | TRUE | DATE_BACKFILL_REQUIRED |
| 96 | RHC-0140-ACQUIRED-VSTM | VSTM | Verastem Oncology | 2024 | LOW | TRUE | DATE_BACKFILL_REQUIRED |

---

## Pre-Work Required Before Filing Collection

All candidates in this queue require date backfill before filing collection can run.
Filing collection is OFF by default (`collect_filings: false` in config).

### Step sequence:

```bash
# Step 1 — Select candidates (already done by running this script)
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --select-next-batch

# Step 2 — Date prefill work queue
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --run-step date-prefill --start 71 --limit 30

# Step 3 — Exception queue (after dates are resolved in acquisition_announcement_dates.csv)
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --run-step exception-queue --start 71 --limit 30

# Step 4 — Review packet for manual adjudication
python3 src/historical_case_tools/case_factory_orchestrator.py \
  --config configs/case_factory.yaml --write-review-packets --start 71 --limit 30
```

---

## Safety Constraints

- No automatic adjudication.
- No VERIFIED flag.
- No CALIBRATION_ELIGIBLE flag.
- No alpha claims.
- FMP live discovery is OFF unless explicitly enabled in `configs/case_factory.yaml`.
- Filing collection is OFF unless `collect_filings: true` is set in config.
- EDGAR/source-backed evidence remains the source of truth for all classifications.
- FMP is context only — not classification.
