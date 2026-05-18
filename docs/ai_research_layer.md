# AI Research Layer

The AI research layer is an optional manual diligence layer on top of the live scanner. It reads scanner alerts, builds structured research cases, optionally calls an LLM for research classification, updates a local watchlist, and writes a local run summary.

This layer is research only. It is not trading advice, does not auto-trade, does not connect to broker APIs, and does not make transaction recommendations.

---

## What It Does

1. **Research case builder** reads `data/live_monitoring/latest_alerts.json`, `data/live_monitoring/latest_review_memo.md`, and `data/live_monitoring/live_alert_log.csv`.
2. **Research gate** classifies whether an alert deserves deeper human diligence.
3. **Watchlist manager** maintains `data/ai_research/watchlist.json` after real AI runs.
4. **Run summary** writes `data/ai_research/latest_ai_research_summary.md`.
5. **Daily cache** stores same-day gate outputs in `data/ai_research/cache/`.

Generated AI research outputs live under `data/ai_research/` and are gitignored.

---

## Environment

`config/.env` exists only on the VPS. Do not commit real values.

Recommended first live settings:

```bash
AI_RESEARCH_ENABLED=true
AI_RESEARCH_DRY_RUN=false
AI_MODEL=gpt-4.1-mini
AI_RESEARCH_MAX_CASES_PER_RUN=10
AI_RESEARCH_DEFAULT_DEPTH=fast_gate
```

`OPENAI_API_KEY` must also be set in `config/.env` before a live LLM run. Status commands only print whether the key is present.

---

## Status

```bash
python3 src/ai_research/run_ai_research.py --status
```

Status reports:

- `AI_RESEARCH_ENABLED`
- `AI_RESEARCH_DRY_RUN`
- `OPENAI_API_KEY set` as `true` or `false`
- `AI_MODEL`
- `AI_RESEARCH_MAX_CASES_PER_RUN`
- `AI_RESEARCH_DEFAULT_DEPTH`
- latest scanner output found or missing
- alert count available
- watchlist path
- cache path
- latest AI summary path
- whether a live LLM call is allowed

No secrets are printed.

---

## Plan Mode

```bash
python3 src/ai_research/run_ai_research.py --latest --limit 5 --plan
```

Plan mode is the safest preflight:

- does not call the LLM
- does not write files
- shows tickers that would be researched
- shows cache hit or miss where possible
- shows `estimated_action=would_call_llm` or `estimated_action=would_reuse_cache`

Use this before the first live AI pass.

---

## Dry-Run Mode

```bash
python3 src/ai_research/run_ai_research.py --latest --limit 5 --dry-run
```

Dry-run mode:

- builds research cases
- validates case and decision schemas
- does not call the LLM
- does not require `OPENAI_API_KEY`
- does not fail just because `AI_RESEARCH_ENABLED=false`
- does not update the watchlist

Dry-run may write local generated research files under `data/ai_research/`. These files are local-only and gitignored.

---

## First Real Manual Run

After `config/.env` has AI enabled, dry-run off, and an OpenAI key set:

```bash
python3 src/ai_research/run_ai_research.py --latest --limit 5 --depth fast_gate
```

A real run:

- requires `AI_RESEARCH_ENABLED=true`
- requires `OPENAI_API_KEY`
- requires `AI_RESEARCH_DRY_RUN=false`
- uses same-day cache entries where available
- writes an AI summary
- updates the watchlist
- fails safely with a clear message if disabled or missing a key

---

## Cache Behavior

The research gate fingerprints each case using ticker, filing date, filing type, trigger phrase, and source excerpt. The cache is stored at:

```text
data/ai_research/cache/gate_cache_YYYY-MM-DD.json
```

If the same signal appears again on the same calendar day, the cached decision is reused and the LLM is not called for that case. Cache files rotate daily, so yesterday's results do not automatically control today's analysis.

---

## VPS Checks

Run the readiness check from the repo:

```bash
bash deploy/vps/check_ai_research.sh
```

The check script:

- sources `config/.env` if present
- never prints secrets
- compiles AI modules
- runs status
- runs dry-run
- runs plan mode
- prints the exact first real AI command

Optional one-shot manual runner:

```bash
bash deploy/vps/run_ai_research_once.sh
```

Defaults are `limit=5` and `depth=fast_gate`. You can override them:

```bash
bash deploy/vps/run_ai_research_once.sh 10 fast_gate
```

The one-shot script runs status and plan first. It only attempts a real AI pass when `AI_RESEARCH_ENABLED=true`, `AI_RESEARCH_DRY_RUN=false`, and `OPENAI_API_KEY` is set.

---

## Keep AI Unscheduled

Do not add the AI layer to `ma-scanner-live.service` or `ma-scanner-live.timer`.

The live scanner systemd units remain scanner-only:

```bash
systemctl status ma-scanner-live.service
systemctl status ma-scanner-live.timer
```

Run AI research manually only:

```bash
cd /opt/ma-scanner
python3 src/ai_research/run_ai_research.py --latest --limit 5 --depth fast_gate
```

---

## Validation Commands

```bash
python3 -m py_compile src/ai_research/research_case_builder.py
python3 -m py_compile src/ai_research/llm_client.py
python3 -m py_compile src/ai_research/investment_gate.py
python3 -m py_compile src/ai_research/prompts.py
python3 -m py_compile src/ai_research/watchlist_manager.py
python3 -m py_compile src/ai_research/run_ai_research.py
bash -n deploy/vps/check_ai_research.sh
bash -n deploy/vps/run_ai_research_once.sh
python3 src/ai_research/run_ai_research.py --status
python3 src/ai_research/run_ai_research.py --latest --limit 5 --dry-run
python3 src/ai_research/run_ai_research.py --latest --limit 5 --plan
git diff --check
git status --short
```
