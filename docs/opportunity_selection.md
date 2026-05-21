# MA Scanner — Opportunity Selection and Discard Suppression

## Why This Exists

The AI email was repeatedly showing the same 10 already-announced DISCARD names. The AI
classified them correctly every time, but each scheduled run treated them as fresh cases,
sent them to the LLM, and included them in the email as top results.

This is a product problem: the AI filter works, but the product is not useful if every email
is a list of known dead cases.

---

## How Suppression Works

After the AI gate runs a decision, `suppression_registry.py` evaluates whether the case
should be suppressed from future email main sections.

A case enters suppression when:

1. `research_action = DISCARD` AND one of:
   - `classification = ALREADY_ANNOUNCED_DEAL`
   - `classification = FALSE_POSITIVE`
   - `classification = GENERIC_PARTNERSHIP_LANGUAGE`
   - `strategy_bucket` contains `already-announced`, `boilerplate`, `post-announcement`
   - `matched_false_positive_archetypes` contains `ALREADY_ANNOUNCED_MERGER`
2. Or: any DISCARD action (all discards are suppressed after first run)

The suppression record stores:
- `evidence_fingerprint` — hash of ticker + signal_type + source_url + accession + excerpt
- `source_fingerprint` — hash of source_url + accession + filing_date
- `signal_type`, `filing_date`, `source_url` — raw fields for unsuppression checks
- `times_seen` — how many times this exact evidence appeared
- `first_suppressed_at`, `last_seen_at`

State lives in: `data/ai_research/suppression_registry.json`

---

## What Unsuppresses a Case

A case is automatically unsuppressed (will re-enter main queue) if any of the following
changes from the stored record:

| Condition | Detection |
|---|---|
| New source URL or accession | `source_fingerprint` changes |
| New filing date | `filing_date` field changes |
| New signal type | `signal_type` field changes |
| Evidence content changed | `evidence_fingerprint` changes |
| Action improves (DISCARD → WATCH/ESCALATE) | `update_registry` removes record |
| Manual force | `--force-unsuppress TICKER` flag |

WATCH and ESCALATE cases are never added to suppression.

---

## Opportunity Queue

`opportunity_selector.py` builds a priority queue from decisions + registry:

| Tier | What goes here |
|---|---|
| P0_ESCALATE_NOW | Any ESCALATE action |
| P1_HUMAN_REVIEW | Any NEEDS_HUMAN_REVIEW action |
| P2_WATCHLIST_SETUP | WATCH/WAIT_FOR_PRICE on new or changed evidence |
| P3_MONITOR_CHANGE | WATCH on unchanged cases, or changed DISCARD |
| P4_SUPPRESSED | Repeated DISCARD with no evidence change |

Email main cards: P0 / P1 / P2 / P3 only.
P4 appears in a compact archive section at the bottom.

Output files (not committed):
- `data/ai_research/latest_opportunity_queue.json`
- `data/ai_research/latest_opportunity_queue.md`

---

## No-Opportunity Email State

When all cases are in P4 (suppressed), the email sends:

> "No new actionable acquisition research opportunities. X repeated
> already-announced/false-positive cases suppressed. Continue monitoring."

This is set by `no_opportunity: true` in the queue dict.

To skip the email entirely when no opportunity (save quota):
```
AI_EMAIL_SEND_NO_OPPORTUNITY_DIGEST=false
```

---

## Email Subject Line

In opportunity mode, the subject reflects priority state:

- `MA Scanner AI Brief — 1 Escalate / 3 Watch`
- `MA Scanner AI Brief — 2 Watch / 1 Review`
- `MA Scanner AI Brief — No New Opportunities / 10 Suppressed`

---

## Opportunity Mode in Scheduled Runs

The systemd service now runs:
```
run_ai_research.py --latest --limit 10 --depth fast_gate --email --strategic-brief --opportunity-mode
```

In opportunity mode:
1. Build cases from latest scanner output
2. Load suppression registry
3. Classify each case: NEW/CHANGED/UNCHANGED_SUPPRESSED
4. For UNCHANGED_SUPPRESSED: skip LLM, create stub decision (no API cost)
5. For others: run LLM gate (with its own daily fingerprint cache)
6. Build opportunity queue from all decisions
7. Update suppression registry with new DISCARD decisions
8. Email focused on P0-P3 only

---

## How to Run Diagnostics

```bash
# See suppression registry state
python3 src/ai_research/run_ai_research.py --suppression-status

# See what opportunity mode would select (no LLM, no files)
python3 src/ai_research/run_ai_research.py --latest --limit 20 --opportunity-plan

# Full dry run in opportunity mode
python3 src/ai_research/run_ai_research.py --latest --limit 20 --opportunity-mode --dry-run

# Standard plan view (shows cache status)
python3 src/ai_research/run_ai_research.py --latest --limit 5 --plan

# Evidence audit
python3 src/ai_research/run_ai_research.py --latest --limit 5 --evidence-audit
```

---

## How to Manage Suppression Manually

```bash
# Force a ticker to be re-analyzed on the next opportunity-mode run
python3 src/ai_research/run_ai_research.py --force-unsuppress TICKER

# Remove a ticker completely from the registry
python3 src/ai_research/run_ai_research.py --clear-suppression TICKER
```

`--force-unsuppress` sets a flag. The LLM will re-run on the next scheduled run.
If the result is still DISCARD + ALREADY_ANNOUNCED, it re-enters suppression.

`--clear-suppression` removes the record. The case will appear in the next email
as NEW_CASE, regardless of evidence.

---

## Limitations

1. **Suppression is per-ticker, not per-filing.** If the same ticker appears in two
   different filings on the same day, the second one uses the same registry record.
   The evidence fingerprint will differ, so it will correctly unsuppress.

2. **No cross-ticker deduplication.** If ticker A and ticker B both appear in the same
   announcement, they're tracked independently.

3. **Registry is local.** On VPS deploy, the registry persists in
   `data/ai_research/suppression_registry.json`. It is not committed to git (runtime data).

4. **No ML-based classification.** Suppression is rule-based only: DISCARD action +
   classification/bucket/archetype checks.

5. **External news signals not yet integrated.** If a case gets media coverage indicating
   new process activity, the system won't detect it without a new SEC filing. This is the
   next improvement: external news integration for TSRO-like signals.
