"""
AI Development Team Orchestrator
=================================

Main orchestration engine that coordinates multiple AI models for collaborative
software development tasks. Integrates memory, learning, and collaboration systems.
"""

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .agents import (
    AIAgent,
    AgentConfig,
    AgentResponse,
    ChatGPTAgent,
    ClaudeAgent,
    GeminiAgent,
    GrokAgent,
    ModelType,
)

logger = logging.getLogger(__name__)


@dataclass
class CollaborationResult:
    """Result of a collaborative AI team task"""
    task_id: str
    success: bool
    final_answer: str
    agent_responses: List[AgentResponse]
    collaboration_log: List[str]
    total_time: float
    confidence_score: float
    participating_agents: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIDevTeam:
    """
    AI Development Team - Multi-Model Orchestration Platform

    Coordinates Claude, ChatGPT, Gemini, and Grok for collaborative
    software development. Supports multiple collaboration modes,
    intelligent task routing, and persistent learning.

    Usage:
        team = AIDevTeam()
        result = await team.collaborate("Build a user authentication API")
        print(result.final_answer)
    """

    def __init__(
        self,
        project_name: str = "default",
        auto_setup: bool = True,
        enable_memory: bool = True,
        enable_learning: bool = True,
    ):
        self.project_name = project_name
        self.agents: Dict[str, AIAgent] = {}
        self.enable_memory = enable_memory
        self.enable_learning = enable_learning
        self._memory_system = None
        self._collaboration_engine = None
        self._task_router = None

        if auto_setup:
            self.setup_agents()

    def setup_agents(self):
        """Setup default AI team based on available API keys"""
        # Claude - Lead Analyst
        if os.getenv("ANTHROPIC_API_KEY"):
            self.register_agent(ClaudeAgent())
            logger.info("Registered Claude agent (Lead Analyst)")

        # ChatGPT - Senior Developer
        if os.getenv("OPENAI_API_KEY"):
            self.register_agent(ChatGPTAgent())
            logger.info("Registered ChatGPT agent (Senior Developer)")

        # Gemini - Creative Director
        if os.getenv("GEMINI_API_KEY"):
            self.register_agent(GeminiAgent())
            logger.info("Registered Gemini agent (Creative Director)")

        # Grok - Strategic Thinker + Speed Coder
        if os.getenv("XAI_API_KEY"):
            self.register_agent(GrokAgent(fast_mode=False))  # Reasoner
            self.register_agent(GrokAgent(fast_mode=True))   # Fast coder
            logger.info("Registered Grok agents (Reasoner + Coder)")

        if not self.agents:
            logger.warning(
                "No AI agents configured. Set API keys: "
                "ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, XAI_API_KEY"
            )

    def register_agent(self, agent: AIAgent):
        """Register an AI agent with the team"""
        self.agents[agent.name] = agent

    def get_agent(self, name: str) -> Optional[AIAgent]:
        """Get agent by name"""
        return self.agents.get(name)

    @property
    def available_agents(self) -> List[str]:
        """List of available agent names"""
        return list(self.agents.keys())

    async def collaborate(
        self,
        prompt: str,
        context: str = "",
        agents: Optional[List[str]] = None,
        mode: str = "parallel",
        max_iterations: int = 2,
    ) -> CollaborationResult:
        """
        Execute a collaborative task with the AI team.

        Args:
            prompt: The task or question for the team
            context: Additional context (code, documentation, etc.)
            agents: Specific agents to use (None = all available)
            mode: Collaboration mode ("parallel", "sequential", "consensus")
            max_iterations: Maximum collaboration rounds

        Returns:
            CollaborationResult with final answer and agent responses
        """
        task_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        collaboration_log = []
        agent_responses = []

        # Select agents
        if agents:
            active_agents = [self.agents[name] for name in agents if name in self.agents]
        else:
            active_agents = list(self.agents.values())

        if not active_agents:
            return CollaborationResult(
                task_id=task_id,
                success=False,
                final_answer="No agents available for collaboration",
                agent_responses=[],
                collaboration_log=["ERROR: No agents available"],
                total_time=0.0,
                confidence_score=0.0,
                participating_agents=[],
            )

        collaboration_log.append(
            f"Starting {mode} collaboration with {len(active_agents)} agents"
        )

        try:
            if mode == "parallel":
                agent_responses = await self._parallel_collaboration(
                    active_agents, prompt, context, collaboration_log
                )
            elif mode == "sequential":
                agent_responses = await self._sequential_collaboration(
                    active_agents, prompt, context, collaboration_log
                )
            elif mode == "consensus":
                agent_responses = await self._consensus_collaboration(
                    active_agents, prompt, context, max_iterations, collaboration_log
                )
            else:
                # Default to parallel
                agent_responses = await self._parallel_collaboration(
                    active_agents, prompt, context, collaboration_log
                )

            # Synthesize final answer
            final_answer = await self._synthesize_responses(
                agent_responses, prompt, context
            )

            # Calculate confidence
            successful_responses = [r for r in agent_responses if r.success]
            if successful_responses:
                avg_confidence = sum(r.confidence for r in successful_responses) / len(
                    successful_responses
                )
            else:
                avg_confidence = 0.0

            total_time = time.time() - start_time
            collaboration_log.append(f"Completed in {total_time:.2f}s")

            result = CollaborationResult(
                task_id=task_id,
                success=bool(successful_responses),
                final_answer=final_answer,
                agent_responses=agent_responses,
                collaboration_log=collaboration_log,
                total_time=total_time,
                confidence_score=avg_confidence,
                participating_agents=[a.name for a in active_agents],
                metadata={"mode": mode, "iterations": max_iterations},
            )

            # Store in memory if enabled
            if self.enable_memory and self._memory_system:
                await self._memory_system.capture_interaction(result)

            return result

        except Exception as e:
            logger.error(f"Collaboration error: {e}")
            return CollaborationResult(
                task_id=task_id,
                success=False,
                final_answer=f"Collaboration failed: {str(e)}",
                agent_responses=agent_responses,
                collaboration_log=collaboration_log + [f"ERROR: {str(e)}"],
                total_time=time.time() - start_time,
                confidence_score=0.0,
                participating_agents=[a.name for a in active_agents],
            )

    async def _parallel_collaboration(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
        log: List[str],
    ) -> List[AgentResponse]:
        """All agents work simultaneously"""
        log.append("Phase 1: Parallel response generation")

        # Create tasks for all agents
        tasks = [agent.generate_response(prompt, context) for agent in agents]

        # Execute in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses
        agent_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                log.append(f"{agents[i].name}: ERROR - {str(response)}")
            elif isinstance(response, AgentResponse):
                agent_responses.append(response)
                status = "OK" if response.success else f"FAILED: {response.error}"
                log.append(f"{agents[i].name}: {status}")

        return agent_responses

    async def _sequential_collaboration(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
        log: List[str],
    ) -> List[AgentResponse]:
        """Agents work in sequence, each building on previous responses"""
        log.append("Phase 1: Sequential response generation")
        agent_responses = []
        accumulated_context = context

        for i, agent in enumerate(agents):
            # Add previous responses to context
            if agent_responses:
                prev_responses = "\n\n".join(
                    f"Previous response from {r.agent_name}:\n{r.content[:500]}..."
                    for r in agent_responses
                    if r.success
                )
                accumulated_context = f"{context}\n\nTeam Progress:\n{prev_responses}"

            response = await agent.generate_response(prompt, accumulated_context)
            agent_responses.append(response)

            status = "OK" if response.success else f"FAILED: {response.error}"
            log.append(f"Step {i + 1}/{len(agents)} - {agent.name}: {status}")

        return agent_responses

    async def _consensus_collaboration(
        self,
        agents: List[AIAgent],
        prompt: str,
        context: str,
        max_iterations: int,
        log: List[str],
    ) -> List[AgentResponse]:
        """Multiple rounds to build consensus"""
        all_responses = []

        for iteration in range(max_iterations):
            log.append(f"Consensus round {iteration + 1}/{max_iterations}")

            # Build context from previous round
            if all_responses:
                prev_context = "\n\n".join(
                    f"{r.agent_name}:\n{r.content[:300]}..."
                    for r in all_responses[-len(agents) :]
                    if r.success
                )
                round_context = f"{context}\n\nPrevious Team Responses:\n{prev_context}"
                round_prompt = (
                    f"Review team responses and refine your answer:\n{prompt}"
                )
            else:
                round_context = context
                round_prompt = prompt

            # Get responses for this round
            tasks = [agent.generate_response(round_prompt, round_context) for agent in agents]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for i, response in enumerate(responses):
                if isinstance(response, AgentResponse):
                    all_responses.append(response)
                    log.append(f"  {agents[i].name}: {'OK' if response.success else 'FAILED'}")

        return all_responses

    async def _synthesize_responses(
        self,
        responses: List[AgentResponse],
        prompt: str,
        context: str,
    ) -> str:
        """Synthesize multiple responses into a final answer"""
        successful_responses = [r for r in responses if r.success]

        if not successful_responses:
            return "No successful responses from the AI team."

        if len(successful_responses) == 1:
            return successful_responses[0].content

        # Use Claude for synthesis if available, otherwise use first available agent
        synthesis_agent = self.agents.get("claude-analyst")
        if not synthesis_agent:
            synthesis_agent = next(iter(self.agents.values()), None)

        if not synthesis_agent:
            # Fallback: concatenate responses
            return "\n\n---\n\n".join(
                f"**{r.agent_name}:**\n{r.content}" for r in successful_responses
            )

        # Build synthesis prompt
        responses_text = "\n\n".join(
            f"[{r.agent_name} - {r.model_type.value}]:\n{r.content}"
            for r in successful_responses
        )

        synthesis_prompt = f"""Synthesize these AI team responses into one comprehensive answer.
Combine the best insights from each response. Be concise but complete.

Original Task: {prompt}

Team Responses:
{responses_text}

Provide a unified, synthesized response:"""

        synthesis_response = await synthesis_agent.generate_response(
            synthesis_prompt, context
        )

        if synthesis_response.success:
            return synthesis_response.content
        else:
            # Fallback to best single response
            best = max(successful_responses, key=lambda r: r.confidence)
            return best.content

    async def ask(
        self,
        prompt: str,
        agent: Optional[str] = None,
        context: str = "",
    ) -> AgentResponse:
        """
        Quick single-agent query.

        Args:
            prompt: Question or task
            agent: Specific agent name (None = best available)
            context: Additional context

        Returns:
            AgentResponse from the selected agent
        """
        if agent and agent in self.agents:
            selected_agent = self.agents[agent]
        elif self.agents:
            # Use Claude if available, otherwise first agent
            selected_agent = self.agents.get("claude-analyst") or next(
                iter(self.agents.values())
            )
        else:
            return AgentResponse(
                agent_name="none",
                model_type=ModelType.LOCAL,
                content="",
                confidence=0.0,
                response_time=0.0,
                error="No agents available",
            )

        return await selected_agent.generate_response(prompt, context)

    def get_team_status(self) -> Dict[str, Any]:
        """Get status of all team members"""
        return {
            "project": self.project_name,
            "total_agents": len(self.agents),
            "memory_enabled": self.enable_memory,
            "learning_enabled": self.enable_learning,
            "agents": {name: agent.get_stats() for name, agent in self.agents.items()},
        }

    async def code_review(
        self,
        code: str,
        language: str = "python",
        focus: Optional[List[str]] = None,
    ) -> CollaborationResult:
        """
        Collaborative code review.

        Args:
            code: Code to review
            language: Programming language
            focus: Specific aspects to focus on (security, performance, etc.)

        Returns:
            CollaborationResult with review feedback
        """
        focus_str = ", ".join(focus) if focus else "code quality, bugs, and improvements"

        prompt = f"""Review this {language} code. Focus on: {focus_str}

Provide:
1. Issues found (with severity)
2. Suggestions for improvement
3. Security concerns (if any)
4. Overall assessment

Code:
```{language}
{code}
```"""

        return await self.collaborate(prompt, mode="parallel")

    async def debug(
        self,
        error: str,
        code: str = "",
        context: str = "",
    ) -> CollaborationResult:
        """
        Collaborative debugging session.

        Args:
            error: Error message or description
            code: Related code (if any)
            context: Additional context

        Returns:
            CollaborationResult with debugging insights
        """
        prompt = f"""Debug this issue:

Error: {error}

{f'Code:```{code}```' if code else ''}

Provide:
1. Root cause analysis
2. Step-by-step fix
3. Prevention strategies"""

        return await self.collaborate(prompt, context=context, mode="consensus")

    async def architect(
        self,
        requirements: str,
        constraints: Optional[List[str]] = None,
    ) -> CollaborationResult:
        """
        Collaborative architecture design.

        Args:
            requirements: System requirements
            constraints: Technical constraints

        Returns:
            CollaborationResult with architecture proposal
        """
        constraints_str = "\n".join(f"- {c}" for c in constraints) if constraints else "None specified"

        prompt = f"""Design a system architecture for:

Requirements:
{requirements}

Constraints:
{constraints_str}

Provide:
1. High-level architecture
2. Component breakdown
3. Technology recommendations
4. Trade-offs and considerations"""

        return await self.collaborate(prompt, mode="consensus", max_iterations=2)


# Convenience function for quick setup
def create_team(project_name: str = "default", **kwargs) -> AIDevTeam:
    """Create and configure an AI development team"""
    return AIDevTeam(project_name=project_name, **kwargs)
