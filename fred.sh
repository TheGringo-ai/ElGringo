#!/usr/bin/env bash
# ============================================================
# Fred Assistant — Quick Start
# Launches just the personal assistant (API + UI)
# ============================================================
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv/bin"
LOG_DIR="$DIR/logs"

mkdir -p "$LOG_DIR"

# Load environment
if [ -f "$DIR/.env" ]; then
    set -a; source "$DIR/.env"; set +a
fi
export PYTHONPATH="$DIR"

echo "============================================"
echo "  🧠 Fred Assistant"
echo "============================================"
echo ""

# Start API
echo "  Starting Fred API on port 7870..."
PORT=7870 $VENV/uvicorn products.fred_assistant.server:app \
    --host 127.0.0.1 --port 7870 --reload --log-level info \
    >> "$LOG_DIR/fred-api.log" 2>&1 &
API_PID=$!

# Start UI
FRONTEND="$DIR/products/fred_assistant/frontend"
if [ -d "$FRONTEND/node_modules" ]; then
    echo "  Starting Fred UI on port 5174..."
    (cd "$FRONTEND" && npx vite --port 5174 >> "$LOG_DIR/fred-ui.log" 2>&1) &
    UI_PID=$!
else
    echo "  Installing frontend dependencies..."
    (cd "$FRONTEND" && npm install && npx vite --port 5174 >> "$LOG_DIR/fred-ui.log" 2>&1) &
    UI_PID=$!
fi

sleep 3

echo ""
echo "  Fred API:  http://localhost:7870/docs"
echo "  Fred UI:   http://localhost:5174"
echo ""
echo "  Data:      ~/.fred-assistant/fred.db"
echo "============================================"
echo "  Press Ctrl+C to stop"
echo "============================================"

# Open browser
if command -v open &>/dev/null; then
    sleep 2 && open "http://localhost:5174" &
fi

cleanup() {
    echo ""
    echo "  Shutting down Fred..."
    kill $API_PID 2>/dev/null || true
    kill $UI_PID 2>/dev/null || true
    echo "  Done."
    exit 0
}
trap cleanup SIGINT SIGTERM

wait
