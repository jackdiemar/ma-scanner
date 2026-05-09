#!/bin/bash
set -euo pipefail

SCANNER_DIR=/Users/jack/Downloads/ma-scanner
PYTHON=${PYTHON:-$(command -v python3)}
LOG="$SCANNER_DIR/logs/scanner_v12.log"
ERROR_LOG="$SCANNER_DIR/logs/scanner_v12_error.log"

cd "$SCANNER_DIR"
mkdir -p logs data/scans data/predictions data/tracking

if [ -f "$SCANNER_DIR/config/.env" ]; then
  set -a
  . "$SCANNER_DIR/config/.env"
  set +a
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting M&A Scanner V12" >> "$LOG"
"$PYTHON" "$SCANNER_DIR/src/PRODUCTION_SCANNER_V12.py" >> "$LOG" 2>> "$ERROR_LOG"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Scan complete, sending email" >> "$LOG"
"$PYTHON" "$SCANNER_DIR/src/send_alert_v12.py" >> "$LOG" 2>> "$ERROR_LOG"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Finished" >> "$LOG"
