"""
AI Team Platform - Monitoring & Intelligence System
====================================================

Self-sustaining monitoring, health checks, and Apple Intelligence integration.
"""

from .system_monitor import SystemMonitor, ResourceStatus, ResourceAlert
from .health_check import HealthChecker, AgentHealth, SystemHealth
from .apple_intelligence import AppleIntelligence, NotificationPriority
from .apple_coreml import (
    AppleCoreMLIntegration,
    MLXModel,
    MLXResult,
    VisionResult,
    get_apple_coreml,
)
from .auto_recovery import AutoRecovery, RecoveryAction
from .performance import PerformanceOptimizer, CacheManager
from .control_center import ControlCenter, ControlCenterConfig
from .resource_manager import (
    ResourceManager,
    RateLimiter,
    CostTracker,
    IdleManager,
    RateLimitConfig
)

__all__ = [
    # System Monitoring
    "SystemMonitor",
    "ResourceStatus",
    "ResourceAlert",
    # Health Checks
    "HealthChecker",
    "AgentHealth",
    "SystemHealth",
    # Apple Intelligence (Notifications)
    "AppleIntelligence",
    "NotificationPriority",
    # Apple Core ML (Neural Engine)
    "AppleCoreMLIntegration",
    "MLXModel",
    "MLXResult",
    "VisionResult",
    "get_apple_coreml",
    # Auto Recovery
    "AutoRecovery",
    "RecoveryAction",
    # Performance
    "PerformanceOptimizer",
    "CacheManager",
    # Control Center
    "ControlCenter",
    "ControlCenterConfig",
    # Resource Management
    "ResourceManager",
    "RateLimiter",
    "CostTracker",
    "IdleManager",
    "RateLimitConfig",
]
