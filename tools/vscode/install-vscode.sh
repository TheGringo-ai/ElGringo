#!/bin/bash
# AI Dev Team - VS Code Integration Installer
# ============================================
#
# Installs VS Code tasks and optional keybindings
# for easy access to AI team features.
#
# Usage:
#   ./install-vscode.sh              # Install in current workspace
#   ./install-vscode.sh /path/to/ws  # Install in specific workspace

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Target workspace
if [ -n "$1" ]; then
    WORKSPACE_DIR="$1"
else
    WORKSPACE_DIR="$(pwd)"
fi

VSCODE_DIR="$WORKSPACE_DIR/.vscode"

echo "Installing AI Dev Team VS Code Integration..."
echo "Workspace: $WORKSPACE_DIR"
echo ""

# Create .vscode directory if needed
mkdir -p "$VSCODE_DIR"

# Install tasks.json
if [ -f "$VSCODE_DIR/tasks.json" ]; then
    echo "⚠️  tasks.json already exists - backing up to tasks.json.bak"
    cp "$VSCODE_DIR/tasks.json" "$VSCODE_DIR/tasks.json.bak"
fi

cp "$SCRIPT_DIR/tasks.json" "$VSCODE_DIR/tasks.json"
echo "✓ Installed tasks.json"

echo ""
echo "Done! AI Dev Team is now available in VS Code."
echo ""
echo "Access tasks via:"
echo "  - Cmd+Shift+P > 'Tasks: Run Task' > AI: ..."
echo "  - Terminal > Run Task > AI: ..."
echo ""
echo "Available tasks:"
echo "  - AI: Ask Question"
echo "  - AI: Review Current File"
echo "  - AI: Review Staged Changes"
echo "  - AI: Generate Commit Message"
echo "  - AI: Fix Error"
echo "  - AI: Team Status"
echo "  - AI: Start Chat"
echo "  - AI: Control Center"
echo ""
echo "Optional: Add keybindings from keybindings.json to your VS Code"
