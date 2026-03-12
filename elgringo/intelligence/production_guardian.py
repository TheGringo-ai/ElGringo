"""
Live Production Agent — ProductionGuardian
============================================

Moat feature #1: No competitor (CrewAI, AutoGen, LangGraph) has this.
Monitors running applications, auto-diagnoses errors, generates fix suggestions.

Usage:
    guardian = get_guardian()
    guardian.add_monitored_app("dashboard", url="https://dashboard.chatterfix.com")
    report = guardian.get_status_report()
    alerts = guardian.get_alerts(limit=10)
"""

import json
import logging
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


@dataclass
class MonitoredApp:
    """An application being monitored."""
    name: str
    app_id: str = ""
    url: str = ""
    log_path: str = ""
    health_endpoint: str = "/health"
    check_interval_seconds: int = 300
    added_at: str = ""
    last_checked: str = ""
    status: str = "unknown"  # healthy, degraded, down, unknown

    def __post_init__(self):
        if not self.app_id:
            self.app_id = f"app-{uuid.uuid4().hex[:8]}"
        if not self.added_at:
            self.added_at = datetime.now(timezone.utc).isoformat()


@dataclass
class HealthCheck:
    """Result of a health check."""
    app_id: str
    timestamp: str
    status: str  # healthy, degraded, down
    response_time_ms: float = 0.0
    status_code: int = 0
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """An alert generated from monitoring."""
    alert_id: str
    app_id: str
    app_name: str
    severity: str  # critical, warning, info
    title: str
    description: str
    timestamp: str = ""
    resolved: bool = False
    resolved_at: str = ""
    diagnosis: str = ""

    def __post_init__(self):
        if not self.alert_id:
            self.alert_id = f"alert-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class DiagnosisResult:
    """Result of auto-diagnosis."""
    error_text: str
    category: str  # connection, auth, server, config, dependency, unknown
    likely_cause: str
    suggested_fixes: List[str]
    confidence: float
    similar_past_issues: List[Dict[str, str]] = field(default_factory=list)


# Common error patterns for auto-diagnosis
ERROR_PATTERNS = [
    {
        "pattern": r"connection\s*(refused|reset|timed?\s*out)",
        "category": "connection",
        "cause": "Service is not running or port is blocked",
        "fixes": ["Check if the service is running", "Verify the port is open", "Check firewall rules"],
        "confidence": 0.85,
    },
    {
        "pattern": r"(401|403|unauthorized|forbidden)",
        "category": "auth",
        "cause": "Authentication or authorization failure",
        "fixes": ["Check API keys/tokens", "Verify credentials are not expired", "Check role permissions"],
        "confidence": 0.9,
    },
    {
        "pattern": r"(500|internal\s*server\s*error)",
        "category": "server",
        "cause": "Internal server error — likely a bug or misconfiguration",
        "fixes": ["Check server logs for stack trace", "Verify database connections", "Check disk space"],
        "confidence": 0.7,
    },
    {
        "pattern": r"(502|bad\s*gateway|503|service\s*unavailable)",
        "category": "server",
        "cause": "Service is down or overloaded",
        "fixes": ["Restart the service", "Check system resources (CPU, memory)", "Check upstream dependencies"],
        "confidence": 0.8,
    },
    {
        "pattern": r"(ENOSPC|no\s*space\s*left|disk\s*full)",
        "category": "config",
        "cause": "Disk space exhausted",
        "fixes": ["Free disk space", "Clear logs/temp files", "Increase disk size"],
        "confidence": 0.95,
    },
    {
        "pattern": r"(ModuleNotFoundError|ImportError|No module named)",
        "category": "dependency",
        "cause": "Missing Python dependency",
        "fixes": ["Install the missing package", "Check virtual environment is activated", "Run pip install -r requirements.txt"],
        "confidence": 0.9,
    },
    {
        "pattern": r"(OOM|out\s*of\s*memory|MemoryError|killed)",
        "category": "server",
        "cause": "Process ran out of memory",
        "fixes": ["Increase memory allocation", "Optimize memory usage", "Add swap space"],
        "confidence": 0.85,
    },
    {
        "pattern": r"(SSL|certificate|TLS|handshake)",
        "category": "config",
        "cause": "SSL/TLS certificate issue",
        "fixes": ["Renew SSL certificate", "Check certificate chain", "Update CA certificates"],
        "confidence": 0.8,
    },
    {
        "pattern": r"(timeout|timed?\s*out|deadline\s*exceeded)",
        "category": "connection",
        "cause": "Request timed out — service is slow or unreachable",
        "fixes": ["Increase timeout values", "Check network connectivity", "Optimize slow queries"],
        "confidence": 0.75,
    },
]


class ProductionGuardian:
    """
    Monitors running applications, detects issues, and auto-diagnoses errors.

    Features:
    - HTTP health checks with response time tracking
    - Log file scanning for error patterns
    - Auto-diagnosis with suggested fixes
    - Alert management with severity levels
    - Health history for trend analysis
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/guardian"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._apps: Dict[str, MonitoredApp] = {}
        self._alerts: List[Alert] = []
        self._health_history: List[HealthCheck] = []
        self._load()

    def _load(self):
        """Load state from disk."""
        apps_file = self.storage_dir / "apps.json"
        if apps_file.exists():
            try:
                with open(apps_file) as f:
                    for a in json.load(f):
                        app = MonitoredApp(**a)
                        self._apps[app.app_id] = app
            except Exception as e:
                logger.warning(f"Error loading apps: {e}")

        alerts_file = self.storage_dir / "alerts.json"
        if alerts_file.exists():
            try:
                with open(alerts_file) as f:
                    self._alerts = [Alert(**a) for a in json.load(f)]
            except Exception as e:
                logger.warning(f"Error loading alerts: {e}")

    def _save(self):
        """Save state to disk."""
        try:
            with open(self.storage_dir / "apps.json", "w") as f:
                json.dump([asdict(a) for a in self._apps.values()], f, indent=2)
            with open(self.storage_dir / "alerts.json", "w") as f:
                json.dump([asdict(a) for a in self._alerts[-500:]], f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving guardian state: {e}")

    def add_monitored_app(
        self, name: str, url: str = "", log_path: str = "", health_endpoint: str = "/health"
    ) -> str:
        """Add an application to monitor. Returns app_id."""
        app = MonitoredApp(name=name, url=url, log_path=log_path, health_endpoint=health_endpoint)
        self._apps[app.app_id] = app
        self._save()
        logger.info(f"Added monitored app: {name} ({app.app_id})")
        return app.app_id

    def check_health(self, app_id: str) -> HealthCheck:
        """Run a health check on a monitored app."""
        app = self._apps.get(app_id)
        if not app:
            return HealthCheck(app_id=app_id, timestamp=datetime.now(timezone.utc).isoformat(),
                               status="unknown", error="App not found")

        if not app.url:
            return HealthCheck(app_id=app_id, timestamp=datetime.now(timezone.utc).isoformat(),
                               status="unknown", error="No URL configured")

        check_url = app.url.rstrip("/") + app.health_endpoint
        start = time.time()
        try:
            req = Request(check_url, method="GET")
            with urlopen(req, timeout=10) as resp:
                elapsed = (time.time() - start) * 1000
                body = resp.read().decode()[:500]
                status = "healthy" if resp.status < 400 else "degraded"
                details = {}
                try:
                    details = json.loads(body)
                except json.JSONDecodeError:
                    details = {"raw": body}

                check = HealthCheck(
                    app_id=app_id, timestamp=datetime.now(timezone.utc).isoformat(),
                    status=status, response_time_ms=round(elapsed, 1),
                    status_code=resp.status, details=details,
                )
        except HTTPError as e:
            elapsed = (time.time() - start) * 1000
            check = HealthCheck(
                app_id=app_id, timestamp=datetime.now(timezone.utc).isoformat(),
                status="degraded" if e.code < 500 else "down",
                response_time_ms=round(elapsed, 1), status_code=e.code,
                error=str(e),
            )
        except (URLError, OSError) as e:
            check = HealthCheck(
                app_id=app_id, timestamp=datetime.now(timezone.utc).isoformat(),
                status="down", error=str(e),
            )

        # Update app status
        app.status = check.status
        app.last_checked = check.timestamp
        self._health_history.append(check)

        # Generate alert if down
        if check.status == "down":
            self._create_alert(app, "critical", f"{app.name} is DOWN", check.error)
        elif check.status == "degraded":
            self._create_alert(app, "warning", f"{app.name} is degraded", check.error)

        self._save()
        return check

    def scan_logs(self, log_path: str, lines: int = 200) -> List[Dict[str, Any]]:
        """Scan a log file for errors. Returns list of error entries."""
        path = Path(os.path.expanduser(log_path))
        if not path.exists():
            return [{"error": f"Log file not found: {log_path}"}]

        errors = []
        try:
            with open(path) as f:
                all_lines = f.readlines()
                recent = all_lines[-lines:] if len(all_lines) > lines else all_lines

            error_re = re.compile(r"(ERROR|CRITICAL|FATAL|Exception|Traceback)", re.IGNORECASE)
            for i, line in enumerate(recent):
                if error_re.search(line):
                    context = recent[max(0, i - 1):min(len(recent), i + 3)]
                    errors.append({
                        "line_number": len(all_lines) - len(recent) + i + 1,
                        "text": line.strip(),
                        "context": [l.strip() for l in context],
                    })
        except Exception as e:
            errors.append({"error": f"Failed to read log: {e}"})

        return errors[:50]  # Cap at 50 errors

    def diagnose(self, error_text: str) -> DiagnosisResult:
        """Auto-diagnose an error using pattern matching."""
        error_lower = error_text.lower()

        best_match = None
        best_confidence = 0.0

        for pattern_info in ERROR_PATTERNS:
            if re.search(pattern_info["pattern"], error_lower, re.IGNORECASE):
                if pattern_info["confidence"] > best_confidence:
                    best_match = pattern_info
                    best_confidence = pattern_info["confidence"]

        if best_match:
            return DiagnosisResult(
                error_text=error_text[:500],
                category=best_match["category"],
                likely_cause=best_match["cause"],
                suggested_fixes=best_match["fixes"],
                confidence=best_match["confidence"],
            )

        return DiagnosisResult(
            error_text=error_text[:500],
            category="unknown",
            likely_cause="Unable to auto-diagnose. Manual investigation needed.",
            suggested_fixes=["Check application logs", "Review recent changes", "Test in isolation"],
            confidence=0.2,
        )

    def get_status_report(self) -> Dict[str, Any]:
        """Get a summary status report of all monitored apps."""
        apps_summary = []
        for app in self._apps.values():
            apps_summary.append({
                "name": app.name,
                "app_id": app.app_id,
                "url": app.url,
                "status": app.status,
                "last_checked": app.last_checked or "never",
            })

        active_alerts = [a for a in self._alerts if not a.resolved]

        return {
            "total_apps": len(self._apps),
            "healthy": sum(1 for a in self._apps.values() if a.status == "healthy"),
            "degraded": sum(1 for a in self._apps.values() if a.status == "degraded"),
            "down": sum(1 for a in self._apps.values() if a.status == "down"),
            "active_alerts": len(active_alerts),
            "apps": apps_summary,
            "recent_alerts": [asdict(a) for a in active_alerts[:10]],
        }

    def get_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        sorted_alerts = sorted(self._alerts, key=lambda a: a.timestamp, reverse=True)
        return [asdict(a) for a in sorted_alerts[:limit]]

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc).isoformat()
                self._save()
                return True
        return False

    def _create_alert(self, app: MonitoredApp, severity: str, title: str, description: str):
        """Create a new alert, avoiding duplicates for the same issue."""
        # Don't duplicate active alerts for the same app + title
        for existing in self._alerts:
            if not existing.resolved and existing.app_id == app.app_id and existing.title == title:
                return

        diagnosis = self.diagnose(description)
        alert = Alert(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            app_id=app.app_id,
            app_name=app.name,
            severity=severity,
            title=title,
            description=description[:500],
            diagnosis=diagnosis.likely_cause,
        )
        self._alerts.append(alert)
        logger.warning(f"ALERT [{severity}] {title}: {description[:200]}")

    def list_apps(self) -> List[Dict[str, Any]]:
        """List all monitored apps."""
        return [asdict(a) for a in self._apps.values()]

    def remove_app(self, app_id: str) -> bool:
        """Remove a monitored app."""
        if app_id in self._apps:
            del self._apps[app_id]
            self._save()
            return True
        return False


def get_guardian() -> ProductionGuardian:
    """Get singleton guardian instance."""
    if not hasattr(get_guardian, "_instance"):
        get_guardian._instance = ProductionGuardian()
    return get_guardian._instance
