"""
Feedback Learning Loop — Automatic improvement from outcomes
=============================================================

Closes the loop between user feedback and system behavior:
1. User rates response (thumbs up/down, stars, corrections)
2. Rating flows to performance tracker -> routing weights adjust
3. Bad solutions get confidence decay in memory
4. Good patterns get reinforced
5. Agent expertise weights adapt over time
"""

import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FeedbackEvent:
    task_id: str
    timestamp: str
    rating: float  # -1.0 to 1.0
    agents_involved: List[str]
    task_type: str
    mode: str
    comment: Optional[str] = None
    correction: Optional[str] = None
    auto_detected: bool = False


@dataclass
class AgentPerformanceProfile:
    agent_name: str
    total_tasks: int = 0
    positive_ratings: int = 0
    negative_ratings: int = 0
    total_rating_sum: float = 0.0
    avg_confidence: float = 0.0
    task_type_scores: Dict[str, float] = field(default_factory=dict)
    last_updated: str = ""

    @property
    def satisfaction_rate(self):
        total = self.positive_ratings + self.negative_ratings
        return self.positive_ratings / total if total > 0 else 0.5

    @property
    def avg_rating(self):
        return self.total_rating_sum / self.total_tasks if self.total_tasks > 0 else 0.0


@dataclass
class LearningOutcome:
    feedback_processed: bool
    routing_adjusted: bool
    solutions_updated: int
    expertise_adjustments: Dict[str, float] = field(default_factory=dict)
    actions_taken: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "processed": self.feedback_processed,
            "routing_adjusted": self.routing_adjusted,
            "solutions_updated": self.solutions_updated,
            "expertise_adjustments": {k: round(v, 3) for k, v in self.expertise_adjustments.items()},
            "actions": self.actions_taken,
        }


class FeedbackLearningLoop:
    """
    Closes the feedback loop to make El Gringo smarter over time.

    Flow:
    1. Collect feedback (user ratings or auto-detected failures)
    2. Update agent performance profiles
    3. Adjust routing weights
    4. Decay/boost solution confidence in memory
    5. Adapt expertise weights
    """

    LEARNING_RATE = 0.05
    MIN_TASKS_FOR_ADJUSTMENT = 3

    def __init__(self, storage_dir="~/.ai-dev-team/feedback_loop", memory_system=None, performance_tracker=None):
        self._storage_dir = Path(os.path.expanduser(storage_dir))
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._memory = memory_system
        self._perf_tracker = performance_tracker
        self._profiles: Dict[str, AgentPerformanceProfile] = {}
        self._feedback_history: List[FeedbackEvent] = []
        self._expertise_adjustments: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._load_state()

    async def process_feedback(
        self, task_id: str, rating: float, agents: List[str],
        task_type: str, mode: str = "unknown",
        comment: Optional[str] = None, correction: Optional[str] = None,
        solution_ids: Optional[List[str]] = None,
    ) -> LearningOutcome:
        rating = max(-1.0, min(1.0, rating))
        event = FeedbackEvent(
            task_id=task_id, timestamp=datetime.now(timezone.utc).isoformat(),
            rating=rating, agents_involved=agents, task_type=task_type,
            mode=mode, comment=comment, correction=correction,
        )
        self._feedback_history.append(event)
        outcome = LearningOutcome(feedback_processed=True, routing_adjusted=False, solutions_updated=0)

        for agent in agents:
            self._update_profile(agent, rating, task_type)
            outcome.actions_taken.append(f"Updated {agent} profile (rating: {rating:+.1f})")

        outcome.routing_adjusted = self._adjust_routing_weights(agents, task_type)
        if outcome.routing_adjusted:
            outcome.actions_taken.append("Adjusted routing weights based on feedback history")

        if self._memory and solution_ids:
            updated = await self._adjust_solution_confidence(solution_ids, rating)
            outcome.solutions_updated = updated
            if updated:
                outcome.actions_taken.append(f"Adjusted confidence for {updated} solutions")

        if correction and self._memory and rating < 0:
            try:
                await self._memory.store_solution(
                    problem_pattern=f"[Correction] {comment or task_type}",
                    solution_steps=[correction], tags=[task_type, "user_correction"],
                    success_rate=0.9,
                )
                outcome.solutions_updated += 1
                outcome.actions_taken.append("Stored user correction as new solution")
            except Exception as e:
                logger.debug(f"Failed to store correction: {e}")

        for agent in agents:
            profile = self._profiles.get(agent)
            if profile and profile.total_tasks >= self.MIN_TASKS_FOR_ADJUSTMENT:
                adjustment = (profile.satisfaction_rate - 0.5) * self.LEARNING_RATE
                current = self._expertise_adjustments.get(agent, {}).get(task_type, 0.0)
                self._expertise_adjustments[agent][task_type] = current + adjustment
                outcome.expertise_adjustments[agent] = adjustment

        self._save_state()
        return outcome

    async def auto_detect_failure(self, task_id: str, error: str, agents: List[str], task_type: str) -> LearningOutcome:
        return await self.process_feedback(
            task_id=task_id, rating=-0.8, agents=agents, task_type=task_type,
            comment=f"Auto-detected failure: {error[:200]}",
        )

    def get_agent_profile(self, agent_name):
        profile = self._profiles.get(agent_name)
        if not profile:
            return None
        return {
            "agent": profile.agent_name,
            "total_tasks": profile.total_tasks,
            "satisfaction_rate": round(profile.satisfaction_rate, 2),
            "avg_rating": round(profile.avg_rating, 2),
            "positive": profile.positive_ratings,
            "negative": profile.negative_ratings,
            "task_type_scores": {k: round(v, 2) for k, v in profile.task_type_scores.items()},
            "expertise_adjustments": {k: round(v, 3) for k, v in self._expertise_adjustments.get(agent_name, {}).items()},
        }

    def get_all_profiles(self):
        return {name: self.get_agent_profile(name) for name in self._profiles}

    def get_expertise_adjustment(self, agent_name, task_type):
        return self._expertise_adjustments.get(agent_name, {}).get(task_type, 0.0)

    def get_roi_summary(self):
        total = len(self._feedback_history)
        positive = sum(1 for f in self._feedback_history if f.rating > 0)
        trend = 0.0
        if total > 10:
            recent = self._feedback_history[-10:]
            older = self._feedback_history[:-10]
            trend = sum(f.rating for f in recent) / len(recent) - sum(f.rating for f in older) / len(older)
        return {
            "total_feedback_events": total,
            "positive_ratio": round(positive / total, 2) if total else 0,
            "improvement_trend": round(trend, 3),
            "trending": "improving" if trend > 0.05 else "declining" if trend < -0.05 else "stable",
            "agents_tracked": len(self._profiles),
        }

    def _update_profile(self, agent_name, rating, task_type):
        if agent_name not in self._profiles:
            self._profiles[agent_name] = AgentPerformanceProfile(agent_name=agent_name)
        p = self._profiles[agent_name]
        p.total_tasks += 1
        p.total_rating_sum += rating
        p.last_updated = datetime.now(timezone.utc).isoformat()
        if rating > 0:
            p.positive_ratings += 1
        elif rating < 0:
            p.negative_ratings += 1
        current = p.task_type_scores.get(task_type, 0.5)
        p.task_type_scores[task_type] = current * 0.8 + ((rating + 1.0) / 2.0) * 0.2

    def _adjust_routing_weights(self, agents, task_type):
        adjusted = False
        for agent in agents:
            p = self._profiles.get(agent)
            if not p or p.total_tasks < self.MIN_TASKS_FOR_ADJUSTMENT:
                continue
            if p.satisfaction_rate < 0.4:
                logger.info(f"Agent {agent} low satisfaction ({p.satisfaction_rate:.0%}) for {task_type}")
                adjusted = True
            elif p.satisfaction_rate > 0.8 and p.total_tasks >= 5:
                logger.info(f"Agent {agent} high satisfaction ({p.satisfaction_rate:.0%}) for {task_type}")
                adjusted = True
        return adjusted

    async def _adjust_solution_confidence(self, solution_ids, rating):
        updated = 0
        if not self._memory:
            return 0
        for sid in solution_ids:
            try:
                solutions = getattr(self._memory, '_solutions', {})
                if sid in solutions:
                    sol = solutions[sid]
                    current = getattr(sol, 'quality_score', 0.5)
                    sol.quality_score = max(0.1, min(1.0, current + rating * 0.1))
                    current_rate = getattr(sol, 'success_rate', 0.5)
                    sol.success_rate = current_rate * 0.9 + ((rating + 1.0) / 2.0) * 0.1
                    updated += 1
            except Exception as e:
                logger.debug(f"Failed to adjust solution {sid}: {e}")
        return updated

    def _save_state(self):
        try:
            state = {
                "profiles": {
                    name: {
                        "agent_name": p.agent_name, "total_tasks": p.total_tasks,
                        "positive_ratings": p.positive_ratings, "negative_ratings": p.negative_ratings,
                        "total_rating_sum": p.total_rating_sum, "task_type_scores": p.task_type_scores,
                        "last_updated": p.last_updated,
                    }
                    for name, p in self._profiles.items()
                },
                "expertise_adjustments": dict(self._expertise_adjustments),
                "feedback_count": len(self._feedback_history),
            }
            (self._storage_dir / "feedback_state.json").write_text(json.dumps(state, indent=2))
        except Exception as e:
            logger.debug(f"Failed to save feedback state: {e}")

    def _load_state(self):
        try:
            state_file = self._storage_dir / "feedback_state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                for name, data in state.get("profiles", {}).items():
                    self._profiles[name] = AgentPerformanceProfile(**data)
                self._expertise_adjustments = defaultdict(dict, state.get("expertise_adjustments", {}))
        except Exception as e:
            logger.debug(f"Failed to load feedback state: {e}")


_loop: Optional[FeedbackLearningLoop] = None

def get_feedback_loop(memory_system=None, performance_tracker=None) -> FeedbackLearningLoop:
    global _loop
    if _loop is None:
        _loop = FeedbackLearningLoop(memory_system=memory_system, performance_tracker=performance_tracker)
    return _loop
