"""
MLX Inference - Apple Silicon Optimized ML
===========================================

Native machine learning on Apple Silicon using MLX framework.
Provides extremely fast inference with unified memory architecture.

Features:
- Unified memory (no CPU<->GPU transfers)
- Lazy evaluation for efficiency
- Native Apple Silicon optimization
- Compatible with PyTorch/NumPy APIs
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class MLXConfig:
    """Configuration for MLX inference."""
    model_path: str
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.95
    repetition_penalty: float = 1.1
    use_quantization: bool = True  # 4-bit quantization for speed
    context_window: int = 4096


@dataclass
class MLXResponse:
    """Response from MLX inference."""
    content: str
    tokens_generated: int
    tokens_per_second: float
    inference_time: float
    model_name: str
    quantization: str
    memory_used_mb: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class MLXInference:
    """
    MLX-based inference engine for Apple Silicon.

    MLX is Apple's array framework for machine learning on Apple Silicon.
    It provides:
    - Unified memory architecture (no data copying between CPU/GPU)
    - Lazy evaluation for memory efficiency
    - Native Metal acceleration
    - NumPy-like API

    Supports models:
    - Llama 2/3
    - Mistral
    - Qwen
    - Phi-3
    - And any model converted to MLX format
    """

    MODELS_DIR = Path.home() / ".ai-dev-team" / "mlx_models"

    # Pre-configured MLX models
    AVAILABLE_MODELS = {
        "mlx-community/Llama-3.2-3B-Instruct-4bit": {
            "size": "1.8GB",
            "quantization": "4bit",
            "capabilities": ["general", "coding", "reasoning"],
            "context": 8192,
        },
        "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit": {
            "size": "4.2GB",
            "quantization": "4bit",
            "capabilities": ["coding", "debugging", "architecture"],
            "context": 32768,
        },
        "mlx-community/Phi-3.5-mini-instruct-4bit": {
            "size": "2.1GB",
            "quantization": "4bit",
            "capabilities": ["coding", "reasoning", "math"],
            "context": 4096,
        },
        "mlx-community/Mistral-7B-Instruct-v0.3-4bit": {
            "size": "4.1GB",
            "quantization": "4bit",
            "capabilities": ["general", "coding", "analysis"],
            "context": 32768,
        },
    }

    def __init__(self, config: Optional[MLXConfig] = None):
        self.config = config or MLXConfig(model_path="")
        self._model = None
        self._tokenizer = None
        self._mlx_available = self._check_mlx_available()

    def _check_mlx_available(self) -> bool:
        """Check if MLX is available."""
        try:
            import mlx.core as mx
            # Verify we're on Apple Silicon
            return mx.metal.is_available()
        except ImportError:
            return False

    @property
    def is_available(self) -> bool:
        """Check if MLX inference is available."""
        return self._mlx_available

    def get_memory_info(self) -> Dict[str, float]:
        """Get MLX memory usage information."""
        if not self._mlx_available:
            return {"available": False}

        try:
            import mlx.core as mx

            # Get memory stats
            active = mx.metal.get_active_memory() / (1024 ** 2)  # MB
            peak = mx.metal.get_peak_memory() / (1024 ** 2)  # MB
            cache = mx.metal.get_cache_memory() / (1024 ** 2)  # MB

            return {
                "active_mb": round(active, 2),
                "peak_mb": round(peak, 2),
                "cache_mb": round(cache, 2),
                "available": True,
            }
        except Exception as e:
            logger.debug(f"Could not get memory info: {e}")
            return {"available": False, "error": str(e)}

    async def load_model(self, model_name: str) -> bool:
        """
        Load an MLX model for inference.

        Args:
            model_name: HuggingFace model ID or local path

        Returns:
            True if model loaded successfully
        """
        if not self._mlx_available:
            logger.error("MLX not available on this system")
            return False

        try:
            from mlx_lm import load

            logger.info(f"Loading MLX model: {model_name}")

            # Load model and tokenizer
            self._model, self._tokenizer = load(model_name)

            self.config.model_path = model_name
            logger.info(f"Successfully loaded {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> Union[MLXResponse, AsyncIterator[str]]:
        """
        Generate text using the loaded MLX model.

        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: If True, yield tokens as they're generated

        Returns:
            MLXResponse or async iterator of tokens
        """
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("No model loaded. Call load_model() first.")

        start_time = time.time()
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature or self.config.temperature

        try:
            from mlx_lm import generate

            # Format prompt with chat template if available
            if hasattr(self._tokenizer, "apply_chat_template"):
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                formatted_prompt = self._tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            else:
                formatted_prompt = prompt
                if system_prompt:
                    formatted_prompt = f"{system_prompt}\n\n{prompt}"

            if stream:
                return self._generate_stream(formatted_prompt, max_tokens, temperature)

            # Generate response
            response_text = generate(
                self._model,
                self._tokenizer,
                prompt=formatted_prompt,
                max_tokens=max_tokens,
                temp=temperature,
                top_p=self.config.top_p,
                repetition_penalty=self.config.repetition_penalty,
            )

            inference_time = time.time() - start_time
            tokens_generated = len(self._tokenizer.encode(response_text))
            tokens_per_second = tokens_generated / inference_time if inference_time > 0 else 0

            memory_info = self.get_memory_info()

            return MLXResponse(
                content=response_text,
                tokens_generated=tokens_generated,
                tokens_per_second=round(tokens_per_second, 2),
                inference_time=round(inference_time, 3),
                model_name=self.config.model_path,
                quantization="4bit" if "4bit" in self.config.model_path else "fp16",
                memory_used_mb=memory_info.get("active_mb", 0),
            )

        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise

    async def _generate_stream(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream tokens as they're generated."""
        try:
            from mlx_lm import generate_step

            # Initialize generation
            tokens = self._tokenizer.encode(prompt)

            for _ in range(max_tokens):
                # Generate next token
                token = generate_step(
                    self._model,
                    tokens,
                    temp=temperature,
                )

                if token == self._tokenizer.eos_token_id:
                    break

                tokens.append(token)
                decoded = self._tokenizer.decode([token])
                yield decoded

                # Allow other tasks to run
                await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise

    async def embed(self, text: str) -> List[float]:
        """
        Generate embeddings for text using the model.

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        if not self._mlx_available:
            raise RuntimeError("MLX not available")

        try:
            import mlx.core as mx

            # Tokenize
            tokens = self._tokenizer.encode(text)
            input_ids = mx.array([tokens])

            # Get embeddings from model
            # This depends on model architecture
            outputs = self._model(input_ids)

            # Mean pooling over token embeddings
            if hasattr(outputs, "last_hidden_state"):
                embeddings = outputs.last_hidden_state.mean(axis=1)
            else:
                embeddings = outputs.mean(axis=1)

            return embeddings.tolist()[0]

        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise

    def clear_cache(self):
        """Clear MLX memory cache."""
        if self._mlx_available:
            try:
                import mlx.core as mx
                mx.metal.clear_cache()
                logger.info("Cleared MLX cache")
            except Exception as e:
                logger.debug(f"Could not clear cache: {e}")


# Global instance
_mlx_inference: Optional[MLXInference] = None


def get_mlx_inference() -> MLXInference:
    """Get or create the global MLX inference engine."""
    global _mlx_inference
    if _mlx_inference is None:
        _mlx_inference = MLXInference()
    return _mlx_inference


async def benchmark_mlx(model_name: str, prompt: str = "Write a Python hello world function"):
    """Benchmark MLX inference speed."""
    inference = get_mlx_inference()

    if not inference.is_available:
        print("MLX not available on this system")
        return

    print(f"Loading model: {model_name}")
    await inference.load_model(model_name)

    print(f"\nGenerating response for: {prompt[:50]}...")

    # Warm up
    await inference.generate(prompt, max_tokens=50)

    # Benchmark
    times = []
    tokens = []

    for i in range(3):
        response = await inference.generate(prompt, max_tokens=200)
        times.append(response.inference_time)
        tokens.append(response.tokens_generated)
        print(f"  Run {i+1}: {response.tokens_per_second:.1f} tokens/sec")

    avg_time = sum(times) / len(times)
    avg_tokens = sum(tokens) / len(tokens)
    avg_speed = avg_tokens / avg_time

    print(f"\nBenchmark Results:")
    print(f"  Average speed: {avg_speed:.1f} tokens/sec")
    print(f"  Memory used: {response.memory_used_mb:.1f} MB")


if __name__ == "__main__":
    import sys

    async def main():
        inference = MLXInference()

        if len(sys.argv) > 1:
            command = sys.argv[1]

            if command == "available":
                print(f"MLX Available: {inference.is_available}")
                if inference.is_available:
                    memory = inference.get_memory_info()
                    print(f"Memory: {memory}")

            elif command == "models":
                print("Available MLX models:")
                for name, info in MLXInference.AVAILABLE_MODELS.items():
                    print(f"  {name}")
                    print(f"    Size: {info['size']}, Quantization: {info['quantization']}")
                    print(f"    Capabilities: {', '.join(info['capabilities'])}")

            elif command == "benchmark" and len(sys.argv) > 2:
                model_name = sys.argv[2]
                await benchmark_mlx(model_name)

            elif command == "generate" and len(sys.argv) > 3:
                model_name = sys.argv[2]
                prompt = " ".join(sys.argv[3:])

                await inference.load_model(model_name)
                response = await inference.generate(prompt)
                print(f"\nResponse ({response.tokens_per_second:.1f} tok/s):")
                print(response.content)

        else:
            print("Usage:")
            print("  python -m ai_dev_team.apple.mlx_inference available")
            print("  python -m ai_dev_team.apple.mlx_inference models")
            print("  python -m ai_dev_team.apple.mlx_inference benchmark <model>")
            print("  python -m ai_dev_team.apple.mlx_inference generate <model> <prompt>")

    asyncio.run(main())
