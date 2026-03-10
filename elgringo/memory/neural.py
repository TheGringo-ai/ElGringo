"""
Neural Memory System for El Gringo
Vector embeddings + knowledge graph + outcome learning
"""
import os
import json
import time
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MemoryNode:
    """A node in the knowledge graph"""
    node_id: str
    node_type: str  # solution, mistake, pattern, concept, file, error
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else self.confidence


@dataclass
class MemoryEdge:
    """A relationship between nodes"""
    source_id: str
    target_id: str
    relation: str  # solves, causes, related_to, depends_on, prevents, similar_to
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecallResult:
    """Result from contextual recall"""
    node: MemoryNode
    relevance_score: float
    related_nodes: List[Tuple[MemoryNode, str, float]] = field(default_factory=list)  # (node, relation, weight)
    source: str = "vector"  # vector, graph, hybrid


class NeuralMemory:
    """
    Neural memory with vector embeddings and knowledge graph.
    Lightweight enough for 4GB RAM (uses all-MiniLM-L6-v2 ~80MB).
    """

    def __init__(
        self,
        storage_dir: str = "~/.ai-dev-team/memory",
        collection_name: str = "elgringo_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.storage_dir = Path(storage_dir).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self._embedding_model_name = embedding_model

        # Lazy-loaded components
        self._embedder = None
        self._chroma_client = None
        self._collection = None

        # Knowledge graph (in-memory + persisted)
        self._nodes: Dict[str, MemoryNode] = {}
        self._edges: List[MemoryEdge] = []
        self._graph_file = self.storage_dir / "knowledge_graph.json"

        # Outcome tracking
        self._outcomes_file = self.storage_dir / "outcomes.json"
        self._outcomes: Dict[str, Dict] = {}  # suggestion_id -> {applied, success, feedback}

        # Pattern cache
        self._pattern_clusters: Dict[str, List[str]] = {}  # cluster_label -> [node_ids]

        self._load_graph()
        self._load_outcomes()
        logger.info(f"NeuralMemory initialized: {len(self._nodes)} nodes, {len(self._edges)} edges")

    # ── Lazy Loading (saves RAM until needed) ──

    @property
    def embedder(self):
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(self._embedding_model_name)
                logger.info(f"Loaded embedding model: {self._embedding_model_name}")
            except ImportError:
                logger.warning("sentence-transformers not installed, falling back to hash-based embeddings")
                self._embedder = "fallback"
        return self._embedder

    @property
    def collection(self):
        if self._collection is None:
            try:
                import chromadb
                self._chroma_client = chromadb.PersistentClient(
                    path=str(self.storage_dir / "chromadb")
                )
                self._collection = self._chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"ChromaDB collection '{self.collection_name}' ready ({self._collection.count()} vectors)")
            except ImportError:
                logger.warning("chromadb not installed, vector search unavailable")
                self._collection = "unavailable"
        return self._collection

    # ── Embedding ──

    def _embed(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        if self.embedder == "fallback":
            # Deterministic hash-based pseudo-embedding (384 dims to match MiniLM)
            h = hashlib.sha384(text.encode()).digest()
            return [float(b) / 255.0 for b in h]
        return self.embedder.encode(text, convert_to_tensor=False).tolist()

    def _node_id(self, content: str, node_type: str) -> str:
        """Generate deterministic node ID"""
        return hashlib.md5(f"{node_type}:{content[:200]}".encode()).hexdigest()[:12]

    # ── Store Operations ──

    def store(
        self,
        content: str,
        node_type: str,
        metadata: Optional[Dict] = None,
        relations: Optional[List[Tuple[str, str]]] = None,  # [(target_content, relation)]
        confidence: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Store a memory with embedding and graph connections"""
        node_id = self._node_id(content, node_type)
        meta = metadata or {}
        if tags:
            meta["tags"] = tags

        # Create/update node
        if node_id in self._nodes:
            node = self._nodes[node_id]
            node.updated_at = time.time()
            node.confidence = max(node.confidence, confidence)
            node.metadata.update(meta)
        else:
            node = MemoryNode(
                node_id=node_id,
                node_type=node_type,
                content=content,
                metadata=meta,
                confidence=confidence,
            )
            self._nodes[node_id] = node

        # Store embedding in ChromaDB
        if self.collection != "unavailable":
            try:
                embedding = self._embed(content)
                self.collection.upsert(
                    ids=[node_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[{
                        "node_type": node_type,
                        "confidence": confidence,
                        "tags": json.dumps(tags or []),
                        "created_at": node.created_at,
                    }],
                )
            except Exception as e:
                logger.error(f"ChromaDB upsert failed: {e}")

        # Add graph relations
        if relations:
            for target_content, relation in relations:
                target_id = self._node_id(target_content, "concept")
                if target_id not in self._nodes:
                    self._nodes[target_id] = MemoryNode(
                        node_id=target_id,
                        node_type="concept",
                        content=target_content,
                    )
                self._edges.append(MemoryEdge(
                    source_id=node_id,
                    target_id=target_id,
                    relation=relation,
                ))

        self._save_graph()
        return node_id

    def store_solution(
        self,
        problem: str,
        solution_steps: List[str],
        tags: Optional[List[str]] = None,
        confidence: float = 0.7,
    ) -> str:
        """Store a solution with problem->solution relationship"""
        content = f"Problem: {problem}\nSolution: {'; '.join(solution_steps)}"
        node_id = self.store(
            content=content,
            node_type="solution",
            metadata={"problem": problem, "steps": solution_steps},
            relations=[(problem, "solves")],
            confidence=confidence,
            tags=tags,
        )
        return node_id

    def store_mistake(
        self,
        description: str,
        resolution: str,
        severity: str = "medium",
        prevention: str = "",
        tags: Optional[List[str]] = None,
    ) -> str:
        """Store a mistake with resolution relationship"""
        content = f"Mistake: {description}\nResolution: {resolution}"
        relations = [(resolution, "resolved_by")]
        if prevention:
            relations.append((prevention, "prevented_by"))
        return self.store(
            content=content,
            node_type="mistake",
            metadata={"severity": severity, "resolution": resolution, "prevention": prevention},
            relations=relations,
            confidence=0.8,
            tags=tags,
        )

    def store_pattern(
        self,
        pattern_name: str,
        description: str,
        examples: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Store a recognized pattern"""
        content = f"Pattern: {pattern_name}\n{description}"
        if examples:
            content += f"\nExamples: {'; '.join(examples)}"
        return self.store(
            content=content,
            node_type="pattern",
            metadata={"pattern_name": pattern_name, "examples": examples or []},
            confidence=0.6,
            tags=tags,
        )

    # ── Search / Recall ──

    def search(
        self,
        query: str,
        node_types: Optional[List[str]] = None,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> List[RecallResult]:
        """Semantic search across all memories"""
        results = []

        # Vector search via ChromaDB
        if self.collection != "unavailable" and self.collection.count() > 0:
            try:
                where_filter = None
                if node_types:
                    if len(node_types) == 1:
                        where_filter = {"node_type": node_types[0]}
                    else:
                        where_filter = {"node_type": {"$in": node_types}}

                query_embedding = self._embed(query)
                chroma_results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(limit * 2, self.collection.count()),
                    where=where_filter,
                    include=["documents", "metadatas", "distances"],
                )

                for i, doc_id in enumerate(chroma_results["ids"][0]):
                    distance = chroma_results["distances"][0][i]
                    relevance = 1.0 - distance  # cosine distance -> similarity

                    if doc_id in self._nodes:
                        node = self._nodes[doc_id]
                        if node.confidence >= min_confidence:
                            # Boost by success rate
                            boosted_relevance = relevance * (0.5 + 0.5 * node.success_rate)
                            related = self._get_related_nodes(doc_id, max_depth=1)
                            results.append(RecallResult(
                                node=node,
                                relevance_score=boosted_relevance,
                                related_nodes=related,
                                source="vector",
                            ))
            except Exception as e:
                logger.error(f"Vector search failed: {e}")

        # Graph-based search (keyword fallback + relationship traversal)
        query_lower = query.lower()
        for node_id, node in self._nodes.items():
            if node_types and node.node_type not in node_types:
                continue
            if node.confidence < min_confidence:
                continue
            # Simple keyword relevance
            content_lower = node.content.lower()
            if query_lower in content_lower:
                # Check if already in vector results
                if not any(r.node.node_id == node_id for r in results):
                    keyword_score = 0.5  # Base keyword match score
                    related = self._get_related_nodes(node_id, max_depth=1)
                    results.append(RecallResult(
                        node=node,
                        relevance_score=keyword_score * node.success_rate,
                        related_nodes=related,
                        source="graph",
                    ))

        # Sort by relevance and return top N
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    def contextual_recall(
        self,
        task_description: str,
        file_paths: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        limit: int = 5,
    ) -> List[RecallResult]:
        """Automatically surface relevant memories for current context"""
        # Build rich query from context
        query_parts = [task_description]
        if file_paths:
            extensions = set(Path(f).suffix for f in file_paths)
            query_parts.append(f"files: {', '.join(file_paths[:5])}")
            query_parts.append(f"languages: {', '.join(extensions)}")
        if error_message:
            query_parts.append(f"error: {error_message[:200]}")

        query = " | ".join(query_parts)

        # Search for solutions AND mistakes (prevention)
        solutions = self.search(query, node_types=["solution", "pattern"], limit=limit)
        mistakes = self.search(query, node_types=["mistake"], limit=3)

        # Merge and re-rank
        all_results = solutions + mistakes
        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        return all_results[:limit]

    # ── Outcome Learning ──

    def record_outcome(
        self,
        node_id: str,
        success: bool,
        feedback: str = "",
    ) -> None:
        """Record whether a suggestion worked or not -- adjusts future ranking"""
        if node_id in self._nodes:
            node = self._nodes[node_id]
            node.usage_count += 1
            if success:
                node.success_count += 1
                node.confidence = min(1.0, node.confidence + 0.05)
            else:
                node.failure_count += 1
                node.confidence = max(0.0, node.confidence - 0.1)
            node.updated_at = time.time()

        self._outcomes[node_id] = {
            "success": success,
            "feedback": feedback,
            "timestamp": time.time(),
        }
        self._save_graph()
        self._save_outcomes()
        logger.info(f"Outcome recorded for {node_id}: success={success}")

    # ── Pattern Detection ──

    def detect_patterns(self, min_cluster_size: int = 3) -> List[Dict]:
        """Cluster similar memories to find recurring patterns"""
        if self.collection == "unavailable" or self.collection.count() < min_cluster_size:
            return []

        try:
            from sklearn.cluster import DBSCAN
            import numpy as np

            # Get all embeddings
            all_data = self.collection.get(include=["embeddings", "metadatas", "documents"])
            if not all_data["embeddings"]:
                return []

            embeddings = np.array(all_data["embeddings"])

            # DBSCAN clustering (no need to specify k)
            clustering = DBSCAN(eps=0.3, min_samples=min_cluster_size, metric="cosine")
            labels = clustering.fit_predict(embeddings)

            patterns = []
            for label in set(labels):
                if label == -1:  # noise
                    continue
                indices = [i for i, l in enumerate(labels) if l == label]
                cluster_docs = [all_data["documents"][i] for i in indices]
                cluster_ids = [all_data["ids"][i] for i in indices]

                patterns.append({
                    "cluster_id": int(label),
                    "size": len(indices),
                    "sample_contents": cluster_docs[:3],
                    "node_ids": cluster_ids,
                    "common_type": max(
                        set(all_data["metadatas"][i].get("node_type", "unknown") for i in indices),
                        key=lambda x: sum(1 for i in indices if all_data["metadatas"][i].get("node_type") == x),
                    ),
                })

            return patterns
        except ImportError:
            logger.warning("scikit-learn not installed, pattern detection unavailable")
            return []
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []

    # ── Knowledge Graph Operations ──

    def _get_related_nodes(
        self, node_id: str, max_depth: int = 2
    ) -> List[Tuple[MemoryNode, str, float]]:
        """Traverse graph to find related nodes"""
        related = []
        visited = {node_id}
        queue = [(node_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for edge in self._edges:
                neighbor_id = None
                if edge.source_id == current_id and edge.target_id not in visited:
                    neighbor_id = edge.target_id
                elif edge.target_id == current_id and edge.source_id not in visited:
                    neighbor_id = edge.source_id

                if neighbor_id and neighbor_id in self._nodes:
                    visited.add(neighbor_id)
                    weight = edge.weight / (depth + 1)  # Decay with depth
                    related.append((self._nodes[neighbor_id], edge.relation, weight))
                    queue.append((neighbor_id, depth + 1))

        return related

    def get_graph_stats(self) -> Dict:
        """Return knowledge graph statistics"""
        type_counts: Dict[str, int] = {}
        for node in self._nodes.values():
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1

        relation_counts: Dict[str, int] = {}
        for edge in self._edges:
            relation_counts[edge.relation] = relation_counts.get(edge.relation, 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": type_counts,
            "relation_types": relation_counts,
            "vector_count": self.collection.count() if self.collection != "unavailable" else 0,
            "outcomes_tracked": len(self._outcomes),
        }

    # ── Persistence ──

    def _save_graph(self) -> None:
        """Persist knowledge graph to disk"""
        data = {
            "nodes": {nid: asdict(n) for nid, n in self._nodes.items()},
            "edges": [asdict(e) for e in self._edges],
        }
        self._graph_file.write_text(json.dumps(data, default=str))

    def _load_graph(self) -> None:
        """Load knowledge graph from disk"""
        if self._graph_file.exists():
            try:
                data = json.loads(self._graph_file.read_text())
                self._nodes = {
                    nid: MemoryNode(**ndata) for nid, ndata in data.get("nodes", {}).items()
                }
                self._edges = [MemoryEdge(**edata) for edata in data.get("edges", [])]
            except Exception as e:
                logger.error(f"Failed to load knowledge graph: {e}")
                self._nodes = {}
                self._edges = []

    def _save_outcomes(self) -> None:
        self._outcomes_file.write_text(json.dumps(self._outcomes, default=str))

    def _load_outcomes(self) -> None:
        if self._outcomes_file.exists():
            try:
                self._outcomes = json.loads(self._outcomes_file.read_text())
            except Exception:
                self._outcomes = {}

    # ── Migration Helper ──

    def import_from_legacy(self, legacy_dir: str = "~/.ai-dev-team/memory") -> Dict:
        """Import existing solutions.json and mistakes.json into neural memory"""
        legacy_path = Path(legacy_dir).expanduser()
        imported = {"solutions": 0, "mistakes": 0}

        # Import solutions
        solutions_file = legacy_path / "solutions.json"
        if solutions_file.exists():
            try:
                solutions = json.loads(solutions_file.read_text())
                for sol in solutions:
                    self.store_solution(
                        problem=sol.get("problem_pattern", ""),
                        solution_steps=sol.get("solution_steps", []),
                        tags=sol.get("tags", []),
                        confidence=sol.get("quality_score", 0.5),
                    )
                    imported["solutions"] += 1
            except Exception as e:
                logger.error(f"Failed to import solutions: {e}")

        # Import mistakes
        mistakes_file = legacy_path / "mistakes.json"
        if mistakes_file.exists():
            try:
                mistakes = json.loads(mistakes_file.read_text())
                for mistake in mistakes:
                    self.store_mistake(
                        description=mistake.get("description", ""),
                        resolution=mistake.get("resolution", ""),
                        severity=mistake.get("severity", "medium"),
                        prevention=mistake.get("prevention_strategy", ""),
                        tags=mistake.get("tags", []),
                    )
                    imported["mistakes"] += 1
            except Exception as e:
                logger.error(f"Failed to import mistakes: {e}")

        logger.info(f"Imported {imported['solutions']} solutions, {imported['mistakes']} mistakes")
        return imported
