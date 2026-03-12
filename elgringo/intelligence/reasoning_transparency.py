"""
Reasoning Transparency — Show the "why" behind multi-agent decisions
====================================================================

Makes the agent collaboration process visible to users by:
1. Extracting each agent's reasoning chain
2. Identifying points of agreement and disagreement
3. Explaining how the final answer was synthesized
4. Showing confidence attribution per agent
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReasoningStep:
    step_number: int
    description: str
    confidence: float = 0.0


@dataclass
class AgentReasoning:
    agent_name: str
    model: str
    position_summary: str
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    key_recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    response_time: float = 0.0
    contribution_weight: float = 0.0


@dataclass
class DisagreementPoint:
    topic: str
    positions: Dict[str, str]
    resolution: str
    resolution_method: str


@dataclass
class TransparencyReport:
    task_id: str
    prompt_summary: str

    agent_reasoning: List[AgentReasoning] = field(default_factory=list)
    agreement_points: List[str] = field(default_factory=list)
    disagreement_points: List[DisagreementPoint] = field(default_factory=list)
    consensus_level: float = 0.0
    consensus_description: str = ""

    primary_contributor: str = ""
    contribution_breakdown: Dict[str, float] = field(default_factory=dict)
    synthesis_explanation: str = ""

    decision_factors: List[str] = field(default_factory=list)
    alternative_approaches: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "prompt_summary": self.prompt_summary,
            "agent_reasoning": [
                {
                    "agent": ar.agent_name,
                    "model": ar.model,
                    "position": ar.position_summary,
                    "key_recommendations": ar.key_recommendations[:5],
                    "confidence": round(ar.confidence, 2),
                    "contribution_weight": round(ar.contribution_weight, 2),
                    "reasoning_steps": [
                        {"step": s.step_number, "description": s.description}
                        for s in ar.reasoning_steps[:5]
                    ],
                }
                for ar in self.agent_reasoning
            ],
            "consensus": {
                "level": round(self.consensus_level, 2),
                "description": self.consensus_description,
                "agreements": self.agreement_points[:5],
                "disagreements": [
                    {
                        "topic": d.topic,
                        "positions": d.positions,
                        "resolution": d.resolution,
                        "method": d.resolution_method,
                    }
                    for d in self.disagreement_points[:5]
                ],
            },
            "attribution": {
                "primary_contributor": self.primary_contributor,
                "breakdown": {k: round(v, 2) for k, v in self.contribution_breakdown.items()},
                "synthesis_explanation": self.synthesis_explanation,
            },
            "decision_factors": self.decision_factors[:5],
            "alternative_approaches": self.alternative_approaches[:3],
        }

    def to_readable(self) -> str:
        lines = [f"## Reasoning Transparency Report", f"**Task:** {self.prompt_summary}\n"]
        lines.append("### Agent Perspectives")
        for ar in self.agent_reasoning:
            emoji = "+" if ar.confidence > 0.8 else "~" if ar.confidence > 0.5 else "-"
            lines.append(f"\n**{ar.agent_name}** ({ar.model}) — [{emoji}] {ar.confidence:.0%} confident")
            lines.append(f"> {ar.position_summary}")
            for rec in ar.key_recommendations[:3]:
                lines.append(f"  - {rec}")
            lines.append(f"  _Influence on final answer: {ar.contribution_weight:.0%}_")

        lines.append(f"\n### Consensus: {self.consensus_description}")
        if self.agreement_points:
            lines.append("\n**Agreements:**")
            for a in self.agreement_points[:5]:
                lines.append(f"  + {a}")
        if self.disagreement_points:
            lines.append("\n**Disagreements:**")
            for d in self.disagreement_points[:3]:
                lines.append(f"  x **{d.topic}**")
                for agent, pos in d.positions.items():
                    lines.append(f"    - {agent}: {pos}")
                lines.append(f"    -> Resolved by: {d.resolution_method} — {d.resolution}")

        lines.append(f"\n### How the Final Answer Was Built")
        lines.append(self.synthesis_explanation)
        return "\n".join(lines)


class ReasoningTransparency:
    """Extracts reasoning transparency from multi-agent collaborations."""

    GENERIC_WORDS = {
        "this", "that", "with", "from", "have", "been", "will", "they",
        "their", "would", "could", "should", "about", "which", "these",
        "there", "what", "when", "your", "each", "also", "more", "some",
        "other", "into", "than", "then", "here", "using", "used", "code",
    }

    def analyze(
        self,
        responses: list,
        prompt: str,
        final_answer: str,
        task_type: str = "general",
        task_id: str = "",
        expertise_weights: Optional[Dict[str, float]] = None,
    ) -> TransparencyReport:
        successful = [r for r in responses if r.success]
        report = TransparencyReport(
            task_id=task_id,
            prompt_summary=prompt[:200] + ("..." if len(prompt) > 200 else ""),
        )
        if not successful:
            report.consensus_description = "No successful responses to analyze"
            return report

        for r in successful:
            weight = (expertise_weights or {}).get(r.agent_name, 1.0)
            report.agent_reasoning.append(self._extract_reasoning(r, weight))

        total_weight = sum(ar.contribution_weight for ar in report.agent_reasoning)
        if total_weight > 0:
            for ar in report.agent_reasoning:
                ar.contribution_weight /= total_weight

        if report.agent_reasoning:
            primary = max(report.agent_reasoning, key=lambda ar: ar.contribution_weight)
            report.primary_contributor = primary.agent_name
            report.contribution_breakdown = {
                ar.agent_name: ar.contribution_weight for ar in report.agent_reasoning
            }

        self._analyze_consensus(report, successful)
        report.synthesis_explanation = self._build_synthesis_explanation(report)
        report.decision_factors = self._extract_decision_factors(successful, task_type)
        report.alternative_approaches = self._extract_alternatives(successful, final_answer)
        return report

    def _extract_reasoning(self, response, expertise_weight):
        content = response.content or ""
        model = response.metadata.get("model", response.model_type.value) if response.metadata else response.model_type.value

        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
        position = re.sub(r'[#*`]', '', paragraphs[0][:300]).strip() if paragraphs else content[:300]

        steps = []
        for pattern in [r'(\d+)[\.\)]\s+(.+?)(?=\n\d+[\.\)]|\n\n|$)', r'[-*]\s+\*\*(.+?)\*\*[:\s]*(.+?)(?=\n[-*]|\n\n|$)']:
            for i, m in enumerate(re.findall(pattern, content, re.DOTALL), 1):
                steps.append(ReasoningStep(i, re.sub(r'[#*`]', '', m[-1].strip()[:200]).strip(), response.confidence))
                if i >= 5:
                    break
            if steps:
                break

        if not steps and len(paragraphs) > 1:
            for i, p in enumerate(paragraphs[:3], 1):
                steps.append(ReasoningStep(i, re.sub(r'[#*`]', '', p[:200]).strip(), response.confidence))

        recommendations = []
        for pattern in [r'(?:recommend|suggest|should|best practice)[:\s]+(.+?)(?:\n|$)', r'[-*]\s+(.+?)(?:\n|$)']:
            for rec in re.findall(pattern, content, re.I)[:5]:
                if len(rec.strip()) > 20:
                    recommendations.append(rec.strip()[:150])
            if recommendations:
                break

        return AgentReasoning(
            agent_name=response.agent_name, model=model,
            position_summary=position,
            reasoning_steps=steps[:5],
            key_recommendations=recommendations[:5],
            confidence=response.confidence,
            response_time=response.response_time,
            contribution_weight=response.confidence * expertise_weight,
        )

    def _analyze_consensus(self, report, responses):
        if len(responses) < 2:
            report.consensus_level = 1.0
            report.consensus_description = f"Single agent response from {responses[0].agent_name}"
            return

        response_terms = {}
        for r in responses:
            text = re.sub(r'```.*?```', '', r.content or '', flags=re.DOTALL)
            response_terms[r.agent_name] = set(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{3,}', text.lower()))

        all_terms = list(response_terms.values())
        common = set.intersection(*all_terms) - self.GENERIC_WORDS if len(all_terms) > 1 else set()

        if common:
            top = sorted(common, key=len, reverse=True)[:5]
            report.agreement_points.append(f"All agents discuss: {', '.join(top[:3])}")

        for agent_name, terms in response_terms.items():
            others = set.union(*(v for k, v in response_terms.items() if k != agent_name)) if len(response_terms) > 1 else set()
            unique = terms - common - self.GENERIC_WORDS - others
            if unique:
                top_u = sorted(unique, key=len, reverse=True)[:3]
                report.agreement_points.append(f"{agent_name} uniquely emphasizes: {', '.join(top_u)}")

        similarities = []
        names = list(response_terms.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                t1, t2 = response_terms[names[i]], response_terms[names[j]]
                union = t1 | t2
                jaccard = len(t1 & t2) / len(union) if union else 0.5
                similarities.append(jaccard)
                if jaccard < 0.25:
                    u_i = sorted(t1 - t2 - self.GENERIC_WORDS, key=len, reverse=True)[:2]
                    u_j = sorted(t2 - t1 - self.GENERIC_WORDS, key=len, reverse=True)[:2]
                    if u_i and u_j:
                        report.disagreement_points.append(DisagreementPoint(
                            topic=f"Approach to {', '.join(u_i[:1])} vs {', '.join(u_j[:1])}",
                            positions={names[i]: f"Focuses on {', '.join(u_i)}", names[j]: f"Focuses on {', '.join(u_j)}"},
                            resolution="Final answer synthesizes both perspectives",
                            resolution_method="expertise_weighted",
                        ))

        avg_sim = sum(similarities) / len(similarities) if similarities else 0.5
        confidences = [r.confidence for r in responses]
        conf_spread = max(confidences) - min(confidences)
        report.consensus_level = 0.6 * avg_sim + 0.4 * max(0, 1 - conf_spread * 2)

        if report.consensus_level > 0.8:
            report.consensus_description = "Strong consensus — agents broadly agree"
        elif report.consensus_level > 0.6:
            report.consensus_description = "Moderate consensus — agree on direction, differ on specifics"
        elif report.consensus_level > 0.4:
            report.consensus_description = "Partial consensus — different approaches worth considering"
        else:
            report.consensus_description = "Low consensus — significantly different solutions proposed"

    def _build_synthesis_explanation(self, report):
        if len(report.agent_reasoning) == 1:
            ar = report.agent_reasoning[0]
            return f"Response from {ar.agent_name} ({ar.model}) with {ar.confidence:.0%} confidence."
        parts = [f"Synthesized from {len(report.agent_reasoning)} agent perspectives."]
        if report.primary_contributor:
            w = report.contribution_breakdown.get(report.primary_contributor, 0)
            parts.append(f"Primary contributor: {report.primary_contributor} ({w:.0%} influence).")
        if report.consensus_level > 0.7:
            parts.append("High consensus made synthesis straightforward.")
        elif report.disagreement_points:
            topics = [d.topic for d in report.disagreement_points[:2]]
            parts.append(f"Resolved disagreements on: {'; '.join(topics)}.")
        return " ".join(parts)

    def _extract_decision_factors(self, responses, task_type):
        factors = [f"Task type: {task_type}", f"Agents consulted: {len(responses)}"]
        avg = sum(r.confidence for r in responses) / len(responses)
        factors.append(f"Average confidence: {avg:.0%}")
        if any(re.search(r'```', r.content or '') for r in responses):
            factors.append("Code implementations provided")
        return factors

    def _extract_alternatives(self, responses, final_answer):
        alternatives = []
        for r in responses:
            for match in re.findall(r'(?:alternativ|another approach|you could also)[:\s]+(.+?)(?:\n\n|$)', r.content or '', re.I | re.DOTALL)[:2]:
                alt = match.strip()[:200]
                if alt and alt not in final_answer[:500]:
                    alternatives.append(f"{r.agent_name}: {alt}")
        return alternatives[:3]


_transparency: Optional[ReasoningTransparency] = None

def get_reasoning_transparency() -> ReasoningTransparency:
    global _transparency
    if _transparency is None:
        _transparency = ReasoningTransparency()
    return _transparency
