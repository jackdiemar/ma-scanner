# AI Research Layer

The AI research layer is an optional, modular research gate that sits on top of the live scanner.
It reads scanner alerts, builds structured research cases, and optionally calls an LLM to classify
whether each alert warrants deeper human research.

**This layer does not auto-trade, does not connect to any broker, and does not produce BUY or SELL signals.**
Its sole purpose is to help a human analyst triage scanner alerts faster.

---

## What It Does

1. **Research case builder** — reads `data/live_monitoring/latest_alerts.json`,
   `data/live_monitoring/latest_review_memo.md`, and `data/live_monitoring/live_alert_log.csv`.
   Writes per-ticker structured case files to `data/ai_research/cases/YYYY-MM-DD/`.

2. **Investment gate** — takes a research case, builds a diligence prompt, calls the LLM,
   and returns a structured JSON decision:
   - Classification (e.g., `PRE_PROCESS_OPPORTUNITY`, `ALREADY_ANNOUNCED_DEAL`, `FALSE_POSITIVE`)
   - Research action (e.g., `ESCALATE`, `WATCH`, `DISCARD`)
   - Confidence, investability score, evidence strength
   - Specific `why_interesting`, `why_not`, `key_evidence`, `next_research_steps`

3. **Watchlist manager** — maintains `data/ai_research/watchlist.json` with per-ticker history,
   status tracking, and automatic stale-marking after 14 days of inactivity.

4. **Run summary** — writes `data/ai_research/latest_ai_research_summary.md` after every run.

---

## Setup

### 1. Install the openai package

```bash
pip install openai
```

The live scanner does not require this. It is only needed if `AI_RESEARCH_ENABLED=true`.

### 2. Configure environment variables

Copy `config/.env.example` to `config/.env` and fill in the AI Research section:

```bash
AI_RESEARCH_ENABLED=true
OPENAI_API_KEY=sk-...           # your OpenAI API key
AI_MODEL=gpt-4.1-mini           # or gpt-4o, gpt-4-turbo, etc.
AI_RESEARCH_MAX_CASES_PER_RUN=5
AI_RESEARCH_DRY_RUN=false       # set true to test without calling the API
```

Keep `config/.env` chmod 600. Never commit real values.

---

## Running

### Dry run (safe — no API calls)

```bash
python3 src/ai_research/run_ai_research.py --latest --dry-run
```

Builds case files for all current alerts, skips LLM, prints status.

### Run with limit (uses LLM if enabled)

```bash
python3 src/ai_research/run_ai_research.py --latest --limit 5
```

Processes the top 5 alerts by scanner priority, runs LLM gate on each.

### Single ticker

```bash
python3 src/ai_research/run_ai_research.py --ticker SDGR
```

### Status check

```bash
python3 src/ai_research/run_ai_research.py --status
```

Prints watchlist counts (escalated, active watch, needs review, discarded, stale)
and LLM config status without exposing secrets.

### Build cases only (no gate)

```bash
python3 src/ai_research/research_case_builder.py --latest
python3 src/ai_research/research_case_builder.py --latest --limit 10
python3 src/ai_research/research_case_builder.py --ticker SDGR
```

---

## Output Files

| Path | Description |
|---|---|
| `data/ai_research/cases/YYYY-MM-DD/{TICKER}_research_case.json` | Structured case + AI decision |
| `data/ai_research/cases/YYYY-MM-DD/{TICKER}_research_case.md` | Human-readable version |
| `data/ai_research/watchlist.json` | Per-ticker watchlist with history |
| `data/ai_research/latest_ai_research_summary.md` | Summary of most recent run |

All output paths are gitignored (`data/ai_research/`). They are local-only.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AI_RESEARCH_ENABLED` | `false` | Master switch. `false` = no LLM calls ever |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key. Required if enabled |
| `AI_MODEL` | `gpt-4.1-mini` | OpenAI model name |
| `AI_RESEARCH_MAX_CASES_PER_RUN` | `5` | Max cases sent to LLM per run |
| `AI_RESEARCH_DRY_RUN` | `true` | If `true`, builds cases but never calls LLM |

If `AI_RESEARCH_ENABLED=false` or `OPENAI_API_KEY` is missing, the AI layer skips
gracefully and prints a clear message. The live scanner is never affected.

---

## Why It Does Not Auto-Trade

The gate output is a research classification, not a trading signal. Classifications like
`PRE_PROCESS_OPPORTUNITY` or `ESCALATE` mean "a human analyst should read this filing now."
They do not mean "buy this stock." No position sizing, no order routing, no broker connection
of any kind is present or intended. All outputs are advisory research notes only.

---

## VPS Deployment

The live scanner runs as a systemd service (`ma-scanner-live.service`).
The AI layer is separate and should be run manually or on a separate cron after the scanner completes.

SSH into the VPS, then:

```bash
cd /path/to/ma-scanner

# Check scanner health first
python3 src/live_monitoring/live_scanner_runner.py --status

# Dry run AI layer (safe)
python3 src/ai_research/run_ai_research.py --latest --dry-run

# Live AI run (requires API key in config/.env)
python3 src/ai_research/run_ai_research.py --latest --limit 5

# Status
python3 src/ai_research/run_ai_research.py --status
```

The AI layer does not touch the systemd service and does not modify any live scanner state files.
It reads from `data/live_monitoring/` (read-only from its perspective) and writes only to
`data/ai_research/`.
