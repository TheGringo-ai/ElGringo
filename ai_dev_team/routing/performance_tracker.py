"""
Model Performance Tracker - Learns which models perform best for which tasks
============================================================================

Tracks actual performance metrics for each AI model and uses this data
to make smarter routing decisions.

Features:
- Track success rates by model and task type
- Track response times
- Track domain-specific performance
- Decay old data (recent performance matters more)
- Persist to disk for learning across sessions
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TaskOutcome:
    """Record of a task outcome for learning"""
    task_id: str
    model_name: str
    task_type: str
    domain: str
    success: bool
    confidence: float
    response_time: float  # seconds
    timestamp: str
    user_rating: Optional[int] = None  # 1-5 rating if provided
    code_executed: bool = False  # Whether generated code was run
    code_passed: bool = False  # Whether code passed tests


@dataclass
class ModelPerformance:
    """Performance metrics for a single model"""
    model_name: str
    total_tasks: int = 0
    successful_tasks: int = 0
    total_response_time: float = 0.0

    # Per-task-type stats: {task_type: {"success": X, "total": Y, "avg_time": Z}}
    task_type_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Per-domain stats: {domain: {"success": X, "total": Y}}
    domain_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Recent performance (last 50 tasks) for trend detection
    recent_outcomes: List[bool] = field(default_factory=list)

    # Last updated
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.5  # Default for no data
        return self.successful_tasks / self.total_tasks

    @property
    def avg_response_time(self) -> float:
        if self.total_tasks == 0:
            return 5.0  # Default 5 seconds
        return self.total_response_time / self.total_tasks

    @property
    def recent_trend(self) -> float:
        """Calculate recent performance trend (-1 to 1, positive = improving)"""
        if len(self.recent_outcomes) < 10:
            return 0.0

        # Compare first half to second half
        mid = len(self.recent_outcomes) // 2
        first_half = sum(self.recent_outcomes[:mid]) / mid if mid > 0 else 0
        second_half = sum(self.recent_outcomes[mid:]) / (len(self.recent_outcomes) - mid)

        return second_half - first_half

    def get_task_type_score(self, task_type: str) -> float:
        """Get performance score for a specific task type"""
        if task_type not in self.task_type_stats:
            return 0.5  # Default

        stats = self.task_type_stats[task_type]
        if stats.get("total", 0) == 0:
            return 0.5

        return stats.get("success", 0) / stats["total"]

    def get_domain_score(self, domain: str) -> float:
        """Get performance score for a specific domain"""
        if domain not in self.domain_stats:
            return 0.5  # Default

        stats = self.domain_stats[domain]
        if stats.get("total", 0) == 0:
            return 0.5

        return stats.get("success", 0) / stats["total"]


class PerformanceTracker:
    """
    Tracks and learns from AI model performance over time.

    This enables smarter routing by:
    - Learning which models excel at which task types
    - Tracking domain-specific performance
    - Detecting performance trends
    - Considering response times for latency-sensitive tasks
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/performance"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._models: Dict[str, ModelPerformance] = {}
        self._outcomes: List[TaskOutcome] = []

        # Decay factor for old data (0.95 = 5% decay per day)
        self.decay_factor = 0.95

        self._load_data()

    def _load_data(self):
        """Load performance data from disk"""
        try:
            models_file = self.storage_dir / "models.json"
            if models_file.exists():
                with open(models_file) as f:
                    data = json.load(f)
                    for name, model_data in data.items():
                        self._models[name] = ModelPerformance(**model_data)

            outcomes_file = self.storage_dir / "outcomes.json"
            if outcomes_file.exists():
                with open(outcomes_file) as f:
                    data = json.load(f)
                    self._outcomes = [TaskOutcome(**o) for o in data[-1000:]]  # Keep last 1000

            logger.info(f"Loaded performance data: {len(self._models)} models, {len(self._outcomes)} outcomes")
        except Exception as e:
            logger.warning(f"Error loading performance data: {e}")

    def _save_data(self):
        """Save performance data to disk"""
        try:
            with open(self.storage_dir / "models.json", "w") as f:
                json.dump({name: asdict(model) for name, model in self._models.items()}, f, indent=2)

            with open(self.storage_dir / "outcomes.json", "w") as f:
                json.dump([asdict(o) for o in self._outcomes[-1000:]], f, indent=2)
        except Exception as e:
            logger.error(f"Error saving performance data: {e}")

    def record_outcome(
        self,
        model_name: str,
        task_type: str,
        success: bool,
        confidence: float,
        response_time: float,
        domain: str = "general",
        task_id: str = "",
        user_rating: Optional[int] = None,
        code_executed: bool = False,
        code_passed: bool = False,
    ):
        """
        Record the outcome of a task for learning.

        Args:
            model_name: Name of the model that performed the task
            task_type: Type of task (coding, debugging, etc.)
            success: Whether the task was successful
            confidence: Model's confidence in response (0-1)
            response_time: Time taken in seconds
            domain: Domain area (firebase, auth, etc.)
            task_id: Unique task identifier
            user_rating: Optional 1-5 rating from user
            code_executed: Whether generated code was executed
            code_passed: Whether code passed tests
        """
        # Create outcome record
        outcome = TaskOutcome(
            task_id=task_id or f"{model_name}_{datetime.now().timestamp()}",
            model_name=model_name,
            task_type=task_type,
            domain=domain,
            success=success,
            confidence=confidence,
            response_time=response_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_rating=user_rating,
            code_executed=code_executed,
            code_passed=code_passed,
        )
        self._outcomes.append(outcome)

        # Update model performance
        if model_name not in self._models:
            self._models[model_name] = ModelPerformance(model_name=model_name)

        model = self._models[model_name]
        model.total_tasks += 1
        if success:
            model.successful_tasks += 1
        model.total_response_time += response_time
        model.last_updated = datetime.now(timezone.utc).isoformat()

        # Update task type stats
        if task_type not in model.task_type_stats:
            model.task_type_stats[task_type] = {"success": 0, "total": 0, "avg_time": 0}
        stats = model.task_type_stats[task_type]
        stats["total"] += 1
        if success:
            stats["success"] += 1
        # Rolling average for time
        stats["avg_time"] = (stats["avg_time"] * (stats["total"] - 1) + response_time) / stats["total"]

        # Update domain stats
        if domain not in model.domain_stats:
            model.domain_stats[domain] = {"success": 0, "total": 0}
        domain_stats = model.domain_stats[domain]
        domain_stats["total"] += 1
        if success:
            domain_stats["success"] += 1

        # Track recent outcomes
        model.recent_outcomes.append(success)
        if len(model.recent_outcomes) > 50:
            model.recent_outcomes = model.recent_outcomes[-50:]

        self._save_data()
        logger.debug(f"Recorded outcome for {model_name}: {task_type} - {'success' if success else 'fail'}")

    def get_best_model(
        self,
        task_type: str,
        available_models: List[str],
        domain: Optional[str] = None,
        prefer_fast: bool = False,
    ) -> Tuple[str, float]:
        """
        Get the best model for a task based on historical performance.

        Args:
            task_type: Type of task
            available_models: List of available model names
            domain: Optional domain for domain-specific routing
            prefer_fast: Whether to prioritize faster models

        Returns:
            Tuple of (best_model_name, confidence_score)
        """
        if not available_models:
            return ("", 0.0)

        scores = []

        for model_name in available_models:
            score = self._calculate_model_score(
                model_name, task_type, domain, prefer_fast
            )
            scores.append((model_name, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        best_model, best_score = scores[0]

        logger.debug(f"Best model for {task_type}: {best_model} (score: {best_score:.3f})")
        return best_model, best_score

    def _calculate_model_score(
        self,
        model_name: str,
        task_type: str,
        domain: Optional[str],
        prefer_fast: bool,
    ) -> float:
        """Calculate overall score for a model on a task"""

        # Base score (if no data)
        if model_name not in self._models:
            return 0.5

        model = self._models[model_name]

        # Start with overall success rate
        score = model.success_rate * 0.3

        # Add task-type specific score (higher weight)
        task_score = model.get_task_type_score(task_type)
        score += task_score * 0.4

        # Add domain-specific score if relevant
        if domain:
            domain_score = model.get_domain_score(domain)
            score += domain_score * 0.2
        else:
            score += 0.1  # Default boost

        # Add trend bonus/penalty
        trend = model.recent_trend
        score += trend * 0.1

        # Speed factor
        if prefer_fast:
            avg_time = model.avg_response_time
            # Faster = better, normalize to 0-0.1 bonus
            speed_score = max(0, 1 - (avg_time / 30)) * 0.1
            score += speed_score

        return min(score, 1.0)

    def get_model_ranking(
        self,
        available_models: List[str],
        task_type: Optional[str] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Get ranked list of models with detailed scores.

        Returns:
            List of (model_name, score, details) tuples
        """
        rankings = []

        for model_name in available_models:
            if model_name not in self._models:
                rankings.append((model_name, 0.5, {"status": "no_data"}))
                continue

            model = self._models[model_name]

            if task_type:
                score = self._calculate_model_score(model_name, task_type, None, False)
                task_score = model.get_task_type_score(task_type)
            else:
                score = model.success_rate
                task_score = None

            details = {
                "success_rate": model.success_rate,
                "total_tasks": model.total_tasks,
                "avg_response_time": model.avg_response_time,
                "recent_trend": model.recent_trend,
                "task_type_score": task_score,
            }

            rankings.append((model_name, score, details))

        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall performance statistics"""
        total_outcomes = len(self._outcomes)
        if total_outcomes == 0:
            return {
                "total_outcomes": 0,
                "models_tracked": 0,
                "message": "No performance data yet"
            }

        # Calculate aggregate stats
        success_count = sum(1 for o in self._outcomes if o.success)
        avg_confidence = sum(o.confidence for o in self._outcomes) / total_outcomes
        avg_time = sum(o.response_time for o in self._outcomes) / total_outcomes

        # Task type breakdown
        task_breakdown = defaultdict(lambda: {"success": 0, "total": 0})
        for o in self._outcomes:
            task_breakdown[o.task_type]["total"] += 1
            if o.success:
                task_breakdown[o.task_type]["success"] += 1

        # Model breakdown
        model_breakdown = {}
        for name, model in self._models.items():
            model_breakdown[name] = {
                "success_rate": model.success_rate,
                "total_tasks": model.total_tasks,
                "avg_response_time": round(model.avg_response_time, 2),
                "trend": round(model.recent_trend, 3),
                "best_task_types": sorted(
                    model.task_type_stats.items(),
                    key=lambda x: x[1].get("success", 0) / max(x[1].get("total", 1), 1),
                    reverse=True
                )[:3]
            }

        return {
            "total_outcomes": total_outcomes,
            "models_tracked": len(self._models),
            "overall_success_rate": success_count / total_outcomes,
            "avg_confidence": avg_confidence,
            "avg_response_time": round(avg_time, 2),
            "task_type_breakdown": dict(task_breakdown),
            "model_performance": model_breakdown,
        }


# Global instance
_performance_tracker: Optional[PerformanceTracker] = None


def get_performance_tracker() -> PerformanceTracker:
    """Get or create the global performance tracker"""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker
