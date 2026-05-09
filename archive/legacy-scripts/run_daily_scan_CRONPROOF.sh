#!/bin/bash
#
# Daily M&A Scanner - CRON-PROOF VERSION
# Works from cron with full paths and environment
#

# Set full paths (cron doesn't have your PATH)
PYTHON3=/usr/bin/python3
SCANNER_DIR=/Users/jack/Downloads/ma-scanner

# Change to scanner directory
cd "$SCANNER_DIR" || exit 1

# Set up Python environment
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# Log start
echo "================================" >> "$SCANNER_DIR/logs/scan.log"
echo "Scan started: $(date)" >> "$SCANNER_DIR/logs/scan.log"
echo "Python: $PYTHON3" >> "$SCANNER_DIR/logs/scan.log"
echo "Working dir: $(pwd)" >> "$SCANNER_DIR/logs/scan.log"

# Step 1: Run scanner with full path
echo "Running scanner..." >> "$SCANNER_DIR/logs/scan.log"
$PYTHON3 "$SCANNER_DIR/src/PRODUCTION_SCANNER_V10_6.py" >> "$SCANNER_DIR/logs/scan.log" 2>&1

if [ $? -ne 0 ]; then
    echo "✗ Scanner failed at $(date)" >> "$SCANNER_DIR/logs/scan.log"
    exit 1
fi

# Step 2: Find most recent scan file
SCAN_FILE=$(ls -t "$SCANNER_DIR"/data/scans/scan_v10_*.json 2>/dev/null | head -1)

if [ -z "$SCAN_FILE" ]; then
    echo "✗ No scan file found at $(date)" >> "$SCANNER_DIR/logs/scan.log"
    exit 1
fi

echo "✓ Scanner completed: $(basename $SCAN_FILE)" >> "$SCANNER_DIR/logs/scan.log"

# Step 3: Send email
echo "Sending email..." >> "$SCANNER_DIR/logs/scan.log"
$PYTHON3 "$SCANNER_DIR/src/send_alert.py" "$SCAN_FILE" >> "$SCANNER_DIR/logs/scan.log" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Email sent successfully at $(date)" >> "$SCANNER_DIR/logs/scan.log"
else
    echo "✗ Email failed at $(date)" >> "$SCANNER_DIR/logs/scan.log"
    exit 1
fi

echo "✓ Daily scan completed at $(date)" >> "$SCANNER_DIR/logs/scan.log"
echo "" >> "$SCANNER_DIR/logs/scan.log"

exit 0
