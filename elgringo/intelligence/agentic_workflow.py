"""
Agentic Workflow Engine — Multi-step autonomous task execution
==============================================================

Implements persistent workflow loops:
  Plan -> Execute -> Validate -> Fix -> Verify

Each step delegates to different agents, retries on failure,
and feeds results back into the next step.
"""

import asyncio
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowPhase(Enum):
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE = "validate"
    FIX = "fix"
    VERIFY = "verify"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class StepResult:
    step_name: str
    phase: WorkflowPhase
    status: StepStatus
    output: str = ""
    error: str = ""
    agent_used: str = ""
    duration: float = 0.0
    attempt: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    workflow_id: str
    task: str
    phase: WorkflowPhase = WorkflowPhase.PLAN
    steps: List[StepResult] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    success: bool = False
    total_fixes: int = 0
    max_fixes: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "task": self.task[:200],
            "phase": self.phase.value,
            "success": self.success,
            "total_fixes": self.total_fixes,
            "steps": [
                {
                    "name": s.step_name, "phase": s.phase.value,
                    "status": s.status.value, "agent": s.agent_used,
                    "duration": round(s.duration, 2), "attempt": s.attempt,
                    "output_preview": s.output[:200] if s.output else "",
                    "error": s.error[:200] if s.error else "",
                }
                for s in self.steps
            ],
            "plan": self.plan,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class AgenticWorkflow:
    """
    Multi-step autonomous workflow engine.

    Orchestrates: Plan -> Execute -> Validate -> Fix -> Verify

    Usage:
        workflow = AgenticWorkflow(collaborate_fn=team.collaborate)
        result = await workflow.run("Add user authentication to the API")
    """

    def __init__(
        self,
        collaborate_fn: Optional[Callable] = None,
        ask_fn: Optional[Callable] = None,
        max_fix_cycles: int = 3,
        timeout_seconds: int = 300,
    ):
        self._collaborate = collaborate_fn
        self._ask = ask_fn
        self.max_fix_cycles = max_fix_cycles
        self.timeout_seconds = timeout_seconds
        self._active_workflows: Dict[str, WorkflowState] = {}

    async def run(
        self,
        task: str,
        context: str = "",
        validate_fn: Optional[Callable[..., Coroutine]] = None,
        on_step: Optional[Callable[[StepResult], None]] = None,
    ) -> WorkflowState:
        state = WorkflowState(
            workflow_id=str(uuid.uuid4())[:8],
            task=task, max_fixes=self.max_fix_cycles,
        )
        self._active_workflows[state.workflow_id] = state
        start_time = time.time()

        try:
            # Phase 1: PLAN
            state.phase = WorkflowPhase.PLAN
            plan_result = await self._execute_step(
                state, "plan", WorkflowPhase.PLAN,
                prompt=(
                    "Break this task into 3-5 concrete implementation steps. "
                    "For each step, specify what needs to be done and what to verify.\n\n"
                    f"Task: {task}"
                ),
                context=context, mode="consensus",
            )
            if on_step:
                on_step(plan_result)
            if plan_result.status == StepStatus.FAILED:
                state.phase = WorkflowPhase.FAILED
                state.completed_at = datetime.now(timezone.utc).isoformat()
                return state

            state.plan = self._parse_plan(plan_result.output)
            if not state.plan:
                state.plan = [task]

            # Phase 2: EXECUTE
            state.phase = WorkflowPhase.EXECUTE
            execution_outputs = []
            for i, step in enumerate(state.plan):
                if time.time() - start_time > self.timeout_seconds:
                    state.steps.append(StepResult(
                        step_name=f"execute_step_{i+1}", phase=WorkflowPhase.EXECUTE,
                        status=StepStatus.FAILED, error="Workflow timeout exceeded",
                    ))
                    break

                step_context = context
                if execution_outputs:
                    step_context += "\n\nPrevious steps completed:\n" + "\n".join(
                        f"- {o[:200]}" for o in execution_outputs[-3:]
                    )

                exec_result = await self._execute_step(
                    state, f"execute_step_{i+1}", WorkflowPhase.EXECUTE,
                    prompt=f"Implement this step:\n{step}\n\nFull task context: {task}",
                    context=step_context, mode="parallel",
                )
                if on_step:
                    on_step(exec_result)
                execution_outputs.append(exec_result.output)

            # Phase 3: VALIDATE
            state.phase = WorkflowPhase.VALIDATE
            full_output = "\n\n---\n\n".join(execution_outputs)
            validation_passed = await self._validate(state, full_output, task, context, validate_fn, on_step)

            # Phase 4: FIX loop
            fix_count = 0
            while not validation_passed and fix_count < self.max_fix_cycles:
                if time.time() - start_time > self.timeout_seconds:
                    break
                fix_count += 1
                state.total_fixes = fix_count
                state.phase = WorkflowPhase.FIX

                last_val = [s for s in state.steps if s.phase == WorkflowPhase.VALIDATE]
                error_ctx = last_val[-1].error if last_val else "Validation failed"

                fix_result = await self._execute_step(
                    state, f"fix_attempt_{fix_count}", WorkflowPhase.FIX,
                    prompt=(
                        f"The previous implementation had issues. Fix them.\n\n"
                        f"Error: {error_ctx}\n\nOriginal task: {task}\n\n"
                        f"Current implementation:\n{full_output[:2000]}"
                    ),
                    context=context, mode="consensus",
                )
                if on_step:
                    on_step(fix_result)
                if fix_result.status == StepStatus.PASSED:
                    full_output = fix_result.output

                state.phase = WorkflowPhase.VERIFY
                validation_passed = await self._validate(state, full_output, task, context, validate_fn, on_step)

            state.phase = WorkflowPhase.COMPLETE if validation_passed else WorkflowPhase.FAILED
            state.success = validation_passed

        except Exception as e:
            logger.error(f"Workflow {state.workflow_id} failed: {e}")
            state.phase = WorkflowPhase.FAILED
            state.steps.append(StepResult(
                step_name="workflow_error", phase=WorkflowPhase.FAILED,
                status=StepStatus.FAILED, error=str(e),
            ))

        state.completed_at = datetime.now(timezone.utc).isoformat()
        return state

    async def _execute_step(self, state, step_name, phase, prompt, context="", mode="parallel"):
        start = time.time()
        result = StepResult(step_name=step_name, phase=phase, status=StepStatus.RUNNING)
        try:
            if self._collaborate:
                collab = await self._collaborate(prompt=prompt, context=context, mode=mode)
                result.output = collab.final_answer
                result.agent_used = ", ".join(collab.participating_agents)
                result.status = StepStatus.PASSED if collab.success else StepStatus.FAILED
                if not collab.success:
                    result.error = "Collaboration returned no successful responses"
            elif self._ask:
                ask_result = await self._ask(prompt=prompt, context=context)
                result.output = ask_result.content or ""
                result.agent_used = ask_result.agent_name
                result.status = StepStatus.PASSED if ask_result.success else StepStatus.FAILED
            else:
                result.status = StepStatus.FAILED
                result.error = "No collaborate or ask function provided"
        except Exception as e:
            result.status = StepStatus.FAILED
            result.error = str(e)

        result.duration = time.time() - start
        state.steps.append(result)
        return result

    async def _validate(self, state, output, task, context, custom_fn, on_step):
        if custom_fn:
            try:
                is_valid = await custom_fn(output, task)
                result = StepResult(
                    step_name="custom_validation", phase=state.phase,
                    status=StepStatus.PASSED if is_valid else StepStatus.FAILED,
                    output="Custom validation passed" if is_valid else "",
                    error="" if is_valid else "Custom validation failed",
                )
                state.steps.append(result)
                if on_step:
                    on_step(result)
                return is_valid
            except Exception as e:
                result = StepResult(
                    step_name="custom_validation", phase=state.phase,
                    status=StepStatus.FAILED, error=f"Validation error: {e}",
                )
                state.steps.append(result)
                if on_step:
                    on_step(result)
                return False

        val_result = await self._execute_step(
            state, "ai_validation", state.phase,
            prompt=(
                f"Review this implementation for correctness and completeness.\n\n"
                f"Original task: {task}\n\nImplementation:\n{output[:3000]}\n\n"
                f"Respond with PASS if correct and complete, or FAIL followed by specific issues."
            ),
            context=context, mode="consensus",
        )
        if on_step:
            on_step(val_result)

        output_lower = val_result.output.lower()
        if "pass" in output_lower[:50] and "fail" not in output_lower[:50]:
            return True
        val_result.status = StepStatus.FAILED
        val_result.error = val_result.output[:500]
        return False

    def _parse_plan(self, plan_text):
        numbered = re.findall(r'\d+[\.\)]\s*(.+?)(?=\n\d+[\.\)]|\n\n|$)', plan_text, re.DOTALL)
        if numbered:
            return [s.strip() for s in numbered if len(s.strip()) > 10][:7]
        bullets = re.findall(r'[-*]\s+(.+?)(?=\n[-*]|\n\n|$)', plan_text, re.DOTALL)
        if bullets:
            return [s.strip() for s in bullets if len(s.strip()) > 10][:7]
        return [p.strip() for p in plan_text.split("\n\n") if len(p.strip()) > 20][:5]

    def get_workflow(self, workflow_id):
        return self._active_workflows.get(workflow_id)

    def list_workflows(self):
        return [
            {"id": w.workflow_id, "task": w.task[:100], "phase": w.phase.value,
             "success": w.success, "steps": len(w.steps), "fixes": w.total_fixes}
            for w in self._active_workflows.values()
        ]
