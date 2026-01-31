"""
Ollama Agent - Local LLM Integration
=====================================

Provides local AI capabilities using Ollama for offline/private use.
Supports multiple models: Llama 3, Qwen Coder, Mistral, etc.

Benefits:
- Free (no API costs)
- Private (data stays local)
- Offline capable
- Fast for simple tasks
"""

import json
import logging
import os
import time
from typing import AsyncIterator, Dict, List, Optional

import aiohttp

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)

# Import knowledge base (lazy to avoid circular imports)
_knowledge_base = None

def _get_knowledge_base():
    """Lazy load knowledge base"""
    global _knowledge_base
    if _knowledge_base is None:
        try:
            from ..ollama_knowledge import get_ollama_knowledge_base
            _knowledge_base = get_ollama_knowledge_base()
        except ImportError:
            _knowledge_base = None
    return _knowledge_base


# Available local models with characteristics
# Simplified to 3 models: general purpose, base coder, fine-tuned coder
LOCAL_MODELS = {
    "llama3.2-3b": {
        "name": "llama3.2:3b",
        "display": "Llama 3.2 (3B)",
        "capabilities": ["general", "reasoning", "writing", "balanced"],
        "speed": "fast",
        "cost_tier": "budget"
    },
    "qwen-coder-7b": {
        "name": "qwen2.5-coder:7b",
        "display": "Qwen Coder (7B)",
        "capabilities": ["coding", "debugging", "code-review", "architecture"],
        "speed": "medium",
        "cost_tier": "budget"
    },
    "qwen-coder-custom": {
        "name": "qwen-coder-custom:latest",
        "display": "Qwen Coder Fine-tuned (7B)",
        "capabilities": ["coding", "debugging", "code-review", "architecture", "python", "ai-team"],
        "speed": "medium",
        "cost_tier": "budget",
        "fine_tuned": True
    },
}


class OllamaAgent(AIAgent):
    """
    Ollama AI Agent for local LLM inference.

    Runs entirely on your machine - free, private, and offline capable.
    """

    DEFAULT_MODEL = "llama3.2:3b"
    CODER_MODEL = "qwen-coder-custom:latest"  # Fine-tuned on Python code
    API_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def __init__(self, config: Optional[AgentConfig] = None, coder_mode: bool = False):
        if config is None:
            if coder_mode:
                config = AgentConfig(
                    name="ollama-coder",
                    model_type=ModelType.LOCAL,
                    role="Local Code Specialist",
                    capabilities=["coding", "debugging", "refactoring", "offline"],
                    model_name=self.CODER_MODEL,
                    temperature=0.3,
                )
            else:
                config = AgentConfig(
                    name="ollama-local",
                    model_type=ModelType.LOCAL,
                    role="Local AI Assistant",
                    capabilities=["general", "analysis", "offline", "privacy"],
                    model_name=self.DEFAULT_MODEL,
                    temperature=0.7,
                )
        super().__init__(config)

    async def is_available(self) -> bool:
        """Check if Ollama is running locally"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_URL}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    async def list_models(self) -> list:
        """List available Ollama models"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_URL}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return [m["name"] for m in result.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
        return []

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None,
        task_type: str = "general",
        domains: Optional[List[str]] = None,
        use_knowledge: bool = True
    ) -> AgentResponse:
        """
        Generate response using local Ollama model with knowledge enhancement.

        Args:
            prompt: The user prompt
            context: Additional context
            system_override: Override system prompt
            task_type: Type of task (coding, debugging, etc.)
            domains: Specific knowledge domains to include
            use_knowledge: Whether to use knowledge enhancement
        """
        start_time = time.time()

        try:
            # Check availability
            if not await self.is_available():
                return AgentResponse(
                    agent_name=self.name,
                    model_type=self.config.model_type,
                    content="",
                    confidence=0.0,
                    response_time=0.0,
                    error="Ollama not running. Start with: ollama serve"
                )

            # Build system prompt with knowledge enhancement
            system_prompt = system_override or self.config.system_prompt

            if not system_prompt and use_knowledge:
                kb = _get_knowledge_base()
                if kb:
                    # Auto-detect domains from prompt if not specified
                    if not domains:
                        domains = self._detect_domains(prompt)

                    # Detect task type if general
                    if task_type == "general":
                        task_type = self._detect_task_type(prompt)

                    system_prompt = kb.get_system_prompt(
                        task_type=task_type,
                        domains=domains,
                        include_tools=True,
                        project_context=context if context and len(context) < 500 else None
                    )

            if not system_prompt:
                if "coder" in self.name.lower():
                    system_prompt = (
                        "You are a skilled coding assistant running locally. "
                        "Provide clean, efficient code solutions. Be concise."
                    )
                else:
                    system_prompt = (
                        f"You are {self.name}, a {self.role}. "
                        "Provide helpful and accurate responses."
                    )

            # Build full prompt
            full_prompt = prompt
            if context:
                full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {full_prompt}"

            # Build request
            data = {
                "model": self.config.model_name or self.DEFAULT_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                }
            }

            # Make API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.API_URL}/api/generate",
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("response", "")
                        response_time = time.time() - start_time

                        # Update stats
                        self.update_stats(response_time, True)
                        self.add_to_history("user", prompt)
                        self.add_to_history("assistant", content)

                        return AgentResponse(
                            agent_name=self.name,
                            model_type=self.config.model_type,
                            content=content,
                            confidence=0.75,  # Local models get slightly lower confidence
                            response_time=response_time,
                            metadata={
                                "model": self.config.model_name,
                                "eval_count": result.get("eval_count"),
                                "eval_duration": result.get("eval_duration"),
                                "local": True,
                            }
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama Error {response.status}: {error_text}")

        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"Ollama connection error: {e}")

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=response_time,
                error=f"Connection error: {e}. Is Ollama running?"
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"Ollama error: {e}")

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=response_time,
                error=str(e)
            )

    def _detect_domains(self, prompt: str) -> List[str]:
        """Auto-detect relevant knowledge domains from prompt"""
        prompt_lower = prompt.lower()
        domains = []

        domain_keywords = {
            "python": ["python", "pip", "pytest", "django", "flask", "fastapi", "pydantic"],
            "javascript": ["javascript", "js", "node", "npm", "yarn"],
            "typescript": ["typescript", "ts", "tsx"],
            "react": ["react", "jsx", "component", "hook", "useState", "useEffect"],
            "fastapi": ["fastapi", "uvicorn", "pydantic", "api endpoint"],
            "firebase": ["firebase", "firestore", "auth", "cloud functions"],
            "docker": ["docker", "container", "dockerfile", "compose"],
            "git": ["git", "commit", "branch", "merge", "pull request"],
            "testing": ["test", "pytest", "unittest", "mock", "coverage"],
            "security": ["security", "authentication", "authorization", "jwt", "oauth"],
            "database": ["database", "sql", "postgres", "sqlite", "query"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                domains.append(domain)

        return domains[:3]  # Limit to 3 most relevant

    def _detect_task_type(self, prompt: str) -> str:
        """Auto-detect task type from prompt"""
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["debug", "error", "fix", "bug", "crash", "fails"]):
            return "debugging"
        elif any(word in prompt_lower for word in ["security", "vulnerability", "auth", "permission"]):
            return "security"
        elif any(word in prompt_lower for word in ["architecture", "design", "structure", "pattern"]):
            return "architecture"
        elif any(word in prompt_lower for word in ["write", "code", "implement", "create", "build", "function"]):
            return "coding"
        else:
            return "general"

    async def pull_model(self, model_name: str) -> bool:
        """Pull/download an Ollama model"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.API_URL}/api/pull",
                    json={"name": model_name},
                    timeout=aiohttp.ClientTimeout(total=600)  # 10 min for large models
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    async def generate_stream(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream response tokens as they arrive"""
        if not await self.is_available():
            return

        try:
            system_prompt = system_override or self.config.system_prompt or (
                f"You are {self.name}, a helpful local AI assistant."
            )

            full_prompt = prompt
            if context:
                full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {full_prompt}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.API_URL}/api/generate",
                    json={
                        "model": self.config.model_name or self.DEFAULT_MODEL,
                        "prompt": full_prompt,
                        "stream": True,
                    },
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")


def create_local_agent(model_key: str = "llama3") -> OllamaAgent:
    """
    Create a local Ollama agent with a specific model.

    Args:
        model_key: Key from LOCAL_MODELS (e.g., "llama3", "qwen-coder-7b")
    """
    if model_key in LOCAL_MODELS:
        model_info = LOCAL_MODELS[model_key]
        config = AgentConfig(
            name=f"local-{model_key}",
            model_type=ModelType.LOCAL,
            role=f"Local AI ({model_info['display']})",
            capabilities=model_info["capabilities"],
            model_name=model_info["name"],
            cost_tier=model_info["cost_tier"],
        )
        return OllamaAgent(config=config)
    else:
        # Fallback to raw model name
        config = AgentConfig(
            name=f"local-{model_key}",
            model_type=ModelType.LOCAL,
            role="Local AI Assistant",
            capabilities=["general"],
            model_name=model_key,
            cost_tier="budget",
        )
        return OllamaAgent(config=config)


def create_local_coder() -> OllamaAgent:
    """Create a local coding specialist (Fine-tuned Qwen Coder)"""
    return create_local_agent("qwen-coder-custom")


def create_fast_local() -> OllamaAgent:
    """Create a fast local agent for general tasks (Llama 3.2 3B)"""
    return create_local_agent("llama3.2-3b")


async def get_available_local_models() -> List[str]:
    """Get list of available local models"""
    agent = OllamaAgent()
    models = await agent.list_models()
    return models
