"""
ROI Dashboard — Track the value El Gringo delivers
====================================================

Computes and presents:
1. Time saved vs manual development
2. Cost efficiency (API spend vs developer hourly rate)
3. Agent performance rankings
4. Quality trends over time
5. System learning velocity
"""

import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MANUAL_TIME_ESTIMATES = {
    "coding": 45, "debugging": 30, "testing": 25, "code_review": 20,
    "architecture": 60, "documentation": 30, "security": 40,
    "optimization": 35, "creative": 20, "research": 25, "general": 15,
}
DEFAULT_DEV_HOURLY_RATE = 75.0


@dataclass
class TaskRecord:
    task_id: str
    timestamp: str
    task_type: str
    complexity: str
    agents_used: List[str]
    mode: str
    duration_seconds: float
    api_cost: float
    success: bool
    confidence: float
    user_rating: Optional[float] = None

    @property
    def estimated_manual_minutes(self):
        base = MANUAL_TIME_ESTIMATES.get(self.task_type, 15)
        return base * {"low": 0.7, "medium": 1.0, "high": 2.0}.get(self.complexity, 1.0)

    @property
    def time_saved_minutes(self):
        return max(0, self.estimated_manual_minutes - self.duration_seconds / 60.0)

    @property
    def money_saved(self):
        return max(0, (self.estimated_manual_minutes / 60.0) * DEFAULT_DEV_HOURLY_RATE - self.api_cost)


@dataclass
class AgentRanking:
    agent_name: str
    total_tasks: int
    success_rate: float
    avg_confidence: float
    avg_response_time: float
    best_task_types: List[str]
    total_cost: float
    satisfaction_rate: float


@dataclass
class ROIReport:
    period: str
    total_tasks: int = 0
    successful_tasks: int = 0
    total_time_saved_hours: float = 0.0
    total_money_saved: float = 0.0
    total_api_cost: float = 0.0
    avg_confidence: float = 0.0
    avg_user_rating: float = 0.0
    success_rate: float = 0.0
    agent_rankings: List[AgentRanking] = field(default_factory=list)
    quality_trend: str = "stable"
    efficiency_trend: str = "stable"
    solutions_learned: int = 0
    mistakes_prevented: int = 0
    feedback_events: int = 0

    def to_dict(self):
        roi = self.total_money_saved / max(self.total_api_cost, 0.01)
        return {
            "period": self.period,
            "summary": {
                "total_tasks": self.total_tasks,
                "successful_tasks": self.successful_tasks,
                "success_rate": f"{self.success_rate:.0%}",
                "time_saved": f"{self.total_time_saved_hours:.1f} hours",
                "money_saved": f"${self.total_money_saved:.2f}",
                "api_cost": f"${self.total_api_cost:.2f}",
                "roi": f"{roi:.0f}x",
            },
            "quality": {
                "avg_confidence": round(self.avg_confidence, 2),
                "avg_user_rating": round(self.avg_user_rating, 2),
                "quality_trend": self.quality_trend,
            },
            "agent_rankings": [
                {
                    "agent": r.agent_name, "tasks": r.total_tasks,
                    "success_rate": f"{r.success_rate:.0%}",
                    "avg_confidence": round(r.avg_confidence, 2),
                    "best_at": r.best_task_types[:3],
                    "satisfaction": f"{r.satisfaction_rate:.0%}",
                }
                for r in self.agent_rankings
            ],
            "learning": {
                "solutions_learned": self.solutions_learned,
                "mistakes_prevented": self.mistakes_prevented,
                "feedback_processed": self.feedback_events,
            },
        }

    def to_readable(self):
        roi = self.total_money_saved / max(self.total_api_cost, 0.01)
        lines = [
            f"# El Gringo ROI Dashboard — {self.period.title()}", "",
            f"## Value Delivered",
            f"  Tasks completed: {self.total_tasks} ({self.success_rate:.0%} success rate)",
            f"  Time saved: {self.total_time_saved_hours:.1f} hours",
            f"  Money saved: ${self.total_money_saved:.2f}",
            f"  API cost: ${self.total_api_cost:.2f}",
            f"  **ROI: {roi:.0f}x**", "",
            f"## Quality",
            f"  Average confidence: {self.avg_confidence:.0%}",
            f"  Quality trend: {self.quality_trend}", "",
            f"## Top Agents",
        ]
        for r in self.agent_rankings[:5]:
            lines.append(f"  {r.agent_name}: {r.success_rate:.0%} success, best at {', '.join(r.best_task_types[:2])}")
        return "\n".join(lines)


class ROIDashboard:
    """Tracks task outcomes and computes ROI metrics."""

    def __init__(self, storage_dir="~/.ai-dev-team/roi", dev_hourly_rate=DEFAULT_DEV_HOURLY_RATE):
        self._storage_dir = Path(os.path.expanduser(storage_dir))
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._dev_rate = dev_hourly_rate
        self._records: List[TaskRecord] = []
        self._load_records()

    def record_task(self, task_id, task_type, complexity, agents_used, mode, duration_seconds, api_cost, success, confidence, user_rating=None):
        self._records.append(TaskRecord(
            task_id=task_id, timestamp=datetime.now(timezone.utc).isoformat(),
            task_type=task_type, complexity=complexity, agents_used=agents_used,
            mode=mode, duration_seconds=duration_seconds, api_cost=api_cost,
            success=success, confidence=confidence, user_rating=user_rating,
        ))
        self._save_records()

    def update_rating(self, task_id, rating):
        for record in reversed(self._records):
            if record.task_id == task_id:
                record.user_rating = rating
                self._save_records()
                return True
        return False

    def get_report(self, period="all_time"):
        now = datetime.now(timezone.utc)
        cutoffs = {"today": timedelta(days=1), "week": timedelta(weeks=1), "month": timedelta(days=30)}
        cutoff = now - cutoffs.get(period, timedelta(days=36500))

        filtered = [r for r in self._records if datetime.fromisoformat(r.timestamp) > cutoff]
        if not filtered:
            return ROIReport(period=period)

        successful = [r for r in filtered if r.success]
        rated = [r for r in filtered if r.user_rating is not None]

        report = ROIReport(
            period=period, total_tasks=len(filtered), successful_tasks=len(successful),
            total_time_saved_hours=sum(r.time_saved_minutes for r in filtered) / 60.0,
            total_money_saved=sum(r.money_saved for r in filtered),
            total_api_cost=sum(r.api_cost for r in filtered),
            avg_confidence=sum(r.confidence for r in filtered) / len(filtered),
            avg_user_rating=sum(r.user_rating for r in rated) / len(rated) if rated else 0.0,
            success_rate=len(successful) / len(filtered),
        )

        # Agent rankings
        agent_data = defaultdict(lambda: {
            "tasks": 0, "successes": 0, "conf_sum": 0.0, "time_sum": 0.0,
            "cost_sum": 0.0, "types": defaultdict(int), "pos": 0, "neg": 0,
        })
        for r in filtered:
            for agent in r.agents_used:
                d = agent_data[agent]
                d["tasks"] += 1
                if r.success: d["successes"] += 1
                d["conf_sum"] += r.confidence
                d["time_sum"] += r.duration_seconds
                d["cost_sum"] += r.api_cost / max(len(r.agents_used), 1)
                d["types"][r.task_type] += 1
                if r.user_rating is not None:
                    if r.user_rating > 0: d["pos"] += 1
                    elif r.user_rating < 0: d["neg"] += 1

        for name, d in agent_data.items():
            best = sorted(d["types"].items(), key=lambda x: x[1], reverse=True)
            total_rated = d["pos"] + d["neg"]
            report.agent_rankings.append(AgentRanking(
                agent_name=name, total_tasks=d["tasks"],
                success_rate=d["successes"] / d["tasks"] if d["tasks"] else 0,
                avg_confidence=d["conf_sum"] / d["tasks"] if d["tasks"] else 0,
                avg_response_time=d["time_sum"] / d["tasks"] if d["tasks"] else 0,
                best_task_types=[t for t, _ in best[:3]], total_cost=d["cost_sum"],
                satisfaction_rate=d["pos"] / total_rated if total_rated else 0.5,
            ))
        report.agent_rankings.sort(key=lambda r: r.success_rate, reverse=True)

        if len(filtered) >= 6:
            mid = len(filtered) // 2
            first = sum(r.confidence for r in filtered[:mid]) / mid
            second = sum(r.confidence for r in filtered[mid:]) / (len(filtered) - mid)
            diff = second - first
            report.quality_trend = "improving" if diff > 0.05 else "declining" if diff < -0.05 else "stable"

        return report

    def get_agent_leaderboard(self):
        report = self.get_report("all_time")
        return [
            {"rank": i + 1, "agent": r.agent_name, "tasks": r.total_tasks,
             "success_rate": f"{r.success_rate:.0%}", "best_at": r.best_task_types[:3]}
            for i, r in enumerate(report.agent_rankings)
        ]

    def _save_records(self):
        try:
            to_save = self._records[-1000:]
            data = [
                {"task_id": r.task_id, "timestamp": r.timestamp, "task_type": r.task_type,
                 "complexity": r.complexity, "agents_used": r.agents_used, "mode": r.mode,
                 "duration_seconds": r.duration_seconds, "api_cost": r.api_cost,
                 "success": r.success, "confidence": r.confidence, "user_rating": r.user_rating}
                for r in to_save
            ]
            (self._storage_dir / "task_records.json").write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"Failed to save ROI records: {e}")

    def _load_records(self):
        try:
            f = self._storage_dir / "task_records.json"
            if f.exists():
                self._records = [TaskRecord(**r) for r in json.loads(f.read_text())]
        except Exception as e:
            logger.debug(f"Failed to load ROI records: {e}")


_dashboard: Optional[ROIDashboard] = None

def get_roi_dashboard() -> ROIDashboard:
    global _dashboard
    if _dashboard is None:
        _dashboard = ROIDashboard()
    return _dashboard
