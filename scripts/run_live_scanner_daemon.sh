#!/bin/bash
set -euo pipefail

SCANNER_DIR=/Users/jack/Downloads/ma-scanner
PYTHON=${PYTHON:-$(command -v python3)}
LOG="$SCANNER_DIR/data/live_monitoring/live_scanner_stdout.log"
INTERVAL=${INTERVAL_MINUTES:-60}

cd "$SCANNER_DIR"
mkdir -p data/live_monitoring

if [ -f "$SCANNER_DIR/config/.env" ]; then
  set -a
  . "$SCANNER_DIR/config/.env"
  set +a
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - live_scanner_runner --daemon --interval-minutes $INTERVAL" >> "$LOG"
"$PYTHON" "$SCANNER_DIR/src/live_monitoring/live_scanner_runner.py" \
  --daemon --interval-minutes "$INTERVAL" "$@" 2>&1 | tee -a "$LOG"
