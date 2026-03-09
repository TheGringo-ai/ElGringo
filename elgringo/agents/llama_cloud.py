"""
Llama Cloud Agent - API-based Llama Models
==========================================

Integrates Llama models via cloud APIs for:
- Higher capacity than local Ollama
- Function calling support
- No local GPU requirements

Supports:
- Groq (fastest inference)
- Together AI (best models)
- Fireworks AI (function calling)
"""

import logging
import os
import time
from typing import Any, AsyncIterator, Dict, List, Optional

import aiohttp

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)


# Provider configurations
LLAMA_PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "models": {
            "llama-3.3-70b": "llama-3.3-70b-versatile",
            "llama-3.2-90b-vision": "llama-3.2-90b-vision-preview",
            "llama-3.1-70b": "llama-3.1-70b-versatile",
            "llama-3.1-8b": "llama-3.1-8b-instant",
            "mixtral": "mixtral-8x7b-32768",
        },
        "speed": "ultra-fast",
        "strengths": ["speed", "coding", "reasoning"],
    },
    "together": {
        "url": "https://api.together.xyz/v1/chat/completions",
        "key_env": "TOGETHER_API_KEY",
        "models": {
            "llama-3.3-70b": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "llama-3.2-90b-vision": "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo",
            "llama-3.2-11b-vision": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
            "llama-3.2-3b": "meta-llama/Llama-3.2-3B-Instruct-Turbo",
            "llama-3.1-405b": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            "llama-3.1-70b": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "llama-3.1-8b": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "qwen-coder-32b": "Qwen/Qwen2.5-Coder-32B-Instruct",
            "deepseek-coder": "deepseek-ai/DeepSeek-V3",
        },
        "speed": "fast",
        "strengths": ["model_variety", "vision", "large_context"],
    },
    "fireworks": {
        "url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "key_env": "FIREWORKS_API_KEY",
        "models": {
            "llama-3.3-70b": "accounts/fireworks/models/llama-v3p3-70b-instruct",
            "llama-3.1-405b": "accounts/fireworks/models/llama-v3p1-405b-instruct",
            "llama-3.1-70b": "accounts/fireworks/models/llama-v3p1-70b-instruct",
            "qwen-coder": "accounts/fireworks/models/qwen2p5-coder-32b-instruct",
        },
        "speed": "fast",
        "strengths": ["function_calling", "structured_output", "reliability"],
    },
}


class LlamaCloudAgent(AIAgent):
    """
    Llama via cloud APIs (Groq, Together, Fireworks).

    Benefits over local Ollama:
    - Llama 3.3 70B, 3.1 405B (too large for most local machines)
    - Function calling and structured output
    - No local resource usage
    - Ultra-fast inference (especially Groq)

    Usage:
        agent = LlamaCloudAgent(provider="groq", model="llama-3.3-70b")
        response = await agent.generate_response("Write a Python function...")
    """

    def __init__(
        self,
        provider: str = "groq",
        model: str = "llama-3.3-70b",
        config: Optional[AgentConfig] = None,
    ):
        self.provider = provider
        self.model_key = model

        if provider not in LLAMA_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Choose from: {list(LLAMA_PROVIDERS.keys())}")

        provider_config = LLAMA_PROVIDERS[provider]
        self.api_url = provider_config["url"]
        self.api_key = os.getenv(provider_config["key_env"])

        # Get model name or use as-is if not in our list
        self.model_name = provider_config["models"].get(model, model)

        if config is None:
            config = AgentConfig(
                name=f"llama-{model.replace('.', '-')}-{provider}",
                model_type=ModelType.LOCAL,  # Categorized with local for cost tier
                role=f"Llama Expert ({model} via {provider})",
                capabilities=["coding", "analysis", "reasoning", "fast-response"],
                model_name=self.model_name,
                temperature=0.7,
                max_tokens=4096,
                cost_tier="budget",  # Llama is very cost-effective
            )
        super().__init__(config)

        logger.info(f"Initialized LlamaCloudAgent: {self.name} ({self.model_name} via {provider})")

    async def is_available(self) -> bool:
        """Check if API key is configured"""
        if not self.api_key:
            return False

        # Quick health check
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url.replace('/chat/completions', '/models')}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status in [200, 401]  # 401 means key works but may need permissions
        except Exception:
            return bool(self.api_key)  # Fall back to just checking key exists

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None,
        task_type: str = "general",
        domains: Optional[List[str]] = None,
        **kwargs
    ) -> AgentResponse:
        """
        Generate response using Llama via cloud API.

        Args:
            prompt: The user prompt
            context: Additional context
            system_override: Override system prompt
            task_type: Type of task for context
            domains: Relevant domains
        """
        start_time = time.time()

        if not self.api_key:
            key_env = LLAMA_PROVIDERS[self.provider]["key_env"]
            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=0.0,
                error=f"Missing API key: {key_env}. Set it in your environment."
            )

        try:
            # Build system prompt
            system_prompt = self.get_system_prompt(
                system_override,
                default_prompt=self._build_system_prompt(task_type, domains),
            )

            # Build messages
            messages = [{"role": "system", "content": system_prompt}]

            if context:
                messages.append({
                    "role": "user",
                    "content": f"Context:\n{context}"
                })

            messages.append({"role": "user", "content": prompt})

            # Request headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Request body
            data = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }

            # Make API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        result = await response.json()

                        content = result["choices"][0]["message"]["content"]
                        usage = result.get("usage", {})

                        # Update internal stats
                        self.update_stats(response_time, True)
                        self.add_to_history("user", prompt)
                        self.add_to_history("assistant", content)

                        # Calculate confidence based on model and provider
                        confidence = self._calculate_confidence()

                        return AgentResponse(
                            agent_name=self.name,
                            model_type=self.config.model_type,
                            content=content,
                            confidence=confidence,
                            response_time=response_time,
                            input_tokens=usage.get("prompt_tokens", 0) or 0,
                            output_tokens=usage.get("completion_tokens", 0) or 0,
                            metadata={
                                "model": self.model_name,
                                "provider": self.provider,
                                "prompt_tokens": usage.get("prompt_tokens"),
                                "completion_tokens": usage.get("completion_tokens"),
                                "total_tokens": usage.get("total_tokens"),
                                "finish_reason": result["choices"][0].get("finish_reason"),
                            }
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(f"API Error {response.status}: {error_text[:500]}")

        except aiohttp.ClientError as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"Llama Cloud connection error: {e}")

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=response_time,
                error=f"Connection error: {e}"
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"Llama Cloud error: {e}")

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=response_time,
                error=str(e)
            )

    async def generate_stream(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens as they arrive"""
        if not self.api_key:
            return

        try:
            system_prompt = self.get_system_prompt(
                system_override,
                default_prompt=f"You are {self.name}, a helpful Llama AI assistant.",
            )

            messages = [{"role": "system", "content": system_prompt}]
            if context:
                messages.append({"role": "user", "content": f"Context:\n{context}"})
            messages.append({"role": "user", "content": prompt})

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": True,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    async for line in response.content:
                        if line:
                            line_str = line.decode("utf-8").strip()
                            if line_str.startswith("data: "):
                                json_str = line_str[6:]
                                if json_str != "[DONE]":
                                    try:
                                        import json
                                        data = json.loads(json_str)
                                        delta = data["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            yield delta["content"]
                                    except Exception:
                                        continue

        except Exception as e:
            logger.error(f"Llama streaming error: {e}")

    def _build_system_prompt(
        self,
        task_type: str = "general",
        domains: Optional[List[str]] = None,
    ) -> str:
        """Build contextual system prompt"""
        base = f"You are {self.name}, a powerful Llama AI assistant"

        task_contexts = {
            "coding": " specialized in writing clean, efficient code",
            "debugging": " specialized in debugging and finding root causes",
            "analysis": " specialized in thorough analysis and reasoning",
            "architecture": " specialized in software architecture and design",
            "creative": " with strong creative problem-solving abilities",
            "security": " with deep expertise in security best practices",
        }

        context = task_contexts.get(task_type, "")
        prompt = f"{base}{context}."

        if domains:
            prompt += f" You have expertise in: {', '.join(domains)}."

        prompt += " Provide helpful, accurate, and well-reasoned responses."

        return prompt

    def _calculate_confidence(self) -> float:
        """Calculate confidence based on model size and provider"""
        # Base confidence by model size
        model_confidence = {
            "405b": 0.95,
            "70b": 0.90,
            "90b": 0.92,
            "32b": 0.85,
            "8b": 0.75,
            "3b": 0.70,
            "11b": 0.78,
        }

        confidence = 0.80  # Default
        model_lower = self.model_key.lower()

        for size, conf in model_confidence.items():
            if size in model_lower:
                confidence = conf
                break

        # Slight boost for reliable providers
        if self.provider == "groq":
            confidence = min(confidence + 0.02, 0.98)

        return confidence

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about current provider"""
        provider_config = LLAMA_PROVIDERS[self.provider]
        return {
            "provider": self.provider,
            "model": self.model_name,
            "model_key": self.model_key,
            "speed": provider_config["speed"],
            "strengths": provider_config["strengths"],
            "available_models": list(provider_config["models"].keys()),
            "has_api_key": bool(self.api_key),
        }


# =============================================================================
# Factory Functions
# =============================================================================

def create_llama_70b(provider: str = "groq") -> LlamaCloudAgent:
    """
    Create Llama 3.3 70B agent (most capable open model).

    Args:
        provider: API provider (groq, together, fireworks)

    Returns:
        LlamaCloudAgent configured for 70B model
    """
    return LlamaCloudAgent(provider=provider, model="llama-3.3-70b")


def create_llama_405b() -> LlamaCloudAgent:
    """
    Create Llama 3.1 405B agent (largest open model).

    Only available via Together AI due to size.

    Returns:
        LlamaCloudAgent configured for 405B model
    """
    return LlamaCloudAgent(provider="together", model="llama-3.1-405b")


def create_llama_fast(provider: str = "groq") -> LlamaCloudAgent:
    """
    Create fast Llama 3.1 8B agent for quick tasks.

    Args:
        provider: API provider

    Returns:
        LlamaCloudAgent configured for fast 8B model
    """
    return LlamaCloudAgent(provider=provider, model="llama-3.1-8b")


def create_llama_vision(provider: str = "together") -> LlamaCloudAgent:
    """
    Create Llama 3.2 Vision agent for image analysis.

    Args:
        provider: API provider (together recommended)

    Returns:
        LlamaCloudAgent configured for vision model
    """
    return LlamaCloudAgent(provider=provider, model="llama-3.2-90b-vision")


def create_qwen_coder(provider: str = "together") -> LlamaCloudAgent:
    """
    Create Qwen 2.5 Coder 32B agent for coding tasks.

    Args:
        provider: API provider

    Returns:
        LlamaCloudAgent configured for Qwen Coder
    """
    return LlamaCloudAgent(provider=provider, model="qwen-coder-32b")


def create_deepseek_coder() -> LlamaCloudAgent:
    """
    Create DeepSeek V3 agent for advanced coding.

    Only available via Together AI.

    Returns:
        LlamaCloudAgent configured for DeepSeek
    """
    return LlamaCloudAgent(provider="together", model="deepseek-coder")


def get_available_providers() -> Dict[str, Dict[str, Any]]:
    """
    Get information about all available providers.

    Returns:
        Dict of provider configurations
    """
    return {
        name: {
            "models": list(config["models"].keys()),
            "speed": config["speed"],
            "strengths": config["strengths"],
            "key_env": config["key_env"],
            "has_key": bool(os.getenv(config["key_env"])),
        }
        for name, config in LLAMA_PROVIDERS.items()
    }


def get_best_available_agent() -> Optional[LlamaCloudAgent]:
    """
    Get the best available Llama agent based on configured API keys.

    Priority: Groq (fastest) -> Together (most models) -> Fireworks

    Returns:
        Best available LlamaCloudAgent or None
    """
    # Check providers in order of preference
    for provider in ["groq", "together", "fireworks"]:
        key_env = LLAMA_PROVIDERS[provider]["key_env"]
        if os.getenv(key_env):
            return create_llama_70b(provider=provider)

    return None
