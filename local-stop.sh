#!/usr/bin/env bash
# Stop all local El Gringo services
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$DIR/logs"

echo "Stopping local El Gringo services..."
for pidfile in "$LOG_DIR"/*.pid; do
    if [ -f "$pidfile" ]; then
        name=$(basename "$pidfile" .pid)
        pid=$(cat "$pidfile")
        if kill "$pid" 2>/dev/null; then
            echo "  Stopped $name (pid $pid)"
        fi
        rm -f "$pidfile"
    fi
done
echo "Done."
