"""
Collaboration Engine Tests
==========================

Tests for collaboration patterns and weighted consensus.
"""

import asyncio
import os
import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_dev_team.collaboration.engine import (
    CollaborationEngine,
    CollaborationMode,
    CollaborationContext,
    CollaborationRound,
    ConsensusBuilder,
    ChallengeGenerator,
)
from ai_dev_team.collaboration.weighted_consensus import (
    WeightedConsensus,
    Vote,
    ConsensusResult,
    DebateRound,
)
from ai_dev_team.agents.base import AgentResponse, ModelType


class TestCollaborationMode:
    """Test CollaborationMode enum"""

    def test_all_modes_defined(self):
        """All collaboration modes should be defined"""
        expected_modes = [
            "PARALLEL",
            "SEQUENTIAL",
            "CONSENSUS",
            "DEVILS_ADVOCATE",
            "PEER_REVIEW",
            "BRAINSTORMING",
            "DEBATE",
            "EXPERT_PANEL",
        ]
        for mode in expected_modes:
            assert hasattr(CollaborationMode, mode)

    def test_mode_values(self):
        """Mode values should be lowercase strings"""
        assert CollaborationMode.PARALLEL.value == "parallel"
        assert CollaborationMode.CONSENSUS.value == "consensus"
        assert CollaborationMode.DEBATE.value == "debate"


class TestCollaborationContext:
    """Test CollaborationContext dataclass"""

    def test_default_values(self):
        """Test default context values"""
        ctx = CollaborationContext(mode=CollaborationMode.PARALLEL)
        assert ctx.mode == CollaborationMode.PARALLEL
        assert ctx.max_rounds == 3
        assert ctx.consensus_threshold == 0.8
        assert ctx.timeout_seconds == 120
        assert ctx.require_all_agents is False
        assert ctx.allow_disagreement is True

    def test_custom_values(self):
        """Test custom context values"""
        ctx = CollaborationContext(
            mode=CollaborationMode.CONSENSUS,
            max_rounds=5,
            consensus_threshold=0.9,
        )
        assert ctx.max_rounds == 5
        assert ctx.consensus_threshold == 0.9


class TestCollaborationRound:
    """Test CollaborationRound dataclass"""

    def test_create_round(self):
        """Test creating a collaboration round"""
        response = AgentResponse(
            agent_name="test",
            model_type=ModelType.CLAUDE,
            content="Test response",
            confidence=0.9,
            response_time=1.0,
        )
        round = CollaborationRound(
            round_number=1,
            prompt="Test prompt",
            responses=[response],
            consensus_level=0.85,
        )
        assert round.round_number == 1
        assert len(round.responses) == 1
        assert round.consensus_level == 0.85

    def test_round_defaults(self):
        """Test default values"""
        round = CollaborationRound(
            round_number=1,
            prompt="Test",
            responses=[],
            consensus_level=0.5,
        )
        assert round.insights == []
        assert round.conflicts == []


class TestVote:
    """Test Vote dataclass"""

    def test_vote_weighted_score(self):
        """Test weighted score calculation"""
        vote = Vote(
            agent_name="claude",
            position="Test position",
            confidence=0.9,
            expertise_weight=0.95,
            reasoning="Test reasoning",
        )
        # weighted_score = confidence * expertise_weight
        assert vote.weighted_score == pytest.approx(0.855, rel=0.01)

    def test_vote_low_expertise(self):
        """Test vote with low expertise"""
        vote = Vote(
            agent_name="unknown",
            position="Test",
            confidence=0.8,
            expertise_weight=0.5,
            reasoning="",
        )
        assert vote.weighted_score == pytest.approx(0.4, rel=0.01)


class TestWeightedConsensus:
    """Test WeightedConsensus class"""

    @pytest.fixture
    def consensus(self):
        return WeightedConsensus()

    def test_expertise_weight_claude(self, consensus):
        """Claude should have high analysis expertise"""
        weight = consensus.get_expertise_weight("claude-analyst", "analysis")
        assert weight >= 0.9

    def test_expertise_weight_chatgpt(self, consensus):
        """ChatGPT should have high coding expertise"""
        weight = consensus.get_expertise_weight("chatgpt-coder", "coding")
        assert weight >= 0.9

    def test_expertise_weight_gemini(self, consensus):
        """Gemini should have high creative expertise"""
        weight = consensus.get_expertise_weight("gemini-creative", "creative")
        assert weight >= 0.9

    def test_expertise_weight_grok(self, consensus):
        """Grok reasoner should have high analysis expertise"""
        weight = consensus.get_expertise_weight("grok-reasoner", "analysis")
        assert weight >= 0.9

    def test_expertise_weight_partial_match(self, consensus):
        """Partial name matches should work"""
        weight = consensus.get_expertise_weight("my-claude-agent", "analysis")
        assert weight >= 0.9

    def test_expertise_weight_unknown_agent(self, consensus):
        """Unknown agents should get default weight"""
        weight = consensus.get_expertise_weight("completely-unknown-xyz", "coding")
        assert 0.4 <= weight <= 0.6

    def test_expertise_weight_unknown_task(self, consensus):
        """Unknown task types should fall back to general"""
        weight = consensus.get_expertise_weight("claude", "unknown_task_xyz")
        assert weight > 0

    def test_calculate_weighted_vote_empty(self, consensus):
        """Empty responses should return no consensus"""
        result = consensus.calculate_weighted_vote([], "coding")
        assert not result.consensus_reached
        assert result.consensus_level == 0.0

    def test_calculate_weighted_vote_single(self, consensus):
        """Single successful response"""
        response = AgentResponse(
            agent_name="claude",
            model_type=ModelType.CLAUDE,
            content="Test answer",
            confidence=0.9,
            response_time=1.0,
        )
        result = consensus.calculate_weighted_vote([response], "analysis")
        assert len(result.votes) == 1

    def test_calculate_weighted_vote_multiple(self, consensus):
        """Multiple responses should calculate consensus"""
        responses = [
            AgentResponse(
                agent_name="claude",
                model_type=ModelType.CLAUDE,
                content="Answer A",
                confidence=0.9,
                response_time=1.0,
            ),
            AgentResponse(
                agent_name="chatgpt",
                model_type=ModelType.CHATGPT,
                content="Answer B",
                confidence=0.85,
                response_time=1.0,
            ),
        ]
        result = consensus.calculate_weighted_vote(responses, "coding")
        assert len(result.votes) == 2
        assert result.winning_position != ""

    def test_calculate_weighted_vote_failed_responses(self, consensus):
        """Failed responses should be filtered out"""
        responses = [
            AgentResponse(
                agent_name="claude",
                model_type=ModelType.CLAUDE,
                content="",
                confidence=0.0,
                response_time=1.0,
                error="API Error",
            ),
        ]
        result = consensus.calculate_weighted_vote(responses, "coding")
        assert result.consensus_level == 0.0

    def test_synthesize_with_weights(self, consensus):
        """Test weighted synthesis"""
        responses = [
            AgentResponse(
                agent_name="claude",
                model_type=ModelType.CLAUDE,
                content="Claude's analysis",
                confidence=0.9,
                response_time=1.0,
            ),
            AgentResponse(
                agent_name="chatgpt",
                model_type=ModelType.CHATGPT,
                content="ChatGPT's code",
                confidence=0.85,
                response_time=1.0,
            ),
        ]
        result = consensus.synthesize_with_weights(responses, "analysis")
        assert "claude" in result.lower()
        assert "chatgpt" in result.lower()

    def test_synthesize_empty(self, consensus):
        """Empty responses should return empty string"""
        result = consensus.synthesize_with_weights([], "coding")
        assert result == ""


class TestConsensusResult:
    """Test ConsensusResult dataclass"""

    def test_create_result(self):
        """Test creating a consensus result"""
        result = ConsensusResult(
            consensus_reached=True,
            consensus_level=0.85,
            winning_position="Position A",
            votes=[],
        )
        assert result.consensus_reached
        assert result.consensus_level == 0.85

    def test_result_defaults(self):
        """Test default values"""
        result = ConsensusResult(
            consensus_reached=False,
            consensus_level=0.0,
            winning_position="",
            votes=[],
        )
        assert result.debate_rounds == []
        assert result.disagreements == []
        assert result.final_synthesis == ""


class TestDebateRound:
    """Test DebateRound dataclass"""

    def test_create_debate_round(self):
        """Test creating a debate round"""
        round = DebateRound(
            round_number=1,
            topic="Architecture decision",
            arguments=[{"agent": "claude", "argument": "Use microservices"}],
            votes_after={"claude": 0.9},
        )
        assert round.round_number == 1
        assert len(round.arguments) == 1


class TestCollaborationEngine:
    """Test CollaborationEngine class"""

    @pytest.fixture
    def engine(self):
        return CollaborationEngine()

    def test_initialization(self, engine):
        """Test engine initializes correctly"""
        assert engine.rounds == []

    def test_calculate_consensus_empty(self, engine):
        """Empty responses should return 1.0 consensus"""
        result = engine._calculate_consensus([])
        assert result == 1.0

    def test_calculate_consensus_single(self, engine):
        """Single response should return its confidence"""
        response = AgentResponse(
            agent_name="test",
            model_type=ModelType.CLAUDE,
            content="Test",
            confidence=0.9,
            response_time=1.0,
        )
        result = engine._calculate_consensus([response])
        assert result == 1.0

    def test_calculate_consensus_multiple_similar(self, engine):
        """Similar confidences should have high consensus"""
        responses = [
            AgentResponse(
                agent_name="a",
                model_type=ModelType.CLAUDE,
                content="Test",
                confidence=0.85,
                response_time=1.0,
            ),
            AgentResponse(
                agent_name="b",
                model_type=ModelType.CHATGPT,
                content="Test",
                confidence=0.87,
                response_time=1.0,
            ),
        ]
        result = engine._calculate_consensus(responses)
        assert result > 0.8

    def test_calculate_consensus_divergent(self, engine):
        """Divergent confidences should reduce consensus"""
        responses = [
            AgentResponse(
                agent_name="a",
                model_type=ModelType.CLAUDE,
                content="Test",
                confidence=0.95,
                response_time=1.0,
            ),
            AgentResponse(
                agent_name="b",
                model_type=ModelType.CHATGPT,
                content="Test",
                confidence=0.5,
                response_time=1.0,
            ),
        ]
        result = engine._calculate_consensus(responses)
        # Variance penalty should reduce consensus
        assert result < 0.9

    def test_get_collaboration_summary_empty(self, engine):
        """Summary of empty collaboration"""
        summary = engine.get_collaboration_summary()
        assert summary["total_rounds"] == 0
        assert summary["rounds"] == []
        assert summary["final_consensus"] == 0.0


class TestConsensusBuilder:
    """Test ConsensusBuilder class"""

    @pytest.fixture
    def builder(self):
        return ConsensusBuilder()

    def test_build_empty(self, builder):
        """Empty responses should return 0 consensus"""
        result = builder.build([])
        assert result["consensus_level"] == 0.0

    def test_build_with_responses(self, builder):
        """Build consensus from responses"""
        responses = [
            AgentResponse(
                agent_name="test",
                model_type=ModelType.CLAUDE,
                content="Test",
                confidence=0.9,
                response_time=1.0,
            ),
        ]
        result = builder.build(responses)
        assert result["consensus_level"] == 0.9


class TestChallengeGenerator:
    """Test ChallengeGenerator class"""

    @pytest.fixture
    def generator(self):
        return ChallengeGenerator()

    def test_generate_challenges_empty(self, generator):
        """Empty responses should still generate template challenges"""
        challenges = generator.generate([])
        assert len(challenges) >= 3

    def test_generate_challenges_with_responses(self, generator):
        """Responses should add agent-specific challenges"""
        responses = [
            AgentResponse(
                agent_name="claude",
                model_type=ModelType.CLAUDE,
                content="A" * 200,  # Long enough content
                confidence=0.9,
                response_time=1.0,
            ),
        ]
        challenges = generator.generate(responses)
        assert len(challenges) > 3

    def test_challenge_templates_exist(self, generator):
        """Should have challenge templates"""
        assert len(generator.CHALLENGE_TEMPLATES) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
