"""
ModelRouter — multi-provider LLM router with auto-fallback.

Supports cloud providers (Gemini, ChatGPT, Claude, Grok) and
local models (Ollama, MLX) with automatic fallback chain.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

_router = None

# Fallback order when no preference is set
DEFAULT_CHAIN = ["gemini", "ollama", "mlx", "openai", "anthropic", "grok", "llama_cloud"]

# Provider → agent factory
_AGENT_FACTORIES = {}


def _make_agent(provider: str):
    """Lazy-create agent instances. Returns (agent, model_name, provider_name) or None."""
    from ai_dev_team.agents.base import AgentConfig, ModelType

    try:
        if provider == "gemini":
            from ai_dev_team.agents.gemini import GeminiAgent
            model = os.getenv("FRED_CHAT_MODEL", "gemini-2.5-flash")
            agent = GeminiAgent(AgentConfig(
                name="fred", model_type=ModelType.GEMINI, role="AI Personal Assistant",
                capabilities=["tasks", "memory", "planning", "code", "chat"],
                model_name=model, temperature=0.7, max_tokens=4000,
            ))
            return agent, model, "gemini"

        elif provider == "openai":
            from ai_dev_team.agents.chatgpt import ChatGPTAgent
            model = os.getenv("FRED_OPENAI_MODEL", "gpt-4o-mini")
            agent = ChatGPTAgent(AgentConfig(
                name="fred-openai", model_type=ModelType.CHATGPT, role="AI Personal Assistant",
                capabilities=["tasks", "memory", "planning", "code", "chat"],
                model_name=model, temperature=0.7, max_tokens=4000,
            ))
            return agent, model, "openai"

        elif provider == "anthropic":
            from ai_dev_team.agents.claude import ClaudeAgent
            model = os.getenv("FRED_CLAUDE_MODEL", "claude-sonnet-4-20250514")
            agent = ClaudeAgent(AgentConfig(
                name="fred-claude", model_type=ModelType.CLAUDE, role="AI Personal Assistant",
                capabilities=["tasks", "memory", "planning", "code", "chat"],
                model_name=model, temperature=0.7, max_tokens=4000,
            ))
            return agent, model, "anthropic"

        elif provider == "grok":
            from ai_dev_team.agents.grok import GrokAgent
            model = os.getenv("FRED_GROK_MODEL", "grok-3-fast")
            agent = GrokAgent(AgentConfig(
                name="fred-grok", model_type=ModelType.GROK, role="AI Personal Assistant",
                capabilities=["tasks", "memory", "planning", "code", "chat"],
                model_name=model, temperature=0.7, max_tokens=4000,
            ))
            return agent, model, "grok"

        elif provider == "ollama":
            from ai_dev_team.agents.ollama import OllamaAgent
            model = os.getenv("FRED_OLLAMA_MODEL", "llama3.2:3b")
            agent = OllamaAgent(AgentConfig(
                name="fred-ollama", model_type=ModelType.LOCAL, role="AI Personal Assistant",
                capabilities=["tasks", "memory", "planning", "code", "chat"],
                model_name=model, temperature=0.7, max_tokens=4000,
            ))
            return agent, model, "ollama"

        elif provider == "mlx":
            from ai_dev_team.agents.mlx_agent import MLXAgent
            model = os.getenv("FRED_MLX_MODEL", "mlx-coder")
            agent = MLXAgent(AgentConfig(
                name="fred-mlx", model_type=ModelType.LOCAL, role="AI Personal Assistant",
                capabilities=["tasks", "memory", "planning", "code", "chat"],
                model_name=model, temperature=0.7, max_tokens=4000,
            ))
            return agent, model, "mlx"

        elif provider == "llama_cloud":
            from ai_dev_team.agents.llama_cloud import LlamaCloudAgent
            model = os.getenv("FRED_LLAMA_MODEL", "llama-3.3-70b-versatile")
            agent = LlamaCloudAgent(AgentConfig(
                name="fred-llama", model_type=ModelType.LOCAL, role="AI Personal Assistant",
                capabilities=["tasks", "memory", "planning", "code", "chat"],
                model_name=model, temperature=0.7, max_tokens=4000,
            ))
            return agent, model, "llama_cloud"

    except Exception as e:
        logger.debug("Cannot create %s agent: %s", provider, e)
    return None


async def _is_provider_available(provider: str) -> bool:
    """Check if a provider is reachable / has valid credentials."""
    try:
        if provider == "gemini":
            return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        elif provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
        elif provider == "anthropic":
            return bool(os.getenv("ANTHROPIC_API_KEY"))
        elif provider == "grok":
            return bool(os.getenv("XAI_API_KEY"))
        elif provider == "llama_cloud":
            return bool(os.getenv("GROQ_API_KEY") or os.getenv("TOGETHER_API_KEY"))
        elif provider == "ollama":
            import httpx
            resp = await httpx.AsyncClient().get("http://localhost:11434/api/tags", timeout=2)
            return resp.status_code == 200
        elif provider == "mlx":
            try:
                import mlx  # noqa: F401
                return True
            except ImportError:
                return False
    except Exception:
        pass
    return False


class ModelRouter:
    """Routes LLM calls to the best available provider with fallback."""

    def __init__(self):
        self._agents = {}  # provider -> (agent, model_name, provider_name)
        self._prefs = None

    def get_preferences(self) -> dict:
        """Load preferences from DB (cached per call)."""
        if self._prefs is not None:
            return self._prefs
        try:
            from products.fred_assistant.database import get_conn
            with get_conn() as conn:
                row = conn.execute(
                    "SELECT value FROM memories WHERE category='system' AND key='model_preferences'"
                ).fetchone()
                if row:
                    self._prefs = json.loads(row["value"])
                    return self._prefs
        except Exception:
            pass
        self._prefs = {"preferred_provider": None, "enabled_providers": list(DEFAULT_CHAIN)}
        return self._prefs

    def set_preferences(self, preferred: str = None, enabled: list = None):
        """Save preferences to DB."""
        import uuid
        prefs = self.get_preferences()
        if preferred is not None:
            prefs["preferred_provider"] = preferred
        if enabled is not None:
            prefs["enabled_providers"] = enabled
        self._prefs = prefs
        try:
            from products.fred_assistant.database import get_conn
            with get_conn() as conn:
                conn.execute(
                    """INSERT INTO memories (id, category, key, value, importance)
                       VALUES (?, 'system', 'model_preferences', ?, 10)
                       ON CONFLICT(category, key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')""",
                    (str(uuid.uuid4()), json.dumps(prefs)),
                )
        except Exception as e:
            logger.warning("Failed to save model preferences: %s", e)

    def _build_chain(self) -> list:
        """Build fallback chain from preferences."""
        prefs = self.get_preferences()
        enabled = prefs.get("enabled_providers") or DEFAULT_CHAIN
        preferred = prefs.get("preferred_provider")

        chain = []
        if preferred and preferred in enabled:
            chain.append(preferred)
        for p in DEFAULT_CHAIN:
            if p in enabled and p not in chain:
                chain.append(p)
        return chain

    def _get_agent(self, provider: str):
        """Get or create a cached agent for a provider."""
        if provider not in self._agents:
            result = _make_agent(provider)
            if result:
                self._agents[provider] = result
        return self._agents.get(provider)

    async def available_providers(self) -> list:
        """List all providers with availability status."""
        result = []
        for provider in DEFAULT_CHAIN:
            available = await _is_provider_available(provider)
            agent_info = self._get_agent(provider) if available else None
            result.append({
                "name": provider,
                "available": available,
                "model": agent_info[1] if agent_info else None,
            })
        return result

    async def route(
        self,
        prompt: str,
        system_prompt: str = "",
        feature: str = "chat",
        preferred_provider: str = None,
    ) -> str:
        """Route a request through the fallback chain. Returns response text."""
        chain = self._build_chain()
        if preferred_provider:
            chain = [preferred_provider] + [p for p in chain if p != preferred_provider]

        for provider in chain:
            agent_tuple = self._get_agent(provider)
            if not agent_tuple:
                continue

            agent, model_name, prov_name = agent_tuple
            try:
                resp = await agent.generate_response(prompt, system_override=system_prompt)

                # Record usage
                from products.fred_assistant.services.llm_shared import _record
                _record(model_name, prov_name, resp, feature)

                if resp.error:
                    logger.info("Provider %s returned error: %s, trying next", provider, resp.error)
                    continue

                return resp.content or ""
            except Exception as e:
                logger.info("Provider %s failed: %s, trying next", provider, e)
                continue

        logger.warning("All providers in chain failed")
        return ""


def get_router() -> ModelRouter:
    """Singleton ModelRouter."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
