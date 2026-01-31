"""
Chain-of-Thought Prompting
==========================

Implementation of Chain-of-Thought (CoT) prompting techniques for
improved reasoning in AI agents.

Chain-of-Thought prompting encourages the model to break down
complex problems into intermediate reasoning steps, leading to
more accurate and explainable outputs.

Reference: "Chain-of-Thought Prompting Elicits Reasoning in Large
           Language Models" (Wei et al., 2022)

Features:
- Zero-shot CoT ("Let's think step by step")
- Few-shot CoT with examples
- Self-consistency (multiple reasoning paths)
- Automatic reasoning chain extraction
- Verification of reasoning steps
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    """Types of reasoning in chain-of-thought."""
    ZERO_SHOT = "zero_shot"           # "Let's think step by step"
    FEW_SHOT = "few_shot"             # With examples
    SELF_CONSISTENCY = "self_consistency"  # Multiple paths
    TREE_OF_THOUGHT = "tree_of_thought"    # Branching exploration


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    step_number: int
    content: str
    confidence: float = 1.0
    evidence: Optional[str] = None
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "content": self.content,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "alternatives": self.alternatives,
        }


@dataclass
class ReasoningChain:
    """A complete chain of reasoning."""
    problem: str
    steps: List[ReasoningStep]
    conclusion: str
    confidence: float
    reasoning_type: ReasoningType
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        lines = [f"# Reasoning Chain\n\n**Problem:** {self.problem}\n"]
        lines.append(f"**Type:** {self.reasoning_type.value}\n")
        lines.append(f"**Confidence:** {self.confidence:.0%}\n")

        lines.append("\n## Reasoning Steps\n")
        for step in self.steps:
            lines.append(f"\n### Step {step.step_number}")
            lines.append(f"\n{step.content}")
            if step.evidence:
                lines.append(f"\n*Evidence:* {step.evidence}")
            if step.alternatives:
                lines.append(f"\n*Alternatives considered:* {', '.join(step.alternatives)}")

        lines.append(f"\n## Conclusion\n\n{self.conclusion}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem": self.problem,
            "steps": [s.to_dict() for s in self.steps],
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "reasoning_type": self.reasoning_type.value,
        }


class ChainOfThought:
    """
    Chain-of-Thought prompting implementation.

    Provides various CoT techniques to improve reasoning quality:
    - Zero-shot: Simply append "Let's think step by step"
    - Few-shot: Provide examples of step-by-step reasoning
    - Self-consistency: Generate multiple reasoning paths
    - Tree-of-thought: Explore branching solution paths

    Example:
        cot = ChainOfThought(llm_call=my_llm)
        chain = await cot.reason("What is 23 * 17?")
        print(chain.conclusion)  # "391"
    """

    ZERO_SHOT_SUFFIX = "\n\nLet's work through this step by step:\n"

    FEW_SHOT_TEMPLATE = """Here are examples of step-by-step reasoning:

{examples}

Now solve this problem step by step:
{problem}

Let's work through this step by step:
"""

    SELF_CONSISTENCY_PROMPT = """Solve this problem using careful step-by-step reasoning.
Show your work clearly with numbered steps.

Problem: {problem}

Reasoning:"""

    VERIFICATION_PROMPT = """Review this reasoning chain for correctness:

Problem: {problem}

Reasoning Steps:
{steps}

Conclusion: {conclusion}

Verify each step is logically sound. Identify any errors or gaps.
Rate the overall confidence (0-100%):"""

    def __init__(
        self,
        llm_call: Callable,
        default_type: ReasoningType = ReasoningType.ZERO_SHOT,
        num_paths: int = 3,  # For self-consistency
        verify_reasoning: bool = False,
    ):
        """
        Initialize Chain-of-Thought.

        Args:
            llm_call: Async function (prompt, system) -> response
            default_type: Default reasoning type
            num_paths: Number of paths for self-consistency
            verify_reasoning: Whether to verify reasoning chains
        """
        self.llm_call = llm_call
        self.default_type = default_type
        self.num_paths = num_paths
        self.verify_reasoning = verify_reasoning

        # Example bank for few-shot
        self.examples: Dict[str, List[Dict]] = {}

    def add_example(
        self,
        category: str,
        problem: str,
        reasoning: str,
        answer: str,
    ):
        """Add a few-shot example."""
        if category not in self.examples:
            self.examples[category] = []

        self.examples[category].append({
            "problem": problem,
            "reasoning": reasoning,
            "answer": answer,
        })

    async def reason(
        self,
        problem: str,
        reasoning_type: ReasoningType = None,
        category: str = None,
        context: str = None,
    ) -> ReasoningChain:
        """
        Apply chain-of-thought reasoning to a problem.

        Args:
            problem: The problem to reason about
            reasoning_type: Type of CoT to use
            category: Category for few-shot examples
            context: Additional context

        Returns:
            ReasoningChain with steps and conclusion
        """
        import time
        start_time = time.time()

        reasoning_type = reasoning_type or self.default_type

        if reasoning_type == ReasoningType.ZERO_SHOT:
            chain = await self._zero_shot_reason(problem, context)
        elif reasoning_type == ReasoningType.FEW_SHOT:
            chain = await self._few_shot_reason(problem, category, context)
        elif reasoning_type == ReasoningType.SELF_CONSISTENCY:
            chain = await self._self_consistency_reason(problem, context)
        elif reasoning_type == ReasoningType.TREE_OF_THOUGHT:
            chain = await self._tree_of_thought_reason(problem, context)
        else:
            chain = await self._zero_shot_reason(problem, context)

        chain.execution_time = time.time() - start_time
        chain.reasoning_type = reasoning_type

        # Optionally verify
        if self.verify_reasoning:
            verification = await self._verify_chain(chain)
            chain.metadata["verification"] = verification
            chain.confidence = verification.get("confidence", chain.confidence)

        return chain

    async def _zero_shot_reason(
        self,
        problem: str,
        context: str = None,
    ) -> ReasoningChain:
        """Zero-shot chain-of-thought."""
        prompt = problem + self.ZERO_SHOT_SUFFIX
        if context:
            prompt = f"Context: {context}\n\n{prompt}"

        response = await self.llm_call(prompt, None)
        steps, conclusion = self._parse_reasoning(response)

        return ReasoningChain(
            problem=problem,
            steps=steps,
            conclusion=conclusion,
            confidence=0.8,  # Default confidence for zero-shot
            reasoning_type=ReasoningType.ZERO_SHOT,
        )

    async def _few_shot_reason(
        self,
        problem: str,
        category: str = None,
        context: str = None,
    ) -> ReasoningChain:
        """Few-shot chain-of-thought with examples."""
        # Get examples
        examples = []
        if category and category in self.examples:
            examples = self.examples[category][:3]  # Max 3 examples
        elif self.examples:
            # Use first available category
            first_category = list(self.examples.keys())[0]
            examples = self.examples[first_category][:3]

        if not examples:
            # Fall back to zero-shot
            return await self._zero_shot_reason(problem, context)

        # Format examples
        example_text = "\n\n".join([
            f"Problem: {ex['problem']}\n"
            f"Reasoning: {ex['reasoning']}\n"
            f"Answer: {ex['answer']}"
            for ex in examples
        ])

        prompt = self.FEW_SHOT_TEMPLATE.format(
            examples=example_text,
            problem=problem,
        )

        if context:
            prompt = f"Context: {context}\n\n{prompt}"

        response = await self.llm_call(prompt, None)
        steps, conclusion = self._parse_reasoning(response)

        return ReasoningChain(
            problem=problem,
            steps=steps,
            conclusion=conclusion,
            confidence=0.85,  # Higher confidence with examples
            reasoning_type=ReasoningType.FEW_SHOT,
        )

    async def _self_consistency_reason(
        self,
        problem: str,
        context: str = None,
    ) -> ReasoningChain:
        """
        Self-consistency: Generate multiple reasoning paths
        and select the most consistent answer.
        """
        prompt = self.SELF_CONSISTENCY_PROMPT.format(problem=problem)
        if context:
            prompt = f"Context: {context}\n\n{prompt}"

        # Generate multiple paths
        tasks = [
            self.llm_call(prompt, None)
            for _ in range(self.num_paths)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse all paths
        all_chains = []
        all_conclusions = []

        for response in responses:
            if isinstance(response, Exception):
                continue
            steps, conclusion = self._parse_reasoning(response)
            all_chains.append((steps, conclusion))
            all_conclusions.append(conclusion.lower().strip())

        if not all_chains:
            return await self._zero_shot_reason(problem, context)

        # Find most common conclusion
        conclusion_counts = {}
        for conc in all_conclusions:
            conclusion_counts[conc] = conclusion_counts.get(conc, 0) + 1

        most_common = max(conclusion_counts, key=conclusion_counts.get)
        consistency = conclusion_counts[most_common] / len(all_conclusions)

        # Use the chain that reached the most common conclusion
        for steps, conclusion in all_chains:
            if conclusion.lower().strip() == most_common:
                return ReasoningChain(
                    problem=problem,
                    steps=steps,
                    conclusion=conclusion,
                    confidence=consistency,
                    reasoning_type=ReasoningType.SELF_CONSISTENCY,
                    metadata={
                        "num_paths": len(all_chains),
                        "agreement": consistency,
                        "all_conclusions": list(set(all_conclusions)),
                    },
                )

        # Fallback
        steps, conclusion = all_chains[0]
        return ReasoningChain(
            problem=problem,
            steps=steps,
            conclusion=conclusion,
            confidence=consistency,
            reasoning_type=ReasoningType.SELF_CONSISTENCY,
        )

    async def _tree_of_thought_reason(
        self,
        problem: str,
        context: str = None,
        max_depth: int = 3,
        branching_factor: int = 2,
    ) -> ReasoningChain:
        """
        Tree-of-Thought: Explore branching solution paths.

        At each step, generate multiple possible next steps,
        evaluate them, and pursue the most promising.
        """
        tree_prompt = f"""Problem: {problem}

Generate {branching_factor} different approaches to start solving this problem.
For each approach, provide:
1. The approach description
2. Why this might work
3. Potential issues

Format as:
APPROACH 1: [description]
RATIONALE: [why it might work]
CONCERNS: [potential issues]

APPROACH 2: ...
"""

        if context:
            tree_prompt = f"Context: {context}\n\n{tree_prompt}"

        response = await self.llm_call(tree_prompt, None)

        # Parse approaches
        approaches = self._parse_approaches(response)

        if not approaches:
            return await self._zero_shot_reason(problem, context)

        # Evaluate and select best approach
        best_approach = approaches[0]  # Simplified: take first

        # Follow through with selected approach
        follow_prompt = f"""Problem: {problem}

Selected Approach: {best_approach['description']}

Now solve the problem completely using this approach.
Show all steps clearly.

Solution:"""

        follow_response = await self.llm_call(follow_prompt, None)
        steps, conclusion = self._parse_reasoning(follow_response)

        # Add approach selection as first step
        approach_step = ReasoningStep(
            step_number=0,
            content=f"Selected approach: {best_approach['description']}",
            alternatives=[a['description'] for a in approaches[1:]],
        )

        steps = [approach_step] + steps

        return ReasoningChain(
            problem=problem,
            steps=steps,
            conclusion=conclusion,
            confidence=0.75,
            reasoning_type=ReasoningType.TREE_OF_THOUGHT,
            metadata={
                "approaches_considered": len(approaches),
                "selected_approach": best_approach,
            },
        )

    def _parse_reasoning(self, response: str) -> Tuple[List[ReasoningStep], str]:
        """Parse reasoning steps from response."""
        steps = []
        lines = response.strip().split("\n")

        current_step = None
        step_num = 0
        conclusion = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for numbered steps
            step_match = re.match(r'^(?:Step\s+)?(\d+)[.):]\s*(.+)', line, re.IGNORECASE)
            if step_match:
                if current_step:
                    steps.append(current_step)
                step_num = int(step_match.group(1))
                current_step = ReasoningStep(
                    step_number=step_num,
                    content=step_match.group(2),
                )
                continue

            # Check for conclusion markers
            if any(marker in line.lower() for marker in
                   ["therefore", "thus", "conclusion", "answer:", "final answer", "so,"]):
                if current_step:
                    steps.append(current_step)
                    current_step = None
                conclusion = line
                continue

            # Continue current step or start new one
            if current_step:
                current_step.content += " " + line
            elif not steps:
                step_num += 1
                current_step = ReasoningStep(
                    step_number=step_num,
                    content=line,
                )

        if current_step:
            steps.append(current_step)

        # If no explicit conclusion, use last step
        if not conclusion and steps:
            conclusion = steps[-1].content

        # Renumber steps
        for i, step in enumerate(steps):
            step.step_number = i + 1

        return steps, conclusion

    def _parse_approaches(self, response: str) -> List[Dict[str, str]]:
        """Parse tree-of-thought approaches."""
        approaches = []

        # Split by approach markers
        pattern = r'APPROACH\s+(\d+)[:\s]*(.+?)(?=APPROACH\s+\d+|$)'
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        for num, content in matches:
            approach = {"description": "", "rationale": "", "concerns": ""}

            # Parse subfields
            if "RATIONALE:" in content.upper():
                parts = re.split(r'RATIONALE:', content, flags=re.IGNORECASE)
                approach["description"] = parts[0].strip()
                if len(parts) > 1:
                    remaining = parts[1]
                    if "CONCERNS:" in remaining.upper():
                        rat_parts = re.split(r'CONCERNS:', remaining, flags=re.IGNORECASE)
                        approach["rationale"] = rat_parts[0].strip()
                        if len(rat_parts) > 1:
                            approach["concerns"] = rat_parts[1].strip()
                    else:
                        approach["rationale"] = remaining.strip()
            else:
                approach["description"] = content.strip()

            approaches.append(approach)

        return approaches

    async def _verify_chain(self, chain: ReasoningChain) -> Dict[str, Any]:
        """Verify a reasoning chain."""
        steps_text = "\n".join([
            f"Step {s.step_number}: {s.content}"
            for s in chain.steps
        ])

        prompt = self.VERIFICATION_PROMPT.format(
            problem=chain.problem,
            steps=steps_text,
            conclusion=chain.conclusion,
        )

        response = await self.llm_call(prompt, None)

        # Parse confidence
        confidence_match = re.search(r'(\d+)\s*%', response)
        confidence = int(confidence_match.group(1)) / 100 if confidence_match else 0.7

        return {
            "confidence": confidence,
            "verification_response": response,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }


async def reason_through(
    problem: str,
    llm_call: Callable,
    reasoning_type: ReasoningType = ReasoningType.ZERO_SHOT,
) -> ReasoningChain:
    """
    Convenience function for quick chain-of-thought reasoning.

    Args:
        problem: The problem to reason about
        llm_call: Async LLM function
        reasoning_type: Type of reasoning to use

    Returns:
        ReasoningChain with solution
    """
    cot = ChainOfThought(llm_call=llm_call, default_type=reasoning_type)
    return await cot.reason(problem)
