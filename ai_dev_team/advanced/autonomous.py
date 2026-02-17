"""
Autonomous Agent - AI That Works While You Sleep

SECRET WEAPON #6: Set a goal and let the AI team work autonomously!
This is true agentic AI - it can:

- Break down complex goals into tasks
- Execute tasks using tools (filesystem, shell, browser)
- Handle errors and retry with different approaches
- Learn from failures and adapt
- Work for hours without human intervention

This is the future of software development!
"""

import asyncio
import json
import logging
import os
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of an autonomous task"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ActionType(Enum):
    """Types of actions the agent can take"""
    THINK = "think"           # Plan next steps
    CODE = "code"             # Write/modify code
    EXECUTE = "execute"       # Run commands
    READ = "read"             # Read files
    WRITE = "write"           # Write files
    SEARCH = "search"         # Search codebase
    BROWSE = "browse"         # Fetch web content
    ASK = "ask"               # Ask for clarification
    COMPLETE = "complete"     # Mark task complete


@dataclass
class Action:
    """An action taken by the autonomous agent"""
    action_type: ActionType
    description: str
    input_data: Dict[str, Any]
    output: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0


@dataclass
class Task:
    """A task in the autonomous execution plan"""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    actions: List[Action] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    result: Optional[str] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3


@dataclass
class AutonomousSession:
    """A complete autonomous work session"""
    goal: str
    tasks: List[Task] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_actions: int = 0
    total_cost_usd: float = 0.0
    logs: List[str] = field(default_factory=list)


class AutonomousAgent:
    """
    Autonomous AI Agent

    Give it a goal and let it work! The agent will:
    1. Break down the goal into tasks
    2. Execute tasks using available tools
    3. Handle errors and adapt
    4. Complete the entire goal autonomously

    Usage:
        agent = AutonomousAgent()

        # Start autonomous work
        session = await agent.work(
            goal="Implement user authentication with JWT",
            project_dir="/path/to/project"
        )

        # Monitor progress
        while session.status == TaskStatus.RUNNING:
            print(agent.get_status())
            await asyncio.sleep(10)

        # Check results
        print(session.result)
    """

    MAX_ITERATIONS = 50  # Safety limit
    MAX_TASK_TIME = 300  # 5 minutes per task max

    def __init__(
        self,
        project_dir: Optional[str] = None,
        allowed_actions: List[ActionType] = None,
        on_action: Optional[Callable[[Action], None]] = None,
        require_confirmation: bool = False
    ):
        """
        Initialize autonomous agent.

        Args:
            project_dir: Working directory for file operations
            allowed_actions: Limit which actions are allowed
            on_action: Callback for each action (for UI updates)
            require_confirmation: If True, pause before destructive actions
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.allowed_actions = allowed_actions or list(ActionType)
        self.on_action = on_action
        self.require_confirmation = require_confirmation
        self._client = None
        self._current_session: Optional[AutonomousSession] = None
        self._should_stop = False

    async def _get_client(self):
        """Get Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._client = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                pass
        return self._client

    def _log(self, message: str):
        """Add to session log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        logger.info(log_entry)
        if self._current_session:
            self._current_session.logs.append(log_entry)

    async def work(
        self,
        goal: str,
        context: str = "",
        max_iterations: int = None
    ) -> AutonomousSession:
        """
        Start autonomous work towards a goal.

        Args:
            goal: What to accomplish
            context: Additional context (requirements, constraints)
            max_iterations: Override max iterations

        Returns:
            AutonomousSession with results
        """
        max_iterations = max_iterations or self.MAX_ITERATIONS
        self._should_stop = False

        # Create session
        self._current_session = AutonomousSession(goal=goal)
        self._current_session.status = TaskStatus.RUNNING
        self._log(f"Starting autonomous work: {goal}")

        try:
            # Step 1: Plan - break goal into tasks
            tasks = await self._plan(goal, context)
            self._current_session.tasks = tasks
            self._log(f"Created {len(tasks)} tasks")

            # Step 2: Execute tasks
            iteration = 0
            while iteration < max_iterations and not self._should_stop:
                iteration += 1

                # Find next executable task
                task = self._get_next_task()
                if not task:
                    # Check if all done or blocked
                    if self._all_tasks_complete():
                        self._log("All tasks completed!")
                        break
                    else:
                        self._log("All remaining tasks are blocked or failed")
                        break

                # Execute the task
                self._log(f"Executing task: {task.description}")
                await self._execute_task(task)

                # Brief pause between tasks
                await asyncio.sleep(0.5)

            # Finalize session
            self._current_session.end_time = datetime.now()
            if self._all_tasks_complete():
                self._current_session.status = TaskStatus.COMPLETED
                self._log("Session completed successfully!")
            else:
                self._current_session.status = TaskStatus.FAILED
                self._log("Session ended with incomplete tasks")

        except Exception as e:
            self._log(f"Session error: {e}")
            self._current_session.status = TaskStatus.FAILED
            self._current_session.end_time = datetime.now()
            traceback.print_exc()

        return self._current_session

    async def _plan(self, goal: str, context: str) -> List[Task]:
        """Create a plan of tasks for the goal"""
        client = await self._get_client()
        if not client:
            return [Task(id="1", description=goal)]

        # Get codebase context
        codebase_context = await self._get_codebase_context()

        prompt = f"""You are an autonomous AI agent planning how to accomplish a goal.

GOAL: {goal}

ADDITIONAL CONTEXT:
{context}

PROJECT STRUCTURE:
{codebase_context}

Create a detailed plan of TASKS to accomplish this goal.
Each task should be:
- Specific and actionable
- Small enough to complete in one step
- Have clear success criteria

Format your response as JSON:
{{
    "tasks": [
        {{
            "id": "1",
            "description": "Specific task description",
            "dependencies": []  // IDs of tasks that must complete first
        }},
        ...
    ]
}}

Create 3-10 tasks depending on complexity."""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system="You are a meticulous planning agent. Create clear, actionable task plans.",
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse tasks from response
        try:
            response_text = response.content[0].text
            # Extract JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0]
            else:
                json_str = response_text

            data = json.loads(json_str)
            tasks = [
                Task(
                    id=t["id"],
                    description=t["description"],
                    dependencies=t.get("dependencies", [])
                )
                for t in data["tasks"]
            ]
            return tasks

        except Exception as e:
            logger.error(f"Failed to parse plan: {e}")
            return [Task(id="1", description=goal)]

    async def _get_codebase_context(self) -> str:
        """Get context about the current codebase"""
        context_parts = []

        # List top-level files and directories
        try:
            items = list(self.project_dir.iterdir())[:50]  # Limit for context size
            files = [f.name for f in items if f.is_file()]
            dirs = [d.name for d in items if d.is_dir() and not d.name.startswith('.')]

            context_parts.append(f"Root files: {', '.join(files[:20])}")
            context_parts.append(f"Directories: {', '.join(dirs[:15])}")

            # Check for common config files
            for config in ['package.json', 'requirements.txt', 'pyproject.toml', 'Cargo.toml']:
                config_path = self.project_dir / config
                if config_path.exists():
                    content = config_path.read_text()[:500]
                    context_parts.append(f"\n{config}:\n{content}")

        except Exception as e:
            context_parts.append(f"Could not read project: {e}")

        return "\n".join(context_parts)

    def _get_next_task(self) -> Optional[Task]:
        """Get the next task to execute"""
        for task in self._current_session.tasks:
            if task.status != TaskStatus.PENDING:
                continue

            # Check dependencies
            deps_met = all(
                self._get_task_by_id(dep_id).status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
                if self._get_task_by_id(dep_id)
            )

            if deps_met:
                return task

        return None

    def _get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Find task by ID"""
        for task in self._current_session.tasks:
            if task.id == task_id:
                return task
        return None

    def _all_tasks_complete(self) -> bool:
        """Check if all tasks are complete"""
        return all(
            t.status == TaskStatus.COMPLETED
            for t in self._current_session.tasks
        )

    async def _execute_task(self, task: Task):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        start_time = time.time()

        try:
            client = await self._get_client()
            if not client:
                raise RuntimeError("No AI client available")

            # Get task context
            previous_results = self._get_previous_results()

            prompt = f"""You are executing a task as part of a larger goal.

OVERALL GOAL: {self._current_session.goal}

CURRENT TASK: {task.description}

PREVIOUS TASK RESULTS:
{previous_results}

PROJECT DIRECTORY: {self.project_dir}

Execute this task by responding with the ACTION you want to take.
Format your response as JSON:

{{
    "action": "code|execute|read|write|search|complete",
    "description": "What you're doing",
    "data": {{
        // For "code": {{"code": "the code to write", "file": "path/to/file"}}
        // For "execute": {{"command": "shell command"}}
        // For "read": {{"file": "path/to/file"}}
        // For "write": {{"file": "path/to/file", "content": "file content"}}
        // For "search": {{"query": "search term"}}
        // For "complete": {{"result": "summary of what was accomplished"}}
    }}
}}

Take ONE action at a time. Use "complete" when the task is done."""

            # Execute actions until task complete or max iterations
            for i in range(10):  # Max 10 actions per task
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    system="You are an autonomous coding agent. Execute tasks precisely.",
                    messages=[{"role": "user", "content": prompt}]
                )

                # Parse and execute action
                action = await self._parse_and_execute_action(response.content[0].text, task)
                task.actions.append(action)
                self._current_session.total_actions += 1

                if self.on_action:
                    self.on_action(action)

                if action.action_type == ActionType.COMPLETE:
                    task.status = TaskStatus.COMPLETED
                    task.result = action.output
                    self._log(f"Task completed: {task.description}")
                    return

                if not action.success:
                    # Add error context for retry
                    prompt += f"\n\nPrevious action failed: {action.error}\nTry a different approach."

                # Safety timeout
                if time.time() - start_time > self.MAX_TASK_TIME:
                    raise TimeoutError("Task timeout")

            # Max iterations reached
            task.status = TaskStatus.FAILED
            task.error = "Max actions reached without completion"

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._log(f"Task failed: {e}")

            # Retry if possible
            if task.retries < task.max_retries:
                task.retries += 1
                task.status = TaskStatus.PENDING
                self._log(f"Will retry task (attempt {task.retries + 1})")

    async def _parse_and_execute_action(self, response: str, task: Task) -> Action:
        """Parse AI response and execute the action"""
        start_time = time.time()

        try:
            # Extract JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response

            data = json.loads(json_str)
            action_type = ActionType(data["action"])
            action_data = data.get("data", {})

            action = Action(
                action_type=action_type,
                description=data.get("description", ""),
                input_data=action_data
            )

            # Execute based on type
            if action_type == ActionType.COMPLETE:
                action.output = action_data.get("result", "Task completed")

            elif action_type == ActionType.READ:
                file_path = self.project_dir / action_data["file"]
                if file_path.exists():
                    action.output = file_path.read_text()[:10000]  # Limit size
                else:
                    action.success = False
                    action.error = f"File not found: {action_data['file']}"

            elif action_type == ActionType.WRITE:
                file_path = self.project_dir / action_data["file"]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(action_data["content"])
                action.output = f"Written to {action_data['file']}"

            elif action_type == ActionType.EXECUTE:
                if self.require_confirmation:
                    self._log(f"Command requires confirmation: {action_data['command']}")
                    action.output = "Command execution requires confirmation"
                else:
                    result = await asyncio.create_subprocess_shell(
                        action_data["command"],
                        cwd=self.project_dir,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=60)
                    action.output = stdout.decode()[:5000]
                    if stderr:
                        action.output += f"\nSTDERR: {stderr.decode()[:1000]}"
                    if result.returncode != 0:
                        action.success = False
                        action.error = f"Command failed with code {result.returncode}"

            elif action_type == ActionType.CODE:
                # Write code to file
                file_path = self.project_dir / action_data.get("file", "output.py")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(action_data["code"])
                action.output = f"Code written to {file_path}"

            elif action_type == ActionType.SEARCH:
                # Simple grep-like search
                query = action_data["query"]
                results = []
                for path in self.project_dir.rglob("*"):
                    if path.is_file() and path.suffix in ['.py', '.js', '.ts', '.jsx', '.tsx']:
                        try:
                            content = path.read_text()
                            if query.lower() in content.lower():
                                results.append(str(path.relative_to(self.project_dir)))
                        except:
                            pass
                action.output = f"Found in: {', '.join(results[:20])}"

            action.duration = time.time() - start_time
            return action

        except Exception as e:
            return Action(
                action_type=ActionType.THINK,
                description="Failed to parse action",
                input_data={"raw_response": response[:500]},
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )

    def _get_previous_results(self) -> str:
        """Get results from previously completed tasks"""
        results = []
        for task in self._current_session.tasks:
            if task.status == TaskStatus.COMPLETED:
                results.append(f"- {task.description}: {task.result or 'Done'}")
        return "\n".join(results) or "No previous tasks completed yet."

    def stop(self):
        """Stop autonomous execution"""
        self._should_stop = True
        self._log("Stop requested")

    def get_status(self) -> Dict[str, Any]:
        """Get current session status"""
        if not self._current_session:
            return {"status": "no_session"}

        completed = sum(1 for t in self._current_session.tasks if t.status == TaskStatus.COMPLETED)
        total = len(self._current_session.tasks)

        return {
            "goal": self._current_session.goal,
            "status": self._current_session.status.value,
            "progress": f"{completed}/{total} tasks",
            "total_actions": self._current_session.total_actions,
            "recent_logs": self._current_session.logs[-10:]
        }


# Convenience function
async def autonomous_work(goal: str, project_dir: str = ".") -> AutonomousSession:
    """Quick autonomous work on a goal"""
    agent = AutonomousAgent(project_dir=project_dir)
    return await agent.work(goal)
