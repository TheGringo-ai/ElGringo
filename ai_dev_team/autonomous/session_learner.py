"""
Session Learning System

Real-time learning that tracks agent performance during a session,
adapts routing, and shares successful solutions across the team.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable, Tuple
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Persistent storage path
LEARNING_DATA_DIR = Path.home() / ".ai-dev-team" / "learning"
LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TaskOutcome:
    """Outcome of a task execution."""
    task_id: str
    task_type: str
    agent_id: str
    prompt: str
    response: str
    success: bool
    confidence: float
    execution_time: float
    error: Optional[str] = None
    user_feedback: Optional[str] = None  # positive, negative, neutral
    corrections_needed: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPerformance:
    """Performance metrics for an agent."""
    agent_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_corrections: int = 0
    total_execution_time: float = 0.0
    confidence_sum: float = 0.0
    task_type_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    recent_outcomes: List[TaskOutcome] = field(default_factory=list)
    is_active: bool = True
    last_failure_streak: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.5  # Default for new agents
        return self.successful_tasks / self.total_tasks

    @property
    def avg_confidence(self) -> float:
        if self.total_tasks == 0:
            return 0.5
        return self.confidence_sum / self.total_tasks

    @property
    def avg_execution_time(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.total_execution_time / self.total_tasks

    @property
    def correction_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.total_corrections / self.total_tasks

    def get_task_type_score(self, task_type: str) -> float:
        """Get performance score for a specific task type."""
        if task_type not in self.task_type_performance:
            return 0.5  # Default
        perf = self.task_type_performance[task_type]
        if perf.get('total', 0) == 0:
            return 0.5
        return perf.get('successes', 0) / perf['total']


@dataclass
class Solution:
    """A successful solution that can be shared."""
    solution_id: str
    task_type: str
    problem_pattern: str
    solution_summary: str
    full_response: str
    agent_id: str
    confidence: float
    reuse_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


class SessionLearner:
    """
    Real-time session learning that tracks agent performance,
    adapts routing, and enables knowledge sharing.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        min_confidence: float = 0.6,
        learning_rate: float = 0.1
    ):
        """
        Initialize the session learner.

        Args:
            failure_threshold: Consecutive failures before agent is deprioritized
            min_confidence: Minimum confidence to consider success
            learning_rate: How fast to adapt weights (0-1)
        """
        self.failure_threshold = failure_threshold
        self.min_confidence = min_confidence
        self.learning_rate = learning_rate

        # Session state
        self.session_start = datetime.now()
        self.agent_performance: Dict[str, AgentPerformance] = {}
        self.task_outcomes: List[TaskOutcome] = []
        self.solutions: Dict[str, Solution] = {}
        self.routing_weights: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Callbacks
        self.on_agent_swap: Optional[Callable] = None
        self.on_solution_found: Optional[Callable] = None

    def register_agent(self, agent_id: str):
        """Register an agent for tracking."""
        if agent_id not in self.agent_performance:
            self.agent_performance[agent_id] = AgentPerformance(agent_id=agent_id)
            logger.info(f"Registered agent for session learning: {agent_id}")

    def record_outcome(self, outcome: TaskOutcome):
        """
        Record the outcome of a task execution.

        Args:
            outcome: The task outcome to record
        """
        self.task_outcomes.append(outcome)

        # Update agent performance
        agent_id = outcome.agent_id
        if agent_id not in self.agent_performance:
            self.register_agent(agent_id)

        perf = self.agent_performance[agent_id]
        perf.total_tasks += 1
        perf.total_execution_time += outcome.execution_time
        perf.confidence_sum += outcome.confidence
        perf.total_corrections += outcome.corrections_needed

        if outcome.success and outcome.confidence >= self.min_confidence:
            perf.successful_tasks += 1
            perf.last_failure_streak = 0

            # Store successful solution
            if outcome.confidence >= 0.8:
                self._store_solution(outcome)
        else:
            perf.failed_tasks += 1
            perf.last_failure_streak += 1

            # Check if agent should be deprioritized
            if perf.last_failure_streak >= self.failure_threshold:
                self._handle_agent_failures(agent_id, outcome.task_type)

        # Update task type performance
        self._update_task_type_performance(perf, outcome)

        # Update routing weights
        self._update_routing_weights(outcome)

        # Keep only recent outcomes
        perf.recent_outcomes.append(outcome)
        if len(perf.recent_outcomes) > 20:
            perf.recent_outcomes.pop(0)

        logger.debug(f"Recorded outcome for {agent_id}: success={outcome.success}, "
                    f"confidence={outcome.confidence:.2f}")

    def _update_task_type_performance(self, perf: AgentPerformance, outcome: TaskOutcome):
        """Update performance metrics for a specific task type."""
        task_type = outcome.task_type
        if task_type not in perf.task_type_performance:
            perf.task_type_performance[task_type] = {'total': 0, 'successes': 0}

        perf.task_type_performance[task_type]['total'] += 1
        if outcome.success:
            perf.task_type_performance[task_type]['successes'] += 1

    def _update_routing_weights(self, outcome: TaskOutcome):
        """Update routing weights based on outcome."""
        agent_id = outcome.agent_id
        task_type = outcome.task_type

        current_weight = self.routing_weights[task_type].get(agent_id, 0.5)

        # Adjust weight based on outcome
        if outcome.success:
            # Increase weight, more for high confidence
            adjustment = self.learning_rate * outcome.confidence
            new_weight = min(1.0, current_weight + adjustment)
        else:
            # Decrease weight
            adjustment = self.learning_rate * (1 - outcome.confidence)
            new_weight = max(0.1, current_weight - adjustment)

        self.routing_weights[task_type][agent_id] = new_weight
        logger.debug(f"Updated routing weight for {agent_id}/{task_type}: "
                    f"{current_weight:.2f} -> {new_weight:.2f}")

    def _handle_agent_failures(self, agent_id: str, task_type: str):
        """Handle an agent that has failed multiple times."""
        logger.warning(f"Agent {agent_id} has failed {self.failure_threshold}+ times "
                      f"consecutively on {task_type} tasks")

        # Significantly reduce routing weight
        self.routing_weights[task_type][agent_id] = 0.1

        # Notify if callback set
        if self.on_agent_swap:
            alternative = self.get_best_agent(task_type, exclude=[agent_id])
            self.on_agent_swap(agent_id, alternative, task_type)

    def _store_solution(self, outcome: TaskOutcome):
        """Store a successful solution for potential reuse."""
        solution_id = f"sol_{len(self.solutions)}"
        solution = Solution(
            solution_id=solution_id,
            task_type=outcome.task_type,
            problem_pattern=self._extract_problem_pattern(outcome.prompt),
            solution_summary=self._extract_solution_summary(outcome.response),
            full_response=outcome.response,
            agent_id=outcome.agent_id,
            confidence=outcome.confidence,
            tags=self._extract_tags(outcome.prompt, outcome.response)
        )
        self.solutions[solution_id] = solution

        if self.on_solution_found:
            self.on_solution_found(solution)

        logger.info(f"Stored solution {solution_id} from {outcome.agent_id}")

    def _extract_problem_pattern(self, prompt: str) -> str:
        """Extract a pattern from the problem description."""
        # Simplified - take first 200 chars
        return prompt[:200].strip()

    def _extract_solution_summary(self, response: str) -> str:
        """Extract a summary from the solution."""
        # Take first paragraph or 300 chars
        lines = response.split('\n\n')
        summary = lines[0] if lines else response[:300]
        return summary[:300].strip()

    def _extract_tags(self, prompt: str, response: str) -> List[str]:
        """Extract relevant tags from prompt and response."""
        tags = []
        text = (prompt + ' ' + response).lower()

        tag_keywords = {
            'python': ['python', '.py', 'def ', 'import '],
            'javascript': ['javascript', 'js', 'function', 'const ', 'let '],
            'api': ['api', 'endpoint', 'rest', 'request', 'response'],
            'database': ['database', 'sql', 'query', 'table', 'mongodb'],
            'testing': ['test', 'assert', 'mock', 'pytest', 'jest'],
            'security': ['security', 'auth', 'token', 'encrypt', 'password'],
            'frontend': ['react', 'vue', 'html', 'css', 'component'],
            'backend': ['server', 'backend', 'express', 'fastapi', 'django'],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)

        return tags

    def get_best_agent(
        self,
        task_type: str,
        exclude: List[str] = None
    ) -> Optional[str]:
        """
        Get the best agent for a task type based on session performance.

        Args:
            task_type: Type of task
            exclude: Agents to exclude

        Returns:
            Agent ID of best performer, or None
        """
        exclude = exclude or []

        candidates = []
        for agent_id, perf in self.agent_performance.items():
            if agent_id in exclude or not perf.is_active:
                continue

            # Calculate score based on multiple factors
            weight = self.routing_weights[task_type].get(agent_id, 0.5)
            success_rate = perf.success_rate
            task_score = perf.get_task_type_score(task_type)
            recency_penalty = 0.1 * perf.last_failure_streak

            score = (
                0.3 * weight +
                0.3 * success_rate +
                0.3 * task_score +
                0.1 * perf.avg_confidence -
                recency_penalty
            )

            candidates.append((agent_id, score))

        if not candidates:
            return None

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def get_similar_solution(
        self,
        prompt: str,
        task_type: str = None,
        min_confidence: float = 0.7
    ) -> Optional[Solution]:
        """
        Find a similar successful solution.

        Args:
            prompt: The current prompt
            task_type: Filter by task type
            min_confidence: Minimum confidence threshold

        Returns:
            Similar solution if found
        """
        prompt_lower = prompt.lower()
        best_match = None
        best_score = 0.0

        for solution in self.solutions.values():
            if solution.confidence < min_confidence:
                continue
            if task_type and solution.task_type != task_type:
                continue

            # Simple similarity based on shared words
            solution_words = set(solution.problem_pattern.lower().split())
            prompt_words = set(prompt_lower.split())
            shared = len(solution_words & prompt_words)
            total = len(solution_words | prompt_words)
            similarity = shared / total if total > 0 else 0

            if similarity > best_score and similarity > 0.3:
                best_score = similarity
                best_match = solution

        return best_match

    def share_solution_with_team(
        self,
        solution: Solution,
        execute_fn: Callable
    ) -> Dict[str, str]:
        """
        Share a successful solution with other agents for learning.

        Args:
            solution: The solution to share
            execute_fn: Function to communicate with agents

        Returns:
            Dict of agent acknowledgments
        """
        # In practice, this would update each agent's context or memory
        # For now, we track that the solution exists and can be referenced
        solution.reuse_count += 1

        logger.info(f"Shared solution {solution.solution_id} with team "
                   f"(reuse count: {solution.reuse_count})")

        return {'status': 'shared', 'solution_id': solution.solution_id}

    def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        total_tasks = len(self.task_outcomes)
        successful = sum(1 for o in self.task_outcomes if o.success)

        agent_stats = {}
        for agent_id, perf in self.agent_performance.items():
            agent_stats[agent_id] = {
                'success_rate': perf.success_rate,
                'avg_confidence': perf.avg_confidence,
                'avg_execution_time': perf.avg_execution_time,
                'correction_rate': perf.correction_rate,
                'total_tasks': perf.total_tasks,
                'is_active': perf.is_active,
                'task_types': {
                    tt: {'score': perf.get_task_type_score(tt), **data}
                    for tt, data in perf.task_type_performance.items()
                }
            }

        return {
            'session_duration': (datetime.now() - self.session_start).total_seconds(),
            'total_tasks': total_tasks,
            'successful_tasks': successful,
            'overall_success_rate': successful / total_tasks if total_tasks > 0 else 0,
            'solutions_stored': len(self.solutions),
            'agent_performance': agent_stats,
            'routing_weights': dict(self.routing_weights),
            'top_solutions': [
                {
                    'id': s.solution_id,
                    'task_type': s.task_type,
                    'confidence': s.confidence,
                    'reuse_count': s.reuse_count
                }
                for s in sorted(
                    self.solutions.values(),
                    key=lambda x: x.confidence,
                    reverse=True
                )[:5]
            ]
        }

    def get_recommendations(self) -> List[str]:
        """Get recommendations for improving performance."""
        recommendations = []

        # Analyze agent performance
        for agent_id, perf in self.agent_performance.items():
            if perf.success_rate < 0.5 and perf.total_tasks >= 3:
                recommendations.append(
                    f"Agent {agent_id} has low success rate ({perf.success_rate:.0%}). "
                    f"Consider using alternatives for complex tasks."
                )

            if perf.correction_rate > 0.5:
                recommendations.append(
                    f"Agent {agent_id} requires frequent corrections. "
                    f"Try using more detailed prompts."
                )

        # Analyze task types
        task_type_success = defaultdict(lambda: {'total': 0, 'success': 0})
        for outcome in self.task_outcomes:
            task_type_success[outcome.task_type]['total'] += 1
            if outcome.success:
                task_type_success[outcome.task_type]['success'] += 1

        for task_type, stats in task_type_success.items():
            rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
            if rate < 0.6 and stats['total'] >= 3:
                best_agent = self.get_best_agent(task_type)
                recommendations.append(
                    f"'{task_type}' tasks have low success rate ({rate:.0%}). "
                    f"Best agent: {best_agent}"
                )

        return recommendations

    def reset_session(self):
        """Reset session data for a fresh start."""
        self.session_start = datetime.now()
        self.task_outcomes.clear()
        self.solutions.clear()

        # Reset agent performance but keep agents registered
        for perf in self.agent_performance.values():
            perf.total_tasks = 0
            perf.successful_tasks = 0
            perf.failed_tasks = 0
            perf.total_corrections = 0
            perf.total_execution_time = 0.0
            perf.confidence_sum = 0.0
            perf.task_type_performance.clear()
            perf.recent_outcomes.clear()
            perf.last_failure_streak = 0

        self.routing_weights.clear()
        logger.info("Session learning state reset")

    def save(self, filename: str = "session_learning.json"):
        """
        Save learning data to persistent storage.

        Args:
            filename: Name of the file to save to
        """
        filepath = LEARNING_DATA_DIR / filename

        # Serialize agent performance
        agent_data = {}
        for agent_id, perf in self.agent_performance.items():
            agent_data[agent_id] = {
                'agent_id': perf.agent_id,
                'total_tasks': perf.total_tasks,
                'successful_tasks': perf.successful_tasks,
                'failed_tasks': perf.failed_tasks,
                'total_corrections': perf.total_corrections,
                'total_execution_time': perf.total_execution_time,
                'confidence_sum': perf.confidence_sum,
                'task_type_performance': perf.task_type_performance,
                'is_active': perf.is_active,
                'last_failure_streak': perf.last_failure_streak,
            }

        # Serialize solutions
        solution_data = {}
        for sol_id, sol in self.solutions.items():
            solution_data[sol_id] = {
                'solution_id': sol.solution_id,
                'task_type': sol.task_type,
                'problem_pattern': sol.problem_pattern,
                'solution_summary': sol.solution_summary,
                'full_response': sol.full_response,
                'agent_id': sol.agent_id,
                'confidence': sol.confidence,
                'reuse_count': sol.reuse_count,
                'created_at': sol.created_at.isoformat(),
                'tags': sol.tags,
            }

        # Serialize routing weights (convert defaultdict to dict)
        routing_data = {k: dict(v) for k, v in self.routing_weights.items()}

        data = {
            'version': '1.0',
            'saved_at': datetime.now().isoformat(),
            'agent_performance': agent_data,
            'solutions': solution_data,
            'routing_weights': routing_data,
            'total_outcomes': len(self.task_outcomes),
        }

        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved session learning to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save session learning: {e}")

    def load(self, filename: str = "session_learning.json") -> bool:
        """
        Load learning data from persistent storage.

        Args:
            filename: Name of the file to load from

        Returns:
            True if loaded successfully, False otherwise
        """
        filepath = LEARNING_DATA_DIR / filename

        if not filepath.exists():
            logger.info(f"No saved learning data found at {filepath}")
            return False

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Load agent performance
            for agent_id, agent_data in data.get('agent_performance', {}).items():
                perf = AgentPerformance(
                    agent_id=agent_data['agent_id'],
                    total_tasks=agent_data.get('total_tasks', 0),
                    successful_tasks=agent_data.get('successful_tasks', 0),
                    failed_tasks=agent_data.get('failed_tasks', 0),
                    total_corrections=agent_data.get('total_corrections', 0),
                    total_execution_time=agent_data.get('total_execution_time', 0.0),
                    confidence_sum=agent_data.get('confidence_sum', 0.0),
                    task_type_performance=agent_data.get('task_type_performance', {}),
                    is_active=agent_data.get('is_active', True),
                    last_failure_streak=agent_data.get('last_failure_streak', 0),
                )
                self.agent_performance[agent_id] = perf

            # Load solutions
            for sol_id, sol_data in data.get('solutions', {}).items():
                created_at = datetime.fromisoformat(sol_data['created_at'])
                sol = Solution(
                    solution_id=sol_data['solution_id'],
                    task_type=sol_data['task_type'],
                    problem_pattern=sol_data['problem_pattern'],
                    solution_summary=sol_data['solution_summary'],
                    full_response=sol_data['full_response'],
                    agent_id=sol_data['agent_id'],
                    confidence=sol_data['confidence'],
                    reuse_count=sol_data.get('reuse_count', 0),
                    created_at=created_at,
                    tags=sol_data.get('tags', []),
                )
                self.solutions[sol_id] = sol

            # Load routing weights
            for task_type, weights in data.get('routing_weights', {}).items():
                self.routing_weights[task_type] = weights

            logger.info(f"Loaded session learning from {filepath}: "
                       f"{len(self.agent_performance)} agents, "
                       f"{len(self.solutions)} solutions")
            return True

        except Exception as e:
            logger.error(f"Failed to load session learning: {e}")
            return False

    @classmethod
    def load_or_create(
        cls,
        filename: str = "session_learning.json",
        **kwargs
    ) -> 'SessionLearner':
        """
        Load existing learning data or create a new instance.

        Args:
            filename: Name of the file to load from
            **kwargs: Arguments for SessionLearner constructor

        Returns:
            SessionLearner instance with loaded data
        """
        learner = cls(**kwargs)
        learner.load(filename)
        return learner


class TeamAdapter:
    """
    Adapts team composition and behavior based on session learning.
    """

    def __init__(self, session_learner: SessionLearner):
        self.learner = session_learner
        self.swap_history: List[Dict] = []

    def suggest_team_composition(
        self,
        task_types: List[str]
    ) -> Dict[str, str]:
        """
        Suggest optimal team composition for given task types.

        Args:
            task_types: List of task types to handle

        Returns:
            Dict mapping task_type to recommended agent
        """
        composition = {}
        used_agents = set()

        for task_type in task_types:
            best = self.learner.get_best_agent(task_type, exclude=list(used_agents))
            if best:
                composition[task_type] = best
                used_agents.add(best)

        return composition

    def should_swap_agent(
        self,
        current_agent: str,
        task_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if an agent should be swapped.

        Args:
            current_agent: Current agent ID
            task_type: Task type being performed

        Returns:
            (should_swap, alternative_agent)
        """
        if current_agent not in self.learner.agent_performance:
            return False, None

        perf = self.learner.agent_performance[current_agent]

        # Check failure streak
        if perf.last_failure_streak >= self.learner.failure_threshold:
            alternative = self.learner.get_best_agent(task_type, exclude=[current_agent])
            if alternative:
                return True, alternative

        # Check if significantly better agent available
        current_score = perf.get_task_type_score(task_type)
        best_agent = self.learner.get_best_agent(task_type, exclude=[current_agent])

        if best_agent:
            best_perf = self.learner.agent_performance[best_agent]
            best_score = best_perf.get_task_type_score(task_type)

            # Swap if alternative is significantly better
            if best_score > current_score + 0.2:
                return True, best_agent

        return False, None

    def record_swap(self, from_agent: str, to_agent: str, reason: str):
        """Record an agent swap for analysis."""
        self.swap_history.append({
            'from': from_agent,
            'to': to_agent,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        logger.info(f"Agent swap recorded: {from_agent} -> {to_agent} ({reason})")

    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get statistics on team adaptation."""
        return {
            'total_swaps': len(self.swap_history),
            'recent_swaps': self.swap_history[-5:],
            'recommendations': self.learner.get_recommendations()
        }
