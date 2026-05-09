#!/bin/bash
set -euo pipefail

cd /Users/jack/Downloads/ma-scanner

echo "Installing M&A Scanner V12 dependencies..."
mkdir -p data/scans data/predictions data/tracking data/cache logs
python3 -m pip install -r docs/requirements.txt --break-system-packages

echo "Verifying active V12 files..."
test -f src/PRODUCTION_SCANNER_V12.py
test -f src/trade_logic.py
test -f src/scanner_cache.py
test -f src/outcome_tracker.py
test -f src/send_alert_v12.py

echo "Done. Run: scripts/run_scanner_v12.sh"
