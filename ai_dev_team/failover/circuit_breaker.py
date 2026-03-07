"""
Circuit Breaker - Prevents cascading failures
=============================================

Implements the circuit breaker pattern to protect against
repeated failures to unhealthy AI models.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, requests blocked
- HALF_OPEN: Testing if service recovered

Based on AI Team consensus recommendations.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for a circuit"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    opened_at: Optional[float] = None
    half_open_at: Optional[float] = None

    # Configuration
    failure_threshold: int = 5
    success_threshold: int = 3  # Successes needed in HALF_OPEN to close
    reset_timeout: float = 60.0  # Seconds before trying HALF_OPEN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": datetime.fromtimestamp(self.last_failure_time, timezone.utc).isoformat() if self.last_failure_time else None,
            "last_success_time": datetime.fromtimestamp(self.last_success_time, timezone.utc).isoformat() if self.last_success_time else None,
            "opened_at": datetime.fromtimestamp(self.opened_at, timezone.utc).isoformat() if self.opened_at else None,
        }


class CircuitBreaker:
    """
    Circuit breaker implementation for AI model calls.

    Prevents cascading failures by temporarily blocking
    requests to failing services.

    Usage:
        breaker = CircuitBreaker()

        if breaker.can_execute("gpt-4"):
            try:
                result = await call_model()
                breaker.record_success("gpt-4")
            except Exception as e:
                breaker.record_failure("gpt-4", str(e))
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        reset_timeout: float = 60.0,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            success_threshold: Successes in HALF_OPEN to close circuit
            reset_timeout: Seconds before transitioning OPEN -> HALF_OPEN
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.reset_timeout = reset_timeout

        self._circuits: Dict[str, CircuitStats] = {}

    def _get_circuit(self, model_name: str) -> CircuitStats:
        """Get or create circuit for a model"""
        if model_name not in self._circuits:
            self._circuits[model_name] = CircuitStats(
                failure_threshold=self.failure_threshold,
                success_threshold=self.success_threshold,
                reset_timeout=self.reset_timeout,
            )
        return self._circuits[model_name]

    def can_execute(self, model_name: str) -> bool:
        """
        Check if a request can be made to this model.

        Also handles state transitions (OPEN -> HALF_OPEN).

        Returns:
            True if request is allowed, False if circuit is open
        """
        circuit = self._get_circuit(model_name)
        now = time.time()

        if circuit.state == CircuitState.CLOSED:
            return True

        elif circuit.state == CircuitState.OPEN:
            # Check if reset timeout has passed
            if circuit.opened_at and (now - circuit.opened_at) >= circuit.reset_timeout:
                # Transition to HALF_OPEN
                circuit.state = CircuitState.HALF_OPEN
                circuit.half_open_at = now
                circuit.success_count = 0
                logger.info(f"Circuit {model_name}: OPEN -> HALF_OPEN (testing recovery)")
                return True
            return False

        elif circuit.state == CircuitState.HALF_OPEN:
            # Allow limited requests to test recovery
            return True

        return False

    def record_success(self, model_name: str):
        """Record a successful request"""
        circuit = self._get_circuit(model_name)
        circuit.last_success_time = time.time()

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.success_count += 1
            if circuit.success_count >= circuit.success_threshold:
                # Service recovered, close circuit
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                circuit.opened_at = None
                circuit.half_open_at = None
                logger.info(f"Circuit {model_name}: HALF_OPEN -> CLOSED (recovered)")

        elif circuit.state == CircuitState.CLOSED:
            # Reset failure count on success
            circuit.failure_count = 0

    def record_failure(self, model_name: str, error: Optional[str] = None):
        """Record a failed request"""
        circuit = self._get_circuit(model_name)
        circuit.failure_count += 1
        circuit.last_failure_time = time.time()

        if circuit.state == CircuitState.HALF_OPEN:
            # Failed during recovery test, reopen circuit
            circuit.state = CircuitState.OPEN
            circuit.opened_at = time.time()
            circuit.success_count = 0
            logger.warning(f"Circuit {model_name}: HALF_OPEN -> OPEN (recovery failed: {error})")

        elif circuit.state == CircuitState.CLOSED:
            if circuit.failure_count >= circuit.failure_threshold:
                # Too many failures, open circuit
                circuit.state = CircuitState.OPEN
                circuit.opened_at = time.time()
                logger.warning(f"Circuit {model_name}: CLOSED -> OPEN (threshold reached: {error})")

    def force_open(self, model_name: str, duration: Optional[float] = None):
        """Force open a circuit"""
        circuit = self._get_circuit(model_name)
        circuit.state = CircuitState.OPEN
        circuit.opened_at = time.time()
        if duration:
            circuit.reset_timeout = duration
        logger.warning(f"Circuit {model_name}: FORCED OPEN")

    def force_close(self, model_name: str):
        """Force close a circuit"""
        circuit = self._get_circuit(model_name)
        circuit.state = CircuitState.CLOSED
        circuit.failure_count = 0
        circuit.opened_at = None
        circuit.half_open_at = None
        logger.info(f"Circuit {model_name}: FORCED CLOSED")

    def get_state(self, model_name: str) -> CircuitState:
        """Get current state of a circuit"""
        circuit = self._get_circuit(model_name)
        # Check for state transitions
        self.can_execute(model_name)
        return circuit.state

    def get_stats(self, model_name: str) -> CircuitStats:
        """Get statistics for a circuit"""
        return self._get_circuit(model_name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuits"""
        return {name: circuit.to_dict() for name, circuit in self._circuits.items()}

    def reset(self, model_name: str):
        """Reset a circuit to initial state"""
        if model_name in self._circuits:
            del self._circuits[model_name]
        logger.info(f"Circuit {model_name}: RESET")

    def reset_all(self):
        """Reset all circuits"""
        self._circuits.clear()
        logger.info("All circuits reset")


# Global instance
_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get or create the global circuit breaker"""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker
