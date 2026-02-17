"""
Smart Task Decomposition System

Automatically breaks down complex goals into subtasks, identifies dependencies,
and orchestrates parallel execution.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Set
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a subtask."""
    PENDING = "pending"
    READY = "ready"        # All dependencies met
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Priority levels for tasks."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class SubTask:
    """A subtask in the execution graph."""
    id: str
    title: str
    description: str
    task_type: str  # coding, testing, documentation, etc.
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)  # IDs of tasks this depends on
    estimated_complexity: float = 0.5  # 0-1 scale
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are met."""
        return all(dep in completed_tasks for dep in self.dependencies)


@dataclass
class ExecutionGraph:
    """Graph of subtasks with dependencies."""
    goal: str
    subtasks: Dict[str, SubTask] = field(default_factory=dict)
    execution_order: List[List[str]] = field(default_factory=list)  # Batches of parallel tasks
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    final_result: Optional[str] = None

    def add_task(self, task: SubTask):
        """Add a subtask to the graph."""
        self.subtasks[task.id] = task

    def get_ready_tasks(self) -> List[SubTask]:
        """Get all tasks that are ready to execute."""
        completed = {tid for tid, t in self.subtasks.items()
                    if t.status == TaskStatus.COMPLETED}
        return [
            task for task in self.subtasks.values()
            if task.status == TaskStatus.PENDING and task.is_ready(completed)
        ]

    def mark_completed(self, task_id: str, result: str):
        """Mark a task as completed."""
        if task_id in self.subtasks:
            task = self.subtasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()

    def mark_failed(self, task_id: str, error: str):
        """Mark a task as failed."""
        if task_id in self.subtasks:
            task = self.subtasks[task_id]
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.now()

    def is_complete(self) -> bool:
        """Check if all tasks are done."""
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED)
            for t in self.subtasks.values()
        )

    def get_progress(self) -> Dict[str, Any]:
        """Get execution progress."""
        total = len(self.subtasks)
        completed = sum(1 for t in self.subtasks.values()
                       if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.subtasks.values()
                    if t.status == TaskStatus.FAILED)
        in_progress = sum(1 for t in self.subtasks.values()
                         if t.status == TaskStatus.IN_PROGRESS)

        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'in_progress': in_progress,
            'pending': total - completed - failed - in_progress,
            'percent_complete': (completed / total * 100) if total > 0 else 0
        }


class TaskDecomposer:
    """
    Intelligent task decomposition that breaks complex goals into
    manageable subtasks with dependency tracking.
    """

    def __init__(self, ai_analyzer: Callable = None):
        """
        Initialize the decomposer.

        Args:
            ai_analyzer: Async function to analyze tasks (e.g., orchestrator.collaborate)
        """
        self.ai_analyzer = ai_analyzer
        self.decomposition_patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, List[Dict]]:
        """Load common decomposition patterns."""
        return {
            'web_app': [
                {'title': 'Setup project structure', 'type': 'setup', 'priority': TaskPriority.CRITICAL},
                {'title': 'Create data models', 'type': 'coding', 'priority': TaskPriority.HIGH},
                {'title': 'Implement backend API', 'type': 'coding', 'priority': TaskPriority.HIGH},
                {'title': 'Create frontend components', 'type': 'coding', 'priority': TaskPriority.HIGH},
                {'title': 'Add authentication', 'type': 'security', 'priority': TaskPriority.HIGH},
                {'title': 'Write tests', 'type': 'testing', 'priority': TaskPriority.MEDIUM},
                {'title': 'Add documentation', 'type': 'documentation', 'priority': TaskPriority.LOW},
            ],
            'api': [
                {'title': 'Define API schema', 'type': 'design', 'priority': TaskPriority.CRITICAL},
                {'title': 'Create data models', 'type': 'coding', 'priority': TaskPriority.HIGH},
                {'title': 'Implement endpoints', 'type': 'coding', 'priority': TaskPriority.HIGH},
                {'title': 'Add validation', 'type': 'coding', 'priority': TaskPriority.HIGH},
                {'title': 'Implement error handling', 'type': 'coding', 'priority': TaskPriority.MEDIUM},
                {'title': 'Write API tests', 'type': 'testing', 'priority': TaskPriority.MEDIUM},
                {'title': 'Generate API docs', 'type': 'documentation', 'priority': TaskPriority.LOW},
            ],
            'feature': [
                {'title': 'Analyze requirements', 'type': 'analysis', 'priority': TaskPriority.CRITICAL},
                {'title': 'Design solution', 'type': 'design', 'priority': TaskPriority.HIGH},
                {'title': 'Implement core logic', 'type': 'coding', 'priority': TaskPriority.HIGH},
                {'title': 'Add edge case handling', 'type': 'coding', 'priority': TaskPriority.MEDIUM},
                {'title': 'Write unit tests', 'type': 'testing', 'priority': TaskPriority.MEDIUM},
                {'title': 'Integration testing', 'type': 'testing', 'priority': TaskPriority.MEDIUM},
            ],
            'bugfix': [
                {'title': 'Reproduce the bug', 'type': 'debugging', 'priority': TaskPriority.CRITICAL},
                {'title': 'Identify root cause', 'type': 'analysis', 'priority': TaskPriority.CRITICAL},
                {'title': 'Implement fix', 'type': 'coding', 'priority': TaskPriority.HIGH},
                {'title': 'Write regression test', 'type': 'testing', 'priority': TaskPriority.HIGH},
                {'title': 'Verify fix', 'type': 'testing', 'priority': TaskPriority.MEDIUM},
            ],
            'refactor': [
                {'title': 'Analyze current code', 'type': 'analysis', 'priority': TaskPriority.HIGH},
                {'title': 'Identify improvement areas', 'type': 'design', 'priority': TaskPriority.HIGH},
                {'title': 'Write tests for existing behavior', 'type': 'testing', 'priority': TaskPriority.HIGH},
                {'title': 'Refactor code', 'type': 'coding', 'priority': TaskPriority.HIGH},
                {'title': 'Verify tests pass', 'type': 'testing', 'priority': TaskPriority.CRITICAL},
            ],
        }

    async def decompose(
        self,
        goal: str,
        context: Dict[str, Any] = None,
        max_subtasks: int = 10,
        use_ai: bool = True
    ) -> ExecutionGraph:
        """
        Decompose a complex goal into subtasks.

        Args:
            goal: The high-level goal to decompose
            context: Additional context (existing code, project type, etc.)
            max_subtasks: Maximum number of subtasks to create
            use_ai: Whether to use AI for intelligent decomposition

        Returns:
            ExecutionGraph with subtasks and dependencies
        """
        context = context or {}
        graph = ExecutionGraph(goal=goal)

        # Detect goal type
        goal_type = self._detect_goal_type(goal)
        logger.info(f"Detected goal type: {goal_type}")

        if use_ai and self.ai_analyzer:
            # Use AI for intelligent decomposition
            subtasks = await self._ai_decompose(goal, context, max_subtasks)
        else:
            # Use pattern-based decomposition
            subtasks = self._pattern_decompose(goal, goal_type, context)

        # Add subtasks to graph
        for i, task_data in enumerate(subtasks[:max_subtasks]):
            task = SubTask(
                id=f"task_{i+1}",
                title=task_data.get('title', f'Step {i+1}'),
                description=task_data.get('description', ''),
                task_type=task_data.get('type', 'coding'),
                priority=task_data.get('priority', TaskPriority.MEDIUM),
                dependencies=task_data.get('dependencies', []),
                estimated_complexity=task_data.get('complexity', 0.5),
                metadata=task_data.get('metadata', {})
            )
            graph.add_task(task)

        # Infer dependencies if not specified
        self._infer_dependencies(graph)

        # Calculate execution order (topological sort with parallelization)
        graph.execution_order = self._calculate_execution_order(graph)

        logger.info(f"Decomposed into {len(graph.subtasks)} subtasks")
        return graph

    def _detect_goal_type(self, goal: str) -> str:
        """Detect the type of goal from the description."""
        goal_lower = goal.lower()

        patterns = {
            'web_app': ['web app', 'website', 'web application', 'frontend', 'full stack'],
            'api': ['api', 'endpoint', 'rest', 'graphql', 'backend service'],
            'bugfix': ['fix', 'bug', 'issue', 'error', 'broken', 'not working'],
            'refactor': ['refactor', 'clean up', 'improve', 'optimize', 'restructure'],
            'feature': ['add', 'implement', 'create', 'build', 'develop'],
        }

        for goal_type, keywords in patterns.items():
            if any(kw in goal_lower for kw in keywords):
                return goal_type

        return 'feature'  # Default

    async def _ai_decompose(
        self,
        goal: str,
        context: Dict[str, Any],
        max_subtasks: int
    ) -> List[Dict]:
        """Use AI to intelligently decompose a goal."""
        prompt = f"""Break down this development goal into concrete subtasks:

GOAL: {goal}

CONTEXT:
{json.dumps(context, indent=2) if context else 'No additional context'}

Return a JSON array of subtasks with this structure:
[
    {{
        "title": "Short task title",
        "description": "Detailed description of what to do",
        "type": "coding|testing|documentation|design|analysis|debugging|setup|security",
        "priority": "critical|high|medium|low",
        "dependencies": ["task_1", "task_2"],  // IDs of tasks this depends on
        "complexity": 0.5  // 0-1 scale
    }}
]

Rules:
- Create {max_subtasks} or fewer subtasks
- Order from most critical to least critical
- Identify clear dependencies between tasks
- Each task should be completable by a single agent
- Include testing for code changes

Return ONLY the JSON array, no other text."""

        try:
            response = await self.ai_analyzer(prompt)

            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                subtasks = json.loads(json_match.group())

                # Normalize priority
                for task in subtasks:
                    priority_map = {
                        'critical': TaskPriority.CRITICAL,
                        'high': TaskPriority.HIGH,
                        'medium': TaskPriority.MEDIUM,
                        'low': TaskPriority.LOW
                    }
                    task['priority'] = priority_map.get(
                        task.get('priority', 'medium').lower(),
                        TaskPriority.MEDIUM
                    )

                return subtasks

        except Exception as e:
            logger.warning(f"AI decomposition failed: {e}, falling back to patterns")

        # Fallback to pattern-based
        return self._pattern_decompose(goal, self._detect_goal_type(goal), context)

    def _pattern_decompose(
        self,
        goal: str,
        goal_type: str,
        context: Dict[str, Any]
    ) -> List[Dict]:
        """Use patterns to decompose a goal."""
        pattern = self.decomposition_patterns.get(goal_type, [])

        subtasks = []
        for i, template in enumerate(pattern):
            task = {
                'title': template['title'],
                'description': f"{template['title']} for: {goal}",
                'type': template['type'],
                'priority': template['priority'],
                'dependencies': [f"task_{j+1}" for j in range(i)] if i > 0 else [],
                'complexity': 0.5
            }
            subtasks.append(task)

        return subtasks

    def _infer_dependencies(self, graph: ExecutionGraph):
        """Infer dependencies between tasks based on type and order."""
        task_list = list(graph.subtasks.values())

        # Type-based dependency inference
        dependency_rules = {
            'coding': ['design', 'analysis', 'setup'],  # Coding depends on these
            'testing': ['coding'],  # Testing depends on coding
            'documentation': ['coding', 'testing'],  # Docs depend on implementation
            'security': ['coding'],  # Security review after coding
        }

        for task in task_list:
            if not task.dependencies:  # Only infer if not already set
                for other in task_list:
                    if other.id == task.id:
                        continue

                    # Check if task type depends on other's type
                    depends_on_types = dependency_rules.get(task.task_type, [])
                    if other.task_type in depends_on_types:
                        if other.id not in task.dependencies:
                            task.dependencies.append(other.id)

    def _calculate_execution_order(self, graph: ExecutionGraph) -> List[List[str]]:
        """Calculate execution order with parallelization using topological sort."""
        # Build dependency graph
        in_degree = {tid: len(t.dependencies) for tid, t in graph.subtasks.items()}
        dependents = {tid: [] for tid in graph.subtasks}

        for tid, task in graph.subtasks.items():
            for dep in task.dependencies:
                if dep in dependents:
                    dependents[dep].append(tid)

        # Kahn's algorithm with batching
        order = []
        current_batch = [tid for tid, degree in in_degree.items() if degree == 0]

        while current_batch:
            # Sort batch by priority
            current_batch.sort(
                key=lambda tid: graph.subtasks[tid].priority.value
            )
            order.append(current_batch)

            next_batch = []
            for tid in current_batch:
                for dependent in dependents[tid]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_batch.append(dependent)

            current_batch = next_batch

        return order


class GraphExecutor:
    """Executes an ExecutionGraph with parallel task execution."""

    def __init__(
        self,
        execute_fn: Callable,
        max_parallel: int = 3,
        on_progress: Callable = None
    ):
        """
        Initialize the executor.

        Args:
            execute_fn: Async function to execute a task
            max_parallel: Maximum parallel tasks
            on_progress: Callback for progress updates
        """
        self.execute_fn = execute_fn
        self.max_parallel = max_parallel
        self.on_progress = on_progress

    async def execute(
        self,
        graph: ExecutionGraph,
        context: Dict[str, Any] = None
    ) -> ExecutionGraph:
        """
        Execute all tasks in the graph.

        Args:
            graph: The execution graph
            context: Shared context for all tasks

        Returns:
            The graph with results
        """
        context = context or {}
        results_context = {}  # Accumulate results for dependent tasks

        for batch in graph.execution_order:
            # Execute batch in parallel (up to max_parallel)
            batch_tasks = [graph.subtasks[tid] for tid in batch]

            for i in range(0, len(batch_tasks), self.max_parallel):
                parallel_tasks = batch_tasks[i:i + self.max_parallel]

                await asyncio.gather(*[
                    self._execute_task(task, graph, context, results_context)
                    for task in parallel_tasks
                ])

                # Report progress
                if self.on_progress:
                    self.on_progress(graph.get_progress())

        # Compile final result
        graph.completed_at = datetime.now()
        graph.final_result = self._compile_results(graph)

        return graph

    async def _execute_task(
        self,
        task: SubTask,
        graph: ExecutionGraph,
        context: Dict[str, Any],
        results_context: Dict[str, str]
    ):
        """Execute a single task."""
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()

        # Build prompt with dependency results
        prompt = self._build_task_prompt(task, graph, context, results_context)

        try:
            result = await self.execute_fn(prompt)
            graph.mark_completed(task.id, result)
            results_context[task.id] = result
            logger.info(f"Task {task.id} completed: {task.title}")

        except Exception as e:
            error_msg = str(e)
            graph.mark_failed(task.id, error_msg)
            logger.error(f"Task {task.id} failed: {error_msg}")

    def _build_task_prompt(
        self,
        task: SubTask,
        graph: ExecutionGraph,
        context: Dict[str, Any],
        results_context: Dict[str, str]
    ) -> str:
        """Build a prompt for executing a task."""
        # Get results from dependencies
        dep_results = []
        for dep_id in task.dependencies:
            if dep_id in results_context:
                dep_task = graph.subtasks[dep_id]
                dep_results.append(f"## {dep_task.title}\n{results_context[dep_id]}")

        prompt = f"""# Task: {task.title}

## Goal
{graph.goal}

## Current Task
{task.description}

## Task Type
{task.task_type}

"""
        if dep_results:
            prompt += f"""## Previous Results
{chr(10).join(dep_results)}

"""

        if context:
            prompt += f"""## Additional Context
{json.dumps(context, indent=2)}

"""

        prompt += """Please complete this task thoroughly. If it's a coding task, provide complete, working code."""

        return prompt

    def _compile_results(self, graph: ExecutionGraph) -> str:
        """Compile all task results into a final output."""
        sections = []

        for batch in graph.execution_order:
            for task_id in batch:
                task = graph.subtasks[task_id]
                if task.status == TaskStatus.COMPLETED and task.result:
                    sections.append(f"## {task.title}\n\n{task.result}")
                elif task.status == TaskStatus.FAILED:
                    sections.append(f"## {task.title} (FAILED)\n\nError: {task.error}")

        return "\n\n---\n\n".join(sections)


# Convenience function
async def decompose_and_execute(
    goal: str,
    execute_fn: Callable,
    ai_analyzer: Callable = None,
    context: Dict[str, Any] = None,
    on_progress: Callable = None
) -> ExecutionGraph:
    """
    Convenience function to decompose and execute a goal.

    Args:
        goal: The goal to accomplish
        execute_fn: Function to execute individual tasks
        ai_analyzer: Function for AI-based decomposition
        context: Additional context
        on_progress: Progress callback

    Returns:
        Completed ExecutionGraph
    """
    decomposer = TaskDecomposer(ai_analyzer=ai_analyzer)
    graph = await decomposer.decompose(goal, context)

    executor = GraphExecutor(execute_fn=execute_fn, on_progress=on_progress)
    return await executor.execute(graph, context)
