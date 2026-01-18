#!/usr/bin/env python3
"""
AI Team Briefing - Parallel Coding System
==========================================

Run this to brief the AI team on their mission and capabilities.
"""

import asyncio
import os
import sys

# Load environment
from dotenv import load_dotenv
load_dotenv()

from ai_dev_team import AIDevTeam


async def team_briefing():
    print("="*70)
    print("  AI TEAM BRIEFING - PARALLEL CODING SYSTEM")
    print("="*70)
    print()

    team = AIDevTeam(project_name="AI-Platform-HQ")

    print(f"Team Lead: Claude (via Claude Code)")
    print(f"Team Members: {len(team.agents)} agents")
    print(f"Agents: {', '.join(team.agents.keys())}")
    print()
    print("-"*70)

    briefing = """
TEAM BRIEFING FROM CLAUDE (Team Lead)
======================================

I'm Claude, your team lead, working directly with Fred through Claude Code terminal.

MISSION: Build the most advanced parallel coding system ever created.

WHAT WE'RE BUILDING:
- Rapid parallel code review and fixing (multiple agents simultaneously)
- Full application development from natural conversation
- Deep GCP integration (Firestore, Firebase, Cloud Functions, Cloud Run)
- Never-repeat-mistakes memory system
- Self-sustaining, self-improving platform

GCP RESOURCES AVAILABLE:
- Project ID: fredfix
- Firestore database (real-time NoSQL)
- Firebase Authentication
- Cloud Functions (serverless)
- Cloud Storage (files/media)
- Cloud Run (containers)
- Service account credentials configured

YOUR ASSIGNMENT:
Please introduce yourself and answer:
1. Your name and primary specialty
2. What unique capability you bring to parallel coding
3. ONE specific GCP service you'll own/specialize in
4. A quick code pattern or integration you can implement immediately

Be concise (3-4 sentences max). We're building something revolutionary.
Ready for action!
"""

    print("\nSending briefing to team...")
    print("-"*70)

    # Get responses from all agents in parallel
    result = await team.collaborate(briefing, mode="parallel")

    print("\n" + "="*70)
    print("  TEAM RESPONSES")
    print("="*70)
    print(result.final_answer)

    print("\n" + "-"*70)
    print(f"Participating agents: {', '.join(result.participating_agents)}")
    print(f"Total response time: {result.total_time:.2f}s")
    print("-"*70)

    # Summary
    print("\n" + "="*70)
    print("  TEAM STATUS: READY FOR PARALLEL CODING")
    print("="*70)
    print("""
Next Commands:
  ai ask "Build a Firebase auth system"     - Quick task
  ai review app.py                          - Code review
  python3 team_collab.py "Your task here"   - Full team collaboration
  python3 control_center.py                 - Monitor & manage team
    """)


if __name__ == "__main__":
    asyncio.run(team_briefing())
