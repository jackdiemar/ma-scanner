#!/bin/bash
# Generates a launchd plist for live_scanner_runner --daemon.
# Does NOT auto-install. Run manually:
#   bash scripts/install_live_scanner_launchd.sh
# Then review the generated plist and load it:
#   cp /tmp/com.blackstarlightcapital.livescanner.plist ~/Library/LaunchAgents/
#   launchctl load ~/Library/LaunchAgents/com.blackstarlightcapital.livescanner.plist

SCANNER_DIR=/Users/jack/Downloads/ma-scanner
PYTHON=$(command -v python3)
INTERVAL_SECONDS=3600   # 60 minutes
PLIST_PATH=/tmp/com.blackstarlightcapital.livescanner.plist

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.blackstarlightcapital.livescanner</string>

  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$SCANNER_DIR/src/live_monitoring/live_scanner_runner.py</string>
    <string>--once</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$SCANNER_DIR</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin</string>
  </dict>

  <key>StartInterval</key>
  <integer>$INTERVAL_SECONDS</integer>

  <key>RunAtLoad</key>
  <true/>

  <key>StandardOutPath</key>
  <string>$SCANNER_DIR/data/live_monitoring/live_scanner_launchd.log</string>

  <key>StandardErrorPath</key>
  <string>$SCANNER_DIR/data/live_monitoring/live_scanner_errors.log</string>
</dict>
</plist>
EOF

echo "Plist written to: $PLIST_PATH"
echo ""
echo "To install:"
echo "  cp $PLIST_PATH ~/Library/LaunchAgents/"
echo "  launchctl load ~/Library/LaunchAgents/com.blackstarlightcapital.livescanner.plist"
echo ""
echo "To uninstall:"
echo "  launchctl unload ~/Library/LaunchAgents/com.blackstarlightcapital.livescanner.plist"
echo "  rm ~/Library/LaunchAgents/com.blackstarlightcapital.livescanner.plist"
