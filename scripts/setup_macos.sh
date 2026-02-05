#!/bin/bash
# Daily-Bot macOS Setup Script
# Sets up Python environment and creates launchd plist

set -e

echo "================================================"
echo "Daily-Bot macOS Setup"
echo "================================================"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Check for Python 3.11+
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.11+ using: brew install python@3.11"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

# Activate virtual environment
source "$PROJECT_DIR/venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -r "$PROJECT_DIR/requirements.txt" --quiet

# Check for .env file
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo ""
    echo "WARNING: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings."
    echo ""
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "Created .env from template. Please edit it with your API keys."
fi

# Create data directory
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"

echo ""
echo "Setup complete!"
echo ""
echo "To run Daily-Bot manually:"
echo "  cd $PROJECT_DIR"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "To install as a launchd service:"
echo "  ./scripts/install_launchd.sh"
echo ""
