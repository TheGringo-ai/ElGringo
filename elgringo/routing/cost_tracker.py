"""
Cost Tracker - Persistent cost tracking and budget alerts
==========================================================

Enhances the CostOptimizer with:
- Persistent storage of usage data
- Historical cost reports
- Budget alerts and warnings
- Per-model and per-task cost breakdowns
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .cost_optimizer import CostOptimizer, CostEstimate, MODEL_COSTS

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    """Record of a single API usage"""
    timestamp: str
    model: str
    agent_name: str
    task_type: str
    input_tokens: int
    output_tokens: int
    cost: float
    task_id: Optional[str] = None


class CostTracker:
    """
    Enhanced cost tracking with persistence and alerts.

    Features:
    - Persistent storage of usage history
    - Daily, weekly, monthly reports
    - Budget alerts at configurable thresholds
    - Per-model and per-task cost breakdown
    - Cost projection/forecasting

    Usage:
        tracker = CostTracker(daily_budget=10.0, monthly_budget=100.0)

        # Record usage
        tracker.record_usage("gpt-4", "chatgpt-coder", "coding", 1000, 2000)

        # Check budget
        status = tracker.get_budget_status()
        if status.daily_warning:
            print("Approaching daily limit!")

        # Get reports
        report = tracker.get_daily_report()
    """

    def __init__(
        self,
        storage_dir: str = "~/.ai-dev-team/costs",
        daily_budget: float = 10.0,
        monthly_budget: float = 100.0,
        alert_threshold: float = 0.8,  # Alert at 80% of budget
        on_budget_alert: Optional[Callable[[str, float, float], None]] = None,
    ):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self.alert_threshold = alert_threshold
        self.on_budget_alert = on_budget_alert

        self._cost_optimizer = CostOptimizer(daily_budget, monthly_budget)

        # Usage records
        self._usage_history: List[UsageRecord] = []
        self._daily_usage: Dict[str, float] = {}  # date -> cost
        self._model_usage: Dict[str, Dict[str, float]] = {}  # model -> {tokens, cost}
        self._task_usage: Dict[str, Dict[str, float]] = {}  # task_type -> {count, cost}

        self._load_data()

    def _load_data(self):
        """Load cost data from disk"""
        try:
            data_file = self.storage_dir / "cost_history.json"
            if data_file.exists():
                with open(data_file) as f:
                    data = json.load(f)

                # Load usage records (last 30 days)
                cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                for record in data.get("usage_history", []):
                    if record.get("timestamp", "") >= cutoff:
                        self._usage_history.append(UsageRecord(**record))

                self._daily_usage = data.get("daily_usage", {})
                self._model_usage = data.get("model_usage", {})
                self._task_usage = data.get("task_usage", {})

                # Restore optimizer state
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                self._cost_optimizer._daily_spent = self._daily_usage.get(today, 0.0)

                # Calculate monthly spent
                month_start = datetime.now(timezone.utc).replace(day=1).strftime("%Y-%m-%d")
                monthly_spent = sum(
                    cost for date, cost in self._daily_usage.items()
                    if date >= month_start
                )
                self._cost_optimizer._monthly_spent = monthly_spent

                logger.info(f"Loaded cost history: {len(self._usage_history)} records")
        except Exception as e:
            logger.warning(f"Error loading cost data: {e}")

    def _save_data(self):
        """Save cost data to disk"""
        try:
            # Clean old daily usage (keep last 90 days)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
            self._daily_usage = {
                date: cost for date, cost in self._daily_usage.items()
                if date >= cutoff
            }

            data = {
                "usage_history": [asdict(r) for r in self._usage_history[-1000:]],
                "daily_usage": self._daily_usage,
                "model_usage": self._model_usage,
                "task_usage": self._task_usage,
                "last_saved": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.storage_dir / "cost_history.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cost data: {e}")

    def record_usage(
        self,
        model: str,
        agent_name: str,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        task_id: Optional[str] = None,
    ) -> CostEstimate:
        """
        Record API usage and update costs.

        Args:
            model: Model name (e.g., "gpt-4")
            agent_name: Agent that made the call
            task_type: Type of task
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            task_id: Optional task ID

        Returns:
            CostEstimate with calculated cost
        """
        # Calculate cost
        estimate = self._cost_optimizer.record_usage(model, input_tokens, output_tokens)

        # Create usage record
        record = UsageRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=model,
            agent_name=agent_name,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=estimate.estimated_cost,
            task_id=task_id,
        )
        self._usage_history.append(record)

        # Update daily usage
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._daily_usage[today] = self._daily_usage.get(today, 0.0) + estimate.estimated_cost

        # Update model usage
        if model not in self._model_usage:
            self._model_usage[model] = {"tokens": 0, "cost": 0.0, "requests": 0}
        self._model_usage[model]["tokens"] += input_tokens + output_tokens
        self._model_usage[model]["cost"] += estimate.estimated_cost
        self._model_usage[model]["requests"] += 1

        # Update task usage
        if task_type not in self._task_usage:
            self._task_usage[task_type] = {"count": 0, "cost": 0.0}
        self._task_usage[task_type]["count"] += 1
        self._task_usage[task_type]["cost"] += estimate.estimated_cost

        # Check for budget alerts
        self._check_budget_alerts()

        # Save periodically
        if len(self._usage_history) % 10 == 0:
            self._save_data()

        return estimate

    def _check_budget_alerts(self):
        """Check and trigger budget alerts"""
        status = self.get_budget_status()

        # Daily alert
        if status["daily_percentage"] >= self.alert_threshold * 100:
            if self.on_budget_alert:
                self.on_budget_alert("daily", status["daily_spent"], status["daily_limit"])
            logger.warning(f"Daily budget alert: {status['daily_percentage']:.1f}% used")

        # Monthly alert
        if status["monthly_percentage"] >= self.alert_threshold * 100:
            if self.on_budget_alert:
                self.on_budget_alert("monthly", status["monthly_spent"], status["monthly_limit"])
            logger.warning(f"Monthly budget alert: {status['monthly_percentage']:.1f}% used")

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status with alerts"""
        base_status = self._cost_optimizer.get_budget_status()

        daily_pct = (base_status.daily_spent / base_status.daily_limit * 100) if base_status.daily_limit > 0 else 0
        monthly_pct = (base_status.monthly_spent / base_status.monthly_limit * 100) if base_status.monthly_limit > 0 else 0

        return {
            "daily_limit": base_status.daily_limit,
            "daily_spent": round(base_status.daily_spent, 4),
            "daily_remaining": round(base_status.remaining_daily, 4),
            "daily_percentage": round(daily_pct, 1),
            "daily_warning": daily_pct >= self.alert_threshold * 100,
            "monthly_limit": base_status.monthly_limit,
            "monthly_spent": round(base_status.monthly_spent, 4),
            "monthly_remaining": round(base_status.remaining_monthly, 4),
            "monthly_percentage": round(monthly_pct, 1),
            "monthly_warning": monthly_pct >= self.alert_threshold * 100,
        }

    def get_daily_report(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get cost report for a specific day"""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        daily_records = [
            r for r in self._usage_history
            if r.timestamp.startswith(date)
        ]

        total_cost = sum(r.cost for r in daily_records)
        total_tokens = sum(r.input_tokens + r.output_tokens for r in daily_records)

        # By model
        by_model = {}
        for r in daily_records:
            if r.model not in by_model:
                by_model[r.model] = {"requests": 0, "cost": 0.0, "tokens": 0}
            by_model[r.model]["requests"] += 1
            by_model[r.model]["cost"] += r.cost
            by_model[r.model]["tokens"] += r.input_tokens + r.output_tokens

        # By task type
        by_task = {}
        for r in daily_records:
            if r.task_type not in by_task:
                by_task[r.task_type] = {"requests": 0, "cost": 0.0}
            by_task[r.task_type]["requests"] += 1
            by_task[r.task_type]["cost"] += r.cost

        return {
            "date": date,
            "total_requests": len(daily_records),
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "by_model": by_model,
            "by_task_type": by_task,
        }

    def get_weekly_report(self) -> Dict[str, Any]:
        """Get cost report for the last 7 days"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)

        daily_costs = {}
        for i in range(7):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily_costs[date] = self._daily_usage.get(date, 0.0)

        total_cost = sum(daily_costs.values())
        avg_daily = total_cost / 7

        return {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "total_cost": round(total_cost, 4),
            "average_daily": round(avg_daily, 4),
            "daily_breakdown": {date: round(cost, 4) for date, cost in daily_costs.items()},
            "projected_monthly": round(avg_daily * 30, 2),
        }

    def get_monthly_report(self) -> Dict[str, Any]:
        """Get cost report for the current month"""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1).strftime("%Y-%m-%d")

        monthly_records = [
            r for r in self._usage_history
            if r.timestamp >= month_start
        ]

        total_cost = sum(r.cost for r in monthly_records)
        days_elapsed = now.day
        days_in_month = 30  # Approximate

        # By model
        by_model = {}
        for r in monthly_records:
            if r.model not in by_model:
                by_model[r.model] = {"requests": 0, "cost": 0.0}
            by_model[r.model]["requests"] += 1
            by_model[r.model]["cost"] += r.cost

        return {
            "month": now.strftime("%Y-%m"),
            "days_elapsed": days_elapsed,
            "total_requests": len(monthly_records),
            "total_cost": round(total_cost, 4),
            "by_model": {k: {"requests": v["requests"], "cost": round(v["cost"], 4)} for k, v in by_model.items()},
            "daily_average": round(total_cost / max(days_elapsed, 1), 4),
            "projected_total": round((total_cost / max(days_elapsed, 1)) * days_in_month, 2),
            "budget_limit": self.monthly_budget,
            "budget_remaining": round(self.monthly_budget - total_cost, 2),
        }

    def get_model_costs(self) -> Dict[str, Dict[str, Any]]:
        """Get cost breakdown by model"""
        result = {}
        for model, usage in self._model_usage.items():
            costs = MODEL_COSTS.get(model, (1.0, 5.0))
            result[model] = {
                "total_requests": usage.get("requests", 0),
                "total_tokens": usage.get("tokens", 0),
                "total_cost": round(usage.get("cost", 0.0), 4),
                "cost_per_1m_input": costs[0],
                "cost_per_1m_output": costs[1],
            }
        return result

    def set_budget(self, daily: Optional[float] = None, monthly: Optional[float] = None):
        """Update budget limits"""
        if daily is not None:
            self.daily_budget = daily
            self._cost_optimizer.daily_budget = daily
        if monthly is not None:
            self.monthly_budget = monthly
            self._cost_optimizer.monthly_budget = monthly
        self._save_data()

    def reset_daily(self):
        """Reset daily spending (called at midnight)"""
        self._cost_optimizer.reset_daily()

    def reset_monthly(self):
        """Reset monthly spending (called at month start)"""
        self._cost_optimizer.reset_monthly()

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall cost statistics"""
        return {
            "budget": self.get_budget_status(),
            "today": self.get_daily_report(),
            "this_week": self.get_weekly_report(),
            "this_month": self.get_monthly_report(),
            "by_model": self.get_model_costs(),
            "by_task_type": self._task_usage,
        }


# Global instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get or create the global cost tracker"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
