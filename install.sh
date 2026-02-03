#!/usr/bin/env bash
# Install dependencies per Playwright Python: https://playwright.dev/python/docs/intro
# Usage: ./install.sh

set -e
cd "$(dirname "$0")"

# Create venv if missing
if [ ! -d "venv" ]; then
  echo "Creating venv..."
  python3 -m venv venv
fi

PYTHON="venv/bin/python"
PLAYWRIGHT="venv/bin/playwright"

echo "Installing Python dependencies (playwright, etc.)..."
"$PYTHON" -m pip install -r requirements.txt

echo "Installing Playwright browsers (Chromium)..."
"$PLAYWRIGHT" install chromium

echo "Done. Run: ./run.sh"
