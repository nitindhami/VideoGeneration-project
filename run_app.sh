#!/usr/bin/env bash
# CineShorts AI - Unified Startup Script

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================"
echo "🎬 Starting CineShorts AI Studio..."
echo "========================================================"

# Activate Backend Virtual Environment
if [ -d "$DIR/backend/venv" ]; then
    source "$DIR/backend/venv/bin/activate"
else
    echo "❌ backend/venv not found. Please run: cd backend && python3.11 -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# Ensure storage directories exist
mkdir -p "$DIR/storage/outputs" "$DIR/storage/temp"

# Start Backend Server
echo "🚀 Launching FastAPI Backend on http://localhost:8000..."
python -m uvicorn app.main:app --app-dir "$DIR/backend" --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Trap Ctrl+C to clean up background processes
trap "echo 'Shutting down CineShorts AI...'; kill $BACKEND_PID 2>/dev/null; exit 0" INT TERM EXIT

# Start Frontend Dev Server
echo "✨ Launching Creator Studio Frontend on http://localhost:5173..."
cd "$DIR/frontend"
npm run dev -- --host 0.0.0.0

