"""
Custom Agent Personas — User-defined specialist agents
========================================================

Create custom AI agents with specialized system prompts, knowledge,
and behavior. Personas persist to disk and auto-register on startup.

Usage:
    pm = get_persona_manager()
    persona = pm.create_persona(
        name="django-expert",
        role="Senior Django Developer",
        system_prompt="You are a Django expert who...",
        model_backend="chatgpt",
    )
    agent = pm.create_agent(persona)
    team.register_agent(agent)
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .agents.base import AIAgent, AgentConfig, ModelType

logger = logging.getLogger(__name__)

PERSONAS_DIR = Path.home() / ".ai-dev-team" / "personas"
PERSONAS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Persona:
    """A custom agent persona definition."""
    name: str
    role: str
    system_prompt: str
    model_backend: str = "chatgpt"  # chatgpt, gemini, grok, grok-fast, ollama
    capabilities: List[str] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4000
    created: str = ""

    def __post_init__(self):
        if not self.created:
            from datetime import datetime, timezone
            self.created = datetime.now(timezone.utc).isoformat()


class PersonaManager:
    """Manages custom agent personas with persistence."""

    def __init__(self):
        self._cache: Dict[str, Persona] = {}
        self._load_all()

    def _load_all(self):
        """Load all personas from disk."""
        for path in PERSONAS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                persona = Persona(**data)
                self._cache[persona.name] = persona
            except Exception as e:
                logger.warning(f"Failed to load persona {path.name}: {e}")
        if self._cache:
            logger.info(f"Loaded {len(self._cache)} custom personas")

    def create_persona(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model_backend: str = "chatgpt",
        capabilities: List[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Persona:
        """Create and persist a new persona."""
        persona = Persona(
            name=name,
            role=role,
            system_prompt=system_prompt,
            model_backend=model_backend,
            capabilities=capabilities or [],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._cache[name] = persona
        self._save(persona)
        logger.info(f"Created persona: {name} ({role}) backed by {model_backend}")
        return persona

    def _save(self, persona: Persona):
        """Persist a persona to disk."""
        path = PERSONAS_DIR / f"{persona.name}.json"
        path.write_text(json.dumps(asdict(persona), indent=2))

    def get_persona(self, name: str) -> Optional[Persona]:
        """Get a persona by name."""
        return self._cache.get(name)

    def list_personas(self) -> List[Dict[str, Any]]:
        """List all personas."""
        return [
            {
                "name": p.name,
                "role": p.role,
                "model": p.model_backend,
                "capabilities": p.capabilities,
            }
            for p in self._cache.values()
        ]

    def delete_persona(self, name: str):
        """Delete a persona."""
        self._cache.pop(name, None)
        path = PERSONAS_DIR / f"{name}.json"
        if path.exists():
            path.unlink()

    def create_agent(self, persona: Persona) -> Optional[AIAgent]:
        """Create a real AIAgent from a persona definition."""
        model_type_map = {
            "chatgpt": ModelType.CHATGPT,
            "gemini": ModelType.GEMINI,
            "grok": ModelType.GROK,
            "grok-fast": ModelType.GROK,
            "ollama": ModelType.LOCAL,
        }
        model_type = model_type_map.get(persona.model_backend, ModelType.CHATGPT)

        config = AgentConfig(
            name=f"persona-{persona.name}",
            model_type=model_type,
            role=persona.role,
            capabilities=persona.capabilities or ["general"],
            system_prompt=persona.system_prompt,
            temperature=persona.temperature,
            max_tokens=persona.max_tokens,
        )

        try:
            if persona.model_backend == "chatgpt":
                from .agents.chatgpt import ChatGPTAgent
                return ChatGPTAgent(config=config)
            elif persona.model_backend == "gemini":
                from .agents.gemini import GeminiAgent
                return GeminiAgent(config=config)
            elif persona.model_backend in ("grok", "grok-fast"):
                from .agents.grok import GrokAgent
                fast = persona.model_backend == "grok-fast"
                return GrokAgent(config=config, fast_mode=fast)
            elif persona.model_backend == "ollama":
                from .agents.ollama import OllamaAgent
                return OllamaAgent(config=config)
            else:
                logger.warning(f"Unknown model backend: {persona.model_backend}")
                return None
        except Exception as e:
            logger.error(f"Failed to create agent for persona {persona.name}: {e}")
            return None

    def register_all(self, team) -> int:
        """Register all personas as agents on a team. Returns count registered."""
        count = 0
        for persona in self._cache.values():
            agent = self.create_agent(persona)
            if agent:
                team.register_agent(agent)
                count += 1
        if count:
            logger.info(f"Registered {count} custom persona agents")
        return count


# Singleton
_manager: Optional[PersonaManager] = None


def get_persona_manager() -> PersonaManager:
    """Get the global persona manager."""
    global _manager
    if _manager is None:
        _manager = PersonaManager()
    return _manager
