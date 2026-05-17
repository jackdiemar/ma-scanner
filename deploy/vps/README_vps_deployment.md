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

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Timer not firing | `systemctl status ma-scanner-live.timer` — is it active/waiting? |
| Service fails immediately | `journalctl -u ma-scanner-live.service -n 20` — check for import errors |
| `FMP_API_KEY` error | Verify `config/.env` exists and contains the key |
| Empty alerts | Old scan format — run `--once` with live FMP to get Gate 1 enriched results |
| Lock file stuck | `rm /opt/ma-scanner/live_scanner.lock` — only if no scan is running |
| Stale scan | `systemctl start ma-scanner-live.service` — force one run immediately |

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
