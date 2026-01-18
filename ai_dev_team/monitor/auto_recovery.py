"""
Auto-Recovery and Self-Healing System
=====================================

Automatically recovers from failures, restarts services,
and maintains system stability without human intervention.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..orchestrator import AIDevTeam

logger = logging.getLogger(__name__)


class RecoveryAction(Enum):
    """Types of recovery actions"""
    RESTART_AGENT = "restart_agent"
    CLEAR_CACHE = "clear_cache"
    RESET_CONNECTION = "reset_connection"
    FALLBACK_AGENT = "fallback_agent"
    REDUCE_LOAD = "reduce_load"
    ALERT_USER = "alert_user"
    NO_ACTION = "no_action"


@dataclass
class RecoveryEvent:
    """Record of a recovery action"""
    action: RecoveryAction
    target: str
    reason: str
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryPolicy:
    """Policy for automatic recovery"""
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 60.0
    cooldown_seconds: float = 300.0  # 5 minutes between recovery attempts


class AutoRecovery:
    """
    Self-Healing System

    Monitors for failures and automatically:
    - Restarts failed agents
    - Clears stuck caches
    - Falls back to alternative agents
    - Reduces load under pressure
    - Alerts when human intervention needed
    """

    def __init__(
        self,
        team: Optional["AIDevTeam"] = None,
        policy: Optional[RecoveryPolicy] = None,
    ):
        self.team = team
        self.policy = policy or RecoveryPolicy()

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._recovery_history: List[RecoveryEvent] = []
        self._last_recovery: Dict[str, float] = {}
        self._failure_counts: Dict[str, int] = {}
        self._callbacks: List[Callable[[RecoveryEvent], None]] = []
        self._max_history = 500

    def set_team(self, team: "AIDevTeam"):
        """Set the AI team to monitor"""
        self.team = team

    def add_callback(self, callback: Callable[[RecoveryEvent], None]):
        """Add callback for recovery events"""
        self._callbacks.append(callback)

    async def handle_agent_failure(
        self,
        agent_name: str,
        error: Optional[str] = None
    ) -> RecoveryEvent:
        """
        Handle an agent failure with automatic recovery

        Recovery strategy:
        1. Check cooldown - don't retry too frequently
        2. Increment failure count
        3. Try to restart/reconnect agent
        4. If repeated failures, fall back to alternative agent
        5. If no alternatives, alert user
        """
        now = time.time()

        # Check cooldown
        last_recovery = self._last_recovery.get(agent_name, 0)
        if now - last_recovery < self.policy.cooldown_seconds:
            logger.info(f"Skipping recovery for {agent_name} - in cooldown")
            return RecoveryEvent(
                action=RecoveryAction.NO_ACTION,
                target=agent_name,
                reason="In cooldown period",
                success=True,
            )

        # Increment failure count
        self._failure_counts[agent_name] = self._failure_counts.get(agent_name, 0) + 1
        failure_count = self._failure_counts[agent_name]

        logger.warning(f"Agent {agent_name} failure #{failure_count}: {error}")

        # Determine recovery action
        if failure_count <= self.policy.max_retries:
            # Try to restart agent
            event = await self._restart_agent(agent_name, error)
        else:
            # Too many failures - try fallback
            event = await self._fallback_to_alternative(agent_name, error)

        # Update tracking
        self._last_recovery[agent_name] = now
        self._recovery_history.append(event)

        if len(self._recovery_history) > self._max_history:
            self._recovery_history = self._recovery_history[-self._max_history:]

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Recovery callback error: {e}")

        return event

    async def _restart_agent(self, agent_name: str, error: Optional[str]) -> RecoveryEvent:
        """Attempt to restart an agent"""
        try:
            if not self.team:
                return RecoveryEvent(
                    action=RecoveryAction.RESTART_AGENT,
                    target=agent_name,
                    reason=f"Restart failed: No team configured",
                    success=False,
                )

            agent = self.team.agents.get(agent_name)
            if not agent:
                return RecoveryEvent(
                    action=RecoveryAction.RESTART_AGENT,
                    target=agent_name,
                    reason=f"Agent not found",
                    success=False,
                )

            # Clear conversation history (soft reset)
            agent.clear_history()

            # Try to verify agent is responsive
            is_available = await agent.is_available()

            if is_available:
                # Reset failure count on success
                self._failure_counts[agent_name] = 0

                return RecoveryEvent(
                    action=RecoveryAction.RESTART_AGENT,
                    target=agent_name,
                    reason=f"Agent restarted successfully after: {error}",
                    success=True,
                )
            else:
                return RecoveryEvent(
                    action=RecoveryAction.RESTART_AGENT,
                    target=agent_name,
                    reason=f"Agent restart failed - still unavailable",
                    success=False,
                )

        except Exception as e:
            return RecoveryEvent(
                action=RecoveryAction.RESTART_AGENT,
                target=agent_name,
                reason=f"Restart exception: {e}",
                success=False,
            )

    async def _fallback_to_alternative(
        self,
        failed_agent: str,
        error: Optional[str]
    ) -> RecoveryEvent:
        """Fall back to an alternative agent"""
        if not self.team:
            return RecoveryEvent(
                action=RecoveryAction.FALLBACK_AGENT,
                target=failed_agent,
                reason="No team configured for fallback",
                success=False,
            )

        # Find alternative agents
        alternatives = [
            name for name, agent in self.team.agents.items()
            if name != failed_agent
        ]

        if not alternatives:
            return RecoveryEvent(
                action=RecoveryAction.ALERT_USER,
                target=failed_agent,
                reason=f"No alternative agents available. Original error: {error}",
                success=False,
                details={"requires_human": True},
            )

        # Check which alternatives are available
        for alt_name in alternatives:
            alt_agent = self.team.agents[alt_name]
            try:
                if await alt_agent.is_available():
                    logger.info(f"Falling back from {failed_agent} to {alt_name}")
                    return RecoveryEvent(
                        action=RecoveryAction.FALLBACK_AGENT,
                        target=failed_agent,
                        reason=f"Switched to {alt_name} after failures",
                        success=True,
                        details={"fallback_agent": alt_name},
                    )
            except Exception:
                continue

        return RecoveryEvent(
            action=RecoveryAction.ALERT_USER,
            target=failed_agent,
            reason="All agents unavailable",
            success=False,
            details={"requires_human": True},
        )

    async def handle_memory_pressure(self, memory_percent: float) -> RecoveryEvent:
        """Handle high memory usage"""
        if memory_percent < 80:
            return RecoveryEvent(
                action=RecoveryAction.NO_ACTION,
                target="system",
                reason="Memory within acceptable range",
                success=True,
            )

        logger.warning(f"Memory pressure detected: {memory_percent:.1f}%")

        # Clear caches
        cleared = await self._clear_caches()

        if cleared:
            return RecoveryEvent(
                action=RecoveryAction.CLEAR_CACHE,
                target="system",
                reason=f"Cleared caches due to {memory_percent:.1f}% memory usage",
                success=True,
            )
        else:
            return RecoveryEvent(
                action=RecoveryAction.ALERT_USER,
                target="system",
                reason=f"Memory at {memory_percent:.1f}% - manual intervention may be needed",
                success=False,
                details={"requires_human": True},
            )

    async def _clear_caches(self) -> bool:
        """Clear all caches to free memory"""
        try:
            if self.team:
                # Clear agent conversation histories
                for agent in self.team.agents.values():
                    agent.clear_history()

                # Clear collaboration engine cache if present
                if hasattr(self.team, '_collaboration_engine') and self.team._collaboration_engine:
                    if hasattr(self.team._collaboration_engine, 'clear_cache'):
                        self.team._collaboration_engine.clear_cache()

            logger.info("Caches cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear caches: {e}")
            return False

    async def health_check_recovery(
        self,
        agent_name: str,
        health_status: str
    ) -> Optional[RecoveryEvent]:
        """Handle health check failures"""
        if health_status in ("healthy", "degraded"):
            # Agent recovered on its own
            if agent_name in self._failure_counts and self._failure_counts[agent_name] > 0:
                self._failure_counts[agent_name] = 0
                return RecoveryEvent(
                    action=RecoveryAction.NO_ACTION,
                    target=agent_name,
                    reason="Agent recovered automatically",
                    success=True,
                )
            return None

        # Agent is unhealthy or offline
        return await self.handle_agent_failure(
            agent_name,
            f"Health check status: {health_status}"
        )

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        recent = self._recovery_history[-100:] if self._recovery_history else []

        total = len(recent)
        successful = sum(1 for e in recent if e.success)
        by_action = {}

        for event in recent:
            action = event.action.value
            if action not in by_action:
                by_action[action] = {"total": 0, "success": 0}
            by_action[action]["total"] += 1
            if event.success:
                by_action[action]["success"] += 1

        return {
            "total_recoveries": total,
            "successful": successful,
            "success_rate": (successful / total * 100) if total > 0 else 100,
            "by_action": by_action,
            "current_failure_counts": dict(self._failure_counts),
            "recent_events": [
                {
                    "action": e.action.value,
                    "target": e.target,
                    "success": e.success,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in recent[-10:]
            ],
        }

    def print_recovery_report(self):
        """Print recovery statistics"""
        stats = self.get_recovery_stats()

        print("\n" + "=" * 50)
        print("  AUTO-RECOVERY REPORT")
        print("=" * 50)

        print(f"\n  Total Recoveries: {stats['total_recoveries']}")
        print(f"  Success Rate: {stats['success_rate']:.0f}%")

        if stats['by_action']:
            print("\n  By Action Type:")
            for action, data in stats['by_action'].items():
                rate = (data['success'] / data['total'] * 100) if data['total'] > 0 else 0
                print(f"    {action}: {data['total']} attempts, {rate:.0f}% success")

        if stats['current_failure_counts']:
            print("\n  Current Failure Counts:")
            for agent, count in stats['current_failure_counts'].items():
                print(f"    {agent}: {count}")

        print("=" * 50)
