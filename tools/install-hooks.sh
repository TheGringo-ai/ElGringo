#!/bin/bash
# AI Dev Team - Git Hooks Installer
# ==================================
#
# Installs AI-powered git hooks in the current repository.
#
# Usage:
#   ./install-hooks.sh           # Install in current repo
#   ./install-hooks.sh /path     # Install in specific repo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$SCRIPT_DIR/git-hooks"

# Target repo
if [ -n "$1" ]; then
    REPO_DIR="$1"
else
    REPO_DIR="$(pwd)"
fi

# Check if it's a git repo
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "Error: $REPO_DIR is not a git repository"
    exit 1
fi

GIT_HOOKS_DIR="$REPO_DIR/.git/hooks"

echo "Installing AI Dev Team git hooks..."
echo "Repository: $REPO_DIR"
echo ""

# Install pre-commit hook
if [ -f "$HOOKS_DIR/pre-commit" ]; then
    cp "$HOOKS_DIR/pre-commit" "$GIT_HOOKS_DIR/pre-commit"
    chmod +x "$GIT_HOOKS_DIR/pre-commit"
    echo "✓ Installed pre-commit hook (code review)"
fi

# Install prepare-commit-msg hook
if [ -f "$HOOKS_DIR/prepare-commit-msg" ]; then
    cp "$HOOKS_DIR/prepare-commit-msg" "$GIT_HOOKS_DIR/prepare-commit-msg"
    chmod +x "$GIT_HOOKS_DIR/prepare-commit-msg"
    echo "✓ Installed prepare-commit-msg hook (AI commit messages)"
fi

echo ""
echo "Done! AI-powered git hooks are now active."
echo ""
echo "Features:"
echo "  - Code review before each commit"
echo "  - AI-generated commit messages"
echo ""
echo "To skip hooks: git commit --no-verify"
