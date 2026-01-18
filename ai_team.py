#!/usr/bin/env python3
"""
AI Team - Universal Development Assistant
==========================================

Single entry point for all AI team capabilities.
Run this from any project to get Claude + AI Team assistance.

Usage:
    python3 ai_team.py                    # Interactive mode
    python3 ai_team.py review             # Review current directory
    python3 ai_team.py fix                # Fix issues in current directory
    python3 ai_team.py "Build a REST API" # Natural language task

Environment Variables Required:
    OPENAI_API_KEY    - For ChatGPT (Senior Developer)
    GEMINI_API_KEY    - For Gemini (Creative Director)
    XAI_API_KEY       - For Grok (Reasoner + Coder)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add ai_dev_team to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from dotenv import load_dotenv
load_dotenv()

from ai_dev_team import AIDevTeam, ParallelCodingEngine


BANNER = """
╔═══════════════════════════════════════════════════════════════════════╗
║                     AI DEVELOPMENT TEAM                                ║
║                                                                        ║
║  Claude (Team Lead) orchestrating:                                     ║
║    • ChatGPT   - Senior Developer                                      ║
║    • Gemini    - Creative Director                                     ║
║    • Grok      - Strategic Reasoner + Speed Coder                      ║
╚═══════════════════════════════════════════════════════════════════════╝
"""


def check_api_keys():
    """Check which API keys are configured"""
    keys = {
        "OPENAI_API_KEY": "ChatGPT",
        "GEMINI_API_KEY": "Gemini",
        "XAI_API_KEY": "Grok",
    }

    available = []
    missing = []

    for key, name in keys.items():
        if os.getenv(key):
            available.append(name)
        else:
            missing.append(name)

    return available, missing


async def quick_review(project_path: str):
    """Quick code review of a project"""
    print(f"\n🔍 Quick Review: {project_path}")
    print("-" * 50)

    team = AIDevTeam(project_name="quick-review")
    engine = ParallelCodingEngine(team)

    if not team.agents:
        print("❌ No API keys configured. Set OPENAI_API_KEY, GEMINI_API_KEY, or XAI_API_KEY")
        return

    print(f"Agents: {', '.join(team.agents.keys())}")
    print("Working...\n")

    result = await engine.review_project(project_path)

    print("=" * 50)
    print(f"✅ Review Complete ({result.total_time:.1f}s)")
    print(result.summary)

    # Show agent insights
    for agent_name, agent_results in result.agent_results.items():
        if isinstance(agent_results, list):
            for r in agent_results:
                if r.get('success') and r.get('content'):
                    print(f"\n📝 {agent_name}:")
                    content = r.get('content', '')
                    # Print first 500 chars
                    print(content[:500] + "..." if len(content) > 500 else content)


async def quick_fix(project_path: str):
    """Quick fix issues in a project"""
    print(f"\n🔧 Quick Fix: {project_path}")
    print("-" * 50)

    team = AIDevTeam(project_name="quick-fix")
    engine = ParallelCodingEngine(team)

    if not team.agents:
        print("❌ No API keys configured.")
        return

    print(f"Agents: {', '.join(team.agents.keys())}")
    print("Analyzing and fixing...\n")

    # First do a quick review to identify issues
    review_result = await engine.review_project(project_path)

    # Then apply fixes
    issues = []
    for agent_name, agent_results in review_result.agent_results.items():
        if isinstance(agent_results, list):
            for r in agent_results:
                if r.get('success'):
                    issues.append({
                        "type": "review_finding",
                        "description": f"Issue found by {agent_name}",
                        "file_path": project_path,
                        "content": r.get('content', '')[:1000]
                    })

    if issues:
        fix_result = await engine.fix_issues(issues[:5], project_path)
        print("=" * 50)
        print(f"✅ Fix Session Complete ({fix_result.total_time:.1f}s)")
        print(f"Proposed fixes: {len(fix_result.proposed_fixes)}")
    else:
        print("No significant issues found to fix.")


async def natural_language_task(task: str, project_path: str):
    """Handle natural language task description"""
    print(f"\n🚀 Task: {task}")
    print(f"Project: {project_path}")
    print("-" * 50)

    team = AIDevTeam(project_name="nl-task")

    if not team.agents:
        print("❌ No API keys configured.")
        return

    print(f"Agents: {', '.join(team.agents.keys())}")
    print("Team is working...\n")

    # Enhance prompt with project context
    full_prompt = f"""
PROJECT CONTEXT:
Working directory: {project_path}

TASK FROM FRED (via Claude, Team Lead):
{task}

INSTRUCTIONS:
1. Analyze what needs to be done
2. Provide production-ready code or solutions
3. Include all necessary imports and error handling
4. Be specific and actionable

Your response:
"""

    result = await team.collaborate(full_prompt, mode="parallel")

    print("=" * 50)
    print("TEAM OUTPUT")
    print("=" * 50)
    print(result.final_answer)
    print()
    print(f"Agents: {', '.join(result.participating_agents)}")
    print(f"Time: {result.total_time:.2f}s")
    print(f"Confidence: {result.confidence_score:.0%}")


async def interactive_mode():
    """Interactive AI team session"""
    print(BANNER)

    available, missing = check_api_keys()
    print(f"✅ Available: {', '.join(available) if available else 'None'}")
    if missing:
        print(f"⚠️  Missing: {', '.join(missing)}")
    print()

    team = AIDevTeam(project_name="interactive")
    engine = ParallelCodingEngine(team)

    if not team.agents:
        print("❌ No API keys configured. Please set at least one of:")
        print("   OPENAI_API_KEY, GEMINI_API_KEY, XAI_API_KEY")
        return

    print(f"Active Agents: {', '.join(team.agents.keys())}")
    print()
    print("Commands:")
    print("  review [path]     - Code review")
    print("  security [path]   - Security audit")
    print("  fix [path]        - Fix issues")
    print("  <any text>        - Natural language task")
    print("  status            - Team status")
    print("  exit              - Quit")
    print("-" * 50)

    cwd = os.getcwd()

    while True:
        try:
            user_input = input(f"\n[{Path(cwd).name}] > ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break

            if user_input.lower() == 'status':
                status = team.get_team_status()
                print(f"\nProject: {status['project']}")
                print(f"Agents: {status['total_agents']}")
                for name, agent_status in status['agents'].items():
                    calls = agent_status.get('total_calls', 0)
                    avg_time = agent_status.get('avg_response_time', 0)
                    print(f"  • {name}: {calls} calls, {avg_time:.1f}s avg")
                continue

            # Parse command
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else cwd

            if cmd == 'review':
                await quick_review(arg)
            elif cmd == 'security':
                result = await engine.security_audit(arg)
                print(f"\n{result.summary}")
            elif cmd == 'fix':
                await quick_fix(arg)
            elif cmd == 'cd':
                if os.path.isdir(arg):
                    cwd = os.path.abspath(arg)
                    print(f"Changed to: {cwd}")
                else:
                    print(f"Not a directory: {arg}")
            else:
                # Treat as natural language task
                await natural_language_task(user_input, cwd)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="AI Development Team - Universal Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 ai_team.py                              # Interactive mode
  python3 ai_team.py review                       # Review current directory
  python3 ai_team.py review ~/Projects/MyApp      # Review specific project
  python3 ai_team.py fix                          # Fix issues
  python3 ai_team.py "Build a user auth API"      # Natural language task
  python3 ai_team.py security ~/Projects/MyApp    # Security audit
        """
    )

    parser.add_argument('command', nargs='?', help='Command or natural language task')
    parser.add_argument('path', nargs='?', default=os.getcwd(), help='Project path')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')

    args = parser.parse_args()

    if args.interactive or not args.command:
        await interactive_mode()
    elif args.command == 'review':
        await quick_review(args.path)
    elif args.command == 'security':
        team = AIDevTeam(project_name="security")
        engine = ParallelCodingEngine(team)
        result = await engine.security_audit(args.path)
        print(BANNER)
        print(result.summary)
    elif args.command == 'fix':
        await quick_fix(args.path)
    else:
        # Treat command as natural language task
        task = args.command + (" " + args.path if args.path != os.getcwd() else "")
        await natural_language_task(task, os.getcwd())


if __name__ == "__main__":
    asyncio.run(main())
