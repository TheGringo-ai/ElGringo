"""
Core ML Agent - On-Device AI for Apple Silicon
===============================================

Provides AI inference using Apple's Core ML framework for:
- Privacy-preserving on-device processing
- Apple Neural Engine (ANE) acceleration
- Low latency responses
- Offline capability

Supports converting and running models optimized for M1/M2/M3 chips.
"""

import asyncio
import logging
import platform
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ComputeUnit(Enum):
    """Core ML compute units for model execution."""
    CPU_ONLY = "cpuOnly"
    CPU_AND_GPU = "cpuAndGPU"
    CPU_AND_NE = "cpuAndNeuralEngine"  # Neural Engine - fastest for supported ops
    ALL = "all"  # Let Core ML decide


@dataclass
class CoreMLConfig:
    """Configuration for Core ML model execution."""
    model_path: str
    compute_units: ComputeUnit = ComputeUnit.ALL
    max_tokens: int = 2048
    temperature: float = 0.7
    use_fp16: bool = True  # Use FP16 for faster inference
    batch_size: int = 1
    cache_predictions: bool = True


@dataclass
class CoreMLResponse:
    """Response from Core ML inference."""
    content: str
    inference_time: float
    tokens_generated: int
    compute_unit_used: str
    model_name: str
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class CoreMLAgent:
    """
    AI Agent using Apple Core ML for on-device inference.

    Features:
    - Runs entirely on-device (privacy-preserving)
    - Accelerated by Apple Neural Engine on M1/M2/M3
    - Zero API costs
    - Works offline
    - Low latency for simple tasks

    Usage:
        agent = CoreMLAgent()
        if await agent.is_available():
            response = await agent.generate("Write a Python function")
            print(response.content)
    """

    MODELS_DIR = Path.home() / ".ai-dev-team" / "coreml_models"

    # Pre-configured models optimized for Apple Silicon
    AVAILABLE_MODELS = {
        "phi-3-mini": {
            "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-onnx",
            "size": "2.4GB",
            "capabilities": ["coding", "reasoning", "general"],
            "recommended_compute": ComputeUnit.CPU_AND_NE,
        },
        "gemma-2b": {
            "url": "https://huggingface.co/google/gemma-2b",
            "size": "1.5GB",
            "capabilities": ["coding", "general"],
            "recommended_compute": ComputeUnit.CPU_AND_NE,
        },
        "tinyllama": {
            "url": "https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "size": "638MB",
            "capabilities": ["general", "fast"],
            "recommended_compute": ComputeUnit.ALL,
        },
    }

    def __init__(self, config: Optional[CoreMLConfig] = None):
        self.config = config
        self._model = None
        self._tokenizer = None
        self._is_apple_silicon = self._check_apple_silicon()
        self._prediction_cache: Dict[str, CoreMLResponse] = {}

    def _check_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon."""
        if platform.system() != "Darwin":
            return False
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
            )
            brand = result.stdout.strip().lower()
            return "apple" in brand or "m1" in brand or "m2" in brand or "m3" in brand
        except Exception:
            return False

    async def is_available(self) -> bool:
        """Check if Core ML is available on this system."""
        if not self._is_apple_silicon:
            logger.debug("Core ML agent requires Apple Silicon")
            return False

        try:
            # Check if coremltools is installed
            import coremltools  # noqa: F401
            return True
        except ImportError:
            logger.debug("coremltools not installed")
            return False

    def get_chip_info(self) -> Dict[str, Any]:
        """Get information about the Apple Silicon chip."""
        info = {
            "is_apple_silicon": self._is_apple_silicon,
            "chip": "Unknown",
            "neural_engine_cores": 0,
            "gpu_cores": 0,
        }

        if not self._is_apple_silicon:
            return info

        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
            )
            info["chip"] = result.stdout.strip()

            # Estimate Neural Engine cores based on chip
            chip_lower = info["chip"].lower()
            if "m3 max" in chip_lower:
                info["neural_engine_cores"] = 16
                info["gpu_cores"] = 40
            elif "m3 pro" in chip_lower:
                info["neural_engine_cores"] = 16
                info["gpu_cores"] = 18
            elif "m3" in chip_lower:
                info["neural_engine_cores"] = 16
                info["gpu_cores"] = 10
            elif "m2 ultra" in chip_lower:
                info["neural_engine_cores"] = 32
                info["gpu_cores"] = 76
            elif "m2 max" in chip_lower:
                info["neural_engine_cores"] = 16
                info["gpu_cores"] = 38
            elif "m2 pro" in chip_lower:
                info["neural_engine_cores"] = 16
                info["gpu_cores"] = 19
            elif "m2" in chip_lower:
                info["neural_engine_cores"] = 16
                info["gpu_cores"] = 10
            elif "m1 ultra" in chip_lower:
                info["neural_engine_cores"] = 32
                info["gpu_cores"] = 64
            elif "m1 max" in chip_lower:
                info["neural_engine_cores"] = 16
                info["gpu_cores"] = 32
            elif "m1 pro" in chip_lower:
                info["neural_engine_cores"] = 16
                info["gpu_cores"] = 16
            elif "m1" in chip_lower:
                info["neural_engine_cores"] = 16
                info["gpu_cores"] = 8

        except Exception as e:
            logger.debug(f"Could not get chip info: {e}")

        return info

    async def load_model(self, model_name: str = "phi-3-mini") -> bool:
        """
        Load a Core ML model for inference.

        Args:
            model_name: Name of the model to load

        Returns:
            True if model loaded successfully
        """
        if not await self.is_available():
            return False

        model_path = self.MODELS_DIR / f"{model_name}.mlpackage"

        if not model_path.exists():
            logger.warning(f"Model not found: {model_path}")
            logger.info(f"Run: python -m elgringo.apple.coreml_agent download {model_name}")
            return False

        try:
            import coremltools as ct

            # Determine compute units
            compute_units = ct.ComputeUnit.ALL
            if self.config and self.config.compute_units:
                compute_map = {
                    ComputeUnit.CPU_ONLY: ct.ComputeUnit.CPU_ONLY,
                    ComputeUnit.CPU_AND_GPU: ct.ComputeUnit.CPU_AND_GPU,
                    ComputeUnit.CPU_AND_NE: ct.ComputeUnit.CPU_AND_NE,
                    ComputeUnit.ALL: ct.ComputeUnit.ALL,
                }
                compute_units = compute_map.get(self.config.compute_units, ct.ComputeUnit.ALL)

            # Load the model
            self._model = ct.models.MLModel(
                str(model_path),
                compute_units=compute_units,
            )

            logger.info(f"Loaded Core ML model: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load Core ML model: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
    ) -> CoreMLResponse:
        """
        Generate a response using the Core ML model.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: System prompt for context

        Returns:
            CoreMLResponse with generated content
        """
        start_time = time.time()

        # Check cache
        cache_key = f"{prompt}:{system_prompt}:{max_tokens}:{temperature}"
        if self.config and self.config.cache_predictions:
            if cache_key in self._prediction_cache:
                cached = self._prediction_cache[cache_key]
                cached.cached = True
                return cached

        if self._model is None:
            # Try to load default model
            if not await self.load_model():
                return CoreMLResponse(
                    content="Core ML model not loaded. Run load_model() first.",
                    inference_time=0,
                    tokens_generated=0,
                    compute_unit_used="none",
                    model_name="none",
                )

        try:
            # Build full prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"

            # Run inference
            # Note: Actual implementation depends on the specific model architecture
            # This is a simplified example
            inputs = {"prompt": full_prompt}
            prediction = self._model.predict(inputs)

            content = prediction.get("generated_text", "")
            inference_time = time.time() - start_time

            response = CoreMLResponse(
                content=content,
                inference_time=inference_time,
                tokens_generated=len(content.split()),  # Approximate
                compute_unit_used=str(self.config.compute_units if self.config else "all"),
                model_name=self._model.get_spec().description.metadata.shortDescription,
            )

            # Cache the response
            if self.config and self.config.cache_predictions:
                self._prediction_cache[cache_key] = response

            return response

        except Exception as e:
            logger.error(f"Core ML inference error: {e}")
            return CoreMLResponse(
                content=f"Error: {e}",
                inference_time=time.time() - start_time,
                tokens_generated=0,
                compute_unit_used="error",
                model_name="error",
            )

    def clear_cache(self):
        """Clear the prediction cache."""
        self._prediction_cache.clear()


def convert_to_coreml(
    source_model: str,
    output_path: str,
    model_type: str = "pytorch",
    optimize_for_neural_engine: bool = True,
) -> bool:
    """
    Convert a model to Core ML format.

    Args:
        source_model: Path to source model or HuggingFace model ID
        output_path: Path for output .mlpackage
        model_type: Type of source model (pytorch, tensorflow, onnx)
        optimize_for_neural_engine: Apply ANE optimizations

    Returns:
        True if conversion successful
    """
    try:
        import coremltools as ct

        logger.info(f"Converting {source_model} to Core ML...")

        if model_type == "pytorch":
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            # Load model
            model = AutoModelForCausalLM.from_pretrained(source_model, torch_dtype=torch.float16)
            tokenizer = AutoTokenizer.from_pretrained(source_model)

            # Trace the model
            model.eval()
            example_input = tokenizer("Hello", return_tensors="pt")
            traced_model = torch.jit.trace(model, example_input["input_ids"])

            # Convert to Core ML
            mlmodel = ct.convert(
                traced_model,
                inputs=[ct.TensorType(name="input_ids", shape=(1, ct.RangeDim(1, 2048)))],
                minimum_deployment_target=ct.target.macOS13,
                compute_precision=ct.precision.FLOAT16 if optimize_for_neural_engine else ct.precision.FLOAT32,
            )

            # Save
            mlmodel.save(output_path)
            logger.info(f"Saved Core ML model to {output_path}")
            return True

        elif model_type == "onnx":
            mlmodel = ct.converters.onnx.convert(
                model=source_model,
                minimum_deployment_target=ct.target.macOS13,
            )
            mlmodel.save(output_path)
            return True

    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return False


# Global instance
_coreml_agent: Optional[CoreMLAgent] = None


def get_coreml_agent() -> CoreMLAgent:
    """Get or create the global Core ML agent."""
    global _coreml_agent
    if _coreml_agent is None:
        _coreml_agent = CoreMLAgent()
    return _coreml_agent


if __name__ == "__main__":
    import sys

    async def main():
        agent = CoreMLAgent()

        if len(sys.argv) > 1:
            command = sys.argv[1]

            if command == "info":
                info = agent.get_chip_info()
                print(f"Apple Silicon: {info['is_apple_silicon']}")
                print(f"Chip: {info['chip']}")
                print(f"Neural Engine Cores: {info['neural_engine_cores']}")
                print(f"GPU Cores: {info['gpu_cores']}")

            elif command == "available":
                available = await agent.is_available()
                print(f"Core ML Available: {available}")

            elif command == "models":
                print("Available models:")
                for name, info in CoreMLAgent.AVAILABLE_MODELS.items():
                    print(f"  {name}: {info['size']} - {', '.join(info['capabilities'])}")

        else:
            print("Usage: python -m elgringo.apple.coreml_agent [info|available|models]")

    asyncio.run(main())
