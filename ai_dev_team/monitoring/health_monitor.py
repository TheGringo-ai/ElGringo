"""
Model Health Monitor - Real-time health tracking for AI models
==============================================================

Tracks API latency, error rates, and availability for all AI models.
Provides health status for intelligent routing and failover decisions.

Based on AI Team consensus recommendations.
"""

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Model health status levels"""
    HEALTHY = "healthy"           # Normal operation
    DEGRADED = "degraded"         # Slow or occasional errors
    UNHEALTHY = "unhealthy"       # Frequent errors, avoid if possible
    UNAVAILABLE = "unavailable"   # Circuit open, do not use


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    latency: float  # seconds
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ModelHealth:
    """Health status for a single model"""
    model_name: str
    status: HealthStatus = HealthStatus.HEALTHY

    # Recent metrics (sliding window)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Latency stats
    avg_latency: float = 0.0
    min_latency: float = float('inf')
    max_latency: float = 0.0
    p95_latency: float = 0.0

    # Error tracking
    error_rate: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[str] = None
    consecutive_failures: int = 0

    # Availability
    last_success_time: Optional[str] = None
    last_check_time: Optional[str] = None
    uptime_percentage: float = 100.0

    # Circuit breaker state
    circuit_open: bool = False
    circuit_open_until: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "status": self.status.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "avg_latency": round(self.avg_latency, 3),
            "min_latency": round(self.min_latency, 3) if self.min_latency != float('inf') else None,
            "max_latency": round(self.max_latency, 3),
            "p95_latency": round(self.p95_latency, 3),
            "error_rate": round(self.error_rate, 4),
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
            "consecutive_failures": self.consecutive_failures,
            "last_success_time": self.last_success_time,
            "uptime_percentage": round(self.uptime_percentage, 2),
            "circuit_open": self.circuit_open,
            "circuit_open_until": self.circuit_open_until,
        }


class HealthMonitor:
    """
    Real-time health monitoring for AI models.

    Features:
    - Tracks latency, errors, and availability per model
    - Sliding window metrics (last N requests)
    - Automatic health status calculation
    - Circuit breaker state management
    - Persistence across sessions
    """

    def __init__(
        self,
        storage_dir: str = "~/.ai-dev-team/health",
        window_size: int = 100,  # Keep last 100 requests per model
        degraded_error_rate: float = 0.1,  # 10% errors = degraded
        unhealthy_error_rate: float = 0.3,  # 30% errors = unhealthy
        degraded_latency: float = 10.0,  # 10s avg = degraded
        unhealthy_latency: float = 30.0,  # 30s avg = unhealthy
    ):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.window_size = window_size
        self.degraded_error_rate = degraded_error_rate
        self.unhealthy_error_rate = unhealthy_error_rate
        self.degraded_latency = degraded_latency
        self.unhealthy_latency = unhealthy_latency

        # Metrics storage: model_name -> deque of MetricPoints
        self._metrics: Dict[str, Deque[MetricPoint]] = {}

        # Health status cache
        self._health: Dict[str, ModelHealth] = {}

        # Circuit breaker state
        self._circuit_failures: Dict[str, int] = {}
        self._circuit_open_until: Dict[str, datetime] = {}

        self._load_data()

    def _load_data(self):
        """Load health data from disk"""
        try:
            health_file = self.storage_dir / "health_state.json"
            if health_file.exists():
                with open(health_file) as f:
                    data = json.load(f)
                    for model_name, health_data in data.get("health", {}).items():
                        # Reconstruct health status
                        health_data["status"] = HealthStatus(health_data.get("status", "healthy"))
                        self._health[model_name] = ModelHealth(**health_data)

                    self._circuit_failures = data.get("circuit_failures", {})

                    # Reconstruct circuit open times
                    for model, time_str in data.get("circuit_open_until", {}).items():
                        if time_str:
                            self._circuit_open_until[model] = datetime.fromisoformat(time_str)

                logger.info(f"Loaded health data for {len(self._health)} models")
        except Exception as e:
            logger.warning(f"Error loading health data: {e}")

    def _save_data(self):
        """Save health data to disk"""
        try:
            data = {
                "health": {
                    name: {**health.to_dict(), "status": health.status.value}
                    for name, health in self._health.items()
                },
                "circuit_failures": self._circuit_failures,
                "circuit_open_until": {
                    model: time.isoformat() if time else None
                    for model, time in self._circuit_open_until.items()
                },
                "last_saved": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.storage_dir / "health_state.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving health data: {e}")

    def record_request(
        self,
        model_name: str,
        latency: float,
        success: bool,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """
        Record a request metric for a model.

        Args:
            model_name: Name of the model
            latency: Request latency in seconds
            success: Whether the request succeeded
            error_type: Type of error if failed (e.g., "timeout", "rate_limit")
            error_message: Error message if failed
        """
        # Initialize if needed
        if model_name not in self._metrics:
            self._metrics[model_name] = deque(maxlen=self.window_size)
        if model_name not in self._health:
            self._health[model_name] = ModelHealth(model_name=model_name)

        # Record metric
        metric = MetricPoint(
            timestamp=time.time(),
            latency=latency,
            success=success,
            error_type=error_type,
            error_message=error_message,
        )
        self._metrics[model_name].append(metric)

        # Update health
        self._update_health(model_name)

        # Update circuit breaker
        if success:
            self._circuit_failures[model_name] = 0
            self._health[model_name].consecutive_failures = 0
        else:
            failures = self._circuit_failures.get(model_name, 0) + 1
            self._circuit_failures[model_name] = failures
            self._health[model_name].consecutive_failures = failures
            self._health[model_name].last_error = error_message
            self._health[model_name].last_error_time = datetime.now(timezone.utc).isoformat()

        # Save periodically (every 10 requests)
        total = sum(len(m) for m in self._metrics.values())
        if total % 10 == 0:
            self._save_data()

    def _update_health(self, model_name: str):
        """Recalculate health status for a model"""
        metrics = self._metrics.get(model_name, deque())
        if not metrics:
            return

        health = self._health[model_name]

        # Calculate stats from sliding window
        latencies = [m.latency for m in metrics]
        successes = [m.success for m in metrics]

        health.total_requests = len(metrics)
        health.successful_requests = sum(successes)
        health.failed_requests = len(metrics) - health.successful_requests

        # Latency stats
        if latencies:
            health.avg_latency = sum(latencies) / len(latencies)
            health.min_latency = min(latencies)
            health.max_latency = max(latencies)
            sorted_latencies = sorted(latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            health.p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]

        # Error rate
        health.error_rate = health.failed_requests / health.total_requests if health.total_requests > 0 else 0

        # Last success time
        for m in reversed(metrics):
            if m.success:
                health.last_success_time = datetime.fromtimestamp(m.timestamp, timezone.utc).isoformat()
                break

        health.last_check_time = datetime.now(timezone.utc).isoformat()

        # Calculate uptime percentage (successes in window)
        health.uptime_percentage = (health.successful_requests / health.total_requests * 100) if health.total_requests > 0 else 100

        # Determine status
        health.status = self._calculate_status(health)

        # Check circuit breaker
        if model_name in self._circuit_open_until:
            if datetime.now(timezone.utc) < self._circuit_open_until[model_name]:
                health.circuit_open = True
                health.circuit_open_until = self._circuit_open_until[model_name].isoformat()
                health.status = HealthStatus.UNAVAILABLE
            else:
                health.circuit_open = False
                health.circuit_open_until = None
                del self._circuit_open_until[model_name]

    def _calculate_status(self, health: ModelHealth) -> HealthStatus:
        """Calculate health status based on metrics"""
        # Check error rate first
        if health.error_rate >= self.unhealthy_error_rate:
            return HealthStatus.UNHEALTHY
        elif health.error_rate >= self.degraded_error_rate:
            return HealthStatus.DEGRADED

        # Check latency
        if health.avg_latency >= self.unhealthy_latency:
            return HealthStatus.UNHEALTHY
        elif health.avg_latency >= self.degraded_latency:
            return HealthStatus.DEGRADED

        # Check consecutive failures
        if health.consecutive_failures >= 5:
            return HealthStatus.UNHEALTHY
        elif health.consecutive_failures >= 3:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def open_circuit(self, model_name: str, duration_seconds: int = 60):
        """
        Open the circuit breaker for a model.

        Args:
            model_name: Model to block
            duration_seconds: How long to keep circuit open
        """
        self._circuit_open_until[model_name] = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        if model_name in self._health:
            self._health[model_name].circuit_open = True
            self._health[model_name].circuit_open_until = self._circuit_open_until[model_name].isoformat()
            self._health[model_name].status = HealthStatus.UNAVAILABLE

        logger.warning(f"Circuit opened for {model_name} for {duration_seconds}s")
        self._save_data()

    def close_circuit(self, model_name: str):
        """Manually close the circuit breaker"""
        if model_name in self._circuit_open_until:
            del self._circuit_open_until[model_name]
        self._circuit_failures[model_name] = 0

        if model_name in self._health:
            self._health[model_name].circuit_open = False
            self._health[model_name].circuit_open_until = None
            self._health[model_name].consecutive_failures = 0
            self._update_health(model_name)

        logger.info(f"Circuit closed for {model_name}")
        self._save_data()

    def is_available(self, model_name: str) -> bool:
        """Check if a model is available for requests"""
        # Check circuit breaker
        if model_name in self._circuit_open_until:
            if datetime.now(timezone.utc) < self._circuit_open_until[model_name]:
                return False
            else:
                # Circuit timeout expired, close it
                self.close_circuit(model_name)

        # Check health status
        health = self._health.get(model_name)
        if health and health.status == HealthStatus.UNAVAILABLE:
            return False

        return True

    def get_health(self, model_name: str) -> Optional[ModelHealth]:
        """Get health status for a model"""
        return self._health.get(model_name)

    def get_all_health(self) -> Dict[str, ModelHealth]:
        """Get health status for all models"""
        return self._health.copy()

    def get_healthy_models(self, models: List[str]) -> List[str]:
        """
        Filter models to only healthy/degraded ones.

        Args:
            models: List of model names to filter

        Returns:
            List of available models, sorted by health (healthiest first)
        """
        available = []

        for model in models:
            if not self.is_available(model):
                continue

            health = self._health.get(model)
            if not health:
                # No data = assume healthy
                available.append((model, 0, 0))  # (name, status_priority, latency)
            elif health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                priority = 0 if health.status == HealthStatus.HEALTHY else 1
                available.append((model, priority, health.avg_latency))

        # Sort by status (healthy first), then by latency
        available.sort(key=lambda x: (x[1], x[2]))

        return [model for model, _, _ in available]

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall health statistics"""
        if not self._health:
            return {
                "total_models": 0,
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0,
                "unavailable": 0,
                "models": {},
            }

        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.UNAVAILABLE: 0,
        }

        for health in self._health.values():
            status_counts[health.status] += 1

        return {
            "total_models": len(self._health),
            "healthy": status_counts[HealthStatus.HEALTHY],
            "degraded": status_counts[HealthStatus.DEGRADED],
            "unhealthy": status_counts[HealthStatus.UNHEALTHY],
            "unavailable": status_counts[HealthStatus.UNAVAILABLE],
            "overall_status": self._get_overall_status(status_counts),
            "models": {name: health.to_dict() for name, health in self._health.items()},
        }

    def _get_overall_status(self, status_counts: Dict[HealthStatus, int]) -> str:
        """Determine overall system status"""
        if status_counts[HealthStatus.UNAVAILABLE] == len(self._health):
            return "critical"
        elif status_counts[HealthStatus.HEALTHY] == len(self._health):
            return "healthy"
        elif status_counts[HealthStatus.UNHEALTHY] > 0 or status_counts[HealthStatus.UNAVAILABLE] > 0:
            return "degraded"
        else:
            return "healthy"


# Global instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create the global health monitor"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
