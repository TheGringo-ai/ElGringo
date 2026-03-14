"""
Gemini Agent - Google Gemini AI Integration

Uses the google-genai SDK (not the deprecated google-generativeai).
"""

import logging
import os
import time
from typing import AsyncIterator, Optional

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)


class GeminiAgent(AIAgent):
    """Gemini AI Agent using Google GenAI SDK"""

    DEFAULT_MODEL = "gemini-2.5-flash"
    API_KEY_ENV = "GEMINI_API_KEY"

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="gemini-coder",
                model_type=ModelType.GEMINI,
                role="Full-Stack Developer & Architect",
                capabilities=["coding", "debugging", "analysis", "creativity", "design", "architecture"],
                model_name=self.DEFAULT_MODEL,
            )
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Get or create Gemini client"""
        if self._client is None:
            try:
                from google import genai
                api_key = os.getenv(self.API_KEY_ENV)
                if api_key:
                    self._client = genai.Client(api_key=api_key)
            except ImportError:
                logger.error("Google GenAI SDK not installed. Run: pip install google-genai")
        return self._client

    async def is_available(self) -> bool:
        """Check if Gemini is available"""
        return bool(os.getenv(self.API_KEY_ENV))

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None
    ) -> AgentResponse:
        """Generate response using Gemini"""
        start_time = time.time()

        try:
            client = self._get_client()
            if not client:
                return AgentResponse(
                    agent_name=self.name,
                    model_type=self.config.model_type,
                    content="",
                    confidence=0.0,
                    response_time=0.0,
                    error=f"{self.API_KEY_ENV} not configured or SDK not installed"
                )

            from google.genai import types

            system_instruction = self.get_system_prompt(
                system_override,
                default_prompt=(
                    f"You are {self.name}, a {self.role}. "
                    f"Your capabilities include: {', '.join(self.config.capabilities)}. "
                    "Provide creative, innovative, and forward-thinking responses."
                ),
            )

            user_content = prompt
            if context:
                user_content = f"Context:\n{context}\n\nTask:\n{prompt}"

            response = await client.aio.models.generate_content(
                model=self.config.model_name or self.DEFAULT_MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_tokens,
                ),
            )

            content = response.text
            response_time = time.time() - start_time

            # Extract token usage from Gemini response
            input_tok = 0
            output_tok = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tok = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                output_tok = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

            self.update_stats(response_time, True)
            self.add_to_history("user", prompt)
            self.add_to_history("assistant", content)

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content=content,
                confidence=0.85,
                response_time=response_time,
                input_tokens=input_tok,
                output_tokens=output_tok,
                metadata={"model": self.config.model_name}
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"Gemini error: {e}")

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
            client = self._get_client()
            if not client:
                return

            from google.genai import types

            system_instruction = self.get_system_prompt(
                system_override,
                default_prompt=(
                    f"You are {self.name}, a {self.role}. "
                    f"Your capabilities include: {', '.join(self.config.capabilities)}. "
                    "Provide creative, innovative, and forward-thinking responses."
                ),
            )

            user_content = prompt
            if context:
                user_content = f"Context:\n{context}\n\nTask:\n{prompt}"

            stream = await client.aio.models.generate_content_stream(
                model=self.config.model_name or self.DEFAULT_MODEL,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_tokens,
                ),
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
