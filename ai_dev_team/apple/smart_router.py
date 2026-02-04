"""
Smart Apple Router
==================

Intelligently routes AI tasks between local MLX models and cloud APIs
based on task complexity, latency requirements, and hardware capabilities.

Optimized for Apple Silicon Macs.
"""

import asyncio
import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for routing decisions."""
    SIMPLE = "simple"      # Quick responses, code completion
    MEDIUM = "medium"      # Code generation, explanations
    COMPLEX = "complex"    # Architecture, multi-file changes
    CRITICAL = "critical"  # Security audits, production code


class ModelTier(Enum):
    """Model tiers available."""
    LOCAL_FAST = "local_fast"    # Small local model (Phi-3, Llama 3B)
    LOCAL_SMART = "local_smart"  # Larger local model (Qwen 7B)
    CLOUD_FAST = "cloud_fast"    # Cloud API (GPT-4o-mini, Claude Haiku)
    CLOUD_SMART = "cloud_smart"  # Best cloud (GPT-4o, Claude Sonnet)


@dataclass
class AppleHardwareInfo:
    """Apple Silicon hardware information."""
    chip: str  # M1, M2, M3, etc.
    variant: str  # Pro, Max, Ultra
    memory_gb: int
    neural_engine_cores: int
    gpu_cores: int
    is_apple_silicon: bool = True

    @property
    def can_run_7b(self) -> bool:
        """Can run 7B parameter models comfortably."""
        return self.memory_gb >= 16

    @property
    def can_run_13b(self) -> bool:
        """Can run 13B parameter models."""
        return self.memory_gb >= 32

    @property
    def optimal_batch_size(self) -> int:
        """Optimal batch size for this hardware."""
        if self.memory_gb >= 32:
            return 8
        elif self.memory_gb >= 16:
            return 4
        return 2


@dataclass
class RoutingDecision:
    """Result of routing decision."""
    tier: ModelTier
    model_name: str
    reason: str
    estimated_latency_ms: int
    use_neural_engine: bool = False
    fallback_tier: Optional[ModelTier] = None


def get_apple_hardware_info() -> Optional[AppleHardwareInfo]:
    """Detect Apple Silicon hardware capabilities."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return None

    try:
        # Get chip info
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True, text=True
        )
        chip_str = result.stdout.strip()

        # Parse chip type
        chip = "M1"
        variant = ""
        if "M3" in chip_str:
            chip = "M3"
        elif "M2" in chip_str:
            chip = "M2"
        elif "M1" in chip_str:
            chip = "M1"

        if "Ultra" in chip_str:
            variant = "Ultra"
        elif "Max" in chip_str:
            variant = "Max"
        elif "Pro" in chip_str:
            variant = "Pro"

        # Get memory
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True
        )
        memory_bytes = int(result.stdout.strip())
        memory_gb = memory_bytes // (1024 ** 3)

        # Neural engine cores (approximation based on chip)
        ne_cores = {
            "M1": 16, "M1 Pro": 16, "M1 Max": 16, "M1 Ultra": 32,
            "M2": 16, "M2 Pro": 16, "M2 Max": 16, "M2 Ultra": 32,
            "M3": 16, "M3 Pro": 16, "M3 Max": 16,
        }.get(f"{chip} {variant}".strip(), 16)

        # GPU cores (approximation)
        gpu_cores = {
            "M1": 8, "M1 Pro": 16, "M1 Max": 32, "M1 Ultra": 64,
            "M2": 10, "M2 Pro": 19, "M2 Max": 38, "M2 Ultra": 76,
            "M3": 10, "M3 Pro": 18, "M3 Max": 40,
        }.get(f"{chip} {variant}".strip(), 10)

        return AppleHardwareInfo(
            chip=chip,
            variant=variant,
            memory_gb=memory_gb,
            neural_engine_cores=ne_cores,
            gpu_cores=gpu_cores,
        )
    except Exception as e:
        logger.warning(f"Could not detect Apple hardware: {e}")
        return None


class SmartAppleRouter:
    """
    Intelligently routes AI tasks between local and cloud models.

    Routing Strategy:
    1. SIMPLE tasks → Local fast model (lowest latency)
    2. MEDIUM tasks → Local smart model if available, else cloud fast
    3. COMPLEX tasks → Cloud smart model (best quality)
    4. CRITICAL tasks → Always cloud smart (reliability)

    Adapts based on:
    - Hardware capabilities (memory, chip generation)
    - Network conditions
    - Task urgency
    - Cost preferences
    """

    # Task type to complexity mapping
    TASK_COMPLEXITY = {
        # Simple tasks - prefer local
        "code_completion": TaskComplexity.SIMPLE,
        "docstring": TaskComplexity.SIMPLE,
        "variable_naming": TaskComplexity.SIMPLE,
        "quick_fix": TaskComplexity.SIMPLE,
        "explain_line": TaskComplexity.SIMPLE,

        # Medium tasks - local if capable
        "code_generation": TaskComplexity.MEDIUM,
        "explain_function": TaskComplexity.MEDIUM,
        "write_test": TaskComplexity.MEDIUM,
        "debug_error": TaskComplexity.MEDIUM,
        "refactor_small": TaskComplexity.MEDIUM,

        # Complex tasks - prefer cloud
        "architecture": TaskComplexity.COMPLEX,
        "code_review": TaskComplexity.COMPLEX,
        "multi_file": TaskComplexity.COMPLEX,
        "optimization": TaskComplexity.COMPLEX,

        # Critical tasks - always cloud
        "security_audit": TaskComplexity.CRITICAL,
        "production_code": TaskComplexity.CRITICAL,
        "api_design": TaskComplexity.CRITICAL,
    }

    def __init__(self, prefer_local: bool = True, cost_sensitive: bool = False):
        """
        Initialize the smart router.

        Args:
            prefer_local: Prefer local models when quality is similar
            cost_sensitive: Minimize cloud API costs
        """
        self.prefer_local = prefer_local
        self.cost_sensitive = cost_sensitive
        self.hardware = get_apple_hardware_info()

        # Track model performance for adaptive routing
        self._latency_history: Dict[str, List[float]] = {}
        self._quality_scores: Dict[str, List[float]] = {}

        # Available models
        self._local_models = self._detect_local_models()
        self._cloud_models = self._detect_cloud_models()

        logger.info(f"SmartRouter initialized: {self.hardware}")
        logger.info(f"Local models: {list(self._local_models.keys())}")
        logger.info(f"Cloud models: {list(self._cloud_models.keys())}")

    def _detect_local_models(self) -> Dict[str, Dict]:
        """Detect available local MLX/Ollama models."""
        models = {}

        # Check Ollama models
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n')[1:]:
                    parts = line.split()
                    if parts:
                        name = parts[0]
                        size = parts[1] if len(parts) > 1 else "unknown"
                        models[name] = {
                            "type": "ollama",
                            "size": size,
                            "tier": self._classify_model_tier(name, size)
                        }
        except Exception:
            pass

        return models

    def _detect_cloud_models(self) -> Dict[str, Dict]:
        """Detect available cloud models based on API keys."""
        models = {}

        if os.getenv("ANTHROPIC_API_KEY"):
            models["claude-sonnet"] = {"tier": ModelTier.CLOUD_SMART, "provider": "anthropic"}
            models["claude-haiku"] = {"tier": ModelTier.CLOUD_FAST, "provider": "anthropic"}

        if os.getenv("OPENAI_API_KEY"):
            models["gpt-4o"] = {"tier": ModelTier.CLOUD_SMART, "provider": "openai"}
            models["gpt-4o-mini"] = {"tier": ModelTier.CLOUD_FAST, "provider": "openai"}

        if os.getenv("GEMINI_API_KEY"):
            models["gemini-pro"] = {"tier": ModelTier.CLOUD_SMART, "provider": "google"}
            models["gemini-flash"] = {"tier": ModelTier.CLOUD_FAST, "provider": "google"}

        return models

    def _classify_model_tier(self, name: str, size: str) -> ModelTier:
        """Classify a local model into a tier."""
        name_lower = name.lower()

        # Small/fast models
        if any(x in name_lower for x in ["phi", "3b", "1b", "tiny", "small"]):
            return ModelTier.LOCAL_FAST

        # Larger/smarter models
        if any(x in name_lower for x in ["7b", "8b", "qwen", "llama3"]):
            return ModelTier.LOCAL_SMART

        return ModelTier.LOCAL_FAST

    def route(
        self,
        task_type: str,
        prompt_length: int = 0,
        urgency: str = "normal",  # low, normal, high
        require_cloud: bool = False,
    ) -> RoutingDecision:
        """
        Determine the best model for a task.

        Args:
            task_type: Type of task (from TASK_COMPLEXITY)
            prompt_length: Length of prompt in characters
            urgency: How urgent is the response needed
            require_cloud: Force cloud model usage

        Returns:
            RoutingDecision with model selection
        """
        complexity = self.TASK_COMPLEXITY.get(task_type, TaskComplexity.MEDIUM)

        # Force cloud for critical tasks or explicit requirement
        if require_cloud or complexity == TaskComplexity.CRITICAL:
            return self._select_cloud_model(complexity, urgency)

        # Check if local models can handle this
        can_use_local = self._can_use_local(complexity, prompt_length)

        if can_use_local and self.prefer_local:
            # Use local model
            decision = self._select_local_model(complexity)
            if decision:
                return decision

        # Fall back to cloud
        return self._select_cloud_model(complexity, urgency)

    def _can_use_local(self, complexity: TaskComplexity, prompt_length: int) -> bool:
        """Check if local models can handle this task."""
        if not self.hardware or not self._local_models:
            return False

        # Check memory constraints for prompt size
        max_context = 4096 if self.hardware.memory_gb < 16 else 8192

        if prompt_length > max_context * 3:  # ~3 chars per token
            return False

        # Complex tasks need larger models
        if complexity == TaskComplexity.COMPLEX:
            return self.hardware.can_run_7b

        return True

    def _select_local_model(self, complexity: TaskComplexity) -> Optional[RoutingDecision]:
        """Select best local model for complexity."""
        target_tier = (
            ModelTier.LOCAL_SMART if complexity in [TaskComplexity.MEDIUM, TaskComplexity.COMPLEX]
            else ModelTier.LOCAL_FAST
        )

        # Find matching model
        for name, info in self._local_models.items():
            if info["tier"] == target_tier:
                return RoutingDecision(
                    tier=target_tier,
                    model_name=name,
                    reason=f"Local {target_tier.value} for {complexity.value} task",
                    estimated_latency_ms=500 if target_tier == ModelTier.LOCAL_FAST else 2000,
                    use_neural_engine=True,
                    fallback_tier=ModelTier.CLOUD_FAST,
                )

        # Fall back to any local model
        if self._local_models:
            name = list(self._local_models.keys())[0]
            return RoutingDecision(
                tier=ModelTier.LOCAL_FAST,
                model_name=name,
                reason="Best available local model",
                estimated_latency_ms=1000,
                use_neural_engine=True,
                fallback_tier=ModelTier.CLOUD_FAST,
            )

        return None

    def _select_cloud_model(self, complexity: TaskComplexity, urgency: str) -> RoutingDecision:
        """Select best cloud model."""
        # Use smart model for complex/critical tasks, fast for simple/urgent
        use_smart = (
            complexity in [TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]
            and urgency != "high"
            and not self.cost_sensitive
        )

        target_tier = ModelTier.CLOUD_SMART if use_smart else ModelTier.CLOUD_FAST

        # Find matching model
        for name, info in self._cloud_models.items():
            if info["tier"] == target_tier:
                return RoutingDecision(
                    tier=target_tier,
                    model_name=name,
                    reason=f"Cloud {target_tier.value} for {complexity.value} task",
                    estimated_latency_ms=1000 if target_tier == ModelTier.CLOUD_FAST else 3000,
                    use_neural_engine=False,
                )

        # Fall back to any cloud model
        if self._cloud_models:
            name = list(self._cloud_models.keys())[0]
            info = self._cloud_models[name]
            return RoutingDecision(
                tier=info["tier"],
                model_name=name,
                reason="Best available cloud model",
                estimated_latency_ms=2000,
                use_neural_engine=False,
            )

        raise RuntimeError("No models available (local or cloud)")

    def get_status(self) -> Dict[str, Any]:
        """Get router status."""
        return {
            "hardware": {
                "chip": f"{self.hardware.chip} {self.hardware.variant}" if self.hardware else "Unknown",
                "memory_gb": self.hardware.memory_gb if self.hardware else 0,
                "can_run_7b": self.hardware.can_run_7b if self.hardware else False,
            },
            "local_models": list(self._local_models.keys()),
            "cloud_models": list(self._cloud_models.keys()),
            "prefer_local": self.prefer_local,
            "cost_sensitive": self.cost_sensitive,
        }


# Global instance
_router_instance: Optional[SmartAppleRouter] = None


def get_smart_router(prefer_local: bool = True) -> SmartAppleRouter:
    """Get or create the global smart router."""
    global _router_instance
    if _router_instance is None:
        _router_instance = SmartAppleRouter(prefer_local=prefer_local)
    return _router_instance
