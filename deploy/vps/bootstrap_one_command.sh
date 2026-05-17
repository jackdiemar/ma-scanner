#!/bin/bash
# bootstrap_one_command.sh — Near one-click VPS bootstrap for MA Scanner live monitor.
#
# Usage after SSH on a fresh Ubuntu VPS:
#   sudo REPO_URL="https://github.com/USER/REPO.git" FMP_API_KEY="..." bash deploy/vps/bootstrap_one_command.sh
#   sudo REPO_URL="git@github.com:USER/REPO.git" bash deploy/vps/bootstrap_one_command.sh
#
# Safe defaults:
#   INSTALL_DIR=/opt/ma-scanner
#   BRANCH=main
#   REPO_USER=ubuntu
#
# This script does not print secrets, connect to broker APIs, place trades, or
# run a live scanner pass. It performs setup, status checks, systemd install,
# and health checks only.

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/ma-scanner}"
BRANCH="${BRANCH:-main}"
REPO_USER="${REPO_USER:-ubuntu}"
REPO_URL="${REPO_URL:-}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

if [[ $EUID -ne 0 ]]; then
  error "Run as root: sudo REPO_URL=... bash deploy/vps/bootstrap_one_command.sh"
fi

info "=== MA Scanner one-command VPS bootstrap ==="
info "Install dir : $INSTALL_DIR"
info "Branch      : $BRANCH"
info "Repo user   : $REPO_USER"

if ! id "$REPO_USER" >/dev/null 2>&1; then
  warn "User '$REPO_USER' does not exist. Creating a locked service user."
  useradd --create-home --shell /bin/bash "$REPO_USER"
  passwd -l "$REPO_USER" >/dev/null 2>&1 || true
fi

info "Installing required OS packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q \
  git \
  python3 \
  python3-venv \
  python3-pip \
  curl \
  ca-certificates

if [[ -d "$INSTALL_DIR/.git" ]]; then
  info "Repo already exists. Pulling latest code..."
  git -C "$INSTALL_DIR" fetch origin "$BRANCH"
  git -C "$INSTALL_DIR" checkout "$BRANCH"
  git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
elif [[ -e "$INSTALL_DIR" ]] && [[ -n "$(find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
  error "$INSTALL_DIR exists and is not an empty git repo. Move it aside or set INSTALL_DIR."
else
  [[ -n "$REPO_URL" ]] || error "REPO_URL is required when $INSTALL_DIR is not already cloned."
  info "Cloning repo into $INSTALL_DIR..."
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

chown -R "$REPO_USER:$REPO_USER" "$INSTALL_DIR"

info "Running base Ubuntu setup script..."
REPO_USER="$REPO_USER" INSTALL_DIR="$INSTALL_DIR" bash "$INSTALL_DIR/deploy/vps/setup_ubuntu_server.sh"

VENV_PYTHON="$INSTALL_DIR/.venv/bin/python"
VENV_PIP="$INSTALL_DIR/.venv/bin/pip"
ENV_FILE="$INSTALL_DIR/config/.env"
ENV_EXAMPLE="$INSTALL_DIR/config/.env.example"

info "Ensuring Python virtualenv and requirements are current..."
if [[ ! -x "$VENV_PYTHON" ]]; then
  sudo -u "$REPO_USER" python3 -m venv "$INSTALL_DIR/.venv"
fi
sudo -u "$REPO_USER" "$VENV_PIP" install --quiet --upgrade pip
sudo -u "$REPO_USER" "$VENV_PIP" install --quiet -r "$INSTALL_DIR/requirements.txt"

info "Preparing config/.env..."
mkdir -p "$INSTALL_DIR/config"
if [[ "${FMP_API_KEY:-}" == "FMP_API_KEY_PLACEHOLDER" ]]; then
  FMP_API_KEY=""
fi
if [[ -f "$ENV_FILE" ]]; then
  info "config/.env already exists. Leaving values unchanged."
elif [[ -n "${FMP_API_KEY:-}" ]]; then
  info "FMP_API_KEY provided through environment. Writing config/.env without printing secrets."
  umask 177
  {
    printf 'FMP_API_KEY=%s\n' "$FMP_API_KEY"
    printf 'SMTP_USER=%s\n' "${SMTP_USER:-}"
    printf 'SMTP_PASSWORD=%s\n' "${SMTP_PASSWORD:-}"
    printf 'SMTP_RECIPIENT=%s\n' "${SMTP_RECIPIENT:-}"
  } > "$ENV_FILE"
else
  warn "FMP_API_KEY not provided. Creating safe config/.env template."
  if [[ -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
  else
    {
      echo "FMP_API_KEY="
      echo "SMTP_USER="
      echo "SMTP_PASSWORD="
      echo "SMTP_RECIPIENT="
    } > "$ENV_FILE"
  fi
fi
chmod 600 "$ENV_FILE"
chown "$REPO_USER:$REPO_USER" "$ENV_FILE"

info "Running shell syntax checks..."
bash -n "$INSTALL_DIR/deploy/vps/bootstrap_one_command.sh"
bash -n "$INSTALL_DIR/deploy/vps/post_deploy_check.sh" 2>/dev/null || true
bash -n "$INSTALL_DIR/deploy/vps/setup_ubuntu_server.sh"
bash -n "$INSTALL_DIR/deploy/vps/install_systemd_service.sh"
bash -n "$INSTALL_DIR/deploy/vps/uninstall_systemd_service.sh"
bash -n "$INSTALL_DIR/deploy/vps/check_server_status.sh"

info "Running Python compile checks..."
"$VENV_PYTHON" -m py_compile \
  "$INSTALL_DIR/src/live_monitoring/live_scanner_runner.py" \
  "$INSTALL_DIR/src/live_monitoring/health_check.py"

info "Running live scanner status check (no scan)..."
sudo -u "$REPO_USER" "$VENV_PYTHON" "$INSTALL_DIR/src/live_monitoring/live_scanner_runner.py" --status || true

info "Installing systemd service and hourly timer..."
INSTALL_DIR="$INSTALL_DIR" REPO_USER="$REPO_USER" bash "$INSTALL_DIR/deploy/vps/install_systemd_service.sh"

info "Running server status check..."
bash "$INSTALL_DIR/deploy/vps/check_server_status.sh" || true

info "Running health check..."
sudo -u "$REPO_USER" "$VENV_PYTHON" "$INSTALL_DIR/src/live_monitoring/health_check.py" || true

echo ""
info "=== Bootstrap complete ==="
echo ""
echo "Next steps:"
echo "  1. If config/.env contains blanks, edit it now:"
echo "       sudo nano $ENV_FILE"
echo "       sudo chmod 600 $ENV_FILE"
echo ""
echo "  2. Check deployment health:"
echo "       bash $INSTALL_DIR/deploy/vps/post_deploy_check.sh"
echo ""
echo "  3. Check timer:"
echo "       systemctl list-timers ma-scanner-live.timer"
echo ""
echo "  4. View scanner logs:"
echo "       journalctl -u ma-scanner-live.service -n 50 --no-pager"
echo ""
echo "  5. Force one run only after secrets are set:"
echo "       sudo systemctl start ma-scanner-live.service"
echo ""
echo "  6. Stop/uninstall if needed:"
echo "       sudo systemctl stop ma-scanner-live.timer"
echo "       sudo bash $INSTALL_DIR/deploy/vps/uninstall_systemd_service.sh"
echo ""
echo "Secrets were not printed. No live scanner pass was run by this bootstrap."
