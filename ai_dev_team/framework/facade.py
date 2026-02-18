"""
Framework Facade - Extracted from AIDevTeam orchestrator
=========================================================

Provides access to advanced agent framework features:
ReAct, planning, chain-of-thought reasoning, and context management.
"""

import logging
from typing import Any, Dict, List, Optional

from . import (
    ReActAgent,
    ReActTrace,
    TaskPlanner,
    ExecutionPlan,
    ChainOfThought,
    ReasoningChain,
    ContextManager,
    get_tool_registry,
)

logger = logging.getLogger(__name__)


class FrameworkFacade:
    """
    Facade for advanced agent framework features.

    Extracted from AIDevTeam to reduce orchestrator complexity.
    Takes a reference to the orchestrator for access to agents and learning.
    """

    def __init__(self, orchestrator):
        self._orchestrator = orchestrator

    @property
    def _auto_learner(self):
        return self._orchestrator._auto_learner

    def _get_best_agent(self):
        """Get the best available agent for framework tasks."""
        if not self._orchestrator.agents:
            return None

        # Prefer the best available reasoning agent (ChatGPT leads)
        for pattern in ["chatgpt", "gpt", "grok-reasoner", "grok", "gemini", "claude"]:
            for name, agent in self._orchestrator.agents.items():
                if pattern in name.lower():
                    return agent

        # Then any cloud agent
        for name, agent in self._orchestrator.agents.items():
            if "local" not in name.lower():
                return agent

        # Finally, any agent
        return list(self._orchestrator.agents.values())[0]

    async def react(
        self,
        task: str,
        max_steps: int = 10,
        verbose: bool = False,
    ) -> ReActTrace:
        """
        Execute a task using ReAct (Reasoning + Acting) pattern.

        ReAct interleaves reasoning with tool use for complex problem solving.
        The agent will think step-by-step, decide on actions, observe results,
        and continue until the task is complete.

        Args:
            task: The task to solve
            max_steps: Maximum reasoning/action steps
            verbose: Print steps as they execute

        Returns:
            ReActTrace with complete execution history

        Example:
            trace = await team.react("Find all TODO comments in Python files")
            print(trace.final_answer)
        """
        # Create LLM call function using best available agent
        agent = self._get_best_agent()

        if not agent:
            return ReActTrace(
                task=task,
                success=False,
                final_answer="No agents available for ReAct execution",
            )

        async def llm_call(prompt: str, system: str) -> str:
            context = system if system else ""
            response = await agent.generate_response(prompt, context)
            return response.content if response.success else f"Error: {response.error}"

        # Create and run ReAct agent
        react_agent = ReActAgent(
            llm_call=llm_call,
            tools=get_tool_registry(),
            max_steps=max_steps,
            verbose=verbose,
        )

        trace = await react_agent.run(task)

        # Auto-learn from ReAct execution
        if self._auto_learner and trace.success:
            # Ensure final_answer is a string for auto-learner
            answer_str = trace.final_answer if isinstance(trace.final_answer, str) else str(trace.final_answer)
            await self._auto_learner.capture_interaction(
                user_prompt=task,
                ai_responses=[{"agent": "react", "content": answer_str}],
                outcome="success",
                task_type="react",
                metadata={
                    "steps": len(trace.steps),
                    "tools_used": trace.tools_used,
                }
            )

        return trace

    async def plan_and_execute(
        self,
        goal: str,
        context: str = "",
        available_tools: Optional[List[str]] = None,
    ) -> ExecutionPlan:
        """
        Create and execute a multi-step plan for achieving a goal.

        The planner will decompose the goal into steps, track dependencies,
        and execute steps in parallel when possible.

        Args:
            goal: The goal to achieve
            context: Additional context
            available_tools: List of available tool names

        Returns:
            ExecutionPlan with results

        Example:
            plan = await team.plan_and_execute("Set up a new Python project with tests")
            print(plan.to_markdown())
        """
        # Create LLM call function
        agent = self._get_best_agent()

        if not agent:
            return ExecutionPlan(
                id="error",
                goal=goal,
                steps=[],
                metadata={"error": "No agents available"},
            )

        async def llm_call(prompt: str) -> str:
            response = await agent.generate_response(prompt, context)
            return response.content if response.success else ""

        # Create planner
        planner = TaskPlanner(llm_call=llm_call)

        # Create plan
        plan = await planner.create_plan(
            goal=goal,
            context=context,
            available_tools=available_tools,
        )

        # Optimize plan for parallelization
        plan = await planner.optimize_plan(plan)

        # Execute plan with callbacks
        def on_step_start(step):
            logger.info(f"Starting step: {step.description}")

        def on_step_complete(step):
            logger.info(f"Completed step: {step.description}")

        def on_step_failed(step, error):
            logger.warning(f"Step failed: {step.description} - {error}")

        executed_plan = await planner.execute_plan(
            plan,
            on_step_start=on_step_start,
            on_step_complete=on_step_complete,
            on_step_failed=on_step_failed,
        )

        return executed_plan

    async def reason(
        self,
        problem: str,
        method: str = "zero_shot",
        verify: bool = False,
    ) -> ReasoningChain:
        """
        Apply chain-of-thought reasoning to a problem.

        Encourages step-by-step reasoning for more accurate answers.

        Args:
            problem: The problem to reason about
            method: "zero_shot", "few_shot", "self_consistency", or "tree_of_thought"
            verify: Whether to verify the reasoning chain

        Returns:
            ReasoningChain with steps and conclusion

        Example:
            chain = await team.reason("What is 17 * 23?")
            print(chain.conclusion)
        """
        from . import ReasoningType

        # Map method string to enum
        method_map = {
            "zero_shot": ReasoningType.ZERO_SHOT,
            "few_shot": ReasoningType.FEW_SHOT,
            "self_consistency": ReasoningType.SELF_CONSISTENCY,
            "tree_of_thought": ReasoningType.TREE_OF_THOUGHT,
        }
        reasoning_type = method_map.get(method, ReasoningType.ZERO_SHOT)

        # Create LLM call function
        agent = self._get_best_agent()

        if not agent:
            return ReasoningChain(
                problem=problem,
                steps=[],
                conclusion="No agents available for reasoning",
                confidence=0.0,
                reasoning_type=reasoning_type,
            )

        async def llm_call(prompt: str, system: str = None) -> str:
            context = system if system else ""
            response = await agent.generate_response(prompt, context)
            return response.content if response.success else ""

        # Create chain-of-thought reasoner
        cot = ChainOfThought(
            llm_call=llm_call,
            default_type=reasoning_type,
            verify_reasoning=verify,
        )

        return await cot.reason(problem, reasoning_type=reasoning_type)

    def get_context_manager(self, max_tokens: int = 8000) -> ContextManager:
        """
        Get a context manager for managing conversation history.

        Useful for long conversations that need to fit within token limits.

        Args:
            max_tokens: Maximum tokens for the context window

        Returns:
            ContextManager instance
        """
        return ContextManager(max_tokens=max_tokens)

    def get_framework_tools(self) -> List[str]:
        """
        Get list of available framework tools.

        Returns:
            List of tool names registered in the framework
        """
        return get_tool_registry().list_tools()

    def get_framework_tool_schemas(self, format: str = "openai") -> List[Dict[str, Any]]:
        """
        Get tool schemas for API integration.

        Args:
            format: "openai" or "anthropic"

        Returns:
            List of tool schemas in the specified format
        """
        return get_tool_registry().get_schemas(format=format)
