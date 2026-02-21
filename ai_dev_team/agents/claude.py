"""
Claude Agent - Anthropic Claude AI Integration
"""

import logging
import os
import time
from typing import AsyncIterator, Optional

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)


class ClaudeAgent(AIAgent):
    """Claude AI Agent using Anthropic API"""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    API_KEY_ENV = "ANTHROPIC_API_KEY"

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="claude-analyst",
                model_type=ModelType.CLAUDE,
                role="Analyst & Researcher",
                capabilities=["analysis", "reasoning", "planning", "architecture", "code-review"],
                model_name=self.DEFAULT_MODEL,
            )
        super().__init__(config)
        self._client = None

    async def _get_client(self):
        """Get or create Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                api_key = os.getenv(self.API_KEY_ENV)
                if api_key:
                    self._client = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                logger.error("Anthropic SDK not installed. Run: pip install anthropic")
        return self._client

    async def is_available(self) -> bool:
        """Check if Claude is available"""
        return bool(os.getenv(self.API_KEY_ENV))

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AgentResponse:
        """Generate response using Claude"""
        start_time = time.time()

        try:
            client = await self._get_client()
            if not client:
                return AgentResponse(
                    agent_name=self.name,
                    model_type=self.config.model_type,
                    content="",
                    confidence=0.0,
                    response_time=0.0,
                    error=f"{self.API_KEY_ENV} not configured or SDK not installed"
                )

            # Build system prompt
            system_prompt = self.get_system_prompt(
                system_override,
                default_prompt=(
                    f"You are {self.name}, a {self.role}. "
                    f"Your capabilities include: {', '.join(self.config.capabilities)}. "
                    "Provide thoughtful, analytical, and comprehensive responses."
                ),
            )

            # Build user message
            user_content = prompt
            if context:
                user_content = f"Context:\n{context}\n\nTask:\n{prompt}"

            # Make API call
            response = await client.messages.create(
                model=self.config.model_name or self.DEFAULT_MODEL,
                max_tokens=min(self.config.max_tokens, 8192),
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )

            content = response.content[0].text
            response_time = time.time() - start_time

            # Update stats
            self.update_stats(response_time, True)
            self.add_to_history("user", prompt)
            self.add_to_history("assistant", content)

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content=content,
                confidence=0.85,
                response_time=response_time,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                metadata={
                    "model": self.config.model_name,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"Claude error: {e}")

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
        try:
            client = await self._get_client()
            if not client:
                return

            # Build system prompt
            system_prompt = self.get_system_prompt(
                system_override,
                default_prompt=(
                    f"You are {self.name}, a {self.role}. "
                    f"Your capabilities include: {', '.join(self.config.capabilities)}. "
                    "Provide thoughtful, analytical, and comprehensive responses."
                ),
            )

            # Build user message
            user_content = prompt
            if context:
                user_content = f"Context:\n{context}\n\nTask:\n{prompt}"

            # Stream the response
            async with client.messages.stream(
                model=self.config.model_name or self.DEFAULT_MODEL,
                max_tokens=min(self.config.max_tokens, 8192),
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
