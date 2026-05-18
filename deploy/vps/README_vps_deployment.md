# VPS Deployment Guide — MA Scanner Live Monitor

Deploys the live biotech process-signal scanner on a headless Ubuntu VPS.
Runs one scan per hour via systemd timer. No auto-trading. No broker APIs.

---

## Recommended Server Spec

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disk | 10 GB | 20 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Network | Any | Any with static IP |

**Provider options:** DigitalOcean Droplet ($6/mo), Hetzner CX22 (~$4/mo), Vultr Cloud Compute, AWS Lightsail. Any Ubuntu VPS with systemd will work.

---

## Fastest path: buy server + bootstrap

The goal is to make the server setup nearly one-click. You still need to buy
the VPS and provide secrets. Do not paste real secrets into git, screenshots, or
support tickets.

### Path A: Cloud-init during server creation

Use this when the VPS provider has a **User Data**, **Cloud-init**, or
**Startup Script** field.

1. Open `deploy/vps/bootstrap_cloud_init.yaml`.
2. Replace these placeholders before creating the server:
   - `REPO_URL_PLACEHOLDER` — your repo remote, for example `https://github.com/USER/REPO.git`
   - `FMP_API_KEY_PLACEHOLDER` — your FMP key, or leave blank and add it later
   - `INSTALL_DIR_PLACEHOLDER` — use `/opt/ma-scanner`
   - `BRANCH_PLACEHOLDER` — usually `main`
3. Paste the edited YAML into the provider's User Data field.
4. Create the Ubuntu server.
5. SSH in after cloud-init finishes.
6. Run:

```bash
bash /opt/ma-scanner/deploy/vps/post_deploy_check.sh
```

Cloud-init writes a bootstrap log here:

```bash
sudo tail -200 /var/log/ma-scanner-bootstrap.log
```

If you left `FMP_API_KEY_PLACEHOLDER` blank, edit the env file after SSH:

```bash
sudo nano /opt/ma-scanner/config/.env
sudo chmod 600 /opt/ma-scanner/config/.env
bash /opt/ma-scanner/deploy/vps/post_deploy_check.sh
```

### Path B: SSH once and run bootstrap

Use this when you prefer to create the server first and run one setup command
after SSH.

1. Create an Ubuntu 22.04 or 24.04 VPS.
2. SSH in:

```bash
ssh root@<your-server-ip>
```

3. Install git if needed and clone the repo:

```bash
apt-get update
apt-get install -y git
git clone <your-repo-url> /opt/ma-scanner
cd /opt/ma-scanner
```

4. Run bootstrap with the FMP key supplied as an environment variable. The key is
written to `config/.env` but not printed:

```bash
sudo REPO_URL="https://github.com/USER/REPO.git" \
  FMP_API_KEY="your_fmp_key_here" \
  bash deploy/vps/bootstrap_one_command.sh
```

Private repo via SSH remote:

```bash
sudo REPO_URL="git@github.com:USER/REPO.git" \
  bash deploy/vps/bootstrap_one_command.sh
```

For SSH remotes, make sure the server has a deploy key with read access before
the clone/pull step.

5. Verify:

```bash
bash /opt/ma-scanner/deploy/vps/post_deploy_check.sh
```

The bootstrap does not run a live scanner pass. It runs status and health
checks, installs the hourly systemd timer, and prints next steps.

---

## One-Time Setup

### 1. Provision the server

Create an Ubuntu 22.04 or 24.04 VPS. Add your SSH key during provisioning. Note the IP address.

### 2. SSH in

```bash
ssh ubuntu@<your-server-ip>
```

### 3. Clone the repo

```bash
sudo git clone <your-repo-url> /opt/ma-scanner
sudo chown -R ubuntu:ubuntu /opt/ma-scanner
```

Replace `<your-repo-url>` with the actual repository URL. If the repo is private, set up a deploy key:

```bash
# On the server:
ssh-keygen -t ed25519 -C "ma-scanner-vps" -f ~/.ssh/deploy_key -N ""
cat ~/.ssh/deploy_key.pub
# Add the public key as a read-only deploy key in your git hosting settings.

# Then clone using the deploy key:
GIT_SSH_COMMAND="ssh -i ~/.ssh/deploy_key" git clone <your-repo-url> /opt/ma-scanner
```

### 4. Run the setup script

```bash
cd /opt/ma-scanner
sudo bash deploy/vps/setup_ubuntu_server.sh
```

This installs Python packages, creates the virtualenv, and creates required directories. Safe to re-run.

### 5. Create config/.env

This file holds secrets. Never commit it. Never let it be world-readable.

```bash
nano /opt/ma-scanner/config/.env
```

Contents:

```
FMP_API_KEY=your_fmp_api_key_here
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_smtp_app_password
SMTP_RECIPIENT=recipient@example.com
```

Lock it down immediately:

```bash
chmod 600 /opt/ma-scanner/config/.env
chown ubuntu:ubuntu /opt/ma-scanner/config/.env
```

> `.gitignore` already excludes `config/.env`. Do not override this.

### 6. Test one run manually

Before enabling the timer, verify the scanner works:

```bash
cd /opt/ma-scanner
.venv/bin/python src/live_monitoring/live_scanner_runner.py --once --dry-run
```

Then try a real run (uses FMP API, takes several minutes):

```bash
.venv/bin/python src/live_monitoring/live_scanner_runner.py --once
```

### 7. Install the hourly timer

```bash
sudo bash /opt/ma-scanner/deploy/vps/install_systemd_service.sh
```

The timer runs once per hour at a random offset (up to 5 minutes) to avoid thundering-herd on external APIs.

---

## Checking Status

### Full health summary

```bash
bash /opt/ma-scanner/deploy/vps/check_server_status.sh
```

### Timer next fire time

```bash
systemctl list-timers ma-scanner-live.timer
```

### Service last run

```bash
systemctl status ma-scanner-live.service
```

### Python health check

```bash
/opt/ma-scanner/.venv/bin/python /opt/ma-scanner/src/live_monitoring/health_check.py
```

---

## Viewing Logs

### Live log stream (follow mode)

```bash
journalctl -u ma-scanner-live.service -f
```

### Last 50 lines

```bash
journalctl -u ma-scanner-live.service -n 50
```

### All logs from today

```bash
journalctl -u ma-scanner-live.service --since today
```

### Error log file

```bash
tail -50 /opt/ma-scanner/data/live_monitoring/live_scanner_errors.log
```

---

## Viewing Alerts and Memo

### Latest review memo

```bash
cat /opt/ma-scanner/data/live_monitoring/latest_review_memo.md
```

### Current alert state

```bash
cat /opt/ma-scanner/data/live_monitoring/latest_alerts.json | python3 -m json.tool | head -100
```

### Scanner run state

```bash
cat /opt/ma-scanner/data/live_monitoring/live_scanner_state.json
```

### Alert history (CSV)

```bash
cat /opt/ma-scanner/data/live_monitoring/live_alert_log.csv
```

---

## Email Alerts

Email notifications are optional and disabled by default. Some VPS providers,
including DigitalOcean in common configurations, block or degrade outbound SMTP
ports. The recommended provider is therefore **Resend over HTTPS**. SMTP remains
available as a fallback.

No broker APIs are involved, and notifications are research monitoring
summaries, not execution instructions.

### Configure Resend over HTTPS

Edit the VPS env file:

```bash
sudo nano /opt/ma-scanner/config/.env
sudo chmod 600 /opt/ma-scanner/config/.env
```

Add Resend settings:

```bash
EMAIL_PROVIDER=resend
EMAIL_ALERTS_ENABLED=true
EMAIL_ON_EVERY_RUN=false
EMAIL_ON_NEW_ALERTS=true
EMAIL_DAILY_DIGEST=true

RESEND_API_KEY=your_resend_api_key
RESEND_FROM=Scanner <alerts@your-verified-domain.com>
EMAIL_RECIPIENT=you@example.com
```

`RESEND_FROM` must use a sender/domain allowed by your Resend account.

Do not commit `config/.env`. Do not paste `RESEND_API_KEY` into logs or support
tickets.

### SMTP fallback

Use this only if outbound SMTP works from the server:

```bash
EMAIL_PROVIDER=smtp
EMAIL_ALERTS_ENABLED=true

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_app_password
SMTP_RECIPIENT=you@example.com
SMTP_FROM=your_smtp_user
```

Do not paste `SMTP_PASSWORD` into logs or support tickets.

### Test email

Run this explicitly after email settings are in place:

```bash
cd /opt/ma-scanner
.venv/bin/python src/live_monitoring/email_notifier.py --status
.venv/bin/python src/live_monitoring/email_notifier.py --test
```

Send the latest memo manually:

```bash
.venv/bin/python src/live_monitoring/email_notifier.py --send-latest
```

### Send rules and throttling

- Error runs (`v12_error` or `v12_timeout`) send an error email when
  `EMAIL_ALERTS_ENABLED=true`.
- New-alert runs send email when `EMAIL_ON_NEW_ALERTS=true` and `last_new_count`
  is greater than zero.
- Daily digest sends at most once per UTC day when `EMAIL_DAILY_DIGEST=true`.
  The sent date is stored in `data/live_monitoring/live_scanner_state.json` as
  `last_daily_digest_date`.
- `EMAIL_ON_EVERY_RUN=true` sends after every non-dry-run scanner pass. Leave it
  false unless you intentionally want hourly email.
- `--once --dry-run` never sends email.

The runner records email state fields when available:

- `last_email_status`
- `last_email_sent_at`
- `last_email_subject`
- `last_email_error`

### Disable email

Set:

```bash
EMAIL_ALERTS_ENABLED=false
```

Then the scanner continues normally and skips all email sends.

---

## Updating the Code

```bash
cd /opt/ma-scanner

# Pull latest changes
sudo -u ubuntu git pull origin main

# If requirements changed:
.venv/bin/pip install -r requirements.txt

# Reload systemd if service/timer files changed:
sudo bash deploy/vps/install_systemd_service.sh
```

No scanner restart needed for code changes — each timer invocation starts a fresh Python process.

---

## Stopping and Uninstalling

### Pause (stop timer, keep installed)

```bash
sudo systemctl stop ma-scanner-live.timer
```

### Resume

```bash
sudo systemctl start ma-scanner-live.timer
```

### Full uninstall

```bash
sudo bash /opt/ma-scanner/deploy/vps/uninstall_systemd_service.sh
```

This removes the systemd files. Repo and data are untouched.

---

## Security Basics

- `config/.env` must be `chmod 600` and owned by the scanner user. Never commit it.
- The scanner user (`ubuntu` by default) should not have passwordless sudo beyond what setup requires.
- Lock down SSH: disable password auth, use key-only login. Add to `/etc/ssh/sshd_config`:
  ```
  PasswordAuthentication no
  PubkeyAuthentication yes
  ```
- The scanner only makes outbound HTTPS calls to SEC EDGAR and FMP APIs. It does not open any listening ports.
- `scan_latest.json`, alert logs, and run snapshots contain ticker data and signal excerpts — treat as non-public research output.
- Rotate `FMP_API_KEY` periodically. Update `config/.env` and the file takes effect on the next scan.

---

## Recovery Scripts

### Fix permissions and restart

When the scanner hits `PermissionError` on data directories, run:

```bash
sudo bash /opt/ma-scanner/deploy/vps/repair_live_scanner.sh
```

This stops the service, creates missing dirs, fixes ownership, clears stale lock,
and restarts. **Only run when no scan is actively in progress.**

### Check AI research layer

```bash
bash /opt/ma-scanner/deploy/vps/check_ai_research.sh
```

Verifies `config/.env` AI config, runs `--status`, and prints the latest summary
mtime and watchlist entry count.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Timer not firing | `systemctl status ma-scanner-live.timer` — is it active/waiting? |
| Service fails immediately | `journalctl -u ma-scanner-live.service -n 20` — check for import errors |
| `FMP_API_KEY` error | Verify `config/.env` exists and contains the key |
| Empty alerts | Old scan format — run `--once` with live FMP to get Gate 1 enriched results |
| Lock file stuck | `python3 src/live_monitoring/live_scanner_runner.py --clear-stale-lock` |
| PermissionError on data dirs | `sudo bash deploy/vps/repair_live_scanner.sh` |
| Stale scan | `systemctl start ma-scanner-live.service` — force one run immediately |

### V12 missing `backtest` import

Older code imported `backtest` at V12 startup, even when the live scanner was not
running backtests. That can fail on a clean VPS with:

```text
ModuleNotFoundError: No module named 'backtest'
```

Fix path:

```bash
cd /opt/ma-scanner
git pull origin main
python3 -m py_compile src/PRODUCTION_SCANNER_V12.py
```

Normal live monitoring does not require the backtest module. If `--backtest` is
requested and the module is unavailable, V12 now exits that mode with a clear
message.

### V12 timeout

The live runner bounds the V12 subprocess with a 15-minute timeout by default:

```bash
/opt/ma-scanner/.venv/bin/python \
  /opt/ma-scanner/src/live_monitoring/live_scanner_runner.py \
  --once --v12-timeout-seconds 900
```

If V12 times out, the runner:

- terminates or kills the V12 subprocess
- writes `last_run_status: v12_timeout` to `data/live_monitoring/live_scanner_state.json`
- writes details to `data/live_monitoring/live_scanner_errors.log`
- writes a failure memo to `data/live_monitoring/latest_review_memo.md`
- avoids treating an old `scan_latest.json` as fresh output
- releases `live_scanner.lock`

Systemd also has `TimeoutStartSec=20min` as a second safety boundary.

### Stop the timer before debugging

```bash
sudo systemctl stop ma-scanner-live.timer
systemctl list-timers ma-scanner-live.timer
```

### Kill a stuck scanner process

Use this only after checking that the timer is stopped and a process is truly
stuck:

```bash
pgrep -af 'live_scanner_runner|PRODUCTION_SCANNER_V12'
sudo pkill -f PRODUCTION_SCANNER_V12.py
sudo pkill -f live_scanner_runner.py
rm -f /opt/ma-scanner/live_scanner.lock
```

### Run one manual service pass

After secrets are set and the code is updated:

```bash
sudo systemctl start ma-scanner-live.service
systemctl status ma-scanner-live.service --no-pager -l
```

### View logs

```bash
journalctl -u ma-scanner-live.service -n 80 --no-pager
journalctl -u ma-scanner-live.service -f
tail -80 /opt/ma-scanner/data/live_monitoring/live_scanner_errors.log
```

### Re-enable the hourly timer after a fix

```bash
sudo systemctl daemon-reload
sudo systemctl start ma-scanner-live.timer
systemctl list-timers ma-scanner-live.timer
bash /opt/ma-scanner/deploy/vps/post_deploy_check.sh
```

---

## File Layout (server)

```
/opt/ma-scanner/
├── config/
│   └── .env                          # secrets — chmod 600, not in git
├── data/
│   ├── scans/
│   │   └── scan_latest.json          # latest V12 scan output
│   └── live_monitoring/
│       ├── latest_review_memo.md     # latest review memo
│       ├── latest_alerts.json        # dedup state
│       ├── live_alert_log.csv        # append-only history
│       ├── live_scanner_state.json   # last-run metadata
│       └── runs/                     # per-run snapshots
├── deploy/vps/                       # this guide and systemd files
├── src/
│   ├── PRODUCTION_SCANNER_V12.py
│   └── live_monitoring/
│       ├── live_scanner_runner.py
│       ├── health_check.py
│       └── ...
├── .venv/                            # Python virtualenv
└── requirements.txt
```
