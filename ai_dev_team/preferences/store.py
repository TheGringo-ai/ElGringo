"""
Preference Store - Persistent Developer Settings
=================================================

SQLite-backed storage for developer preferences and constraints.
All data stays local - no cloud sync.
"""

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DevConstraints:
    """
    Developer preferences that affect routing and behavior.

    These are persisted per-project and influence:
    - Which models are selected
    - Cost limits
    - Quality thresholds
    - Deterministic behavior
    """

    # Model preferences
    prefer_local: bool = True
    allow_cloud_fallback: bool = False
    blocked_providers: List[str] = field(default_factory=list)
    preferred_agents: Dict[str, str] = field(default_factory=dict)  # task_type -> agent

    # Cost constraints
    max_cost_per_request: float = 0.0  # 0 = unlimited (but prefer_local applies)
    daily_budget: float = 0.0  # 0 = unlimited
    monthly_budget: float = 0.0

    # Quality constraints
    min_confidence: float = 0.6
    require_deterministic: bool = False  # temperature=0 for reproducibility
    max_retries: int = 2

    # Behavior
    verbose_routing: bool = False  # Show routing decisions
    auto_explain: bool = False  # Always explain choices
    log_all_requests: bool = True

    # Project context
    project_type: str = "python"
    coding_style: str = "concise"  # verbose, concise, minimal
    default_language: str = "python"

    def get_matched(self, decision_context: Dict[str, Any] = None) -> List[str]:
        """Get list of constraints that were matched/applied"""
        matched = []
        if self.prefer_local:
            matched.append("prefer_local")
        if self.require_deterministic:
            matched.append("deterministic_mode")
        if self.max_cost_per_request > 0:
            matched.append(f"max_cost=${self.max_cost_per_request}")
        if self.blocked_providers:
            matched.append(f"blocked:{','.join(self.blocked_providers)}")
        return matched

    def should_use_agent(self, agent_name: str, is_local: bool, cost: float = 0) -> tuple[bool, str]:
        """
        Check if an agent should be used given constraints.

        Returns:
            (allowed, reason)
        """
        # Check blocked providers
        for blocked in self.blocked_providers:
            if blocked.lower() in agent_name.lower():
                return False, f"Provider {blocked} is blocked"

        # Check local preference
        if self.prefer_local and not is_local and not self.allow_cloud_fallback:
            return False, "Cloud agents disabled (prefer_local=True)"

        # Check cost
        if self.max_cost_per_request > 0 and cost > self.max_cost_per_request:
            return False, f"Cost ${cost} exceeds limit ${self.max_cost_per_request}"

        return True, "Allowed"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevConstraints":
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class PreferenceStore:
    """
    SQLite-backed preference storage.

    Stores:
    - Per-project constraints
    - Global defaults
    - Routing decision history
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path.home() / ".ai-dev-team" / "preferences.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS constraints (
                    project TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    response_time REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def get_constraints(self, project: str = "default") -> DevConstraints:
        """Load constraints for a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM constraints WHERE project = ?",
                (project,)
            )
            row = cursor.fetchone()

            if row:
                try:
                    data = json.loads(row[0])
                    return DevConstraints.from_dict(data)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse constraints for {project}: {e}")

            # Return defaults
            return DevConstraints()

    def save_constraints(self, constraints: DevConstraints, project: str = "default"):
        """Save constraints for a project"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO constraints (project, data, updated_at)
                VALUES (?, ?, ?)
                """,
                (project, json.dumps(constraints.to_dict()), datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

    def set_constraint(self, key: str, value: Any, project: str = "default"):
        """Update a single constraint"""
        constraints = self.get_constraints(project)

        # Handle nested keys like "preferred_agents.code_review"
        if "." in key:
            parts = key.split(".")
            if parts[0] == "preferred_agents" and len(parts) == 2:
                constraints.preferred_agents[parts[1]] = value
            elif parts[0] == "blocked_providers":
                if value not in constraints.blocked_providers:
                    constraints.blocked_providers.append(value)
            else:
                raise ValueError(f"Unknown nested key: {key}")
        elif hasattr(constraints, key):
            # Type coercion
            field_type = type(getattr(constraints, key))
            if field_type == bool:
                value = str(value).lower() in ("true", "1", "yes")
            elif field_type == float:
                value = float(value)
            elif field_type == int:
                value = int(value)
            setattr(constraints, key, value)
        else:
            raise ValueError(f"Unknown constraint: {key}")

        self.save_constraints(constraints, project)

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a global setting"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str):
        """Set a global setting"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            conn.commit()

    def log_routing(
        self,
        project: str,
        agent: str,
        task_type: str,
        success: bool,
        response_time: float = None,
    ):
        """Log a routing decision for history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO routing_history (project, agent, task_type, success, response_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project, agent, task_type, int(success), response_time, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

    def get_routing_history(self, project: str = None, limit: int = 100) -> List[Dict]:
        """Get routing history"""
        with sqlite3.connect(self.db_path) as conn:
            if project:
                cursor = conn.execute(
                    """
                    SELECT agent, task_type, success, response_time, timestamp
                    FROM routing_history
                    WHERE project = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (project, limit)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT agent, task_type, success, response_time, timestamp
                    FROM routing_history
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,)
                )

            return [
                {
                    "agent": row[0],
                    "task_type": row[1],
                    "success": bool(row[2]),
                    "response_time": row[3],
                    "timestamp": row[4],
                }
                for row in cursor.fetchall()
            ]

    def get_agent_stats(self, project: str = None) -> Dict[str, Dict]:
        """Get performance stats per agent"""
        history = self.get_routing_history(project, limit=1000)

        stats = {}
        for entry in history:
            agent = entry["agent"]
            if agent not in stats:
                stats[agent] = {"total": 0, "success": 0, "total_time": 0.0}

            stats[agent]["total"] += 1
            if entry["success"]:
                stats[agent]["success"] += 1
            if entry["response_time"]:
                stats[agent]["total_time"] += entry["response_time"]

        # Calculate rates
        for agent, data in stats.items():
            data["success_rate"] = data["success"] / data["total"] if data["total"] > 0 else 0
            data["avg_time"] = data["total_time"] / data["total"] if data["total"] > 0 else 0

        return stats

    def list_projects(self) -> List[str]:
        """List all projects with saved constraints"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT project FROM constraints")
            return [row[0] for row in cursor.fetchall()]

    def export_all(self) -> Dict[str, Any]:
        """Export all preferences for backup"""
        projects = {}
        for project in self.list_projects():
            projects[project] = self.get_constraints(project).to_dict()

        return {
            "projects": projects,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }


# Global store instance
_preference_store: Optional[PreferenceStore] = None


def get_preference_store() -> PreferenceStore:
    """Get the global preference store"""
    global _preference_store
    if _preference_store is None:
        _preference_store = PreferenceStore()
    return _preference_store
