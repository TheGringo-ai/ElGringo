"""
Universal RAG (Retrieval-Augmented Generation) System
======================================================

Comprehensive knowledge retrieval system that indexes and searches across:
- Code snippets and patterns from CodingKnowledgeHub
- Error fixes and solutions
- API documentation
- Project files and documentation
- External documentation (Firebase, React, Python, etc.)
- Conversation history and learnings

Usage:
    rag = UniversalRAG()

    # Index knowledge sources
    rag.index_coding_hub()
    rag.index_project_files("/path/to/project")
    rag.index_documentation("firebase")

    # Search for relevant context
    results = rag.search("how to batch write to Firestore")

    # Generate context for AI prompts
    context = rag.get_context_for_task("implement user authentication with Firebase")
"""

import hashlib
import json
import logging
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from threading import Lock
from time import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class RAGCache:
    """
    Thread-safe LRU cache with TTL for RAG search results.

    Features:
    - Configurable max size and TTL
    - Thread-safe operations
    - Automatic cleanup of expired entries
    - Hit/miss statistics
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, timestamp)
        self._access_order: List[str] = []  # LRU tracking
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, **kwargs) -> str:
        """Create a cache key from query and parameters."""
        key_parts = [query]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    def get(self, query: str, **kwargs) -> Optional[Any]:
        """Get a cached result if valid."""
        key = self._make_key(query, **kwargs)

        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time() - timestamp < self.ttl_seconds:
                    # Move to end of access order (most recent)
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    self._hits += 1
                    return value
                else:
                    # Expired, remove it
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)

            self._misses += 1
            return None

    def set(self, query: str, value: Any, **kwargs):
        """Cache a result."""
        key = self._make_key(query, **kwargs)

        with self._lock:
            # Evict if at capacity
            while len(self._cache) >= self.max_size and self._access_order:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    del self._cache[oldest_key]

            self._cache[key] = (value, time())
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

    def clear(self):
        """Clear all cached results."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0,
                "ttl_seconds": self.ttl_seconds,
            }


@dataclass
class Document:
    """A document in the RAG system."""
    doc_id: str
    content: str
    source_type: str  # snippet, error_fix, pattern, api, file, documentation, conversation
    source_path: Optional[str] = None
    title: str = ""
    language: Optional[str] = None
    framework: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    indexed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SearchResult:
    """A search result from the RAG system."""
    document: Document
    score: float
    matched_terms: List[str] = field(default_factory=list)
    snippet: str = ""  # Relevant excerpt


@dataclass
class RAGContext:
    """Context generated for AI prompts."""
    query: str
    results: List[SearchResult]
    context_text: str
    sources: List[str]
    total_tokens_estimate: int


class TFIDFIndex:
    """TF-IDF based search index."""

    def __init__(self):
        self._documents: Dict[str, Document] = {}
        self._term_doc_freq: Dict[str, Set[str]] = defaultdict(set)  # term -> doc_ids
        self._doc_term_freq: Dict[str, Counter] = {}  # doc_id -> term frequencies
        self._doc_lengths: Dict[str, int] = {}
        self._avg_doc_length: float = 0.0
        self._total_docs: int = 0

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        # Keep underscores for code identifiers
        tokens = re.findall(r'[a-z0-9_]+', text)
        # Filter short tokens but keep important ones
        return [t for t in tokens if len(t) > 1 or t in {'i', 'a'}]

    def _compute_tf(self, term: str, doc_id: str) -> float:
        """Compute term frequency."""
        if doc_id not in self._doc_term_freq:
            return 0.0
        count = self._doc_term_freq[doc_id].get(term, 0)
        total = sum(self._doc_term_freq[doc_id].values())
        return count / total if total > 0 else 0.0

    def _compute_idf(self, term: str) -> float:
        """Compute inverse document frequency."""
        if term not in self._term_doc_freq:
            return 0.0
        doc_freq = len(self._term_doc_freq[term])
        if doc_freq == 0:
            return 0.0
        return math.log((self._total_docs + 1) / (doc_freq + 1)) + 1

    def add_document(self, doc: Document):
        """Add a document to the index."""
        # Combine searchable text
        searchable = f"{doc.title} {doc.content} {' '.join(doc.tags)}"
        tokens = self._tokenize(searchable)

        self._documents[doc.doc_id] = doc
        self._doc_term_freq[doc.doc_id] = Counter(tokens)
        self._doc_lengths[doc.doc_id] = len(tokens)

        for term in set(tokens):
            self._term_doc_freq[term].add(doc.doc_id)

        self._total_docs = len(self._documents)
        self._avg_doc_length = sum(self._doc_lengths.values()) / self._total_docs if self._total_docs > 0 else 0

    def remove_document(self, doc_id: str):
        """Remove a document from the index."""
        if doc_id not in self._documents:
            return

        # Remove from term index
        for term in self._doc_term_freq.get(doc_id, {}).keys():
            self._term_doc_freq[term].discard(doc_id)
            if not self._term_doc_freq[term]:
                del self._term_doc_freq[term]

        del self._documents[doc_id]
        del self._doc_term_freq[doc_id]
        del self._doc_lengths[doc_id]

        self._total_docs = len(self._documents)
        self._avg_doc_length = sum(self._doc_lengths.values()) / self._total_docs if self._total_docs > 0 else 0

    def search(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[Tuple[str, float, List[str]]]:
        """Search the index using BM25-like scoring."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # BM25 parameters
        k1 = 1.5
        b = 0.75

        scores: Dict[str, float] = defaultdict(float)
        matched_terms: Dict[str, List[str]] = defaultdict(list)

        for term in query_tokens:
            idf = self._compute_idf(term)

            for doc_id in self._term_doc_freq.get(term, set()):
                # Apply filters
                if filters:
                    doc = self._documents[doc_id]
                    skip = False
                    for key, value in filters.items():
                        doc_value = getattr(doc, key, None) or doc.metadata.get(key)
                        if value is not None and doc_value != value:
                            skip = True
                            break
                    if skip:
                        continue

                tf = self._doc_term_freq[doc_id].get(term, 0)
                doc_len = self._doc_lengths[doc_id]

                # BM25 formula
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / self._avg_doc_length))
                score = idf * (numerator / denominator) if denominator > 0 else 0

                scores[doc_id] += score
                if term not in matched_terms[doc_id]:
                    matched_terms[doc_id].append(term)

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return [(doc_id, score, matched_terms[doc_id]) for doc_id, score in ranked[:limit]]

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self._documents.get(doc_id)

    def get_all_documents(self) -> List[Document]:
        """Get all documents."""
        return list(self._documents.values())

    def __len__(self) -> int:
        return self._total_docs


class UniversalRAG:
    """
    Universal Retrieval-Augmented Generation system.

    Indexes and searches across all knowledge sources for the AI team.
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/rag", cache_size: int = 1000, cache_ttl: int = 300):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._index = TFIDFIndex()
        self._source_stats: Dict[str, int] = defaultdict(int)

        # Initialize search cache
        self._cache = RAGCache(max_size=cache_size, ttl_seconds=cache_ttl)

        # Load existing index
        self._load_index()

    def _generate_doc_id(self, content: str, source_type: str) -> str:
        """Generate unique document ID."""
        hash_input = f"{source_type}:{content[:500]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _load_index(self):
        """Load index from disk."""
        index_file = self.storage_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file) as f:
                    data = json.load(f)

                for doc_data in data.get("documents", []):
                    doc = Document(**doc_data)
                    self._index.add_document(doc)
                    self._source_stats[doc.source_type] += 1

                logger.info(f"Loaded RAG index: {len(self._index)} documents")
            except Exception as e:
                logger.warning(f"Error loading RAG index: {e}")

    def _save_index(self):
        """Save index to disk."""
        try:
            index_file = self.storage_dir / "index.json"
            data = {
                "documents": [asdict(doc) for doc in self._index.get_all_documents()],
                "stats": dict(self._source_stats),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(index_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving RAG index: {e}")

    # ==================== Indexing Methods ====================

    def index_document(self, doc: Document) -> str:
        """Index a single document."""
        self._index.add_document(doc)
        self._source_stats[doc.source_type] += 1
        self._save_index()
        return doc.doc_id

    def index_text(
        self,
        content: str,
        source_type: str,
        title: str = "",
        language: str = None,
        framework: str = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        source_path: str = None,
    ) -> str:
        """Index arbitrary text content."""
        doc_id = self._generate_doc_id(content, source_type)

        doc = Document(
            doc_id=doc_id,
            content=content,
            source_type=source_type,
            source_path=source_path,
            title=title,
            language=language,
            framework=framework,
            tags=tags or [],
            metadata=metadata or {},
        )

        return self.index_document(doc)

    def index_coding_hub(self, coding_hub=None):
        """Index all knowledge from CodingKnowledgeHub."""
        if coding_hub is None:
            from .coding_hub import get_coding_hub
            coding_hub = get_coding_hub()

        indexed = 0

        # Index code snippets
        for snippet in coding_hub._snippets:
            doc = Document(
                doc_id=f"snippet_{snippet.snippet_id}",
                content=f"{snippet.description}\n\n{snippet.code}",
                source_type="snippet",
                title=snippet.title,
                language=snippet.language,
                tags=snippet.tags + [snippet.category],
                metadata={
                    "category": snippet.category,
                    "use_count": snippet.use_count,
                    "success_count": snippet.success_count,
                },
            )
            self._index.add_document(doc)
            indexed += 1

        # Index error fixes
        for fix in coding_hub._error_fixes:
            doc = Document(
                doc_id=f"error_fix_{fix.fix_id}",
                content=f"Error: {fix.error_pattern}\n\nFix: {'; '.join(fix.fix_steps)}\n\n{fix.explanation}",
                source_type="error_fix",
                title=f"Fix for: {fix.error_pattern[:50]}",
                language=fix.language,
                tags=fix.tags + [fix.error_type],
                metadata={
                    "error_type": fix.error_type,
                    "success_count": fix.success_count,
                    "fix_code": fix.fix_code,
                },
            )
            self._index.add_document(doc)
            indexed += 1

        # Index framework patterns
        for pattern in coding_hub._patterns:
            doc = Document(
                doc_id=f"pattern_{pattern.pattern_id}",
                content=f"{pattern.description}\n\nTemplate:\n{pattern.code_template}\n\nUse cases: {', '.join(pattern.use_cases)}",
                source_type="pattern",
                title=pattern.pattern_name,
                framework=pattern.framework,
                tags=pattern.use_cases,
                metadata={
                    "anti_patterns": pattern.anti_patterns,
                    "related_patterns": pattern.related_patterns,
                },
            )
            self._index.add_document(doc)
            indexed += 1

        # Index API knowledge
        for api in coding_hub._api_knowledge:
            doc = Document(
                doc_id=f"api_{api.api_id}",
                content=f"{api.description}\n\nExample:\n{api.example_code}\n\nTips: {'; '.join(api.tips)}",
                source_type="api",
                title=f"{api.api_name}: {api.endpoint_or_method}",
                tags=[api.api_name] + api.common_errors,
                metadata={
                    "parameters": api.parameters,
                    "common_errors": api.common_errors,
                },
            )
            self._index.add_document(doc)
            indexed += 1

        self._source_stats["snippet"] = len(coding_hub._snippets)
        self._source_stats["error_fix"] = len(coding_hub._error_fixes)
        self._source_stats["pattern"] = len(coding_hub._patterns)
        self._source_stats["api"] = len(coding_hub._api_knowledge)

        self._save_index()
        logger.info(f"Indexed {indexed} items from CodingKnowledgeHub")

        return indexed

    def index_project_files(
        self,
        project_path: str,
        extensions: List[str] = None,
        exclude_patterns: List[str] = None,
        max_file_size: int = 100000,
    ) -> int:
        """Index source files from a project directory."""
        if extensions is None:
            extensions = [".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".rst", ".txt"]

        if exclude_patterns is None:
            exclude_patterns = [
                "node_modules", "__pycache__", ".git", "dist", "build",
                "venv", ".venv", "env", ".env", "*.min.js", "*.bundle.js"
            ]

        project_path = Path(project_path)
        indexed = 0

        for ext in extensions:
            for file_path in project_path.rglob(f"*{ext}"):
                # Check exclusions
                path_str = str(file_path)
                if any(pattern in path_str for pattern in exclude_patterns):
                    continue

                try:
                    # Check file size
                    if file_path.stat().st_size > max_file_size:
                        continue

                    content = file_path.read_text(encoding="utf-8", errors="ignore")

                    # Detect language
                    lang_map = {
                        ".py": "python",
                        ".ts": "typescript",
                        ".tsx": "typescript",
                        ".js": "javascript",
                        ".jsx": "javascript",
                        ".md": "markdown",
                        ".rst": "restructuredtext",
                    }
                    language = lang_map.get(ext, "text")

                    doc = Document(
                        doc_id=self._generate_doc_id(content, "file"),
                        content=content,
                        source_type="file",
                        source_path=str(file_path.relative_to(project_path)),
                        title=file_path.name,
                        language=language,
                        metadata={
                            "project": project_path.name,
                            "extension": ext,
                        },
                    )

                    self._index.add_document(doc)
                    indexed += 1

                except Exception as e:
                    logger.warning(f"Error indexing {file_path}: {e}")

        self._source_stats["file"] = indexed
        self._save_index()
        logger.info(f"Indexed {indexed} files from {project_path}")

        return indexed

    def index_documentation(
        self,
        name: str,
        content: str,
        doc_type: str = "external",
        url: str = None,
        tags: List[str] = None,
    ) -> str:
        """Index external documentation."""
        doc = Document(
            doc_id=self._generate_doc_id(content, "documentation"),
            content=content,
            source_type="documentation",
            title=name,
            tags=tags or [name.lower()],
            metadata={
                "doc_type": doc_type,
                "url": url,
            },
        )

        self._index.add_document(doc)
        self._source_stats["documentation"] += 1
        self._save_index()

        return doc.doc_id

    def index_conversation(
        self,
        prompt: str,
        response: str,
        outcome: str = "success",
        task_type: str = None,
        tags: List[str] = None,
    ) -> str:
        """Index a conversation for future reference."""
        content = f"Question: {prompt}\n\nAnswer: {response}"

        doc = Document(
            doc_id=self._generate_doc_id(content, "conversation"),
            content=content,
            source_type="conversation",
            title=prompt[:100],
            tags=tags or [],
            metadata={
                "outcome": outcome,
                "task_type": task_type,
            },
        )

        self._index.add_document(doc)
        self._source_stats["conversation"] += 1
        self._save_index()

        return doc.doc_id

    # ==================== Search Methods ====================

    def search(
        self,
        query: str,
        limit: int = 10,
        source_types: List[str] = None,
        language: str = None,
        framework: str = None,
        min_score: float = 0.1,
        use_cache: bool = True,
    ) -> List[SearchResult]:
        """
        Search across all indexed knowledge.

        Args:
            query: Search query
            limit: Maximum results to return
            source_types: Filter by source types
            language: Filter by language
            framework: Filter by framework
            min_score: Minimum relevance score
            use_cache: Whether to use cached results

        Returns:
            List of SearchResults ordered by relevance
        """
        # Check cache first
        cache_key_args = {
            "limit": limit,
            "source_types": tuple(source_types) if source_types else None,
            "language": language,
            "framework": framework,
            "min_score": min_score,
        }

        if use_cache:
            cached = self._cache.get(query, **cache_key_args)
            if cached is not None:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached

        # Build filters
        filters = {}
        if language:
            filters["language"] = language
        if framework:
            filters["framework"] = framework

        # Search index
        raw_results = self._index.search(query, limit=limit * 2, filters=filters if filters else None)

        results = []
        for doc_id, score, matched_terms in raw_results:
            if score < min_score:
                continue

            doc = self._index.get_document(doc_id)
            if not doc:
                continue

            # Filter by source type
            if source_types and doc.source_type not in source_types:
                continue

            # Generate snippet
            snippet = self._extract_snippet(doc.content, matched_terms)

            results.append(SearchResult(
                document=doc,
                score=score,
                matched_terms=matched_terms,
                snippet=snippet,
            ))

            if len(results) >= limit:
                break

        # Cache the results
        if use_cache:
            self._cache.set(query, results, **cache_key_args)

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get RAG cache statistics."""
        return self._cache.stats()

    def clear_cache(self):
        """Clear the search cache."""
        self._cache.clear()

    def search_similar(self, content: str, limit: int = 5) -> List[SearchResult]:
        """Find documents similar to given content."""
        # Use first 500 chars as query
        query = content[:500]
        return self.search(query, limit=limit)

    def search_by_error(self, error_message: str, language: str = None) -> List[SearchResult]:
        """Search specifically for error fixes."""
        return self.search(
            error_message,
            limit=5,
            source_types=["error_fix", "snippet", "conversation"],
            language=language,
        )

    def search_code_patterns(self, description: str, framework: str = None) -> List[SearchResult]:
        """Search for code patterns and snippets."""
        return self.search(
            description,
            limit=10,
            source_types=["snippet", "pattern", "api"],
            framework=framework,
        )

    def _extract_snippet(self, content: str, matched_terms: List[str], max_length: int = 300) -> str:
        """Extract relevant snippet from content."""
        if len(content) <= max_length:
            return content

        # Find position of first matched term
        content_lower = content.lower()
        best_pos = 0

        for term in matched_terms:
            pos = content_lower.find(term)
            if pos != -1:
                best_pos = pos
                break

        # Extract snippet around best position
        start = max(0, best_pos - 50)
        end = min(len(content), start + max_length)

        snippet = content[start:end]

        # Clean up
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    # ==================== Context Generation ====================

    def get_context_for_task(
        self,
        task_description: str,
        language: str = None,
        framework: str = None,
        max_results: int = 5,
        max_tokens: int = 2000,
    ) -> RAGContext:
        """Generate comprehensive context for an AI task."""
        results = self.search(
            task_description,
            limit=max_results,
            language=language,
            framework=framework,
        )

        context_parts = ["## RELEVANT KNOWLEDGE\n"]
        sources = []
        token_estimate = 0

        for result in results:
            doc = result.document

            # Estimate tokens (rough approximation)
            content_tokens = len(doc.content.split()) * 1.3

            if token_estimate + content_tokens > max_tokens:
                # Truncate content
                available_tokens = max_tokens - token_estimate
                words = doc.content.split()[:int(available_tokens / 1.3)]
                content = " ".join(words) + "..."
            else:
                content = doc.content

            # Format based on source type
            if doc.source_type == "snippet":
                context_parts.append(f"### Code Example: {doc.title}")
                if doc.language:
                    context_parts.append(f"```{doc.language}\n{content}\n```")
                else:
                    context_parts.append(f"```\n{content}\n```")

            elif doc.source_type == "error_fix":
                context_parts.append(f"### Error Fix: {doc.title}")
                context_parts.append(content)

            elif doc.source_type == "pattern":
                context_parts.append(f"### Pattern: {doc.title}")
                context_parts.append(content)

            elif doc.source_type == "api":
                context_parts.append(f"### API Reference: {doc.title}")
                context_parts.append(content)

            elif doc.source_type == "documentation":
                context_parts.append(f"### Documentation: {doc.title}")
                context_parts.append(result.snippet)

            elif doc.source_type == "file":
                context_parts.append(f"### From {doc.source_path}")
                context_parts.append(result.snippet)

            else:
                context_parts.append(f"### {doc.title or doc.source_type}")
                context_parts.append(result.snippet)

            context_parts.append("")
            sources.append(f"{doc.source_type}: {doc.title or doc.source_path or doc.doc_id}")
            token_estimate += content_tokens

        context_text = "\n".join(context_parts)

        return RAGContext(
            query=task_description,
            results=results,
            context_text=context_text,
            sources=sources,
            total_tokens_estimate=int(token_estimate),
        )

    def get_error_context(self, error_message: str, code_context: str = None) -> RAGContext:
        """Generate context specifically for debugging an error."""
        query = error_message
        if code_context:
            query = f"{error_message}\n\nCode:\n{code_context[:500]}"

        return self.get_context_for_task(
            query,
            max_results=3,
            max_tokens=1500,
        )

    # ==================== Statistics ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        return {
            "total_documents": len(self._index),
            "documents_by_source": dict(self._source_stats),
            "storage_path": str(self.storage_dir),
        }

    def clear_index(self):
        """Clear all indexed documents."""
        self._index = TFIDFIndex()
        self._source_stats.clear()
        self._save_index()
        logger.info("RAG index cleared")

    def index_project_if_stale(
        self,
        project_name: str,
        project_path: str,
        max_age_hours: int = 24,
    ) -> bool:
        """Index a project if not indexed recently. Returns True if indexing occurred."""
        import time as _time

        marker_file = self.storage_dir / f"indexed_{project_name}.marker"
        if marker_file.exists():
            age_hours = (_time.time() - marker_file.stat().st_mtime) / 3600
            if age_hours < max_age_hours:
                return False

        # Index the project
        count = self.index_project_files(project_path)
        if count > 0:
            marker_file.write_text(f"{project_name}:{count}:{_time.time()}")
            logger.info(f"Auto-indexed project '{project_name}': {count} files")
            return True
        return False


# Global instance
_rag_instance: Optional[UniversalRAG] = None


def get_rag() -> UniversalRAG:
    """Get or create the global RAG instance."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = UniversalRAG()
    return _rag_instance
