"""
Extended Thinking Engine - Deep Reasoning Mode

SECRET WEAPON #1: Claude's extended thinking capability allows the model to
"think out loud" before responding, producing much higher quality outputs
for complex problems.

Features:
- Configurable thinking budget (tokens dedicated to reasoning)
- Streaming thinking + response
- Automatic complexity detection
- Thinking extraction for debugging
- Budget-aware automatic activation

This is one of the most powerful features most people don't know about!
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ThinkingResult:
    """Result from extended thinking"""
    thinking: str  # The model's internal reasoning
    response: str  # The final response
    thinking_tokens: int
    response_tokens: int
    total_time: float
    model: str
    complexity_detected: str  # "low", "medium", "high", "extreme"


@dataclass
class ThinkingConfig:
    """Configuration for extended thinking"""
    enabled: bool = True
    min_thinking_tokens: int = 1024  # Minimum thinking budget
    max_thinking_tokens: int = 32000  # Maximum thinking budget
    auto_detect_complexity: bool = True  # Automatically adjust budget based on task
    stream_thinking: bool = True  # Stream thinking process
    save_thinking_logs: bool = True  # Save thinking for analysis


class ExtendedThinkingEngine:
    """
    Extended Thinking Engine for Deep Reasoning

    Uses Claude's extended thinking mode to solve complex problems
    with step-by-step reasoning before producing a response.

    This is particularly effective for:
    - Complex code architecture decisions
    - Debugging intricate bugs
    - Security vulnerability analysis
    - System design problems
    - Mathematical/logical reasoning
    """

    # Complexity indicators for auto-detection
    COMPLEXITY_KEYWORDS = {
        "extreme": [
            "design a system", "architect", "scale to millions",
            "distributed", "microservices", "security audit",
            "performance optimization", "concurrency", "race condition"
        ],
        "high": [
            "refactor", "debug", "analyze", "complex", "algorithm",
            "optimize", "integrate", "migrate", "upgrade", "redesign"
        ],
        "medium": [
            "implement", "create", "build", "add feature", "fix bug",
            "write tests", "documentation", "review"
        ],
        "low": [
            "explain", "what is", "how to", "example", "simple",
            "basic", "quick", "help with"
        ]
    }

    COMPLEXITY_BUDGETS = {
        "extreme": 32000,
        "high": 16000,
        "medium": 8000,
        "low": 2000
    }

    def __init__(self, config: Optional[ThinkingConfig] = None):
        self.config = config or ThinkingConfig()
        self._client = None
        self._thinking_logs: List[ThinkingResult] = []

    async def _get_client(self):
        """Get Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._client = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                logger.error("Anthropic SDK not installed")
        return self._client

    def detect_complexity(self, prompt: str) -> str:
        """Auto-detect task complexity from prompt"""
        prompt_lower = prompt.lower()

        for level in ["extreme", "high", "medium", "low"]:
            for keyword in self.COMPLEXITY_KEYWORDS[level]:
                if keyword in prompt_lower:
                    return level

        # Default based on length
        if len(prompt) > 2000:
            return "high"
        elif len(prompt) > 500:
            return "medium"
        return "low"

    def get_thinking_budget(self, prompt: str) -> int:
        """Calculate thinking token budget based on complexity"""
        if not self.config.auto_detect_complexity:
            return self.config.min_thinking_tokens

        complexity = self.detect_complexity(prompt)
        budget = self.COMPLEXITY_BUDGETS.get(complexity, 4000)

        # Clamp to config limits
        return max(
            self.config.min_thinking_tokens,
            min(budget, self.config.max_thinking_tokens)
        )

    async def think_and_respond(
        self,
        prompt: str,
        context: str = "",
        system_prompt: Optional[str] = None,
        force_thinking: bool = False,
        custom_budget: Optional[int] = None
    ) -> ThinkingResult:
        """
        Generate response with extended thinking.

        The model will think through the problem step-by-step before
        providing a response, leading to much higher quality outputs
        for complex problems.

        Args:
            prompt: The user's request
            context: Additional context (code, docs, etc.)
            system_prompt: Override system prompt
            force_thinking: Force extended thinking even for simple tasks
            custom_budget: Override auto-detected thinking budget

        Returns:
            ThinkingResult with both thinking and response
        """
        client = await self._get_client()
        if not client:
            return ThinkingResult(
                thinking="",
                response="Extended thinking requires ANTHROPIC_API_KEY",
                thinking_tokens=0,
                response_tokens=0,
                total_time=0,
                model="",
                complexity_detected="unknown"
            )

        start_time = time.time()
        complexity = self.detect_complexity(prompt)
        budget = custom_budget or self.get_thinking_budget(prompt)

        # Build the full prompt
        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\n---\n\nTask:\n{prompt}"

        # System prompt for extended thinking
        system = system_prompt or """You are an expert AI assistant with deep expertise in software engineering,
system design, and problem-solving. Think through complex problems step-by-step
before providing your response. Consider edge cases, potential issues, and
alternative approaches in your thinking."""

        try:
            # Use Claude's extended thinking feature
            # This uses the thinking parameter in the API
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",  # Sonnet 4 supports extended thinking
                max_tokens=16000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": budget
                },
                system=system,
                messages=[{"role": "user", "content": full_prompt}]
            )

            # Extract thinking and response
            thinking_text = ""
            response_text = ""
            thinking_tokens = 0
            response_tokens = 0

            for block in response.content:
                if block.type == "thinking":
                    thinking_text = block.thinking
                elif block.type == "text":
                    response_text = block.text

            # Get token counts from usage
            if hasattr(response, 'usage'):
                thinking_tokens = getattr(response.usage, 'thinking_tokens', 0) or 0
                response_tokens = response.usage.output_tokens

            total_time = time.time() - start_time

            result = ThinkingResult(
                thinking=thinking_text,
                response=response_text,
                thinking_tokens=thinking_tokens,
                response_tokens=response_tokens,
                total_time=total_time,
                model="claude-sonnet-4-20250514",
                complexity_detected=complexity
            )

            # Log for analysis
            if self.config.save_thinking_logs:
                self._thinking_logs.append(result)

            logger.info(
                f"Extended thinking complete: {thinking_tokens} thinking tokens, "
                f"{response_tokens} response tokens, {total_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Extended thinking error: {e}")

            # Fallback to regular response
            try:
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8000,
                    system=system,
                    messages=[{"role": "user", "content": full_prompt}]
                )

                return ThinkingResult(
                    thinking=f"[Extended thinking unavailable: {e}]",
                    response=response.content[0].text,
                    thinking_tokens=0,
                    response_tokens=response.usage.output_tokens,
                    total_time=time.time() - start_time,
                    model="claude-sonnet-4-20250514",
                    complexity_detected=complexity
                )
            except Exception as e2:
                return ThinkingResult(
                    thinking="",
                    response=f"Error: {e2}",
                    thinking_tokens=0,
                    response_tokens=0,
                    total_time=time.time() - start_time,
                    model="",
                    complexity_detected=complexity
                )

    async def stream_thinking(
        self,
        prompt: str,
        context: str = "",
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[Tuple[str, str]]:
        """
        Stream both thinking and response in real-time.

        Yields tuples of (type, content) where type is "thinking" or "response".
        This lets you show the AI's reasoning process as it happens!
        """
        client = await self._get_client()
        if not client:
            yield ("error", "Extended thinking requires ANTHROPIC_API_KEY")
            return

        budget = self.get_thinking_budget(prompt)

        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\n---\n\nTask:\n{prompt}"

        system = system_prompt or """You are an expert AI assistant. Think through
complex problems step-by-step before providing your response."""

        try:
            async with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": budget
                },
                system=system,
                messages=[{"role": "user", "content": full_prompt}]
            ) as stream:
                current_type = None

                async for event in stream:
                    if hasattr(event, 'type'):
                        if event.type == 'content_block_start':
                            if hasattr(event, 'content_block'):
                                block_type = event.content_block.type
                                if block_type == 'thinking':
                                    current_type = 'thinking'
                                    yield ('thinking_start', '')
                                elif block_type == 'text':
                                    current_type = 'response'
                                    yield ('response_start', '')

                        elif event.type == 'content_block_delta':
                            if hasattr(event, 'delta'):
                                if hasattr(event.delta, 'thinking'):
                                    yield ('thinking', event.delta.thinking)
                                elif hasattr(event.delta, 'text'):
                                    yield ('response', event.delta.text)

                        elif event.type == 'content_block_stop':
                            if current_type:
                                yield (f'{current_type}_end', '')

        except Exception as e:
            logger.error(f"Streaming thinking error: {e}")
            yield ('error', str(e))

    def get_thinking_stats(self) -> Dict:
        """Get statistics on thinking usage"""
        if not self._thinking_logs:
            return {"total_sessions": 0}

        total_thinking_tokens = sum(r.thinking_tokens for r in self._thinking_logs)
        total_response_tokens = sum(r.response_tokens for r in self._thinking_logs)
        avg_time = sum(r.total_time for r in self._thinking_logs) / len(self._thinking_logs)

        complexity_counts = {}
        for r in self._thinking_logs:
            complexity_counts[r.complexity_detected] = complexity_counts.get(r.complexity_detected, 0) + 1

        return {
            "total_sessions": len(self._thinking_logs),
            "total_thinking_tokens": total_thinking_tokens,
            "total_response_tokens": total_response_tokens,
            "avg_session_time": round(avg_time, 2),
            "complexity_distribution": complexity_counts,
            "thinking_efficiency": round(total_thinking_tokens / max(total_response_tokens, 1), 2)
        }

    def clear_logs(self):
        """Clear thinking logs"""
        self._thinking_logs = []


# Convenience function for quick extended thinking
async def deep_think(prompt: str, context: str = "") -> ThinkingResult:
    """Quick access to extended thinking for complex problems"""
    engine = ExtendedThinkingEngine()
    return await engine.think_and_respond(prompt, context)
