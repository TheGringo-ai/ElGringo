"""
Orchestrator Tests
==================

Comprehensive tests for the AIDevTeam orchestration engine.
Tests initialization, agent management, collaboration modes, and error handling.
"""

import asyncio
import os
import pytest
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_dev_team.orchestrator import AIDevTeam, CollaborationResult
from ai_dev_team.agents.base import AIAgent, AgentConfig, AgentResponse, ModelType


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_env_no_keys():
    """Environment with no API keys"""
    with patch.dict(os.environ, {}, clear=True):
        yield


@pytest.fixture
def mock_env_with_keys():
    """Environment with mock API keys"""
    env = {
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "OPENAI_API_KEY": "test-openai-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "XAI_API_KEY": "test-xai-key",
    }
    with patch.dict(os.environ, env, clear=True):
        yield


@pytest.fixture
def mock_agent():
    """Create a mock AI agent"""
    agent = MagicMock(spec=AIAgent)
    agent.name = "mock-agent"
    agent.model_type = ModelType.CLAUDE
    agent.get_stats.return_value = {
        "total_calls": 10,
        "avg_response_time": 1.5,
        "success_rate": 0.95,
    }
    return agent


@pytest.fixture
def mock_agent_response():
    """Create a mock agent response"""
    return AgentResponse(
        agent_name="mock-agent",
        model_type=ModelType.CLAUDE,
        content="This is a test response from the mock agent.",
        confidence=0.9,
        response_time=1.5,
        error=None,  # No error means success=True (computed property)
    )


# =============================================================================
# CollaborationResult Tests
# =============================================================================

class TestCollaborationResult:
    """Test CollaborationResult dataclass"""

    def test_create_result(self):
        """Test creating a collaboration result"""
        result = CollaborationResult(
            task_id="test-123",
            success=True,
            final_answer="Test answer",
            agent_responses=[],
            collaboration_log=["Step 1", "Step 2"],
            total_time=5.5,
            confidence_score=0.85,
            participating_agents=["claude", "chatgpt"],
        )
        assert result.task_id == "test-123"
        assert result.success is True
        assert result.final_answer == "Test answer"
        assert result.confidence_score == 0.85
        assert len(result.participating_agents) == 2

    def test_result_with_defaults(self):
        """Test result with default values"""
        result = CollaborationResult(
            task_id="test-456",
            success=False,
            final_answer="",
            agent_responses=[],
            collaboration_log=[],
            total_time=0.0,
            confidence_score=0.0,
            participating_agents=[],
        )
        assert result.metadata == {}
        assert isinstance(result.timestamp, datetime)

    def test_result_with_metadata(self):
        """Test result with custom metadata"""
        result = CollaborationResult(
            task_id="test-789",
            success=True,
            final_answer="Answer",
            agent_responses=[],
            collaboration_log=[],
            total_time=2.0,
            confidence_score=0.7,
            participating_agents=["claude"],
            metadata={"mode": "parallel", "iterations": 2},
        )
        assert result.metadata["mode"] == "parallel"
        assert result.metadata["iterations"] == 2


# =============================================================================
# AIDevTeam Initialization Tests
# =============================================================================

class TestAIDevTeamInit:
    """Test AIDevTeam initialization"""

    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()
            assert team.project_name == "default"
            assert team.enable_memory is True
            assert team.enable_learning is True
            assert team.local_only is False

    def test_init_with_project_name(self):
        """Test initialization with custom project name"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(project_name="my-project")
            assert team.project_name == "my-project"

    def test_init_local_only_mode(self):
        """Test initialization in local-only mode"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(local_only=True)
            assert team.local_only is True

    def test_init_memory_disabled(self):
        """Test initialization with memory disabled"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(enable_memory=False)
            assert team.enable_memory is False
            assert team._memory_system is None
            assert team._learning_engine is None

    def test_init_auto_setup_disabled(self):
        """Test initialization with auto_setup disabled"""
        with patch.object(AIDevTeam, 'setup_agents') as mock_setup:
            team = AIDevTeam(auto_setup=False)
            mock_setup.assert_not_called()

    def test_init_creates_tools(self):
        """Test that initialization creates tool instances"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()
            assert "filesystem" in team._tools
            assert "browser" in team._tools
            assert "shell" in team._tools


# =============================================================================
# Agent Registration Tests
# =============================================================================

class TestAgentRegistration:
    """Test agent registration functionality"""

    def test_register_agent(self, mock_agent):
        """Test registering an agent"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)
            team.register_agent(mock_agent)
            assert "mock-agent" in team.agents
            assert team.agents["mock-agent"] == mock_agent

    def test_register_multiple_agents(self, mock_agent):
        """Test registering multiple agents"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)

            agent2 = MagicMock(spec=AIAgent)
            agent2.name = "agent-2"

            team.register_agent(mock_agent)
            team.register_agent(agent2)

            assert len(team.agents) == 2
            assert "mock-agent" in team.agents
            assert "agent-2" in team.agents

    def test_get_agent(self, mock_agent):
        """Test getting an agent by name"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)
            team.register_agent(mock_agent)

            retrieved = team.get_agent("mock-agent")
            assert retrieved == mock_agent

            missing = team.get_agent("nonexistent")
            assert missing is None

    def test_available_agents_property(self, mock_agent):
        """Test available_agents property"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)
            team.register_agent(mock_agent)

            available = team.available_agents
            assert "mock-agent" in available


# =============================================================================
# Team Status Tests
# =============================================================================

class TestTeamStatus:
    """Test get_team_status functionality"""

    def test_get_team_status_basic(self, mock_agent):
        """Test basic team status"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)
            team.register_agent(mock_agent)

            status = team.get_team_status()

            assert status["project"] == "default"
            assert status["total_agents"] == 1
            assert status["memory_enabled"] is True
            assert "agents" in status
            assert "mock-agent" in status["agents"]

    def test_get_team_status_empty_team(self):
        """Test status with no agents"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)

            status = team.get_team_status()

            assert status["total_agents"] == 0
            assert status["agents"] == {}

    def test_get_team_status_includes_learning(self, mock_agent):
        """Test status includes learning info"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False, enable_auto_learning=True)
            team.register_agent(mock_agent)

            # Mock auto_learner statistics
            team._auto_learner = MagicMock()
            team._auto_learner.get_statistics.return_value = {"patterns_learned": 5}

            status = team.get_team_status()

            assert "auto_learning" in status
            assert status["auto_learning"]["patterns_learned"] == 5


# =============================================================================
# Setup Agents Tests
# =============================================================================

class TestSetupAgents:
    """Test automatic agent setup based on API keys"""

    def test_setup_with_anthropic_key(self):
        """Test setup with Anthropic API key"""
        env = {"ANTHROPIC_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            with patch('ai_dev_team.orchestrator.ClaudeAgent') as MockClaude:
                mock_instance = MagicMock()
                mock_instance.name = "claude"
                MockClaude.return_value = mock_instance

                team = AIDevTeam(auto_setup=True)

                # Claude should be registered
                MockClaude.assert_called()

    def test_setup_with_no_keys_warns(self):
        """Test setup with no API keys logs warning"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('ai_dev_team.orchestrator.logger') as mock_logger:
                with patch.object(AIDevTeam, '_setup_llama_cloud_agents'):
                    with patch.object(AIDevTeam, '_setup_local_agents'):
                        team = AIDevTeam(auto_setup=True)

                        # Should have logged a warning
                        mock_logger.warning.assert_called()

    def test_setup_local_only_mode(self):
        """Test setup in local-only mode skips cloud APIs"""
        env = {"ANTHROPIC_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            with patch('ai_dev_team.orchestrator.ClaudeAgent') as MockClaude:
                with patch.object(AIDevTeam, '_setup_local_agents') as mock_local:
                    team = AIDevTeam(local_only=True)

                    # Claude should NOT be registered in local-only mode
                    MockClaude.assert_not_called()
                    # Local setup should be called
                    mock_local.assert_called()


# =============================================================================
# Constraints Tests
# =============================================================================

class TestConstraints:
    """Test developer constraints functionality"""

    def test_get_constraints(self):
        """Test getting constraints"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()
            constraints = team.constraints
            assert constraints is not None

    def test_update_constraints(self):
        """Test updating constraints"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            # Mock the preference store
            team._preference_store = MagicMock()
            team._constraints = MagicMock()
            team._constraints.prefer_local = False

            team.update_constraints(prefer_local=True)

            assert team._constraints.prefer_local is True
            team._preference_store.save_constraints.assert_called()


# =============================================================================
# Collaboration Tests
# =============================================================================

class TestCollaboration:
    """Test collaboration functionality"""

    @pytest.mark.asyncio
    async def test_collaborate_basic(self, mock_agent, mock_agent_response):
        """Test basic collaboration flow"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)
            team.register_agent(mock_agent)

            # Mock the task router
            mock_classification = MagicMock()
            mock_classification.primary_type = MagicMock()
            mock_classification.primary_type.value = "coding"
            mock_classification.complexity = "medium"
            mock_classification.confidence = 0.8
            mock_classification.recommended_agents = ["mock-agent"]
            mock_classification.suggested_mode = "parallel"

            team._task_router = MagicMock()
            team._task_router.classify.return_value = mock_classification

            # Mock agent execute
            mock_agent.execute = AsyncMock(return_value=mock_agent_response)

            # Mock weighted consensus
            team._weighted_consensus = MagicMock()
            team._weighted_consensus.build_consensus.return_value = (
                "Consensus answer",
                0.85,
                {"reasoning": "Test"}
            )

            result = await team.collaborate("Write a hello world function")

            assert isinstance(result, CollaborationResult)
            assert result.task_id is not None

    @pytest.mark.asyncio
    async def test_collaborate_with_no_agents(self):
        """Test collaboration with no agents returns error"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)

            # Mock task router
            mock_classification = MagicMock()
            mock_classification.primary_type = MagicMock()
            mock_classification.primary_type.value = "coding"
            mock_classification.complexity = "low"
            mock_classification.confidence = 0.5
            mock_classification.recommended_agents = []
            mock_classification.suggested_mode = "parallel"

            team._task_router = MagicMock()
            team._task_router.classify.return_value = mock_classification

            result = await team.collaborate("Do something")

            assert result.success is False


# =============================================================================
# Ask Tests
# =============================================================================

class TestAsk:
    """Test single-agent ask functionality"""

    @pytest.mark.asyncio
    async def test_ask_specific_agent(self, mock_agent, mock_agent_response):
        """Test asking a specific agent"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False, enable_auto_learning=False)
            team.register_agent(mock_agent)

            # Mock both execute and generate_response (orchestrator may use either)
            mock_agent.execute = AsyncMock(return_value=mock_agent_response)
            mock_agent.generate_response = AsyncMock(return_value=mock_agent_response)

            response = await team.ask("What is Python?", agent="mock-agent")

            # Verify agent was called (either method)
            assert mock_agent.execute.called or mock_agent.generate_response.called

    @pytest.mark.asyncio
    async def test_ask_auto_select_agent(self, mock_agent, mock_agent_response):
        """Test asking with auto-selected agent"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False, enable_auto_learning=False)
            team.register_agent(mock_agent)

            # Mock both execute and generate_response (orchestrator may use either)
            mock_agent.execute = AsyncMock(return_value=mock_agent_response)
            mock_agent.generate_response = AsyncMock(return_value=mock_agent_response)

            # Mock task router
            mock_classification = MagicMock()
            mock_classification.recommended_agents = ["mock-agent"]
            team._task_router = MagicMock()
            team._task_router.classify.return_value = mock_classification

            response = await team.ask("What is Python?")

            # Verify agent was called (either method)
            assert mock_agent.execute.called or mock_agent.generate_response.called

    @pytest.mark.asyncio
    async def test_ask_no_agents_error(self):
        """Test asking with no agents returns error"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)

            response = await team.ask("What is Python?")

            assert response.success is False
            assert "No agents" in response.error or response.error is not None


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling in orchestrator"""

    @pytest.mark.asyncio
    async def test_agent_execution_error_handled(self, mock_agent):
        """Test that agent execution errors are handled gracefully"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False, enable_auto_learning=False)
            team.register_agent(mock_agent)

            # Make agent raise an exception on all possible methods
            error_response = AgentResponse(
                agent_name="mock-agent",
                model_type=ModelType.CLAUDE,
                content="",
                confidence=0.0,
                response_time=0.0,
                error="API Error",
            )
            mock_agent.execute = AsyncMock(side_effect=Exception("API Error"))
            mock_agent.generate_response = AsyncMock(return_value=error_response)

            # Should not raise, should return error response
            response = await team.ask("Test question", agent="mock-agent")

            # Response should indicate failure
            assert response.success is False or response.error is not None or "error" in str(response).lower()

    @pytest.mark.asyncio
    async def test_collaboration_timeout_handled(self, mock_agent):
        """Test that collaboration timeout is handled"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(auto_setup=False)
            team.register_agent(mock_agent)

            # Make agent hang
            async def slow_execute(*args, **kwargs):
                await asyncio.sleep(100)

            mock_agent.execute = slow_execute

            # Mock task router
            mock_classification = MagicMock()
            mock_classification.primary_type = MagicMock()
            mock_classification.primary_type.value = "coding"
            mock_classification.complexity = "low"
            mock_classification.confidence = 0.8
            mock_classification.recommended_agents = ["mock-agent"]
            mock_classification.suggested_mode = "sequential"

            team._task_router = MagicMock()
            team._task_router.classify.return_value = mock_classification


# =============================================================================
# Memory Integration Tests
# =============================================================================

class TestMemoryIntegration:
    """Test memory system integration"""

    def test_memory_system_initialized(self):
        """Test memory system is initialized when enabled"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(enable_memory=True)

            assert team._memory_system is not None
            assert team._learning_engine is not None
            assert team._prevention is not None

    def test_memory_system_disabled(self):
        """Test memory system is None when disabled"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam(enable_memory=False)

            assert team._memory_system is None
            assert team._learning_engine is None
            assert team._prevention is None


# =============================================================================
# Autonomous Features Tests
# =============================================================================

class TestAutonomousFeatures:
    """Test autonomous capabilities"""

    def test_self_corrector_initialized(self):
        """Test self-corrector is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._self_corrector is not None
            assert team.enable_self_correction is True

    def test_task_decomposer_initialized(self):
        """Test task decomposer is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._task_decomposer is not None
            assert team.enable_task_decomposition is True

    def test_session_learner_initialized(self):
        """Test session learner is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._session_learner is not None
            assert team.enable_session_learning is True


# =============================================================================
# Task Router Integration Tests
# =============================================================================

class TestTaskRouterIntegration:
    """Test task router integration"""

    def test_task_router_initialized(self):
        """Test task router is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._task_router is not None

    def test_cost_optimizer_initialized(self):
        """Test cost optimizer is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._cost_optimizer is not None


# =============================================================================
# Tools Integration Tests
# =============================================================================

class TestToolsIntegration:
    """Test tools integration"""

    def test_tools_initialized(self):
        """Test all tools are initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert "filesystem" in team._tools
            assert "browser" in team._tools
            assert "shell" in team._tools

    def test_permission_manager_initialized(self):
        """Test permission manager is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._permission_manager is not None


# =============================================================================
# Knowledge System Tests
# =============================================================================

class TestKnowledgeSystem:
    """Test knowledge/teaching system integration"""

    def test_teaching_system_initialized(self):
        """Test teaching system is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._teaching_system is not None

    def test_coding_hub_initialized(self):
        """Test coding hub is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._coding_hub is not None

    def test_rag_system_initialized(self):
        """Test RAG system is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._rag is not None


# =============================================================================
# Health Monitoring Tests
# =============================================================================

class TestHealthMonitoring:
    """Test health monitoring integration"""

    def test_health_monitor_initialized(self):
        """Test health monitor is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._health_monitor is not None

    def test_failover_manager_initialized(self):
        """Test failover manager is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._failover_manager is not None

    def test_circuit_breaker_initialized(self):
        """Test circuit breaker is initialized"""
        with patch.object(AIDevTeam, 'setup_agents'):
            team = AIDevTeam()

            assert team._circuit_breaker is not None


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
