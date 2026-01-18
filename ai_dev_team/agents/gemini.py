"""
Gemini Agent - Google Gemini AI Integration
"""

import logging
import os
import time
from typing import Optional

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)


class GeminiAgent(AIAgent):
    """Gemini AI Agent using Google AI API"""

    DEFAULT_MODEL = "gemini-2.5-flash"
    API_KEY_ENV = "GEMINI_API_KEY"

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="gemini-creative",
                model_type=ModelType.GEMINI,
                role="Creative Director & Innovator",
                capabilities=["creativity", "design", "innovation", "ui-ux", "brainstorming"],
                model_name=self.DEFAULT_MODEL,
            )
        super().__init__(config)
        self._model = None
        self._configured = False

    async def _get_model(self):
        """Get or create Gemini model"""
        if self._model is None and not self._configured:
            try:
                import google.generativeai as genai
                api_key = os.getenv(self.API_KEY_ENV)
                if api_key:
                    genai.configure(api_key=api_key)
                    self._model = genai.GenerativeModel(
                        self.config.model_name or self.DEFAULT_MODEL
                    )
                    self._configured = True
            except ImportError:
                logger.error("Google AI SDK not installed. Run: pip install google-generativeai")
        return self._model

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
            model = await self._get_model()
            if not model:
                return AgentResponse(
                    agent_name=self.name,
                    model_type=self.config.model_type,
                    content="",
                    confidence=0.0,
                    response_time=0.0,
                    error=f"{self.API_KEY_ENV} not configured or SDK not installed"
                )

            # Build prompt with context and role
            system_context = system_override or self.config.system_prompt or (
                f"You are {self.name}, a {self.role}. "
                f"Your capabilities include: {', '.join(self.config.capabilities)}. "
                "Provide creative, innovative, and forward-thinking responses."
            )

            full_prompt = f"{system_context}\n\n"
            if context:
                full_prompt += f"Context:\n{context}\n\n"
            full_prompt += f"Task:\n{prompt}"

            # Make API call
            response = await model.generate_content_async(full_prompt)
            content = response.text
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
