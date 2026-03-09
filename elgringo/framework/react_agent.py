"""
ReAct Agent Framework
=====================

Implementation of the ReAct (Reasoning + Acting) pattern for AI agents.

ReAct interleaves reasoning (thinking) with acting (tool use) to solve
complex tasks through a series of thought-action-observation cycles.

Reference: "ReAct: Synergizing Reasoning and Acting in Language Models"
           (Yao et al., 2022)

Features:
- Structured thought-action-observation loops
- Automatic tool selection and execution
- Execution trace for debugging
- Configurable max iterations
- Support for multiple LLM backends
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .tools import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


class ThoughtType(Enum):
    """Types of thoughts in ReAct."""
    REASONING = "reasoning"      # Analyzing the problem
    PLANNING = "planning"        # Deciding what to do next
    REFLECTION = "reflection"    # Evaluating progress
    CONCLUSION = "conclusion"    # Final answer


@dataclass
class ReActStep:
    """A single step in the ReAct execution."""
    step_number: int
    thought: str
    thought_type: ThoughtType
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_prompt_format(self) -> str:
        """Format step for inclusion in prompt."""
        lines = [f"Thought {self.step_number}: {self.thought}"]
        if self.action:
            lines.append(f"Action {self.step_number}: {self.action}")
            if self.action_input:
                lines.append(f"Action Input {self.step_number}: {json.dumps(self.action_input)}")
        if self.observation:
            lines.append(f"Observation {self.step_number}: {self.observation}")
        return "\n".join(lines)


@dataclass
class ReActTrace:
    """Complete execution trace of a ReAct agent run."""
    task: str
    steps: List[ReActStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    success: bool = False
    total_tokens: int = 0
    execution_time: float = 0.0
    tools_used: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Convert trace to markdown for display."""
        lines = [f"# ReAct Trace\n\n**Task:** {self.task}\n"]

        for step in self.steps:
            lines.append(f"\n## Step {step.step_number}\n")
            lines.append(f"**Thought** ({step.thought_type.value}): {step.thought}\n")
            if step.action:
                lines.append(f"**Action:** `{step.action}`\n")
                if step.action_input:
                    lines.append(f"```json\n{json.dumps(step.action_input, indent=2)}\n```\n")
            if step.observation:
                lines.append(f"**Observation:**\n```\n{step.observation[:500]}\n```\n")

        if self.final_answer:
            lines.append(f"\n## Final Answer\n\n{self.final_answer}\n")

        lines.append(f"\n---\n**Tools Used:** {', '.join(self.tools_used) or 'None'}")
        lines.append(f"**Steps:** {len(self.steps)}")
        lines.append(f"**Success:** {self.success}")

        return "\n".join(lines)


class ReActAgent:
    """
    ReAct Agent that interleaves reasoning with tool use.

    The agent follows this pattern:
    1. Thought: Reason about the current state and what to do
    2. Action: Select and execute a tool
    3. Observation: Process the tool's output
    4. Repeat until task is complete or max steps reached

    Example:
        agent = ReActAgent(llm_call=my_llm_function)
        trace = await agent.run("Find all Python files with TODO comments")
        print(trace.final_answer)
    """

    SYSTEM_PROMPT = """You are a ReAct agent that solves tasks by interleaving reasoning with actions.

For each step, you must output:
1. Thought: Your reasoning about what to do next
2. Action: The tool to use (or "finish" if done)
3. Action Input: The parameters for the tool (as JSON)

Available tools:
{tools}

Format your response EXACTLY like this:
Thought: [your reasoning]
Action: [tool_name or "finish"]
Action Input: {{"param1": "value1", "param2": "value2"}}

When you have the final answer, use:
Thought: I now have enough information to answer.
Action: finish
Action Input: {{"answer": "your final answer here"}}

Important:
- Always think step by step
- Use tools to gather information
- Reflect on observations before proceeding
- If stuck, try a different approach
"""

    def __init__(
        self,
        llm_call: Callable,
        tools: ToolRegistry = None,
        max_steps: int = 10,
        verbose: bool = False,
    ):
        """
        Initialize ReAct agent.

        Args:
            llm_call: Async function that takes (prompt, system) and returns response text
            tools: Tool registry (uses global registry if not provided)
            max_steps: Maximum reasoning steps before stopping
            verbose: Print steps as they execute
        """
        self.llm_call = llm_call
        self.tools = tools or get_tool_registry()
        self.max_steps = max_steps
        self.verbose = verbose

    def _build_system_prompt(self) -> str:
        """Build system prompt with available tools."""
        tool_descriptions = []
        for name in self.tools.list_tools():
            tool = self.tools.get(name)
            if tool:
                params = ", ".join(
                    f"{p.name}: {p.type.value}" + ("" if p.required else f" = {p.default}")
                    for p in tool.parameters
                )
                tool_descriptions.append(f"- {name}({params}): {tool.description}")

        return self.SYSTEM_PROMPT.format(tools="\n".join(tool_descriptions))

    def _build_prompt(self, task: str, steps: List[ReActStep]) -> str:
        """Build the prompt with task and previous steps."""
        lines = [f"Task: {task}\n"]

        for step in steps:
            lines.append(step.to_prompt_format())
            lines.append("")

        lines.append("Now continue with the next step:")
        return "\n".join(lines)

    def _parse_response(self, response: str) -> Tuple[str, ThoughtType, Optional[str], Optional[Dict]]:
        """Parse LLM response into thought, action, and input."""
        thought = ""
        action = None
        action_input = None
        thought_type = ThoughtType.REASONING

        # Extract thought
        thought_match = re.search(r'Thought[:\s]*(.+?)(?=Action|$)', response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()

            # Determine thought type
            thought_lower = thought.lower()
            if "plan" in thought_lower or "will" in thought_lower:
                thought_type = ThoughtType.PLANNING
            elif "reflect" in thought_lower or "observe" in thought_lower:
                thought_type = ThoughtType.REFLECTION
            elif "final" in thought_lower or "answer" in thought_lower or "conclude" in thought_lower:
                thought_type = ThoughtType.CONCLUSION

        # Extract action
        action_match = re.search(r'Action[:\s]*(\w+)', response, re.IGNORECASE)
        if action_match:
            action = action_match.group(1).lower()

        # Extract action input
        input_match = re.search(r'Action Input[:\s]*(\{.+?\})', response, re.DOTALL | re.IGNORECASE)
        if input_match:
            try:
                action_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                # Try to fix common JSON issues
                try:
                    fixed = input_match.group(1).replace("'", '"')
                    action_input = json.loads(fixed)
                except Exception:
                    action_input = {"raw": input_match.group(1)}

        return thought, thought_type, action, action_input

    async def run(self, task: str) -> ReActTrace:
        """
        Run the ReAct agent on a task.

        Args:
            task: The task to solve

        Returns:
            ReActTrace with complete execution history
        """
        import time
        start_time = time.time()

        trace = ReActTrace(task=task)
        steps: List[ReActStep] = []

        system_prompt = self._build_system_prompt()

        for step_num in range(1, self.max_steps + 1):
            # Build prompt
            prompt = self._build_prompt(task, steps)

            # Get LLM response
            try:
                response = await self.llm_call(prompt, system_prompt)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                break

            # Parse response
            thought, thought_type, action, action_input = self._parse_response(response)

            if self.verbose:
                print(f"\n=== Step {step_num} ===")
                print(f"Thought: {thought}")
                print(f"Action: {action}")
                print(f"Input: {action_input}")

            # Create step
            step = ReActStep(
                step_number=step_num,
                thought=thought,
                thought_type=thought_type,
                action=action,
                action_input=action_input,
            )

            # Handle finish action
            if action == "finish":
                if action_input and "answer" in action_input:
                    trace.final_answer = action_input["answer"]
                else:
                    trace.final_answer = thought
                trace.success = True
                steps.append(step)
                break

            # Execute tool
            if action:
                result = await self.tools.execute(action, action_input or {})
                step.observation = result.to_string()

                if result.success:
                    trace.tools_used.append(action)

                if self.verbose:
                    print(f"Observation: {step.observation[:200]}...")

            steps.append(step)

        trace.steps = steps
        trace.execution_time = time.time() - start_time

        return trace

    async def run_with_callbacks(
        self,
        task: str,
        on_thought: Callable[[str, ThoughtType], None] = None,
        on_action: Callable[[str, Dict], None] = None,
        on_observation: Callable[[str], None] = None,
    ) -> ReActTrace:
        """
        Run with callbacks for each step (useful for streaming UI).

        Args:
            task: The task to solve
            on_thought: Callback when thought is generated
            on_action: Callback when action is selected
            on_observation: Callback when observation is received

        Returns:
            ReActTrace with complete execution history
        """
        import time
        start_time = time.time()

        trace = ReActTrace(task=task)
        steps: List[ReActStep] = []

        system_prompt = self._build_system_prompt()

        for step_num in range(1, self.max_steps + 1):
            prompt = self._build_prompt(task, steps)

            try:
                response = await self.llm_call(prompt, system_prompt)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                break

            thought, thought_type, action, action_input = self._parse_response(response)

            # Callbacks
            if on_thought:
                on_thought(thought, thought_type)

            step = ReActStep(
                step_number=step_num,
                thought=thought,
                thought_type=thought_type,
                action=action,
                action_input=action_input,
            )

            if action == "finish":
                if action_input and "answer" in action_input:
                    trace.final_answer = action_input["answer"]
                else:
                    trace.final_answer = thought
                trace.success = True
                steps.append(step)
                break

            if action:
                if on_action:
                    on_action(action, action_input or {})

                result = await self.tools.execute(action, action_input or {})
                step.observation = result.to_string()

                if on_observation:
                    on_observation(step.observation)

                if result.success:
                    trace.tools_used.append(action)

            steps.append(step)

        trace.steps = steps
        trace.execution_time = time.time() - start_time

        return trace


async def create_react_agent_with_orchestrator(task: str, verbose: bool = False) -> ReActTrace:
    """
    Create and run a ReAct agent using the AI Team orchestrator.

    This is a convenience function that sets up the ReAct agent with
    the AI Team's orchestrator as the LLM backend.
    """
    from ..orchestrator import AIDevTeam

    team = AIDevTeam(project_name="react-agent", enable_memory=False)

    async def llm_call(prompt: str, system: str) -> str:
        result = await team.collaborate(
            prompt=prompt,
            context=system,
            mode="fastest",  # Use fastest available agent
        )
        return result.final_answer if hasattr(result, 'final_answer') else str(result)

    agent = ReActAgent(llm_call=llm_call, verbose=verbose)
    return await agent.run(task)
