"""
Weighted Consensus - Real voting system with expertise weights and debate
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List

from ..agents import AgentResponse, AIAgent

logger = logging.getLogger(__name__)


@dataclass
class Vote:
    """Individual vote from an agent"""
    agent_name: str
    position: str  # Summary of stance
    confidence: float
    expertise_weight: float  # Based on task type match
    reasoning: str
    weighted_score: float = 0.0

    def __post_init__(self):
        self.weighted_score = self.confidence * self.expertise_weight


@dataclass
class DebateRound:
    """A round of debate between disagreeing agents"""
    round_number: int
    topic: str
    arguments: List[Dict[str, str]]
    votes_after: Dict[str, float]


@dataclass
class ConsensusResult:
    """Result of weighted consensus building"""
    consensus_reached: bool
    consensus_level: float
    winning_position: str
    votes: List[Vote]
    debate_rounds: List[DebateRound] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    final_synthesis: str = ""


class WeightedConsensus:
    """
    Weighted consensus builder with debate mechanism.

    Uses expertise weights and confidence scores to build
    real consensus, with debate rounds for disagreements.
    """

    # Agent expertise by task type - comprehensive mapping
    AGENT_EXPERTISE: Dict[str, Dict[str, float]] = {
        # ChatGPT agents (Lead Developer & Architect)
        "chatgpt-coder": {
            "coding": 1.0, "debugging": 0.95, "testing": 0.9,
            "analysis": 0.95, "documentation": 0.85, "optimization": 0.9,
            "general": 0.9, "architecture": 0.9, "security": 0.8,
            "research": 0.85,
        },
        "chatgpt": {
            "coding": 1.0, "debugging": 0.95, "testing": 0.9,
            "analysis": 0.95, "documentation": 0.85, "optimization": 0.9,
            "general": 0.9, "architecture": 0.9, "security": 0.8,
            "research": 0.85,
        },
        # Claude agents (optional - Analyst & Researcher)
        "claude-analyst": {
            "analysis": 0.85, "architecture": 0.8, "research": 0.85,
            "coding": 0.7, "debugging": 0.75, "security": 0.8,
            "general": 0.75, "creative": 0.7, "documentation": 0.8,
        },
        "claude": {
            "analysis": 0.85, "architecture": 0.8, "research": 0.85,
            "coding": 0.7, "debugging": 0.75, "security": 0.8,
            "general": 0.75, "creative": 0.7, "documentation": 0.8,
        },
        # Gemini agents
        "gemini-coder": {
            "creative": 1.0, "ui_ux": 0.95, "documentation": 0.9,
            "analysis": 0.6, "coding": 0.65, "research": 0.75,
            "general": 0.7, "architecture": 0.6, "brainstorming": 1.0,
        },
        "gemini": {
            "creative": 1.0, "ui_ux": 0.95, "documentation": 0.9,
            "analysis": 0.6, "coding": 0.65, "research": 0.75,
            "general": 0.7, "architecture": 0.6, "brainstorming": 1.0,
        },
        # Grok agents
        "grok-reasoner": {
            "analysis": 0.95, "architecture": 0.9, "research": 0.95,
            "coding": 0.7, "strategy": 1.0, "debugging": 0.75,
            "general": 0.85, "security": 0.85, "reasoning": 1.0,
        },
        "grok-coder": {
            "coding": 0.95, "optimization": 1.0, "debugging": 0.9,
            "analysis": 0.65, "testing": 0.8, "security": 0.75,
            "general": 0.75, "performance": 1.0, "refactoring": 0.9,
        },
        "grok": {
            "coding": 0.9, "optimization": 0.9, "debugging": 0.85,
            "analysis": 0.8, "testing": 0.75, "security": 0.8,
            "general": 0.8, "reasoning": 0.95, "strategy": 0.9,
        },
        # Local Ollama agents
        "llama3": {
            "coding": 0.7, "analysis": 0.65, "debugging": 0.6,
            "general": 0.75, "documentation": 0.7, "creative": 0.65,
            "research": 0.6, "testing": 0.6, "architecture": 0.55,
        },
        "qwen-coder": {
            "coding": 0.85, "debugging": 0.8, "optimization": 0.8,
            "general": 0.6, "analysis": 0.55, "testing": 0.75,
            "documentation": 0.5, "architecture": 0.5, "security": 0.6,
        },
    }

    # Default expertise for unknown agents
    DEFAULT_EXPERTISE: Dict[str, float] = {
        "coding": 0.5, "analysis": 0.5, "debugging": 0.5,
        "general": 0.5, "creative": 0.5, "documentation": 0.5,
        "architecture": 0.5, "security": 0.5, "testing": 0.5,
        "optimization": 0.5, "research": 0.5, "strategy": 0.5,
    }

    def __init__(self, consensus_threshold: float = 0.75):
        self.consensus_threshold = consensus_threshold

    def get_expertise_weight(self, agent_name: str, task_type: str) -> float:
        """Get expertise weight for an agent on a task type"""
        # Try exact match first
        agent_expertise = self.AGENT_EXPERTISE.get(agent_name, {})

        # If not found, try partial match (e.g., "claude-analyst" matches "claude")
        if not agent_expertise:
            for key in self.AGENT_EXPERTISE:
                if key in agent_name.lower() or agent_name.lower() in key:
                    agent_expertise = self.AGENT_EXPERTISE[key]
                    break

        # Fall back to default expertise
        if not agent_expertise:
            agent_expertise = self.DEFAULT_EXPERTISE

        return agent_expertise.get(task_type, agent_expertise.get("general", 0.5))

    def calculate_weighted_vote(
        self,
        responses: List[AgentResponse],
        task_type: str,
    ) -> ConsensusResult:
        """
        Calculate weighted consensus from agent responses.

        Args:
            responses: List of agent responses
            task_type: The type of task being performed

        Returns:
            ConsensusResult with voting analysis
        """
        if not responses:
            return ConsensusResult(
                consensus_reached=False,
                consensus_level=0.0,
                winning_position="",
                votes=[],
            )

        successful = [r for r in responses if r.success]
        if not successful:
            return ConsensusResult(
                consensus_reached=False,
                consensus_level=0.0,
                winning_position="No successful responses",
                votes=[],
            )

        # Build votes
        votes = []
        for response in successful:
            expertise_weight = self.get_expertise_weight(response.agent_name, task_type)

            vote = Vote(
                agent_name=response.agent_name,
                position=self._extract_position(response.content),
                confidence=response.confidence,
                expertise_weight=expertise_weight,
                reasoning=response.content[:500],
            )
            votes.append(vote)

        # Calculate weighted scores
        total_weight = sum(v.weighted_score for v in votes)
        if total_weight == 0:
            total_weight = 1.0

        # Normalize scores
        for vote in votes:
            vote.weighted_score = vote.weighted_score / total_weight

        # Detect disagreements
        disagreements = self._detect_disagreements(votes)

        # Calculate consensus level based on score distribution
        max_score = max(v.weighted_score for v in votes)
        score_variance = self._calculate_variance([v.weighted_score for v in votes])
        consensus_level = max_score * (1 - min(score_variance * 2, 0.5))

        # Get winning position
        winning_vote = max(votes, key=lambda v: v.weighted_score)

        return ConsensusResult(
            consensus_reached=consensus_level >= self.consensus_threshold,
            consensus_level=consensus_level,
            winning_position=winning_vote.position,
            votes=votes,
            disagreements=disagreements,
        )

    def _extract_position(self, content: str) -> str:
        """Extract a summary position from response content"""
        # Take first sentence or first 200 chars
        if "." in content[:200]:
            return content[:content.index(".") + 1]
        return content[:200] + "..."

    def _detect_disagreements(self, votes: List[Vote]) -> List[str]:
        """Detect disagreements between agents"""
        disagreements = []

        # Check for significantly different confidence levels
        confidences = [v.confidence for v in votes]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            for vote in votes:
                if abs(vote.confidence - avg_confidence) > 0.3:
                    disagreements.append(
                        f"{vote.agent_name} has significantly different confidence "
                        f"({vote.confidence:.2f} vs avg {avg_confidence:.2f})"
                    )

        # Check for weighted score outliers
        scores = [v.weighted_score for v in votes]
        if len(scores) > 1:
            avg_score = sum(scores) / len(scores)
            for vote in votes:
                if vote.weighted_score < avg_score * 0.5:
                    disagreements.append(
                        f"{vote.agent_name}'s position has low support (score: {vote.weighted_score:.2f})"
                    )

        return disagreements

    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)

    async def initiate_debate(
        self,
        disagreements: List[str],
        agents: List[AIAgent],
        original_prompt: str,
        context: str = "",
    ) -> List[DebateRound]:
        """
        Initiate debate rounds for disagreements.

        Args:
            disagreements: List of identified disagreements
            agents: Agents to participate in debate
            original_prompt: Original task prompt
            context: Additional context

        Returns:
            List of debate rounds
        """
        if not disagreements or len(agents) < 2:
            return []

        debate_rounds = []

        for i, disagreement in enumerate(disagreements[:2]):  # Max 2 debate rounds
            debate_prompt = f"""DEBATE ROUND: Address this disagreement in the team's analysis.

Original Task: {original_prompt}

Disagreement: {disagreement}

Provide your argument defending or refining your position. Be concise and specific.
Focus on evidence and reasoning, not on criticizing other positions."""

            arguments = []
            for agent in agents[:3]:  # Max 3 agents in debate
                try:
                    response = await agent.generate_response(debate_prompt, context)
                    if response.success:
                        arguments.append({
                            "agent": agent.name,
                            "argument": response.content[:500],
                            "confidence": response.confidence,
                        })
                except Exception as e:
                    logger.warning(f"Debate error from {agent.name}: {e}")

            # Calculate votes after debate
            votes_after = {}
            for arg in arguments:
                votes_after[arg["agent"]] = arg["confidence"]

            debate_rounds.append(DebateRound(
                round_number=i + 1,
                topic=disagreement,
                arguments=arguments,
                votes_after=votes_after,
            ))

        return debate_rounds

    def synthesize_with_weights(
        self,
        responses: List[AgentResponse],
        task_type: str,
    ) -> str:
        """
        Synthesize responses using weighted contributions.

        Higher weighted agents contribute more to the synthesis.
        """
        if not responses:
            return ""

        successful = [r for r in responses if r.success]
        if not successful:
            return "No successful responses to synthesize."

        # Get weighted contributions
        weighted_parts = []
        for response in successful:
            weight = self.get_expertise_weight(response.agent_name, task_type)
            weight_label = "HIGH" if weight > 0.8 else "MEDIUM" if weight > 0.6 else "STANDARD"
            weighted_parts.append(
                f"[{response.agent_name} - Expertise: {weight_label}]\n{response.content}"
            )

        return "\n\n---\n\n".join(weighted_parts)
