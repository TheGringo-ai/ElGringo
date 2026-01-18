"""
System Resource Monitor
=======================

Monitors CPU, memory, disk, and network resources.
Triggers alerts when thresholds are exceeded.
"""

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ResourceStatus:
    """Current resource status"""
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_healthy(self) -> bool:
        """Check if all resources are within acceptable limits"""
        return (
            self.cpu_percent < 90 and
            self.memory_percent < 85 and
            self.disk_percent < 90
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_gb": self.memory_used_gb,
            "memory_total_gb": self.memory_total_gb,
            "disk_percent": self.disk_percent,
            "disk_used_gb": self.disk_used_gb,
            "disk_total_gb": self.disk_total_gb,
            "is_healthy": self.is_healthy,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ResourceAlert:
    """Resource alert notification"""
    level: AlertLevel
    resource: str
    message: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __str__(self) -> str:
        return f"[{self.level.value.upper()}] {self.resource}: {self.message} ({self.current_value:.1f}% / threshold: {self.threshold:.1f}%)"


class SystemMonitor:
    """
    System Resource Monitor

    Continuously monitors system resources and triggers alerts
    when thresholds are exceeded. Integrates with Apple Intelligence
    for native macOS notifications.
    """

    # Default thresholds
    DEFAULT_THRESHOLDS = {
        "cpu_warning": 70,
        "cpu_critical": 90,
        "memory_warning": 70,
        "memory_critical": 85,
        "disk_warning": 80,
        "disk_critical": 90,
    }

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        check_interval: float = 30.0,  # seconds
        alert_cooldown: float = 300.0,  # 5 minutes between same alerts
    ):
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.check_interval = check_interval
        self.alert_cooldown = alert_cooldown

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._alert_history: List[ResourceAlert] = []
        self._last_alert_time: Dict[str, float] = {}
        self._alert_callbacks: List[Callable[[ResourceAlert], None]] = []
        self._status_history: List[ResourceStatus] = []
        self._max_history = 1000

    def add_alert_callback(self, callback: Callable[[ResourceAlert], None]):
        """Add callback to be notified of alerts"""
        self._alert_callbacks.append(callback)

    def get_current_status(self) -> ResourceStatus:
        """Get current system resource status"""
        # Get CPU usage (macOS)
        cpu_percent = self._get_cpu_percent()

        # Get memory usage (macOS)
        memory_info = self._get_memory_info()

        # Get disk usage
        disk_info = self._get_disk_info()

        return ResourceStatus(
            cpu_percent=cpu_percent,
            memory_percent=memory_info["percent"],
            memory_used_gb=memory_info["used_gb"],
            memory_total_gb=memory_info["total_gb"],
            disk_percent=disk_info["percent"],
            disk_used_gb=disk_info["used_gb"],
            disk_total_gb=disk_info["total_gb"],
        )

    def _get_cpu_percent(self) -> float:
        """Get CPU usage percentage on macOS"""
        try:
            # Use top command for CPU
            result = subprocess.run(
                ["top", "-l", "1", "-n", "0"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split("\n"):
                if "CPU usage" in line:
                    # Parse: CPU usage: 5.26% user, 10.52% sys, 84.21% idle
                    parts = line.split(",")
                    user = float(parts[0].split(":")[1].strip().replace("%", "").split()[0])
                    sys = float(parts[1].strip().replace("%", "").split()[0])
                    return user + sys
        except Exception as e:
            logger.warning(f"Failed to get CPU: {e}")
        return 0.0

    def _get_memory_info(self) -> Dict[str, float]:
        """Get memory info on macOS"""
        try:
            # Use vm_stat for memory
            result = subprocess.run(
                ["vm_stat"],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Parse vm_stat output
            stats = {}
            for line in result.stdout.split("\n"):
                if ":" in line:
                    key, value = line.split(":")
                    # Remove "Pages " prefix and periods
                    value = value.strip().rstrip(".")
                    try:
                        stats[key.strip()] = int(value)
                    except ValueError:
                        pass

            # Page size is typically 16384 on Apple Silicon, 4096 on Intel
            page_size = 16384  # bytes
            try:
                ps_result = subprocess.run(["pagesize"], capture_output=True, text=True, timeout=2)
                page_size = int(ps_result.stdout.strip())
            except:
                pass

            # Calculate memory
            pages_free = stats.get("Pages free", 0)
            pages_active = stats.get("Pages active", 0)
            pages_inactive = stats.get("Pages inactive", 0)
            pages_wired = stats.get("Pages wired down", 0)
            pages_compressed = stats.get("Pages occupied by compressor", 0)

            total_pages = pages_free + pages_active + pages_inactive + pages_wired + pages_compressed
            used_pages = pages_active + pages_wired + pages_compressed

            total_gb = (total_pages * page_size) / (1024 ** 3)
            used_gb = (used_pages * page_size) / (1024 ** 3)

            # Get actual total from sysctl
            try:
                mem_result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                total_gb = int(mem_result.stdout.strip()) / (1024 ** 3)
            except:
                pass

            percent = (used_gb / total_gb * 100) if total_gb > 0 else 0

            return {
                "percent": percent,
                "used_gb": used_gb,
                "total_gb": total_gb,
            }
        except Exception as e:
            logger.warning(f"Failed to get memory: {e}")
            return {"percent": 0, "used_gb": 0, "total_gb": 0}

    def _get_disk_info(self) -> Dict[str, float]:
        """Get disk usage info"""
        try:
            result = subprocess.run(
                ["df", "-g", "/"],
                capture_output=True,
                text=True,
                timeout=5
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split()
                total_gb = float(parts[1])
                used_gb = float(parts[2])
                percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
                return {
                    "percent": percent,
                    "used_gb": used_gb,
                    "total_gb": total_gb,
                }
        except Exception as e:
            logger.warning(f"Failed to get disk: {e}")
        return {"percent": 0, "used_gb": 0, "total_gb": 0}

    def check_thresholds(self, status: ResourceStatus) -> List[ResourceAlert]:
        """Check if any thresholds are exceeded"""
        alerts = []
        now = time.time()

        # CPU checks
        if status.cpu_percent >= self.thresholds["cpu_critical"]:
            alerts.append(self._create_alert(
                "cpu_critical", AlertLevel.CRITICAL, "CPU",
                f"CPU usage critical: {status.cpu_percent:.1f}%",
                status.cpu_percent, self.thresholds["cpu_critical"]
            ))
        elif status.cpu_percent >= self.thresholds["cpu_warning"]:
            alerts.append(self._create_alert(
                "cpu_warning", AlertLevel.WARNING, "CPU",
                f"CPU usage high: {status.cpu_percent:.1f}%",
                status.cpu_percent, self.thresholds["cpu_warning"]
            ))

        # Memory checks
        if status.memory_percent >= self.thresholds["memory_critical"]:
            alerts.append(self._create_alert(
                "memory_critical", AlertLevel.CRITICAL, "Memory",
                f"Memory usage critical: {status.memory_percent:.1f}% ({status.memory_used_gb:.1f}GB / {status.memory_total_gb:.1f}GB)",
                status.memory_percent, self.thresholds["memory_critical"]
            ))
        elif status.memory_percent >= self.thresholds["memory_warning"]:
            alerts.append(self._create_alert(
                "memory_warning", AlertLevel.WARNING, "Memory",
                f"Memory usage high: {status.memory_percent:.1f}%",
                status.memory_percent, self.thresholds["memory_warning"]
            ))

        # Disk checks
        if status.disk_percent >= self.thresholds["disk_critical"]:
            alerts.append(self._create_alert(
                "disk_critical", AlertLevel.CRITICAL, "Disk",
                f"Disk usage critical: {status.disk_percent:.1f}%",
                status.disk_percent, self.thresholds["disk_critical"]
            ))
        elif status.disk_percent >= self.thresholds["disk_warning"]:
            alerts.append(self._create_alert(
                "disk_warning", AlertLevel.WARNING, "Disk",
                f"Disk usage high: {status.disk_percent:.1f}%",
                status.disk_percent, self.thresholds["disk_warning"]
            ))

        # Filter by cooldown
        filtered_alerts = []
        for alert in alerts:
            key = f"{alert.resource}_{alert.level.value}"
            last_time = self._last_alert_time.get(key, 0)
            if now - last_time >= self.alert_cooldown:
                self._last_alert_time[key] = now
                filtered_alerts.append(alert)

        return filtered_alerts

    def _create_alert(
        self,
        key: str,
        level: AlertLevel,
        resource: str,
        message: str,
        current: float,
        threshold: float
    ) -> ResourceAlert:
        """Create an alert"""
        alert = ResourceAlert(
            level=level,
            resource=resource,
            message=message,
            current_value=current,
            threshold=threshold,
        )
        self._alert_history.append(alert)
        return alert

    async def start(self):
        """Start continuous monitoring"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("System monitor started")

    async def stop(self):
        """Stop monitoring"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("System monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                status = self.get_current_status()

                # Store history
                self._status_history.append(status)
                if len(self._status_history) > self._max_history:
                    self._status_history = self._status_history[-self._max_history:]

                # Check thresholds
                alerts = self.check_thresholds(status)

                # Notify callbacks
                for alert in alerts:
                    for callback in self._alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            logger.error(f"Alert callback error: {e}")

                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(self.check_interval)

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of current status and recent history"""
        current = self.get_current_status()

        return {
            "current": current.to_dict(),
            "is_healthy": current.is_healthy,
            "recent_alerts": [
                {
                    "level": a.level.value,
                    "resource": a.resource,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in self._alert_history[-10:]
            ],
            "thresholds": self.thresholds,
            "monitoring": self._running,
        }

    def print_status(self):
        """Print current status to console"""
        status = self.get_current_status()

        print("\n" + "=" * 50)
        print("  SYSTEM RESOURCE STATUS")
        print("=" * 50)

        # CPU
        cpu_bar = self._progress_bar(status.cpu_percent)
        cpu_color = self._get_color(status.cpu_percent, 70, 90)
        print(f"\n  CPU:    {cpu_bar} {status.cpu_percent:5.1f}%")

        # Memory
        mem_bar = self._progress_bar(status.memory_percent)
        print(f"  Memory: {mem_bar} {status.memory_percent:5.1f}% ({status.memory_used_gb:.1f}GB / {status.memory_total_gb:.1f}GB)")

        # Disk
        disk_bar = self._progress_bar(status.disk_percent)
        print(f"  Disk:   {disk_bar} {status.disk_percent:5.1f}% ({status.disk_used_gb:.0f}GB / {status.disk_total_gb:.0f}GB)")

        # Health
        health = "HEALTHY" if status.is_healthy else "WARNING"
        print(f"\n  Status: {health}")
        print("=" * 50)

    def _progress_bar(self, percent: float, width: int = 20) -> str:
        """Create a text progress bar"""
        filled = int(width * percent / 100)
        empty = width - filled

        if percent >= 90:
            char = "!"
        elif percent >= 70:
            char = "#"
        else:
            char = "="

        return f"[{char * filled}{'-' * empty}]"

    def _get_color(self, value: float, warning: float, critical: float) -> str:
        """Get color based on thresholds"""
        if value >= critical:
            return "red"
        elif value >= warning:
            return "yellow"
        return "green"
