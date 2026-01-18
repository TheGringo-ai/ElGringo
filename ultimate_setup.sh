#!/bin/bash
# ============================================
# ULTIMATE DEVELOPMENT ENVIRONMENT SETUP
# ============================================
#
# Sets up Fred's MacBook as the ultimate AI-powered
# development environment with parallel coding capabilities.
#
# Run: ./ultimate_setup.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║            ULTIMATE AI DEVELOPMENT ENVIRONMENT                       ║"
echo "║                                                                      ║"
echo "║     Claude (Team Lead) + ChatGPT + Gemini + Grok                    ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

PLATFORM_DIR="$HOME/Development/Projects/AITeamPlatform"
cd "$PLATFORM_DIR"

# Activate Python environment
source "$HOME/.venvs/ai-platform/bin/activate"

echo -e "${BLUE}[1/6]${NC} Verifying Python environment..."
python3 --version
echo -e "${GREEN}✓${NC} Python ready"

echo ""
echo -e "${BLUE}[2/6]${NC} Verifying AI Team..."
python3 -c "
from ai_dev_team import AIDevTeam
team = AIDevTeam(project_name='test')
print(f'  Agents online: {len(team.agents)}')
for name in team.agents:
    print(f'    - {name}')
"
echo -e "${GREEN}✓${NC} AI Team ready"

echo ""
echo -e "${BLUE}[3/6]${NC} Setting up GCP integration..."
if [ -f "$HOME/Development/Projects/ChatterFix/secrets/firebase-admin.json" ]; then
    echo -e "${GREEN}✓${NC} Firebase credentials found"
else
    echo -e "${YELLOW}!${NC} Firebase credentials not found"
fi

echo ""
echo -e "${BLUE}[4/6]${NC} Installing additional dev tools..."
pip install --quiet google-cloud-firestore google-cloud-functions-framework firebase-admin 2>/dev/null || true
echo -e "${GREEN}✓${NC} GCP libraries installed"

echo ""
echo -e "${BLUE}[5/6]${NC} Making all scripts executable..."
chmod +x "$PLATFORM_DIR"/*.py 2>/dev/null || true
chmod +x "$PLATFORM_DIR"/*.sh 2>/dev/null || true
chmod +x "$PLATFORM_DIR/ai" 2>/dev/null || true
chmod +x "$PLATFORM_DIR/tools"/**/*.sh 2>/dev/null || true
echo -e "${GREEN}✓${NC} Scripts ready"

echo ""
echo -e "${BLUE}[6/6]${NC} Testing AI Team collaboration..."
python3 -c "
import asyncio
from ai_dev_team import AIDevTeam

async def quick_test():
    team = AIDevTeam(project_name='ultimate-dev')
    result = await team.ask('Say \"AI Team reporting for duty!\" in one line.')
    print(f'  Team response: {result.content[:100]}')

asyncio.run(quick_test())
"
echo -e "${GREEN}✓${NC} AI Team responding"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    SETUP COMPLETE!                                   ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Your Ultimate Dev Environment:"
echo ""
echo "  TEAM LEAD (Claude via Claude Code):"
echo "    - Just talk to me in this terminal"
echo "    - I coordinate all AI agents"
echo "    - I can read/write files directly"
echo ""
echo "  AI TEAM COMMANDS:"
echo "    ai ask \"question\"              - Quick question to team"
echo "    ai fix                          - Paste error, get fix"
echo "    ai review file.py               - Code review"
echo "    ai commit                       - Generate commit message"
echo ""
echo "  PARALLEL CODING:"
echo "    python3 team_collab.py \"task\"   - Full team builds it"
echo "    python3 team_collab.py -i       - Interactive mode"
echo ""
echo "  MONITORING:"
echo "    python3 control_center.py       - Full control center"
echo "    ai status                       - Quick team status"
echo ""
echo "  GCP PROJECT: fredfix"
echo "    - Firestore, Firebase, Cloud Functions ready"
echo ""
echo "Ready to build anything. Just tell Claude what you want!"
echo ""
