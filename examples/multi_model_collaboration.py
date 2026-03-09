#!/usr/bin/env python3
"""
Multi-Model Collaboration Examples

Demonstrates the different collaboration modes available in the AI Team Platform:
- Parallel: Execute across multiple models simultaneously
- Sequential: Chain outputs for iterative refinement
- Consensus: Multi-model voting for critical decisions
- Devil's Advocate: Challenge proposed solutions
- Peer Review: Cross-model code review
- Brainstorming: Creative ideation
- Debate: Structured argumentation
- Expert Panel: Domain-specific consultation
"""

import asyncio
from elgringo import AIDevTeam, CollaborationMode


async def parallel_execution():
    """
    Parallel Mode: Get responses from all available models simultaneously.
    Best for: Quick ideation, gathering diverse perspectives
    """
    print("\n" + "=" * 70)
    print("PARALLEL MODE - All models respond simultaneously")
    print("=" * 70)

    team = AIDevTeam()

    result = await team.collaborate(
        task="Suggest the best database choice for a real-time analytics platform",
        mode=CollaborationMode.PARALLEL,
    )

    print(f"\nParticipating models: {', '.join(result.participating_agents)}")
    print(f"Total time: {result.total_time:.2f}s")
    print(f"\nSynthesized answer:\n{result.final_answer[:800]}...")


async def consensus_voting():
    """
    Consensus Mode: Models vote on the best approach.
    Best for: Critical decisions, architecture choices, security-sensitive code
    """
    print("\n" + "=" * 70)
    print("CONSENSUS MODE - Multi-model voting on critical decisions")
    print("=" * 70)

    team = AIDevTeam()

    result = await team.collaborate(
        task="""We need to choose an authentication strategy for our API:
        Option A: JWT tokens with refresh tokens
        Option B: Session-based with Redis
        Option C: OAuth 2.0 with third-party providers

        Which approach is best for a B2B SaaS platform with strict security requirements?""",
        mode=CollaborationMode.CONSENSUS,
    )

    print(f"\nVoting models: {', '.join(result.participating_agents)}")
    print(f"Confidence score: {result.confidence_score:.0%}")
    print(f"\nConsensus decision:\n{result.final_answer[:800]}...")


async def devils_advocate():
    """
    Devil's Advocate Mode: One model intentionally challenges the solution.
    Best for: Finding edge cases, stress-testing designs, security review
    """
    print("\n" + "=" * 70)
    print("DEVIL'S ADVOCATE MODE - Challenge proposed solutions")
    print("=" * 70)

    team = AIDevTeam()

    result = await team.collaborate(
        task="""Review this proposed caching strategy:

        1. Use Redis for session storage
        2. Cache API responses for 5 minutes
        3. Use CDN for static assets
        4. No cache invalidation mechanism

        Find all potential issues and failure modes.""",
        mode=CollaborationMode.DEVILS_ADVOCATE,
    )

    print(f"\nParticipating models: {', '.join(result.participating_agents)}")
    print(f"\nCritical analysis:\n{result.final_answer[:800]}...")


async def peer_review():
    """
    Peer Review Mode: Models review each other's suggestions.
    Best for: Code review, documentation review, design validation
    """
    print("\n" + "=" * 70)
    print("PEER REVIEW MODE - Cross-model code review")
    print("=" * 70)

    team = AIDevTeam()

    code_to_review = '''
async def process_payment(user_id: str, amount: float, card_token: str):
    """Process a payment for a user."""
    user = await db.get_user(user_id)
    if user.balance >= amount:
        result = await payment_gateway.charge(card_token, amount)
        if result.success:
            user.balance -= amount
            await db.save_user(user)
            return {"status": "success", "transaction_id": result.id}
    return {"status": "failed"}
'''

    result = await team.collaborate(
        task=f"Perform a thorough peer review of this payment processing code:\n```python\n{code_to_review}\n```",
        mode=CollaborationMode.PEER_REVIEW,
    )

    print(f"\nReviewers: {', '.join(result.participating_agents)}")
    print(f"\nPeer review findings:\n{result.final_answer[:1000]}...")


async def brainstorming():
    """
    Brainstorming Mode: Creative ideation across all models.
    Best for: Feature ideas, problem-solving, innovation
    """
    print("\n" + "=" * 70)
    print("BRAINSTORMING MODE - Creative ideation")
    print("=" * 70)

    team = AIDevTeam()

    result = await team.collaborate(
        task="""Brainstorm innovative features for a CMMS (Computerized Maintenance
        Management System) that uses AI to help technicians work more efficiently.
        Focus on hands-free, voice-activated features.""",
        mode=CollaborationMode.BRAINSTORMING,
    )

    print(f"\nContributors: {', '.join(result.participating_agents)}")
    print(f"\nIdeas generated:\n{result.final_answer[:1000]}...")


async def expert_panel():
    """
    Expert Panel Mode: Each model acts as a domain specialist.
    Best for: Complex problems requiring multiple expertise areas
    """
    print("\n" + "=" * 70)
    print("EXPERT PANEL MODE - Domain-specific consultation")
    print("=" * 70)

    team = AIDevTeam()

    result = await team.collaborate(
        task="""We're designing a microservices architecture for a fintech platform.

        We need expert opinions from:
        - Security: How to handle PCI compliance
        - Performance: How to achieve sub-100ms latency
        - Reliability: How to achieve 99.99% uptime
        - Cost: How to optimize cloud spending

        Each expert should provide their specialized recommendations.""",
        mode=CollaborationMode.EXPERT_PANEL,
    )

    print(f"\nPanel experts: {', '.join(result.participating_agents)}")
    print(f"\nExpert recommendations:\n{result.final_answer[:1200]}...")


async def sequential_refinement():
    """
    Sequential Mode: Each model builds on the previous one's output.
    Best for: Iterative refinement, complex code generation
    """
    print("\n" + "=" * 70)
    print("SEQUENTIAL MODE - Iterative refinement")
    print("=" * 70)

    team = AIDevTeam()

    result = await team.collaborate(
        task="""Create a Python class for rate limiting API requests.

        Requirements:
        1. Token bucket algorithm
        2. Support for multiple rate limit tiers
        3. Async-compatible
        4. Redis backend for distributed systems

        Each model should improve upon the previous implementation.""",
        mode=CollaborationMode.SEQUENTIAL,
    )

    print(f"\nRefinement chain: {' -> '.join(result.participating_agents)}")
    print(f"Iterations: {len(result.participating_agents)}")
    print(f"\nFinal refined solution:\n{result.final_answer[:1000]}...")


async def main():
    """Run all collaboration mode examples."""
    print("\n" + "=" * 70)
    print("AI TEAM PLATFORM - Multi-Model Collaboration Examples")
    print("=" * 70)

    # Check for available agents
    team = AIDevTeam()
    if not team.agents:
        print("\n❌ No agents available. Please set at least one API key:")
        print("   export ANTHROPIC_API_KEY=your_key  # For Claude")
        print("   export OPENAI_API_KEY=your_key     # For ChatGPT")
        print("   export GOOGLE_API_KEY=your_key     # For Gemini")
        return

    print(f"\n✅ Available agents: {', '.join(team.available_agents)}")

    # Run examples (uncomment the ones you want to try)
    await parallel_execution()
    # await consensus_voting()
    # await devils_advocate()
    # await peer_review()
    # await brainstorming()
    # await expert_panel()
    # await sequential_refinement()


if __name__ == "__main__":
    asyncio.run(main())
