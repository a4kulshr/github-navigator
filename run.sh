#!/usr/bin/env bash
# One-command runner: loads .env and runs the navigator.
# Usage: ./run.sh [OPTIONS]
# Example: ./run.sh
#          ./run.sh --repo "owner/repo" --debug
#          ./run.sh --no-headless

set -e
cd "$(dirname "$0")"

# Use venv if present
if [ -d "venv" ]; then
  PYTHON="venv/bin/python"
else
  PYTHON="python3"
fi

exec "$PYTHON" navigate.py --repo "openclaw/openclaw" --provider gemini "$@"
