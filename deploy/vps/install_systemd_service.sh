#!/bin/bash
# install_systemd_service.sh — Install the MA Scanner hourly timer on a Linux VPS.
#
# What this does:
#   1. Backs up any existing service/timer files before overwriting
#   2. Copies ma-scanner-live.service and ma-scanner-live.timer to /etc/systemd/system/
#   3. Runs systemctl daemon-reload
#   4. Enables and starts the timer
#   5. Prints status and useful commands
#
# Usage:
#   sudo bash deploy/vps/install_systemd_service.sh
#
# Run from the repo root: /opt/ma-scanner/

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Must run as root ──────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  error "Run as root: sudo bash deploy/vps/install_systemd_service.sh"
fi

# ── Locate source files relative to this script ───────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_SRC="$SCRIPT_DIR/ma-scanner-live.service"
TIMER_SRC="$SCRIPT_DIR/ma-scanner-live.timer"
SYSTEMD_DIR="/etc/systemd/system"
BACKUP_DIR="/etc/systemd/system/ma-scanner-backup-$(date +%Y%m%d%H%M%S)"

for f in "$SERVICE_SRC" "$TIMER_SRC"; do
  [[ -f "$f" ]] || error "Source file not found: $f"
done

# ── Back up existing files if present ────────────────────────────────────────
if [[ -f "$SYSTEMD_DIR/ma-scanner-live.service" ]] || \
   [[ -f "$SYSTEMD_DIR/ma-scanner-live.timer" ]]; then
  warn "Existing service/timer files found. Backing up to $BACKUP_DIR"
  mkdir -p "$BACKUP_DIR"
  cp -f "$SYSTEMD_DIR/ma-scanner-live.service" "$BACKUP_DIR/" 2>/dev/null || true
  cp -f "$SYSTEMD_DIR/ma-scanner-live.timer"   "$BACKUP_DIR/" 2>/dev/null || true
  info "Backup written to $BACKUP_DIR"
fi

# ── Stop timer if running (safe — timer will restart on enable) ───────────────
if systemctl is-active --quiet ma-scanner-live.timer 2>/dev/null; then
  info "Stopping existing timer..."
  systemctl stop ma-scanner-live.timer
fi

# ── Copy service and timer files ──────────────────────────────────────────────
info "Installing service file..."
cp "$SERVICE_SRC" "$SYSTEMD_DIR/ma-scanner-live.service"
chmod 644 "$SYSTEMD_DIR/ma-scanner-live.service"

info "Installing timer file..."
cp "$TIMER_SRC" "$SYSTEMD_DIR/ma-scanner-live.timer"
chmod 644 "$SYSTEMD_DIR/ma-scanner-live.timer"

# ── Reload systemd so it sees the new unit files ──────────────────────────────
info "Reloading systemd daemon..."
systemctl daemon-reload

# ── Enable timer (start on boot) and start it now ────────────────────────────
info "Enabling and starting timer..."
systemctl enable ma-scanner-live.timer
systemctl start ma-scanner-live.timer

# ── Verify ────────────────────────────────────────────────────────────────────
echo ""
info "=== Installation complete ==="
echo ""
echo "Timer status:"
systemctl status ma-scanner-live.timer --no-pager || true
echo ""
echo "Useful commands:"
echo "  Check timer:     systemctl status ma-scanner-live.timer"
echo "  Check service:   systemctl status ma-scanner-live.service"
echo "  View logs:       journalctl -u ma-scanner-live.service -n 50 -f"
echo "  Next fire time:  systemctl list-timers ma-scanner-live.timer"
echo "  Run now:         systemctl start ma-scanner-live.service"
echo "  Stop timer:      systemctl stop ma-scanner-live.timer"
echo "  Uninstall:       sudo bash deploy/vps/uninstall_systemd_service.sh"
echo ""
