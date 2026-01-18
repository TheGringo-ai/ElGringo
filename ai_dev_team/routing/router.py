"""
Task Router - Intelligent task classification and agent selection
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..agents import ModelType

logger = logging.getLogger(__name__)


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


class TaskRouter:
    """
    Intelligent task router that classifies tasks and selects optimal agents.

    Uses keyword matching and patterns to determine the best agents
    and collaboration mode for each task.
    """

    def __init__(self):
        self.classification_patterns = self._build_patterns()
        self.agent_strengths = self._build_agent_strengths()

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
                "keywords": ["design", "creative", "ui", "ux", "interface", "mockup", "prototype", "brainstorm"],
                "patterns": [
                    r"\b(design|create)\s+(ui|ux|interface|mockup)",
                    r"\buser\s+(experience|interface)",
                ],
                "weight": 1.0,
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
            "claude-analyst": {
                "model_type": ModelType.CLAUDE,
                "strengths": [TaskType.ANALYSIS, TaskType.ARCHITECTURE, TaskType.RESEARCH],
                "capabilities": ["analysis", "reasoning", "planning", "architecture"],
                "performance_weight": 1.2,
            },
            "chatgpt-coder": {
                "model_type": ModelType.CHATGPT,
                "strengths": [TaskType.CODING, TaskType.DEBUGGING, TaskType.TESTING],
                "capabilities": ["coding", "debugging", "testing", "documentation"],
                "performance_weight": 1.1,
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
        }

    def classify(
        self,
        prompt: str,
        context: str = "",
    ) -> TaskClassification:
        """
        Classify a task and recommend agents.

        Args:
            prompt: The task prompt
            context: Additional context

        Returns:
            TaskClassification with recommendations
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

        # Recommend agents
        recommended_agents = self._recommend_agents(primary_type, secondary_types)

        # Recommend collaboration mode
        recommended_mode = self._recommend_mode(primary_type, complexity)

        return TaskClassification(
            primary_type=primary_type,
            secondary_types=secondary_types,
            confidence=min(primary_score, 1.0),
            complexity=complexity,
            recommended_agents=recommended_agents,
            recommended_mode=recommended_mode,
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
        """Assess task complexity"""
        high_indicators = ["complex", "advanced", "comprehensive", "full system", "entire", "sophisticated"]
        low_indicators = ["simple", "basic", "quick", "small", "minor", "easy"]

        if any(ind in text for ind in high_indicators):
            return "high"
        if any(ind in text for ind in low_indicators):
            return "low"

        # Word count as secondary indicator
        word_count = len(text.split())
        if word_count > 50:
            return "high"
        if word_count < 15:
            return "low"

        return "medium"

    def _recommend_agents(
        self,
        primary_type: TaskType,
        secondary_types: List[TaskType],
    ) -> List[str]:
        """Recommend agents for the task"""
        scored_agents = []

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

            if score > 0:
                scored_agents.append((agent_name, score))

        # Sort by score
        scored_agents.sort(key=lambda x: x[1], reverse=True)

        # Return top agents
        return [name for name, _ in scored_agents[:4]]

    def _recommend_mode(self, primary_type: TaskType, complexity: str) -> str:
        """Recommend collaboration mode"""
        # High complexity = consensus
        if complexity == "high":
            return "consensus"

        # Debugging and security = sequential (build on findings)
        if primary_type in [TaskType.DEBUGGING, TaskType.SECURITY]:
            return "sequential"

        # Creative = parallel (diverse ideas)
        if primary_type in [TaskType.CREATIVE, TaskType.RESEARCH]:
            return "parallel"

        # Default based on complexity
        if complexity == "low":
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
