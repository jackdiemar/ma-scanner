#!/bin/bash
#
# Daily M&A Scanner - WITH PROGRESS TRACKING
# Shows what's happening in real-time
#

# Set full paths
PYTHON3=/usr/bin/python3
SCANNER_DIR=/Users/jack/Downloads/ma-scanner

# Change to scanner directory
cd "$SCANNER_DIR" || exit 1

# Set up Python environment
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# Clear screen and show header
clear
echo "========================================"
echo "  M&A SCANNER - DAILY RUN"
echo "  Started: $(date)"
echo "========================================"
echo ""

# Log start
echo "================================" >> "$SCANNER_DIR/logs/scan.log"
echo "Scan started: $(date)" >> "$SCANNER_DIR/logs/scan.log"

# Step 1: Run scanner
echo "[1/3] Running scanner..."
echo "       This may take 5-10 minutes..."
echo ""

$PYTHON3 "$SCANNER_DIR/src/PRODUCTION_SCANNER_V10_6.py" 2>&1 | tee -a "$SCANNER_DIR/logs/scan.log"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo ""
    echo "✗ Scanner failed!"
    echo "Check scan.log for details"
    exit 1
fi

echo ""
echo "✓ Scanner completed"
echo ""

# Step 2: Find scan file
echo "[2/3] Looking for scan results..."
SCAN_FILE=$(ls -t "$SCANNER_DIR"/data/scans/scan_v10_*.json 2>/dev/null | head -1)

if [ -z "$SCAN_FILE" ]; then
    echo "✗ No scan file found!"
    exit 1
fi

echo "✓ Found: $(basename $SCAN_FILE)"
echo ""

# Step 3: Send email
echo "[3/3] Sending email..."
$PYTHON3 "$SCANNER_DIR/src/send_alert.py" "$SCAN_FILE" 2>&1 | tee -a "$SCANNER_DIR/logs/scan.log"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✓ COMPLETE - Email sent successfully"
    echo "  Finished: $(date)"
    echo "========================================"
    echo ""
else
    echo ""
    echo "✗ Email failed"
    echo "Check scan.log for details"
    exit 1
fi

exit 0
