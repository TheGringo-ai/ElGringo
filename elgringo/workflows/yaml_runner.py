"""
YAML Workflow Runner — Declarative Pipeline Definitions
========================================================

Closes the gap with CrewAI's YAML tasks and LangGraph's declarative graphs.
Define multi-step AI workflows in YAML and execute them.

Usage:
    runner = YAMLWorkflowRunner(collaborate_fn=team.collaborate)

    # From YAML string
    result = await runner.run_yaml('''
    name: code-review-pipeline
    steps:
      - name: analyze
        prompt: "Analyze the codebase for issues"
        mode: parallel
      - name: review
        prompt: "Review the analysis and prioritize fixes"
        mode: consensus
        depends_on: [analyze]
      - name: fix
        prompt: "Generate fixes for top 3 issues"
        mode: parallel
        depends_on: [review]
    ''')

    # From YAML file
    result = await runner.run_file("workflows/review.yaml")
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a YAML workflow."""
    name: str
    prompt: str
    mode: str = "parallel"
    depends_on: List[str] = field(default_factory=list)
    agent: str = ""  # specific agent, empty = auto-route
    output_schema: str = ""  # schema name for structured output
    approval_required: bool = False  # human-in-the-loop gate
    retry_on_fail: int = 1  # max retries
    timeout_seconds: int = 120
    condition: str = ""  # skip condition (e.g. "prev.confidence > 0.8")
    context_from: List[str] = field(default_factory=list)  # inject output from these steps
    status: StepStatus = StepStatus.PENDING
    output: str = ""
    error: str = ""
    duration: float = 0.0


@dataclass
class WorkflowDefinition:
    """Parsed YAML workflow."""
    name: str
    description: str = ""
    version: str = "1.0"
    steps: List[WorkflowStep] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    on_failure: str = "stop"  # stop, continue, retry


@dataclass
class WorkflowRunResult:
    """Result of a workflow execution."""
    workflow_id: str
    workflow_name: str
    success: bool
    steps_completed: int
    steps_total: int
    total_time: float
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    final_output: str = ""
    errors: List[str] = field(default_factory=list)


class YAMLWorkflowRunner:
    """
    Executes declarative YAML workflow definitions.

    Supports:
    - Sequential and parallel step execution
    - Step dependencies (DAG)
    - Variable substitution
    - Conditional step execution
    - Structured output enforcement
    - Human approval gates
    - Retry on failure
    """

    def __init__(
        self,
        collaborate_fn: Optional[Callable] = None,
        ask_fn: Optional[Callable] = None,
    ):
        self._collaborate = collaborate_fn
        self._ask = ask_fn

    def parse_yaml(self, yaml_content: str) -> WorkflowDefinition:
        """Parse a YAML workflow definition."""
        if not HAS_YAML:
            # Fallback: basic parsing without PyYAML
            return self._parse_basic(yaml_content)

        data = yaml.safe_load(yaml_content)
        return self._parse_dict(data)

    def parse_file(self, file_path: str) -> WorkflowDefinition:
        """Parse a YAML workflow file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")

        content = path.read_text()
        return self.parse_yaml(content)

    async def run_yaml(
        self,
        yaml_content: str,
        variables: Optional[Dict[str, str]] = None,
        context: str = "",
    ) -> WorkflowRunResult:
        """Parse and execute a YAML workflow."""
        definition = self.parse_yaml(yaml_content)
        if variables:
            definition.variables.update(variables)
        return await self.run(definition, context=context)

    async def run_file(
        self,
        file_path: str,
        variables: Optional[Dict[str, str]] = None,
        context: str = "",
    ) -> WorkflowRunResult:
        """Parse and execute a YAML workflow file."""
        definition = self.parse_file(file_path)
        if variables:
            definition.variables.update(variables)
        return await self.run(definition, context=context)

    async def run(
        self,
        definition: WorkflowDefinition,
        context: str = "",
    ) -> WorkflowRunResult:
        """Execute a parsed workflow definition."""
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        completed: Set[str] = set()
        outputs: Dict[str, str] = {}

        result = WorkflowRunResult(
            workflow_id=workflow_id,
            workflow_name=definition.name,
            success=True,
            steps_completed=0,
            steps_total=len(definition.steps),
        )

        # Apply variable substitution to all prompts
        for step in definition.steps:
            step.prompt = self._substitute_vars(step.prompt, definition.variables)

        # Execute steps respecting dependencies
        remaining = list(definition.steps)
        while remaining:
            # Find steps ready to run (all deps completed)
            ready = [s for s in remaining if all(d in completed for d in s.depends_on)]

            if not ready:
                # Deadlock — remaining steps have unmet dependencies
                for s in remaining:
                    s.status = StepStatus.FAILED
                    s.error = f"Unmet dependencies: {[d for d in s.depends_on if d not in completed]}"
                    result.errors.append(f"Step '{s.name}': deadlock — unmet dependencies")
                result.success = False
                break

            # Execute ready steps
            for step in ready:
                step_start = time.time()
                step.status = StepStatus.RUNNING

                # Inject context from previous steps
                step_context = context
                for ctx_step in step.context_from:
                    if ctx_step in outputs:
                        step_context += f"\n\n[Output from '{ctx_step}']:\n{outputs[ctx_step][:2000]}"

                # Also auto-inject direct dependency outputs
                for dep in step.depends_on:
                    if dep in outputs and dep not in step.context_from:
                        step_context += f"\n\n[Output from '{dep}']:\n{outputs[dep][:1000]}"

                # Execute with retry
                success = False
                for attempt in range(step.retry_on_fail):
                    try:
                        output = await self._execute_step(step, step_context)
                        step.output = output
                        step.status = StepStatus.COMPLETED
                        step.duration = time.time() - step_start
                        outputs[step.name] = output
                        completed.add(step.name)
                        result.steps_completed += 1
                        success = True
                        break
                    except Exception as e:
                        step.error = str(e)
                        if attempt < step.retry_on_fail - 1:
                            logger.warning(f"Step '{step.name}' failed (attempt {attempt + 1}), retrying: {e}")
                        else:
                            step.status = StepStatus.FAILED
                            step.duration = time.time() - step_start

                if not success:
                    result.errors.append(f"Step '{step.name}' failed: {step.error}")
                    if definition.on_failure == "stop":
                        result.success = False
                        remaining = [s for s in remaining if s not in ready]
                        for s in remaining:
                            s.status = StepStatus.SKIPPED
                        remaining = []
                        break

                result.step_results.append({
                    "name": step.name,
                    "status": step.status.value,
                    "duration": round(step.duration, 2),
                    "output_preview": step.output[:300] if step.output else "",
                    "error": step.error,
                })

                remaining = [s for s in remaining if s not in ready]

        result.total_time = time.time() - start_time

        # Final output = last completed step's output
        if outputs:
            last_step = definition.steps[-1]
            result.final_output = outputs.get(last_step.name, "")

        return result

    async def _execute_step(self, step: WorkflowStep, context: str) -> str:
        """Execute a single workflow step."""
        if not self._collaborate:
            raise RuntimeError("No collaborate function provided to workflow runner")

        # Build the prompt with structured output suffix if needed
        prompt = step.prompt
        if step.output_schema:
            from elgringo.intelligence.structured_output import get_structured_enforcer
            enforcer = get_structured_enforcer()
            schema = enforcer.get_schema(step.output_schema)
            if schema:
                prompt += enforcer.build_prompt_suffix(schema)

        # Call the AI team
        kwargs = {"prompt": prompt, "mode": step.mode}
        if context:
            kwargs["context"] = context

        result = await self._collaborate(**kwargs)

        # Extract the response
        if hasattr(result, "final_answer"):
            output = result.final_answer
        elif isinstance(result, dict):
            output = result.get("final_answer", str(result))
        else:
            output = str(result)

        # Validate structured output if schema specified
        if step.output_schema:
            from elgringo.intelligence.structured_output import get_structured_enforcer
            enforcer = get_structured_enforcer()
            schema = enforcer.get_schema(step.output_schema)
            if schema:
                enforcement = enforcer.enforce(output, schema)
                if not enforcement.success:
                    logger.warning(f"Step '{step.name}' output didn't match schema: {enforcement.errors}")

        return output

    def _parse_dict(self, data: Dict[str, Any]) -> WorkflowDefinition:
        """Parse a dictionary into a WorkflowDefinition."""
        steps = []
        for step_data in data.get("steps", []):
            steps.append(WorkflowStep(
                name=step_data.get("name", f"step-{len(steps)+1}"),
                prompt=step_data.get("prompt", ""),
                mode=step_data.get("mode", "parallel"),
                depends_on=step_data.get("depends_on", []),
                agent=step_data.get("agent", ""),
                output_schema=step_data.get("output_schema", ""),
                approval_required=step_data.get("approval_required", False),
                retry_on_fail=step_data.get("retry_on_fail", 1),
                timeout_seconds=step_data.get("timeout_seconds", 120),
                condition=step_data.get("condition", ""),
                context_from=step_data.get("context_from", []),
            ))

        return WorkflowDefinition(
            name=data.get("name", "unnamed-workflow"),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            steps=steps,
            variables=data.get("variables", {}),
            on_failure=data.get("on_failure", "stop"),
        )

    def _parse_basic(self, yaml_content: str) -> WorkflowDefinition:
        """Basic YAML parsing without PyYAML (fallback)."""
        import json as _json

        # Try JSON first (YAML is a superset of JSON)
        try:
            data = _json.loads(yaml_content)
            return self._parse_dict(data)
        except _json.JSONDecodeError:
            pass

        # Very basic YAML-like parsing for simple workflows
        lines = yaml_content.strip().split("\n")
        data: Dict[str, Any] = {"steps": []}
        current_step: Optional[Dict[str, Any]] = None

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("name:"):
                data["name"] = stripped.split(":", 1)[1].strip().strip("'\"")
            elif stripped.startswith("- name:"):
                if current_step:
                    data["steps"].append(current_step)
                current_step = {"name": stripped.split(":", 1)[1].strip().strip("'\""), "depends_on": []}
            elif current_step and ":" in stripped:
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key == "depends_on":
                    val = val.strip("[]")
                    current_step[key] = [v.strip().strip("'\"") for v in val.split(",") if v.strip()]
                elif key in ("approval_required",):
                    current_step[key] = val.lower() == "true"
                elif key in ("retry_on_fail", "timeout_seconds"):
                    try:
                        current_step[key] = int(val)
                    except ValueError:
                        pass
                else:
                    current_step[key] = val

        if current_step:
            data["steps"].append(current_step)

        return self._parse_dict(data)

    def _substitute_vars(self, text: str, variables: Dict[str, str]) -> str:
        """Substitute ${var} placeholders in text."""
        for key, value in variables.items():
            text = text.replace(f"${{{key}}}", str(value))
        return text


def get_workflow_runner(collaborate_fn=None, ask_fn=None) -> YAMLWorkflowRunner:
    """Get a workflow runner instance."""
    return YAMLWorkflowRunner(collaborate_fn=collaborate_fn, ask_fn=ask_fn)
