#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

swift build -c release

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
cp .build/release/ClaudeMeter "$BIN_DIR/claude-meter-widget"

PLIST_DST="$HOME/Library/LaunchAgents/com.snstanton.claudemeter.plist"
sed "s#__BIN_PATH__#$BIN_DIR/claude-meter-widget#" com.snstanton.claudemeter.plist > "$PLIST_DST"

launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "Installed and started. Check with: launchctl list | grep claudemeter"
echo "Budget config: ~/.claude-meter/config.json"
