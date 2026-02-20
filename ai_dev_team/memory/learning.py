"""
Learning Engine - Continuous improvement from interactions
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .system import MemorySystem, MistakeType, OutcomeRating, tokenize

logger = logging.getLogger(__name__)


@dataclass
class LearningInsight:
    """An insight derived from learning analysis"""
    insight_type: str  # "pattern", "recommendation", "warning"
    description: str
    confidence: float
    source_interactions: int
    actionable_steps: List[str]


@dataclass
class AgentPerformanceAnalysis:
    """Analysis of agent performance"""
    agent_name: str
    total_tasks: int
    success_rate: float
    avg_confidence: float
    best_task_types: List[str]
    improvement_areas: List[str]


class LearningEngine:
    """
    Learning engine for continuous improvement.

    Analyzes patterns across interactions, mistakes, and solutions
    to provide insights and recommendations.
    """

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system

    async def analyze_performance(
        self,
        project: Optional[str] = None,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """Analyze overall performance and learning trends"""
        interactions = self.memory._interactions_cache

        if project:
            interactions = [i for i in interactions if i.project == project]

        if not interactions:
            return {"message": "No data available for analysis"}

        # Calculate metrics
        total = len(interactions)
        successful = sum(1 for i in interactions if i.success)
        avg_confidence = sum(i.confidence for i in interactions) / total
        avg_time = sum(i.total_time for i in interactions) / total

        # Agent performance
        agent_stats = self._analyze_agent_performance(interactions)

        # Common patterns
        patterns = self._identify_patterns(interactions)

        # Recommendations
        recommendations = self._generate_recommendations(
            interactions,
            self.memory._mistakes_cache,
            self.memory._solutions_cache,
        )

        return {
            "total_interactions": total,
            "success_rate": successful / total,
            "avg_confidence": avg_confidence,
            "avg_response_time": avg_time,
            "agent_performance": agent_stats,
            "patterns_identified": patterns,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _analyze_agent_performance(
        self,
        interactions: List,
    ) -> Dict[str, AgentPerformanceAnalysis]:
        """Analyze performance of each agent"""
        agent_data = {}

        for interaction in interactions:
            for response in interaction.responses:
                agent_name = response.get("agent", "unknown")
                if agent_name not in agent_data:
                    agent_data[agent_name] = {
                        "total": 0,
                        "successful": 0,
                        "confidence_sum": 0,
                    }

                agent_data[agent_name]["total"] += 1
                if response.get("success", False):
                    agent_data[agent_name]["successful"] += 1
                agent_data[agent_name]["confidence_sum"] += response.get("confidence", 0)

        result = {}
        for agent_name, data in agent_data.items():
            total = data["total"]
            result[agent_name] = AgentPerformanceAnalysis(
                agent_name=agent_name,
                total_tasks=total,
                success_rate=data["successful"] / max(total, 1),
                avg_confidence=data["confidence_sum"] / max(total, 1),
                best_task_types=[],  # Would need task type tracking
                improvement_areas=[],
            )

        return result

    def _identify_patterns(self, interactions: List) -> List[LearningInsight]:
        """Identify patterns from interactions"""
        patterns = []

        # Pattern: Common successful approaches
        successful = [i for i in interactions if i.success and i.confidence > 0.8]
        if len(successful) > 5:
            patterns.append(LearningInsight(
                insight_type="pattern",
                description=f"High-confidence successful pattern identified in {len(successful)} interactions",
                confidence=0.8,
                source_interactions=len(successful),
                actionable_steps=["Continue using similar approaches for best results"],
            ))

        # Pattern: Failure clusters
        failures = [i for i in interactions if not i.success]
        if len(failures) > 3:
            patterns.append(LearningInsight(
                insight_type="warning",
                description=f"Failure pattern detected in {len(failures)} interactions",
                confidence=0.7,
                source_interactions=len(failures),
                actionable_steps=["Review failed interactions for common causes"],
            ))

        return patterns

    def _generate_recommendations(
        self,
        interactions: List,
        mistakes: List,
        solutions: List,
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Based on success rate
        if interactions:
            success_rate = sum(1 for i in interactions if i.success) / len(interactions)
            if success_rate < 0.7:
                recommendations.append(
                    "Success rate below 70%. Consider using consensus mode for complex tasks."
                )

        # Based on mistakes
        if len(mistakes) > len(solutions):
            recommendations.append(
                "More mistakes than solutions captured. Focus on documenting successful patterns."
            )

        # Based on agent usage
        if interactions:
            agents_used = set()
            for i in interactions:
                agents_used.update(i.agents_used)
            if len(agents_used) < 3:
                recommendations.append(
                    "Limited agent diversity. Try using more AI models for better coverage."
                )

        if not recommendations:
            recommendations.append("Performance is healthy. Continue current practices.")

        return recommendations

    async def learn_from_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        project: str = "default",
    ) -> str:
        """
        Learn from an error by capturing it as a mistake pattern.

        Returns the mistake ID for reference.
        """
        # Determine mistake type from error
        error_str = str(error).lower()
        if "connection" in error_str or "timeout" in error_str:
            mistake_type = MistakeType.INTEGRATION_ISSUE
        elif "permission" in error_str or "auth" in error_str:
            mistake_type = MistakeType.SECURITY_VULNERABILITY
        elif "memory" in error_str or "performance" in error_str:
            mistake_type = MistakeType.PERFORMANCE_ISSUE
        else:
            mistake_type = MistakeType.CODE_ERROR

        mistake_id = await self.memory.capture_mistake(
            mistake_type=mistake_type,
            description=f"Error occurred: {str(error)}",
            context=context,
            severity="medium",
            project=project,
        )

        logger.info(f"Learned from error: {mistake_id}")
        return mistake_id

    async def learn_from_success(
        self,
        result,  # CollaborationResult
        problem_description: str,
        project: str = "default",
        extractor_agent=None,  # Optional AIAgent for intelligent extraction
    ) -> Optional[Dict[str, Any]]:
        """
        Learn from a successful interaction by extracting reusable patterns.

        If extractor_agent is provided, uses it to distill the actual lesson
        from the AI responses instead of blindly truncating.

        Returns dict with solution_id, solution_steps, best_practices, tags
        or empty string on skip.
        """
        if not result.success or result.confidence_score < 0.7:
            return ""

        # Quality gate: skip trivial prompts (< 4 tokens)
        prompt_tokens = tokenize(problem_description)
        if len(prompt_tokens) < 4:
            logger.debug(f"Skipping trivial prompt ({len(prompt_tokens)} tokens): {problem_description[:60]}")
            return ""

        # Dedup check: if a near-duplicate solution exists, bump its access instead
        for sol in self.memory._solutions_cache:
            existing_tokens = tokenize(sol.problem_pattern)
            if MemorySystem._jaccard_similarity(prompt_tokens, existing_tokens) >= 0.7:
                MemorySystem._bump_access(sol)
                logger.debug(f"Near-duplicate found, bumped access on {sol.solution_id}")
                return sol.solution_id

        # Gather raw agent responses
        raw_responses = []
        for response in result.agent_responses:
            if response.success and response.content and len(response.content) > 50:
                raw_responses.append(response.content[:1500])

        if not raw_responses:
            return ""

        # Use LLM extraction if an agent is available, otherwise fallback
        solution_steps = []
        best_practices = []
        tags = []

        if extractor_agent and raw_responses:
            extracted = await self._extract_patterns(
                extractor_agent, problem_description, raw_responses
            )
            if extracted:
                solution_steps = extracted.get("solution_steps", [])
                best_practices = extracted.get("best_practices", [])
                tags = extracted.get("tags", [])

        # Fallback: summarize first 100 chars per response
        if not solution_steps:
            for response in result.agent_responses:
                if response.success and response.content and len(response.content) > 50:
                    solution_steps.append(response.content[:150].strip())

        if not solution_steps:
            return ""

        solution_id = await self.memory.capture_solution(
            problem_pattern=problem_description[:300],
            solution_steps=solution_steps[:5],
            success_rate=result.confidence_score,
            project=project,
            best_practices=best_practices[:6],
            tags=tags[:5],
        )

        logger.info(f"Learned from success: {solution_id} ({len(best_practices)} best practices)")
        return {
            "solution_id": solution_id,
            "solution_steps": solution_steps[:5],
            "best_practices": best_practices[:6],
            "tags": tags[:5],
        }

    async def _extract_patterns(
        self,
        agent,
        problem: str,
        responses: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Use an LLM agent to extract reusable patterns from raw responses.

        Returns dict with solution_steps, best_practices, tags — or None on failure.
        """
        combined = "\n---\n".join(responses[:3])  # Cap at 3 responses

        extraction_prompt = (
            "Extract the reusable development patterns from this AI team interaction.\n\n"
            f"PROBLEM: {problem[:300]}\n\n"
            f"AI TEAM RESPONSES:\n{combined[:3000]}\n\n"
            "Return ONLY a JSON object with these fields:\n"
            '{\n'
            '  "solution_steps": ["step 1", "step 2", ...],  // 2-5 concise steps (under 100 chars each)\n'
            '  "best_practices": ["rule 1", "rule 2", ...],  // reusable rules/conventions (under 80 chars each)\n'
            '  "tags": ["tag1", "tag2", ...]  // 2-5 searchable tags\n'
            '}\n\n'
            "Focus on REUSABLE patterns — things another developer would need to know. "
            "Skip generic advice. Be specific about libraries, methods, and conventions used."
        )

        try:
            response = await agent.generate_response(extraction_prompt)
            if not response.success:
                return None

            # Parse JSON from response
            text = response.content.strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                # Validate structure
                steps = data.get("solution_steps", [])
                practices = data.get("best_practices", [])
                tags = data.get("tags", [])
                if steps or practices:
                    return {
                        "solution_steps": [s for s in steps if isinstance(s, str) and len(s) < 200][:5],
                        "best_practices": [p for p in practices if isinstance(p, str) and len(p) < 150][:6],
                        "tags": [t for t in tags if isinstance(t, str) and len(t) < 30][:5],
                    }
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Pattern extraction failed: {e}")

        return None

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of all learning data"""
        stats = self.memory.get_statistics()

        return {
            **stats,
            "learning_status": "active" if stats["total_interactions"] > 0 else "no_data",
            "mistake_prevention_ready": stats["total_mistakes"] > 0,
            "solution_patterns_available": stats["total_solutions"] > 0,
        }
