#!/bin/bash
# ============================================
# AI Dev Team - Python Environment Setup
# ============================================
#
# Sets up a stable Python 3.11 environment that:
# - Works with Google Cloud (Functions, App Engine, Cloud Run)
# - Is compatible with all major AI SDKs
# - Can be shared across all your projects
#
# Usage:
#   ./setup-python.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

success() { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}→${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

PYTHON_VERSION="3.11"  # Google Cloud compatible, stable
VENV_NAME="ai-platform"
VENV_PATH="$HOME/.venvs/$VENV_NAME"

echo ""
echo "============================================"
echo "  AI Platform - Python Environment Setup"
echo "============================================"
echo ""
echo "This will set up Python $PYTHON_VERSION for:"
echo "  - AI Dev Team Platform"
echo "  - ChatterFix"
echo "  - Google Cloud compatibility"
echo "  - All your AI projects"
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    error "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install Python 3.11 via Homebrew
info "Checking Python $PYTHON_VERSION..."
if ! command -v python$PYTHON_VERSION &> /dev/null; then
    info "Installing Python $PYTHON_VERSION via Homebrew..."
    brew install python@$PYTHON_VERSION
    success "Python $PYTHON_VERSION installed"
else
    success "Python $PYTHON_VERSION already installed"
fi

# Get the Homebrew Python path
PYTHON_PATH=$(brew --prefix python@$PYTHON_VERSION)/bin/python$PYTHON_VERSION

if [ ! -f "$PYTHON_PATH" ]; then
    # Try alternate path
    PYTHON_PATH="/opt/homebrew/bin/python$PYTHON_VERSION"
fi

if [ ! -f "$PYTHON_PATH" ]; then
    PYTHON_PATH=$(which python$PYTHON_VERSION)
fi

echo ""
info "Using Python: $PYTHON_PATH"
$PYTHON_PATH --version

# Create virtual environment directory
mkdir -p "$HOME/.venvs"

# Create or recreate virtual environment
if [ -d "$VENV_PATH" ]; then
    warn "Virtual environment already exists at $VENV_PATH"
    read -p "Recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_PATH"
        info "Creating fresh virtual environment..."
        $PYTHON_PATH -m venv "$VENV_PATH"
    fi
else
    info "Creating virtual environment..."
    $PYTHON_PATH -m venv "$VENV_PATH"
fi

success "Virtual environment created at $VENV_PATH"

# Activate and install dependencies
info "Activating environment and installing dependencies..."
source "$VENV_PATH/bin/activate"

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install AI Platform requirements
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -r "$SCRIPT_DIR/requirements.txt"
    success "AI Platform dependencies installed"
fi

# Install Google Cloud SDK compatibility
pip install google-cloud-firestore google-cloud-storage

success "Google Cloud libraries installed"

# Add to shell profile
SHELL_RC="$HOME/.zshrc"
ACTIVATION_LINE="source $VENV_PATH/bin/activate"

echo ""
info "Configuring shell profile..."

# Check if already configured
if grep -q "ai-platform" "$SHELL_RC" 2>/dev/null; then
    warn "Shell already configured for ai-platform"
else
    cat >> "$SHELL_RC" << SHELL_CONFIG

# ============================================
# AI Platform Python Environment
# ============================================
# Python $PYTHON_VERSION - Google Cloud Compatible
# Shared across: AITeamPlatform, ChatterFix, etc.

# Auto-activate AI platform environment
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
fi

# Ensure this Python is used for all projects
alias python=python3
alias pip=pip3
# ============================================
SHELL_CONFIG
    success "Shell profile updated"
fi

echo ""
echo "============================================"
echo -e "${GREEN}  Setup Complete!${NC}"
echo "============================================"
echo ""
echo "Python Environment:"
echo "  Version:  $(python --version)"
echo "  Location: $VENV_PATH"
echo "  Python:   $(which python)"
echo ""
echo "Google Cloud Compatibility:"
echo "  - Cloud Functions: ✓"
echo "  - App Engine: ✓"
echo "  - Cloud Run: ✓"
echo ""
echo "Next steps:"
echo "  1. Run: source ~/.zshrc"
echo "  2. Verify: python --version (should show $PYTHON_VERSION.x)"
echo "  3. Run: ./setup.sh (to complete AI Platform setup)"
echo ""
echo "This environment will auto-activate in new terminals."
echo ""
