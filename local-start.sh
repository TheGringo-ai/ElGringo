#!/usr/bin/env bash
# ============================================================
# DEPRECATED — Use local-code-agent.sh instead
# ============================================================
# This script starts old/unused services (Chat UI, Studio, etc.)
# The coding agent is the only local service that matters now.
# Run: ./local-code-agent.sh start
# ============================================================
echo "DEPRECATED: Use ./local-code-agent.sh instead"
echo "  ./local-code-agent.sh start   # start coding agent"
echo "  ./local-code-agent.sh stop    # stop it"
exit 0
# ============================================================
# OLD CODE BELOW (kept for reference)
# ============================================================
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv/bin"
ENV_FILE="$DIR/.env"
LOG_DIR="$DIR/logs"

mkdir -p "$LOG_DIR"

# Load environment
set -a
source "$ENV_FILE"
set +a
export PYTHONPATH="$DIR"

# Override Gradio auth for local use
export GRADIO_USERNAME="${GRADIO_USERNAME:-yoyofred}"
export GRADIO_PASSWORD="${GRADIO_PASSWORD:-@Gringo420}"

# No root_path needed locally (not behind nginx)
unset GRADIO_ROOT_PATH

echo "============================================================"
echo "  El Gringo Local Services"
echo "============================================================"
echo ""

# Function to start a service in the background
start_service() {
    local name="$1"
    local port="$2"
    local cmd="$3"
    echo "  Starting $name on port $port..."
    PORT=$port $VENV/$cmd >> "$LOG_DIR/$name.log" 2>&1 &
    echo $! > "$LOG_DIR/$name.pid"
}

# Start services
start_service "chat"       7860 "python -m elgringo.chat_ui"
start_service "studio"     7861 "python -m elgringo.studio_ui"
start_service "code-audit" 8081 "uvicorn products.code_audit.server:app --host 127.0.0.1 --port 8081 --log-level info"
start_service "test-gen"   8082 "uvicorn products.test_generator.server:app --host 127.0.0.1 --port 8082 --log-level info"
start_service "doc-gen"    8083 "uvicorn products.doc_generator.server:app --host 127.0.0.1 --port 8083 --log-level info"
start_service "cmd-api"    7862 "uvicorn products.command_center.server:app --host 127.0.0.1 --port 7862 --reload --log-level info"

# Command Center React frontend (Vite dev server with API proxy)
FRONTEND_DIR="$DIR/products/command_center/frontend"
if [ -d "$FRONTEND_DIR/node_modules" ]; then
    echo "  Starting cmd-ui on port 5173..."
    (cd "$FRONTEND_DIR" && npx vite --port 5173 >> "$LOG_DIR/cmd-ui.log" 2>&1) &
    echo $! > "$LOG_DIR/cmd-ui.pid"
else
    echo "  Skipping cmd-ui (run 'npm install' in products/command_center/frontend first)"
fi

# Fred Assistant (local AI personal assistant)
start_service "fred-api" 7870 "uvicorn products.fred_assistant.server:app --host 127.0.0.1 --port 7870 --reload --log-level info"
FRED_FRONTEND="$DIR/products/fred_assistant/frontend"
if [ -d "$FRED_FRONTEND/node_modules" ]; then
    echo "  Starting fred-ui on port 5174..."
    (cd "$FRED_FRONTEND" && npx vite --port 5174 >> "$LOG_DIR/fred-ui.log" 2>&1) &
    echo $! > "$LOG_DIR/fred-ui.pid"
else
    echo "  Skipping fred-ui (run 'npm install' in products/fred_assistant/frontend first)"
fi

echo ""
echo "  Waiting for services to start..."
sleep 5

# Health checks
echo ""
echo "=== Local Services ==="
curl -s -o /dev/null -w "  Chat UI:     http://localhost:7860  HTTP %{http_code}\n" http://127.0.0.1:7860/ 2>/dev/null || echo "  Chat UI:     http://localhost:7860  starting..."
curl -s -o /dev/null -w "  Studio:      http://localhost:7861  HTTP %{http_code}\n" http://127.0.0.1:7861/ 2>/dev/null || echo "  Studio:      http://localhost:7861  starting..."
curl -s -o /dev/null -w "  Code Audit:  http://localhost:8081  HTTP %{http_code}\n" http://127.0.0.1:8081/audit/health 2>/dev/null || echo "  Code Audit:  http://localhost:8081  starting..."
curl -s -o /dev/null -w "  Test Gen:    http://localhost:8082  HTTP %{http_code}\n" http://127.0.0.1:8082/tests/health 2>/dev/null || echo "  Test Gen:    http://localhost:8082  starting..."
curl -s -o /dev/null -w "  Doc Gen:     http://localhost:8083  HTTP %{http_code}\n" http://127.0.0.1:8083/docs/health 2>/dev/null || echo "  Doc Gen:     http://localhost:8083  starting..."
curl -s -o /dev/null -w "  Cmd API:     http://localhost:7862  HTTP %{http_code}\n" http://127.0.0.1:7862/health 2>/dev/null || echo "  Cmd API:     http://localhost:7862  starting..."
curl -s -o /dev/null -w "  Command UI:  http://localhost:5173  HTTP %{http_code}\n" http://127.0.0.1:5173/ 2>/dev/null || echo "  Command UI:  http://localhost:5173  starting..."
curl -s -o /dev/null -w "  Fred API:    http://localhost:7870  HTTP %{http_code}\n" http://127.0.0.1:7870/health 2>/dev/null || echo "  Fred API:    http://localhost:7870  starting..."
curl -s -o /dev/null -w "  Fred UI:     http://localhost:5174  HTTP %{http_code}\n" http://127.0.0.1:5174/ 2>/dev/null || echo "  Fred UI:     http://localhost:5174  starting..."

echo ""
echo "=== VM Services (ai.chatterfix.com) ==="
echo "  API Server:  https://ai.chatterfix.com/api/health"
echo "  PR Bot:      https://ai.chatterfix.com/webhook"
echo "  Fred API:    https://ai.chatterfix.com/v1/health"

echo ""
echo "============================================================"
echo "  Press Ctrl+C to stop all local services"
echo "============================================================"

# Trap Ctrl+C to kill all background services
cleanup() {
    echo ""
    echo "Stopping local services..."
    for pidfile in "$LOG_DIR"/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            kill "$pid" 2>/dev/null || true
            rm -f "$pidfile"
        fi
    done
    echo "All local services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

# Wait for Ctrl+C
wait
