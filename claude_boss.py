#!/usr/bin/env python3
"""
Claude as Team Lead - Orchestrating the AI Dev Team
"""

import asyncio
from ai_dev_team import AIDevTeam


async def main():
    print("=" * 70)
    print("  CLAUDE CODE - AI TEAM ORCHESTRATOR")
    print("=" * 70)
    print()
    print("Hello Team! I'm Claude, running through Claude Code.")
    print("I'll be coordinating our work together. Let me introduce myself")
    print("to each of you and hear your capabilities.")
    print()
    print("-" * 70)

    # Create the team
    team = AIDevTeam(project_name="claude-orchestrated")

    print(f"\nTeam assembled: {len(team.agents)} agents online")
    print()

    # Send introduction to the team
    introduction = """
    Hello team! I'm Claude, your team lead running through Claude Code.
    I coordinate development tasks and will be delegating work to you.

    Please briefly introduce yourself in 1-2 sentences - your name,
    what you're best at, and how you like to help developers.
    """

    print("Sending introduction to all agents...")
    print("-" * 70)

    # Get responses from each agent
    for name, agent in team.agents.items():
        print(f"\n[{name.upper()}] responding...")
        try:
            response = await agent.generate_response(
                prompt=introduction,
                context="You are part of an AI development team. Claude is the team lead."
            )
            print(f"\n{response.content[:400]}")
            if len(response.content) > 400:
                print("...")
            print(f"\n  (Response time: {response.response_time:.2f}s, Confidence: {response.confidence:.0%})")
        except Exception as e:
            print(f"  Error: {e}")
        print("-" * 70)

    # Now demonstrate collaboration
    print("\n" + "=" * 70)
    print("  TEAM COLLABORATION DEMO")
    print("=" * 70)
    print("\nNow let me assign a task and have the team collaborate...")
    print()

    result = await team.collaborate(
        "As a team, suggest 3 key features for a developer productivity tool. "
        "Each suggestion should be 1 sentence. Be concise.",
        mode="parallel"
    )

    print(f"Task completed in {result.total_time:.2f}s")
    print(f"Participating agents: {', '.join(result.participating_agents)}")
    print(f"Confidence: {result.confidence_score:.0%}")
    print()
    print("TEAM'S ANSWER:")
    print("-" * 70)
    print(result.final_answer)
    print("-" * 70)

    print("\n" + "=" * 70)
    print("  Claude Code + AI Dev Team = Ready to Build!")
    print("=" * 70)
    print()
    print("I (Claude through Claude Code) can now:")
    print("  - Delegate tasks to ChatGPT, Grok, Gemini")
    print("  - Coordinate parallel work across agents")
    print("  - Use consensus mode for important decisions")
    print("  - Learn from all our interactions")
    print()


if __name__ == "__main__":
    asyncio.run(main())
