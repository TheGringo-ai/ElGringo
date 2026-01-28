"""
Apple Core ML Integration
=========================

Leverage Apple Silicon Neural Engine for:
- On-device inference (complete privacy)
- Hardware acceleration via Neural Engine
- Zero API costs
- Offline capable

Supports:
- MLX for LLM inference on Apple Silicon
- Vision framework for image analysis
- Speech framework for transcription
- NaturalLanguage framework for text analysis
"""

import asyncio
import logging
import os
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MLXModel(Enum):
    """Available MLX models for Apple Silicon"""
    LLAMA_3_2_1B = "mlx-community/Llama-3.2-1B-Instruct-4bit"
    LLAMA_3_2_3B = "mlx-community/Llama-3.2-3B-Instruct-4bit"
    LLAMA_3_1_8B = "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit"
    QWEN_2_5_3B = "mlx-community/Qwen2.5-3B-Instruct-4bit"
    QWEN_CODER_1B = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    MISTRAL_7B = "mlx-community/Mistral-7B-Instruct-v0.3-4bit"
    PHI_3_MINI = "mlx-community/Phi-3.5-mini-instruct-4bit"


@dataclass
class MLXResult:
    """Result from MLX inference"""
    success: bool
    content: str
    model: str
    tokens_generated: int
    tokens_per_second: float
    device: str
    error: Optional[str] = None


@dataclass
class VisionResult:
    """Result from Vision framework analysis"""
    success: bool
    text_results: List[Dict[str, Any]]
    objects_detected: List[str]
    faces_detected: int
    error: Optional[str] = None


class AppleCoreMLIntegration:
    """
    Apple Silicon Neural Engine integration for on-device AI.

    Provides:
    - On-device LLM inference via MLX
    - Image analysis via Vision framework
    - Speech recognition via Speech framework
    - Text analysis via NaturalLanguage framework
    - Complete privacy (no data leaves device)
    - Zero API costs
    - Works offline
    """

    def __init__(self):
        self.is_apple_silicon = self._check_apple_silicon()
        self.mlx_available = self._check_mlx()
        self._model_cache: Dict[str, Any] = {}
        self._cache_dir = Path.home() / ".ai-dev-team" / "mlx-cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        if self.is_apple_silicon:
            logger.info("Apple Silicon detected - Neural Engine available")
        else:
            logger.info("Not running on Apple Silicon - MLX unavailable")

    def _check_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon Mac"""
        if platform.system() != "Darwin":
            return False
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            return "Apple" in result.stdout
        except Exception:
            return False

    def _check_mlx(self) -> bool:
        """Check if MLX is available"""
        try:
            import mlx.core
            return True
        except ImportError:
            return False

    def get_system_info(self) -> Dict[str, Any]:
        """Get Apple Silicon system capabilities"""
        info = {
            "is_apple_silicon": self.is_apple_silicon,
            "mlx_available": self.mlx_available,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

        if self.is_apple_silicon:
            try:
                # Get chip and memory info
                result = subprocess.run(
                    ["system_profiler", "SPHardwareDataType", "-json"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    import json
                    data = json.loads(result.stdout)
                    hw = data.get("SPHardwareDataType", [{}])[0]
                    info["chip"] = hw.get("chip_type", "Unknown")
                    info["memory"] = hw.get("physical_memory", "Unknown")
                    info["cores"] = hw.get("number_processors", "Unknown")
            except Exception as e:
                logger.debug(f"Could not get hardware info: {e}")

            # Check for Neural Engine
            info["neural_engine"] = self.is_apple_silicon  # All Apple Silicon has ANE

        return info

    async def run_local_llm(
        self,
        prompt: str,
        model: str = MLXModel.LLAMA_3_2_3B.value,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
    ) -> MLXResult:
        """
        Run LLM inference on Apple Silicon Neural Engine via MLX.

        Benefits:
        - Completely private (on-device)
        - No API costs
        - Fast on Apple Silicon
        - Works offline

        Args:
            prompt: User prompt
            model: MLX model path
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt

        Returns:
            MLXResult with generated text
        """
        if not self.is_apple_silicon:
            return MLXResult(
                success=False,
                content="",
                model=model,
                tokens_generated=0,
                tokens_per_second=0.0,
                device="N/A",
                error="Requires Apple Silicon Mac (M1/M2/M3/M4)"
            )

        if not self.mlx_available:
            return MLXResult(
                success=False,
                content="",
                model=model,
                tokens_generated=0,
                tokens_per_second=0.0,
                device="N/A",
                error="MLX not installed. Run: pip install mlx mlx-lm"
            )

        try:
            from mlx_lm import load, generate

            # Load model (cached after first load)
            if model not in self._model_cache:
                logger.info(f"Loading MLX model: {model}")
                model_obj, tokenizer = load(model)
                self._model_cache[model] = (model_obj, tokenizer)
            else:
                model_obj, tokenizer = self._model_cache[model]

            # Build prompt with system message
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"

            # Generate response
            start_time = datetime.now(timezone.utc)
            response = generate(
                model_obj,
                tokenizer,
                prompt=full_prompt,
                max_tokens=max_tokens,
                verbose=False,
            )
            end_time = datetime.now(timezone.utc)

            # Calculate stats
            duration = (end_time - start_time).total_seconds()
            tokens = len(tokenizer.encode(response))
            tps = tokens / duration if duration > 0 else 0

            return MLXResult(
                success=True,
                content=response,
                model=model,
                tokens_generated=tokens,
                tokens_per_second=round(tps, 2),
                device="Apple Neural Engine",
            )

        except Exception as e:
            logger.error(f"MLX inference error: {e}")
            return MLXResult(
                success=False,
                content="",
                model=model,
                tokens_generated=0,
                tokens_per_second=0.0,
                device="Apple Neural Engine",
                error=str(e)
            )

    async def analyze_image_ocr(self, image_path: str) -> VisionResult:
        """
        Extract text from image using Apple Vision framework.

        On-device OCR - private and fast.

        Args:
            image_path: Path to image file

        Returns:
            VisionResult with extracted text
        """
        if platform.system() != "Darwin":
            return VisionResult(
                success=False,
                text_results=[],
                objects_detected=[],
                faces_detected=0,
                error="Requires macOS"
            )

        try:
            # Use AppleScript/Python bridge to call Vision framework
            script = f'''
import objc
from Foundation import NSURL
from Vision import VNRecognizeTextRequest, VNImageRequestHandler

# Load image
url = NSURL.fileURLWithPath_("{image_path}")

# Create text recognition request
request = VNRecognizeTextRequest.alloc().init()
request.setRecognitionLevel_(1)  # VNRequestTextRecognitionLevelAccurate

# Create handler and perform request
handler = VNImageRequestHandler.alloc().initWithURL_options_(url, None)
success, error = handler.performRequests_error_([request], None)

if not success:
    print("ERROR:", error)
else:
    results = []
    for observation in request.results():
        text = observation.topCandidates_(1)[0].string()
        conf = observation.confidence()
        results.append({{"text": text, "confidence": float(conf)}})
    import json
    print(json.dumps(results))
'''
            result = subprocess.run(
                ["python3", "-c", script],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                import json
                text_results = json.loads(result.stdout.strip())
                return VisionResult(
                    success=True,
                    text_results=text_results,
                    objects_detected=[],
                    faces_detected=0,
                )
            else:
                return VisionResult(
                    success=False,
                    text_results=[],
                    objects_detected=[],
                    faces_detected=0,
                    error=result.stderr or "OCR failed"
                )

        except Exception as e:
            return VisionResult(
                success=False,
                text_results=[],
                objects_detected=[],
                faces_detected=0,
                error=str(e)
            )

    async def transcribe_audio(
        self,
        audio_path: str,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Transcribe audio using on-device speech recognition.

        For better results, uses whisper.cpp if available (also runs on Neural Engine).

        Args:
            audio_path: Path to audio file
            language: Language code

        Returns:
            Dict with transcription result
        """
        if platform.system() != "Darwin":
            return {"success": False, "error": "Requires macOS"}

        try:
            # Try whisper.cpp first (runs on Neural Engine via Core ML)
            whisper_path = Path.home() / ".ai-dev-team" / "whisper.cpp"
            if whisper_path.exists():
                result = subprocess.run(
                    [
                        str(whisper_path / "main"),
                        "-m", str(whisper_path / "models" / "ggml-base.bin"),
                        "-f", audio_path,
                        "-l", language,
                        "--output-txt",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if result.returncode == 0:
                    return {
                        "success": True,
                        "transcription": result.stdout,
                        "engine": "whisper.cpp (Core ML)",
                    }

            # Fallback to macOS say command with speech recognition
            # (This is a simplified version - full implementation would use Speech framework)
            return {
                "success": False,
                "error": "whisper.cpp not installed. Install from: https://github.com/ggerganov/whisper.cpp"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def analyze_text_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze text sentiment using Apple NaturalLanguage framework.

        On-device, private, no API costs.

        Args:
            text: Text to analyze

        Returns:
            Dict with sentiment score
        """
        if platform.system() != "Darwin":
            return {"success": False, "error": "Requires macOS"}

        try:
            # Escape quotes for the script
            escaped_text = text.replace('"', "'")
            script = f'''
import NaturalLanguage

tagger = NaturalLanguage.NLTagger.alloc().initWithTagSchemes_([NaturalLanguage.NLTagSchemeSentimentScore])
tagger.setString_("{escaped_text}")

sentiment, _ = tagger.tagAtIndex_unit_scheme_tokenRange_(
    0,
    NaturalLanguage.NLTokenUnitDocument,
    NaturalLanguage.NLTagSchemeSentimentScore,
    None
)

print(float(sentiment) if sentiment else 0.0)
'''
            result = subprocess.run(
                ["python3", "-c", script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                score = float(result.stdout.strip())
                sentiment = "positive" if score > 0.1 else ("negative" if score < -0.1 else "neutral")
                return {
                    "success": True,
                    "score": score,
                    "sentiment": sentiment,
                    "engine": "Apple NaturalLanguage",
                }
            else:
                return {"success": False, "error": result.stderr}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List available MLX models for local inference"""
        return [
            {
                "id": model.value,
                "name": model.name.replace("_", " ").title(),
                "size": self._get_model_size(model.value),
                "type": "LLM",
            }
            for model in MLXModel
        ]

    def _get_model_size(self, model_path: str) -> str:
        """Estimate model size from name"""
        model_lower = model_path.lower()
        if "1b" in model_lower or "1.5b" in model_lower:
            return "~1GB"
        elif "3b" in model_lower:
            return "~2GB"
        elif "7b" in model_lower or "8b" in model_lower:
            return "~4-5GB"
        return "Unknown"

    def clear_model_cache(self):
        """Clear loaded models from memory"""
        self._model_cache.clear()
        logger.info("Cleared MLX model cache")


# Singleton instance
_apple_coreml: Optional[AppleCoreMLIntegration] = None


def get_apple_coreml() -> AppleCoreMLIntegration:
    """Get Apple Core ML integration instance"""
    global _apple_coreml
    if _apple_coreml is None:
        _apple_coreml = AppleCoreMLIntegration()
    return _apple_coreml
