#!/usr/bin/env bash
# AI Team MCP Server Startup Script
# Used by Claude Code via ~/.claude/mcp.json
#
# This script ensures the MCP server starts reliably by:
# 1. Using the correct Python venv
# 2. Validating dependencies before launch
# 3. Providing clear error messages if something is wrong

set -euo pipefail

VENV_PYTHON="/Users/fredtaylor/.venvs/ai-platform/bin/python3"
PROJECT_DIR="/Users/fredtaylor/Development/Projects/ElGringo"
MCP_SERVER="$PROJECT_DIR/mcp_server.py"
LOG_FILE="/tmp/ai_team_mcp.log"

# Verify venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Python venv not found at $VENV_PYTHON" >&2
    echo "Fix: python3 -m venv /Users/fredtaylor/.venvs/ai-platform" >&2
    exit 1
fi

# Verify MCP server script exists
if [ ! -f "$MCP_SERVER" ]; then
    echo "ERROR: MCP server not found at $MCP_SERVER" >&2
    exit 1
fi

# Verify critical dependencies
"$VENV_PYTHON" -c "import mcp" 2>/dev/null || {
    echo "ERROR: Missing mcp dependency. Run:" >&2
    echo "  $VENV_PYTHON -m pip install 'mcp>=1.0.0'" >&2
    exit 1
}

# Load API keys if available
if [ -f "$HOME/.ai_secrets" ]; then
    source "$HOME/.ai_secrets"
fi

# Set PYTHONPATH so imports resolve
export PYTHONPATH="$PROJECT_DIR:${PYTHONPATH:-}"

# Launch MCP server (unbuffered output for stdio protocol)
exec "$VENV_PYTHON" -u "$MCP_SERVER"
