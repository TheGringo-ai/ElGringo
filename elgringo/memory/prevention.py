"""
Mistake Prevention System - Proactive issue detection and prevention
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .system import MemorySystem, MistakeRecord

logger = logging.getLogger(__name__)


@dataclass
class PreventionGuidance:
    """Guidance to prevent a potential mistake"""
    warning_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    message: str
    similar_mistakes: List[MistakeRecord]
    prevention_steps: List[str]
    risk_score: float


class MistakePrevention:
    """
    Proactive mistake prevention system.

    Analyzes current context against historical mistake patterns
    to warn about potential issues before they occur.
    """

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.risk_threshold = 0.6

    async def analyze_context(
        self,
        context: Dict[str, Any],
        task_description: str = "",
    ) -> Optional[PreventionGuidance]:
        """
        Analyze current context for potential mistakes.

        Returns PreventionGuidance if risks are detected.
        """
        try:
            # Find similar past mistakes
            similar_mistakes = await self.memory.find_similar_mistakes(context)

            if not similar_mistakes:
                return None

            # Calculate risk score
            risk_score = self._calculate_risk(similar_mistakes, context)

            if risk_score < self.risk_threshold:
                return None

            # Determine warning level
            warning_level = self._get_warning_level(risk_score)

            # Collect prevention steps
            prevention_steps = []
            for mistake in similar_mistakes[:3]:
                if mistake.prevention_strategy:
                    prevention_steps.append(mistake.prevention_strategy)
                if mistake.resolution:
                    prevention_steps.append(f"Previous fix: {mistake.resolution}")

            message = self._generate_warning_message(similar_mistakes, task_description)

            return PreventionGuidance(
                warning_level=warning_level,
                message=message,
                similar_mistakes=similar_mistakes[:3],
                prevention_steps=list(set(prevention_steps)),
                risk_score=risk_score,
            )

        except Exception as e:
            logger.error(f"Error in mistake prevention analysis: {e}")
            return None

    def _calculate_risk(
        self,
        similar_mistakes: List[MistakeRecord],
        context: Dict[str, Any],
    ) -> float:
        """Calculate risk score based on similar mistakes"""
        if not similar_mistakes:
            return 0.0

        total_risk = 0.0
        severity_weights = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3,
        }

        for mistake in similar_mistakes:
            weight = severity_weights.get(mistake.severity, 0.5)
            total_risk += weight

        # Normalize
        max_possible = len(similar_mistakes) * 1.0
        return min(total_risk / max_possible, 1.0)

    def _get_warning_level(self, risk_score: float) -> str:
        """Determine warning level from risk score"""
        if risk_score >= 0.9:
            return "CRITICAL"
        elif risk_score >= 0.75:
            return "HIGH"
        elif risk_score >= 0.6:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_warning_message(
        self,
        mistakes: List[MistakeRecord],
        task_description: str,
    ) -> str:
        """Generate human-readable warning message"""
        if not mistakes:
            return "No specific warnings"

        mistake_types = set(m.mistake_type for m in mistakes)
        types_str = ", ".join(mistake_types)

        return (
            f"POTENTIAL ISSUE DETECTED: Similar {types_str} mistakes have occurred before. "
            f"Found {len(mistakes)} related past mistakes. Review prevention steps below."
        )

    async def get_prevention_context(
        self,
        task_type: str,
        project: str = "default",
    ) -> str:
        """
        Get prevention context to include in AI prompts.

        This helps the AI team avoid known pitfalls.
        """
        # Get relevant mistakes for this task type
        context = {"task_type": task_type, "project": project}
        mistakes = await self.memory.find_similar_mistakes(context, limit=5)

        if not mistakes:
            return ""

        prevention_context = "IMPORTANT - KNOWN ISSUES TO AVOID:\n"

        for i, mistake in enumerate(mistakes, 1):
            prevention_context += f"\n{i}. {mistake.description}"
            if mistake.prevention_strategy:
                prevention_context += f"\n   Prevention: {mistake.prevention_strategy}"

        return prevention_context
