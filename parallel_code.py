#!/usr/bin/env python3
"""
Parallel Coding CLI
===================

Command-line interface for the parallel coding automation system.
Claude (via Claude Code) orchestrates the AI team for parallel development.

Usage:
    python3 parallel_code.py review /path/to/project
    python3 parallel_code.py security /path/to/project
    python3 parallel_code.py fix /path/to/project --issues issues.json
    python3 parallel_code.py feature /path/to/project "Add user authentication"
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from ai_dev_team import AIDevTeam
from ai_dev_team.parallel_coding import ParallelCodingEngine, TaskType


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║         PARALLEL CODING AUTOMATION SYSTEM                        ║
║         Claude (Team Lead) + AI Team                             ║
╠══════════════════════════════════════════════════════════════════╣
║  Agents: ChatGPT | Gemini | Grok-Reasoner | Grok-Coder           ║
╚══════════════════════════════════════════════════════════════════╝
    """)


async def review_project(args):
    """Run parallel code review"""
    print(f"\n🔍 Starting parallel code review: {args.project}")
    print("-" * 60)

    team = AIDevTeam(project_name="parallel-review")
    engine = ParallelCodingEngine(team)

    print(f"Active agents: {', '.join(team.agents.keys())}")
    print()

    focus = args.focus.split(',') if args.focus else None
    result = await engine.review_project(args.project, focus_areas=focus)

    print("\n" + "=" * 60)
    print("  REVIEW RESULTS")
    print("=" * 60)
    print(f"Session: {result.session_id}")
    print(f"Status: {'✅ Success' if result.success else '❌ Failed'}")
    print(f"Time: {result.total_time:.2f}s")
    print()

    print("Agent Contributions:")
    for agent_name, agent_results in result.agent_results.items():
        if isinstance(agent_results, list):
            success_count = sum(1 for r in agent_results if r.get('success'))
            print(f"  • {agent_name}: {success_count}/{len(agent_results)} tasks")

    print()
    print(f"Summary: {result.summary}")

    if result.proposed_fixes:
        print(f"\nProposed fixes: {len(result.proposed_fixes)}")

    # Output detailed results if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump({
                "session_id": result.session_id,
                "success": result.success,
                "summary": result.summary,
                "agent_results": result.agent_results
            }, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {output_path}")


async def security_audit(args):
    """Run parallel security audit"""
    print(f"\n🔒 Starting parallel security audit: {args.project}")
    print("-" * 60)

    team = AIDevTeam(project_name="security-audit")
    engine = ParallelCodingEngine(team)

    print(f"Active agents: {', '.join(team.agents.keys())}")
    print()

    result = await engine.security_audit(
        args.project,
        severity_threshold=args.severity
    )

    print("\n" + "=" * 60)
    print("  SECURITY AUDIT RESULTS")
    print("=" * 60)
    print(f"Session: {result.session_id}")
    print(f"Status: {'✅ Complete' if result.success else '❌ Failed'}")
    print(f"Time: {result.total_time:.2f}s")
    print()
    print(f"Summary: {result.summary}")

    if result.proposed_fixes:
        print(f"\n⚠️  Security fixes proposed: {len(result.proposed_fixes)}")
        for i, fix in enumerate(result.proposed_fixes[:5], 1):
            print(f"  {i}. [{fix.agent_name}] {fix.description[:60]}...")


async def fix_issues(args):
    """Fix issues in parallel"""
    print(f"\n🔧 Starting parallel issue fixing: {args.project}")
    print("-" * 60)

    # Load issues from file or generate from scan
    if args.issues:
        with open(args.issues) as f:
            issues = json.load(f)
    else:
        # Quick scan for common issues
        issues = [
            {"type": "security", "description": "Review for security vulnerabilities", "file_path": args.project},
            {"type": "quality", "description": "Review for code quality issues", "file_path": args.project},
        ]

    team = AIDevTeam(project_name="parallel-fix")
    engine = ParallelCodingEngine(team)

    print(f"Issues to fix: {len(issues)}")
    print(f"Active agents: {', '.join(team.agents.keys())}")
    print(f"Auto-apply: {args.auto_apply}")
    print()

    result = await engine.fix_issues(
        issues,
        args.project,
        auto_apply=args.auto_apply
    )

    print("\n" + "=" * 60)
    print("  FIX RESULTS")
    print("=" * 60)
    print(f"Session: {result.session_id}")
    print(f"Status: {'✅ Complete' if result.success else '❌ Failed'}")
    print(f"Time: {result.total_time:.2f}s")
    print(f"Proposed fixes: {len(result.proposed_fixes)}")

    if args.auto_apply:
        print("\n✅ Fixes have been applied to the codebase")


async def implement_feature(args):
    """Implement feature in parallel"""
    print(f"\n🚀 Starting parallel feature implementation")
    print("-" * 60)
    print(f"Project: {args.project}")
    print(f"Feature: {args.feature}")
    print()

    team = AIDevTeam(project_name="parallel-impl")
    engine = ParallelCodingEngine(team)

    print(f"Active agents: {', '.join(team.agents.keys())}")
    print()

    specs = {}
    if args.specs:
        with open(args.specs) as f:
            specs = json.load(f)

    result = await engine.implement_feature(
        args.feature,
        args.project,
        specifications=specs
    )

    print("\n" + "=" * 60)
    print("  IMPLEMENTATION RESULTS")
    print("=" * 60)
    print(f"Session: {result.session_id}")
    print(f"Status: {'✅ Complete' if result.success else '❌ Failed'}")
    print(f"Time: {result.total_time:.2f}s")
    print()

    if "architecture" in result.agent_results:
        print("📐 Architecture:")
        print("-" * 40)
        arch = result.agent_results.get("architecture", "")
        print(arch[:1000] + "..." if len(arch) > 1000 else arch)


async def interactive_mode():
    """Interactive parallel coding mode"""
    print_banner()
    print("\nInteractive Mode - Type commands or 'help' for options")
    print("-" * 60)

    team = AIDevTeam(project_name="interactive")
    engine = ParallelCodingEngine(team)

    print(f"Agents online: {', '.join(team.agents.keys())}")

    while True:
        try:
            cmd = input("\n[parallel] > ").strip()

            if not cmd:
                continue
            if cmd.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
            if cmd.lower() == 'help':
                print("""
Commands:
  review <path>       - Review a project
  security <path>     - Security audit
  fix <path>          - Fix issues
  feature <path> <desc> - Implement feature
  status              - Show team status
  exit                - Exit
                """)
                continue
            if cmd.lower() == 'status':
                status = team.get_team_status()
                print(f"Project: {status['project']}")
                print(f"Agents: {status['total_agents']}")
                for name, agent_status in status['agents'].items():
                    print(f"  • {name}: {agent_status.get('total_calls', 0)} calls")
                continue

            # Parse command
            parts = cmd.split(maxsplit=2)
            if len(parts) < 2:
                print("Usage: <command> <path> [options]")
                continue

            action = parts[0].lower()
            path = parts[1]

            if action == 'review':
                result = await engine.review_project(path)
                print(f"\n{result.summary}")
            elif action == 'security':
                result = await engine.security_audit(path)
                print(f"\n{result.summary}")
            elif action == 'fix':
                result = await engine.fix_issues([], path)
                print(f"\n{result.summary}")
            elif action == 'feature':
                feature_desc = parts[2] if len(parts) > 2 else "New feature"
                result = await engine.implement_feature(feature_desc, path)
                print(f"\n{result.summary}")
            else:
                print(f"Unknown command: {action}")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Parallel Coding Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 parallel_code.py review ~/Projects/MyApp
  python3 parallel_code.py security ~/Projects/MyApp --severity high
  python3 parallel_code.py fix ~/Projects/MyApp --issues bugs.json --auto-apply
  python3 parallel_code.py feature ~/Projects/MyApp "Add user authentication"
  python3 parallel_code.py --interactive
        """
    )

    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode')

    subparsers = parser.add_subparsers(dest='command')

    # Review command
    review_parser = subparsers.add_parser('review', help='Parallel code review')
    review_parser.add_argument('project', help='Project path')
    review_parser.add_argument('--focus', '-f', help='Focus areas (comma-separated)')
    review_parser.add_argument('--output', '-o', help='Output file for results')

    # Security command
    security_parser = subparsers.add_parser('security', help='Security audit')
    security_parser.add_argument('project', help='Project path')
    security_parser.add_argument('--severity', '-s', default='medium',
                                choices=['low', 'medium', 'high', 'critical'],
                                help='Minimum severity threshold')

    # Fix command
    fix_parser = subparsers.add_parser('fix', help='Fix issues in parallel')
    fix_parser.add_argument('project', help='Project path')
    fix_parser.add_argument('--issues', help='JSON file with issues to fix')
    fix_parser.add_argument('--auto-apply', '-a', action='store_true',
                           help='Automatically apply fixes')

    # Feature command
    feature_parser = subparsers.add_parser('feature', help='Implement feature')
    feature_parser.add_argument('project', help='Project path')
    feature_parser.add_argument('feature', help='Feature description')
    feature_parser.add_argument('--specs', help='JSON file with specifications')

    args = parser.parse_args()

    print_banner()

    if args.interactive:
        await interactive_mode()
    elif args.command == 'review':
        await review_project(args)
    elif args.command == 'security':
        await security_audit(args)
    elif args.command == 'fix':
        await fix_issues(args)
    elif args.command == 'feature':
        await implement_feature(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
