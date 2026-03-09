"""
Agent Tests
===========

Tests for AI agent base classes and implementations.
"""

import os
import pytest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elgringo.agents.base import (
    AgentConfig,
    AgentResponse,
    ModelType,
)


class TestModelType:
    """Test ModelType enum"""

    def test_model_types_exist(self):
        """Model types enum should have members"""
        # Check that ModelType has at least some members
        assert len(list(ModelType)) > 0


class TestAgentConfig:
    """Test AgentConfig dataclass"""

    def test_create_config(self):
        """Test creating agent config"""
        config = AgentConfig(
            name="test-agent",
            model_type=ModelType.CLAUDE,
            role="tester",
            capabilities=["testing"],
        )
        assert config.name == "test-agent"
        assert config.model_type == ModelType.CLAUDE
        assert config.role == "tester"

    def test_config_defaults(self):
        """Test default values"""
        config = AgentConfig(
            name="test",
            model_type=ModelType.CLAUDE,
            role="tester",
            capabilities=[],
        )
        assert config.temperature == 0.7
        assert config.max_tokens == 4000
        assert config.enabled is True


class TestAgentResponse:
    """Test AgentResponse dataclass"""

    def test_create_response(self):
        """Test creating agent response"""
        response = AgentResponse(
            agent_name="claude",
            model_type=ModelType.CLAUDE,
            content="Test response",
            confidence=0.9,
            response_time=1.5,
        )
        assert response.agent_name == "claude"
        assert response.content == "Test response"
        assert response.confidence == 0.9
        assert response.success is True

    def test_failed_response(self):
        """Test creating failed response"""
        response = AgentResponse(
            agent_name="claude",
            model_type=ModelType.CLAUDE,
            content="",
            confidence=0.0,
            response_time=0.5,
            error="API Error",
        )
        assert response.error == "API Error"
        assert response.success is False

    def test_response_with_metadata(self):
        """Test response with metadata"""
        response = AgentResponse(
            agent_name="claude",
            model_type=ModelType.CLAUDE,
            content="Test",
            confidence=0.85,
            response_time=2.0,
            metadata={"tokens": 100, "model": "claude-3-sonnet"},
        )
        assert response.metadata["tokens"] == 100


class TestClaudeAgent:
    """Test Claude agent"""

    def test_import(self):
        """Should be importable"""
        from elgringo.agents.claude import ClaudeAgent
        assert ClaudeAgent is not None

    def test_create_with_default_config(self):
        """Creating with default config should work"""
        from elgringo.agents.claude import ClaudeAgent
        # Should not raise during creation
        agent = ClaudeAgent()
        assert agent.name == "claude-analyst"


class TestChatGPTAgent:
    """Test ChatGPT agent"""

    def test_import(self):
        """Should be importable"""
        from elgringo.agents.chatgpt import ChatGPTAgent
        assert ChatGPTAgent is not None

    def test_create_with_default_config(self):
        """Creating with default config should work"""
        from elgringo.agents.chatgpt import ChatGPTAgent
        agent = ChatGPTAgent()
        assert "chatgpt" in agent.name.lower()


class TestGeminiAgent:
    """Test Gemini agent"""

    def test_import(self):
        """Should be importable"""
        from elgringo.agents.gemini import GeminiAgent
        assert GeminiAgent is not None

    def test_create_with_default_config(self):
        """Creating with default config should work"""
        from elgringo.agents.gemini import GeminiAgent
        agent = GeminiAgent()
        assert "gemini" in agent.name.lower()


class TestGrokAgent:
    """Test Grok agent"""

    def test_import(self):
        """Should be importable"""
        from elgringo.agents.grok import GrokAgent
        assert GrokAgent is not None

    def test_create_with_default_config(self):
        """Creating with default config should work"""
        from elgringo.agents.grok import GrokAgent
        agent = GrokAgent()
        assert "grok" in agent.name.lower()


class TestOllamaAgent:
    """Test Ollama agent"""

    def test_import(self):
        """Should be importable"""
        from elgringo.agents.ollama import OllamaAgent
        assert OllamaAgent is not None

    def test_create_with_default_config(self):
        """Create Ollama agent with default config"""
        from elgringo.agents.ollama import OllamaAgent
        agent = OllamaAgent()
        assert agent.name is not None


class TestAgentExports:
    """Test agent module exports"""

    def test_agent_response_exported(self):
        """AgentResponse should be exported"""
        from elgringo.agents import AgentResponse
        assert AgentResponse is not None

    def test_model_type_exported(self):
        """ModelType should be exported"""
        from elgringo.agents import ModelType
        assert ModelType is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
