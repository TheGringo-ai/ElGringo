"""
Autonomous Executor - Extracted from AIDevTeam orchestrator
=============================================================

Handles autonomous collaboration, task decomposition, self-correction,
and session learning.
"""

import logging
import time
import uuid
from typing import Any, Dict, Optional

from . import TaskOutcome, GraphExecutor

logger = logging.getLogger(__name__)


class AutonomousExecutor:
    """
    Manages autonomous AI collaboration with self-correction and task decomposition.

    Extracted from AIDevTeam to reduce orchestrator complexity.
    Takes a reference to the orchestrator for access to agents, router, and learning.
    """

    def __init__(self, orchestrator):
        self._orchestrator = orchestrator

    @property
    def _task_router(self):
        return self._orchestrator._task_router

    @property
    def _session_learner(self):
        return self._orchestrator._session_learner

    @property
    def _self_corrector(self):
        return self._orchestrator._self_corrector

    @property
    def _task_decomposer(self):
        return self._orchestrator._task_decomposer

    @property
    def _team_adapter(self):
        return self._orchestrator._team_adapter

    async def auto_collaborate(
        self,
        goal: str,
        context: Dict[str, Any] = None,
        enable_correction: bool = True,
        enable_decomposition: bool = True,
        on_progress: callable = None
    ) -> Dict[str, Any]:
        """
        Fully autonomous collaboration with self-correction and task decomposition.

        This is the main entry point for autonomous coding assistance.

        Args:
            goal: High-level goal to accomplish
            context: Additional context (code, project info, etc.)
            enable_correction: Auto-correct failed responses
            enable_decomposition: Break complex goals into subtasks
            on_progress: Callback for progress updates

        Returns:
            Dict with results, including all subtask outputs
        """
        start_time = time.time()
        context = context or {}

        # Register agents with session learner
        for agent_id in self._orchestrator.available_agents:
            self._session_learner.register_agent(agent_id)

        # Check if task is complex enough to decompose
        is_complex = len(goal.split()) > 20 or any(
            kw in goal.lower() for kw in ['build', 'create', 'implement', 'develop', 'full']
        )

        if enable_decomposition and is_complex:
            # Decompose and execute
            logger.info(f"Decomposing complex goal: {goal[:50]}...")
            result = await self._execute_with_decomposition(goal, context, on_progress)
        else:
            # Direct execution with correction
            result = await self._execute_with_correction(
                goal, context, enable_correction
            )

        # Update session learner
        outcome = TaskOutcome(
            task_id=str(uuid.uuid4()),
            task_type=self._task_router.classify(goal).primary_type.value,
            agent_id=result.get('agent', 'unknown'),
            prompt=goal,
            response=result.get('response', ''),
            success=result.get('success', False),
            confidence=result.get('confidence', 0.5),
            execution_time=time.time() - start_time,
            corrections_needed=result.get('corrections', 0)
        )
        self._session_learner.record_outcome(outcome)
        # Auto-save learning data after each outcome
        self._session_learner.save()

        return {
            **result,
            'total_time': time.time() - start_time,
            'session_stats': self._session_learner.get_session_stats()
        }

    async def _execute_with_decomposition(
        self,
        goal: str,
        context: Dict[str, Any],
        on_progress: callable = None
    ) -> Dict[str, Any]:
        """Execute a complex goal with task decomposition."""
        # Decompose the goal
        graph = await self._task_decomposer.decompose(goal, context, use_ai=True)

        # Create executor
        async def execute_subtask(prompt: str, **kwargs) -> str:
            result = await self._execute_with_correction(prompt, context, True)
            return result.get('response', '')

        executor = GraphExecutor(
            execute_fn=execute_subtask,
            max_parallel=3,
            on_progress=on_progress
        )

        # Execute all subtasks
        completed_graph = await executor.execute(graph, context)

        return {
            'success': completed_graph.is_complete(),
            'response': completed_graph.final_result,
            'subtasks': {
                tid: {
                    'title': t.title,
                    'status': t.status.value,
                    'result': t.result[:500] if t.result else None
                }
                for tid, t in completed_graph.subtasks.items()
            },
            'progress': completed_graph.get_progress(),
            'corrections': 0,
            'agent': 'team'
        }

    async def _execute_with_correction(
        self,
        prompt: str,
        context: Dict[str, Any],
        enable_correction: bool = True
    ) -> Dict[str, Any]:
        """Execute a task with self-correction if needed."""
        # Get best agent from session learner
        task_type = self._task_router.classify(prompt).primary_type.value
        best_agent_id = self._session_learner.get_best_agent(task_type)

        if not best_agent_id:
            best_agent_id = self._orchestrator.available_agents[0] if self._orchestrator.available_agents else None

        if not best_agent_id:
            return {
                'success': False,
                'response': 'No agents available',
                'agent': None,
                'confidence': 0.0,
                'corrections': 0
            }

        agent = self._orchestrator.get_agent(best_agent_id)
        if not agent:
            # Fallback to collaborate
            result = await self._orchestrator.collaborate(prompt)
            return {
                'success': True,
                'response': result.final_answer,
                'agent': 'team',
                'confidence': 0.7,
                'corrections': 0
            }

        # Execute
        response = await agent.generate_response(prompt)
        original_response = response.content

        if not enable_correction or not self._orchestrator.enable_self_correction:
            return {
                'success': True,
                'response': original_response,
                'agent': best_agent_id,
                'confidence': 0.7,
                'corrections': 0
            }

        # Self-correction
        async def retry_execute(new_prompt: str, **kwargs) -> str:
            agent_override = kwargs.get('agent_override')
            mode = kwargs.get('mode')

            if mode == 'consensus':
                result = await self._orchestrator.collaborate(new_prompt, mode='consensus')
                return result.final_answer
            elif agent_override:
                alt_agent = self._orchestrator.get_agent(agent_override)
                if alt_agent:
                    resp = await alt_agent.generate_response(new_prompt)
                    return resp.content
            return (await agent.generate_response(new_prompt)).content

        correction_result = await self._self_corrector.correct(
            original_prompt=prompt,
            original_response=original_response,
            execute_fn=retry_execute,
            task_type=task_type,
            available_agents=self._orchestrator.available_agents,
            context={'current_agent': best_agent_id, 'task_type': task_type}
        )

        return {
            'success': correction_result.success,
            'response': correction_result.corrected_response or original_response,
            'agent': best_agent_id,
            'confidence': correction_result.confidence,
            'corrections': correction_result.attempts,
            'strategy_used': correction_result.strategy_used.value if correction_result.strategy_used else None
        }

    async def build(
        self,
        description: str,
        context: Dict[str, Any] = None,
        on_progress: callable = None
    ) -> Dict[str, Any]:
        """
        High-level autonomous build command.

        Example:
            result = await team.build("Create a FastAPI REST API for user management")

        Args:
            description: What to build
            context: Additional context (existing code, requirements, etc.)
            on_progress: Progress callback

        Returns:
            Dict with complete build output
        """
        return await self.auto_collaborate(
            goal=description,
            context=context,
            enable_correction=True,
            enable_decomposition=True,
            on_progress=on_progress
        )

    def get_autonomous_stats(self) -> Dict[str, Any]:
        """Get statistics on autonomous features."""
        return {
            'self_correction': self._self_corrector.get_statistics(),
            'session_learning': self._session_learner.get_session_stats(),
            'team_adaptation': self._team_adapter.get_adaptation_stats(),
            'recommendations': self._session_learner.get_recommendations()
        }

    def get_best_agent_for(self, task_type: str) -> Optional[str]:
        """Get the best agent for a specific task type based on session learning."""
        return self._session_learner.get_best_agent(task_type)
