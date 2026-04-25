#!/bin/bash

# Test Environment Startup Script for Kirjanpito-ohjelma
# Linux/macOS Version

set -e  # Exit on error

echo
echo "===================================="
echo "Kirjanpito-ohjelma Test Environment"
echo "===================================="
echo

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "[1/4] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[1/4] Virtual environment found"
fi

# Activate virtual environment
echo "[2/4] Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "[3/4] Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1 || {
    echo "ERROR: Failed to install dependencies"
    echo "Trying with --no-cache-dir..."
    pip install --no-cache-dir -r requirements.txt
}

# Start server
echo "[4/4] Starting FastAPI server..."
echo
echo "===================================="
echo "Server running at:"
echo "   http://127.0.0.1:8000"
echo
echo "Default views:"
echo "   - Expenses:   http://127.0.0.1:8000/expenses/"
echo "   - Categories: http://127.0.0.1:8000/categories/"
echo "   - Reports:    http://127.0.0.1:8000/reports/yearly?cost_center_id=1&year=2026"
echo
echo "Press Ctrl+C to stop"
echo "===================================="
echo

.venv/bin/uvicorn app.main:app --reload
