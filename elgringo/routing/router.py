"""
Task Router - Intelligent task classification and agent selection
================================================================

Smart routing engine that replaces manual team selection.
Automatically picks the right agents, mode, and persona for every task.

Signals used:
  1. Keyword + regex pattern matching → task type
  2. Multi-signal complexity assessment → low/medium/high
  3. Cost-aware agent ranking → prefer free agents for simple tasks
  4. Feedback-informed weights → learn from past outcomes
  5. Dynamic persona injection → shape agent behavior per-request
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..agents import ModelType
from .performance_tracker import get_performance_tracker

logger = logging.getLogger(__name__)


# ── Dynamic Persona Prompts ─────────────────────────────────────────
# Injected into agent system prompts based on task type + complexity.
# Replaces the old "teams" feature — router shapes behavior automatically.

PERSONA_PROMPTS: Dict[str, Dict[str, str]] = {
    "security": {
        "low": "Check for common security issues. Flag anything obvious.",
        "medium": (
            "Think like a penetration tester. Check for OWASP Top 10 vulnerabilities, "
            "injection attacks, auth bypasses, and data exposure. Be thorough."
        ),
        "high": (
            "You are a senior security auditor. Systematically evaluate: authentication, "
            "authorization, input validation, cryptography, session management, error handling, "
            "and compliance. Challenge every assumption. Assume the attacker is sophisticated."
        ),
    },
    "architecture": {
        "low": "Suggest a clean, simple design. Don't over-engineer.",
        "medium": (
            "Evaluate trade-offs between approaches. Consider scalability, maintainability, "
            "and operational complexity. Justify your recommendations."
        ),
        "high": (
            "You are a principal architect. Challenge assumptions. Consider failure modes, "
            "scaling bottlenecks, data consistency, deployment complexity, and migration paths. "
            "Present multiple options with explicit trade-offs. Think 2 years ahead."
        ),
    },
    "debugging": {
        "low": "Find the bug and suggest a fix. Keep it simple.",
        "medium": (
            "Systematically analyze the issue. Consider: race conditions, state corruption, "
            "edge cases, environment differences. Trace the root cause, don't just fix symptoms."
        ),
        "high": (
            "Deep investigation mode. Consider: concurrency issues, memory leaks, cascading "
            "failures, environment-specific behavior, and interaction effects between components. "
            "Provide a root cause analysis with evidence."
        ),
    },
    "coding": {
        "low": "Write clean, working code. Keep it simple.",
        "medium": (
            "Write production-quality code. Handle edge cases, add input validation where needed, "
            "and follow the project's existing patterns. No over-engineering."
        ),
        "high": (
            "Write battle-tested code. Consider: error handling, performance implications, "
            "backward compatibility, testability, and operational concerns. "
            "The code should be ready for production traffic."
        ),
    },
    "creative": {
        "low": "Be creative but practical. One good idea is better than ten mediocre ones.",
        "medium": (
            "Explore multiple creative directions. Consider user experience, visual hierarchy, "
            "accessibility, and modern design patterns. Be bold but grounded."
        ),
        "high": (
            "Push creative boundaries. Think about brand differentiation, emotional impact, "
            "micro-interactions, and delight. Reference best-in-class examples. "
            "Balance innovation with usability."
        ),
    },
    "testing": {
        "low": "Write clear, focused tests for the happy path and one edge case.",
        "medium": (
            "Write comprehensive tests. Cover: happy path, edge cases, error conditions, "
            "boundary values. Use descriptive test names that document behavior."
        ),
        "high": (
            "Design a thorough test strategy. Cover: unit, integration, and contract tests. "
            "Consider: race conditions, resource cleanup, flaky test prevention, "
            "and test isolation. Tests should catch regressions, not just verify current behavior."
        ),
    },
}

# Agents that cost $0 to run (local inference)
FREE_AGENTS = {"qwen-coder", "qwen-general", "ollama-local", "local-llama3", "local-qwen-coder-7b"}


class TaskType(Enum):
    """Types of development tasks"""
    CODING = "coding"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    DEBUGGING = "debugging"
    ARCHITECTURE = "architecture"
    OPTIMIZATION = "optimization"
    RESEARCH = "research"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    SECURITY = "security"
    UI_UX = "ui_ux"


@dataclass
class TaskClassification:
    """Result of task classification"""
    primary_type: TaskType
    secondary_types: List[TaskType]
    confidence: float
    complexity: str  # "low", "medium", "high"
    recommended_agents: List[str]
    recommended_mode: str  # "parallel", "sequential", "consensus"
    persona_prompt: str = ""  # Injected into agent system prompts
    cost_tier: str = "standard"  # "free", "standard", "premium"


class TaskRouter:
    """
    Intelligent task router that classifies tasks and selects optimal agents.

    Uses keyword matching and patterns to determine the best agents
    and collaboration mode for each task.
    """

    def __init__(self):
        self.classification_patterns = self._build_patterns()
        self.agent_strengths = self._build_agent_strengths()
        self._benchmark_data = self._load_benchmark_data()

    def _load_benchmark_data(self) -> Dict[str, Dict[str, float]]:
        """Load benchmark routing table if it exists."""
        try:
            from .benchmark import STORAGE_DIR
            import json
            table_path = STORAGE_DIR / "routing_table.json"
            if table_path.exists():
                table = json.loads(table_path.read_text())
                # Convert to {task_type: {agent_name: score}}
                result = {}
                for task_type, data in table.items():
                    if "rankings" in data:
                        result[task_type] = data["rankings"]
                return result
        except Exception:
            pass
        return {}

    def _build_patterns(self) -> Dict[TaskType, Dict]:
        """Build classification patterns for each task type"""
        return {
            TaskType.CODING: {
                "keywords": ["code", "implement", "function", "class", "method", "api", "endpoint", "script", "build"],
                "patterns": [
                    r"\b(write|create|implement|code|build|develop)\s+(a\s+)?(function|class|method|api|script)",
                    r"\b(add|create|implement)\s+(feature|functionality)",
                ],
                "weight": 1.0,
            },
            TaskType.ANALYSIS: {
                "keywords": ["analyze", "examine", "investigate", "review", "assess", "evaluate", "understand", "explain"],
                "patterns": [
                    r"\b(analyze|examine|investigate|review|assess|evaluate)\s+",
                    r"\bwhat\s+(is|are|does)\b",
                    r"\bhow\s+(does|can|should)\b",
                ],
                "weight": 1.0,
            },
            TaskType.CREATIVE: {
                "keywords": ["design", "creative", "ui", "ux", "interface", "mockup", "prototype", "brainstorm",
                            "beautiful", "stunning", "elegant", "modern", "landing", "website", "webpage", "visual"],
                "patterns": [
                    r"\b(design|create)\s+(ui|ux|interface|mockup)",
                    r"\buser\s+(experience|interface)",
                    r"\b(beautiful|stunning|elegant|modern)\s+",
                    r"\blanding\s+page\b",
                    r"\b(website|webpage)\s+(design|layout)",
                ],
                "weight": 1.1,  # Slightly higher weight for creative
            },
            TaskType.DEBUGGING: {
                "keywords": ["debug", "fix", "error", "bug", "issue", "problem", "troubleshoot", "not working"],
                "patterns": [
                    r"\b(fix|debug|resolve|solve|troubleshoot)\s+",
                    r"\b(error|bug|issue|problem)\b",
                ],
                "weight": 1.2,  # Higher weight for debugging
            },
            TaskType.ARCHITECTURE: {
                "keywords": ["architecture", "structure", "design", "pattern", "framework", "system"],
                "patterns": [
                    r"\b(architecture|structure|design)\s+(pattern|framework|system)",
                    r"\bsystem\s+design\b",
                ],
                "weight": 1.0,
            },
            TaskType.OPTIMIZATION: {
                "keywords": ["optimize", "performance", "improve", "faster", "efficient", "scale"],
                "patterns": [
                    r"\b(optimize|improve|enhance)\s+(performance|speed|efficiency)",
                    r"\bmake\s+(faster|more\s+efficient)",
                ],
                "weight": 1.0,
            },
            TaskType.SECURITY: {
                "keywords": ["security", "authentication", "authorization", "encrypt", "vulnerability", "secure"],
                "patterns": [
                    r"\b(security|authentication|authorization|encryption)\b",
                    r"\bsecure\s+",
                ],
                "weight": 1.1,
            },
            TaskType.TESTING: {
                "keywords": ["test", "testing", "unit test", "integration", "validate", "qa"],
                "patterns": [
                    r"\b(test|testing|validate)\s+",
                    r"\b(unit|integration)\s+test\b",
                ],
                "weight": 1.0,
            },
            TaskType.DOCUMENTATION: {
                "keywords": ["document", "documentation", "readme", "comments", "explain"],
                "patterns": [
                    r"\b(document|documentation|readme)\b",
                    r"\bwrite\s+(documentation|docs)\b",
                ],
                "weight": 0.9,
            },
            TaskType.RESEARCH: {
                "keywords": ["research", "find", "search", "look up", "investigate"],
                "patterns": [
                    r"\b(research|find|search|look\s+up)\b",
                ],
                "weight": 0.9,
            },
        }

    def _build_agent_strengths(self) -> Dict[str, Dict]:
        """Build agent capability mappings"""
        return {
            "chatgpt-coder": {
                "model_type": ModelType.CHATGPT,
                "strengths": [TaskType.CODING, TaskType.DEBUGGING, TaskType.TESTING, TaskType.ANALYSIS, TaskType.ARCHITECTURE],
                "capabilities": ["coding", "debugging", "testing", "documentation", "analysis", "architecture"],
                "performance_weight": 1.3,
            },
            "claude-analyst": {
                "model_type": ModelType.CLAUDE,
                "strengths": [TaskType.ANALYSIS, TaskType.ARCHITECTURE, TaskType.RESEARCH],
                "capabilities": ["analysis", "reasoning", "planning", "architecture"],
                "performance_weight": 1.0,
            },
            "gemini-creative": {
                "model_type": ModelType.GEMINI,
                "strengths": [TaskType.CREATIVE, TaskType.UI_UX, TaskType.DOCUMENTATION],
                "capabilities": ["creativity", "design", "innovation", "ui-ux"],
                "performance_weight": 1.0,
            },
            "grok-reasoner": {
                "model_type": ModelType.GROK,
                "strengths": [TaskType.ANALYSIS, TaskType.ARCHITECTURE, TaskType.RESEARCH],
                "capabilities": ["reasoning", "analysis", "strategy"],
                "performance_weight": 1.1,
            },
            "grok-coder": {
                "model_type": ModelType.GROK,
                "strengths": [TaskType.CODING, TaskType.OPTIMIZATION, TaskType.DEBUGGING],
                "capabilities": ["fast-coding", "optimization", "debugging"],
                "performance_weight": 1.3,
            },
            # Llama Cloud Agents (via Groq, Together, Fireworks)
            "llama-3-3-70b-groq": {
                "model_type": ModelType.LOCAL,
                "strengths": [TaskType.CODING, TaskType.ANALYSIS, TaskType.DEBUGGING],
                "capabilities": ["fast-coding", "reasoning", "analysis", "multilingual"],
                "performance_weight": 1.2,
            },
            "llama-3-3-70b-together": {
                "model_type": ModelType.LOCAL,
                "strengths": [TaskType.CODING, TaskType.ANALYSIS, TaskType.CREATIVE],
                "capabilities": ["coding", "reasoning", "large-context"],
                "performance_weight": 1.15,
            },
            "llama-3-1-8b-together": {
                "model_type": ModelType.LOCAL,
                "strengths": [TaskType.CODING, TaskType.DOCUMENTATION],
                "capabilities": ["fast-response", "simple-tasks"],
                "performance_weight": 0.9,
            },
            # Local Ollama Agents
            "ollama-local": {
                "model_type": ModelType.LOCAL,
                "strengths": [TaskType.CODING, TaskType.DEBUGGING],
                "capabilities": ["offline", "privacy", "fast-simple"],
                "performance_weight": 0.85,
            },
            "local-llama3": {
                "model_type": ModelType.LOCAL,
                "strengths": [TaskType.CODING, TaskType.ANALYSIS],
                "capabilities": ["offline", "privacy", "general"],
                "performance_weight": 0.8,
            },
            "local-qwen-coder-7b": {
                "model_type": ModelType.LOCAL,
                "strengths": [TaskType.CODING, TaskType.DEBUGGING, TaskType.OPTIMIZATION],
                "capabilities": ["offline", "coding", "debugging"],
                "performance_weight": 0.9,
            },
            # Qwen Local Agents (Apple Silicon MLX - zero cost, fast)
            "qwen-coder": {
                "model_type": ModelType.LOCAL,
                "strengths": [TaskType.CODING, TaskType.DEBUGGING, TaskType.OPTIMIZATION, TaskType.TESTING],
                "capabilities": ["coding", "debugging", "refactoring", "architecture", "zero-cost", "offline"],
                "performance_weight": 1.3,
            },
            "qwen-general": {
                "model_type": ModelType.LOCAL,
                "strengths": [TaskType.ANALYSIS, TaskType.DOCUMENTATION, TaskType.RESEARCH, TaskType.CREATIVE],
                "capabilities": ["general", "reasoning", "writing", "analysis", "zero-cost", "offline"],
                "performance_weight": 1.1,
            },
        }

    def classify(
        self,
        prompt: str,
        context: str = "",
        prefer_free: Optional[bool] = None,
    ) -> TaskClassification:
        """
        Classify a task and recommend agents, mode, and persona.

        Args:
            prompt: The task prompt
            context: Additional context
            prefer_free: Force free agent preference (None = auto based on complexity)

        Returns:
            TaskClassification with full routing decision
        """
        text = f"{prompt} {context}".lower()

        # Score each task type
        type_scores = {}
        for task_type, config in self.classification_patterns.items():
            score = self._calculate_score(text, config)
            type_scores[task_type] = score

        # Sort by score
        sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)

        # Primary and secondary types
        primary_type = sorted_types[0][0]
        primary_score = sorted_types[0][1]

        secondary_types = [
            task_type for task_type, score in sorted_types[1:4]
            if score > 0.3 and (primary_score - score) < 0.5
        ]

        # Determine complexity
        complexity = self._assess_complexity(text)

        # Cost-aware agent selection
        use_free = prefer_free if prefer_free is not None else (complexity == "low")
        recommended_agents = self._recommend_agents(
            primary_type, secondary_types, prefer_free=use_free,
        )

        # Recommend collaboration mode
        recommended_mode = self._recommend_mode(primary_type, complexity)

        # Dynamic persona injection
        persona_prompt = self._get_persona_prompt(primary_type, complexity)

        # Cost tier
        cost_tier = "free" if use_free else ("premium" if complexity == "high" else "standard")

        return TaskClassification(
            primary_type=primary_type,
            secondary_types=secondary_types,
            confidence=min(primary_score, 1.0),
            complexity=complexity,
            recommended_agents=recommended_agents,
            recommended_mode=recommended_mode,
            persona_prompt=persona_prompt,
            cost_tier=cost_tier,
        )

    def _calculate_score(self, text: str, config: Dict) -> float:
        """Calculate score for a task type"""
        score = 0.0

        # Keyword matching
        keywords = config.get("keywords", [])
        keyword_matches = sum(1 for kw in keywords if kw in text)
        if keyword_matches:
            score += min(keyword_matches * 0.2, 0.6)

        # Pattern matching
        patterns = config.get("patterns", [])
        pattern_matches = sum(1 for p in patterns if re.search(p, text))
        if pattern_matches:
            score += min(pattern_matches * 0.3, 0.4)

        # Apply weight
        score *= config.get("weight", 1.0)

        return max(score, 0.0)

    def _assess_complexity(self, text: str) -> str:
        """Assess task complexity using multiple signals."""
        high_indicators = [
            "complex", "advanced", "comprehensive", "full system", "entire",
            "sophisticated", "trade-off", "trade off", "scaling", "concurrent",
            "distributed", "microservice", "failure mode", "high availability",
            "fault toleran", "load balanc", "delivery guarantee", "consistency",
            "architecture design", "system design", "real-time", "realtime",
        ]
        low_indicators = ["simple", "basic", "quick", "small", "minor", "easy"]

        # Count high-complexity signals (multiple signals = definitely high)
        high_count = sum(1 for ind in high_indicators if ind in text)
        if high_count >= 2:
            return "high"

        if any(ind in text for ind in low_indicators):
            return "low"

        if high_count == 1:
            return "high"

        # Multiple requirements (commas, "and", bullet points) suggest complexity
        comma_count = text.count(",")
        and_count = len(re.findall(r"\band\b", text))
        requirement_signals = comma_count + and_count

        # Word count as secondary indicator
        word_count = len(text.split())
        if word_count > 50:
            return "high"
        if word_count > 30 and requirement_signals >= 4:
            return "high"
        if word_count < 15:
            return "low"

        return "medium"

    def _recommend_agents(
        self,
        primary_type: TaskType,
        secondary_types: List[TaskType],
        prefer_free: bool = False,
    ) -> List[str]:
        """Recommend agents for the task with cost-aware + feedback-informed ranking."""
        scored_agents = []
        feedback_adjustments = self._get_feedback_adjustments()

        for agent_name, config in self.agent_strengths.items():
            score = 0.0

            # Primary type match
            if primary_type in config["strengths"]:
                score += 0.6

            # Secondary type matches
            for sec_type in secondary_types:
                if sec_type in config["strengths"]:
                    score += 0.2

            # Apply performance weight
            score *= config["performance_weight"]

            # Feedback-informed adjustment: boost/penalize based on learned outcomes
            task_type_str = primary_type.value
            adjustment = feedback_adjustments.get(agent_name, {}).get(task_type_str, 0.0)
            score += adjustment

            # Cost-aware: boost free agents when prefer_free is set
            if prefer_free and agent_name in FREE_AGENTS:
                score += 0.3  # Significant boost for free agents on simple tasks
            elif not prefer_free and agent_name in FREE_AGENTS:
                score -= 0.1  # Slight penalty for complex tasks (prefer cloud quality)

            if score > 0:
                scored_agents.append((agent_name, score))

        # Sort by score
        scored_agents.sort(key=lambda x: x[1], reverse=True)

        # Return top agents
        return [name for name, _ in scored_agents[:4]]

    def _get_feedback_adjustments(self) -> Dict[str, Dict[str, float]]:
        """Load expertise adjustments from the feedback loop if available."""
        try:
            from ..intelligence.feedback_loop import get_feedback_loop
            loop = get_feedback_loop()
            return dict(loop._expertise_adjustments)
        except Exception:
            return {}

    def _get_persona_prompt(self, primary_type: TaskType, complexity: str) -> str:
        """Get dynamic persona prompt based on task type and complexity."""
        type_prompts = PERSONA_PROMPTS.get(primary_type.value, {})
        if type_prompts:
            return type_prompts.get(complexity, type_prompts.get("medium", ""))
        # Fallback: generic complexity-based prompt
        fallback = {
            "low": "Keep it simple and direct.",
            "medium": "Be thorough but practical.",
            "high": "Be rigorous. Challenge assumptions. Consider edge cases and failure modes.",
        }
        return fallback.get(complexity, "")

    def _recommend_mode(self, primary_type: TaskType, complexity: str) -> str:
        """Recommend collaboration mode based on task type and complexity."""
        # High complexity: real multi-agent collaboration
        if complexity == "high":
            if primary_type == TaskType.ARCHITECTURE:
                return "debate"  # Architecture benefits from opposing viewpoints
            if primary_type == TaskType.SECURITY:
                return "devils_advocate"  # Security needs adversarial thinking
            return "peer_review"  # Default high-complexity: agents review each other

        # Medium complexity: agents interact, not just answer independently
        if complexity == "medium":
            if primary_type in [TaskType.DEBUGGING, TaskType.SECURITY]:
                return "sequential"  # Build on findings
            if primary_type in [TaskType.CREATIVE, TaskType.RESEARCH]:
                return "brainstorming"  # Diverse ideas with cross-pollination
            return "parallel"  # Standard parallel with critique round

        # Low complexity: fast single-agent or simple parallel
        if primary_type in [TaskType.CREATIVE, TaskType.RESEARCH]:
            return "parallel"

        return "parallel"

    def get_agent_for_task(
        self,
        task_type: TaskType,
        available_agents: List[str],
    ) -> Optional[str]:
        """Get best single agent for a task type"""
        best_agent = None
        best_score = 0.0

        for agent_name in available_agents:
            if agent_name not in self.agent_strengths:
                continue

            config = self.agent_strengths[agent_name]
            if task_type in config["strengths"]:
                score = config["performance_weight"]
                if score > best_score:
                    best_score = score
                    best_agent = agent_name

        return best_agent

    def get_performance_enhanced_agents(
        self,
        task_type: TaskType,
        available_agents: List[str],
        domain: Optional[str] = None,
        prefer_fast: bool = False,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Get ranked agents using both static strengths and historical performance.

        Combines predefined agent strengths with learned performance data
        to make smarter routing decisions.

        Args:
            task_type: Type of task
            available_agents: List of available agent names
            domain: Optional domain for domain-specific routing
            prefer_fast: Whether to prioritize faster models

        Returns:
            List of (agent_name, combined_score, details) tuples
        """
        tracker = get_performance_tracker()
        task_type_str = task_type.value

        ranked_agents = []

        for agent_name in available_agents:
            # Static score from predefined strengths
            static_score = 0.5  # Default
            if agent_name in self.agent_strengths:
                config = self.agent_strengths[agent_name]
                if task_type in config["strengths"]:
                    static_score = 0.7 + (config["performance_weight"] - 1.0) * 0.3
                else:
                    static_score = 0.4

            # Performance-based score from tracker
            perf_score, _ = tracker.get_best_model(
                task_type=task_type_str,
                available_models=[agent_name],
                domain=domain,
                prefer_fast=prefer_fast,
            )
            # perf_score is 0.5 if no data, otherwise based on history

            # Benchmark score from standardized tests
            benchmark_score = 0.5  # Default neutral
            has_benchmark = False
            if self._benchmark_data and task_type_str in self._benchmark_data:
                if agent_name in self._benchmark_data[task_type_str]:
                    benchmark_score = self._benchmark_data[task_type_str][agent_name]
                    has_benchmark = True

            # Combine scores using available data
            model_rankings = tracker.get_model_ranking([agent_name], task_type_str)
            has_perf = model_rankings and model_rankings[0][2].get("status") != "no_data"

            if has_perf and has_benchmark:
                # All three signals: 25% static, 40% performance, 35% benchmark
                perf_val = model_rankings[0][1]
                combined_score = (static_score * 0.25) + (perf_val * 0.40) + (benchmark_score * 0.35)
            elif has_perf:
                # Static + performance only
                combined_score = (static_score * 0.4) + (model_rankings[0][1] * 0.6)
            elif has_benchmark:
                # Static + benchmark only
                combined_score = (static_score * 0.4) + (benchmark_score * 0.6)
            else:
                # Static only
                combined_score = static_score

            details = {
                "static_score": round(static_score, 3),
                "performance_score": round(model_rankings[0][1] if has_perf else 0.5, 3),
                "benchmark_score": round(benchmark_score, 3),
                "has_performance_data": has_perf,
                "has_benchmark_data": has_benchmark,
            }
            if has_perf:
                details.update(model_rankings[0][2])

            ranked_agents.append((agent_name, combined_score, details))

        # Sort by combined score descending
        ranked_agents.sort(key=lambda x: x[1], reverse=True)

        return ranked_agents

    def classify_with_performance(
        self,
        prompt: str,
        context: str = "",
        available_agents: Optional[List[str]] = None,
        domain: Optional[str] = None,
    ) -> TaskClassification:
        """
        Classify a task and recommend agents using performance data.

        Enhanced version of classify() that incorporates historical
        performance data into agent recommendations.
        """
        # First do standard classification
        classification = self.classify(prompt, context)

        # If we have available agents, re-rank using performance data
        if available_agents:
            ranked = self.get_performance_enhanced_agents(
                task_type=classification.primary_type,
                available_agents=available_agents,
                domain=domain,
            )
            # Update recommended agents based on performance
            classification.recommended_agents = [name for name, _, _ in ranked[:4]]

        return classification
