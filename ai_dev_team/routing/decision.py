"""
Routing Decision - Explainable Model Selection
===============================================

Provides transparency into why specific agents are chosen for tasks.
Every routing decision is logged and can be explained to developers.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class DecisionFactor(Enum):
    """Factors that influence routing decisions"""
    TASK_TYPE_MATCH = "task_type_match"
    PERFORMANCE_HISTORY = "performance_history"
    COST_CONSTRAINT = "cost_constraint"
    USER_PREFERENCE = "user_preference"
    AVAILABILITY = "availability"
    COMPLEXITY_MATCH = "complexity_match"
    DOMAIN_EXPERTISE = "domain_expertise"
    FALLBACK = "fallback"
    DETERMINISTIC_MODE = "deterministic_mode"


@dataclass
class AgentScore:
    """Score breakdown for a single agent"""
    agent_name: str
    total_score: float
    breakdown: Dict[str, float] = field(default_factory=dict)
    eligible: bool = True
    rejection_reason: Optional[str] = None


@dataclass
class RoutingDecision:
    """
    Explains why a specific agent was selected for a task.

    Every request through the AI Team produces one of these,
    enabling full transparency and debugging of routing logic.
    """

    # Selection result
    selected_agent: str
    task_type: str
    complexity: str
    confidence: float

    # Explainability
    candidates: List[AgentScore] = field(default_factory=list)
    decision_factors: List[str] = field(default_factory=list)
    primary_reason: str = ""

    # Constraints
    constraints_applied: Dict[str, Any] = field(default_factory=dict)
    constraints_matched: List[str] = field(default_factory=list)
    constraints_violated: List[str] = field(default_factory=list)

    # Fallback chain
    fallback_order: List[str] = field(default_factory=list)
    is_fallback: bool = False
    original_choice: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decision_time_ms: float = 0.0
    request_id: str = ""

    def explain(self, verbose: bool = False) -> str:
        """
        Human-readable explanation of the routing decision.

        Args:
            verbose: Include full candidate scoring

        Returns:
            Formatted explanation string
        """
        lines = [
            f"Selected: {self.selected_agent}",
            f"Task: {self.task_type} ({self.complexity} complexity)",
            f"Reason: {self.primary_reason}",
        ]

        if self.is_fallback:
            lines.append(f"Note: Fallback from {self.original_choice}")

        if self.constraints_matched:
            lines.append(f"Constraints: {', '.join(self.constraints_matched)}")

        if self.fallback_order:
            lines.append(f"Fallbacks: {' → '.join(self.fallback_order[:3])}")

        if verbose and self.candidates:
            lines.append("\nCandidate Scores:")
            for c in sorted(self.candidates, key=lambda x: x.total_score, reverse=True)[:5]:
                status = "✓" if c.eligible else f"✗ ({c.rejection_reason})"
                lines.append(f"  {c.agent_name}: {c.total_score:.2f} {status}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            "selected_agent": self.selected_agent,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "primary_reason": self.primary_reason,
            "decision_factors": self.decision_factors,
            "constraints_matched": self.constraints_matched,
            "fallback_order": self.fallback_order,
            "is_fallback": self.is_fallback,
            "timestamp": self.timestamp.isoformat(),
            "decision_time_ms": self.decision_time_ms,
            "candidates": [
                {
                    "agent": c.agent_name,
                    "score": c.total_score,
                    "eligible": c.eligible,
                }
                for c in self.candidates
            ],
        }

    @classmethod
    def create_simple(
        cls,
        agent: str,
        task_type: str,
        reason: str,
        fallbacks: List[str] = None,
    ) -> "RoutingDecision":
        """Create a simple routing decision without full scoring"""
        return cls(
            selected_agent=agent,
            task_type=task_type,
            complexity="medium",
            confidence=0.8,
            primary_reason=reason,
            fallback_order=fallbacks or [],
        )


class DecisionLogger:
    """
    Logs routing decisions for analysis and debugging.

    Stores decisions locally for:
    - Debugging routing issues
    - Analyzing agent performance
    - Optimizing routing rules
    """

    def __init__(self, max_history: int = 1000):
        self._history: List[RoutingDecision] = []
        self._max_history = max_history

    def log(self, decision: RoutingDecision):
        """Log a routing decision"""
        self._history.append(decision)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_recent(self, count: int = 10) -> List[RoutingDecision]:
        """Get recent decisions"""
        return self._history[-count:]

    def get_by_agent(self, agent_name: str) -> List[RoutingDecision]:
        """Get decisions for a specific agent"""
        return [d for d in self._history if d.selected_agent == agent_name]

    def get_fallbacks(self) -> List[RoutingDecision]:
        """Get decisions that used fallback"""
        return [d for d in self._history if d.is_fallback]

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        if not self._history:
            return {"total": 0}

        agent_counts = {}
        task_counts = {}
        fallback_count = 0

        for d in self._history:
            agent_counts[d.selected_agent] = agent_counts.get(d.selected_agent, 0) + 1
            task_counts[d.task_type] = task_counts.get(d.task_type, 0) + 1
            if d.is_fallback:
                fallback_count += 1

        return {
            "total": len(self._history),
            "by_agent": agent_counts,
            "by_task": task_counts,
            "fallback_rate": fallback_count / len(self._history),
            "avg_decision_time_ms": sum(d.decision_time_ms for d in self._history) / len(self._history),
        }


# Global decision logger
_decision_logger: Optional[DecisionLogger] = None


def get_decision_logger() -> DecisionLogger:
    """Get the global decision logger"""
    global _decision_logger
    if _decision_logger is None:
        _decision_logger = DecisionLogger()
    return _decision_logger
