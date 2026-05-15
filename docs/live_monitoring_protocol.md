# Live Monitoring Protocol

Status: Active protocol  
Started: 2026-05-15  
System: MA Scanner V12  

## Purpose

The live monitoring record is the sellable evidence layer for MA Scanner. It should show, day by day, which companies were monitored, which filings arrived, which signals fired, which alerts were accepted or rejected, and the source-backed reason for each decision.

This is not a prediction log. It is an audit trail for strategic-process intelligence.

## Core Standard

Every alert must answer five questions:

1. Which company was monitored?
2. What source filing or public source changed?
3. What signal fired?
4. Was the alert accepted, rejected, or left open?
5. Why did that decision matter?

If an alert cannot be tied to a source URL, accession number, or reviewable excerpt, it should not be treated as evidence.

## Log File

Primary log:

`data/live_monitoring/live_monitoring_log.csv`

Use one row per monitored company per day for coverage, and one row per filing or alert decision when something changes.

Required `record_type` values:

- `DAILY_COVERAGE`: confirms the company was included in that day's monitored universe, even if no filing arrived.
- `FILING_REVIEW`: records each new filing reviewed.
- `ALERT_DECISION`: records accepted, rejected, or open alert decisions.
- `FOLLOW_UP`: records later outcome checks or changes in interpretation.

## Daily Workflow

1. Run the V12 scanner or load the latest completed V12 scan.
2. Record the monitored universe with `DAILY_COVERAGE` rows.
3. Review new filings for companies that are in active monitoring or that newly enter a process state.
4. For each filing reviewed, add a `FILING_REVIEW` row with source URL, filing type, accession number if available, and the scanner signal.
5. For each signal, add an `ALERT_DECISION` row:
   - `ACCEPTED` if the source supports real process evidence.
   - `REJECTED` if it is boilerplate, score-only, stale, governance-only, asset-specific, or otherwise not actionable process evidence.
   - `OPEN_REVIEW` if source text needs manual review before a decision.
6. Write the plain-English reason in `decision_reason`.
7. Write why the alert matters or does not matter in `matters_because` or `rejected_because`.
8. Add source links every time. No source link means no evidence.

## Accepted Alert Standard

Accepted alerts should usually contain at least one of:

- Public strategic review or alternatives language that is not boilerplate.
- Sale-pressure 13D Item 4 language.
- Board/advisor/process language tied to a company-level transaction.
- Whole-company ROFR, ROFN, acquisition option, or matching-right pathway.
- A meaningful process-state escalation, such as `SCREENING` to `LIVE` or `PATHWAY`.
- A fresh sequence pattern that is source-backed and not merely score movement.

Accepted does not mean buy, deal likely, or verified outcome. It means the filing deserves analyst attention.

## Rejection Standard

Reject alerts when the source is:

- `SCORE_ONLY`.
- Boilerplate strategic alternatives language.
- Governance-only, passive, or capital-allocation 13D language.
- Generic legal rights language.
- Asset-specific rights without a whole-company pathway.
- Post-announcement background that was not public before announcement.
- Stale signal reuse without new source evidence.
- Missing source URL or accession reference.

Rejected alerts are valuable. They become the false-positive library.

## Minimum Daily Summary

At the end of each monitoring day, the log should support this summary:

- Companies monitored.
- New filings reviewed.
- Signals fired.
- Alerts accepted.
- Alerts rejected.
- Open manual reviews.
- Most important source links.
- Changes in process state.
- Follow-up actions.

## Commercial Use

This log is the proof layer for diligence conversations. It demonstrates that MA Scanner can:

- Show continuous monitoring coverage.
- Preserve exact source evidence.
- Separate real process signals from noise.
- Build a dated false-positive dataset.
- Explain why a signal mattered in institutional language.
- Track live process evolution before outcomes are known.

The product becomes more credible as the log compounds.
