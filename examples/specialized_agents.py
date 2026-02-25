#!/usr/bin/env python3
"""
Specialized Agents Examples

Demonstrates the specialized AI agents:
- SecurityAuditor: Vulnerability scanning and security analysis
- CodeReviewer: Code quality analysis and best practices
- SolutionArchitect: System design and architecture decisions
"""

import asyncio

from examples.demos import (
    demonstrate_security_auditor,
    demonstrate_code_reviewer,
    demonstrate_solution_architect,
    demonstrate_agent_collaboration,
)


async def main():
    """Run all specialized agent examples."""
    print("\n" + "=" * 70)
    print("AI TEAM PLATFORM - Specialized Agents Examples")
    print("=" * 70)

    await demonstrate_security_auditor()
    await demonstrate_code_reviewer()
    await demonstrate_solution_architect()
    await demonstrate_agent_collaboration()

    print("\n" + "=" * 70)
    print("Specialized agents provide domain-expert AI capabilities!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
