"""
Cross-Project Intelligence — KnowledgeNexus
=============================================

Moat feature #2: No competitor (CrewAI, AutoGen, LangGraph) has this.
Learns patterns across ALL projects, surfaces cross-project fixes and insights.

Usage:
    nexus = get_nexus()
    nexus.register_project("dashboard", "/path/to/dashboard", ["python", "fastapi"])
    nexus.index_solution("dashboard", "CORS error", "Add middleware config", ["cors", "fastapi"])
    results = nexus.search_across_projects("CORS blocking requests")
"""

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ProjectRecord:
    """A registered project."""
    name: str
    project_id: str = ""
    path: str = ""
    tech_stack: List[str] = field(default_factory=list)
    registered_at: str = ""
    solution_count: int = 0
    mistake_count: int = 0

    def __post_init__(self):
        if not self.project_id:
            self.project_id = f"proj-{uuid.uuid4().hex[:8]}"
        if not self.registered_at:
            self.registered_at = datetime.now(timezone.utc).isoformat()


@dataclass
class IndexedSolution:
    """A solution indexed for cross-project search."""
    solution_id: str
    project: str
    problem: str
    solution: str
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    times_reused: int = 0
    indexed_at: str = ""

    def __post_init__(self):
        if not self.solution_id:
            self.solution_id = f"sol-{uuid.uuid4().hex[:8]}"
        if not self.indexed_at:
            self.indexed_at = datetime.now(timezone.utc).isoformat()


@dataclass
class IndexedMistake:
    """A mistake indexed for cross-project prevention."""
    mistake_id: str
    project: str
    mistake: str
    resolution: str
    tags: List[str] = field(default_factory=list)
    severity: str = "medium"
    indexed_at: str = ""

    def __post_init__(self):
        if not self.mistake_id:
            self.mistake_id = f"mis-{uuid.uuid4().hex[:8]}"
        if not self.indexed_at:
            self.indexed_at = datetime.now(timezone.utc).isoformat()


@dataclass
class CrossProjectInsight:
    """An insight derived from cross-project analysis."""
    pattern: str
    projects_affected: List[str]
    solution: str
    confidence: float
    occurrences: int


class KnowledgeNexus:
    """
    Cross-project intelligence engine.

    Indexes solutions and mistakes across all projects, enables
    cross-project search, and surfaces patterns that span multiple codebases.
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/nexus"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._projects: Dict[str, ProjectRecord] = {}
        self._solutions: List[IndexedSolution] = []
        self._mistakes: List[IndexedMistake] = []
        self._load()

    def _load(self):
        """Load state from disk."""
        for fname, target, cls in [
            ("projects.json", "_projects", ProjectRecord),
            ("solutions.json", "_solutions", IndexedSolution),
            ("mistakes.json", "_mistakes", IndexedMistake),
        ]:
            fpath = self.storage_dir / fname
            if fpath.exists():
                try:
                    with open(fpath) as f:
                        data = json.load(f)
                    if target == "_projects":
                        self._projects = {p["project_id"]: cls(**p) for p in data}
                    else:
                        setattr(self, target, [cls(**d) for d in data])
                except Exception as e:
                    logger.warning(f"Error loading {fname}: {e}")

    def _save(self):
        """Save state to disk."""
        try:
            with open(self.storage_dir / "projects.json", "w") as f:
                json.dump([asdict(p) for p in self._projects.values()], f, indent=2)
            with open(self.storage_dir / "solutions.json", "w") as f:
                json.dump([asdict(s) for s in self._solutions], f, indent=2)
            with open(self.storage_dir / "mistakes.json", "w") as f:
                json.dump([asdict(m) for m in self._mistakes], f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving nexus state: {e}")

    def register_project(self, name: str, path: str = "", tech_stack: Optional[List[str]] = None) -> str:
        """Register a project. Returns project_id."""
        proj = ProjectRecord(name=name, path=path, tech_stack=tech_stack or [])
        self._projects[proj.project_id] = proj
        self._save()
        return proj.project_id

    def index_solution(
        self, project: str, problem: str, solution: str,
        tags: Optional[List[str]] = None, confidence: float = 1.0,
    ) -> str:
        """Index a solution for cross-project search. Returns solution_id."""
        sol = IndexedSolution(
            solution_id=f"sol-{uuid.uuid4().hex[:8]}",
            project=project, problem=problem, solution=solution,
            tags=tags or [], confidence=confidence,
        )
        self._solutions.append(sol)
        # Update project counter
        for p in self._projects.values():
            if p.name == project:
                p.solution_count += 1
                break
        self._save()
        return sol.solution_id

    def index_mistake(
        self, project: str, mistake: str, resolution: str,
        tags: Optional[List[str]] = None, severity: str = "medium",
    ) -> str:
        """Index a mistake for cross-project prevention. Returns mistake_id."""
        mis = IndexedMistake(
            mistake_id=f"mis-{uuid.uuid4().hex[:8]}",
            project=project, mistake=mistake, resolution=resolution,
            tags=tags or [], severity=severity,
        )
        self._mistakes.append(mis)
        for p in self._projects.values():
            if p.name == project:
                p.mistake_count += 1
                break
        self._save()
        return mis.mistake_id

    def search_across_projects(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search solutions and mistakes across all projects."""
        query_words = set(query.lower().split())
        results = []

        for sol in self._solutions:
            score = self._relevance_score(query_words, sol.problem, sol.solution, sol.tags)
            if score > 0:
                results.append({
                    "type": "solution",
                    "project": sol.project,
                    "problem": sol.problem,
                    "solution": sol.solution,
                    "tags": sol.tags,
                    "confidence": sol.confidence,
                    "times_reused": sol.times_reused,
                    "score": score,
                })

        for mis in self._mistakes:
            score = self._relevance_score(query_words, mis.mistake, mis.resolution, mis.tags)
            if score > 0:
                results.append({
                    "type": "mistake",
                    "project": mis.project,
                    "mistake": mis.mistake,
                    "resolution": mis.resolution,
                    "tags": mis.tags,
                    "severity": mis.severity,
                    "score": score,
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    def get_related_solutions(self, problem_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find solutions related to a problem description."""
        return self.search_across_projects(problem_text, limit=limit)

    def get_project_insights(self, project_name: str) -> Dict[str, Any]:
        """Get insights for a specific project."""
        proj = None
        for p in self._projects.values():
            if p.name == project_name:
                proj = p
                break

        solutions = [s for s in self._solutions if s.project == project_name]
        mistakes = [m for m in self._mistakes if m.project == project_name]

        # Find solutions from OTHER projects that share tags
        project_tags: Set[str] = set()
        for s in solutions:
            project_tags.update(s.tags)
        for m in mistakes:
            project_tags.update(m.tags)

        cross_project_solutions = []
        for s in self._solutions:
            if s.project != project_name and set(s.tags) & project_tags:
                cross_project_solutions.append({
                    "from_project": s.project,
                    "problem": s.problem,
                    "solution": s.solution,
                    "shared_tags": list(set(s.tags) & project_tags),
                })

        return {
            "project": project_name,
            "registered": asdict(proj) if proj else None,
            "total_solutions": len(solutions),
            "total_mistakes": len(mistakes),
            "top_tags": self._top_tags(solutions, mistakes),
            "cross_project_solutions": cross_project_solutions[:10],
        }

    def get_cross_project_patterns(self) -> List[CrossProjectInsight]:
        """Find patterns that appear across multiple projects."""
        # Group solutions by tag
        tag_solutions: Dict[str, List[IndexedSolution]] = {}
        for sol in self._solutions:
            for tag in sol.tags:
                tag_solutions.setdefault(tag, []).append(sol)

        insights = []
        for tag, solutions in tag_solutions.items():
            projects = list(set(s.project for s in solutions))
            if len(projects) >= 2:
                # This pattern spans multiple projects
                best_sol = max(solutions, key=lambda s: s.confidence)
                insights.append(CrossProjectInsight(
                    pattern=tag,
                    projects_affected=projects,
                    solution=best_sol.solution,
                    confidence=best_sol.confidence,
                    occurrences=len(solutions),
                ))

        return sorted(insights, key=lambda i: i.occurrences, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get nexus statistics."""
        return {
            "total_projects": len(self._projects),
            "total_solutions": len(self._solutions),
            "total_mistakes": len(self._mistakes),
            "projects": [{"name": p.name, "solutions": p.solution_count, "mistakes": p.mistake_count}
                         for p in self._projects.values()],
            "cross_project_patterns": len(self.get_cross_project_patterns()),
        }

    def _relevance_score(self, query_words: Set[str], *texts_and_tags) -> float:
        """Calculate relevance score based on word overlap."""
        all_text = ""
        tag_set: Set[str] = set()

        for item in texts_and_tags:
            if isinstance(item, list):
                tag_set.update(t.lower() for t in item)
            elif isinstance(item, str):
                all_text += " " + item.lower()

        text_words = set(all_text.split())
        overlap = query_words & text_words
        tag_overlap = query_words & tag_set

        if not overlap and not tag_overlap:
            return 0.0

        text_score = len(overlap) / max(len(query_words), 1)
        tag_score = len(tag_overlap) * 0.3  # Tags are worth more
        return round(text_score + tag_score, 3)

    def _top_tags(self, solutions: List[IndexedSolution], mistakes: List[IndexedMistake], limit: int = 10) -> List[str]:
        """Get most common tags."""
        tag_counts: Dict[str, int] = {}
        for s in solutions:
            for t in s.tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1
        for m in mistakes:
            for t in m.tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1
        return sorted(tag_counts, key=tag_counts.get, reverse=True)[:limit]


def get_nexus() -> KnowledgeNexus:
    """Get singleton nexus instance."""
    if not hasattr(get_nexus, "_instance"):
        get_nexus._instance = KnowledgeNexus()
    return get_nexus._instance
