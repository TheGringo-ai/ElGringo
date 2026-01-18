"""
AI Development Team - Multi-Model AI Orchestration Platform
============================================================

A standalone, reusable AI development team that orchestrates multiple AI models
(Claude, ChatGPT, Gemini, Grok) for collaborative software development.

Features:
- Multi-model orchestration with intelligent task routing
- Never-repeat-mistakes memory system
- Advanced collaboration patterns (consensus, devil's advocate, peer review)
- Performance optimization with caching
- Cross-project learning and knowledge sharing
- Self-sustaining monitoring with Apple Intelligence integration
- Auto-recovery and self-healing capabilities

Usage:
    from ai_dev_team import AIDevTeam

    team = AIDevTeam()
    result = await team.collaborate("Build a REST API for user authentication")
    print(result.final_answer)

Control Center:
    from ai_dev_team.monitor import ControlCenter

    center = ControlCenter(team=team)
    await center.start()  # Starts monitoring, health checks, auto-recovery
"""

__version__ = "1.0.0"
__author__ = "Fred AI Team"

from .orchestrator import AIDevTeam, CollaborationResult
from .agents import (
    AIAgent,
    ClaudeAgent,
    ChatGPTAgent,
    GeminiAgent,
    GrokAgent,
    AgentConfig,
    ModelType,
)
from .memory import MemorySystem, MistakePrevention, LearningEngine
from .collaboration import CollaborationEngine, CollaborationMode
from .routing import TaskRouter, TaskType, TaskClassification
from .integrations import ChatterFixConnector, check_against_learnings, find_solution
from .parallel_coding import ParallelCodingEngine, CodeTask, CodeFix, ParallelCodingResult
from .shared_config import SharedConfig, AIProviderConfig, ProviderType, shared_config, get_shared_config

__all__ = [
    # Core
    "AIDevTeam",
    "CollaborationResult",
    # Agents
    "AIAgent",
    "ClaudeAgent",
    "ChatGPTAgent",
    "GeminiAgent",
    "GrokAgent",
    "AgentConfig",
    "ModelType",
    # Memory
    "MemorySystem",
    "MistakePrevention",
    "LearningEngine",
    # Collaboration
    "CollaborationEngine",
    "CollaborationMode",
    # Routing
    "TaskRouter",
    "TaskType",
    "TaskClassification",
    # Integrations
    "ChatterFixConnector",
    "check_against_learnings",
    "find_solution",
    # Parallel Coding
    "ParallelCodingEngine",
    "CodeTask",
    "CodeFix",
    "ParallelCodingResult",
    # Shared Config
    "SharedConfig",
    "AIProviderConfig",
    "ProviderType",
    "shared_config",
    "get_shared_config",
]
