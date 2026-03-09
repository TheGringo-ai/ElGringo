"""
Teaching System - Train the AI team with new knowledge
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Lesson:
    """A lesson to teach the AI team"""
    lesson_id: str
    domain: str
    topic: str
    content: str
    examples: List[Dict[str, str]] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "manual"  # manual, code_review, project, documentation


@dataclass
class ProjectPattern:
    """A successful project pattern to learn from"""
    pattern_id: str
    name: str
    description: str
    domains: List[str]
    structure: Dict[str, Any]  # File structure, architecture
    technologies: List[str]
    code_samples: Dict[str, str]  # filename -> code
    lessons_learned: List[str]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TeachingSystem:
    """
    System for teaching the AI team new knowledge.

    Allows adding lessons, project patterns, and building
    domain expertise over time.
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/knowledge"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._lessons: List[Lesson] = []
        self._patterns: List[ProjectPattern] = []
        self._custom_domains: Dict[str, Dict] = {}

        self._load_knowledge()

    def _load_knowledge(self):
        """Load existing knowledge from disk"""
        try:
            lessons_file = self.storage_dir / "lessons.json"
            if lessons_file.exists():
                with open(lessons_file) as f:
                    data = json.load(f)
                    self._lessons = [Lesson(**item) for item in data]

            patterns_file = self.storage_dir / "patterns.json"
            if patterns_file.exists():
                with open(patterns_file) as f:
                    data = json.load(f)
                    self._patterns = [ProjectPattern(**item) for item in data]

            domains_file = self.storage_dir / "custom_domains.json"
            if domains_file.exists():
                with open(domains_file) as f:
                    self._custom_domains = json.load(f)

        except Exception as e:
            logger.warning(f"Error loading knowledge: {e}")

    def _save_knowledge(self):
        """Save knowledge to disk"""
        try:
            with open(self.storage_dir / "lessons.json", "w") as f:
                json.dump([asdict(lesson) for lesson in self._lessons], f, indent=2)

            with open(self.storage_dir / "patterns.json", "w") as f:
                json.dump([asdict(p) for p in self._patterns], f, indent=2)

            with open(self.storage_dir / "custom_domains.json", "w") as f:
                json.dump(self._custom_domains, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving knowledge: {e}")

    def add_lesson(
        self,
        domain: str,
        topic: str,
        content: str,
        examples: Optional[List[Dict[str, str]]] = None,
        best_practices: Optional[List[str]] = None,
        anti_patterns: Optional[List[str]] = None,
        source: str = "manual",
    ) -> str:
        """
        Add a new lesson to the knowledge base.

        Args:
            domain: Domain area (frontend, backend, etc.)
            topic: Specific topic
            content: Main lesson content
            examples: Code examples [{"description": "", "code": ""}]
            best_practices: List of best practices
            anti_patterns: Things to avoid
            source: Where this lesson came from

        Returns:
            Lesson ID
        """
        import hashlib
        lesson_id = hashlib.sha256(
            f"{domain}{topic}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        lesson = Lesson(
            lesson_id=lesson_id,
            domain=domain,
            topic=topic,
            content=content,
            examples=examples or [],
            best_practices=best_practices or [],
            anti_patterns=anti_patterns or [],
            source=source,
        )

        self._lessons.append(lesson)
        self._save_knowledge()

        logger.info(f"Added lesson: {topic} ({domain})")
        return lesson_id

    def add_project_pattern(
        self,
        name: str,
        description: str,
        domains: List[str],
        structure: Dict[str, Any],
        technologies: List[str],
        code_samples: Optional[Dict[str, str]] = None,
        lessons_learned: Optional[List[str]] = None,
    ) -> str:
        """
        Add a successful project pattern.

        Args:
            name: Pattern name
            description: What this pattern does
            domains: Related domains
            structure: Project structure
            technologies: Technologies used
            code_samples: Example code files
            lessons_learned: Key takeaways

        Returns:
            Pattern ID
        """
        import hashlib
        pattern_id = hashlib.sha256(
            f"{name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        pattern = ProjectPattern(
            pattern_id=pattern_id,
            name=name,
            description=description,
            domains=domains,
            structure=structure,
            technologies=technologies,
            code_samples=code_samples or {},
            lessons_learned=lessons_learned or [],
        )

        self._patterns.append(pattern)
        self._save_knowledge()

        logger.info(f"Added project pattern: {name}")
        return pattern_id

    def add_custom_domain(
        self,
        domain_name: str,
        technologies: List[str],
        best_practices: List[str],
        patterns: List[str],
        common_mistakes: List[str],
    ):
        """
        Add a custom domain expertise area.

        Args:
            domain_name: Name of the domain
            technologies: Technologies in this domain
            best_practices: Best practices to follow
            patterns: Design patterns to use
            common_mistakes: Mistakes to avoid
        """
        self._custom_domains[domain_name] = {
            "technologies": technologies,
            "best_practices": best_practices,
            "patterns": patterns,
            "common_mistakes": common_mistakes,
        }
        self._save_knowledge()
        logger.info(f"Added custom domain: {domain_name}")

    def get_lessons_for_domain(self, domain: str) -> List[Lesson]:
        """Get all lessons for a domain"""
        return [lesson for lesson in self._lessons if lesson.domain == domain]

    def get_lessons_for_topic(self, topic: str) -> List[Lesson]:
        """Search lessons by topic"""
        topic_lower = topic.lower()
        return [
            lesson for lesson in self._lessons
            if topic_lower in lesson.topic.lower() or topic_lower in lesson.content.lower()
        ]

    def get_patterns_for_domains(self, domains: List[str]) -> List[ProjectPattern]:
        """Get patterns that match any of the domains"""
        return [
            p for p in self._patterns
            if any(d in p.domains for d in domains)
        ]

    def generate_teaching_context(
        self,
        domains: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
    ) -> str:
        """
        Generate context string for AI prompts.

        Combines domain expertise, lessons, and patterns into
        a context string that can be prepended to prompts.
        """
        context_parts = []

        # Add custom domain knowledge
        if domains:
            for domain in domains:
                if domain in self._custom_domains:
                    expertise = self._custom_domains[domain]
                    context_parts.append(f"\n## {domain.upper()} EXPERTISE (Custom)\n")
                    context_parts.append(f"**Technologies**: {', '.join(expertise['technologies'])}")
                    context_parts.append("**Best Practices**:\n" + "\n".join(f"- {bp}" for bp in expertise['best_practices']))
                    context_parts.append("**Avoid**:\n" + "\n".join(f"- {m}" for m in expertise['common_mistakes']))

        # Add relevant lessons
        relevant_lessons = []
        if domains:
            for domain in domains:
                relevant_lessons.extend(self.get_lessons_for_domain(domain))
        if topics:
            for topic in topics:
                relevant_lessons.extend(self.get_lessons_for_topic(topic))

        # Deduplicate
        seen_ids = set()
        unique_lessons = []
        for lesson in relevant_lessons:
            if lesson.lesson_id not in seen_ids:
                seen_ids.add(lesson.lesson_id)
                unique_lessons.append(lesson)

        if unique_lessons:
            context_parts.append("\n## RELEVANT LESSONS\n")
            for lesson in unique_lessons[:5]:  # Limit to 5 most relevant
                context_parts.append(f"### {lesson.topic}")
                context_parts.append(lesson.content[:500])
                if lesson.best_practices:
                    context_parts.append("Best practices: " + "; ".join(lesson.best_practices[:3]))

        # Add relevant patterns
        if domains:
            patterns = self.get_patterns_for_domains(domains)
            if patterns:
                context_parts.append("\n## PROVEN PATTERNS\n")
                for pattern in patterns[:3]:
                    context_parts.append(f"### {pattern.name}")
                    context_parts.append(pattern.description)
                    if pattern.lessons_learned:
                        context_parts.append("Key lessons: " + "; ".join(pattern.lessons_learned[:3]))

        return "\n".join(context_parts)

    def learn_from_code_review(
        self,
        code: str,
        review_feedback: str,
        domain: str,
        was_approved: bool,
    ) -> str:
        """
        Learn from a code review outcome.

        Args:
            code: The code that was reviewed
            review_feedback: Feedback from the review
            domain: Domain of the code
            was_approved: Whether the code was approved

        Returns:
            Lesson ID if a lesson was created
        """
        if was_approved:
            # Learn good patterns
            return self.add_lesson(
                domain=domain,
                topic="Approved code pattern",
                content=f"This code pattern was approved:\n```\n{code[:500]}\n```\n\nFeedback: {review_feedback}",
                best_practices=[review_feedback[:200]],
                source="code_review",
            )
        else:
            # Learn what to avoid
            return self.add_lesson(
                domain=domain,
                topic="Code review rejection",
                content=f"This code needed changes:\n```\n{code[:500]}\n```\n\nFeedback: {review_feedback}",
                anti_patterns=[review_feedback[:200]],
                source="code_review",
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get teaching system statistics"""
        domains_covered = set()
        for lesson in self._lessons:
            domains_covered.add(lesson.domain)
        for pattern in self._patterns:
            domains_covered.update(pattern.domains)
        domains_covered.update(self._custom_domains.keys())

        return {
            "total_lessons": len(self._lessons),
            "total_patterns": len(self._patterns),
            "custom_domains": len(self._custom_domains),
            "domains_covered": list(domains_covered),
            "lessons_by_domain": {
                domain: len([lesson for lesson in self._lessons if lesson.domain == domain])
                for domain in domains_covered
            },
        }
