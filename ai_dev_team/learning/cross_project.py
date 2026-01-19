"""
Cross-Project Learning System
=============================

Enables knowledge sharing across multiple projects (ChatterFix, Fix it Fred,
LineSmart, etc.) to prevent repeated mistakes and leverage successful solutions.

Features:
- Project profiles with domain and technology stack
- Knowledge transfer between similar projects
- Cross-project insights and pattern detection
- Solution recommendation based on project context
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import difflib

logger = logging.getLogger(__name__)


class InsightType(Enum):
    """Types of cross-project insights"""
    COMMON_ERROR = "common_error"  # Same error across projects
    SHARED_SOLUTION = "shared_solution"  # Solution applicable to multiple projects
    PATTERN_MATCH = "pattern_match"  # Similar code patterns
    BEST_PRACTICE = "best_practice"  # Proven best practices
    ANTI_PATTERN = "anti_pattern"  # Things to avoid
    OPTIMIZATION = "optimization"  # Performance improvements


@dataclass
class ProjectProfile:
    """Profile of a project for cross-project learning"""
    name: str
    domain: str  # e.g., 'maintenance_management', 'training', 'automation'
    description: str
    technologies: List[str]  # e.g., ['python', 'flask', 'react', 'postgresql']
    frameworks: List[str]  # e.g., ['fastapi', 'nextjs']
    challenges: List[str]  # Common challenges faced
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    solution_count: int = 0
    error_count: int = 0
    pattern_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectProfile':
        data = data.copy()
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class KnowledgeEntry:
    """A piece of knowledge that can be shared across projects"""
    entry_id: str
    source_project: str
    entry_type: str  # 'solution', 'error_fix', 'pattern', 'best_practice'
    title: str
    description: str
    content: str  # The actual solution/pattern/fix
    tags: List[str]
    technologies: List[str]
    success_count: int = 0
    failure_count: int = 0
    shared_with: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        result['success_rate'] = self.success_rate
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeEntry':
        data = data.copy()
        data.pop('success_rate', None)
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class CrossProjectInsight:
    """An insight derived from cross-project analysis"""
    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    projects_involved: List[str]
    recommendations: List[str]
    confidence: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['insight_type'] = self.insight_type.value
        result['created_at'] = self.created_at.isoformat()
        return result


class CrossProjectLearning:
    """
    Cross-Project Learning System

    Enables knowledge sharing and pattern recognition across multiple projects.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path.home() / '.ai-dev-team' / 'cross-learning'
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._projects: Dict[str, ProjectProfile] = {}
        self._knowledge_base: Dict[str, KnowledgeEntry] = {}
        self._insights: List[CrossProjectInsight] = []
        self._entry_counter = 0

        self._load_data()

    def _load_data(self):
        """Load persisted data"""
        # Load projects
        projects_file = self.data_dir / 'projects.json'
        if projects_file.exists():
            with open(projects_file, 'r') as f:
                data = json.load(f)
                self._projects = {
                    name: ProjectProfile.from_dict(p)
                    for name, p in data.items()
                }
                logger.info(f"Loaded {len(self._projects)} project profiles")

        # Load knowledge base
        knowledge_file = self.data_dir / 'knowledge.json'
        if knowledge_file.exists():
            with open(knowledge_file, 'r') as f:
                data = json.load(f)
                self._knowledge_base = {
                    eid: KnowledgeEntry.from_dict(e)
                    for eid, e in data.items()
                }
                self._entry_counter = len(self._knowledge_base)
                logger.info(f"Loaded {len(self._knowledge_base)} knowledge entries")

    def _save_data(self):
        """Persist data to disk"""
        # Save projects
        projects_file = self.data_dir / 'projects.json'
        with open(projects_file, 'w') as f:
            json.dump({
                name: p.to_dict()
                for name, p in self._projects.items()
            }, f, indent=2)

        # Save knowledge base
        knowledge_file = self.data_dir / 'knowledge.json'
        with open(knowledge_file, 'w') as f:
            json.dump({
                eid: e.to_dict()
                for eid, e in self._knowledge_base.items()
            }, f, indent=2)

    # ==================== Project Management ====================

    def register_project(
        self,
        name: str,
        domain: str,
        description: str,
        technologies: List[str],
        frameworks: Optional[List[str]] = None,
        challenges: Optional[List[str]] = None,
    ) -> ProjectProfile:
        """Register a new project for cross-project learning"""
        profile = ProjectProfile(
            name=name,
            domain=domain,
            description=description,
            technologies=technologies,
            frameworks=frameworks or [],
            challenges=challenges or [],
        )
        self._projects[name] = profile
        self._save_data()
        logger.info(f"Registered project: {name}")
        return profile

    def update_project(
        self,
        name: str,
        **updates,
    ) -> Optional[ProjectProfile]:
        """Update a project profile"""
        if name not in self._projects:
            return None

        profile = self._projects[name]
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = datetime.now(timezone.utc)
        self._save_data()
        return profile

    def get_project(self, name: str) -> Optional[ProjectProfile]:
        """Get a project profile"""
        return self._projects.get(name)

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all registered projects"""
        return [p.to_dict() for p in self._projects.values()]

    def find_similar_projects(
        self,
        project_name: str,
        min_similarity: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Find projects similar to the given project"""
        if project_name not in self._projects:
            return []

        source = self._projects[project_name]
        similar = []

        for name, project in self._projects.items():
            if name == project_name:
                continue

            # Calculate similarity based on technologies and domain
            tech_overlap = len(set(source.technologies) & set(project.technologies))
            tech_total = len(set(source.technologies) | set(project.technologies))
            tech_similarity = tech_overlap / tech_total if tech_total > 0 else 0

            domain_similarity = 1.0 if source.domain == project.domain else 0.3

            # Combined similarity score
            similarity = (tech_similarity * 0.6) + (domain_similarity * 0.4)

            if similarity >= min_similarity:
                similar.append({
                    'project': project.to_dict(),
                    'similarity': round(similarity, 3),
                    'shared_technologies': list(set(source.technologies) & set(project.technologies)),
                    'same_domain': source.domain == project.domain,
                })

        similar.sort(key=lambda x: x['similarity'], reverse=True)
        return similar

    # ==================== Knowledge Management ====================

    def add_knowledge(
        self,
        source_project: str,
        entry_type: str,
        title: str,
        description: str,
        content: str,
        tags: List[str],
        technologies: Optional[List[str]] = None,
    ) -> KnowledgeEntry:
        """Add a new knowledge entry"""
        self._entry_counter += 1
        entry_id = f"ke-{self._entry_counter:06d}"

        # Get technologies from project if not specified
        if technologies is None and source_project in self._projects:
            technologies = self._projects[source_project].technologies
        technologies = technologies or []

        entry = KnowledgeEntry(
            entry_id=entry_id,
            source_project=source_project,
            entry_type=entry_type,
            title=title,
            description=description,
            content=content,
            tags=tags,
            technologies=technologies,
        )

        self._knowledge_base[entry_id] = entry

        # Update project stats
        if source_project in self._projects:
            if entry_type == 'solution':
                self._projects[source_project].solution_count += 1
            elif entry_type == 'error_fix':
                self._projects[source_project].error_count += 1
            elif entry_type == 'pattern':
                self._projects[source_project].pattern_count += 1

        self._save_data()
        logger.info(f"Added knowledge entry: {entry_id} ({entry_type})")
        return entry

    def get_knowledge(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a knowledge entry by ID"""
        return self._knowledge_base.get(entry_id)

    def search_knowledge(
        self,
        query: Optional[str] = None,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        technologies: Optional[List[str]] = None,
        project: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base"""
        results = []

        for entry in self._knowledge_base.values():
            score = 1.0

            # Filter by type
            if entry_type and entry.entry_type != entry_type:
                continue

            # Filter by project
            if project and entry.source_project != project:
                continue

            # Filter/score by tags
            if tags:
                matching_tags = len(set(tags) & set(entry.tags))
                if matching_tags == 0:
                    continue
                score *= (0.5 + (matching_tags / len(tags)) * 0.5)

            # Filter/score by technologies
            if technologies:
                matching_tech = len(set(technologies) & set(entry.technologies))
                if matching_tech > 0:
                    score *= (0.5 + (matching_tech / len(technologies)) * 0.5)

            # Text search
            if query:
                query_lower = query.lower()
                if query_lower in entry.title.lower():
                    score *= 1.5
                elif query_lower in entry.description.lower():
                    score *= 1.2
                elif query_lower in entry.content.lower():
                    score *= 1.0
                else:
                    continue

            # Boost by success rate
            score *= (0.5 + entry.success_rate * 0.5)

            results.append({
                'entry': entry.to_dict(),
                'relevance_score': round(score, 3),
            })

        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:limit]

    def record_usage(
        self,
        entry_id: str,
        target_project: str,
        success: bool,
    ):
        """Record when knowledge is used by another project"""
        entry = self._knowledge_base.get(entry_id)
        if not entry:
            return

        if success:
            entry.success_count += 1
        else:
            entry.failure_count += 1

        if target_project not in entry.shared_with:
            entry.shared_with.append(target_project)

        entry.updated_at = datetime.now(timezone.utc)
        self._save_data()

    # ==================== Cross-Project Transfer ====================

    def get_recommendations_for_project(
        self,
        project_name: str,
        context: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get knowledge recommendations for a project"""
        if project_name not in self._projects:
            return []

        project = self._projects[project_name]
        recommendations = []

        for entry in self._knowledge_base.values():
            # Skip own knowledge
            if entry.source_project == project_name:
                continue

            score = 0.0

            # Technology match
            tech_match = len(set(project.technologies) & set(entry.technologies))
            if tech_match > 0:
                score += tech_match * 0.3

            # Check if from similar project
            if entry.source_project in self._projects:
                source = self._projects[entry.source_project]
                if source.domain == project.domain:
                    score += 0.3

            # Success rate boost
            score += entry.success_rate * 0.2

            # Context match
            if context:
                context_lower = context.lower()
                if context_lower in entry.title.lower() or context_lower in entry.description.lower():
                    score += 0.4

            if score > 0.2:
                recommendations.append({
                    'entry': entry.to_dict(),
                    'recommendation_score': round(score, 3),
                    'reason': self._get_recommendation_reason(project, entry),
                })

        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return recommendations[:limit]

    def _get_recommendation_reason(
        self,
        project: ProjectProfile,
        entry: KnowledgeEntry,
    ) -> str:
        """Generate a human-readable reason for the recommendation"""
        reasons = []

        tech_match = set(project.technologies) & set(entry.technologies)
        if tech_match:
            reasons.append(f"Uses same technologies: {', '.join(tech_match)}")

        if entry.source_project in self._projects:
            source = self._projects[entry.source_project]
            if source.domain == project.domain:
                reasons.append(f"From similar domain ({project.domain})")

        if entry.success_rate > 0.7:
            reasons.append(f"High success rate ({entry.success_rate:.0%})")

        if len(entry.shared_with) > 1:
            reasons.append(f"Proven in {len(entry.shared_with)} other projects")

        return "; ".join(reasons) if reasons else "Potentially relevant"

    def transfer_knowledge(
        self,
        entry_id: str,
        target_project: str,
    ) -> Dict[str, Any]:
        """Transfer a knowledge entry to another project"""
        entry = self._knowledge_base.get(entry_id)
        if not entry:
            return {'success': False, 'error': 'Entry not found'}

        if target_project not in self._projects:
            return {'success': False, 'error': 'Target project not found'}

        if target_project in entry.shared_with:
            return {'success': False, 'error': 'Already shared with this project'}

        entry.shared_with.append(target_project)
        entry.updated_at = datetime.now(timezone.utc)
        self._save_data()

        return {
            'success': True,
            'entry_id': entry_id,
            'target_project': target_project,
            'message': f"Knowledge transferred to {target_project}",
        }

    # ==================== Insights ====================

    def generate_insights(self) -> List[Dict[str, Any]]:
        """Generate cross-project insights"""
        insights = []

        # Find common errors across projects
        error_entries = [e for e in self._knowledge_base.values() if e.entry_type == 'error_fix']
        tag_counts: Dict[str, List[str]] = {}
        for entry in error_entries:
            for tag in entry.tags:
                if tag not in tag_counts:
                    tag_counts[tag] = []
                tag_counts[tag].append(entry.source_project)

        for tag, projects in tag_counts.items():
            if len(set(projects)) >= 2:
                insights.append({
                    'type': InsightType.COMMON_ERROR.value,
                    'title': f"Common error type: {tag}",
                    'description': f"This error type appears in {len(set(projects))} projects",
                    'projects': list(set(projects)),
                    'recommendation': f"Consider creating a shared solution for '{tag}' errors",
                })

        # Find widely successful solutions
        for entry in self._knowledge_base.values():
            if entry.success_rate > 0.8 and len(entry.shared_with) >= 2:
                insights.append({
                    'type': InsightType.BEST_PRACTICE.value,
                    'title': f"Proven solution: {entry.title}",
                    'description': f"This solution has {entry.success_rate:.0%} success rate across {len(entry.shared_with)} projects",
                    'projects': [entry.source_project] + entry.shared_with,
                    'recommendation': "Consider applying this pattern to all similar projects",
                })

        return insights

    def get_statistics(self) -> Dict[str, Any]:
        """Get cross-project learning statistics"""
        total_entries = len(self._knowledge_base)
        entries_by_type = {}
        total_shares = 0

        for entry in self._knowledge_base.values():
            entries_by_type[entry.entry_type] = entries_by_type.get(entry.entry_type, 0) + 1
            total_shares += len(entry.shared_with)

        avg_success_rate = (
            sum(e.success_rate for e in self._knowledge_base.values()) / total_entries
            if total_entries > 0 else 0
        )

        return {
            'total_projects': len(self._projects),
            'total_entries': total_entries,
            'entries_by_type': entries_by_type,
            'total_shares': total_shares,
            'avg_success_rate': round(avg_success_rate, 3),
            'projects': [
                {
                    'name': p.name,
                    'domain': p.domain,
                    'solutions': p.solution_count,
                    'errors': p.error_count,
                    'patterns': p.pattern_count,
                }
                for p in self._projects.values()
            ],
        }


# Singleton instance
_cross_project: Optional[CrossProjectLearning] = None


def get_cross_project_learning() -> CrossProjectLearning:
    """Get the global cross-project learning instance"""
    global _cross_project
    if _cross_project is None:
        _cross_project = CrossProjectLearning()
    return _cross_project
