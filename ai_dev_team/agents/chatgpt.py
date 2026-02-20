"""
ChatGPT Agent - OpenAI GPT Integration
"""

import logging
import os
import time
from typing import AsyncIterator, Optional

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)


class ChatGPTAgent(AIAgent):
    """ChatGPT AI Agent using OpenAI API"""

    DEFAULT_MODEL = "gpt-4o"
    API_KEY_ENV = "OPENAI_API_KEY"

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="chatgpt-coder",
                model_type=ModelType.CHATGPT,
                role="Lead Developer & Architect",
                capabilities=["coding", "debugging", "testing", "optimization", "documentation", "analysis", "architecture"],
                model_name=self.DEFAULT_MODEL,
            )
        super().__init__(config)
        self._client = None

    async def _get_client(self):
        """Get or create OpenAI client"""
        if self._client is None:
            try:
                import openai
                api_key = os.getenv(self.API_KEY_ENV)
                if api_key:
                    self._client = openai.AsyncOpenAI(api_key=api_key)
            except ImportError:
                logger.error("OpenAI SDK not installed. Run: pip install openai")
        return self._client

    async def is_available(self) -> bool:
        """Check if ChatGPT is available"""
        return bool(os.getenv(self.API_KEY_ENV))

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AgentResponse:
        """Generate response using ChatGPT"""
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

            # Build system message
            system_prompt = system_override or self.config.system_prompt or (
                f"You are {self.name}, a {self.role}. "
                f"Your capabilities include: {', '.join(self.config.capabilities)}. "
                "Be practical, comprehensive, and code-focused in your responses."
            )

            # Build messages
            messages = [{"role": "system", "content": system_prompt}]

            user_content = prompt
            if context:
                user_content = f"Context:\n{context}\n\nTask:\n{prompt}"

            messages.append({"role": "user", "content": user_content})

            # Make API call
            response = await client.chat.completions.create(
                model=self.config.model_name or self.DEFAULT_MODEL,
                messages=messages,
                max_tokens=min(self.config.max_tokens, 4096),
                temperature=self.config.temperature
            )

            content = response.choices[0].message.content
            response_time = time.time() - start_time

            # Update stats
            self.update_stats(response_time, True)
            self.add_to_history("user", prompt)
            self.add_to_history("assistant", content)

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content=content,
                confidence=0.92,
                response_time=response_time,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                metadata={
                    "model": self.config.model_name,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                    }
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"ChatGPT error: {e}")

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

            # Build messages
            system_prompt = system_override or self.config.system_prompt or (
                f"You are {self.name}, a {self.role}. "
                f"Your capabilities include: {', '.join(self.config.capabilities)}. "
                "Provide practical, well-structured solutions."
            )

            user_content = prompt
            if context:
                user_content = f"Context:\n{context}\n\nTask:\n{prompt}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]

            # Stream the response
            stream = await client.chat.completions.create(
                model=self.config.model_name or self.DEFAULT_MODEL,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=messages,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"ChatGPT streaming error: {e}")
