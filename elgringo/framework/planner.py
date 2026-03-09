"""
Task Planner
============

Multi-step task planning and execution framework.

Features:
- Automatic task decomposition
- Dependency tracking between steps
- Parallel execution when possible
- Progress tracking and recovery
- Plan validation and optimization
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PlanStatus(Enum):
    """Status of a plan or step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    id: str
    description: str
    action: str  # Tool or function to call
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Step IDs this depends on
    status: PlanStatus = PlanStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_duration: Optional[float] = None  # Seconds

    def can_execute(self, completed_steps: Set[str]) -> bool:
        """Check if all dependencies are satisfied."""
        return all(dep in completed_steps for dep in self.dependencies)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "action": self.action,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class ExecutionPlan:
    """A complete execution plan with multiple steps."""
    id: str
    goal: str
    steps: List[PlanStep]
    status: PlanStatus = PlanStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_ready_steps(self) -> List[PlanStep]:
        """Get steps that are ready to execute."""
        completed = {s.id for s in self.steps if s.status == PlanStatus.COMPLETED}
        return [
            s for s in self.steps
            if s.status == PlanStatus.PENDING and s.can_execute(completed)
        ]

    def get_progress(self) -> Dict[str, Any]:
        """Get execution progress."""
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.status == PlanStatus.COMPLETED)
        failed = sum(1 for s in self.steps if s.status == PlanStatus.FAILED)
        in_progress = sum(1 for s in self.steps if s.status == PlanStatus.IN_PROGRESS)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "percent_complete": (completed / total * 100) if total > 0 else 0,
        }

    def to_markdown(self) -> str:
        """Convert plan to markdown."""
        lines = [f"# Execution Plan: {self.goal}\n"]
        lines.append(f"**Status:** {self.status.value}\n")

        progress = self.get_progress()
        lines.append(f"**Progress:** {progress['completed']}/{progress['total']} steps ({progress['percent_complete']:.0f}%)\n")

        lines.append("\n## Steps\n")
        for i, step in enumerate(self.steps, 1):
            status_emoji = {
                PlanStatus.PENDING: "⏳",
                PlanStatus.IN_PROGRESS: "🔄",
                PlanStatus.COMPLETED: "✅",
                PlanStatus.FAILED: "❌",
                PlanStatus.SKIPPED: "⏭️",
                PlanStatus.BLOCKED: "🚫",
            }.get(step.status, "❓")

            lines.append(f"{i}. {status_emoji} **{step.description}**")
            lines.append(f"   - Action: `{step.action}`")
            if step.dependencies:
                lines.append(f"   - Depends on: {', '.join(step.dependencies)}")
            if step.error:
                lines.append(f"   - Error: {step.error}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.get_progress(),
        }


class TaskPlanner:
    """
    Plans and executes multi-step tasks.

    The planner can:
    1. Decompose a goal into steps using an LLM
    2. Track dependencies between steps
    3. Execute steps in parallel when possible
    4. Handle failures and retries
    5. Provide progress updates

    Example:
        planner = TaskPlanner(llm_call=my_llm, executor=my_executor)
        plan = await planner.create_plan("Build a REST API for users")
        result = await planner.execute_plan(plan)
    """

    PLANNING_PROMPT = """You are a task planner. Break down the following goal into a series of concrete steps.

Goal: {goal}

Context: {context}

Available actions/tools:
{tools}

Output a JSON array of steps, where each step has:
- id: Unique identifier (step_1, step_2, etc.)
- description: What this step does
- action: The tool/action to use
- parameters: Parameters for the action (as object)
- dependencies: Array of step IDs this depends on

Example output:
```json
[
  {{"id": "step_1", "description": "Create project directory", "action": "run_shell", "parameters": {{"command": "mkdir -p my_api"}}, "dependencies": []}},
  {{"id": "step_2", "description": "Initialize Python project", "action": "run_shell", "parameters": {{"command": "cd my_api && python -m venv venv"}}, "dependencies": ["step_1"]}}
]
```

Now create a plan for the goal. Output ONLY the JSON array:"""

    def __init__(
        self,
        llm_call: Callable,
        executor: Callable = None,
        max_parallel: int = 3,
        retry_failed: bool = True,
        max_retries: int = 2,
    ):
        """
        Initialize the planner.

        Args:
            llm_call: Async function for LLM calls (prompt) -> response
            executor: Async function to execute steps (step) -> result
            max_parallel: Maximum parallel step executions
            retry_failed: Whether to retry failed steps
            max_retries: Maximum retries per step
        """
        self.llm_call = llm_call
        self.executor = executor or self._default_executor
        self.max_parallel = max_parallel
        self.retry_failed = retry_failed
        self.max_retries = max_retries

        # Track active plans
        self._active_plans: Dict[str, ExecutionPlan] = {}

    async def _default_executor(self, step: PlanStep) -> Any:
        """Default step executor using tool registry."""
        from .tools import get_tool_registry

        registry = get_tool_registry()
        result = await registry.execute(step.action, step.parameters)

        if not result.success:
            raise Exception(result.error)

        return result.output

    async def create_plan(
        self,
        goal: str,
        context: str = "",
        available_tools: List[str] = None,
    ) -> ExecutionPlan:
        """
        Create an execution plan for a goal.

        Args:
            goal: The goal to achieve
            context: Additional context
            available_tools: List of available tool names

        Returns:
            ExecutionPlan with steps
        """
        import uuid
        from .tools import get_tool_registry

        # Get tool descriptions
        registry = get_tool_registry()
        if available_tools:
            tool_names = available_tools
        else:
            tool_names = registry.list_tools()

        tool_descriptions = []
        for name in tool_names:
            tool = registry.get(name)
            if tool:
                tool_descriptions.append(f"- {name}: {tool.description}")

        # Build prompt
        prompt = self.PLANNING_PROMPT.format(
            goal=goal,
            context=context or "No additional context",
            tools="\n".join(tool_descriptions) or "No tools available",
        )

        # Get LLM response
        response = await self.llm_call(prompt)

        # Parse steps from response
        steps = self._parse_plan_response(response)

        # Create plan
        plan = ExecutionPlan(
            id=str(uuid.uuid4())[:8],
            goal=goal,
            steps=steps,
            metadata={"context": context},
        )

        self._active_plans[plan.id] = plan
        return plan

    def _parse_plan_response(self, response: str) -> List[PlanStep]:
        """Parse LLM response into plan steps."""
        import re

        # Try to extract JSON array
        json_match = re.search(r'\[[\s\S]*\]', response)
        if not json_match:
            logger.warning("Could not find JSON array in response")
            return []

        try:
            steps_data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            return []

        steps = []
        for data in steps_data:
            step = PlanStep(
                id=data.get("id", f"step_{len(steps)+1}"),
                description=data.get("description", ""),
                action=data.get("action", ""),
                parameters=data.get("parameters", {}),
                dependencies=data.get("dependencies", []),
            )
            steps.append(step)

        return steps

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        on_step_start: Callable[[PlanStep], None] = None,
        on_step_complete: Callable[[PlanStep], None] = None,
        on_step_failed: Callable[[PlanStep, str], None] = None,
    ) -> ExecutionPlan:
        """
        Execute a plan.

        Args:
            plan: The plan to execute
            on_step_start: Callback when step starts
            on_step_complete: Callback when step completes
            on_step_failed: Callback when step fails

        Returns:
            Updated plan with results
        """
        plan.status = PlanStatus.IN_PROGRESS
        plan.started_at = datetime.now(timezone.utc).isoformat()

        completed_ids: Set[str] = set()
        retry_counts: Dict[str, int] = {}

        while True:
            # Get steps ready to execute
            ready_steps = plan.get_ready_steps()

            if not ready_steps:
                # Check if all done or blocked
                pending = [s for s in plan.steps if s.status == PlanStatus.PENDING]
                if not pending:
                    break
                else:
                    # Steps are blocked
                    for step in pending:
                        step.status = PlanStatus.BLOCKED
                    break

            # Execute ready steps (up to max_parallel)
            batch = ready_steps[:self.max_parallel]
            tasks = []

            for step in batch:
                step.status = PlanStatus.IN_PROGRESS
                step.started_at = datetime.now(timezone.utc).isoformat()

                if on_step_start:
                    on_step_start(step)

                tasks.append(self._execute_step(step, retry_counts))

            # Wait for batch
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for step, result in zip(batch, results):
                step.completed_at = datetime.now(timezone.utc).isoformat()

                if isinstance(result, Exception):
                    step.status = PlanStatus.FAILED
                    step.error = str(result)

                    if on_step_failed:
                        on_step_failed(step, str(result))

                    # Check for retry
                    if self.retry_failed:
                        count = retry_counts.get(step.id, 0)
                        if count < self.max_retries:
                            retry_counts[step.id] = count + 1
                            step.status = PlanStatus.PENDING
                            step.error = f"{step.error} (retry {count + 1})"
                else:
                    step.status = PlanStatus.COMPLETED
                    step.result = result
                    completed_ids.add(step.id)

                    if on_step_complete:
                        on_step_complete(step)

        # Update plan status
        failed = any(s.status == PlanStatus.FAILED for s in plan.steps)
        blocked = any(s.status == PlanStatus.BLOCKED for s in plan.steps)

        if failed or blocked:
            plan.status = PlanStatus.FAILED
        else:
            plan.status = PlanStatus.COMPLETED

        plan.completed_at = datetime.now(timezone.utc).isoformat()

        return plan

    async def _execute_step(self, step: PlanStep, retry_counts: Dict[str, int]) -> Any:
        """Execute a single step."""
        try:
            return await self.executor(step)
        except Exception as e:
            logger.error(f"Step {step.id} failed: {e}")
            raise

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get a plan by ID."""
        return self._active_plans.get(plan_id)

    def list_plans(self) -> List[ExecutionPlan]:
        """List all active plans."""
        return list(self._active_plans.values())

    async def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Optimize a plan by identifying parallelizable steps.

        Analyzes dependencies to maximize parallel execution.
        """
        # Build dependency graph
        step_map = {s.id: s for s in plan.steps}

        # Find steps that can run in parallel (same level in dependency tree)
        levels: Dict[str, int] = {}

        def get_level(step_id: str) -> int:
            if step_id in levels:
                return levels[step_id]

            step = step_map.get(step_id)
            if not step or not step.dependencies:
                levels[step_id] = 0
                return 0

            max_dep_level = max(get_level(dep) for dep in step.dependencies)
            levels[step_id] = max_dep_level + 1
            return levels[step_id]

        for step in plan.steps:
            get_level(step.id)

        # Sort steps by level
        plan.steps.sort(key=lambda s: levels.get(s.id, 0))

        # Add metadata about parallelization
        plan.metadata["optimization"] = {
            "levels": levels,
            "max_parallel_at_level": {},
        }

        # Count steps at each level
        level_counts: Dict[int, int] = {}
        for step_id, level in levels.items():
            level_counts[level] = level_counts.get(level, 0) + 1

        plan.metadata["optimization"]["max_parallel_at_level"] = level_counts

        return plan
