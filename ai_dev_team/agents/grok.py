"""
Grok Agent - xAI Grok Integration
"""

import logging
import os
import time
from typing import AsyncIterator, Optional

import aiohttp

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)


class GrokAgent(AIAgent):
    """Grok AI Agent using xAI API"""

    DEFAULT_MODEL = "grok-3"
    CODER_MODEL = "grok-3-fast"
    API_KEY_ENV = "XAI_API_KEY"
    API_URL = "https://api.x.ai/v1/chat/completions"

    def __init__(self, config: Optional[AgentConfig] = None, fast_mode: bool = False):
        if config is None:
            if fast_mode:
                config = AgentConfig(
                    name="grok-coder",
                    model_type=ModelType.GROK,
                    role="Speed Coder",
                    capabilities=["fast-coding", "optimization", "debugging", "refactoring"],
                    model_name=self.CODER_MODEL,
                    temperature=0.5,
                )
            else:
                config = AgentConfig(
                    name="grok-reasoner",
                    model_type=ModelType.GROK,
                    role="Strategic Thinker",
                    capabilities=["reasoning", "analysis", "strategy", "problem-solving"],
                    model_name=self.DEFAULT_MODEL,
                )
        super().__init__(config)

    async def is_available(self) -> bool:
        """Check if Grok is available"""
        return bool(os.getenv(self.API_KEY_ENV))

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AgentResponse:
        """Generate response using Grok"""
        start_time = time.time()

        api_key = os.getenv(self.API_KEY_ENV)
        if not api_key:
            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=0.0,
                error=f"{self.API_KEY_ENV} not configured"
            )

        try:
            # Build system prompt
            if "coder" in self.name.lower():
                default = (
                    "You are a highly efficient coding specialist. "
                    "Focus on clean, optimized, production-ready code solutions. "
                    "Be concise and practical."
                )
            else:
                default = (
                    f"You are {self.name}, a {self.role}. "
                    "Provide thoughtful strategic analysis and insights."
                )
            system_prompt = self.get_system_prompt(system_override, default_prompt=default)

            # Build user content
            user_content = prompt
            if context:
                user_content = f"Context:\n{context}\n\nTask:\n{prompt}"

            # Build request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "model": self.config.model_name or self.DEFAULT_MODEL,
                "temperature": self.config.temperature,
                "max_tokens": min(self.config.max_tokens, 4000)
            }

            # Make API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        response_time = time.time() - start_time

                        # Update stats
                        self.update_stats(response_time, True)
                        self.add_to_history("user", prompt)
                        self.add_to_history("assistant", content)

                        usage = result.get("usage", {})
                        return AgentResponse(
                            agent_name=self.name,
                            model_type=self.config.model_type,
                            content=content,
                            confidence=0.87,
                            response_time=response_time,
                            input_tokens=usage.get("prompt_tokens", 0) or 0,
                            output_tokens=usage.get("completion_tokens", 0) or 0,
                            metadata={
                                "model": self.config.model_name,
                                "usage": usage
                            }
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(f"API Error {response.status}: {error_text}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"Grok error: {e}")

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
        system_override: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream response tokens as they arrive"""
        api_key = os.getenv(self.API_KEY_ENV)
        if not api_key:
            logger.error(f"{self.API_KEY_ENV} not configured")
            return

        try:
            # Build system prompt
            if "coder" in self.name.lower():
                default = (
                    "You are a highly efficient coding specialist. "
                    "Focus on clean, optimized, production-ready code solutions. "
                    "Be concise and practical."
                )
            else:
                default = (
                    f"You are {self.name}, a {self.role}. "
                    "Provide thoughtful strategic analysis and insights."
                )
            system_prompt = self.get_system_prompt(system_override, default_prompt=default)

            # Build user content
            user_content = prompt
            if context:
                user_content = f"Context:\n{context}\n\nTask:\n{prompt}"

            # Build request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "model": self.config.model_name or self.DEFAULT_MODEL,
                "temperature": self.config.temperature,
                "max_tokens": min(self.config.max_tokens, 4000),
                "stream": True
            }

            # Make streaming API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Grok streaming API Error {response.status}: {error_text}")
                        return

                    # Process SSE stream
                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data_str)
                                if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                                    yield chunk["choices"][0]["delta"]["content"]
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Grok streaming error: {e}")
