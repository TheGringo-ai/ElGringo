#!/usr/bin/env python3
"""
El Gringo Development Assistant
Quick helper to consult the AI team during development
"""

import asyncio
import sys
from ai_dev_team.orchestrator import AIDevTeam


async def consult_team(task: str, mode: str = "parallel"):
    """Quick consultation with the AI team"""
    print(f"\n🤖 Consulting AI Team...")
    print(f"📋 Task: {task}")
    print(f"🎯 Mode: {mode}\n")
    
    team = AIDevTeam(
        project_name="ElGringo",
        enable_memory=True,
        enable_learning=True
    )
    
    # Show available agents
    agents = list(team.agents.keys())
    print(f"👥 Active Agents: {', '.join(agents)}\n")
    print("─" * 80)
    
    result = await team.collaborate(task, mode=mode)
    
    print("\n" + "=" * 80)
    print("📊 RESULT")
    print("=" * 80)
    print(f"\n{result.final_answer}\n")
    print("─" * 80)
    print(f"✅ Success: {result.success}")
    print(f"📈 Confidence: {result.confidence_score:.2f}")
    print(f"⏱️  Time: {result.total_time:.2f}s")
    print(f"👥 Agents Used: {', '.join(result.participating_agents)}")
    print("=" * 80 + "\n")
    
    return result


async def code_review(file_path: str):
    """Get multi-agent code review"""
    print(f"\n🔍 Getting code review for: {file_path}")
    
    with open(file_path, 'r') as f:
        code = f.read()
    
    task = f"""Review this code for:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance improvements
4. Security concerns

```python
{code[:2000]}  # First 2000 chars
```
"""
    
    return await consult_team(task, mode="peer_review")


async def architecture_review(description: str):
    """Get architecture recommendations"""
    task = f"""Provide architecture recommendations for:

{description}

Consider:
- Scalability
- Maintainability
- Security
- Performance
- Best practices
"""
    
    return await consult_team(task, mode="expert_panel")


async def brainstorm_feature(feature: str):
    """Brainstorm implementation approaches"""
    task = f"""Brainstorm different approaches to implement:

{feature}

Provide:
- 3-5 different implementation strategies
- Pros and cons of each
- Recommended approach with rationale
"""
    
    return await consult_team(task, mode="brainstorming")


async def debug_help(error: str, context: str = ""):
    """Get debugging assistance"""
    task = f"""Help debug this issue:

Error: {error}

Context: {context}

Provide:
- Root cause analysis
- Step-by-step debugging approach
- Potential fixes
- Prevention strategies
"""
    
    return await consult_team(task, mode="consensus")


async def quick_ask(question: str):
    """Quick question to the team"""
    team = AIDevTeam(project_name="ElGringo")
    
    print(f"\n💬 Quick Ask: {question}\n")
    print("─" * 80)
    
    result = await team.ask(question)
    
    print(f"\n{result.content}\n")
    print("─" * 80 + "\n")
    
    return result


# CLI Interface
async def main():
    if len(sys.argv) < 2:
        print("""
El Gringo Development Assistant
=============================

Usage:
  python dev_assistant.py ask "Your question"
  python dev_assistant.py review <file_path>
  python dev_assistant.py brainstorm "Feature description"
  python dev_assistant.py debug "Error message" "Context"
  python dev_assistant.py architecture "Architecture description"

Examples:
  python dev_assistant.py ask "What's the best way to handle rate limiting?"
  python dev_assistant.py review ai_dev_team/orchestrator.py
  python dev_assistant.py brainstorm "Add caching layer with Redis"
  python dev_assistant.py debug "ValueError: invalid literal" "Parsing config file"
""")
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "ask" and len(sys.argv) >= 3:
            await quick_ask(" ".join(sys.argv[2:]))
        
        elif command == "review" and len(sys.argv) >= 3:
            await code_review(sys.argv[2])
        
        elif command == "brainstorm" and len(sys.argv) >= 3:
            await brainstorm_feature(" ".join(sys.argv[2:]))
        
        elif command == "debug" and len(sys.argv) >= 3:
            error = sys.argv[2]
            context = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
            await debug_help(error, context)
        
        elif command == "architecture" and len(sys.argv) >= 3:
            await architecture_review(" ".join(sys.argv[2:]))
        
        else:
            print(f"❌ Unknown command: {command}")
            print("Run without arguments for usage help")
    
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
