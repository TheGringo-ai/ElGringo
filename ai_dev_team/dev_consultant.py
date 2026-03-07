"""
El Gringo Integration Module
Use El Gringo agents during development sessions
"""

import asyncio
from typing import Optional, Dict, Any
from ai_dev_team.orchestrator import AIDevTeam


class DevConsultant:
    """Wrapper for easy El Gringo consultation during development"""
    
    def __init__(self):
        self.team: Optional[AIDevTeam] = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of the AI team"""
        if not self._initialized:
            print("🤖 Initializing El Gringo team...")
            self.team = AIDevTeam(
                project_name="ElGringo",
                enable_memory=True,
                enable_learning=True
            )
            agents = list(self.team.agents.keys())
            print(f"✅ Team ready with: {', '.join(agents)}\n")
            self._initialized = True
    
    async def review_code(self, code: str, context: str = "") -> str:
        """Quick code review"""
        await self._ensure_initialized()
        
        prompt = f"""Review this code:

{code}

Context: {context}

Provide:
1. Issues found (bugs, security, performance)
2. Suggested improvements
3. Code quality rating (1-10)
"""
        
        result = await self.team.collaborate(prompt, mode="peer_review")
        return result.final_answer
    
    async def ask(self, question: str) -> str:
        """Quick question"""
        await self._ensure_initialized()
        result = await self.team.ask(question)
        return result.content
    
    async def brainstorm(self, topic: str) -> str:
        """Brainstorm ideas"""
        await self._ensure_initialized()
        result = await self.team.collaborate(
            f"Brainstorm: {topic}",
            mode="brainstorming"
        )
        return result.final_answer
    
    async def get_consensus(self, question: str) -> str:
        """Get multi-agent consensus"""
        await self._ensure_initialized()
        result = await self.team.collaborate(question, mode="consensus")
        return result.final_answer
    
    async def architecture_advice(self, description: str) -> str:
        """Get architecture recommendations"""
        await self._ensure_initialized()
        
        prompt = f"""Architecture consultation:

{description}

Provide:
1. Recommended architecture
2. Key components
3. Technology choices
4. Scalability considerations
5. Potential pitfalls
"""
        
        result = await self.team.collaborate(prompt, mode="expert_panel")
        return result.final_answer
    
    async def debug_assistant(self, error: str, code: str = "", context: str = "") -> str:
        """Get debugging help"""
        await self._ensure_initialized()
        
        prompt = f"""Debug this issue:

Error: {error}

Code:
{code}

Context: {context}

Provide:
1. Root cause
2. Fix
3. Prevention strategy
"""
        
        result = await self.team.collaborate(prompt, mode="consensus")
        return result.final_answer


# Singleton instance
_consultant: Optional[DevConsultant] = None


def get_consultant() -> DevConsultant:
    """Get the singleton dev consultant"""
    global _consultant
    if _consultant is None:
        _consultant = DevConsultant()
    return _consultant


# Convenience functions
async def consult(question: str) -> str:
    """Quick consultation"""
    consultant = get_consultant()
    return await consultant.ask(question)


async def review(code: str, context: str = "") -> str:
    """Quick code review"""
    consultant = get_consultant()
    return await consultant.review_code(code, context)


async def brainstorm(topic: str) -> str:
    """Quick brainstorm"""
    consultant = get_consultant()
    return await consultant.brainstorm(topic)


# Example usage in interactive Python
if __name__ == "__main__":
    async def demo():
        print("=" * 80)
        print("El Gringo Development Consultant - Interactive Demo")
        print("=" * 80 + "\n")
        
        # Example 1: Quick question
        print("📋 Example 1: Quick Question\n")
        answer = await consult(
            "What's the best practice for handling async errors in Python?"
        )
        print(f"Answer:\n{answer}\n")
        print("─" * 80 + "\n")
        
        # Example 2: Code review
        print("📋 Example 2: Code Review\n")
        sample_code = """
def process_data(data):
    result = []
    for item in data:
        try:
            result.append(item['value'])
        except Exception:
            pass
    return result
"""
        review_result = await review(sample_code, "Data processing function")
        print(f"Review:\n{review_result}\n")
        print("─" * 80 + "\n")
        
        # Example 3: Brainstorm
        print("📋 Example 3: Brainstorm\n")
        ideas = await brainstorm(
            "Ways to improve El Gringo's error handling and recovery"
        )
        print(f"Ideas:\n{ideas}\n")
        print("=" * 80)
    
    asyncio.run(demo())
