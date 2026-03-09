"""
Base AI Agent - Abstract foundation for all AI model integrations
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Platform identity — prepended to every agent's system prompt so each agent
# knows it is part of El Gringo and can speak about the platform as a team.
# ---------------------------------------------------------------------------
PLATFORM_IDENTITY = """\
You are part of **El Gringo**, a multi-agent AI orchestration platform that \
coordinates multiple AI models to deliver superior results no single model \
can achieve alone.

**What makes El Gringo different:**
- 8 collaboration modes: parallel, consensus, debate, sequential, \
benchmark, specialized routing, weighted synthesis, and red-team review.
- Mistake-prevention system: a shared memory layer records every past \
error and solution so the team never repeats a mistake.
- Intelligent benchmark routing: tasks are automatically routed to the \
best-suited model based on task type, complexity, and historical \
performance data.
- Intelligence reports: every multi-agent run produces a transparency \
report showing how each model contributed and how the final answer was \
synthesized.

**The El Gringo team consists of:**
ChatGPT (Lead Developer), Claude (Analyst & Researcher), \
Gemini (Creative Director), Grok (Strategic Thinker + Speed Coder), \
Ollama local models (offline/private), and Llama Cloud models \
(Groq/Together/Fireworks for high-capacity open-source inference).

When describing the platform, speak as "we" or "the El Gringo team." \
You are one specialist on this team — contribute your unique strengths \
while acknowledging the collaborative nature of the platform."""


class ModelType(Enum):
    """Supported AI model types"""
    CLAUDE = "claude"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    GROK = "grok"
    LOCAL = "local"


@dataclass
class AgentConfig:
    """Configuration for an AI agent"""
    name: str
    model_type: ModelType
    role: str
    capabilities: List[str]
    model_name: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7
    enabled: bool = True
    system_prompt: Optional[str] = None
    cost_tier: str = "standard"  # "budget", "standard", "premium"

    # Performance tracking
    total_requests: int = 0
    successful_requests: int = 0
    total_response_time: float = 0.0


@dataclass
class AgentResponse:
    """Response from an AI agent"""
    agent_name: str
    model_type: ModelType
    content: str
    confidence: float
    response_time: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.content)


class AIAgent(ABC):
    """Abstract base class for all AI agents"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
        self._last_response_time: float = 0.0

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def role(self) -> str:
        return self.config.role

    def get_system_prompt(
        self,
        system_override: Optional[str] = None,
        default_prompt: Optional[str] = None,
    ) -> str:
        """Build system prompt with platform identity prepended.

        Resolution order:
        1. ``system_override`` (caller-supplied per-request override)
        2. ``self.config.system_prompt`` (set at agent construction)
        3. ``default_prompt`` (agent-specific flavour text)
        4. Generic fallback built from name / role / capabilities
        """
        agent_prompt = system_override or self.config.system_prompt or default_prompt or (
            f"You are {self.name}, a {self.role}. "
            f"Your capabilities include: {', '.join(self.config.capabilities)}."
        )
        return f"{PLATFORM_IDENTITY}\n\n{agent_prompt}"

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AgentResponse:
        """Generate a response from this AI agent"""
        pass

    async def generate_stream(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream response tokens as they arrive.

        Override this method to enable streaming for the agent.
        Default implementation falls back to non-streaming.
        """
        # Default: yield entire response at once (fallback for non-streaming agents)
        response = await self.generate_response(prompt, context, system_override)
        if response.success:
            yield response.content

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this agent is available (API key configured, etc.)"""
        pass

    async def generate_with_retry(
        self,
        prompt: str,
        context: str = "",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> AgentResponse:
        """Generate response with automatic retry on failure"""
        last_error = None

        for attempt in range(max_retries):
            try:
                response = await self.generate_response(prompt, context)
                if response.success:
                    return response
                last_error = response.error
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1} failed for {self.name}: {e}")

            if attempt < max_retries - 1:
                await self._async_sleep(retry_delay * (attempt + 1))

        return AgentResponse(
            agent_name=self.name,
            model_type=self.config.model_type,
            content="",
            confidence=0.0,
            response_time=0.0,
            error=f"All {max_retries} attempts failed. Last error: {last_error}"
        )

    async def _async_sleep(self, seconds: float):
        """Async sleep helper"""
        import asyncio
        await asyncio.sleep(seconds)

    def update_stats(self, response_time: float, success: bool):
        """Update agent performance statistics"""
        self.config.total_requests += 1
        self.config.total_response_time += response_time
        if success:
            self.config.successful_requests += 1
        self._last_response_time = response_time

    def get_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics"""
        total = self.config.total_requests
        return {
            "name": self.name,
            "model_type": self.config.model_type.value,
            "role": self.role,
            "total_requests": total,
            "successful_requests": self.config.successful_requests,
            "success_rate": self.config.successful_requests / max(total, 1),
            "avg_response_time": self.config.total_response_time / max(total, 1),
            "last_response_time": self._last_response_time,
            "enabled": self.config.enabled,
        }

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []

    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, model={self.config.model_type.value})>"
