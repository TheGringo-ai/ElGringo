"""
Response Quality Scorer — Composite quality scoring for multi-agent responses
=============================================================================

Synthesizes agent confidence, agreement patterns, and response characteristics
into a single quality score. Feeds into routing optimization and user-facing
transparency.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class AgentPerspective:
    """An individual agent's contribution to a response"""
    agent_name: str
    confidence: float
    response_length: int
    has_code: bool
    has_reasoning: bool
    key_points: List[str] = field(default_factory=list)
    stance: str = ""


@dataclass
class QualityReport:
    """Comprehensive quality assessment of a collaboration result"""
    overall_score: float
    grade: str  # A, B, C, D, F

    confidence_score: float
    agreement_score: float
    completeness_score: float
    specificity_score: float

    perspectives: List[AgentPerspective] = field(default_factory=list)
    agreements: List[str] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    synthesis_method: str = ""

    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 3),
            "grade": self.grade,
            "scores": {
                "confidence": round(self.confidence_score, 3),
                "agreement": round(self.agreement_score, 3),
                "completeness": round(self.completeness_score, 3),
                "specificity": round(self.specificity_score, 3),
            },
            "perspectives": [
                {
                    "agent": p.agent_name,
                    "confidence": round(p.confidence, 2),
                    "stance": p.stance,
                    "key_points": p.key_points[:3],
                }
                for p in self.perspectives
            ],
            "agreements": self.agreements[:5],
            "disagreements": self.disagreements[:5],
            "synthesis_method": self.synthesis_method,
            "warnings": self.warnings[:5],
            "suggestions": self.suggestions[:3],
        }


class QualityScorer:
    """
    Scores quality of multi-agent collaboration results.

    Composite score from:
    1. Weighted confidence (agent expertise x self-reported confidence)
    2. Agreement level (shared key terms between responses)
    3. Completeness (does response address all parts of the task)
    4. Specificity (concrete code/steps vs vague advice)
    """

    WEIGHTS = {
        "confidence": 0.30,
        "agreement": 0.25,
        "completeness": 0.25,
        "specificity": 0.20,
    }

    GRADE_THRESHOLDS = [
        (0.90, "A"), (0.80, "B"), (0.65, "C"), (0.50, "D"), (0.0, "F"),
    ]

    STOPWORDS = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can",
        "had", "her", "was", "one", "our", "out", "has", "have", "from",
        "they", "been", "said", "each", "which", "their", "will", "other",
        "about", "many", "then", "them", "these", "some", "would", "make",
        "like", "into", "could", "time", "very", "when", "what", "your",
        "how", "that", "this", "with", "also", "use", "using", "used",
        "should", "here", "there", "where", "does", "more",
    }

    def score(
        self,
        responses: list,
        prompt: str,
        final_answer: str,
        task_type: str = "general",
        expertise_weights: Optional[Dict[str, float]] = None,
    ) -> QualityReport:
        """Score the quality of a collaboration result."""
        successful = [r for r in responses if r.success]
        if not successful:
            return QualityReport(
                overall_score=0.0, grade="F",
                confidence_score=0.0, agreement_score=0.0,
                completeness_score=0.0, specificity_score=0.0,
                warnings=["No successful agent responses"],
            )

        confidence_score = self._compute_confidence(successful, expertise_weights)
        agreement_score, agreements, disagreements = self._compute_agreement(successful)
        completeness_score = self._compute_completeness(final_answer, prompt)
        specificity_score = self._compute_specificity(final_answer, task_type)

        overall = (
            self.WEIGHTS["confidence"] * confidence_score
            + self.WEIGHTS["agreement"] * agreement_score
            + self.WEIGHTS["completeness"] * completeness_score
            + self.WEIGHTS["specificity"] * specificity_score
        )

        grade = "F"
        for threshold, g in self.GRADE_THRESHOLDS:
            if overall >= threshold:
                grade = g
                break

        perspectives = []
        for r in successful:
            content = r.content or ""
            perspectives.append(AgentPerspective(
                agent_name=r.agent_name,
                confidence=r.confidence,
                response_length=len(content),
                has_code=bool(re.search(r'```', content)),
                has_reasoning=bool(re.search(r'because|therefore|since|reason', content, re.I)),
                key_points=self._extract_key_points(content),
                stance=content[:150].replace("\n", " ").strip() + ("..." if len(content) > 150 else ""),
            ))

        if len(successful) == 1:
            synthesis_method = f"Single agent: {successful[0].agent_name}"
        elif agreement_score > 0.8:
            synthesis_method = "High consensus — merged best elements from all agents"
        elif agreement_score > 0.5:
            synthesis_method = "Moderate consensus — weighted toward higher-confidence agents"
        else:
            synthesis_method = "Low consensus — expertise-weighted voting resolved disagreements"

        warnings = []
        if confidence_score < 0.5:
            warnings.append("Low agent confidence — consider reviewing manually")
        if agreement_score < 0.4:
            warnings.append("Significant agent disagreement — multiple valid approaches may exist")
        if completeness_score < 0.5:
            warnings.append("Response may not fully address the task")
        if specificity_score < 0.4:
            warnings.append("Response is more conceptual than concrete")

        suggestions = []
        if agreement_score < 0.5:
            suggestions.append("Try 'debate' mode for deeper exploration of disagreements")
        if specificity_score < 0.5 and task_type in ("coding", "debugging"):
            suggestions.append("Add code context or error messages for more specific answers")
        if len(successful) == 1:
            suggestions.append("Use 'parallel' or 'consensus' mode for multi-agent validation")

        return QualityReport(
            overall_score=overall, grade=grade,
            confidence_score=confidence_score,
            agreement_score=agreement_score,
            completeness_score=completeness_score,
            specificity_score=specificity_score,
            perspectives=perspectives,
            agreements=agreements,
            disagreements=disagreements,
            synthesis_method=synthesis_method,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _compute_confidence(self, responses, expertise_weights):
        total_weight = 0.0
        weighted_conf = 0.0
        for r in responses:
            w = (expertise_weights or {}).get(r.agent_name, 1.0)
            weighted_conf += r.confidence * w
            total_weight += w
        return weighted_conf / total_weight if total_weight > 0 else 0.0

    def _compute_agreement(self, responses):
        if len(responses) < 2:
            return 1.0, ["Single agent — no disagreement possible"], []

        term_sets = []
        for r in responses:
            terms = set(self._extract_terms(r.content or ""))
            term_sets.append((r.agent_name, terms))

        similarities = []
        agreements = []
        disagreements = []

        for i in range(len(term_sets)):
            for j in range(i + 1, len(term_sets)):
                name_i, terms_i = term_sets[i]
                name_j, terms_j = term_sets[j]
                if not terms_i or not terms_j:
                    similarities.append(0.5)
                    continue

                intersection = terms_i & terms_j
                union = terms_i | terms_j
                jaccard = len(intersection) / len(union) if union else 0.0
                similarities.append(jaccard)

                shared = intersection - self.STOPWORDS
                if shared:
                    top_shared = sorted(shared, key=len, reverse=True)[:3]
                    agreements.append(f"{name_i} & {name_j} agree on: {', '.join(top_shared)}")

                if jaccard < 0.3:
                    only_i = sorted(terms_i - terms_j, key=len, reverse=True)[:2]
                    only_j = sorted(terms_j - terms_i, key=len, reverse=True)[:2]
                    if only_i and only_j:
                        disagreements.append(
                            f"{name_i} focuses on {', '.join(only_i)}, "
                            f"while {name_j} focuses on {', '.join(only_j)}"
                        )

        avg_sim = sum(similarities) / len(similarities) if similarities else 0.5
        confidences = [r.confidence for r in responses]
        conf_spread = max(confidences) - min(confidences)
        conf_agreement = max(0.0, 1.0 - conf_spread * 2)
        return 0.7 * avg_sim + 0.3 * conf_agreement, agreements[:5], disagreements[:5]

    def _compute_completeness(self, answer, prompt):
        if not answer:
            return 0.0
        prompt_terms = set(self._extract_terms(prompt))
        answer_terms = set(self._extract_terms(answer))
        if not prompt_terms:
            return 0.7
        coverage = len(prompt_terms & answer_terms) / len(prompt_terms)
        length_score = min(1.0, len(answer) / max(len(prompt) * 2, 200))
        return 0.6 * coverage + 0.4 * length_score

    def _compute_specificity(self, answer, task_type):
        if not answer:
            return 0.0
        score = 0.5
        code_blocks = len(re.findall(r'```', answer)) // 2
        score += min(0.3, code_blocks * 0.1)
        steps = len(re.findall(r'^\s*\d+[\.\)]\s', answer, re.MULTILINE))
        score += min(0.15, steps * 0.03)
        specifics = len(re.findall(r'`[^`]+`', answer))
        score += min(0.15, specifics * 0.02)
        hedges = len(re.findall(r'\b(maybe|perhaps|might|could|possibly|generally|usually)\b', answer, re.I))
        score -= min(0.2, hedges * 0.03)
        return max(0.0, min(1.0, score))

    def _extract_terms(self, text):
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{2,}', text.lower())
        return [w for w in words if w not in self.STOPWORDS]

    def _extract_key_points(self, content, max_points=3):
        bullets = re.findall(r'[-*]\s+(.+?)(?:\n|$)', content)
        numbered = re.findall(r'\d+[\.\)]\s+(.+?)(?:\n|$)', content)
        bold = re.findall(r'\*\*(.+?)\*\*', content)
        points = bullets + numbered + bold
        seen = set()
        unique = []
        for p in points:
            p_clean = p.strip()[:100]
            if p_clean and p_clean.lower() not in seen:
                seen.add(p_clean.lower())
                unique.append(p_clean)
        return unique[:max_points] if unique else [content[:100].strip()]


_scorer: Optional[QualityScorer] = None

def get_quality_scorer() -> QualityScorer:
    global _scorer
    if _scorer is None:
        _scorer = QualityScorer()
    return _scorer
