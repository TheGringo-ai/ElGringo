"""
MLX Agent - Native Apple Silicon AI Agent
==========================================

First-class AIAgent implementation using MLX for native Metal-accelerated
inference on Apple Silicon. Faster than Ollama for small/medium tasks due
to zero-copy unified memory access.

Supports:
- Qwen2.5-Coder-7B-Instruct-4bit (coding tasks)
- Llama-3.2-3B-Instruct-4bit (general chat, ultra-fast)

Usage:
    agent = MLXAgent()  # auto-selects best model
    response = await agent.generate_response("Write a Python hello world")
"""

import logging
import time
from typing import AsyncIterator, Optional

from .base import AIAgent, AgentConfig, AgentResponse, ModelType

logger = logging.getLogger(__name__)

# MLX model presets optimized for M3 Pro 18GB
MLX_MODELS = {
    "mlx-coder": {
        "hf_id": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        "display": "Qwen 2.5 Coder 7B (MLX)",
        "role": "Local Code Specialist (MLX Native)",
        "capabilities": ["coding", "debugging", "refactoring", "architecture"],
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "mlx-general": {
        "hf_id": "mlx-community/Llama-3.2-3B-Instruct-4bit",
        "display": "Llama 3.2 3B (MLX)",
        "role": "Local General Assistant (MLX Native)",
        "capabilities": ["general", "reasoning", "writing", "analysis"],
        "temperature": 0.7,
        "max_tokens": 2048,
    },
}


class MLXAgent(AIAgent):
    """
    AI Agent using Apple's MLX framework for native Metal inference.

    Benefits over Ollama:
    - Zero-copy unified memory (no CPU<->GPU transfers)
    - Native Metal 4 acceleration on M3 Pro
    - Lazy evaluation for memory efficiency
    - Faster first-token latency
    """

    def __init__(self, config: Optional[AgentConfig] = None, preset: str = "mlx-coder"):
        if config is None:
            model_info = MLX_MODELS.get(preset, MLX_MODELS["mlx-coder"])
            config = AgentConfig(
                name=preset,
                model_type=ModelType.LOCAL,
                role=model_info["role"],
                capabilities=model_info["capabilities"],
                model_name=model_info["hf_id"],
                temperature=model_info["temperature"],
                max_tokens=model_info["max_tokens"],
                cost_tier="budget",
            )
        super().__init__(config)
        self._mlx = None
        self._model_loaded = False

    def _get_mlx(self):
        """Lazy-load the MLX inference engine."""
        if self._mlx is not None:
            return self._mlx
        try:
            from ..apple.mlx_inference import get_mlx_inference
            self._mlx = get_mlx_inference()
            return self._mlx
        except Exception as e:
            logger.debug(f"MLX not available: {e}")
            return None

    async def _ensure_model_loaded(self) -> bool:
        """Load the model if not already loaded."""
        if self._model_loaded:
            return True

        mlx = self._get_mlx()
        if mlx is None or not mlx.is_available:
            return False

        try:
            success = await mlx.load_model(self.config.model_name)
            if success:
                self._model_loaded = True
                logger.info(f"MLX model loaded: {self.config.model_name}")
            return success
        except Exception as e:
            logger.warning(f"Could not load MLX model {self.config.model_name}: {e}")
            return False

    async def is_available(self) -> bool:
        """Check if MLX inference is available on this system."""
        mlx = self._get_mlx()
        return mlx is not None and mlx.is_available

    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None,
    ) -> AgentResponse:
        """Generate response using MLX native inference."""
        start_time = time.time()

        # Check availability and load model
        if not await self._ensure_model_loaded():
            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=0.0,
                error="MLX not available or model failed to load",
            )

        try:
            mlx = self._get_mlx()

            # Build prompt with context
            full_prompt = prompt
            if context:
                full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"

            system_prompt = self.get_system_prompt(
                system_override,
                default_prompt=f"You are {self.name}, a {self.role}. Provide clean, concise responses.",
            )

            # Generate with MLX
            response = await mlx.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            response_time = time.time() - start_time

            # Update stats
            self.update_stats(response_time, True)
            self.add_to_history("user", prompt)
            self.add_to_history("assistant", response.content)

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content=response.content,
                confidence=0.80,  # MLX local models: good quality
                response_time=response_time,
                input_tokens=len(prompt.split()),  # Approximate
                output_tokens=response.tokens_generated,
                metadata={
                    "model": self.config.model_name,
                    "tokens_per_second": response.tokens_per_second,
                    "inference_time": response.inference_time,
                    "memory_mb": response.memory_used_mb,
                    "quantization": response.quantization,
                    "engine": "mlx",
                    "local": True,
                },
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_stats(response_time, False)
            logger.error(f"MLX generation error: {e}")

            return AgentResponse(
                agent_name=self.name,
                model_type=self.config.model_type,
                content="",
                confidence=0.0,
                response_time=response_time,
                error=str(e),
            )

    async def generate_stream(
        self,
        prompt: str,
        context: str = "",
        system_override: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens using MLX native streaming."""
        if not await self._ensure_model_loaded():
            return

        try:
            mlx = self._get_mlx()

            full_prompt = prompt
            if context:
                full_prompt = f"Context:\n{context}\n\nTask:\n{prompt}"

            system_prompt = self.get_system_prompt(
                system_override,
                default_prompt=f"You are {self.name}, a {self.role}.",
            )

            # Stream with MLX
            stream = await mlx.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
            )

            async for token in stream:
                yield token

        except Exception as e:
            logger.error(f"MLX streaming error: {e}")


def create_mlx_coder() -> Optional[MLXAgent]:
    """Create an MLX-based coding agent. Returns None if MLX unavailable."""
    agent = MLXAgent(preset="mlx-coder")
    try:
        from ..apple.mlx_inference import get_mlx_inference
        if get_mlx_inference().is_available:
            return agent
    except Exception:
        pass
    return None


def create_mlx_general() -> Optional[MLXAgent]:
    """Create an MLX-based general agent. Returns None if MLX unavailable."""
    agent = MLXAgent(preset="mlx-general")
    try:
        from ..apple.mlx_inference import get_mlx_inference
        if get_mlx_inference().is_available:
            return agent
    except Exception:
        pass
    return None
