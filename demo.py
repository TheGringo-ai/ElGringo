#!/usr/bin/env python3
"""
El Gringo Quick Demo — works with just Ollama (no API keys needed)

Usage:
    ollama pull llama3.2:3b
    python demo.py
"""

import asyncio
import sys
import os

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(__file__))


def print_header(text):
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}\n")


async def main():
    from ai_dev_team.orchestrator import AIDevTeam

    print_header("El Gringo Demo")
    print("Initializing AI team...\n")

    team = AIDevTeam(project_name="demo")
    agents = list(team.agents.keys())

    if not agents:
        print("No agents available!")
        print("Install Ollama and run: ollama pull llama3.2:3b")
        print("Or set API keys: OPENAI_API_KEY, XAI_API_KEY, GEMINI_API_KEY")
        return

    print(f"Agents online: {', '.join(agents)}\n")

    # Demo 1: Quick ask
    print_header("Demo 1: Quick Ask")
    print("Prompt: 'What are 3 best practices for Python error handling?'\n")

    result = await team.ask("What are 3 best practices for Python error handling? Be concise.")
    print(result.content[:500])

    # Demo 2: Multi-agent collaboration
    if len(agents) >= 2:
        print_header("Demo 2: Multi-Agent Collaboration")
        print(f"Mode: parallel ({len(agents)} agents)")
        print("Prompt: 'Design a REST API endpoint for user registration'\n")

        result = await team.collaborate(
            "Design a REST API endpoint for user registration. Include validation, error handling, and response format. Be concise.",
            mode="parallel",
        )
        print(f"Success: {result.success}")
        print(f"Confidence: {result.confidence_score:.0%}")
        print(f"Agents used: {', '.join(result.participating_agents)}")
        print(f"Time: {result.total_time:.1f}s\n")
        print(result.final_answer[:600])

    # Demo 3: Memory system
    print_header("Demo 3: Memory System")
    from ai_dev_team.memory.system import MemorySystem

    mem = MemorySystem()
    stats = mem.get_statistics()
    print(f"Interactions stored: {stats['total_interactions']}")
    print(f"Solutions learned:   {stats['total_solutions']}")
    print(f"Mistakes tracked:    {stats['total_mistakes']}")
    print(f"Overall success:     {stats['success_rate']:.0%}")

    print_header("Done")
    print("Star us: https://github.com/TheGringo-ai/ElGringo")


if __name__ == "__main__":
    asyncio.run(main())
