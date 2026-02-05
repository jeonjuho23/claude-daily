#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Daily-Bot Linux Setup ==="

# Python version check
python3 --version || { echo "Python3 required"; exit 1; }

# Create venv
python3 -m venv "$PROJECT_DIR/venv"
source "$PROJECT_DIR/venv/bin/activate"

# Install dependencies
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Copy .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "Edit .env with your settings: nano $PROJECT_DIR/.env"
fi
chmod 600 "$PROJECT_DIR/.env"

# Create directories
mkdir -p "$PROJECT_DIR/data" "$PROJECT_DIR/logs"

echo ""
echo "Setup complete! Next: edit .env, then run install_systemd.sh"
