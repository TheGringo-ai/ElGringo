"""
Cost Arbitrage Engine — ValueOptimizer
=======================================

Moat feature #3: No competitor (CrewAI, AutoGen, LangGraph) has this.
Real-time cost comparison across AI providers, savings tracking, optimal routing.

Usage:
    optimizer = get_optimizer()
    optimizer.record_usage("chatgpt", "code_review", cost=0.045, quality=8.5, tokens=1500)
    best = optimizer.get_best_provider("code_review")
    report = optimizer.get_savings_report()
"""

import json
import logging
import os
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Per-1K token costs (approximate)
PROVIDER_COSTS = {
    "chatgpt": 0.030,
    "gemini": 0.010,
    "grok": 0.020,
    "grok-coder": 0.020,
    "llama": 0.005,
    "mlx-coder": 0.000,
    "mlx-general": 0.000,
}

EXPENSIVE_BASELINE = "chatgpt"  # Compare savings against most expensive


@dataclass
class UsageRecord:
    """A single usage record."""
    record_id: str
    provider: str
    task_type: str
    cost: float
    quality_score: float  # 0-10
    tokens: int
    timestamp: str = ""

    def __post_init__(self):
        if not self.record_id:
            self.record_id = f"use-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class ProviderStats:
    """Aggregated stats for a provider."""
    provider: str
    total_queries: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    avg_quality: float = 0.0
    avg_cost_per_query: float = 0.0
    cost_per_quality_point: float = 0.0
    task_types: Dict[str, int] = field(default_factory=dict)


@dataclass
class ArbitrageOpportunity:
    """A cost arbitrage opportunity."""
    task_type: str
    current_provider: str
    recommended_provider: str
    current_cost_per_query: float
    recommended_cost_per_query: float
    quality_difference: float  # positive = recommended is better
    savings_percent: float
    description: str


@dataclass
class SavingsReport:
    """Overall savings report."""
    total_spent: float
    baseline_would_have_cost: float
    total_saved: float
    savings_percent: float
    total_queries: int
    total_tokens: int
    provider_breakdown: List[Dict[str, Any]]
    best_value_provider: str
    top_arbitrage_opportunities: List[Dict[str, Any]]


class ValueOptimizer:
    """
    Cost arbitrage engine for multi-provider AI routing.

    Tracks cost vs quality across providers, identifies savings opportunities,
    and recommends optimal providers for each task type.
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/arbitrage"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._records: List[UsageRecord] = []
        self._load()

    def _load(self):
        """Load usage records from disk."""
        records_file = self.storage_dir / "usage.json"
        if records_file.exists():
            try:
                with open(records_file) as f:
                    self._records = [UsageRecord(**r) for r in json.load(f)]
            except Exception as e:
                logger.warning(f"Error loading usage records: {e}")

    def _save(self):
        """Save usage records to disk."""
        try:
            # Keep last 5000 records
            to_save = self._records[-5000:]
            with open(self.storage_dir / "usage.json", "w") as f:
                json.dump([asdict(r) for r in to_save], f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving usage records: {e}")

    def record_usage(
        self, provider: str, task_type: str, cost: float,
        quality_score: float = 7.0, tokens: int = 0,
    ) -> str:
        """Record a usage event. Returns record_id."""
        record = UsageRecord(
            record_id=f"use-{uuid.uuid4().hex[:8]}",
            provider=provider, task_type=task_type,
            cost=cost, quality_score=quality_score, tokens=tokens,
        )
        self._records.append(record)
        self._save()
        return record.record_id

    def get_best_provider(self, task_type: str) -> Dict[str, Any]:
        """Get the best provider for a task type based on historical data."""
        task_records = [r for r in self._records if r.task_type == task_type]

        if not task_records:
            # No data — recommend cheapest
            cheapest = min(PROVIDER_COSTS, key=PROVIDER_COSTS.get)
            return {
                "recommended": cheapest,
                "reason": "No historical data — recommending cheapest provider",
                "confidence": 0.3,
            }

        # Calculate value score per provider: quality / (cost + 0.001)
        provider_scores: Dict[str, List[float]] = defaultdict(list)
        provider_quality: Dict[str, List[float]] = defaultdict(list)
        provider_cost: Dict[str, List[float]] = defaultdict(list)

        for r in task_records:
            value = r.quality_score / max(r.cost, 0.001)
            provider_scores[r.provider].append(value)
            provider_quality[r.provider].append(r.quality_score)
            provider_cost[r.provider].append(r.cost)

        best_provider = None
        best_value = -1

        candidates = []
        for provider, scores in provider_scores.items():
            avg_value = sum(scores) / len(scores)
            avg_quality = sum(provider_quality[provider]) / len(provider_quality[provider])
            avg_cost = sum(provider_cost[provider]) / len(provider_cost[provider])
            candidates.append({
                "provider": provider,
                "avg_value_score": round(avg_value, 2),
                "avg_quality": round(avg_quality, 2),
                "avg_cost": round(avg_cost, 4),
                "sample_size": len(scores),
            })
            if avg_value > best_value:
                best_value = avg_value
                best_provider = provider

        candidates.sort(key=lambda c: c["avg_value_score"], reverse=True)

        return {
            "recommended": best_provider,
            "reason": f"Best value score for '{task_type}' tasks",
            "confidence": min(0.95, 0.5 + len(task_records) * 0.05),
            "candidates": candidates,
        }

    def get_savings_report(self) -> Dict[str, Any]:
        """Get comprehensive savings report."""
        if not self._records:
            return {"message": "No usage data recorded yet"}

        total_spent = sum(r.cost for r in self._records)
        total_tokens = sum(r.tokens for r in self._records)

        # What would it have cost using only the expensive baseline?
        baseline_rate = PROVIDER_COSTS.get(EXPENSIVE_BASELINE, 0.03)
        baseline_cost = (total_tokens / 1000) * baseline_rate if total_tokens > 0 else total_spent * 2

        saved = max(0, baseline_cost - total_spent)
        savings_pct = (saved / baseline_cost * 100) if baseline_cost > 0 else 0

        # Provider breakdown
        provider_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "queries": 0, "cost": 0.0, "tokens": 0, "quality_sum": 0.0,
        })
        for r in self._records:
            pd = provider_data[r.provider]
            pd["queries"] += 1
            pd["cost"] += r.cost
            pd["tokens"] += r.tokens
            pd["quality_sum"] += r.quality_score

        breakdown = []
        for provider, data in provider_data.items():
            avg_q = data["quality_sum"] / max(data["queries"], 1)
            breakdown.append({
                "provider": provider,
                "queries": data["queries"],
                "total_cost": round(data["cost"], 4),
                "total_tokens": data["tokens"],
                "avg_quality": round(avg_q, 2),
                "cost_per_query": round(data["cost"] / max(data["queries"], 1), 4),
            })

        breakdown.sort(key=lambda b: b["total_cost"], reverse=True)

        # Best value provider
        best_value = "unknown"
        best_ratio = -1
        for b in breakdown:
            ratio = b["avg_quality"] / max(b["cost_per_query"], 0.001)
            if ratio > best_ratio:
                best_ratio = ratio
                best_value = b["provider"]

        return {
            "total_spent": round(total_spent, 4),
            "baseline_would_have_cost": round(baseline_cost, 4),
            "total_saved": round(saved, 4),
            "savings_percent": round(savings_pct, 1),
            "total_queries": len(self._records),
            "total_tokens": total_tokens,
            "best_value_provider": best_value,
            "provider_breakdown": breakdown,
            "arbitrage_opportunities": [asdict(a) if hasattr(a, '__dataclass_fields__') else a
                                        for a in self.get_arbitrage_opportunities()[:5]],
        }

    def get_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """Find cost arbitrage opportunities."""
        opportunities = []

        # Group by task type
        task_providers: Dict[str, Dict[str, List[UsageRecord]]] = defaultdict(lambda: defaultdict(list))
        for r in self._records:
            task_providers[r.task_type][r.provider].append(r)

        for task_type, providers in task_providers.items():
            if len(providers) < 2:
                continue

            # Find most expensive and cheapest with comparable quality
            provider_stats = {}
            for provider, records in providers.items():
                avg_cost = sum(r.cost for r in records) / len(records)
                avg_quality = sum(r.quality_score for r in records) / len(records)
                provider_stats[provider] = {"cost": avg_cost, "quality": avg_quality, "count": len(records)}

            most_expensive = max(provider_stats, key=lambda p: provider_stats[p]["cost"])
            exp_stats = provider_stats[most_expensive]

            for provider, stats in provider_stats.items():
                if provider == most_expensive:
                    continue
                quality_diff = stats["quality"] - exp_stats["quality"]
                if quality_diff >= -1.0 and stats["cost"] < exp_stats["cost"]:
                    savings = ((exp_stats["cost"] - stats["cost"]) / max(exp_stats["cost"], 0.001)) * 100
                    opportunities.append(ArbitrageOpportunity(
                        task_type=task_type,
                        current_provider=most_expensive,
                        recommended_provider=provider,
                        current_cost_per_query=round(exp_stats["cost"], 4),
                        recommended_cost_per_query=round(stats["cost"], 4),
                        quality_difference=round(quality_diff, 2),
                        savings_percent=round(savings, 1),
                        description=f"Switch {task_type} from {most_expensive} to {provider}: "
                                    f"save {savings:.0f}% with {'same' if abs(quality_diff) < 0.5 else 'comparable'} quality",
                    ))

        return sorted(opportunities, key=lambda o: o.savings_percent, reverse=True)

    def get_provider_comparison(self, task_type: str = "") -> Dict[str, Any]:
        """Compare all providers, optionally for a specific task type."""
        records = self._records
        if task_type:
            records = [r for r in records if r.task_type == task_type]

        if not records:
            return {"message": f"No data for task type: {task_type}" if task_type else "No usage data"}

        comparison = {}
        for r in records:
            if r.provider not in comparison:
                comparison[r.provider] = {"costs": [], "qualities": [], "tokens": []}
            comparison[r.provider]["costs"].append(r.cost)
            comparison[r.provider]["qualities"].append(r.quality_score)
            comparison[r.provider]["tokens"].append(r.tokens)

        result = []
        for provider, data in comparison.items():
            n = len(data["costs"])
            result.append({
                "provider": provider,
                "queries": n,
                "avg_cost": round(sum(data["costs"]) / n, 4),
                "avg_quality": round(sum(data["qualities"]) / n, 2),
                "total_cost": round(sum(data["costs"]), 4),
                "total_tokens": sum(data["tokens"]),
                "value_ratio": round(
                    (sum(data["qualities"]) / n) / max(sum(data["costs"]) / n, 0.001), 2
                ),
            })

        result.sort(key=lambda r: r["value_ratio"], reverse=True)
        return {"task_type": task_type or "all", "providers": result}

    def get_cost_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get cost trends over time."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        recent = [r for r in self._records if r.timestamp >= cutoff_str]
        if not recent:
            return {"message": f"No data in last {days} days"}

        # Group by day
        daily: Dict[str, Dict[str, float]] = defaultdict(lambda: {"cost": 0.0, "queries": 0, "tokens": 0})
        for r in recent:
            day = r.timestamp[:10]
            daily[day]["cost"] += r.cost
            daily[day]["queries"] += 1
            daily[day]["tokens"] += r.tokens

        days_sorted = sorted(daily.keys())
        return {
            "period_days": days,
            "total_cost": round(sum(d["cost"] for d in daily.values()), 4),
            "total_queries": sum(int(d["queries"]) for d in daily.values()),
            "avg_daily_cost": round(sum(d["cost"] for d in daily.values()) / max(len(daily), 1), 4),
            "daily_data": [{
                "date": day,
                "cost": round(daily[day]["cost"], 4),
                "queries": int(daily[day]["queries"]),
                "tokens": int(daily[day]["tokens"]),
            } for day in days_sorted],
        }


def get_optimizer() -> ValueOptimizer:
    """Get singleton optimizer instance."""
    if not hasattr(get_optimizer, "_instance"):
        get_optimizer._instance = ValueOptimizer()
    return get_optimizer._instance
