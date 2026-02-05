#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="daily-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Python venv check
if [ ! -f "$PROJECT_DIR/venv/bin/python" ]; then
    echo "ERROR: venv not found. Run setup first."
    exit 1
fi

# .env check
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "ERROR: .env not found. Copy from .env.example."
    exit 1
fi
chmod 600 "$PROJECT_DIR/.env"

# Copy service file and replace placeholders
sudo cp "$SCRIPT_DIR/daily-bot.service" "$SERVICE_FILE"
sudo sed -i "s|PLACEHOLDER_DIR|$PROJECT_DIR|g" "$SERVICE_FILE"
sudo sed -i "s|PLACEHOLDER_USER|$(whoami)|g" "$SERVICE_FILE"

# Register with systemd
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo ""
echo "Daily-Bot service installed!"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
