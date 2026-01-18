"""
Collaboration Engine - Advanced multi-agent collaboration patterns
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..agents import AIAgent, AgentResponse

logger = logging.getLogger(__name__)


class CollaborationMode(Enum):
    """Available collaboration modes"""
    PARALLEL = "parallel"           # All agents work simultaneously
    SEQUENTIAL = "sequential"       # Agents work in sequence
    CONSENSUS = "consensus"         # Multiple rounds to build agreement
    DEVILS_ADVOCATE = "devils_advocate"  # One agent challenges others
    PEER_REVIEW = "peer_review"     # Agents review each other's work
    BRAINSTORMING = "brainstorming" # Creative ideation mode


@dataclass
class CollaborationContext:
    """Context for a collaboration session"""
    mode: CollaborationMode
    max_rounds: int = 3
    consensus_threshold: float = 0.8
    timeout_seconds: int = 120
    require_all_agents: bool = False
    allow_disagreement: bool = True


@dataclass
class CollaborationRound:
    """A single round of collaboration"""
    round_number: int
    prompt: str
    responses: List[AgentResponse]
    consensus_level: float
    insights: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)


class CollaborationEngine:
    """
    Advanced collaboration engine supporting multiple patterns.

    Implements sophisticated collaboration strategies including
    consensus building, devil's advocate, and peer review.
    """

    def __init__(self):
        self.rounds: List[CollaborationRound] = []
        self._consensus_builder = ConsensusBuilder()
        self._challenge_generator = ChallengeGenerator()

    async def execute(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str = "",
        collaboration_context: Optional[CollaborationContext] = None,
    ) -> List[AgentResponse]:
        """
        Execute collaboration with specified mode.

        Returns all responses from the collaboration.
        """
        if not collaboration_context:
            collaboration_context = CollaborationContext(mode=CollaborationMode.PARALLEL)

        self.rounds = []

        if collaboration_context.mode == CollaborationMode.PARALLEL:
            return await self._execute_parallel(agents, prompt, context)

        elif collaboration_context.mode == CollaborationMode.SEQUENTIAL:
            return await self._execute_sequential(agents, prompt, context)

        elif collaboration_context.mode == CollaborationMode.CONSENSUS:
            return await self._execute_consensus(
                agents, prompt, context, collaboration_context
            )

        elif collaboration_context.mode == CollaborationMode.DEVILS_ADVOCATE:
            return await self._execute_devils_advocate(
                agents, prompt, context, collaboration_context
            )

        elif collaboration_context.mode == CollaborationMode.PEER_REVIEW:
            return await self._execute_peer_review(agents, prompt, context)

        elif collaboration_context.mode == CollaborationMode.BRAINSTORMING:
            return await self._execute_brainstorming(agents, prompt, context)

        else:
            return await self._execute_parallel(agents, prompt, context)

    async def _execute_parallel(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
    ) -> List[AgentResponse]:
        """All agents respond simultaneously"""
        tasks = [agent.generate_response(prompt, context) for agent in agents]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        valid_responses = []
        for response in responses:
            if isinstance(response, AgentResponse):
                valid_responses.append(response)

        self.rounds.append(CollaborationRound(
            round_number=1,
            prompt=prompt,
            responses=valid_responses,
            consensus_level=self._calculate_consensus(valid_responses),
        ))

        return valid_responses

    async def _execute_sequential(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
    ) -> List[AgentResponse]:
        """Agents respond in sequence, building on previous responses"""
        all_responses = []
        accumulated_context = context

        for i, agent in enumerate(agents):
            # Add previous responses to context
            if all_responses:
                prev_text = "\n\n".join(
                    f"[{r.agent_name}]: {r.content[:500]}..."
                    for r in all_responses if r.success
                )
                accumulated_context = f"{context}\n\nTeam progress:\n{prev_text}"

            response = await agent.generate_response(prompt, accumulated_context)
            all_responses.append(response)

        self.rounds.append(CollaborationRound(
            round_number=1,
            prompt=prompt,
            responses=all_responses,
            consensus_level=self._calculate_consensus(all_responses),
        ))

        return all_responses

    async def _execute_consensus(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
        config: CollaborationContext,
    ) -> List[AgentResponse]:
        """Multiple rounds to build consensus"""
        all_responses = []

        for round_num in range(1, config.max_rounds + 1):
            # Build round context
            if all_responses:
                prev_round = "\n\n".join(
                    f"[{r.agent_name}]: {r.content[:300]}..."
                    for r in all_responses[-len(agents):] if r.success
                )
                round_context = f"{context}\n\nPrevious round:\n{prev_round}"
                round_prompt = f"Review and refine based on team feedback:\n{prompt}"
            else:
                round_context = context
                round_prompt = prompt

            # Get responses
            tasks = [agent.generate_response(round_prompt, round_context) for agent in agents]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            round_responses = [r for r in responses if isinstance(r, AgentResponse)]
            all_responses.extend(round_responses)

            # Check consensus
            consensus_level = self._calculate_consensus(round_responses)
            self.rounds.append(CollaborationRound(
                round_number=round_num,
                prompt=round_prompt,
                responses=round_responses,
                consensus_level=consensus_level,
            ))

            if consensus_level >= config.consensus_threshold:
                logger.info(f"Consensus reached at round {round_num}")
                break

        return all_responses

    async def _execute_devils_advocate(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
        config: CollaborationContext,
    ) -> List[AgentResponse]:
        """One agent challenges the others"""
        if len(agents) < 2:
            return await self._execute_parallel(agents, prompt, context)

        # Round 1: Initial solutions
        tasks = [agent.generate_response(prompt, context) for agent in agents]
        initial_responses = await asyncio.gather(*tasks, return_exceptions=True)
        initial_responses = [r for r in initial_responses if isinstance(r, AgentResponse)]

        self.rounds.append(CollaborationRound(
            round_number=1,
            prompt=prompt,
            responses=initial_responses,
            consensus_level=0.5,
            insights=["Initial solutions generated"],
        ))

        # Round 2: Generate challenges
        challenges = self._challenge_generator.generate(initial_responses)
        challenge_prompt = (
            f"Original task: {prompt}\n\n"
            f"Initial solutions provided. Now consider these challenges:\n"
            + "\n".join(f"- {c}" for c in challenges[:3])
            + "\n\nProvide a refined solution addressing these concerns."
        )

        tasks = [agent.generate_response(challenge_prompt, context) for agent in agents]
        refined_responses = await asyncio.gather(*tasks, return_exceptions=True)
        refined_responses = [r for r in refined_responses if isinstance(r, AgentResponse)]

        self.rounds.append(CollaborationRound(
            round_number=2,
            prompt=challenge_prompt,
            responses=refined_responses,
            consensus_level=self._calculate_consensus(refined_responses),
            insights=["Challenges addressed"],
            conflicts=challenges,
        ))

        return initial_responses + refined_responses

    async def _execute_peer_review(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
    ) -> List[AgentResponse]:
        """Agents review each other's work"""
        if len(agents) < 2:
            return await self._execute_parallel(agents, prompt, context)

        # Round 1: Initial solutions
        tasks = [agent.generate_response(prompt, context) for agent in agents]
        initial_responses = await asyncio.gather(*tasks, return_exceptions=True)
        initial_responses = [r for r in initial_responses if isinstance(r, AgentResponse)]

        self.rounds.append(CollaborationRound(
            round_number=1,
            prompt=prompt,
            responses=initial_responses,
            consensus_level=0.5,
        ))

        # Round 2: Peer review
        all_responses = list(initial_responses)
        for i, agent in enumerate(agents):
            # Review the next agent's work
            peer_idx = (i + 1) % len(agents)
            peer_response = initial_responses[peer_idx] if peer_idx < len(initial_responses) else None

            if peer_response and peer_response.success:
                review_prompt = (
                    f"Review this solution and provide feedback:\n\n"
                    f"Original task: {prompt}\n\n"
                    f"Solution from {peer_response.agent_name}:\n{peer_response.content}\n\n"
                    f"Provide constructive feedback and improvements."
                )
                review_response = await agent.generate_response(review_prompt, context)
                all_responses.append(review_response)

        self.rounds.append(CollaborationRound(
            round_number=2,
            prompt="Peer review round",
            responses=all_responses[len(initial_responses):],
            consensus_level=self._calculate_consensus(all_responses),
        ))

        return all_responses

    async def _execute_brainstorming(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
    ) -> List[AgentResponse]:
        """Creative brainstorming mode"""
        brainstorm_prompt = (
            f"BRAINSTORMING MODE: Think creatively and outside the box.\n\n"
            f"Task: {prompt}\n\n"
            f"Generate innovative, creative ideas. Don't worry about being practical yet - "
            f"focus on novel approaches and unique solutions."
        )

        tasks = [agent.generate_response(brainstorm_prompt, context) for agent in agents]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        responses = [r for r in responses if isinstance(r, AgentResponse)]

        self.rounds.append(CollaborationRound(
            round_number=1,
            prompt=brainstorm_prompt,
            responses=responses,
            consensus_level=0.4,  # Low consensus expected in brainstorming
            insights=["Creative ideas generated"],
        ))

        return responses

    def _calculate_consensus(self, responses: List[AgentResponse]) -> float:
        """Calculate consensus level from responses"""
        if len(responses) < 2:
            return 1.0

        successful = [r for r in responses if r.success]
        if not successful:
            return 0.0

        # Simple: base on confidence scores
        avg_confidence = sum(r.confidence for r in successful) / len(successful)

        # Variance penalty
        variance = sum((r.confidence - avg_confidence) ** 2 for r in successful) / len(successful)
        variance_penalty = min(variance * 0.5, 0.3)

        return max(0.0, avg_confidence - variance_penalty)

    def get_collaboration_summary(self) -> Dict[str, Any]:
        """Get summary of collaboration rounds"""
        return {
            "total_rounds": len(self.rounds),
            "rounds": [
                {
                    "number": r.round_number,
                    "responses": len(r.responses),
                    "consensus": r.consensus_level,
                    "insights": r.insights,
                    "conflicts": r.conflicts,
                }
                for r in self.rounds
            ],
            "final_consensus": self.rounds[-1].consensus_level if self.rounds else 0.0,
        }


class ConsensusBuilder:
    """Builds consensus from multiple agent responses"""

    def build(self, responses: List[AgentResponse]) -> Dict[str, Any]:
        """Analyze responses and build consensus"""
        if not responses:
            return {"consensus_level": 0.0, "agreements": [], "conflicts": []}

        successful = [r for r in responses if r.success]
        if not successful:
            return {"consensus_level": 0.0, "agreements": [], "conflicts": []}

        # Simple analysis
        avg_confidence = sum(r.confidence for r in successful) / len(successful)

        return {
            "consensus_level": avg_confidence,
            "agreements": [f"All agents responded successfully"],
            "conflicts": [],
        }


class ChallengeGenerator:
    """Generates challenges for devil's advocate mode"""

    CHALLENGE_TEMPLATES = [
        "What are the potential flaws or edge cases in this approach?",
        "How might this solution fail under heavy load or unusual conditions?",
        "What security vulnerabilities could exist?",
        "What alternative approaches were not considered?",
        "What assumptions are being made that might not hold true?",
    ]

    def generate(self, responses: List[AgentResponse]) -> List[str]:
        """Generate challenges for the given responses"""
        challenges = []

        # Add template challenges
        challenges.extend(self.CHALLENGE_TEMPLATES[:3])

        # Add response-specific challenges
        for response in responses[:2]:
            if response.success and len(response.content) > 100:
                challenges.append(
                    f"Challenge to {response.agent_name}'s solution: "
                    f"What if the opposite approach was better?"
                )

        return challenges
