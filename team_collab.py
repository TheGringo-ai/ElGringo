#!/usr/bin/env python3
"""
AI Team Collaboration - Natural Language to Code
=================================================

Give the team a task in natural language, they build it together.

Usage:
    python3 team_collab.py "Build a user authentication API with Firebase"
    python3 team_collab.py "Create a Firestore CRUD service for inventory"
    python3 team_collab.py --interactive
"""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from ai_dev_team import AIDevTeam


GCP_CONTEXT = """
GCP ENVIRONMENT:
- Project: fredfix
- Firestore: Available for NoSQL storage
- Firebase Auth: Available for authentication
- Cloud Functions: Python 3.11 runtime
- Cloud Storage: Available for files
- Credentials: Configured via service account

CODING STANDARDS:
- Python 3.11 compatible
- Type hints required
- Async/await for I/O operations
- Error handling with proper logging
- Google Cloud client libraries preferred
"""


async def collaborate(task: str, mode: str = "parallel"):
    """Run a team collaboration on a task"""
    team = AIDevTeam(project_name="AI-Platform-HQ")

    print("="*70)
    print("  AI TEAM COLLABORATION")
    print("="*70)
    print(f"\nTask: {task}")
    print(f"Mode: {mode}")
    print(f"Agents: {', '.join(team.agents.keys())}")
    print("-"*70)

    full_prompt = f"""
{GCP_CONTEXT}

TASK FROM FRED (via Claude, Team Lead):
{task}

INSTRUCTIONS:
1. Analyze the task and identify your role
2. Write production-ready code (not pseudocode)
3. Include proper imports, error handling, type hints
4. If creating GCP integrations, use google-cloud libraries
5. Be specific and complete - this code should run

Provide your implementation:
"""

    print("\nTeam is working...\n")

    result = await team.collaborate(full_prompt, mode=mode)

    print("="*70)
    print("  TEAM OUTPUT")
    print("="*70)
    print(result.final_answer)

    print("\n" + "-"*70)
    print(f"Agents: {', '.join(result.participating_agents)}")
    print(f"Time: {result.total_time:.2f}s")
    print("-"*70)

    return result


async def interactive_mode():
    """Interactive collaboration mode"""
    print("="*70)
    print("  AI TEAM - INTERACTIVE MODE")
    print("="*70)
    print("\nDescribe what you want to build. The team will create it.")
    print("Commands: 'exit' to quit, 'mode parallel/consensus' to change mode")
    print("-"*70)

    mode = "parallel"

    while True:
        try:
            task = input(f"\n[{mode}] What should we build? > ").strip()

            if not task:
                continue
            if task.lower() == 'exit':
                print("Goodbye!")
                break
            if task.lower().startswith('mode '):
                mode = task.split()[1]
                print(f"Mode changed to: {mode}")
                continue

            await collaborate(task, mode=mode)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            break


async def main():
    parser = argparse.ArgumentParser(
        description="AI Team Collaboration - Natural Language to Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 team_collab.py "Build a REST API for user management"
  python3 team_collab.py "Create Firestore service for work orders"
  python3 team_collab.py --mode consensus "Design database schema for CMMS"
  python3 team_collab.py --interactive
        """
    )

    parser.add_argument('task', nargs='?', help='Task description')
    parser.add_argument('--mode', '-m', default='parallel',
                       choices=['parallel', 'sequential', 'consensus', 'devils_advocate'],
                       help='Collaboration mode')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode')

    args = parser.parse_args()

    if args.interactive:
        await interactive_mode()
    elif args.task:
        await collaborate(args.task, args.mode)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
