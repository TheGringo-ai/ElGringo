#!/bin/bash
# ============================================
# AI Dev Team - Complete Setup Script
# ============================================
#
# This script sets up the entire AI Development Team platform:
# - Shell aliases for quick CLI access
# - Git hooks for code review
# - VS Code integration
# - Python dependencies
#
# Usage:
#   ./setup.sh              # Full setup
#   ./setup.sh --shell-only # Just shell aliases
#   ./setup.sh --hooks      # Install git hooks in current repo
#   ./setup.sh --vscode     # Install VS Code tasks in current workspace

set -e

PLATFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_RC="$HOME/.zshrc"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                                      ║${NC}"
    echo -e "${BLUE}║     █████╗ ██╗    ██████╗ ███████╗██╗   ██╗    ████████╗███████╗    ║${NC}"
    echo -e "${BLUE}║    ██╔══██╗██║    ██╔══██╗██╔════╝██║   ██║    ╚══██╔══╝██╔════╝    ║${NC}"
    echo -e "${BLUE}║    ███████║██║    ██║  ██║█████╗  ██║   ██║       ██║   █████╗      ║${NC}"
    echo -e "${BLUE}║    ██╔══██║██║    ██║  ██║██╔══╝  ╚██╗ ██╔╝       ██║   ██╔══╝      ║${NC}"
    echo -e "${BLUE}║    ██║  ██║██║    ██████╔╝███████╗ ╚████╔╝        ██║   ███████╗    ║${NC}"
    echo -e "${BLUE}║    ╚═╝  ╚═╝╚═╝    ╚═════╝ ╚══════╝  ╚═══╝         ╚═╝   ╚══════╝    ║${NC}"
    echo -e "${BLUE}║                                                                      ║${NC}"
    echo -e "${BLUE}║                    PLATFORM SETUP WIZARD                             ║${NC}"
    echo -e "${BLUE}║                                                                      ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

info() {
    echo -e "${BLUE}→${NC} $1"
}

warn() {
    echo -e "${YELLOW}!${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Setup shell aliases
setup_shell() {
    echo ""
    echo "Setting up shell aliases..."

    # Check if already configured
    if grep -q "AI Dev Team Platform" "$SHELL_RC" 2>/dev/null; then
        warn "Shell aliases already configured in $SHELL_RC"
        return
    fi

    # Add configuration block
    cat >> "$SHELL_RC" << 'SHELL_CONFIG'

# ============================================
# AI Dev Team Platform
# ============================================
export AI_PLATFORM_DIR="$HOME/Development/Projects/AITeamPlatform"

# Quick CLI commands
alias ai="$AI_PLATFORM_DIR/ai"
alias aiask='ai ask'
alias aifix='ai fix'
alias aireview='ai review'
alias aicommit='ai commit'
alias aichat='ai chat'
alias aistatus='ai status'

# Control center
alias aicontrol='python3 $AI_PLATFORM_DIR/control_center.py'
alias aidashboard='python3 $AI_PLATFORM_DIR/control_center.py --status'

# Quick functions
aihelp() {
    echo "AI Dev Team Commands:"
    echo "  ai ask \"question\"     - Ask the AI team a question"
    echo "  ai fix                 - Paste error, get solution"
    echo "  ai review <file>       - Review code"
    echo "  ai review --staged     - Review staged git changes"
    echo "  ai commit              - Generate commit message"
    echo "  ai chat                - Interactive chat"
    echo "  ai status              - Team status"
    echo ""
    echo "  aicontrol              - Launch control center"
    echo "  aidashboard            - Quick status dashboard"
}

# Auto-complete for ai command
_ai_completions() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=($(compgen -W "ask fix review commit chat status" -- "$cur"))
}
complete -F _ai_completions ai
# ============================================
SHELL_CONFIG

    success "Shell aliases added to $SHELL_RC"
    info "Run 'source $SHELL_RC' or restart terminal to activate"
}

# Install Python dependencies
setup_python() {
    echo ""
    echo "Setting up Python environment..."

    # Check if ai-platform venv exists
    AI_VENV="$HOME/.venvs/ai-platform"

    if [ -d "$AI_VENV" ]; then
        info "Using AI Platform virtual environment"
        source "$AI_VENV/bin/activate"
    else
        warn "AI Platform venv not found"
        info "Run ./setup-python.sh first for the best setup"
        info "Continuing with system Python..."
    fi

    # Check Python version
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    info "Python version: $PYTHON_VERSION"

    # Warn about Python 3.13 (too new for some packages)
    if [ "$PYTHON_MINOR" -ge 13 ]; then
        warn "Python 3.13+ detected - some packages may not work"
        warn "For best compatibility, run: ./setup-python.sh"
        warn "This installs Python 3.11 (Google Cloud compatible)"
    fi

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        error "Python 3.10+ required. You have $PYTHON_VERSION"
        return 1
    fi

    if [ -f "$PLATFORM_DIR/requirements.txt" ]; then
        pip3 install --upgrade pip setuptools wheel -q
        pip3 install -r "$PLATFORM_DIR/requirements.txt"
        if [ $? -eq 0 ]; then
            success "Python dependencies installed"
        else
            error "Failed to install some dependencies"
            if [ "$PYTHON_MINOR" -ge 13 ]; then
                error "Python 3.13 compatibility issue detected"
                info "Run: ./setup-python.sh to install Python 3.11"
            else
                warn "Try: pip3 install --upgrade pip setuptools wheel"
                warn "Then run: pip3 install -r requirements.txt"
            fi
        fi
    else
        warn "requirements.txt not found"
    fi
}

# Make CLI executable
setup_cli() {
    echo ""
    echo "Setting up CLI..."

    if [ -f "$PLATFORM_DIR/ai" ]; then
        chmod +x "$PLATFORM_DIR/ai"
        success "CLI is executable"
    fi
}

# Install git hooks
setup_git_hooks() {
    local target_dir="${1:-$(pwd)}"

    echo ""
    echo "Installing git hooks in $target_dir..."

    if [ ! -d "$target_dir/.git" ]; then
        error "$target_dir is not a git repository"
        return 1
    fi

    if [ -f "$PLATFORM_DIR/tools/install-hooks.sh" ]; then
        bash "$PLATFORM_DIR/tools/install-hooks.sh" "$target_dir"
        success "Git hooks installed"
    else
        warn "Git hooks installer not found"
    fi
}

# Install VS Code integration
setup_vscode() {
    local target_dir="${1:-$(pwd)}"

    echo ""
    echo "Installing VS Code integration in $target_dir..."

    if [ -f "$PLATFORM_DIR/tools/vscode/install-vscode.sh" ]; then
        bash "$PLATFORM_DIR/tools/vscode/install-vscode.sh" "$target_dir"
        success "VS Code integration installed"
    else
        warn "VS Code installer not found"
    fi
}

# Check API keys
check_api_keys() {
    echo ""
    echo "Checking API configuration..."

    if [ -f "$PLATFORM_DIR/.env" ]; then
        success "Environment file found"

        # Check for keys
        if grep -q "OPENAI_API_KEY" "$PLATFORM_DIR/.env"; then
            success "OpenAI API key configured"
        else
            warn "OpenAI API key not found"
        fi

        if grep -q "GEMINI_API_KEY" "$PLATFORM_DIR/.env"; then
            success "Gemini API key configured"
        else
            warn "Gemini API key not found"
        fi

        if grep -q "XAI_API_KEY" "$PLATFORM_DIR/.env"; then
            success "Grok API key configured"
        else
            warn "Grok API key not found"
        fi

        if grep -q "ANTHROPIC_API_KEY" "$PLATFORM_DIR/.env"; then
            success "Anthropic API key configured"
        else
            warn "Anthropic API key not found"
        fi
    else
        error "No .env file found - copy .env.template to .env and add your API keys"
    fi
}

# Full setup
full_setup() {
    print_banner

    echo "Running full setup..."

    setup_python
    setup_cli
    make_executable
    setup_shell
    setup_gcp
    check_api_keys
    verify_ai_team

    echo ""
    echo "============================================"
    echo -e "${GREEN}Setup complete!${NC}"
    echo "============================================"
    echo ""
    echo "Your AI Development Environment:"
    echo ""
    echo "  QUICK COMMANDS:"
    echo "    fred                    Interactive mode"
    echo "    fred review             Code review"
    echo "    fred fix                Fix issues"
    echo "    fred \"build X\"          Natural language task"
    echo ""
    echo "  NEXT STEPS:"
    echo "    1. Run: source ~/.zshrc"
    echo "    2. Try: fred status"
    echo "    3. Try: fred \"How do I use this platform?\""
    echo ""
    echo "  OPTIONAL:"
    echo "    ./setup.sh --hooks      Install git hooks"
    echo "    ./setup.sh --vscode     Install VS Code integration"
    echo "    ./setup.sh --verify --test  Test AI collaboration"
    echo ""
}

# Verify AI Team is working
verify_ai_team() {
    echo ""
    echo "Verifying AI Team..."

    # Check if venv exists and activate
    AI_VENV="$HOME/.venvs/ai-platform"
    if [ -d "$AI_VENV" ]; then
        source "$AI_VENV/bin/activate"
    fi

    # Test AI Team import
    info "Testing AI Team agents..."
    python3 -c "
from ai_dev_team import AIDevTeam
team = AIDevTeam(project_name='verify')
print(f'  Agents online: {len(team.agents)}')
for name in team.agents:
    print(f'    - {name}')
" 2>/dev/null && success "AI Team agents verified" || warn "Could not verify agents (check API keys)"

    # Check GCP credentials
    info "Checking GCP/Firebase..."
    if [ -f "$HOME/Development/Projects/ChatterFix/secrets/firebase-admin.json" ]; then
        success "Firebase credentials found"
    else
        warn "Firebase credentials not found at ChatterFix/secrets/"
    fi

    # Test collaboration (optional, requires API keys)
    if [ "${2:-}" == "--test" ]; then
        info "Testing AI Team collaboration..."
        python3 -c "
import asyncio
from ai_dev_team import AIDevTeam

async def quick_test():
    team = AIDevTeam(project_name='verify-test')
    result = await team.ask('Say \"AI Team ready\" in one line.')
    print(f'  Response: {result.content[:80]}')

asyncio.run(quick_test())
" 2>/dev/null && success "AI Team responding" || warn "Collaboration test failed"
    fi
}

# Install GCP dependencies
setup_gcp() {
    echo ""
    echo "Installing GCP dependencies..."

    pip install --quiet google-cloud-firestore google-cloud-functions-framework firebase-admin 2>/dev/null
    if [ $? -eq 0 ]; then
        success "GCP libraries installed"
    else
        warn "Some GCP libraries failed to install"
    fi
}

# Make all scripts executable
make_executable() {
    echo ""
    echo "Making scripts executable..."

    chmod +x "$PLATFORM_DIR"/*.py 2>/dev/null || true
    chmod +x "$PLATFORM_DIR"/*.sh 2>/dev/null || true
    chmod +x "$PLATFORM_DIR/ai" 2>/dev/null || true
    chmod +x "$PLATFORM_DIR/cli"/*.py 2>/dev/null || true
    chmod +x "$PLATFORM_DIR/scripts"/*.sh 2>/dev/null || true

    success "Scripts ready"
}

# Parse arguments
case "${1:-}" in
    --shell-only)
        setup_shell
        ;;
    --hooks)
        setup_git_hooks "${2:-$(pwd)}"
        ;;
    --vscode)
        setup_vscode "${2:-$(pwd)}"
        ;;
    --check)
        check_api_keys
        ;;
    --verify)
        print_banner
        verify_ai_team "$@"
        ;;
    --gcp)
        setup_gcp
        ;;
    --help|-h)
        echo "AI Dev Team - Setup Script"
        echo ""
        echo "Usage:"
        echo "  ./setup.sh              Full setup (recommended)"
        echo "  ./setup.sh --shell-only Just add shell aliases"
        echo "  ./setup.sh --hooks      Install git hooks in current repo"
        echo "  ./setup.sh --vscode     Install VS Code in current workspace"
        echo "  ./setup.sh --check      Check API key configuration"
        echo "  ./setup.sh --verify     Verify AI Team is working"
        echo "  ./setup.sh --verify --test  Verify + test collaboration"
        echo "  ./setup.sh --gcp        Install GCP dependencies"
        echo "  ./setup.sh --help       Show this help"
        ;;
    *)
        full_setup
        ;;
esac
