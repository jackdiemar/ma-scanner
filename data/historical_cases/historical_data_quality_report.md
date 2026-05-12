# Historical pipeline data quality audit

- Generated (UTC): `2026-05-12T02:24:17Z`
- Data directory: `/Users/jack/Downloads/ma-scanner/data/historical_cases`

## Severity counts

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 8 |
| MEDIUM | 30 |
| LOW | 44 |
| INFO | 2 |

## Outputs

- `historical_data_quality_issues.csv` — one row per finding
- This report — summary and top priorities

## Top 20 priority issues

1. **[HIGH]** `CROSS_CASE_ID` — cases_seed case_id HARP-2023-001 != verification_working_queue case_id_current HARP-2020-001
   - File: `cross_file` row aggregate entity `HARP` field `case_id`

2. **[HIGH]** `MISSING_REQUIRED` — Missing or empty required field per schema.json: deal_type
   - File: `cases_seed.csv` row 4 entity `GNCA-2022-001` field `deal_type`

3. **[HIGH]** `MISSING_REQUIRED` — Missing or empty required field per schema.json: deal_type
   - File: `cases_seed.csv` row 8 entity `CRBP-2022-001` field `deal_type`

4. **[HIGH]** `MISSING_REQUIRED` — Missing or empty required field per schema.json: deal_type
   - File: `cases_seed.csv` row 9 entity `MGTA-2022-001` field `deal_type`

5. **[HIGH]** `MISSING_REQUIRED` — Missing or empty required field per schema.json: deal_type
   - File: `cases_seed.csv` row 10 entity `RIGL-2020-001` field `deal_type`

6. **[HIGH]** `MISSING_REQUIRED` — Missing or empty required field per schema.json: deal_type
   - File: `cases_seed.csv` row 11 entity `VNDA-2021-001` field `deal_type`

7. **[HIGH]** `MISSING_REQUIRED` — Missing or empty required field per schema.json: deal_type
   - File: `cases_seed.csv` row 14 entity `SURF-2022-001` field `deal_type`

8. **[HIGH]** `MISSING_REQUIRED` — Missing or empty required field per schema.json: deal_type
   - File: `cases_seed.csv` row 15 entity `PTGX-2022-001` field `deal_type`

9. **[MEDIUM]** `DUP_TICKER_OUTCOME` — Duplicate rows for same ticker+outcome (2 rows)
   - File: `resolved_case_candidates.csv` row aggregate entity `RXDX|ACQUIRED` field `ticker+likely_outcome_type`

10. **[MEDIUM]** `DUP_TICKER_OUTCOME` — Duplicate rows for same ticker+outcome (2 rows)
   - File: `resolved_case_candidates.csv` row aggregate entity `DOVA|ACQUIRED` field `ticker+likely_outcome_type`

11. **[MEDIUM]** `DUP_TICKER_OUTCOME` — Duplicate rows for same ticker+outcome (2 rows)
   - File: `resolved_case_candidates.csv` row aggregate entity `DCPH|ACQUIRED` field `ticker+likely_outcome_type`

12. **[MEDIUM]** `DUP_TICKER_OUTCOME` — Duplicate rows for same ticker+outcome (2 rows)
   - File: `resolved_case_candidates.csv` row aggregate entity `CRBP|FAILED_REVIEW` field `ticker+likely_outcome_type`

13. **[MEDIUM]** `DUP_TICKER_OUTCOME` — Duplicate rows for same ticker+outcome (2 rows)
   - File: `resolved_case_candidates.csv` row aggregate entity `SURF|REVERSE_MERGER` field `ticker+likely_outcome_type`

14. **[MEDIUM]** `NAME_MISMATCH` — Multiple normalized company strings for same ticker across pipeline files
   - File: `cross_file` row aggregate entity `RXDX` field `company`
   - Detail: ignyta | prometheus biosciences

15. **[MEDIUM]** `NAME_MISMATCH` — Multiple normalized company strings for same ticker across pipeline files
   - File: `cross_file` row aggregate entity `BHVN` field `company`
   - Detail: biohaven | biohaven pharmaceutical

16. **[MEDIUM]** `OUTCOME_YEAR_MISSING` — likely_outcome_type set but likely_outcome_year not a 4-digit year
   - File: `resolved_case_candidates.csv` row 114 entity `RHC-0113-FAILED_REVIEW-CRBP` field `likely_outcome_year`

17. **[MEDIUM]** `OUTCOME_YEAR_MISSING` — likely_outcome_type set but likely_outcome_year not a 4-digit year
   - File: `resolved_case_candidates.csv` row 115 entity `RHC-0114-FAILED_REVIEW-RIGL` field `likely_outcome_year`

18. **[MEDIUM]** `OUTCOME_YEAR_MISSING` — likely_outcome_type set but likely_outcome_year not a 4-digit year
   - File: `resolved_case_candidates.csv` row 116 entity `RHC-0115-FAILED_REVIEW-VNDA` field `likely_outcome_year`

19. **[MEDIUM]** `OUTCOME_YEAR_MISSING` — likely_outcome_type set but likely_outcome_year not a 4-digit year
   - File: `resolved_case_candidates.csv` row 126 entity `RHC-0125-REVERSE_MERGER-SURF` field `likely_outcome_year`

20. **[MEDIUM]** `PLACEHOLDER_DATE` — Placeholder or VERIFY_REQUIRED in date-like field: VERIFY_REQUIRED
   - File: `cases_seed.csv` row 2 entity `HARP-2023-001` field `source_filing_date`

## Suggested next cleanup task

Reconcile **CROSS_CASE_ID** (queue vs `cases_seed`) and backfill schema-required fields such as **deal_type** where rows are otherwise structured, then clear **PLACEHOLDER_DATE** / **PRICE_WITHOUT_OBS_DATE** so evidence, prices, and case IDs line up.
