#!/usr/bin/env bash
set -euo pipefail

if [ ! -f ".venv/bin/python" ]; then
  echo "Virtual environment not found. Run this first:"
  echo "  bash scripts/first_run_mac.sh"
  exit 1
fi

.venv/bin/python -m app.main
