"""
Memory System - Core memory and knowledge storage
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ── Embedding Search (optional, uses Ollama) ─────────────────────────

class EmbeddingSearch:
    """Vector-based semantic search using Ollama's embedding endpoint.

    Falls back to TF-IDF if Ollama is unavailable or the embedding model
    is not pulled.  Uses cosine similarity over nomic-embed-text vectors.
    """

    MODEL = "nomic-embed-text"
    OLLAMA_URL = "http://localhost:11434/api/embed"

    def __init__(self):
        self._available: Optional[bool] = None
        self._cache: Dict[str, List[float]] = {}

    async def is_available(self) -> bool:
        """Check if Ollama is running and the embedding model is pulled."""
        if self._available is not None:
            return self._available
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(
                    self.OLLAMA_URL,
                    json={"model": self.MODEL, "input": "test"},
                )
                self._available = resp.status_code == 200
        except Exception:
            self._available = False
        logger.info(f"EmbeddingSearch available: {self._available}")
        return self._available

    async def embed(self, text: str) -> Optional[List[float]]:
        """Get embedding vector for a text string."""
        if text in self._cache:
            return self._cache[text]
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.OLLAMA_URL,
                    json={"model": self.MODEL, "input": text[:2000]},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings:
                        vec = embeddings[0]
                        self._cache[text] = vec
                        return vec
        except Exception as e:
            logger.debug(f"Embedding failed: {e}")
        return None

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def rank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10,
    ) -> List[tuple]:
        """Rank documents by semantic similarity to query.

        Returns list of (index, score) tuples sorted by score descending.
        """
        query_vec = await self.embed(query)
        if query_vec is None:
            return []

        scored = []
        for i, doc in enumerate(documents):
            doc_vec = await self.embed(doc[:500])  # Truncate for speed
            if doc_vec is not None:
                score = self.cosine_similarity(query_vec, doc_vec)
                scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


# Global embedding search instance (lazy)
_embedding_search: Optional[EmbeddingSearch] = None


def get_embedding_search() -> EmbeddingSearch:
    global _embedding_search
    if _embedding_search is None:
        _embedding_search = EmbeddingSearch()
    return _embedding_search


def tokenize(text: str) -> List[str]:
    """Simple tokenizer for text matching"""
    # Convert to lowercase and split on non-alphanumeric characters
    return [w for w in re.split(r'[^a-zA-Z0-9]+', text.lower()) if len(w) > 2]


def compute_tf_idf_score(query_tokens: List[str], doc_tokens: List[str], all_docs_tokens: List[List[str]]) -> float:
    """Compute a simplified TF-IDF score"""
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_counter = Counter(doc_tokens)
    total_docs = len(all_docs_tokens) + 1

    score = 0.0
    for token in query_tokens:
        if token in doc_counter:
            # Term frequency in this document
            tf = doc_counter[token] / len(doc_tokens)

            # Inverse document frequency
            docs_with_term = sum(1 for doc in all_docs_tokens if token in doc) + 1
            idf = 1 + (total_docs / docs_with_term)

            score += tf * idf

    return score


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
    access_count: int = 0
    last_accessed: str = ""
    tier: str = "hot"
    compressed: bool = False


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
    access_count: int = 0
    last_accessed: str = ""


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
    access_count: int = 0
    last_accessed: str = ""
    merged_from: List[str] = field(default_factory=list)
    # Quality scoring fields
    quality_score: float = 0.5  # 0-1, starts neutral
    injection_count: int = 0  # times injected into a collaborate call
    positive_ratings: int = 0  # thumbs up from user
    negative_ratings: int = 0  # thumbs down from user


class MemorySystem:
    """
    Comprehensive memory system for AI team learning.

    Supports both local file storage and Firestore for persistence.
    Captures all interactions, mistakes, and solutions for continuous improvement.

    Features:
    - TF-IDF based semantic search
    - Automatic periodic persistence
    - Comprehensive statistics
    - Cross-reference indexing
    """

    def __init__(
        self,
        storage_dir: str = "~/.ai-dev-team/memory",
        use_firestore: bool = False,
        project_id: Optional[str] = None,
        auto_flush_interval: int = 300,  # 5 minutes
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

        # Token caches for TF-IDF search
        self._mistake_tokens: List[List[str]] = []
        self._solution_tokens: List[List[str]] = []

        # Dirty flag for periodic flush
        self._dirty = False
        self._last_flush = time.time()
        self._auto_flush_interval = auto_flush_interval
        self._flush_task: Optional[asyncio.Task] = None

        # Consolidation counter — triggers every 10 interactions
        self._capture_count = 0
        self._consolidate_every = 10

        # Load existing data
        self._load_from_disk()
        self._rebuild_token_caches()

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

            self._dirty = False
            self._last_flush = time.time()
            logger.debug(f"Memory flushed to disk: {self.storage_dir}")

        except Exception as e:
            logger.error(f"Error saving to disk: {e}")

    def _rebuild_token_caches(self):
        """Rebuild token caches for TF-IDF search"""
        self._mistake_tokens = []
        for mistake in self._mistakes_cache:
            tokens = tokenize(f"{mistake.description} {mistake.mistake_type} {' '.join(mistake.tags)}")
            self._mistake_tokens.append(tokens)

        self._solution_tokens = []
        for solution in self._solutions_cache:
            tokens = tokenize(f"{solution.problem_pattern} {' '.join(solution.solution_steps)} {' '.join(solution.tags)}")
            self._solution_tokens.append(tokens)

    @staticmethod
    def _bump_access(record):
        """Increment access count and update last_accessed timestamp"""
        record.access_count += 1
        if hasattr(record, 'injection_count'):
            record.injection_count += 1
        record.last_accessed = datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _jaccard_similarity(tokens_a: List[str], tokens_b: List[str]) -> float:
        """Jaccard similarity between two token lists"""
        if not tokens_a or not tokens_b:
            return 0.0
        set_a, set_b = set(tokens_a), set(tokens_b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    async def start_auto_flush(self):
        """Start background auto-flush task"""
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._auto_flush_loop())
            logger.info("Started memory auto-flush background task")

    async def stop_auto_flush(self):
        """Stop background auto-flush task"""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped memory auto-flush background task")

    async def _auto_flush_loop(self):
        """Background loop for periodic flushing"""
        while True:
            await asyncio.sleep(self._auto_flush_interval)
            if self._dirty:
                self._save_to_disk()
                logger.debug("Auto-flushed memory to disk")

    def mark_dirty(self):
        """Mark memory as having unsaved changes"""
        self._dirty = True

    def flush_now(self):
        """Force immediate flush to disk"""
        self._save_to_disk()

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
        self._capture_count += 1

        # Auto-consolidate every N interactions
        if self._capture_count >= self._consolidate_every:
            self._consolidate()
            self._capture_count = 0

        self.mark_dirty()
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
        # Update token cache for this mistake
        tokens = tokenize(f"{mistake.description} {mistake.mistake_type} {' '.join(mistake.tags)}")
        self._mistake_tokens.append(tokens)
        self.mark_dirty()
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
        # Update token cache for this solution
        tokens = tokenize(f"{solution.problem_pattern} {' '.join(solution.solution_steps)} {' '.join(solution.tags)}")
        self._solution_tokens.append(tokens)
        self.mark_dirty()
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
        """
        Find similar mistakes based on context using TF-IDF scoring.

        Args:
            context: Context dictionary (can contain 'query', 'task_type', 'project', etc.)
            limit: Maximum number of results

        Returns:
            List of similar MistakeRecord objects sorted by relevance
        """
        if not self._mistakes_cache:
            return []

        # Build query from context
        query_parts = []
        if isinstance(context, dict):
            query_parts.append(context.get("query", ""))
            query_parts.append(context.get("task_type", ""))
            query_parts.append(context.get("project", ""))
            query_parts.append(json.dumps(context))
        else:
            query_parts.append(str(context))

        query_str = " ".join(query_parts)
        query_tokens = tokenize(query_str)

        if not query_tokens:
            # Fall back to returning most recent mistakes
            return self._mistakes_cache[-limit:]

        # Score each mistake using TF-IDF
        scored_mistakes = []
        for i, mistake in enumerate(self._mistakes_cache):
            if i < len(self._mistake_tokens):
                doc_tokens = self._mistake_tokens[i]
            else:
                doc_tokens = tokenize(f"{mistake.description} {mistake.mistake_type}")

            score = compute_tf_idf_score(query_tokens, doc_tokens, self._mistake_tokens)

            # Boost by severity
            severity_boost = {"critical": 1.5, "high": 1.3, "medium": 1.0, "low": 0.8}
            score *= severity_boost.get(mistake.severity, 1.0)

            if score > 0:
                scored_mistakes.append((score, mistake))

        # Sort by score and return top matches
        scored_mistakes.sort(key=lambda x: x[0], reverse=True)
        results = [m for _, m in scored_mistakes[:limit]]
        for r in results:
            self._bump_access(r)
        return results

    async def find_solution_patterns(
        self,
        problem_description: str,
        limit: int = 5,
    ) -> List[SolutionRecord]:
        """
        Find solution patterns for similar problems using TF-IDF scoring.

        Args:
            problem_description: Description of the problem to find solutions for
            limit: Maximum number of results

        Returns:
            List of SolutionRecord objects sorted by relevance
        """
        if not self._solutions_cache:
            return []

        query_tokens = tokenize(problem_description)

        if not query_tokens:
            # Fall back to returning highest success rate solutions
            return sorted(self._solutions_cache, key=lambda s: s.success_rate, reverse=True)[:limit]

        # Score each solution using TF-IDF
        scored_solutions = []
        for i, solution in enumerate(self._solutions_cache):
            if i < len(self._solution_tokens):
                doc_tokens = self._solution_tokens[i]
            else:
                doc_tokens = tokenize(f"{solution.problem_pattern} {' '.join(solution.solution_steps)}")

            score = compute_tf_idf_score(query_tokens, doc_tokens, self._solution_tokens)

            # Weight by success rate
            score *= solution.success_rate

            # Boost by quality score (0.5-1.5x range, neutral at 1.0)
            quality_boost = 0.5 + solution.quality_score
            score *= quality_boost

            # Boost by access count (up to 1.5x for frequently accessed)
            access_boost = min(1.0 + (solution.access_count * 0.05), 1.5)
            score *= access_boost

            if score > 0:
                scored_solutions.append((score, solution))

        scored_solutions.sort(key=lambda x: x[0], reverse=True)
        results = [s for _, s in scored_solutions[:limit]]
        for r in results:
            self._bump_access(r)
        return results

    # --- Feedback & Quality Scoring ---

    # Maps task_id -> list of solution_ids that were injected for that task
    _injection_map: Dict[str, List[str]] = {}

    def track_injection(self, task_id: str, solution_ids: List[str]):
        """Record which solutions were injected for a given task."""
        self._injection_map[task_id] = solution_ids
        # Keep map bounded (last 200 tasks)
        if len(self._injection_map) > 200:
            oldest = list(self._injection_map.keys())[0]
            del self._injection_map[oldest]

    def rate_interaction(
        self,
        task_id: str,
        rating: str,  # "positive" or "negative"
        note: str = "",
    ) -> Dict[str, Any]:
        """
        Rate a collaborate output. Propagates rating to all solutions
        that were injected for that task.

        Returns summary of which solutions were affected.
        """
        solution_ids = self._injection_map.get(task_id, [])
        affected = []

        for sol in self._solutions_cache:
            if sol.solution_id in solution_ids:
                if rating == "positive":
                    sol.positive_ratings += 1
                else:
                    sol.negative_ratings += 1
                # Recalculate quality score
                sol.quality_score = self._compute_quality_score(sol)
                affected.append({
                    "solution_id": sol.solution_id,
                    "pattern": sol.problem_pattern[:80],
                    "new_quality": round(sol.quality_score, 3),
                })

        if affected:
            self.mark_dirty()
            self._save_to_disk()

        return {
            "task_id": task_id,
            "rating": rating,
            "note": note,
            "solutions_affected": len(affected),
            "details": affected,
        }

    @staticmethod
    def _compute_quality_score(sol: SolutionRecord) -> float:
        """
        Compute quality score (0-1) for a solution based on:
        - User ratings (50%): positive / (positive + negative)
        - Usage signal (30%): injection count normalized
        - Content quality (20%): has best_practices, tags, reasonable steps
        """
        # Rating component
        total_ratings = sol.positive_ratings + sol.negative_ratings
        if total_ratings > 0:
            rating_score = sol.positive_ratings / total_ratings
        else:
            rating_score = 0.5  # Neutral if no ratings

        # Usage component (more injections = more trusted, caps at 1.0)
        usage_score = min(sol.injection_count / 10.0, 1.0) if sol.injection_count > 0 else 0.3

        # Content quality component
        content_score = 0.0
        if sol.best_practices:
            content_score += 0.5
        if sol.tags:
            content_score += 0.2
        if 1 <= len(sol.solution_steps) <= 6:
            content_score += 0.3

        return (rating_score * 0.5) + (usage_score * 0.3) + (content_score * 0.2)

    def decay_old_patterns(self, days_threshold: int = 30) -> int:
        """
        Decay quality scores for patterns not accessed in N days.
        Returns count of decayed patterns.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_threshold)).isoformat()
        decayed = 0

        for sol in self._solutions_cache:
            if sol.last_accessed and sol.last_accessed < cutoff:
                # Decay by 10% per cycle
                sol.quality_score = max(0.1, sol.quality_score * 0.9)
                decayed += 1

        if decayed:
            self.mark_dirty()
            self._save_to_disk()

        return decayed

    def auto_prune(self, min_quality: float = 0.15, min_age_days: int = 14) -> int:
        """
        Remove solutions that are old AND have very low quality scores.
        Never removes solutions with positive ratings or best_practices.
        Returns count of pruned solutions.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=min_age_days)).isoformat()
        keep = []
        pruned = 0

        for sol in self._solutions_cache:
            # Never prune curated or positively-rated solutions
            if sol.positive_ratings > 0 or sol.best_practices:
                keep.append(sol)
            elif sol.quality_score < min_quality and sol.timestamp < cutoff:
                pruned += 1
            else:
                keep.append(sol)

        if pruned:
            self._solutions_cache = keep
            # Rebuild TF-IDF index
            self._solution_tokens = [
                tokenize(f"{s.problem_pattern} {' '.join(s.solution_steps)} {' '.join(s.tags)}")
                for s in keep
            ]
            self.mark_dirty()
            self._save_to_disk()

        return pruned

    def get_quality_report(self) -> Dict[str, Any]:
        """Get quality distribution of stored solutions."""
        if not self._solutions_cache:
            return {"total": 0}

        scores = [s.quality_score for s in self._solutions_cache]
        rated = [s for s in self._solutions_cache if s.positive_ratings + s.negative_ratings > 0]
        curated = [s for s in self._solutions_cache if s.best_practices]

        return {
            "total": len(self._solutions_cache),
            "avg_quality": round(sum(scores) / len(scores), 3),
            "high_quality": len([s for s in scores if s >= 0.7]),
            "medium_quality": len([s for s in scores if 0.4 <= s < 0.7]),
            "low_quality": len([s for s in scores if s < 0.4]),
            "user_rated": len(rated),
            "curated_with_practices": len(curated),
            "top_5": [
                {
                    "pattern": s.problem_pattern[:60],
                    "quality": round(s.quality_score, 3),
                    "ratings": f"+{s.positive_ratings}/-{s.negative_ratings}",
                    "injections": s.injection_count,
                }
                for s in sorted(self._solutions_cache, key=lambda x: x.quality_score, reverse=True)[:5]
            ],
        }

    async def search_all(
        self,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Search across all memory stores (mistakes, solutions, interactions).

        Uses embedding-based search (Ollama nomic-embed-text) when available,
        falls back to TF-IDF otherwise.

        Args:
            query: Search query
            limit: Maximum results per category

        Returns:
            Dictionary with results from each category
        """
        mistakes = await self.find_similar_mistakes({"query": query}, limit=limit)
        solutions = await self.find_solution_patterns(query, limit=limit)

        # Search interactions using embeddings if available, else TF-IDF
        search_method = "tf-idf"
        scored_interactions = []

        embedder = get_embedding_search()
        use_embeddings = await embedder.is_available()

        if use_embeddings and self._interactions_cache:
            search_method = "embedding"
            docs = [
                f"{i.prompt} {i.final_answer}" for i in self._interactions_cache
            ]
            ranked = await embedder.rank(query, docs, top_k=limit)
            for idx, score in ranked:
                if score > 0.3:  # Cosine similarity threshold
                    interaction = self._interactions_cache[idx]
                    tier_boost = {"hot": 1.0, "warm": 1.1, "cold": 0.9}
                    boosted = score * tier_boost.get(interaction.tier, 1.0)
                    scored_interactions.append((boosted, interaction))
        else:
            # Fallback to TF-IDF
            query_tokens = tokenize(query)
            for interaction in self._interactions_cache:
                doc_tokens = tokenize(f"{interaction.prompt} {interaction.final_answer}")
                score = compute_tf_idf_score(query_tokens, doc_tokens, [])
                if score > 0:
                    tier_boost = {"hot": 1.0, "warm": 1.3, "cold": 0.7}
                    score *= tier_boost.get(interaction.tier, 1.0)
                    scored_interactions.append((score, interaction))

        scored_interactions.sort(key=lambda x: x[0], reverse=True)
        top_interactions = [i for _, i in scored_interactions[:limit]]
        for r in top_interactions:
            self._bump_access(r)

        return {
            "mistakes": mistakes,
            "solutions": solutions,
            "interactions": top_interactions,
            "query": query,
            "search_method": search_method,
            "total_results": len(mistakes) + len(solutions) + len(top_interactions),
        }

    def consolidate(self) -> Dict[str, Any]:
        """Public interface: run consolidation and save results"""
        report = self._consolidate()
        self._save_to_disk()
        return report

    def _consolidate(self) -> Dict[str, Any]:
        """
        Consolidation engine — dedup solutions, prune trivial entries,
        tier interactions, compress cold data, rebuild caches.
        """
        report = {
            "solutions_merged": 0,
            "solutions_pruned": 0,
            "interactions_compressed": 0,
            "tier_counts": {"hot": 0, "warm": 0, "cold": 0},
        }

        # --- 1. Deduplicate solutions (Jaccard ≥ 0.7) ---
        if len(self._solutions_cache) > 1:
            token_lists = [
                tokenize(f"{s.problem_pattern} {' '.join(s.solution_steps)}")
                for s in self._solutions_cache
            ]
            to_remove: Set[int] = set()
            for i in range(len(self._solutions_cache)):
                if i in to_remove:
                    continue
                for j in range(i + 1, len(self._solutions_cache)):
                    if j in to_remove:
                        continue
                    sim = self._jaccard_similarity(token_lists[i], token_lists[j])
                    if sim >= 0.7:
                        winner, loser = (i, j) if (
                            self._solutions_cache[i].success_rate
                            >= self._solutions_cache[j].success_rate
                        ) else (j, i)
                        w = self._solutions_cache[winner]
                        l = self._solutions_cache[loser]
                        # Merge unique steps from loser
                        existing = set(w.solution_steps)
                        for step in l.solution_steps:
                            if step not in existing:
                                w.solution_steps.append(step)
                        # Merge projects
                        for p in l.projects_used:
                            if p not in w.projects_used:
                                w.projects_used.append(p)
                        w.merged_from.append(l.solution_id)
                        w.access_count += l.access_count
                        to_remove.add(loser)
                        report["solutions_merged"] += 1

            if to_remove:
                self._solutions_cache = [
                    s for idx, s in enumerate(self._solutions_cache)
                    if idx not in to_remove
                ]

        # --- 2. Prune trivial solutions ---
        now = datetime.now(timezone.utc)
        kept_solutions = []
        for sol in self._solutions_cache:
            pattern_tokens = tokenize(sol.problem_pattern)
            is_trivial = len(pattern_tokens) <= 5
            never_accessed = sol.access_count == 0

            age_days = 0
            try:
                ts = datetime.fromisoformat(sol.timestamp.replace('Z', '+00:00'))
                age_days = (now - ts).days
            except (ValueError, AttributeError):
                pass

            if is_trivial and never_accessed and age_days > 14:
                report["solutions_pruned"] += 1
                logger.info(f"Pruned trivial solution: {sol.solution_id} ({sol.problem_pattern[:50]})")
            else:
                kept_solutions.append(sol)
        self._solutions_cache = kept_solutions

        # --- 3 & 4. Tier interactions and compress cold ---
        for interaction in self._interactions_cache:
            age_days = 0
            try:
                ts = datetime.fromisoformat(interaction.timestamp.replace('Z', '+00:00'))
                age_days = (now - ts).days
            except (ValueError, AttributeError):
                pass

            if age_days <= 7:
                interaction.tier = "hot"
            elif interaction.access_count >= 2 or (
                interaction.confidence >= 0.85 and interaction.success
            ):
                interaction.tier = "warm"
            else:
                interaction.tier = "cold"
                # Compress cold interactions
                if not interaction.compressed:
                    interaction.responses = [
                        {"agent": r.get("agent", ""), "success": r.get("success", False)}
                        for r in interaction.responses
                    ]
                    if len(interaction.final_answer) > 200:
                        interaction.final_answer = interaction.final_answer[:200] + "..."
                    interaction.context = ""
                    interaction.compressed = True
                    report["interactions_compressed"] += 1

            report["tier_counts"][interaction.tier] += 1

        # --- 5. Rebuild TF-IDF caches ---
        self._rebuild_token_caches()

        logger.info(
            f"Consolidation complete: {report['solutions_merged']} merged, "
            f"{report['solutions_pruned']} pruned, "
            f"{report['interactions_compressed']} compressed"
        )
        return report

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory system statistics"""
        # Calculate time-based metrics
        interactions_24h = 0
        interactions_7d = 0
        now = datetime.now(timezone.utc)

        for interaction in self._interactions_cache:
            try:
                ts = datetime.fromisoformat(interaction.timestamp.replace('Z', '+00:00'))
                delta = (now - ts).total_seconds()
                if delta < 86400:  # 24 hours
                    interactions_24h += 1
                if delta < 604800:  # 7 days
                    interactions_7d += 1
            except (ValueError, AttributeError):
                pass

        # Get project distribution
        projects = Counter(i.project for i in self._interactions_cache)

        # Get agent usage
        agent_usage = Counter()
        for interaction in self._interactions_cache:
            for agent in interaction.agents_used:
                agent_usage[agent] += 1

        return {
            "total_interactions": len(self._interactions_cache),
            "total_mistakes": len(self._mistakes_cache),
            "total_solutions": len(self._solutions_cache),
            "storage_path": str(self.storage_dir),
            "firestore_enabled": self.use_firestore,
            "mistake_types": self._get_mistake_type_counts(),
            "mistake_severities": self._get_severity_counts(),
            "success_rate": self._calculate_overall_success_rate(),
            "average_confidence": self._calculate_average_confidence(),
            "interactions_last_24h": interactions_24h,
            "interactions_last_7d": interactions_7d,
            "projects": dict(projects.most_common(10)),
            "agent_usage": dict(agent_usage.most_common(10)),
            "solution_success_rates": self._get_solution_success_rates(),
            "last_flush": datetime.fromtimestamp(self._last_flush).isoformat() if self._last_flush else None,
            "has_unsaved_changes": self._dirty,
        }

    def _get_mistake_type_counts(self) -> Dict[str, int]:
        """Count mistakes by type"""
        counts = {}
        for mistake in self._mistakes_cache:
            counts[mistake.mistake_type] = counts.get(mistake.mistake_type, 0) + 1
        return counts

    def _get_severity_counts(self) -> Dict[str, int]:
        """Count mistakes by severity"""
        counts = {}
        for mistake in self._mistakes_cache:
            counts[mistake.severity] = counts.get(mistake.severity, 0) + 1
        return counts

    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate from interactions"""
        if not self._interactions_cache:
            return 0.0
        successful = sum(1 for i in self._interactions_cache if i.success)
        return round(successful / len(self._interactions_cache), 3)

    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence score across interactions"""
        if not self._interactions_cache:
            return 0.0
        total_confidence = sum(i.confidence for i in self._interactions_cache)
        return round(total_confidence / len(self._interactions_cache), 3)

    def _get_solution_success_rates(self) -> Dict[str, float]:
        """Get success rate statistics for solutions"""
        if not self._solutions_cache:
            return {"average": 0.0, "min": 0.0, "max": 0.0}

        rates = [s.success_rate for s in self._solutions_cache]
        return {
            "average": round(sum(rates) / len(rates), 3),
            "min": round(min(rates), 3),
            "max": round(max(rates), 3),
            "count_above_90": sum(1 for r in rates if r >= 0.9),
        }

    def get_recent_activity(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of recent memory activity"""
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        recent_interactions = []
        recent_mistakes = []
        recent_solutions = []

        for i in self._interactions_cache:
            try:
                ts = datetime.fromisoformat(i.timestamp.replace('Z', '+00:00')).timestamp()
                if ts >= cutoff:
                    recent_interactions.append(i)
            except (ValueError, AttributeError):
                pass

        for m in self._mistakes_cache:
            try:
                ts = datetime.fromisoformat(m.timestamp.replace('Z', '+00:00')).timestamp()
                if ts >= cutoff:
                    recent_mistakes.append(m)
            except (ValueError, AttributeError):
                pass

        for s in self._solutions_cache:
            try:
                ts = datetime.fromisoformat(s.timestamp.replace('Z', '+00:00')).timestamp()
                if ts >= cutoff:
                    recent_solutions.append(s)
            except (ValueError, AttributeError):
                pass

        return {
            "hours": hours,
            "interactions": len(recent_interactions),
            "mistakes": len(recent_mistakes),
            "solutions": len(recent_solutions),
            "success_rate": (
                sum(1 for i in recent_interactions if i.success) / len(recent_interactions)
                if recent_interactions else 0.0
            ),
        }
