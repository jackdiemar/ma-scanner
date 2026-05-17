#!/bin/bash
# setup_ubuntu_server.sh — Prepare a fresh Ubuntu VPS to run the MA Scanner.
#
# What this does:
#   1. Installs system packages (python3, venv, pip, git, curl)
#   2. Creates the repo directory at INSTALL_DIR
#   3. Creates a Python virtualenv at INSTALL_DIR/.venv
#   4. Installs Python dependencies from requirements.txt
#   5. Creates required data and log directories
#   6. Prints next steps — you must add config/.env manually (never in git)
#
# Usage:
#   sudo bash deploy/vps/setup_ubuntu_server.sh
#   # or from /opt/ma-scanner after cloning:
#   sudo bash deploy/vps/setup_ubuntu_server.sh
#
# Environment variables (override defaults):
#   INSTALL_DIR   — where the repo lives (default: /opt/ma-scanner)
#   REPO_USER     — Linux user who will own the files (default: current user or 'ubuntu')
#
# Requirements:
#   Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
#   Root or sudo access

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
INSTALL_DIR="${INSTALL_DIR:-/opt/ma-scanner}"
REPO_USER="${REPO_USER:-${SUDO_USER:-ubuntu}}"
PYTHON_MIN="3.10"

# ── Color output ──────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Must run as root ──────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  error "Run as root: sudo bash deploy/vps/setup_ubuntu_server.sh"
fi

info "=== MA Scanner VPS Setup ==="
info "Install dir : $INSTALL_DIR"
info "Repo user   : $REPO_USER"

# ── Step 1: System packages ───────────────────────────────────────────────────
info "Updating apt and installing system packages..."
apt-get update -q
apt-get install -y -q \
  python3 \
  python3-venv \
  python3-pip \
  git \
  curl \
  ca-certificates

# Verify Python version meets minimum
PYTHON_BIN=$(command -v python3)
PYTHON_VER=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python version: $PYTHON_VER (minimum required: $PYTHON_MIN)"

# ── Step 2: Create and own install directory ──────────────────────────────────
info "Creating install directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
chown -R "$REPO_USER:$REPO_USER" "$INSTALL_DIR"

# ── Step 3: Create Python virtualenv ─────────────────────────────────────────
VENV_DIR="$INSTALL_DIR/.venv"
if [[ -d "$VENV_DIR" ]]; then
  warn "Virtualenv already exists at $VENV_DIR — skipping creation."
else
  info "Creating virtualenv at $VENV_DIR..."
  sudo -u "$REPO_USER" "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

VENV_PIP="$VENV_DIR/bin/pip"
VENV_PYTHON="$VENV_DIR/bin/python"

info "Upgrading pip inside venv..."
sudo -u "$REPO_USER" "$VENV_PIP" install --quiet --upgrade pip

# ── Step 4: Install Python dependencies ──────────────────────────────────────
REQ_FILE="$INSTALL_DIR/requirements.txt"
if [[ -f "$REQ_FILE" ]]; then
  info "Installing requirements from requirements.txt..."
  sudo -u "$REPO_USER" "$VENV_PIP" install --quiet -r "$REQ_FILE"
else
  warn "requirements.txt not found at $REQ_FILE. Skipping pip install."
  warn "Clone the repo first, then re-run this script."
fi

# ── Step 5: Create required directories ──────────────────────────────────────
info "Creating data and log directories..."
DIRS=(
  "$INSTALL_DIR/data/scans"
  "$INSTALL_DIR/data/live_monitoring/runs"
  "$INSTALL_DIR/data/predictions"
  "$INSTALL_DIR/data/tracking"
  "$INSTALL_DIR/config"
  "$INSTALL_DIR/logs"
)
for d in "${DIRS[@]}"; do
  mkdir -p "$d"
done
chown -R "$REPO_USER:$REPO_USER" "$INSTALL_DIR/data" "$INSTALL_DIR/logs" "$INSTALL_DIR/config"

# ── Step 6: Verify key files are present ─────────────────────────────────────
info "Checking for required source files..."
REQUIRED_FILES=(
  "$INSTALL_DIR/src/PRODUCTION_SCANNER_V12.py"
  "$INSTALL_DIR/src/live_monitoring/live_scanner_runner.py"
)
for f in "${REQUIRED_FILES[@]}"; do
  if [[ -f "$f" ]]; then
    info "  [OK] $f"
  else
    warn "  [MISSING] $f — clone the repo first, then re-run."
  fi
done

# ── Step 7: Check for config/.env (never create or populate it here) ──────────
ENV_FILE="$INSTALL_DIR/config/.env"
if [[ -f "$ENV_FILE" ]]; then
  info "config/.env exists. Verifying it is not world-readable..."
  chmod 600 "$ENV_FILE"
  chown "$REPO_USER:$REPO_USER" "$ENV_FILE"
else
  warn "config/.env not found — you must create it before the scanner will run."
fi

# ── Done — Print next steps ───────────────────────────────────────────────────
echo ""
info "=== Setup complete ==="
echo ""
echo "Next steps:"
echo ""
echo "  1. If you haven't cloned the repo yet:"
echo "       sudo git clone <your-repo-url> $INSTALL_DIR"
echo "       sudo chown -R $REPO_USER:$REPO_USER $INSTALL_DIR"
echo "       sudo bash $INSTALL_DIR/deploy/vps/setup_ubuntu_server.sh   # re-run to install deps"
echo ""
echo "  2. Create config/.env (NEVER commit this file):"
echo "       sudo -u $REPO_USER nano $INSTALL_DIR/config/.env"
echo "     Contents:"
echo "       FMP_API_KEY=your_key_here"
echo "       SMTP_USER=your_email@example.com"
echo "       SMTP_PASSWORD=your_smtp_password"
echo "       SMTP_RECIPIENT=recipient@example.com"
echo "       chmod 600 $INSTALL_DIR/config/.env"
echo ""
echo "  3. Install the hourly systemd timer:"
echo "       sudo bash $INSTALL_DIR/deploy/vps/install_systemd_service.sh"
echo ""
echo "  4. Check status:"
echo "       bash $INSTALL_DIR/deploy/vps/check_server_status.sh"
echo ""
echo "  5. View logs:"
echo "       journalctl -u ma-scanner-live.service -n 50"
echo ""
