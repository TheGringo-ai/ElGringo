"""
ChatterFix Integration
======================

Connects to ChatterFix's knowledge base for shared learnings.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict

# ChatterFix paths
CHATTERFIX_ROOT = Path(os.path.expanduser(
    "~/Development/Projects/ChatterFix"
))
CHATTERFIX_CLAUDE_MD = CHATTERFIX_ROOT / "CLAUDE.md"
CHATTERFIX_DOCUMENTS = CHATTERFIX_ROOT / "documents"


@dataclass
class Lesson:
    """A learned lesson from ChatterFix"""
    number: int
    title: str
    problem: str
    root_cause: str
    solution: str
    prevention: str


@dataclass
class KnowledgeBase:
    """ChatterFix knowledge base"""
    lessons: List[Lesson]
    patterns: List[str]
    solutions: Dict[str, str]
    available: bool


class ChatterFixConnector:
    """
    Connector to ChatterFix's knowledge base.

    Provides access to:
    - Learned lessons from CLAUDE.md
    - Architecture documentation
    - Solution patterns
    - Mistake prevention strategies
    """

    def __init__(self):
        self.available = CHATTERFIX_CLAUDE_MD.exists()
        self._knowledge: Optional[KnowledgeBase] = None

    def is_available(self) -> bool:
        """Check if ChatterFix is available"""
        return self.available

    def load_knowledge(self) -> KnowledgeBase:
        """Load knowledge from ChatterFix"""
        if self._knowledge:
            return self._knowledge

        lessons = []
        patterns = []
        solutions = {}

        if not self.available:
            self._knowledge = KnowledgeBase(
                lessons=lessons,
                patterns=patterns,
                solutions=solutions,
                available=False
            )
            return self._knowledge

        # Parse CLAUDE.md for lessons
        try:
            content = CHATTERFIX_CLAUDE_MD.read_text()
            lessons = self._parse_lessons(content)
            patterns = self._extract_patterns(content)
        except Exception:
            pass

        self._knowledge = KnowledgeBase(
            lessons=lessons,
            patterns=patterns,
            solutions=solutions,
            available=True
        )

        return self._knowledge

    def _parse_lessons(self, content: str) -> List[Lesson]:
        """Parse lessons from CLAUDE.md content"""
        lessons = []

        # Find lesson blocks
        import re
        lesson_pattern = r"LESSON #(\d+): ([^\n]+)\n\*\*Problem\*\*: ([^\n]+)\n\*\*Root Cause\*\*: ([^\n]+)\n\*\*Solution\*\*: ([^\n]+)\n\*\*Prevention\*\*: ([^\n]+)"

        for match in re.finditer(lesson_pattern, content, re.IGNORECASE):
            lessons.append(Lesson(
                number=int(match.group(1)),
                title=match.group(2).strip(),
                problem=match.group(3).strip(),
                root_cause=match.group(4).strip(),
                solution=match.group(5).strip(),
                prevention=match.group(6).strip()
            ))

        return lessons

    def _extract_patterns(self, content: str) -> List[str]:
        """Extract development patterns from content"""
        patterns = []

        # Extract patterns from known sections
        if "NEVER-REPEAT-MISTAKES" in content:
            patterns.append("mistake_prevention")
        if "UNIVERSAL SOLUTION DATABASE" in content:
            patterns.append("solution_reuse")
        if "VOICE COMMANDS" in content:
            patterns.append("voice_interface")
        if "OCR" in content:
            patterns.append("document_scanning")

        return patterns

    def get_lessons(self) -> List[Lesson]:
        """Get all learned lessons"""
        kb = self.load_knowledge()
        return kb.lessons

    def search_lessons(self, query: str) -> List[Lesson]:
        """Search lessons by keyword"""
        query = query.lower()
        lessons = self.get_lessons()

        return [
            item for item in lessons
            if query in item.title.lower() or
               query in item.problem.lower() or
               query in item.solution.lower()
        ]

    def get_prevention_advice(self, context: str) -> Optional[str]:
        """Get prevention advice based on context"""
        context_lower = context.lower()

        for lesson in self.get_lessons():
            # Check if this lesson is relevant
            if any(word in context_lower for word in lesson.problem.lower().split()):
                return f"Warning from ChatterFix Lesson #{lesson.number}: {lesson.title}\n" \
                       f"Prevention: {lesson.prevention}"

        return None

    def get_solution_hint(self, problem: str) -> Optional[str]:
        """Get solution hint from knowledge base"""
        problem_lower = problem.lower()

        for lesson in self.get_lessons():
            # Check if this lesson matches the problem
            if any(word in problem_lower for word in lesson.problem.lower().split()[:5]):
                return f"Similar issue found (Lesson #{lesson.number}):\n" \
                       f"Root Cause: {lesson.root_cause}\n" \
                       f"Solution: {lesson.solution}"

        return None

    def get_documents_path(self) -> Optional[Path]:
        """Get path to ChatterFix documents folder"""
        if CHATTERFIX_DOCUMENTS.exists():
            return CHATTERFIX_DOCUMENTS
        return None


# Global connector instance
_connector: Optional[ChatterFixConnector] = None


def get_connector() -> ChatterFixConnector:
    """Get the ChatterFix connector singleton"""
    global _connector
    if _connector is None:
        _connector = ChatterFixConnector()
    return _connector


def check_against_learnings(context: str) -> Optional[str]:
    """
    Check development context against ChatterFix learnings.
    Returns warning/advice if relevant lessons found.
    """
    connector = get_connector()
    return connector.get_prevention_advice(context)


def find_solution(problem: str) -> Optional[str]:
    """
    Find solution hints from ChatterFix knowledge base.
    """
    connector = get_connector()
    return connector.get_solution_hint(problem)
