# Batch 71 100 Date Backfill Report

Generated: 2026-05-16

---

## Summary

| Metric | Count |
|---|---|
| Candidates attempted | 10 |
| Dates found (HIGH/MEDIUM) | 0 |
| Not resolved | 10 |
| Already had date (skipped) | 16 |
| New rows written → acquisition_announcement_dates.csv | 0 |
| New rows written → source_evidence.csv | 0 |

---

## Dates Found

No dates found in this run.

---

## Unresolved (manual backfill required)

| Ticker | Status | Reason |
|---|---|---|
| ENLV | NOT_FOUND | No Item 1.01 8-K in 2021–2023 |
| FATE | LOW_CONFIDENCE | Found 5 Item 1.01 8-K(s) in range; best=2024-08-30; EX-2.x=NO; confidence=LOW |
| GRCL | NOT_FOUND | No Item 1.01 8-K in 2022–2024 |
| HRMY | LOW_CONFIDENCE | Found 3 Item 1.01 8-K(s) in range; best=2023-09-25; EX-2.x=NO; confidence=LOW |
| KPTI | LOW_CONFIDENCE | Found 3 Item 1.01 8-K(s) in range; best=2024-11-08; EX-2.x=NO; confidence=LOW |
| LMNX | NOT_FOUND | CIK lookup failed |
| MOR | NOT_FOUND | No Item 1.01 8-K in 2022–2024 |
| SYNH | LOW_CONFIDENCE | Found 7 Item 1.01 8-K(s) in range; best=2023-09-28; EX-2.x=NO; confidence=LOW |
| TGTX | LOW_CONFIDENCE | Found 4 Item 1.01 8-K(s) in range; best=2024-08-06; EX-2.x=NO; confidence=LOW |
| VECT | NOT_FOUND | No Item 1.01 8-K in 2021–2023 |

Use EDGAR URLs in `batch_N_M_date_prefill_queue.csv` to resolve manually.
Record dates in `acquisition_announcement_dates.csv` with `confidence=HIGH`.

---

## Skipped (already have confirmed dates)

| Ticker |
|---|
| ALBO |
| CHMA |
| CNST |
| FUSN |
| G1T |
| HZNP |
| KROS |
| KRTX |
| LBPH |
| MORF |
| MRTX |
| SGEN |
| SNDX |
| STML |
| TBIO |
| VSTM |

---

## Safety

- No classifications changed.
- No adjudication performed.
- No VERIFIED flag set.
- No CALIBRATION_ELIGIBLE flag set.
- Only EDGAR submissions JSON used. No FMP. No live scanner.
