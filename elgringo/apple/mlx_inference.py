"""
MLX Inference - Apple Silicon Optimized ML
===========================================

Native machine learning on Apple Silicon using MLX framework.
Provides extremely fast inference with unified memory architecture.

Features:
- Multi-model support (hot-swap between coder and general models)
- Unified memory (no CPU<->GPU transfers)
- Lazy evaluation for efficiency
- Native Metal acceleration
- Streaming support with async iteration
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


@dataclass
class MLXConfig:
    """Configuration for MLX inference."""
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.95
    repetition_penalty: float = 1.1
    max_cached_models: int = 2  # Keep up to 2 models in memory (18GB M3 Pro)
    memory_limit_mb: int = 10_000  # Max Metal memory before refusing new loads (10GB)
    memory_warning_mb: int = 8_000  # Warn and clear cache at this threshold
    min_free_system_mb: int = 2_000  # Keep at least 2GB free for system/Python


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


# Pre-configured MLX models optimized for M3 Pro 18GB
AVAILABLE_MODELS = {
    "mlx-community/Qwen2.5-3B-Instruct-4bit": {
        "size": "1.8GB",
        "quantization": "4bit",
        "capabilities": ["general", "coding", "reasoning"],
        "context": 32768,
        "alias": "qwen-3b",
    },
    "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit": {
        "size": "4.2GB",
        "quantization": "4bit",
        "capabilities": ["coding", "debugging", "architecture"],
        "context": 32768,
        "alias": "qwen-coder",
    },
    "mlx-community/Phi-3.5-mini-instruct-4bit": {
        "size": "2.1GB",
        "quantization": "4bit",
        "capabilities": ["coding", "reasoning", "math"],
        "context": 4096,
        "alias": "phi-3",
    },
    "mlx-community/Mistral-7B-Instruct-v0.3-4bit": {
        "size": "4.1GB",
        "quantization": "4bit",
        "capabilities": ["general", "coding", "analysis"],
        "context": 32768,
        "alias": "mistral-7b",
    },
}


class MLXInference:
    """
    MLX-based inference engine for Apple Silicon with multi-model support.

    Keeps multiple models loaded in unified memory (M3 Pro 18GB can hold
    both the 3B general + 7B coder model simultaneously at ~6GB total).
    Uses LRU eviction when memory is tight.
    """

    def __init__(self, config: Optional[MLXConfig] = None):
        self.config = config or MLXConfig()
        self._models: Dict[str, Tuple[Any, Any]] = {}  # name -> (model, tokenizer)
        self._load_order: List[str] = []  # LRU tracking
        self._mlx_available = self._check_mlx_available()

    def _check_mlx_available(self) -> bool:
        """Check if MLX is available."""
        try:
            import mlx.core as mx
            return mx.metal.is_available()
        except ImportError:
            return False

    @property
    def is_available(self) -> bool:
        """Check if MLX inference is available."""
        return self._mlx_available

    @property
    def loaded_models(self) -> List[str]:
        """List currently loaded model names."""
        return list(self._models.keys())

    def get_memory_info(self) -> Dict[str, Any]:
        """Get MLX memory usage information."""
        if not self._mlx_available:
            return {"available": False}

        try:
            import mlx.core as mx

            active = mx.get_active_memory() / (1024 ** 2)
            peak = mx.get_peak_memory() / (1024 ** 2)
            cache = mx.get_cache_memory() / (1024 ** 2)
            system_free = self._get_system_free_memory_mb()

            return {
                "active_mb": round(active, 2),
                "peak_mb": round(peak, 2),
                "cache_mb": round(cache, 2),
                "system_free_mb": system_free,
                "loaded_models": self.loaded_models,
                "memory_pressure": self._get_memory_pressure(active),
                "available": True,
            }
        except Exception as e:
            logger.debug(f"Could not get memory info: {e}")
            return {"available": False, "error": str(e)}

    def _get_system_free_memory_mb(self) -> int:
        """Get free system memory in MB using vm_stat on macOS."""
        try:
            import subprocess
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=2,
            )
            page_size = 16384  # Default Apple Silicon page size
            free_pages = 0
            for line in result.stdout.splitlines():
                if "page size" in line.lower():
                    page_size = int(''.join(c for c in line if c.isdigit()))
                elif "Pages free" in line:
                    free_pages += int(line.split(":")[1].strip().rstrip("."))
                elif "Pages inactive" in line:
                    free_pages += int(line.split(":")[1].strip().rstrip("."))
            return int(free_pages * page_size / (1024 * 1024))
        except Exception:
            return 99999  # Assume plenty if we can't check

    def _get_memory_pressure(self, active_mb: float) -> str:
        """Classify memory pressure: low/medium/high/critical."""
        if active_mb > self.config.memory_limit_mb:
            return "critical"
        elif active_mb > self.config.memory_warning_mb:
            return "high"
        elif active_mb > self.config.memory_warning_mb * 0.6:
            return "medium"
        return "low"

    def _check_memory_safe(self, model_name: str) -> Tuple[bool, str]:
        """Check if it's safe to load a model. Returns (safe, reason)."""
        if not self._mlx_available:
            return False, "MLX not available"

        try:
            import mlx.core as mx
            active_mb = mx.get_active_memory() / (1024 ** 2)
            cache_mb = mx.get_cache_memory() / (1024 ** 2)

            # Check Metal memory
            if active_mb > self.config.memory_limit_mb:
                return False, (
                    f"Metal memory too high ({active_mb:.0f}MB/{self.config.memory_limit_mb}MB). "
                    f"Loaded: {self.loaded_models}"
                )

            # Check system memory
            sys_free = self._get_system_free_memory_mb()
            if sys_free < self.config.min_free_system_mb:
                return False, (
                    f"System memory too low ({sys_free}MB free, need {self.config.min_free_system_mb}MB). "
                    f"Loaded: {self.loaded_models}"
                )

            # Estimate model size from AVAILABLE_MODELS
            model_size_mb = 0
            if model_name in AVAILABLE_MODELS:
                size_str = AVAILABLE_MODELS[model_name]["size"]
                model_size_mb = float(size_str.replace("GB", "")) * 1024

            # Check if loading this model would exceed the limit
            projected = active_mb + model_size_mb
            if projected > self.config.memory_limit_mb:
                # Try clearing cache first
                if cache_mb > 200:
                    mx.metal.clear_cache()
                    active_mb = mx.get_active_memory() / (1024 ** 2)
                    projected = active_mb + model_size_mb
                    logger.info(f"Cleared {cache_mb:.0f}MB cache, active now {active_mb:.0f}MB")

                if projected > self.config.memory_limit_mb:
                    return False, (
                        f"Loading {model_name} (~{model_size_mb:.0f}MB) would exceed limit "
                        f"({active_mb:.0f}MB + {model_size_mb:.0f}MB > {self.config.memory_limit_mb}MB)"
                    )

            return True, "ok"

        except Exception as e:
            logger.warning(f"Memory check failed: {e} — allowing load")
            return True, "check_failed"

    def _auto_free_memory(self):
        """Proactively free memory when pressure is high."""
        if not self._mlx_available:
            return

        try:
            import mlx.core as mx
            active_mb = mx.get_active_memory() / (1024 ** 2)

            if active_mb > self.config.memory_warning_mb:
                logger.warning(f"Memory pressure high ({active_mb:.0f}MB) — clearing cache")
                mx.metal.clear_cache()

                # If still high after cache clear, evict least-used model
                active_mb = mx.get_active_memory() / (1024 ** 2)
                if active_mb > self.config.memory_warning_mb and self._load_order:
                    oldest = self._load_order[0]
                    logger.warning(f"Still high ({active_mb:.0f}MB) — evicting {oldest}")
                    self.unload_model(oldest)

        except Exception as e:
            logger.debug(f"Auto-free failed: {e}")

    def _evict_if_needed(self):
        """Evict the least recently used model if we're at capacity."""
        while len(self._models) >= self.config.max_cached_models and self._load_order:
            oldest = self._load_order.pop(0)
            if oldest in self._models:
                del self._models[oldest]
                logger.info(f"Evicted model from cache: {oldest}")
                self.clear_cache()

    async def load_model(self, model_name: str) -> bool:
        """
        Load an MLX model with memory safety checks.
        Checks system + Metal memory before loading.
        Evicts LRU model if at capacity. Auto-clears cache under pressure.
        """
        if not self._mlx_available:
            logger.error("MLX not available on this system")
            return False

        # Already loaded — just bump LRU
        if model_name in self._models:
            if model_name in self._load_order:
                self._load_order.remove(model_name)
            self._load_order.append(model_name)
            return True

        # Memory safety check BEFORE loading
        safe, reason = self._check_memory_safe(model_name)
        if not safe:
            logger.error(f"Cannot load {model_name}: {reason}")
            # Try evicting a model and check again
            if self._load_order:
                oldest = self._load_order[0]
                logger.warning(f"Evicting {oldest} to make room for {model_name}")
                self.unload_model(oldest)
                safe, reason = self._check_memory_safe(model_name)
                if not safe:
                    logger.error(f"Still cannot load after eviction: {reason}")
                    return False

        try:
            from mlx_lm import load

            self._evict_if_needed()

            mem_before = self.get_memory_info()
            logger.info(f"Loading MLX model: {model_name} (Metal: {mem_before.get('active_mb', '?')}MB)")
            model, tokenizer = load(model_name)
            self._models[model_name] = (model, tokenizer)
            self._load_order.append(model_name)

            mem_after = self.get_memory_info()
            delta = mem_after.get("active_mb", 0) - mem_before.get("active_mb", 0)
            logger.info(
                f"Loaded {model_name} (+{delta:.0f}MB, total {mem_after.get('active_mb', '?')}MB, "
                f"{len(self._models)} models cached, pressure: {mem_after.get('memory_pressure', '?')})"
            )
            return True

        except RuntimeError as e:
            if "Insufficient Memory" in str(e) or "kIOGPU" in str(e):
                logger.error(f"Metal OOM loading {model_name} — clearing all and retrying")
                self._emergency_cleanup()
                return False
            logger.error(f"Failed to load model {model_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False

    def _emergency_cleanup(self):
        """Last-resort cleanup: unload all models, clear all caches."""
        logger.warning("Emergency cleanup — unloading all models")
        model_names = list(self._models.keys())
        for name in model_names:
            try:
                del self._models[name]
            except Exception:
                pass
        self._models.clear()
        self._load_order.clear()
        self.clear_cache()
        try:
            import gc
            gc.collect()
        except Exception:
            pass
        logger.info("Emergency cleanup complete")

    def _get_model(self, model_name: str) -> Tuple[Any, Any]:
        """Get a loaded model and tokenizer by name."""
        if model_name not in self._models:
            raise RuntimeError(f"Model not loaded: {model_name}. Call load_model() first.")
        return self._models[model_name]

    async def generate(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> Union[MLXResponse, AsyncIterator[str]]:
        """
        Generate text using an MLX model.

        Args:
            prompt: User prompt
            model_name: Which model to use (defaults to last loaded)
            system_prompt: System prompt for context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: If True, yield tokens as they're generated
        """
        # Resolve model
        if model_name is None:
            if not self._load_order:
                raise RuntimeError("No model loaded. Call load_model() first.")
            model_name = self._load_order[-1]

        model, tokenizer = self._get_model(model_name)

        # Pre-generation memory check — free cache if pressure is high
        self._auto_free_memory()

        start_time = time.time()
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature

        try:
            from mlx_lm import generate as mlx_generate

            # Format prompt with chat template
            if hasattr(tokenizer, "apply_chat_template"):
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                formatted_prompt = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True,
                )
            else:
                formatted_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            if stream:
                return self._generate_stream(model, tokenizer, model_name, formatted_prompt, max_tokens, temperature)

            # Build sampler
            from mlx_lm.sample_utils import make_sampler
            sampler = make_sampler(temp=temperature, top_p=self.config.top_p)

            response_text = mlx_generate(
                model, tokenizer,
                prompt=formatted_prompt,
                max_tokens=max_tokens,
                sampler=sampler,
            )

            # Strip special tokens that leak into output
            for tok in ("<|im_end|>", "<|endoftext|>", "<|end|>", "</s>"):
                response_text = response_text.replace(tok, "")
            response_text = response_text.strip()

            inference_time = time.time() - start_time
            tokens_generated = len(tokenizer.encode(response_text))
            tokens_per_second = tokens_generated / inference_time if inference_time > 0 else 0

            memory_info = self.get_memory_info()

            return MLXResponse(
                content=response_text,
                tokens_generated=tokens_generated,
                tokens_per_second=round(tokens_per_second, 2),
                inference_time=round(inference_time, 3),
                model_name=model_name,
                quantization="4bit" if "4bit" in model_name else "fp16",
                memory_used_mb=memory_info.get("active_mb", 0),
            )

        except RuntimeError as e:
            if "Insufficient Memory" in str(e) or "kIOGPU" in str(e):
                logger.error(f"Metal OOM during generation ({model_name}): {e}")
                self._emergency_cleanup()
                raise RuntimeError(
                    f"Metal out of memory during generation. Models unloaded. "
                    f"Retry with a smaller max_tokens or fewer loaded models."
                ) from e
            logger.error(f"Generation error ({model_name}): {e}")
            raise
        except Exception as e:
            logger.error(f"Generation error ({model_name}): {e}")
            raise

    async def _generate_stream(
        self,
        model: Any,
        tokenizer: Any,
        model_name: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream tokens as they're generated."""
        try:
            from mlx_lm import stream_generate
            from mlx_lm.sample_utils import make_sampler

            sampler = make_sampler(temp=temperature, top_p=self.config.top_p)

            for response in stream_generate(
                model, tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                sampler=sampler,
            ):
                yield response.text
                await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Streaming error ({model_name}): {e}")
            raise

    def unload_model(self, model_name: str):
        """Explicitly unload a model to free memory."""
        if model_name in self._models:
            del self._models[model_name]
            if model_name in self._load_order:
                self._load_order.remove(model_name)
            self.clear_cache()
            logger.info(f"Unloaded model: {model_name}")

    def clear_cache(self):
        """Clear MLX Metal memory cache."""
        if self._mlx_available:
            try:
                import mlx.core as mx
                mx.metal.clear_cache()
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
    await inference.generate(prompt, model_name=model_name, max_tokens=50)

    # Benchmark
    times = []
    tokens = []

    for i in range(3):
        response = await inference.generate(prompt, model_name=model_name, max_tokens=200)
        times.append(response.inference_time)
        tokens.append(response.tokens_generated)
        print(f"  Run {i+1}: {response.tokens_per_second:.1f} tokens/sec")

    avg_time = sum(times) / len(times)
    avg_tokens = sum(tokens) / len(tokens)
    avg_speed = avg_tokens / avg_time

    print(f"\nBenchmark Results:")
    print(f"  Model: {model_name}")
    print(f"  Average speed: {avg_speed:.1f} tokens/sec")
    print(f"  Memory: {inference.get_memory_info()}")


if __name__ == "__main__":
    import sys

    async def main():
        inference = MLXInference()

        if len(sys.argv) > 1:
            command = sys.argv[1]

            if command == "available":
                print(f"MLX Available: {inference.is_available}")
                if inference.is_available:
                    print(f"Memory: {inference.get_memory_info()}")

            elif command == "models":
                print("Available MLX models:")
                for name, info in AVAILABLE_MODELS.items():
                    print(f"  {info['alias']:12s}  {name}")
                    print(f"               Size: {info['size']}, Quant: {info['quantization']}, Ctx: {info['context']}")

            elif command == "benchmark" and len(sys.argv) > 2:
                model_name = sys.argv[2]
                await benchmark_mlx(model_name)

            elif command == "generate" and len(sys.argv) > 3:
                model_name = sys.argv[2]
                prompt = " ".join(sys.argv[3:])

                await inference.load_model(model_name)
                response = await inference.generate(prompt, model_name=model_name)
                print(f"\nResponse ({response.tokens_per_second:.1f} tok/s):")
                print(response.content)

            elif command == "chat" and len(sys.argv) > 2:
                model_name = sys.argv[2]
                await inference.load_model(model_name)
                print(f"MLX Chat — {model_name} (type 'quit' to exit)")
                while True:
                    try:
                        prompt = input("\n> ")
                    except (EOFError, KeyboardInterrupt):
                        break
                    if prompt.strip().lower() in ("quit", "exit"):
                        break
                    response = await inference.generate(prompt, model_name=model_name)
                    print(f"\n[{response.tokens_per_second:.1f} tok/s] {response.content}")

        else:
            print("Usage:")
            print("  python -m elgringo.apple.mlx_inference available")
            print("  python -m elgringo.apple.mlx_inference models")
            print("  python -m elgringo.apple.mlx_inference benchmark <model>")
            print("  python -m elgringo.apple.mlx_inference generate <model> <prompt>")
            print("  python -m elgringo.apple.mlx_inference chat <model>")

    asyncio.run(main())
