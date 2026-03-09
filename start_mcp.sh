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
