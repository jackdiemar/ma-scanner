#!/usr/bin/env bash
# uninstall_ai_research_timer.sh — Disable and remove AI research timer.
# Safe to run even if timer is not installed.
# Usage: sudo bash deploy/vps/uninstall_ai_research_timer.sh

set -uo pipefail

echo "=== Uninstall AI Research Timer ==="
echo ""

echo "[1/5] Stopping timer..."
systemctl stop ma-scanner-ai-research.timer 2>/dev/null || true

echo "[2/5] Disabling timer..."
systemctl disable ma-scanner-ai-research.timer 2>/dev/null || true

echo "[3/5] Stopping service (if running)..."
systemctl stop ma-scanner-ai-research.service 2>/dev/null || true

echo "[4/5] Removing unit files..."
rm -f /etc/systemd/system/ma-scanner-ai-research.service
rm -f /etc/systemd/system/ma-scanner-ai-research.timer

echo "[5/5] Reloading systemd daemon..."
systemctl daemon-reload

echo ""
echo "AI research timer uninstalled. Live scanner timer unchanged."
echo ""
echo "Remaining MA Scanner timers:"
systemctl list-timers | grep ma-scanner || echo "  (none)"
