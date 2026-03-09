#!/usr/bin/env python3
"""
Basic usage example for AI Development Team
"""

import asyncio

# Ensure you have API keys set
# export ANTHROPIC_API_KEY=your_key
# export OPENAI_API_KEY=your_key

from elgringo import AIDevTeam


async def main():
    print("🤖 AI Development Team - Basic Usage Example\n")

    # Create AI team
    team = AIDevTeam(project_name="example-project")

    # Show available agents
    print(f"Available agents: {team.available_agents}\n")

    if not team.agents:
        print("❌ No agents available. Please set API keys.")
        return

    # Example 1: Simple question
    print("=" * 60)
    print("Example 1: Simple Question (Single Agent)")
    print("=" * 60)

    response = await team.ask("What is the best way to handle errors in Python?")
    print(f"\nAgent: {response.agent_name}")
    print(f"Confidence: {response.confidence:.0%}")
    print(f"\n{response.content[:500]}...\n")

    # Example 2: Collaborative task
    print("=" * 60)
    print("Example 2: Collaborative Task (Parallel Mode)")
    print("=" * 60)

    result = await team.collaborate(
        "Design a function to validate email addresses with comprehensive error handling",
        mode="parallel",
    )

    print(f"\nSuccess: {result.success}")
    print(f"Agents: {', '.join(result.participating_agents)}")
    print(f"Time: {result.total_time:.2f}s")
    print(f"Confidence: {result.confidence_score:.0%}")
    print(f"\n{result.final_answer[:800]}...\n")

    # Example 3: Code review
    print("=" * 60)
    print("Example 3: Code Review")
    print("=" * 60)

    sample_code = '''
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
'''

    review_result = await team.code_review(
        code=sample_code,
        language="python",
        focus=["performance", "error handling"],
    )

    print(f"\nReview completed by: {', '.join(review_result.participating_agents)}")
    print(f"\n{review_result.final_answer[:600]}...\n")

    # Show team status
    print("=" * 60)
    print("Team Status")
    print("=" * 60)
    status = team.get_team_status()
    print(f"Project: {status['project']}")
    print(f"Total Agents: {status['total_agents']}")
    for name, stats in status['agents'].items():
        print(f"  - {name}: {stats['total_requests']} requests, {stats['success_rate']:.0%} success")


if __name__ == "__main__":
    asyncio.run(main())
