#!/bin/bash
# uninstall_systemd_service.sh — Remove the MA Scanner systemd timer from the VPS.
#
# What this does:
#   1. Stops the timer and service (if running)
#   2. Disables the timer (removes from boot)
#   3. Removes service and timer files from /etc/systemd/system/
#   4. Reloads systemd daemon
#   5. Confirms removal
#
# Does NOT:
#   - Delete the repo or any data files
#   - Remove config/.env
#   - Remove the virtualenv
#
# Usage:
#   sudo bash deploy/vps/uninstall_systemd_service.sh

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

if [[ $EUID -ne 0 ]]; then
  echo "[ERROR] Run as root: sudo bash deploy/vps/uninstall_systemd_service.sh"
  exit 1
fi

SYSTEMD_DIR="/etc/systemd/system"

# ── Stop timer if active ──────────────────────────────────────────────────────
if systemctl is-active --quiet ma-scanner-live.timer 2>/dev/null; then
  info "Stopping timer..."
  systemctl stop ma-scanner-live.timer
else
  warn "Timer is not active — nothing to stop."
fi

# ── Stop service if active (shouldn't be, but be safe) ───────────────────────
if systemctl is-active --quiet ma-scanner-live.service 2>/dev/null; then
  info "Stopping service..."
  systemctl stop ma-scanner-live.service
fi

# ── Disable timer ─────────────────────────────────────────────────────────────
if systemctl is-enabled --quiet ma-scanner-live.timer 2>/dev/null; then
  info "Disabling timer..."
  systemctl disable ma-scanner-live.timer
else
  warn "Timer is not enabled — skipping disable."
fi

# ── Remove unit files ─────────────────────────────────────────────────────────
for f in \
  "$SYSTEMD_DIR/ma-scanner-live.service" \
  "$SYSTEMD_DIR/ma-scanner-live.timer"; do
  if [[ -f "$f" ]]; then
    info "Removing $f"
    rm -f "$f"
  else
    warn "File not found: $f — already removed."
  fi
done

# ── Reload systemd ────────────────────────────────────────────────────────────
info "Reloading systemd daemon..."
systemctl daemon-reload

echo ""
info "=== Uninstall complete ==="
echo ""
echo "The scanner will no longer run on a schedule."
echo "Repo and data files are untouched at /opt/ma-scanner."
echo ""
echo "To re-install: sudo bash deploy/vps/install_systemd_service.sh"
