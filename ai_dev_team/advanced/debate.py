"""
Multi-Model Debate System - AI Models Arguing for Better Solutions

SECRET WEAPON #4: Instead of just asking one model, have multiple models
DEBATE each other! This produces dramatically better results because:

1. Models challenge each other's assumptions
2. Weaknesses in one model's thinking are caught by others
3. The final answer is stress-tested from multiple angles
4. You get diverse perspectives and approaches

This is like having a room full of senior engineers debating your problem!
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DebateRole(Enum):
    """Roles in a debate"""
    PROPOSER = "proposer"      # Presents initial solution
    CHALLENGER = "challenger"  # Challenges the solution
    SYNTHESIZER = "synthesizer"  # Combines best ideas
    JUDGE = "judge"            # Picks the winner


@dataclass
class DebateArgument:
    """A single argument in the debate"""
    model: str
    role: DebateRole
    content: str
    round_number: int
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.8


@dataclass
class DebateResult:
    """Final result of a debate"""
    topic: str
    winner: str
    final_answer: str
    confidence: float
    total_rounds: int
    arguments: List[DebateArgument]
    synthesis: str
    minority_opinions: List[str]
    debate_time: float


class MultiModelDebate:
    """
    Multi-Model Debate System

    Orchestrates debates between AI models to find the best solution.
    Models take turns proposing, challenging, and refining ideas until
    convergence or a judge decides.

    Usage:
        debate = MultiModelDebate()

        # Quick debate
        result = await debate.debate(
            "Should we use microservices or monolith for this project?"
        )

        # Full adversarial debate
        result = await debate.adversarial_debate(
            topic="Best database for our use case",
            context="We have 10M users, need real-time updates, complex queries",
            rounds=3
        )

        # Code review debate
        result = await debate.code_review_debate(code, "Is this secure?")
    """

    def __init__(self):
        self._clients = {}
        self._models = ["claude", "gpt4", "gemini"]

    async def _get_response(
        self,
        model: str,
        prompt: str,
        system: str = ""
    ) -> str:
        """Get response from a model"""
        try:
            if model == "claude":
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    system=system,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            elif model == "gpt4":
                import openai
                client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=4000,
                    messages=messages
                )
                return response.choices[0].message.content

            elif model == "gemini":
                from google import genai
                from google.genai import types
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                client = genai.Client(api_key=api_key)
                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                    ) if system else None,
                )
                return response.text

        except Exception as e:
            logger.error(f"Error getting response from {model}: {e}")
            return f"[{model} unavailable: {e}]"

        return f"[{model} not configured]"

    async def debate(
        self,
        topic: str,
        context: str = "",
        models: List[str] = None,
        rounds: int = 2
    ) -> DebateResult:
        """
        Run a structured debate between models.

        Args:
            topic: The question or topic to debate
            context: Additional context (code, requirements, etc.)
            models: Which models to include (default: all available)
            rounds: Number of debate rounds

        Returns:
            DebateResult with the synthesized answer
        """
        start_time = time.time()
        models = models or self._models[:3]  # Use up to 3 models
        arguments: List[DebateArgument] = []

        full_topic = topic
        if context:
            full_topic = f"Context:\n{context}\n\nTopic: {topic}"

        # Round 1: Each model proposes their solution
        logger.info(f"Debate starting: {topic}")
        logger.info("Round 1: Initial proposals")

        initial_prompt = f"""You are participating in a debate about: {full_topic}

Present your best solution or answer. Be specific and justify your position with reasoning.
Consider pros, cons, trade-offs, and potential issues."""

        proposals = await asyncio.gather(*[
            self._get_response(model, initial_prompt, "You are an expert debater. Present your position clearly and persuasively.")
            for model in models
        ])

        for i, (model, proposal) in enumerate(zip(models, proposals)):
            arguments.append(DebateArgument(
                model=model,
                role=DebateRole.PROPOSER,
                content=proposal,
                round_number=1
            ))

        # Rounds 2+: Challenge and refine
        for round_num in range(2, rounds + 1):
            logger.info(f"Round {round_num}: Challenges and refinements")

            # Each model responds to the others
            all_proposals = "\n\n---\n\n".join([
                f"**{models[i].upper()}'s position:**\n{proposals[i]}"
                for i in range(len(models))
            ])

            challenge_prompt = f"""The debate topic is: {full_topic}

Here are the current positions:
{all_proposals}

Now, respond to the other positions:
1. Identify weaknesses in their arguments
2. Defend your position against their challenges
3. Acknowledge valid points they made
4. Refine your position if needed

Be constructive but rigorous."""

            challenges = await asyncio.gather(*[
                self._get_response(model, challenge_prompt, "You are a rigorous debater. Challenge weak arguments while acknowledging good points.")
                for model in models
            ])

            for i, (model, challenge) in enumerate(zip(models, challenges)):
                arguments.append(DebateArgument(
                    model=model,
                    role=DebateRole.CHALLENGER,
                    content=challenge,
                    round_number=round_num
                ))

            proposals = challenges  # Update for next round

        # Final synthesis
        logger.info("Final round: Synthesis")

        all_arguments = "\n\n---\n\n".join([
            f"**{arg.model.upper()} (Round {arg.round_number}, {arg.role.value}):**\n{arg.content}"
            for arg in arguments
        ])

        synthesis_prompt = f"""You are the synthesizer in a debate about: {full_topic}

Here is the full debate:
{all_arguments}

Your job is to:
1. Identify the strongest arguments from each side
2. Find common ground and areas of agreement
3. Resolve contradictions with reasoned analysis
4. Produce a FINAL ANSWER that takes the best from all perspectives
5. Note any minority opinions that may still be valid

Provide a comprehensive synthesis."""

        # Use the most capable model for synthesis
        synthesis = await self._get_response(
            "claude",
            synthesis_prompt,
            "You are an expert synthesizer who combines diverse viewpoints into coherent conclusions."
        )

        arguments.append(DebateArgument(
            model="claude",
            role=DebateRole.SYNTHESIZER,
            content=synthesis,
            round_number=rounds + 1
        ))

        # Extract minority opinions
        minority_opinions = []
        for arg in arguments:
            if "disagree" in arg.content.lower() or "however" in arg.content.lower():
                # This is a simplified extraction - could be more sophisticated
                pass

        return DebateResult(
            topic=topic,
            winner="synthesis",  # In collaborative debate, synthesis wins
            final_answer=synthesis,
            confidence=0.9,
            total_rounds=rounds,
            arguments=arguments,
            synthesis=synthesis,
            minority_opinions=minority_opinions,
            debate_time=time.time() - start_time
        )

    async def adversarial_debate(
        self,
        topic: str,
        position_a: str,
        position_b: str,
        context: str = "",
        rounds: int = 3
    ) -> DebateResult:
        """
        Run an adversarial debate between two specific positions.

        This is useful when you want to explore a specific trade-off,
        like "microservices vs monolith" or "SQL vs NoSQL".

        Args:
            topic: The overall topic
            position_a: First position to argue
            position_b: Second position to argue
            context: Additional context
            rounds: Number of rounds

        Returns:
            DebateResult with judge's decision
        """
        start_time = time.time()
        arguments: List[DebateArgument] = []

        # Assign positions
        model_a = "claude"
        model_b = "gpt4"
        judge = "gemini"

        context_str = f"\nContext: {context}" if context else ""

        for round_num in range(1, rounds + 1):
            logger.info(f"Adversarial round {round_num}")

            # Get previous arguments for context
            prev_args = ""
            if arguments:
                prev_args = "\n\nPrevious arguments:\n" + "\n---\n".join([
                    f"{a.model}: {a.content[:500]}..." for a in arguments[-4:]
                ])

            # Position A argues
            prompt_a = f"""You are arguing FOR: {position_a}
Topic: {topic}{context_str}
{prev_args}

Round {round_num}: Make your strongest argument for {position_a}.
Address any challenges from the opposing side.
Be specific with examples and evidence."""

            arg_a = await self._get_response(model_a, prompt_a, f"You strongly believe in {position_a}. Argue persuasively.")
            arguments.append(DebateArgument(model=model_a, role=DebateRole.PROPOSER, content=arg_a, round_number=round_num))

            # Position B argues
            prompt_b = f"""You are arguing FOR: {position_b}
Topic: {topic}{context_str}
{prev_args}

Latest argument for {position_a}:
{arg_a}

Round {round_num}: Counter this argument and make your case for {position_b}.
Be specific with examples and evidence."""

            arg_b = await self._get_response(model_b, prompt_b, f"You strongly believe in {position_b}. Argue persuasively.")
            arguments.append(DebateArgument(model=model_b, role=DebateRole.CHALLENGER, content=arg_b, round_number=round_num))

        # Judge decides
        all_args = "\n\n---\n\n".join([
            f"**{a.model} (Round {a.round_number}) argues for {position_a if a.model == model_a else position_b}:**\n{a.content}"
            for a in arguments
        ])

        judge_prompt = f"""You are the impartial judge in a debate.

Topic: {topic}{context_str}

Position A: {position_a}
Position B: {position_b}

Here is the full debate:
{all_args}

As the judge, provide:
1. Summary of strongest arguments for each side
2. Weaknesses in each position
3. YOUR VERDICT: Which position wins and why?
4. Nuanced recommendation: When might each approach be better?
5. Final synthesis incorporating the best of both"""

        judgment = await self._get_response(judge, judge_prompt, "You are a fair, analytical judge who values evidence and logic.")
        arguments.append(DebateArgument(model=judge, role=DebateRole.JUDGE, content=judgment, round_number=rounds + 1))

        # Determine winner from judgment
        winner = position_a if position_a.lower() in judgment.lower()[:500] else position_b

        return DebateResult(
            topic=topic,
            winner=winner,
            final_answer=judgment,
            confidence=0.85,
            total_rounds=rounds,
            arguments=arguments,
            synthesis=judgment,
            minority_opinions=[],
            debate_time=time.time() - start_time
        )

    async def code_review_debate(
        self,
        code: str,
        focus: str = "security and best practices"
    ) -> DebateResult:
        """
        Have models debate about code quality.

        Each model reviews the code and they discuss their findings.
        Great for catching issues that one model might miss!
        """
        topic = f"Code review focusing on: {focus}"

        return await self.debate(
            topic=topic,
            context=f"```\n{code}\n```",
            rounds=2
        )

    async def architecture_debate(
        self,
        requirements: str
    ) -> DebateResult:
        """
        Have models debate the best architecture for requirements.
        """
        return await self.debate(
            topic="What is the best architecture for these requirements?",
            context=requirements,
            rounds=3
        )


# Convenience functions
async def quick_debate(question: str) -> str:
    """Quick debate on any question"""
    debate = MultiModelDebate()
    result = await debate.debate(question)
    return result.final_answer


async def versus_debate(topic: str, option_a: str, option_b: str) -> str:
    """Quick A vs B debate"""
    debate = MultiModelDebate()
    result = await debate.adversarial_debate(topic, option_a, option_b)
    return result.final_answer
