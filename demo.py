#!/usr/bin/env python3
"""
AI Development Team - Interactive Demo
=======================================
Run this to see the AI team in action!
"""

import asyncio

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from ai_dev_team import AIDevTeam
from ai_dev_team.routing import TaskRouter


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title):
    print(f"\n{title}")
    print("-" * 40)


async def main():
    print_header("AI DEVELOPMENT TEAM - LIVE DEMO")

    # 1. Create Team
    print_section("1. INITIALIZING AI TEAM")
    team = AIDevTeam(project_name="demo-project")

    print(f"Project: demo-project")
    print(f"Available agents: {len(team.agents)}")
    print()
    for name, agent in team.agents.items():
        print(f"  [{agent.config.model_type.value.upper()}] {name}")
        print(f"       Role: {agent.role}")
        print(f"       Capabilities: {', '.join(agent.config.capabilities[:3])}")
        print()

    if not team.agents:
        print("No agents available! Set API keys:")
        print("  export ANTHROPIC_API_KEY=your_key")
        print("  export OPENAI_API_KEY=your_key")
        print("  export GEMINI_API_KEY=your_key")
        print("  export XAI_API_KEY=your_key")
        return

    # 2. Task Routing Demo
    print_section("2. INTELLIGENT TASK ROUTING")
    router = TaskRouter()

    tasks = [
        "Fix the authentication bug in login.py",
        "Design a microservices architecture for e-commerce",
        "Review this code for security vulnerabilities",
        "Add unit tests for the payment service",
        "Optimize database query performance",
    ]

    for task in tasks:
        result = router.classify(task)
        print(f'Task: "{task}"')
        print(f"  Type: {result.primary_type.value}")
        print(f"  Best Agents: {', '.join(result.recommended_agents)}")
        print(f"  Mode: {result.recommended_mode}")
        print(f"  Confidence: {result.confidence:.0%}")
        print()

    # 3. Memory System Status
    print_section("3. MEMORY & LEARNING SYSTEM")
    print(f"Memory System: {'ENABLED' if team.enable_memory else 'DISABLED'}")
    print(f"Learning Engine: {'ENABLED' if team.enable_learning else 'DISABLED'}")
    print()
    print("Capabilities:")
    print("  - Captures all conversations and outcomes")
    print("  - Learns from mistakes to prevent repetition")
    print("  - Stores successful solutions for reuse")
    print("  - Shares knowledge across projects")

    # 4. Live Collaboration Demo
    print_section("4. LIVE AI COLLABORATION")
    print("Sending task to AI team...")
    print('Task: "What are the best practices for error handling in Python?"')
    print()

    try:
        response = await team.ask(
            "What are the top 3 best practices for error handling in Python? Be concise."
        )
        print(f"Agent: {response.agent_name}")
        print(f"Confidence: {response.confidence:.0%}")
        print(f"Response Time: {response.response_time:.2f}s")
        print()
        print("Response:")
        print("-" * 40)
        print(response.content[:800])
        if len(response.content) > 800:
            print("... [truncated]")
    except Exception as e:
        print(f"Error: {e}")
        print("(Make sure API keys are configured)")

    # 5. Team Status
    print_section("5. TEAM STATUS")
    status = team.get_team_status()
    print(f"Project: {status['project']}")
    print(f"Total Agents: {status['total_agents']}")
    print(f"Memory Enabled: {status['memory_enabled']}")
    print(f"Learning Enabled: {status['learning_enabled']}")

    print_header("DEMO COMPLETE")
    print("\nUsage examples:")
    print('  ai-dev-team "Your task here"')
    print('  ai-dev-team -m consensus "Design a database schema"')
    print("  ai-dev-team --status")
    print()


if __name__ == "__main__":
    asyncio.run(main())
