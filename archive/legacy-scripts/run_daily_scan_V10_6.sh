#!/bin/bash
#
# Daily M&A Scanner - V10.6
# Runs src/PRODUCTION_SCANNER_V10_6.py, then emails with src/send_alert.py
#

# Set working directory
cd /Users/jack/Downloads/ma-scanner || exit 1

# Log start
echo "================================" >> logs/scan.log
echo "Scan started: $(date)" >> logs/scan.log

# Step 1: Run the V10.6 scanner
echo "Running src/PRODUCTION_SCANNER_V10_6.py..." >> logs/scan.log
python3 src/PRODUCTION_SCANNER_V10_6.py >> logs/scan.log 2>&1

if [ $? -ne 0 ]; then
    echo "✗ Scanner failed" >> logs/scan.log
    exit 1
fi

# Step 2: Find the most recent scan JSON file
SCAN_FILE=$(ls -t data/scans/scan_v10_*.json 2>/dev/null | head -1)

if [ -z "$SCAN_FILE" ]; then
    echo "✗ No scan file created" >> logs/scan.log
    exit 1
fi

echo "✓ Scanner completed: $SCAN_FILE" >> logs/scan.log

# Step 3: Send email with results
echo "Sending email with src/send_alert.py..." >> logs/scan.log
python3 src/send_alert.py "$SCAN_FILE" >> logs/scan.log 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Email sent successfully at $(date)" >> logs/scan.log
else
    echo "✗ Email failed at $(date)" >> logs/scan.log
    exit 1
fi

echo "✓ Daily scan completed successfully" >> logs/scan.log
echo "" >> logs/scan.log
