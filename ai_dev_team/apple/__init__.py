"""
Apple Intelligence Integration
==============================

Deep integration with Apple's AI ecosystem:
- Core ML for on-device inference
- MLX for Apple Silicon optimization
- Apple Neural Engine (ANE) acceleration
- Siri and Shortcuts integration
- Writing Tools and system-wide AI features
"""

from .coreml_agent import CoreMLAgent, convert_to_coreml, get_coreml_agent
from .mlx_inference import MLXInference, get_mlx_inference
from .apple_shortcuts import ShortcutsIntegration, create_shortcut
from .system_integration import (
    AppleIntelligenceHub,
    get_apple_hub,
    WritingToolsProvider,
    SiriIntentHandler,
)
from .smart_router import (
    SmartAppleRouter,
    get_smart_router,
    get_apple_hardware_info,
    TaskComplexity,
    ModelTier,
    RoutingDecision,
)

__all__ = [
    # Core ML
    "CoreMLAgent",
    "convert_to_coreml",
    "get_coreml_agent",
    # MLX
    "MLXInference",
    "get_mlx_inference",
    # Shortcuts
    "ShortcutsIntegration",
    "create_shortcut",
    # System Integration
    "AppleIntelligenceHub",
    "get_apple_hub",
    "WritingToolsProvider",
    "SiriIntentHandler",
    # Smart Router
    "SmartAppleRouter",
    "get_smart_router",
    "get_apple_hardware_info",
    "TaskComplexity",
    "ModelTier",
    "RoutingDecision",
]
