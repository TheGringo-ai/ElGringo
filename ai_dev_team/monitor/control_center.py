"""
Unified Control Center
======================

Central command for the entire AI Dev Team platform.
Integrates all monitoring, health, recovery, and optimization systems.
"""

import asyncio
import logging
import signal
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .system_monitor import SystemMonitor, ResourceAlert, AlertLevel
from .health_check import HealthChecker, HealthStatus
from .apple_intelligence import AppleIntelligence, NotificationPriority
from .auto_recovery import AutoRecovery, RecoveryAction
from .performance import PerformanceOptimizer, CacheManager
from .resource_manager import ResourceManager, RateLimitConfig

if TYPE_CHECKING:
    from ..orchestrator import AIDevTeam

logger = logging.getLogger(__name__)


@dataclass
class ControlCenterConfig:
    """Configuration for Control Center"""
    enable_system_monitor: bool = True
    enable_health_checks: bool = True
    enable_apple_notifications: bool = True
    enable_auto_recovery: bool = True
    enable_performance_optimizer: bool = True
    enable_resource_manager: bool = True

    system_check_interval: float = 30.0  # seconds
    health_check_interval: float = 60.0  # seconds
    notify_on_warnings: bool = True
    notify_on_recovery: bool = True
    speak_critical_alerts: bool = False  # Use Siri voice for critical alerts

    # Resource management
    daily_budget_usd: float = 10.0  # Daily API cost budget
    idle_timeout_seconds: float = 300.0  # Shutdown idle agents after 5 minutes
    rate_limit_config: RateLimitConfig = None  # Use defaults if not specified


class ControlCenter:
    """
    Unified Control Center

    The brain of the AI Dev Team platform. Coordinates:
    - System resource monitoring
    - AI agent health checks
    - Apple Intelligence notifications
    - Automatic recovery
    - Performance optimization

    This is your self-sustaining, always-watching command center.
    """

    def __init__(
        self,
        team: Optional["AIDevTeam"] = None,
        config: Optional[ControlCenterConfig] = None,
    ):
        self.team = team
        self.config = config or ControlCenterConfig()

        # Initialize subsystems
        self.system_monitor = SystemMonitor(
            check_interval=self.config.system_check_interval
        ) if self.config.enable_system_monitor else None

        self.health_checker = HealthChecker(
            check_interval=self.config.health_check_interval
        ) if self.config.enable_health_checks else None

        self.apple = AppleIntelligence() if self.config.enable_apple_notifications else None

        self.recovery = AutoRecovery(team=team) if self.config.enable_auto_recovery else None

        self.optimizer = PerformanceOptimizer() if self.config.enable_performance_optimizer else None

        self.resource_manager = ResourceManager(
            rate_limit_config=self.config.rate_limit_config,
            daily_budget_usd=self.config.daily_budget_usd,
            idle_timeout_seconds=self.config.idle_timeout_seconds,
        ) if self.config.enable_resource_manager else None

        self._running = False
        self._start_time: Optional[datetime] = None

        # Wire up callbacks
        self._setup_callbacks()

    def set_team(self, team: "AIDevTeam"):
        """Set or update the AI team"""
        self.team = team

        if self.recovery:
            self.recovery.set_team(team)

        if self.health_checker and team:
            for name, agent in team.agents.items():
                self.health_checker.register_agent(name, agent)

    def _setup_callbacks(self):
        """Wire up event callbacks between subsystems"""
        # System monitor alerts
        if self.system_monitor:
            self.system_monitor.add_alert_callback(self._handle_resource_alert)

        # Health checker status changes
        if self.health_checker:
            self.health_checker.add_callback(self._handle_health_change)

        # Recovery events
        if self.recovery:
            self.recovery.add_callback(self._handle_recovery_event)

    def _handle_resource_alert(self, alert: ResourceAlert):
        """Handle system resource alerts"""
        logger.warning(f"Resource alert: {alert}")

        # Notify via Apple Intelligence
        if self.apple and self.config.notify_on_warnings:
            if alert.level == AlertLevel.CRITICAL:
                self.apple.notify_alert(
                    f"{alert.resource} Critical",
                    alert.message
                )
                if self.config.speak_critical_alerts:
                    asyncio.create_task(
                        self.apple.speak_async(f"Warning: {alert.resource} usage is critical")
                    )
            elif alert.level == AlertLevel.WARNING:
                self.apple.notify(
                    f"{alert.resource} Warning",
                    alert.message,
                    priority=NotificationPriority.HIGH
                )

        # Trigger recovery for memory pressure
        if self.recovery and alert.resource == "Memory" and alert.level == AlertLevel.CRITICAL:
            asyncio.create_task(
                self.recovery.handle_memory_pressure(alert.current_value)
            )

    def _handle_health_change(self, agent_name: str, health):
        """Handle agent health status changes"""
        logger.info(f"Agent health change: {agent_name} -> {health.status.value}")

        # Notify
        if self.apple:
            if health.status == HealthStatus.OFFLINE:
                self.apple.notify_agent_offline(agent_name)
            elif health.status == HealthStatus.HEALTHY and health.consecutive_failures == 0:
                # Only notify recovery if there were previous failures
                pass  # Will be handled by recovery system

        # Trigger recovery
        if self.recovery and health.status in (HealthStatus.UNHEALTHY, HealthStatus.OFFLINE):
            asyncio.create_task(
                self.recovery.health_check_recovery(agent_name, health.status.value)
            )

    def _handle_recovery_event(self, event):
        """Handle recovery events"""
        logger.info(f"Recovery event: {event.action.value} on {event.target} - success={event.success}")

        # Notify on recovery
        if self.apple and self.config.notify_on_recovery:
            if event.success and event.action == RecoveryAction.RESTART_AGENT:
                self.apple.notify_agent_recovered(event.target)
            elif not event.success and event.details.get("requires_human"):
                self.apple.notify_critical(
                    "Human Intervention Required",
                    f"{event.target}: {event.reason}"
                )

    async def start(self):
        """Start the control center and all subsystems"""
        if self._running:
            return

        self._running = True
        self._start_time = datetime.now(timezone.utc)

        logger.info("Starting Control Center...")

        # Register agents if team is set
        if self.team and self.health_checker:
            for name, agent in self.team.agents.items():
                self.health_checker.register_agent(name, agent)

        # Start subsystems
        tasks = []

        if self.system_monitor:
            tasks.append(self.system_monitor.start())

        if self.health_checker:
            tasks.append(self.health_checker.start())

        if self.resource_manager:
            tasks.append(self.resource_manager.start())

        await asyncio.gather(*tasks)

        # Send startup notification
        if self.apple:
            agent_count = len(self.team.agents) if self.team else 0
            self.apple.notify(
                "AI Dev Team Online",
                f"Control Center active with {agent_count} agents",
                priority=NotificationPriority.LOW
            )

        logger.info("Control Center started successfully")

    async def stop(self):
        """Stop all subsystems"""
        if not self._running:
            return

        self._running = False

        logger.info("Stopping Control Center...")

        tasks = []

        if self.system_monitor:
            tasks.append(self.system_monitor.stop())

        if self.health_checker:
            tasks.append(self.health_checker.stop())

        if self.resource_manager:
            tasks.append(self.resource_manager.stop())

        await asyncio.gather(*tasks)

        # Send shutdown notification
        if self.apple:
            self.apple.notify(
                "AI Dev Team Offline",
                "Control Center shutting down",
                priority=NotificationPriority.LOW
            )

        logger.info("Control Center stopped")

    def get_dashboard(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        uptime = None
        if self._start_time:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()

        dashboard = {
            "status": "running" if self._running else "stopped",
            "uptime_seconds": uptime,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # System resources
        if self.system_monitor:
            dashboard["system"] = self.system_monitor.get_status_summary()

        # Agent health
        if self.health_checker:
            health = self.health_checker.get_system_health()
            dashboard["health"] = health.to_dict()

        # Recovery stats
        if self.recovery:
            dashboard["recovery"] = self.recovery.get_recovery_stats()

        # Performance
        if self.optimizer:
            dashboard["performance"] = self.optimizer.get_performance_summary()

        # Resources
        if self.resource_manager:
            dashboard["resources"] = self.resource_manager.get_status()

        # Team info
        if self.team:
            dashboard["team"] = {
                "project": self.team.project_name,
                "agents": list(self.team.agents.keys()),
                "total_agents": len(self.team.agents),
            }

        return dashboard

    def print_dashboard(self):
        """Print dashboard to console"""
        print("\n" + "=" * 70)
        print("  AI DEV TEAM - CONTROL CENTER DASHBOARD")
        print("=" * 70)

        dashboard = self.get_dashboard()

        # Status
        status = "ONLINE" if self._running else "OFFLINE"
        uptime = dashboard.get("uptime_seconds", 0)
        uptime_str = f"{uptime/3600:.1f}h" if uptime else "N/A"
        print(f"\n  Status: {status}  |  Uptime: {uptime_str}")

        # Team
        if "team" in dashboard:
            team = dashboard["team"]
            print(f"  Project: {team['project']}  |  Agents: {team['total_agents']}")

        # System Resources
        if "system" in dashboard:
            sys = dashboard["system"]["current"]
            print(f"\n  SYSTEM RESOURCES")
            print(f"  CPU: {sys['cpu_percent']:.1f}%  |  Memory: {sys['memory_percent']:.1f}%  |  Disk: {sys['disk_percent']:.1f}%")

        # Agent Health
        if "health" in dashboard:
            health = dashboard["health"]
            print(f"\n  AGENT HEALTH")
            print(f"  Overall: {health['status'].upper()}  |  Availability: {health['availability_percent']:.0f}%")
            print(f"  Healthy: {health['healthy_agents']}  |  Degraded: {health['degraded_agents']}  |  Offline: {health['offline_agents']}")

        # Performance
        if "performance" in dashboard:
            perf = dashboard["performance"]
            print(f"\n  PERFORMANCE")
            print(f"  Total Requests: {perf['total_requests']}  |  Avg Response: {perf['avg_response_time_ms']:.0f}ms")
            if perf.get("cache"):
                print(f"  Cache Hit Rate: {perf['cache']['hit_rate']:.1f}%")

        # Recovery
        if "recovery" in dashboard:
            rec = dashboard["recovery"]
            print(f"\n  AUTO-RECOVERY")
            print(f"  Total Recoveries: {rec['total_recoveries']}  |  Success Rate: {rec['success_rate']:.0f}%")

        # Resources
        if "resources" in dashboard:
            res = dashboard["resources"]
            print(f"\n  RESOURCE MANAGEMENT")
            if "costs" in res:
                costs = res["costs"]
                budget_pct = (costs['daily_spend_usd'] / costs['daily_budget_usd'] * 100) if costs['daily_budget_usd'] > 0 else 0
                print(f"  Budget: ${costs['daily_spend_usd']:.4f} / ${costs['daily_budget_usd']:.2f} ({budget_pct:.0f}%)")
            if "rate_limits" in res:
                rl = res["rate_limits"]
                print(f"  Rate: {rl['requests_last_minute']}/{rl['limits']['requests_per_minute']} req/min")

        print("\n" + "=" * 70)

    async def run_forever(self):
        """Run the control center until interrupted"""
        await self.start()

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    # Convenience methods for quick access

    def check_system(self):
        """Quick system status check"""
        if self.system_monitor:
            self.system_monitor.print_status()

    def check_health(self):
        """Quick health check"""
        if self.health_checker:
            self.health_checker.print_health_report()

    def check_performance(self):
        """Quick performance check"""
        if self.optimizer:
            self.optimizer.print_performance_report()

    def check_recovery(self):
        """Quick recovery status"""
        if self.recovery:
            self.recovery.print_recovery_report()

    def notify(self, title: str, message: str):
        """Send a notification"""
        if self.apple:
            self.apple.notify(title, message)

    def speak(self, text: str):
        """Speak text using Siri"""
        if self.apple:
            self.apple.speak(text)

    def check_resources(self):
        """Quick resource status"""
        if self.resource_manager:
            self.resource_manager.print_status()

    async def can_make_request(self, tokens: int = 0) -> tuple[bool, str]:
        """Check if a request can be made (rate/budget limits)"""
        if self.resource_manager:
            return await self.resource_manager.can_make_request(tokens)
        return True, "OK"
