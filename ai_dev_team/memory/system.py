"""
Memory System - Core memory and knowledge storage
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OutcomeRating(Enum):
    """Rating for interaction outcomes"""
    EXCELLENT = 5
    GOOD = 4
    SATISFACTORY = 3
    POOR = 2
    FAILURE = 1


class MistakeType(Enum):
    """Types of mistakes that can be tracked"""
    CODE_ERROR = "code_error"
    ARCHITECTURE_FLAW = "architecture_flaw"
    PERFORMANCE_ISSUE = "performance_issue"
    SECURITY_VULNERABILITY = "security_vulnerability"
    DEPLOYMENT_FAILURE = "deployment_failure"
    LOGIC_ERROR = "logic_error"
    INTEGRATION_ISSUE = "integration_issue"


@dataclass
class Interaction:
    """Record of an AI team interaction"""
    interaction_id: str
    timestamp: str
    project: str
    prompt: str
    context: str
    responses: List[Dict[str, Any]]
    final_answer: str
    success: bool
    confidence: float
    total_time: float
    agents_used: List[str]
    outcome_rating: int = 3
    lessons_learned: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class MistakeRecord:
    """Record of a mistake for prevention"""
    mistake_id: str
    timestamp: str
    mistake_type: str
    description: str
    context: Dict[str, Any]
    resolution: str
    prevention_strategy: str
    severity: str
    related_projects: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class SolutionRecord:
    """Record of a successful solution pattern"""
    solution_id: str
    timestamp: str
    problem_pattern: str
    solution_steps: List[str]
    success_rate: float
    projects_used: List[str]
    best_practices: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


class MemorySystem:
    """
    Comprehensive memory system for AI team learning.

    Supports both local file storage and Firestore for persistence.
    Captures all interactions, mistakes, and solutions for continuous improvement.
    """

    def __init__(
        self,
        storage_dir: str = "~/.ai-dev-team/memory",
        use_firestore: bool = False,
        project_id: Optional[str] = None,
    ):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.use_firestore = use_firestore
        self.project_id = project_id
        self._firestore_client = None

        # In-memory caches
        self._interactions_cache: List[Interaction] = []
        self._mistakes_cache: List[MistakeRecord] = []
        self._solutions_cache: List[SolutionRecord] = []

        # Load existing data
        self._load_from_disk()

    def _get_firestore(self):
        """Get Firestore client if available"""
        if self._firestore_client is None and self.use_firestore:
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore

                # Check if already initialized
                try:
                    firebase_admin.get_app()
                except ValueError:
                    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                    if cred_path and os.path.exists(cred_path):
                        cred = credentials.Certificate(cred_path)
                        firebase_admin.initialize_app(cred)
                    else:
                        firebase_admin.initialize_app()

                self._firestore_client = firestore.client()
            except Exception as e:
                logger.warning(f"Firestore not available: {e}")

        return self._firestore_client

    def _generate_id(self, content: str) -> str:
        """Generate unique ID"""
        return hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:16]

    def _load_from_disk(self):
        """Load cached data from disk"""
        try:
            interactions_file = self.storage_dir / "interactions.json"
            if interactions_file.exists():
                with open(interactions_file) as f:
                    data = json.load(f)
                    self._interactions_cache = [Interaction(**item) for item in data[-1000:]]

            mistakes_file = self.storage_dir / "mistakes.json"
            if mistakes_file.exists():
                with open(mistakes_file) as f:
                    data = json.load(f)
                    self._mistakes_cache = [MistakeRecord(**item) for item in data]

            solutions_file = self.storage_dir / "solutions.json"
            if solutions_file.exists():
                with open(solutions_file) as f:
                    data = json.load(f)
                    self._solutions_cache = [SolutionRecord(**item) for item in data]

        except Exception as e:
            logger.warning(f"Error loading from disk: {e}")

    def _save_to_disk(self):
        """Save cached data to disk"""
        try:
            with open(self.storage_dir / "interactions.json", "w") as f:
                json.dump([asdict(i) for i in self._interactions_cache[-1000:]], f, indent=2)

            with open(self.storage_dir / "mistakes.json", "w") as f:
                json.dump([asdict(m) for m in self._mistakes_cache], f, indent=2)

            with open(self.storage_dir / "solutions.json", "w") as f:
                json.dump([asdict(s) for s in self._solutions_cache], f, indent=2)

        except Exception as e:
            logger.error(f"Error saving to disk: {e}")

    async def capture_interaction(
        self,
        result,  # CollaborationResult
        project: str = "default",
        tags: Optional[List[str]] = None,
    ) -> str:
        """Capture an AI team interaction"""
        interaction_id = self._generate_id(result.task_id)

        interaction = Interaction(
            interaction_id=interaction_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            project=project,
            prompt=result.metadata.get("prompt", ""),
            context=result.metadata.get("context", ""),
            responses=[
                {
                    "agent": r.agent_name,
                    "content": r.content[:1000],  # Truncate for storage
                    "confidence": r.confidence,
                    "success": r.success,
                }
                for r in result.agent_responses
            ],
            final_answer=result.final_answer[:2000],  # Truncate
            success=result.success,
            confidence=result.confidence_score,
            total_time=result.total_time,
            agents_used=result.participating_agents,
            tags=tags or [],
        )

        self._interactions_cache.append(interaction)
        self._save_to_disk()

        # Also save to Firestore if available
        if self.use_firestore:
            db = self._get_firestore()
            if db:
                try:
                    db.collection("ai_interactions").document(interaction_id).set(asdict(interaction))
                except Exception as e:
                    logger.warning(f"Firestore save failed: {e}")

        logger.info(f"Captured interaction {interaction_id}")
        return interaction_id

    async def capture_mistake(
        self,
        mistake_type: MistakeType,
        description: str,
        context: Dict[str, Any],
        resolution: str = "",
        prevention_strategy: str = "",
        severity: str = "medium",
        project: str = "default",
        tags: Optional[List[str]] = None,
    ) -> str:
        """Capture a mistake for prevention learning"""
        mistake_id = self._generate_id(description)

        mistake = MistakeRecord(
            mistake_id=mistake_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            mistake_type=mistake_type.value,
            description=description,
            context=context,
            resolution=resolution,
            prevention_strategy=prevention_strategy,
            severity=severity,
            related_projects=[project],
            tags=tags or [],
        )

        self._mistakes_cache.append(mistake)
        self._save_to_disk()

        if self.use_firestore:
            db = self._get_firestore()
            if db:
                try:
                    db.collection("mistake_patterns").document(mistake_id).set(asdict(mistake))
                except Exception as e:
                    logger.warning(f"Firestore save failed: {e}")

        logger.warning(f"Captured mistake pattern: {mistake_id}")
        return mistake_id

    async def capture_solution(
        self,
        problem_pattern: str,
        solution_steps: List[str],
        success_rate: float = 1.0,
        project: str = "default",
        best_practices: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Capture a successful solution pattern"""
        solution_id = self._generate_id(problem_pattern)

        solution = SolutionRecord(
            solution_id=solution_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            problem_pattern=problem_pattern,
            solution_steps=solution_steps,
            success_rate=success_rate,
            projects_used=[project],
            best_practices=best_practices or [],
            tags=tags or [],
        )

        self._solutions_cache.append(solution)
        self._save_to_disk()

        if self.use_firestore:
            db = self._get_firestore()
            if db:
                try:
                    db.collection("solution_patterns").document(solution_id).set(asdict(solution))
                except Exception as e:
                    logger.warning(f"Firestore save failed: {e}")

        logger.info(f"Captured solution pattern: {solution_id}")
        return solution_id

    async def find_similar_mistakes(
        self,
        context: Dict[str, Any],
        limit: int = 5,
    ) -> List[MistakeRecord]:
        """Find similar mistakes based on context"""
        # Simple keyword matching (can be enhanced with embeddings)
        context_str = json.dumps(context).lower()
        scored_mistakes = []

        for mistake in self._mistakes_cache:
            mistake_context = json.dumps(mistake.context).lower()
            # Count common words
            context_words = set(context_str.split())
            mistake_words = set(mistake_context.split())
            common = len(context_words & mistake_words)
            if common > 0:
                scored_mistakes.append((common, mistake))

        # Sort by score and return top matches
        scored_mistakes.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored_mistakes[:limit]]

    async def find_solution_patterns(
        self,
        problem_description: str,
        limit: int = 5,
    ) -> List[SolutionRecord]:
        """Find solution patterns for similar problems"""
        problem_words = set(problem_description.lower().split())
        scored_solutions = []

        for solution in self._solutions_cache:
            pattern_words = set(solution.problem_pattern.lower().split())
            common = len(problem_words & pattern_words)
            if common > 0:
                score = common * solution.success_rate
                scored_solutions.append((score, solution))

        scored_solutions.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored_solutions[:limit]]

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "total_interactions": len(self._interactions_cache),
            "total_mistakes": len(self._mistakes_cache),
            "total_solutions": len(self._solutions_cache),
            "storage_path": str(self.storage_dir),
            "firestore_enabled": self.use_firestore,
            "mistake_types": self._get_mistake_type_counts(),
            "success_rate": self._calculate_overall_success_rate(),
        }

    def _get_mistake_type_counts(self) -> Dict[str, int]:
        """Count mistakes by type"""
        counts = {}
        for mistake in self._mistakes_cache:
            counts[mistake.mistake_type] = counts.get(mistake.mistake_type, 0) + 1
        return counts

    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate from interactions"""
        if not self._interactions_cache:
            return 0.0
        successful = sum(1 for i in self._interactions_cache if i.success)
        return successful / len(self._interactions_cache)
