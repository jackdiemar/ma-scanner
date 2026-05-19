# MA Scanner — Operator Runbook

**System:** Black Starlight Capital — Biotech M&A Process Signal Monitor  
**Repo:** `/opt/ma-scanner` (VPS)  
**Branch:** `ai-final`

> **IMPORTANT:** This system is for internal research monitoring only. All AI outputs are research classifications, not investment advice and not recommendations to buy, sell, or hold any security. No output should be acted on without independent human analyst review.

---

## Quick Reference

| Goal | Command |
|---|---|
| Full production cycle | `sudo bash /opt/ma-scanner/deploy/vps/run_full_production_cycle.sh` |
| AI email only (no scanner) | `bash /opt/ma-scanner/deploy/vps/run_ai_email_now.sh` |
| Scanner only | `sudo bash /opt/ma-scanner/deploy/vps/run_scanner_once_safe.sh` |
| Install AI timer | `sudo bash /opt/ma-scanner/deploy/vps/install_ai_research_timer.sh` |
| Disable AI timer | `sudo bash /opt/ma-scanner/deploy/vps/uninstall_ai_research_timer.sh` |
| Evidence audit | `python3 src/ai_research/run_ai_research.py --latest --limit 10 --evidence-audit` |
| Inspect source fields | `python3 src/ai_research/run_ai_research.py --inspect-source-fields --limit 10` |
| Check AI layer status | `python3 src/ai_research/run_ai_research.py --status` |
| Post-deploy health check | `bash /opt/ma-scanner/deploy/vps/post_deploy_check.sh` |
| Repair permissions | `sudo bash /opt/ma-scanner/deploy/vps/repair_live_scanner.sh` |
| View logs | `journalctl -u ma-scanner-live.service -n 80 --no-pager` |

---

## 1. Full Production Cycle

Runs everything end-to-end: git pull → permissions repair → syntax check → live scanner → evidence audit → AI gate + email → health check.

```bash
sudo bash /opt/ma-scanner/deploy/vps/run_full_production_cycle.sh
```

Options:
```
--skip-git-pull          Skip git pull (use current local code)
--skip-scanner           Skip scanner run (use existing alert data)
--skip-ai                Skip AI research + email
--install-ai-timer       Install/restart AI research timer after run
--restart-scanner-timer  Start ma-scanner-live.timer after run
--limit N                Max alerts for AI (default: 10)
--timeout N              Scanner V12 timeout seconds (default: 1800)
--depth DEPTH            fast_gate or deep (default: fast_gate)
--branch BRANCH          Git branch (default: ai-final)
```

**Example — skip scanner, run AI only:**
```bash
sudo bash /opt/ma-scanner/deploy/vps/run_full_production_cycle.sh --skip-scanner
```

**Example — full cycle + install AI timer:**
```bash
sudo bash /opt/ma-scanner/deploy/vps/run_full_production_cycle.sh --install-ai-timer
```

Logs are written to:
```
/opt/ma-scanner/data/live_monitoring/operator_runs/operator_run_YYYY-MM-DD_HHMM.log
```

---

## 2. AI Email Only

Use when scanner has already run and you just want to re-run the AI gate and send the email.

```bash
bash /opt/ma-scanner/deploy/vps/run_ai_email_now.sh
```

With options:
```bash
bash /opt/ma-scanner/deploy/vps/run_ai_email_now.sh /opt/ma-scanner 10 fast_gate
# args: [INSTALL_DIR] [LIMIT] [DEPTH]
```

Steps it runs:
1. AI layer status check
2. Evidence audit with EDGAR fetch (`--evidence-audit --fetch-text`)
3. AI gate + email (`--latest --limit N --depth D --email`)
4. Print AI summary

---

## 3. Scanner Only

Run the live scanner once with permissions repair and health check.

```bash
sudo bash /opt/ma-scanner/deploy/vps/run_scanner_once_safe.sh
```

With custom timeout:
```bash
sudo bash /opt/ma-scanner/deploy/vps/run_scanner_once_safe.sh /opt/ma-scanner 1800
```

**Note:** Scanner takes 5–20 minutes. The script does not background the process — you see live output. If it fails, it prints the error log and journalctl tail automatically.

---

## 4. AI Research Timer

The AI research timer sends a briefing email 3× per trading day (09:30, 13:00, 16:10 ET).

**Install:**
```bash
sudo bash /opt/ma-scanner/deploy/vps/install_ai_research_timer.sh
```

**Check status:**
```bash
systemctl status ma-scanner-ai-research.timer
systemctl list-timers | grep ma-scanner
```

**Run immediately (one-shot):**
```bash
sudo systemctl start ma-scanner-ai-research.service
journalctl -u ma-scanner-ai-research.service -n 50 --no-pager
```

**Disable (if cost concern):**
```bash
sudo bash /opt/ma-scanner/deploy/vps/uninstall_ai_research_timer.sh
```

The live scanner timer (`ma-scanner-live.timer`) is not affected by the AI timer install/uninstall.

---

## 5. Evidence System

### Evidence grades

| Grade | Meaning | AI behavior |
|---|---|---|
| A | Full filing text + exact excerpt from SEC | Confident classifications allowed |
| B | Exact excerpt + direct SEC URL | Confident classifications allowed |
| C | Exact excerpt + any source URL | Confident classifications allowed |
| D | Constructed EDGAR URL only, no excerpt | Confidence capped 0.40, ESCALATE → NEEDS_HUMAN_REVIEW |
| F | No URL, no excerpt | Same as D |

**Why grades are D/F:** The scanner has been running in dry-run mode. Gate 1 (EDGAR filing fetch) was skipped. Re-run the scanner in live mode to populate `signal_source_url` and `signal_source_excerpt` fields.

### Run evidence audit:
```bash
cd /opt/ma-scanner
python3 src/ai_research/run_ai_research.py --latest --limit 10 --evidence-audit
python3 src/ai_research/run_ai_research.py --latest --limit 10 --evidence-audit --fetch-text
```

### Inspect raw source fields per ticker:
```bash
python3 src/ai_research/run_ai_research.py --inspect-source-fields --limit 10
```

### Show full evidence detail for one ticker:
```bash
python3 src/ai_research/run_ai_research.py --show-evidence APLS
python3 src/ai_research/run_ai_research.py --show-evidence APLS --fetch-text
```

---

## 6. Systemd Services

| Service | Purpose | Timer |
|---|---|---|
| `ma-scanner-live.service` | One-pass scanner run | `ma-scanner-live.timer` |
| `ma-scanner-ai-research.service` | AI gate + email | `ma-scanner-ai-research.timer` (3× daily) |

**Live scanner timer schedule:** configured in `deploy/vps/ma-scanner-live.timer`

**AI research timer schedule:** Mon–Fri at 09:30, 13:00, 16:10 ET

```bash
# Check both timers
systemctl list-timers | grep ma-scanner

# Follow live scanner journal
journalctl -u ma-scanner-live.service -f

# Follow AI research journal
journalctl -u ma-scanner-ai-research.service -f
```

---

## 7. Configuration

All secrets in `config/.env` (chmod 600, never committed).

Key variables:

```bash
# Scanner
FMP_API_KEY=...
LIVE_SCANNER_DRY_RUN=false       # Must be false for live runs

# AI research
AI_RESEARCH_ENABLED=true
AI_RESEARCH_DRY_RUN=false
OPENAI_API_KEY=sk-...
AI_MODEL=gpt-4.1-mini
AI_RESEARCH_MAX_CASES_PER_RUN=10

# Email
AI_EMAILS_ENABLED=true
RESEND_API_KEY=...
RESEND_FROM=alerts@blackstarlightcapital.com
EMAIL_RECIPIENT=...
```

---

## 8. Troubleshooting

### Scanner fails / permission error
```bash
sudo bash /opt/ma-scanner/deploy/vps/repair_live_scanner.sh
```

### Scanner stuck / stale lock
```bash
rm -f /opt/ma-scanner/live_scanner.lock
sudo bash /opt/ma-scanner/deploy/vps/run_scanner_once_safe.sh
```

### AI email not sending
```bash
python3 src/ai_research/run_ai_research.py --status
# Check: AI_EMAILS_ENABLED, RESEND_API_KEY, EMAIL_RECIPIENT
```

### All cases evidence grade F
```bash
python3 src/ai_research/run_ai_research.py --inspect-source-fields --limit 5
# Will show scanner_dry_run=True — set LIVE_SCANNER_DRY_RUN=false and re-run scanner
```

### Deploy new code from local machine
See **Section 10** for the one-command local deploy script.

Manual VPS steps:
```bash
# On VPS:
cd /opt/ma-scanner
git pull --ff-only origin ai-final
sudo bash deploy/vps/run_full_production_cycle.sh --skip-scanner
```

---

## 9. Do Not

- Do not commit `config/.env` (contains secrets)
- Do not commit `data/*` (generated outputs, cases, caches)
- Do not run auto-trading. This system outputs research classifications, not trade signals.
- Do not act on AI output without independent human analyst review of source filings.
- Do not use `--no-verify` on git commits without checking why hooks fail.

---

## 10. Local Deploy

Push code from your local machine to the VPS in one command.

### Setup (one-time)
```bash
cp deploy/local/.env.deploy.example deploy/local/.env.deploy
# Edit .env.deploy — set MA_SCANNER_VPS_HOST=root@your_server_ip
```

### Push + run AI email (most common)
```bash
bash deploy/local/push_and_deploy_to_vps.sh --run-ai-email
```

### Push + run full production cycle
```bash
bash deploy/local/push_and_deploy_to_vps.sh --run-full-cycle
```

### Push only (no remote action)
```bash
bash deploy/local/push_and_deploy_to_vps.sh
```

### Push + cleanup runtime noise on VPS first
```bash
bash deploy/local/push_and_deploy_to_vps.sh --run-cleanup --run-full-cycle
```

### All options
```
--host HOST             VPS SSH target (overrides .env.deploy)
--remote-dir DIR        Install dir on VPS (default: /opt/ma-scanner)
--branch BRANCH         Git branch (default: ai-final)
--run-full-cycle        Run full production cycle on VPS after pull
--run-ai-email          Run AI email only on VPS after pull
--run-scanner           Run scanner only on VPS after pull
--run-cleanup           Run clean_runtime_git_noise.sh on VPS before pull
--run-health-check      Run health check on VPS after deploy
--skip-push             Skip git push (VPS pull only)
--skip-remote-pull      Skip VPS pull (push only)
```

**Safety:** The script aborts if the VPS has uncommitted source changes. It uses `git pull --ff-only` to avoid accidental merge commits on the VPS.

---

## 11. Repo Hygiene

### Check for tracked runtime artifacts
```bash
bash deploy/vps/check_repo_clean.sh
```

Checks: `config/.env` not tracked, no runtime data files tracked, source tree clean. Exits non-zero on any failure.

### Untrack runtime artifacts (without deleting local files)
```bash
bash deploy/vps/clean_runtime_git_noise.sh
git add .gitignore
git commit -m "chore: untrack runtime artifacts from git index"
```

**What gets untracked:**
- `data/cache/` — FMP/EDGAR API response cache
- `data/ai_research/` — generated research outputs
- `data/live_monitoring/` runtime files (alerts, state, logs)
- `data/scans/scan_v12_*.json` — timestamped scan files
- `data/legacy-scans/`, `data/predictions/`, `data/tracking/`
- `.DS_Store` files everywhere
