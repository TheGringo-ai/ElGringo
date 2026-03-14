"""
Agent Setup Manager — Extracted from AIDevTeam orchestrator
=============================================================

Handles agent registration, cloud/local/MLX agent setup, and
Ollama availability detection.
"""

import asyncio
import concurrent.futures
import logging
import os
from typing import TYPE_CHECKING, Dict, List

from .agents import (
    AIAgent,
    ChatGPTAgent,
    ClaudeAgent,
    GeminiAgent,
    GrokAgent,
    OllamaAgent,
    create_llama_70b,
    create_llama_fast,
)
from .agents.ollama import create_local_agent, create_local_coder
from .core.personas import get_persona_manager

if TYPE_CHECKING:
    from .orchestrator import AIDevTeam

logger = logging.getLogger(__name__)


class AgentSetupManager:
    """
    Manages agent discovery, creation, and registration.

    Extracted from AIDevTeam to reduce orchestrator complexity.
    Takes a reference to the orchestrator for access to the agent registry.
    """

    def __init__(self, orchestrator: "AIDevTeam"):
        self._orchestrator = orchestrator

    @property
    def agents(self) -> Dict[str, AIAgent]:
        return self._orchestrator.agents

    def register_agent(self, agent: AIAgent):
        self._orchestrator.register_agent(agent)

    def setup_agents(self):
        """Setup default AI team based on available API keys."""
        if self._orchestrator.local_only:
            logger.info("Local-only mode: using Ollama models only (no cloud APIs)")
            self._setup_local_agents()
            if not self.agents:
                logger.warning(
                    "No local Ollama models available. "
                    "Install Ollama and run: ollama pull llama3.2:3b"
                )
            return

        # Cloud agents (requires API keys)
        if os.getenv("OPENAI_API_KEY"):
            self.register_agent(ChatGPTAgent())
            logger.info("Registered ChatGPT agent (Lead Developer & Architect)")

        if os.getenv("ANTHROPIC_API_KEY"):
            self.register_agent(ClaudeAgent())
            logger.info("Registered Claude agent (Analyst)")

        if os.getenv("GEMINI_API_KEY"):
            self.register_agent(GeminiAgent())
            logger.info("Registered Gemini agent (Full-Stack Coder)")

        if os.getenv("XAI_API_KEY"):
            self.register_agent(GrokAgent(fast_mode=False))
            self.register_agent(GrokAgent(fast_mode=True))
            logger.info("Registered Grok agents (Reasoner + Coder)")

        self._setup_llama_cloud_agents()
        self._setup_local_agents()

        # Custom personas
        try:
            pm = get_persona_manager()
            pm.register_all(self._orchestrator)
        except Exception as e:
            logger.debug(f"Persona registration skipped: {e}")

        if not self.agents:
            logger.warning(
                "No AI agents configured. Set API keys: "
                "ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, XAI_API_KEY "
                "or use local_only=True with Ollama"
            )

    def _setup_llama_cloud_agents(self):
        """Setup Llama Cloud agents via Groq, Together, or Fireworks."""
        llama_registered = False

        if os.getenv("GROQ_API_KEY"):
            self.register_agent(create_llama_70b(provider="groq"))
            logger.info("Registered Llama 3.3 70B agent (via Groq - ultra-fast)")
            llama_registered = True

        if os.getenv("TOGETHER_API_KEY"):
            if not llama_registered:
                self.register_agent(create_llama_70b(provider="together"))
                logger.info("Registered Llama 3.3 70B agent (via Together AI)")
            self.register_agent(create_llama_fast(provider="together"))
            logger.info("Registered Llama 3.1 8B agent (via Together AI - fast)")

        if os.getenv("FIREWORKS_API_KEY") and not llama_registered:
            self.register_agent(create_llama_70b(provider="fireworks"))
            logger.info("Registered Llama 3.3 70B agent (via Fireworks)")

    def _setup_local_agents(self):
        """Setup local Ollama + MLX agents if available."""
        models = self._detect_ollama_models()

        if models:
            if any("llama3" in m.lower() for m in models):
                self.register_agent(create_local_agent("llama3"))
                logger.info("Registered local agent: Llama 3.2 (General)")

            if any("qwen-coder-custom" in m.lower() for m in models):
                self.register_agent(create_local_coder())
                logger.info("Registered local agent: Qwen Coder Custom (Fine-tuned)")
            elif any("qwen" in m.lower() and "coder" in m.lower() for m in models):
                self.register_agent(create_local_agent("qwen-coder-7b"))
                logger.info("Registered local agent: Qwen Coder (Code Specialist)")

            if any("llama-coder-custom" in m.lower() for m in models):
                self.register_agent(create_local_agent("llama-coder-custom"))
                logger.info("Registered local agent: Llama Coder Custom (Fine-tuned)")

        # Qwen agents via MLX (faster than Ollama on Apple Silicon)
        try:
            from .agents.mlx_agent import create_qwen_coder, create_qwen_general

            qwen_coder = create_qwen_coder()
            if qwen_coder:
                self.register_agent(qwen_coder)
                logger.info("Registered Qwen agent: Qwen 2.5 Coder 7B (native Metal)")

            qwen_general = create_qwen_general()
            if qwen_general:
                self.register_agent(qwen_general)
                logger.info("Registered Qwen agent: Qwen 2.5 3B (native Metal)")
        except Exception as e:
            logger.debug(f"Qwen/MLX agents not available: {e}")

    @staticmethod
    def _detect_ollama_models() -> List[str]:
        """Detect available Ollama models (handles event loop complexity)."""
        async def check_ollama():
            try:
                agent = OllamaAgent()
                if await agent.is_available():
                    return await agent.list_models()
            except Exception:
                pass
            return []

        def run_in_new_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(check_ollama())
            finally:
                loop.close()

        try:
            try:
                asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    return future.result(timeout=5)
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    return loop.run_until_complete(check_ollama())
                except RuntimeError:
                    return asyncio.run(check_ollama())
        except Exception as e:
            logger.debug(f"Could not check Ollama availability: {e}")
            return []
