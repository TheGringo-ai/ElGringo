#!/usr/bin/env bash
# ============================================================
# El Gringo Local Coding Agent
# ============================================================
# Runs the fred_api server locally so the AI team can
# read/edit/test code on your Mac. Port 8090.
#
# Usage:
#   ./local-code-agent.sh          # start (foreground)
#   ./local-code-agent.sh start    # start (background)
#   ./local-code-agent.sh stop     # stop background instance
#   ./local-code-agent.sh status   # check if running
#
# Then call:
#   curl -X POST http://localhost:8090/v1/code/task \
#     -H "Authorization: Bearer local" \
#     -H "Content-Type: application/json" \
#     -d '{"task":"fix the bug in utils.py","project_path":"/path/to/project"}'
# ============================================================
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv/bin/python3"
PORT="${PORT:-8090}"
PID_FILE="$DIR/logs/local-code-agent.pid"
LOG_FILE="$DIR/logs/local-code-agent.log"
SECRETS="$HOME/.ai_secrets"

mkdir -p "$DIR/logs"

# Load API keys
if [ -f "$SECRETS" ]; then
    set -a
    source "$SECRETS"
    set +a
fi

# Also load project .env if exists
if [ -f "$DIR/.env" ]; then
    set -a
    source "$DIR/.env"
    set +a
fi

export PYTHONPATH="$DIR"
export FRED_API_PORT="$PORT"

# Add 'local' to API keys so both real key and 'local' work
export FRED_API_KEYS="${FRED_API_KEYS},local"
export ELGRINGO_API_TOKEN="${ELGRINGO_API_TOKEN:-local}"

# Allow all local project paths
export PROJECTS_DIR="${PROJECTS_DIR:-/Users/fredtaylor/Development/Projects}"

CMD="$1"

case "${CMD:-run}" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Already running (PID $(cat "$PID_FILE"))"
            exit 0
        fi
        echo "Starting El Gringo coding agent on port $PORT (background)..."
        nohup "$VENV" -m uvicorn products.fred_api.server:app \
            --host 127.0.0.1 --port "$PORT" --log-level info \
            >> "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 2
        if curl -sf "http://127.0.0.1:$PORT/v1/health" > /dev/null 2>&1; then
            echo "Running on http://localhost:$PORT (PID $(cat "$PID_FILE"))"
            echo "Docs: http://localhost:$PORT/v1/docs"
        else
            echo "Started (PID $(cat "$PID_FILE")), waiting for startup..."
            echo "Check logs: tail -f $LOG_FILE"
        fi
        ;;
    stop)
        if [ -f "$PID_FILE" ]; then
            pid=$(cat "$PID_FILE")
            if kill "$pid" 2>/dev/null; then
                echo "Stopped (PID $pid)"
            else
                echo "Process $pid already gone"
            fi
            rm -f "$PID_FILE"
        else
            echo "Not running (no PID file)"
        fi
        ;;
    status)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Running (PID $(cat "$PID_FILE"))"
            curl -sf "http://127.0.0.1:$PORT/v1/health" 2>/dev/null && echo "" || echo "  (not responding yet)"
        else
            echo "Not running"
        fi
        ;;
    run|"")
        echo "============================================================"
        echo "  El Gringo Local Coding Agent — port $PORT"
        echo "============================================================"
        echo ""
        echo "  Endpoints:"
        echo "    POST /v1/code/task         Execute coding task"
        echo "    POST /v1/code/plan         Plan without executing"
        echo "    POST /v1/code/review       Code review"
        echo "    GET  /v1/code/project-info Project structure"
        echo "    POST /v1/collaborate       Team collaboration"
        echo "    POST /v1/team-debate       Virtual dev team debate"
        echo "    GET  /v1/health            Health check"
        echo ""
        echo "  Docs: http://localhost:$PORT/v1/docs"
        echo "  Press Ctrl+C to stop"
        echo "============================================================"
        echo ""
        exec "$VENV" -m uvicorn products.fred_api.server:app \
            --host 127.0.0.1 --port "$PORT" --reload --log-level info
        ;;
    *)
        echo "Usage: $0 [start|stop|status|run]"
        exit 1
        ;;
esac
