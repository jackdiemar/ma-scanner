#!/bin/bash
# BSC M&A Scanner V11.0 — Daily Run Script
# Runs the full scan then sends the email report.

cd /Users/jack/Downloads/ma-scanner

LOG="/Users/jack/Downloads/ma-scanner/logs/scanner.log"
ERROR_LOG="/Users/jack/Downloads/ma-scanner/logs/scanner_error.log"

PYTHON=$(which python3 2>/dev/null || echo /usr/bin/python3)

echo "$(date '+%Y-%m-%d %H:%M:%S') — Starting scan" >> "$LOG"

"$PYTHON" /Users/jack/Downloads/ma-scanner/src/PRODUCTION_SCANNER_V11.py >> "$LOG" 2>> "$ERROR_LOG"
SCAN_CODE=$?

if [ $SCAN_CODE -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — Scan complete, sending email" >> "$LOG"
    "$PYTHON" /Users/jack/Downloads/ma-scanner/src/send_alert_v11.py >> "$LOG" 2>> "$ERROR_LOG"
    EMAIL_CODE=$?
    if [ $EMAIL_CODE -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') — Email sent successfully" >> "$LOG"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') — Email FAILED with code $EMAIL_CODE" >> "$LOG"
    fi
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') — Scan FAILED with code $SCAN_CODE, skipping email" >> "$LOG"
fi
