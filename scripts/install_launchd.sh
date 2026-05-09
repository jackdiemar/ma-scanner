#!/bin/bash
#
# Install M&A Scanner V12 as macOS LaunchAgent
#

echo "Installing M&A Scanner LaunchAgent..."

# Copy plist to LaunchAgents folder
cp scripts/com.blackstarlightcapital.mascanner.plist ~/Library/LaunchAgents/

# Load the agent
launchctl load ~/Library/LaunchAgents/com.blackstarlightcapital.mascanner.plist

echo ""
echo "✓ LaunchAgent installed!"
echo ""
echo "Scanner V12 will run daily at 8:00 AM"
echo ""
echo "To test it now:"
echo "  launchctl start com.blackstarlightcapital.mascanner"
echo ""
echo "To check status:"
echo "  launchctl list | grep mascanner"
echo ""
echo "To view logs:"
echo "  tail -f ~/Downloads/ma-scanner/logs/launchd.log"
echo ""
echo "To uninstall:"
echo "  launchctl unload ~/Library/LaunchAgents/com.blackstarlightcapital.mascanner.plist"
echo ""
