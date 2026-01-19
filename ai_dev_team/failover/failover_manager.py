"""
Failover Manager - Automatic retry with fallback models
=======================================================

Manages automatic failover when AI models fail or timeout.
Uses health data and circuit breakers for smart retry decisions.

Based on AI Team consensus recommendations.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic

from ..monitoring import get_health_monitor, HealthStatus
from .circuit_breaker import get_circuit_breaker, CircuitState

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class FailoverResult(Generic[T]):
    """Result of a failover-protected operation"""
    success: bool
    result: Optional[T] = None
    error: Optional[str] = None
    model_used: Optional[str] = None
    attempts: int = 0
    models_tried: List[str] = None
    total_time: float = 0.0

    def __post_init__(self):
        if self.models_tried is None:
            self.models_tried = []


class FailoverManager:
    """
    Manages automatic failover for AI model calls.

    Features:
    - Automatic retry with next-best model on failure
    - Circuit breaker integration to skip unhealthy models
    - Health monitoring integration for smart model selection
    - Configurable retry strategies
    - Timeout handling

    Usage:
        manager = FailoverManager(available_models=["gpt-4", "claude", "gemini"])

        result = await manager.execute_with_failover(
            operation=lambda model: call_ai_model(model, prompt),
            task_type="coding",
        )

        if result.success:
            print(f"Success with {result.model_used}: {result.result}")
        else:
            print(f"All models failed: {result.error}")
    """

    def __init__(
        self,
        available_models: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout_seconds: float = 120.0,
        retry_delay: float = 1.0,
        exponential_backoff: bool = True,
    ):
        """
        Initialize failover manager.

        Args:
            available_models: List of model names to try
            max_retries: Maximum number of models to try
            timeout_seconds: Timeout per model attempt
            retry_delay: Base delay between retries
            exponential_backoff: Whether to use exponential backoff
        """
        self.available_models = available_models or []
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff

        self._health_monitor = get_health_monitor()
        self._circuit_breaker = get_circuit_breaker()

    def set_available_models(self, models: List[str]):
        """Update the list of available models"""
        self.available_models = models

    def get_ordered_models(
        self,
        task_type: Optional[str] = None,
        preferred_model: Optional[str] = None,
    ) -> List[str]:
        """
        Get models ordered by health and suitability.

        Args:
            task_type: Type of task for performance-based ordering
            preferred_model: Model to try first if healthy

        Returns:
            List of model names, healthiest first
        """
        if not self.available_models:
            return []

        # Start with healthy models from health monitor
        healthy_models = self._health_monitor.get_healthy_models(self.available_models)

        # Filter out models with open circuits
        available = []
        for model in healthy_models:
            if self._circuit_breaker.can_execute(model):
                available.append(model)

        # Move preferred model to front if specified and available
        if preferred_model and preferred_model in available:
            available.remove(preferred_model)
            available.insert(0, preferred_model)

        # Add unhealthy models at the end (last resort)
        for model in self.available_models:
            if model not in available:
                # Only add if circuit allows
                if self._circuit_breaker.can_execute(model):
                    available.append(model)

        return available

    async def execute_with_failover(
        self,
        operation: Callable[[str], Any],
        task_type: Optional[str] = None,
        preferred_model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailoverResult:
        """
        Execute an operation with automatic failover.

        Args:
            operation: Async function that takes model_name and returns result
            task_type: Type of task for model selection
            preferred_model: Model to try first
            context: Additional context for logging

        Returns:
            FailoverResult with outcome details
        """
        start_time = time.time()
        models_to_try = self.get_ordered_models(task_type, preferred_model)

        if not models_to_try:
            return FailoverResult(
                success=False,
                error="No available models to try",
                attempts=0,
                total_time=time.time() - start_time,
            )

        models_tried = []
        last_error = None

        for attempt, model_name in enumerate(models_to_try[:self.max_retries]):
            models_tried.append(model_name)
            attempt_start = time.time()

            try:
                logger.info(f"Failover attempt {attempt + 1}/{self.max_retries}: trying {model_name}")

                # Execute with timeout
                if asyncio.iscoroutinefunction(operation):
                    result = await asyncio.wait_for(
                        operation(model_name),
                        timeout=self.timeout_seconds,
                    )
                else:
                    result = operation(model_name)

                # Success!
                latency = time.time() - attempt_start
                self._health_monitor.record_request(model_name, latency, success=True)
                self._circuit_breaker.record_success(model_name)

                logger.info(f"Failover success with {model_name} (attempt {attempt + 1})")

                return FailoverResult(
                    success=True,
                    result=result,
                    model_used=model_name,
                    attempts=attempt + 1,
                    models_tried=models_tried,
                    total_time=time.time() - start_time,
                )

            except asyncio.TimeoutError:
                latency = time.time() - attempt_start
                last_error = f"Timeout after {self.timeout_seconds}s"
                self._health_monitor.record_request(
                    model_name, latency, success=False,
                    error_type="timeout", error_message=last_error
                )
                self._circuit_breaker.record_failure(model_name, last_error)
                logger.warning(f"Failover timeout for {model_name}: {last_error}")

            except Exception as e:
                latency = time.time() - attempt_start
                last_error = str(e)
                error_type = type(e).__name__
                self._health_monitor.record_request(
                    model_name, latency, success=False,
                    error_type=error_type, error_message=last_error
                )
                self._circuit_breaker.record_failure(model_name, last_error)
                logger.warning(f"Failover error for {model_name}: {error_type}: {last_error}")

            # Delay before next retry
            if attempt < len(models_to_try) - 1:
                delay = self.retry_delay
                if self.exponential_backoff:
                    delay *= (2 ** attempt)
                await asyncio.sleep(min(delay, 10.0))  # Cap at 10 seconds

        # All models failed
        return FailoverResult(
            success=False,
            error=f"All {len(models_tried)} models failed. Last error: {last_error}",
            attempts=len(models_tried),
            models_tried=models_tried,
            total_time=time.time() - start_time,
        )

    async def execute_with_fallback(
        self,
        primary_operation: Callable[[], Any],
        fallback_operation: Callable[[], Any],
        primary_model: str,
    ) -> FailoverResult:
        """
        Execute with a specific fallback operation.

        Args:
            primary_operation: Primary operation to try
            fallback_operation: Fallback if primary fails
            primary_model: Name of primary model for tracking

        Returns:
            FailoverResult
        """
        start_time = time.time()

        # Try primary
        try:
            if not self._circuit_breaker.can_execute(primary_model):
                raise Exception(f"Circuit open for {primary_model}")

            attempt_start = time.time()

            if asyncio.iscoroutinefunction(primary_operation):
                result = await asyncio.wait_for(
                    primary_operation(),
                    timeout=self.timeout_seconds,
                )
            else:
                result = primary_operation()

            latency = time.time() - attempt_start
            self._health_monitor.record_request(primary_model, latency, success=True)
            self._circuit_breaker.record_success(primary_model)

            return FailoverResult(
                success=True,
                result=result,
                model_used=primary_model,
                attempts=1,
                models_tried=[primary_model],
                total_time=time.time() - start_time,
            )

        except Exception as primary_error:
            logger.warning(f"Primary operation failed: {primary_error}, trying fallback")

            # Record failure
            self._health_monitor.record_request(
                primary_model, time.time() - start_time, success=False,
                error_type=type(primary_error).__name__,
                error_message=str(primary_error),
            )
            self._circuit_breaker.record_failure(primary_model, str(primary_error))

        # Try fallback
        try:
            if asyncio.iscoroutinefunction(fallback_operation):
                result = await fallback_operation()
            else:
                result = fallback_operation()

            return FailoverResult(
                success=True,
                result=result,
                model_used="fallback",
                attempts=2,
                models_tried=[primary_model, "fallback"],
                total_time=time.time() - start_time,
            )

        except Exception as fallback_error:
            return FailoverResult(
                success=False,
                error=f"Both primary and fallback failed. Fallback error: {fallback_error}",
                attempts=2,
                models_tried=[primary_model, "fallback"],
                total_time=time.time() - start_time,
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get failover statistics"""
        health_stats = self._health_monitor.get_statistics()
        circuit_stats = self._circuit_breaker.get_all_stats()

        return {
            "available_models": self.available_models,
            "healthy_models": self._health_monitor.get_healthy_models(self.available_models),
            "health": health_stats,
            "circuits": circuit_stats,
            "config": {
                "max_retries": self.max_retries,
                "timeout_seconds": self.timeout_seconds,
                "retry_delay": self.retry_delay,
                "exponential_backoff": self.exponential_backoff,
            },
        }


# Global instance
_failover_manager: Optional[FailoverManager] = None


def get_failover_manager() -> FailoverManager:
    """Get or create the global failover manager"""
    global _failover_manager
    if _failover_manager is None:
        _failover_manager = FailoverManager()
    return _failover_manager
