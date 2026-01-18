"""
Command Line Interface for AI Dev Team
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Optional

from . import AIDevTeam
from .utils.config import check_api_keys, load_config


def print_banner():
    """Print the AI Dev Team banner"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                 🤖 AI DEVELOPMENT TEAM 🤖                 ║
║         Multi-Model AI Orchestration Platform            ║
╠══════════════════════════════════════════════════════════╣
║  Models: Claude | ChatGPT | Gemini | Grok                ║
║  Features: Collaboration | Memory | Learning | Routing   ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_status(team: AIDevTeam):
    """Print team status"""
    status = team.get_team_status()
    print(f"\n📊 Team Status: {status['project']}")
    print(f"   Agents: {status['total_agents']}")
    print(f"   Memory: {'✓' if status['memory_enabled'] else '✗'}")
    print(f"   Learning: {'✓' if status['learning_enabled'] else '✗'}")
    print("\n   Available Agents:")
    for name, agent_stats in status['agents'].items():
        role = agent_stats.get('role', 'Unknown')
        model = agent_stats.get('model_type', 'Unknown')
        print(f"   - {name} ({model}): {role}")
    print()


async def interactive_mode(team: AIDevTeam):
    """Run interactive chat mode"""
    print("\n🎮 Interactive Mode - Type 'exit' to quit, 'status' for team status\n")

    while True:
        try:
            prompt = input("You: ").strip()

            if not prompt:
                continue

            if prompt.lower() == 'exit':
                print("Goodbye!")
                break

            if prompt.lower() == 'status':
                print_status(team)
                continue

            if prompt.lower().startswith('mode '):
                mode = prompt.split(' ', 1)[1]
                print(f"Collaboration mode set to: {mode}")
                continue

            # Execute collaboration
            print("\n🔄 AI Team is working...\n")
            result = await team.collaborate(prompt)

            print("═" * 60)
            if result.success:
                print(f"✅ Task completed in {result.total_time:.2f}s")
                print(f"   Confidence: {result.confidence_score:.0%}")
                print(f"   Agents: {', '.join(result.participating_agents)}")
                print("─" * 60)
                print(result.final_answer)
            else:
                print(f"❌ Task failed: {result.final_answer}")
            print("═" * 60 + "\n")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


async def run_single_task(team: AIDevTeam, prompt: str, mode: str = "parallel"):
    """Run a single task"""
    print(f"\n🔄 Running task with {len(team.agents)} agents ({mode} mode)...\n")

    result = await team.collaborate(prompt, mode=mode)

    if result.success:
        print(f"✅ Completed in {result.total_time:.2f}s")
        print(f"   Confidence: {result.confidence_score:.0%}")
        print(f"   Agents: {', '.join(result.participating_agents)}")
        print("\n" + "─" * 60)
        print(result.final_answer)
        print("─" * 60)
    else:
        print(f"❌ Failed: {result.final_answer}")

    return result


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="AI Development Team - Multi-Model AI Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ai-dev-team                     # Interactive mode
  ai-dev-team "Build a REST API"  # Single task
  ai-dev-team -m consensus "Design a database schema"
  ai-dev-team --status            # Show team status
  ai-dev-team --check-keys        # Check API key configuration
        """,
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="Task prompt (optional, interactive mode if not provided)",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["parallel", "sequential", "consensus"],
        default="parallel",
        help="Collaboration mode (default: parallel)",
    )
    parser.add_argument(
        "-p", "--project",
        default="default",
        help="Project name for memory/learning",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show team status and exit",
    )
    parser.add_argument(
        "--check-keys",
        action="store_true",
        help="Check API key configuration",
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable memory system",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Check API keys
    if args.check_keys:
        print("\n🔑 API Key Status:\n")
        keys = check_api_keys()
        for name, configured in keys.items():
            status = "✓ Configured" if configured else "✗ Not set"
            print(f"   {name.upper()}: {status}")
        print()
        sys.exit(0)

    # Print banner
    if not args.json:
        print_banner()

    # Create team
    team = AIDevTeam(
        project_name=args.project,
        enable_memory=not args.no_memory,
    )

    if not team.agents:
        print("❌ No AI agents available. Please set API keys:")
        print("   export ANTHROPIC_API_KEY=your_key")
        print("   export OPENAI_API_KEY=your_key")
        print("   export GEMINI_API_KEY=your_key")
        print("   export XAI_API_KEY=your_key")
        sys.exit(1)

    # Show status
    if args.status:
        print_status(team)
        sys.exit(0)

    # Run task or interactive mode
    if args.prompt:
        # Single task mode
        result = asyncio.run(run_single_task(team, args.prompt, args.mode))

        if args.json:
            output = {
                "success": result.success,
                "answer": result.final_answer,
                "confidence": result.confidence_score,
                "time": result.total_time,
                "agents": result.participating_agents,
            }
            print(json.dumps(output, indent=2))

        sys.exit(0 if result.success else 1)
    else:
        # Interactive mode
        asyncio.run(interactive_mode(team))


if __name__ == "__main__":
    main()
