#!/usr/bin/env python3
"""
AI Team Code Review - FixItFred
================================

Comprehensive parallel code review by the AI team.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from ai_dev_team import AIDevTeam

FIXITFRED_DIR = Path.home() / "Development/Projects/FixItFred"

def read_file(path: str, max_lines: int = 200) -> str:
    """Read file content, truncated if needed"""
    try:
        full_path = FIXITFRED_DIR / path
        if full_path.exists():
            content = full_path.read_text()
            lines = content.split('\n')
            if len(lines) > max_lines:
                return '\n'.join(lines[:max_lines]) + f"\n... [truncated, {len(lines)} total lines]"
            return content
    except Exception as e:
        return f"[Error reading {path}: {e}]"
    return f"[File not found: {path}]"


async def review_codebase():
    print("="*70)
    print("  AI TEAM CODE REVIEW - FIXITFRED")
    print("="*70)
    print()

    team = AIDevTeam(project_name="FixItFred-Review")
    print(f"Review Team: {', '.join(team.agents.keys())}")
    print(f"Team Lead: Claude (coordinating)")
    print()

    # Gather key files for review
    print("Gathering codebase files...")

    files_to_review = {
        "Main Flask App": read_file("backend/app/main.py"),
        "AI Model Router": read_file("backend/app/ai/model_router.py"),
        "Groq Client": read_file("backend/app/ai/groq_client.py"),
        "OpenAI Team": read_file("backend/app/ai/simple_openai_team.py", 300),
        "KB Retriever": read_file("backend/app/ai/kb_retriever.py"),
        "Firestore User": read_file("backend/app/models/firestore_user.py"),
        "Metrics Logger": read_file("backend/app/services/metrics_logger.py"),
        "Requirements": read_file("backend/requirements.txt"),
        "Dockerfile": read_file("backend/Dockerfile"),
        "CLAUDE.md": read_file("CLAUDE.md", 150),
    }

    # Build review prompt
    code_summary = ""
    for name, content in files_to_review.items():
        if not content.startswith("["):
            code_summary += f"\n\n### {name}\n```\n{content[:3000]}\n```"

    review_prompt = f"""
FIXITFRED CODEBASE REVIEW
=========================

You are reviewing FixItFred - an AI-powered DIY home repair assistant.

TECH STACK:
- Frontend: React + TypeScript + Styled Components
- Backend: Flask (Python 3.9) + Gunicorn
- Database: Firestore
- AI: Tiered inference (Groq → OpenAI → Grok)
- Hosting: Firebase (frontend) + Cloud Run (backend)
- Knowledge Base: 98+ expert repair guides

YOUR REVIEW TASK:
Review the following code files and provide:

1. **ARCHITECTURE ASSESSMENT** (1-10 score + reasoning)
   - Is the structure clean and maintainable?
   - Is the tiered AI routing well-implemented?

2. **SECURITY ISSUES** (Critical/High/Medium/Low)
   - API key handling
   - Input validation
   - Authentication flows
   - Any vulnerabilities?

3. **PERFORMANCE CONCERNS**
   - Bottlenecks in the AI pipeline
   - Database query efficiency
   - Caching opportunities

4. **CODE QUALITY**
   - Error handling
   - Logging
   - Type hints / documentation
   - Dead code or redundancy

5. **TOP 5 IMPROVEMENTS** (prioritized)
   - What should be fixed/improved first?

6. **WHAT'S DONE WELL**
   - Highlight good patterns to keep

Be specific. Reference file names and line concepts. This is a production codebase.

CODE FILES:
{code_summary}
"""

    print("-"*70)
    print("Sending to AI Team for parallel review...")
    print("-"*70)
    print()

    result = await team.collaborate(review_prompt, mode="parallel")

    print("="*70)
    print("  TEAM CODE REVIEW RESULTS")
    print("="*70)
    print()
    print(result.final_answer)
    print()
    print("-"*70)
    print(f"Reviewers: {', '.join(result.participating_agents)}")
    print(f"Review time: {result.total_time:.2f}s")
    print("-"*70)

    # Save review to file
    review_file = FIXITFRED_DIR / "CODE_REVIEW_AI_TEAM.md"
    with open(review_file, 'w') as f:
        f.write("# AI Team Code Review - FixItFred\n\n")
        f.write(f"**Date**: {asyncio.get_event_loop().time()}\n")
        f.write(f"**Reviewers**: {', '.join(result.participating_agents)}\n")
        f.write(f"**Team Lead**: Claude (via Claude Code)\n\n")
        f.write("---\n\n")
        f.write(result.final_answer)

    print(f"\nReview saved to: {review_file}")


if __name__ == "__main__":
    asyncio.run(review_codebase())
