#!/usr/bin/env bash
# El Gringo MCP Server startup script
# Used by Claude Code via ~/.claude/mcp.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source API keys
if [[ -f ~/.ai_secrets ]]; then
    source ~/.ai_secrets
fi

# Point MCP at local coding agent (port 8090) if running, else use VM
if curl -sf http://127.0.0.1:8090/v1/health > /dev/null 2>&1; then
    export ELGRINGO_API_URL="http://127.0.0.1:8090"
    export ELGRINGO_API_KEY="local"
else
    export ELGRINGO_API_URL="${ELGRINGO_API_URL:-https://ai.chatterfix.com}"
    export ELGRINGO_API_KEY="${ELGRINGO_API_KEY:-K0-FkrsM2qiJRl-oD8V-k0LHA9gvveBo4icSvwS3Cqc}"
fi

# Use the platform venv
VENV_PYTHON="/Users/fredtaylor/.venvs/ai-platform/bin/python3"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "ERROR: Python venv not found at $VENV_PYTHON" >&2
    exit 1
fi

# Check mcp dependency
if ! "$VENV_PYTHON" -c "import mcp" 2>/dev/null; then
    echo "ERROR: mcp package not installed. Run: $VENV_PYTHON -m pip install 'mcp>=1.0.0'" >&2
    exit 1
fi

exec "$VENV_PYTHON" "$SCRIPT_DIR/elgringo/server/mcp_server.py"
