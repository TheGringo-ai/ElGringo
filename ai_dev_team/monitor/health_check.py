"""
AI Agent Health Check System
============================

Monitors the health and availability of all AI agents.
Detects failures, latency issues, and API problems.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents import AIAgent

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Agent health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class AgentHealth:
    """Health status of a single agent"""
    agent_name: str
    status: HealthStatus
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    success_rate: float = 100.0
    avg_response_time_ms: float = 0.0

    @property
    def is_available(self) -> bool:
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "is_available": self.is_available,
            "last_check": self.last_check.isoformat(),
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "consecutive_failures": self.consecutive_failures,
            "success_rate": self.success_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
        }


@dataclass
class SystemHealth:
    """Overall system health"""
    status: HealthStatus
    agents: Dict[str, AgentHealth]
    total_agents: int
    healthy_agents: int
    degraded_agents: int
    offline_agents: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def availability_percent(self) -> float:
        if self.total_agents == 0:
            return 0.0
        return ((self.healthy_agents + self.degraded_agents) / self.total_agents) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "total_agents": self.total_agents,
            "healthy_agents": self.healthy_agents,
            "degraded_agents": self.degraded_agents,
            "offline_agents": self.offline_agents,
            "availability_percent": self.availability_percent,
            "timestamp": self.timestamp.isoformat(),
            "agents": {name: health.to_dict() for name, health in self.agents.items()},
        }


class HealthChecker:
    """
    AI Agent Health Checker

    Performs periodic health checks on all AI agents,
    tracks their availability, and triggers recovery actions.
    """

    # Thresholds
    HEALTHY_RESPONSE_TIME_MS = 5000  # 5 seconds
    DEGRADED_RESPONSE_TIME_MS = 15000  # 15 seconds
    FAILURE_THRESHOLD = 3  # consecutive failures before marking offline

    def __init__(
        self,
        check_interval: float = 60.0,  # seconds
        timeout: float = 30.0,  # seconds per health check
    ):
        self.check_interval = check_interval
        self.timeout = timeout

        self._agents: Dict[str, "AIAgent"] = {}
        self._health_status: Dict[str, AgentHealth] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[str, AgentHealth], None]] = []
        self._check_history: Dict[str, List[Dict[str, Any]]] = {}
        self._max_history = 100

    def register_agent(self, name: str, agent: "AIAgent"):
        """Register an agent for health monitoring"""
        self._agents[name] = agent
        self._health_status[name] = AgentHealth(
            agent_name=name,
            status=HealthStatus.UNKNOWN,
            last_check=datetime.now(timezone.utc),
        )
        self._check_history[name] = []
        logger.info(f"Registered agent for health monitoring: {name}")

    def unregister_agent(self, name: str):
        """Unregister an agent"""
        self._agents.pop(name, None)
        self._health_status.pop(name, None)
        self._check_history.pop(name, None)

    def add_callback(self, callback: Callable[[str, AgentHealth], None]):
        """Add callback for health status changes"""
        self._callbacks.append(callback)

    async def check_agent(self, name: str) -> AgentHealth:
        """Check health of a specific agent"""
        if name not in self._agents:
            return AgentHealth(
                agent_name=name,
                status=HealthStatus.UNKNOWN,
                last_check=datetime.now(timezone.utc),
                error_message="Agent not registered",
            )

        agent = self._agents[name]
        previous_health = self._health_status.get(name)
        start_time = time.time()

        try:
            # Simple health check - ask for availability
            is_available = await asyncio.wait_for(
                agent.is_available(),
                timeout=self.timeout
            )

            response_time_ms = (time.time() - start_time) * 1000

            if not is_available:
                health = AgentHealth(
                    agent_name=name,
                    status=HealthStatus.OFFLINE,
                    last_check=datetime.now(timezone.utc),
                    error_message="Agent reports unavailable (API key missing?)",
                    consecutive_failures=(previous_health.consecutive_failures if previous_health else 0) + 1,
                )
            elif response_time_ms > self.DEGRADED_RESPONSE_TIME_MS:
                health = AgentHealth(
                    agent_name=name,
                    status=HealthStatus.DEGRADED,
                    last_check=datetime.now(timezone.utc),
                    response_time_ms=response_time_ms,
                    consecutive_failures=0,
                )
            elif response_time_ms > self.HEALTHY_RESPONSE_TIME_MS:
                health = AgentHealth(
                    agent_name=name,
                    status=HealthStatus.DEGRADED,
                    last_check=datetime.now(timezone.utc),
                    response_time_ms=response_time_ms,
                    consecutive_failures=0,
                )
            else:
                health = AgentHealth(
                    agent_name=name,
                    status=HealthStatus.HEALTHY,
                    last_check=datetime.now(timezone.utc),
                    response_time_ms=response_time_ms,
                    consecutive_failures=0,
                )

        except asyncio.TimeoutError:
            health = AgentHealth(
                agent_name=name,
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(timezone.utc),
                error_message=f"Health check timed out after {self.timeout}s",
                consecutive_failures=(previous_health.consecutive_failures if previous_health else 0) + 1,
            )
        except Exception as e:
            health = AgentHealth(
                agent_name=name,
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(timezone.utc),
                error_message=str(e),
                consecutive_failures=(previous_health.consecutive_failures if previous_health else 0) + 1,
            )

        # Mark as offline if too many consecutive failures
        if health.consecutive_failures >= self.FAILURE_THRESHOLD:
            health.status = HealthStatus.OFFLINE

        # Calculate success rate and avg response time from history
        self._update_history(name, health)
        health.success_rate = self._calculate_success_rate(name)
        health.avg_response_time_ms = self._calculate_avg_response_time(name)

        # Store and notify
        self._health_status[name] = health

        # Notify callbacks if status changed
        if previous_health and previous_health.status != health.status:
            for callback in self._callbacks:
                try:
                    callback(name, health)
                except Exception as e:
                    logger.error(f"Health callback error: {e}")

        return health

    def _update_history(self, name: str, health: AgentHealth):
        """Update health check history"""
        self._check_history[name].append({
            "status": health.status.value,
            "response_time_ms": health.response_time_ms,
            "timestamp": health.last_check.isoformat(),
            "success": health.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED),
        })

        # Trim history
        if len(self._check_history[name]) > self._max_history:
            self._check_history[name] = self._check_history[name][-self._max_history:]

    def _calculate_success_rate(self, name: str) -> float:
        """Calculate success rate from recent history"""
        history = self._check_history.get(name, [])
        if not history:
            return 100.0

        recent = history[-20:]  # Last 20 checks
        successes = sum(1 for h in recent if h["success"])
        return (successes / len(recent)) * 100

    def _calculate_avg_response_time(self, name: str) -> float:
        """Calculate average response time from recent history"""
        history = self._check_history.get(name, [])
        if not history:
            return 0.0

        recent = history[-20:]
        times = [h["response_time_ms"] for h in recent if h["response_time_ms"] is not None]
        return sum(times) / len(times) if times else 0.0

    async def check_all_agents(self) -> SystemHealth:
        """Check health of all registered agents"""
        tasks = [self.check_agent(name) for name in self._agents.keys()]
        await asyncio.gather(*tasks, return_exceptions=True)

        return self.get_system_health()

    def get_system_health(self) -> SystemHealth:
        """Get overall system health"""
        agents = self._health_status

        healthy = sum(1 for h in agents.values() if h.status == HealthStatus.HEALTHY)
        degraded = sum(1 for h in agents.values() if h.status == HealthStatus.DEGRADED)
        offline = sum(1 for h in agents.values() if h.status in (HealthStatus.UNHEALTHY, HealthStatus.OFFLINE))

        # Determine overall status
        if offline > 0 and healthy == 0:
            overall = HealthStatus.OFFLINE
        elif offline > 0 or degraded > healthy:
            overall = HealthStatus.DEGRADED
        elif healthy > 0:
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.UNKNOWN

        return SystemHealth(
            status=overall,
            agents=agents,
            total_agents=len(agents),
            healthy_agents=healthy,
            degraded_agents=degraded,
            offline_agents=offline,
        )

    async def start(self):
        """Start periodic health checking"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info("Health checker started")

    async def stop(self):
        """Stop health checking"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health checker stopped")

    async def _check_loop(self):
        """Main health check loop"""
        while self._running:
            try:
                await self.check_all_agents()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.check_interval)

    def get_agent_health(self, name: str) -> Optional[AgentHealth]:
        """Get health status of specific agent"""
        return self._health_status.get(name)

    def print_health_report(self):
        """Print health report to console"""
        health = self.get_system_health()

        print("\n" + "=" * 60)
        print("  AI AGENT HEALTH REPORT")
        print("=" * 60)

        status_icon = {
            HealthStatus.HEALTHY: "[OK]",
            HealthStatus.DEGRADED: "[!!]",
            HealthStatus.UNHEALTHY: "[XX]",
            HealthStatus.OFFLINE: "[--]",
            HealthStatus.UNKNOWN: "[??]",
        }

        print(f"\n  Overall Status: {status_icon[health.status]} {health.status.value.upper()}")
        print(f"  Availability: {health.availability_percent:.0f}%")
        print(f"  Agents: {health.healthy_agents} healthy, {health.degraded_agents} degraded, {health.offline_agents} offline")

        print("\n  Agent Details:")
        print("-" * 60)

        for name, agent_health in health.agents.items():
            icon = status_icon[agent_health.status]
            rt = f"{agent_health.avg_response_time_ms:.0f}ms" if agent_health.avg_response_time_ms else "N/A"
            sr = f"{agent_health.success_rate:.0f}%"
            print(f"  {icon} {name:20} | Response: {rt:>8} | Success: {sr:>4}")
            if agent_health.error_message:
                print(f"       Error: {agent_health.error_message[:50]}")

        print("=" * 60)
