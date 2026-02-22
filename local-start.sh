#!/usr/bin/env bash
# ============================================================
# FredAI Local Services (runs on your Mac)
# Chat UI, Studio, Code Audit, Test Gen, Doc Gen
# VM handles: API Server, PR Bot, Fred API
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
echo "  FredAI Local Services"
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
start_service "chat"       7860 "python -m ai_dev_team.chat_ui"
start_service "studio"     7861 "python -m ai_dev_team.studio_ui"
start_service "code-audit" 8081 "uvicorn products.code_audit.server:app --host 127.0.0.1 --port 8081 --log-level info"
start_service "test-gen"   8082 "uvicorn products.test_generator.server:app --host 127.0.0.1 --port 8082 --log-level info"
start_service "doc-gen"    8083 "uvicorn products.doc_generator.server:app --host 127.0.0.1 --port 8083 --log-level info"

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
