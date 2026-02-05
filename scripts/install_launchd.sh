#!/bin/bash
# Daily-Bot macOS launchd Installation
# Creates a launchd plist that runs daily and wakes from sleep

set -e

echo "================================================"
echo "Daily-Bot launchd Setup"
echo "================================================"

# Get paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
MAIN_SCRIPT="$PROJECT_DIR/main.py"
PLIST_PATH="$HOME/Library/LaunchAgents/com.daily-bot.plist"

# Verify paths
if [ ! -f "$PYTHON_PATH" ]; then
    echo "ERROR: Python virtual environment not found"
    echo "Please run setup_macos.sh first"
    exit 1
fi

# Get schedule time
read -p "Enter schedule time (HH:MM, 24-hour format) [default: 07:00]: " SCHEDULE_TIME
SCHEDULE_TIME=${SCHEDULE_TIME:-07:00}

# Parse time
HOUR=$(echo "$SCHEDULE_TIME" | cut -d: -f1)
MINUTE=$(echo "$SCHEDULE_TIME" | cut -d: -f2)

# Remove leading zeros for plist
HOUR=$((10#$HOUR))
MINUTE=$((10#$MINUTE))

echo ""
echo "Creating launchd plist..."
echo "  Time: $SCHEDULE_TIME"
echo "  Python: $PYTHON_PATH"
echo "  Script: $MAIN_SCRIPT"
echo ""

# Create LaunchAgents directory if not exists
mkdir -p "$HOME/Library/LaunchAgents"

# Unload existing plist if exists
if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# Create plist file
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.daily-bot</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$MAIN_SCRIPT</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>$HOUR</integer>
        <key>Minute</key>
        <integer>$MINUTE</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/launchd_stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/launchd_stderr.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF

# Load the plist
launchctl load "$PLIST_PATH"

echo ""
echo "================================================"
echo "launchd plist created successfully!"
echo "================================================"
echo ""
echo "Plist Location: $PLIST_PATH"
echo "Schedule: Daily at $SCHEDULE_TIME"
echo ""
echo "To enable wake from sleep, run:"
echo "  sudo pmset repeat wakeorpoweron MTWRFSU $SCHEDULE_TIME"
echo ""
echo "Commands:"
echo "  View:    launchctl list | grep daily-bot"
echo "  Run now: launchctl start com.daily-bot"
echo "  Stop:    launchctl stop com.daily-bot"
echo "  Unload:  launchctl unload $PLIST_PATH"
echo ""

# Ask about wake from sleep
read -p "Do you want to enable wake from sleep? (requires sudo) [y/N]: " ENABLE_WAKE
if [[ "$ENABLE_WAKE" =~ ^[Yy]$ ]]; then
    echo "Setting up wake from sleep..."
    sudo pmset repeat wakeorpoweron MTWRFSU "$SCHEDULE_TIME"
    echo "Wake from sleep enabled!"
fi
