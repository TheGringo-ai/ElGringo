"""
Pytest Configuration
====================

Shared fixtures and configuration for tests.
"""

import os
import sys
import pytest
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory"""
    storage_dir = tmp_path / "ai_team_memory"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables for testing"""
    # Clear API keys to prevent accidental API calls
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)


@pytest.fixture
def memory_system(temp_storage):
    """Create a test memory system"""
    from elgringo.memory import MemorySystem
    return MemorySystem(storage_dir=str(temp_storage))


@pytest.fixture
def weighted_consensus():
    """Create a weighted consensus instance"""
    from elgringo.collaboration import WeightedConsensus
    return WeightedConsensus()


@pytest.fixture
def fredfix(memory_system):
    """Create a FredFix instance without team"""
    from elgringo.workflows.fredfix import FredFix
    return FredFix(memory=memory_system)


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)
