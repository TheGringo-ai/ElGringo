"""
Code RAG (Retrieval-Augmented Generation)
=========================================
Enhances AI responses by retrieving relevant code context.

This makes the AI team smarter by:
- Finding relevant code from the codebase before answering
- Providing examples from similar past solutions
- Understanding project patterns and conventions

Usage:
    rag = CodeRAG()

    # Index a project
    rag.index_project("/path/to/project")

    # Get context for a task
    context = rag.get_context("implement user authentication")

    # Use context in prompt
    prompt = f"{context}\n\nTask: {task}"
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from .code_embeddings import (
    CodeEmbeddings,
    chunk_code_file,
    chunk_by_functions,
)

logger = logging.getLogger(__name__)


@dataclass
class RetrievedContext:
    """Context retrieved for a task"""
    query: str
    code_snippets: List[Dict[str, Any]]
    patterns: List[Dict[str, Any]]
    similar_solutions: List[Dict[str, Any]]
    total_tokens_estimate: int

    def to_prompt(self, max_tokens: int = 2000) -> str:
        """Format as prompt context"""
        parts = ["## Relevant Context\n"]
        tokens_used = 50  # Header

        # Add code snippets
        if self.code_snippets:
            parts.append("### Related Code\n")
            for snippet in self.code_snippets[:3]:
                snippet_text = f"```{snippet.get('language', '')}\n{snippet['content'][:500]}\n```\n"
                if tokens_used + len(snippet_text) // 4 > max_tokens:
                    break
                parts.append(f"**{snippet.get('file', 'snippet')}** (score: {snippet['score']:.2f})")
                parts.append(snippet_text)
                tokens_used += len(snippet_text) // 4

        # Add patterns
        if self.patterns and tokens_used < max_tokens - 200:
            parts.append("### Patterns\n")
            for pattern in self.patterns[:2]:
                pattern_text = f"- {pattern.get('name', 'Pattern')}: {pattern.get('description', '')}\n"
                parts.append(pattern_text)
                tokens_used += len(pattern_text) // 4

        return "\n".join(parts)


class CodeRAG:
    """
    Retrieval-Augmented Generation for code.

    Indexes codebases and retrieves relevant context for tasks.
    """

    def __init__(
        self,
        embeddings: Optional[CodeEmbeddings] = None,
        max_context_tokens: int = 2000,
    ):
        """
        Initialize Code RAG.

        Args:
            embeddings: Code embeddings instance (creates new if None)
            max_context_tokens: Maximum tokens in retrieved context
        """
        self.embeddings = embeddings or CodeEmbeddings()
        self.max_context_tokens = max_context_tokens

        # Track indexed projects
        self._indexed_projects: Set[str] = set()
        self._index_stats: Dict[str, Any] = {}

    def index_project(
        self,
        project_path: str,
        languages: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        use_function_chunking: bool = True,
    ) -> Dict[str, Any]:
        """
        Index a project for retrieval.

        Args:
            project_path: Path to project root
            languages: Languages to index (None = auto-detect)
            exclude_patterns: Glob patterns to exclude
            use_function_chunking: Chunk by functions vs fixed size

        Returns:
            Indexing statistics
        """
        project_path = Path(project_path).resolve()
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Default exclusions
        exclude_patterns = exclude_patterns or [
            "**/node_modules/**",
            "**/.git/**",
            "**/venv/**",
            "**/__pycache__/**",
            "**/dist/**",
            "**/build/**",
            "**/*.min.js",
            "**/*.map",
        ]

        # Language extensions
        lang_extensions = {
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx"],
            "rust": [".rs"],
            "go": [".go"],
            "java": [".java"],
            "cpp": [".cpp", ".hpp", ".c", ".h"],
        }

        if languages:
            extensions = []
            for lang in languages:
                extensions.extend(lang_extensions.get(lang, []))
        else:
            extensions = [ext for exts in lang_extensions.values() for ext in exts]

        # Find files
        files_to_index = []
        for ext in extensions:
            files_to_index.extend(project_path.rglob(f"*{ext}"))

        # Apply exclusions
        import fnmatch
        filtered_files = []
        for f in files_to_index:
            rel_path = str(f.relative_to(project_path))
            if not any(fnmatch.fnmatch(rel_path, pat.lstrip("**/")) for pat in exclude_patterns):
                filtered_files.append(f)

        logger.info(f"Indexing {len(filtered_files)} files from {project_path}")

        # Chunk and index files
        all_chunks = []
        for file_path in filtered_files:
            try:
                content = file_path.read_text(errors="ignore")
                if len(content) < 50:  # Skip tiny files
                    continue

                # Detect language
                ext = file_path.suffix
                language = "unknown"
                for lang, exts in lang_extensions.items():
                    if ext in exts:
                        language = lang
                        break

                # Chunk the file
                rel_path = str(file_path.relative_to(project_path))
                if use_function_chunking:
                    chunks = chunk_by_functions(content, language, rel_path)
                else:
                    chunks = chunk_code_file(content, language, rel_path)

                all_chunks.extend(chunks)

            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")

        # Batch index
        if all_chunks:
            self.embeddings.add_batch(all_chunks)
            self.embeddings.save()

        # Update tracking
        self._indexed_projects.add(str(project_path))
        self._index_stats[str(project_path)] = {
            "files": len(filtered_files),
            "chunks": len(all_chunks),
            "indexed_at": datetime.now().isoformat(),
        }

        return {
            "project": str(project_path),
            "files_indexed": len(filtered_files),
            "chunks_created": len(all_chunks),
        }

    def get_context(
        self,
        query: str,
        project_filter: Optional[str] = None,
        language_filter: Optional[str] = None,
        top_k: int = 5,
        include_patterns: bool = True,
    ) -> RetrievedContext:
        """
        Retrieve relevant context for a task.

        Args:
            query: Task description or question
            project_filter: Only search within specific project
            language_filter: Only return specific language
            top_k: Number of code snippets to retrieve
            include_patterns: Include pattern suggestions

        Returns:
            RetrievedContext with relevant code and patterns
        """
        # Build metadata filter
        filter_metadata = {}
        if language_filter:
            filter_metadata["language"] = language_filter

        # Search for relevant code
        results = self.embeddings.search(
            query=query,
            top_k=top_k,
            min_score=0.3,
            filter_metadata=filter_metadata if filter_metadata else None,
        )

        # Format results
        code_snippets = []
        for r in results:
            code_snippets.append({
                "content": r["content"],
                "score": r["score"],
                "file": r["metadata"].get("file", "unknown"),
                "language": r["metadata"].get("language", "unknown"),
                "function": r["metadata"].get("function"),
                "start_line": r["metadata"].get("start_line"),
            })

        # Detect patterns (simple heuristic for now)
        patterns = self._detect_patterns(query, code_snippets)

        # Estimate tokens
        total_content = sum(len(s["content"]) for s in code_snippets)
        tokens_estimate = total_content // 4  # Rough estimate

        return RetrievedContext(
            query=query,
            code_snippets=code_snippets,
            patterns=patterns,
            similar_solutions=[],  # TODO: Add solution memory integration
            total_tokens_estimate=tokens_estimate,
        )

    def _detect_patterns(
        self,
        query: str,
        code_snippets: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Detect common patterns in retrieved code"""
        patterns = []
        query_lower = query.lower()

        # Pattern detection based on query and code
        pattern_keywords = {
            "auth": {
                "name": "Authentication Pattern",
                "description": "JWT or session-based auth with middleware",
            },
            "crud": {
                "name": "CRUD Pattern",
                "description": "Create, Read, Update, Delete operations with validation",
            },
            "api": {
                "name": "REST API Pattern",
                "description": "RESTful endpoints with proper HTTP methods and status codes",
            },
            "database": {
                "name": "Repository Pattern",
                "description": "Data access layer separating business logic from DB operations",
            },
            "test": {
                "name": "Testing Pattern",
                "description": "Unit tests with mocking and fixtures",
            },
            "async": {
                "name": "Async Pattern",
                "description": "Asynchronous operations with proper error handling",
            },
        }

        for keyword, pattern in pattern_keywords.items():
            if keyword in query_lower:
                patterns.append(pattern)

        return patterns[:3]

    def enhance_prompt(
        self,
        prompt: str,
        task_description: Optional[str] = None,
        max_context: int = 2000,
    ) -> str:
        """
        Enhance a prompt with retrieved context.

        Args:
            prompt: Original prompt
            task_description: Task description for retrieval (uses prompt if None)
            max_context: Maximum context tokens

        Returns:
            Enhanced prompt with context
        """
        query = task_description or prompt[:500]
        context = self.get_context(query)

        context_text = context.to_prompt(max_tokens=max_context)
        if context_text:
            return f"{context_text}\n\n{prompt}"
        return prompt

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG statistics"""
        return {
            "indexed_projects": list(self._indexed_projects),
            "project_stats": self._index_stats,
            "embeddings_stats": self.embeddings.get_stats(),
        }


# ============================================================================
# INTEGRATION WITH CODING HUB
# ============================================================================

def create_rag_enhanced_context(
    task: str,
    coding_hub: Any,
    rag: Optional[CodeRAG] = None,
    max_tokens: int = 3000,
) -> str:
    """
    Create enhanced context combining coding hub and RAG.

    Args:
        task: Task description
        coding_hub: CodingKnowledgeHub instance
        rag: CodeRAG instance (creates if None)
        max_tokens: Maximum context tokens

    Returns:
        Combined context string
    """
    parts = []
    tokens_used = 0

    # Get coding hub context
    hub_context = coding_hub.generate_coding_context(
        task_description=task,
        max_items=3,
    )
    if hub_context:
        parts.append(hub_context)
        tokens_used += len(hub_context) // 4

    # Get RAG context
    if rag and tokens_used < max_tokens - 500:
        rag_context = rag.get_context(task)
        rag_text = rag_context.to_prompt(max_tokens=max_tokens - tokens_used)
        if rag_text:
            parts.append(rag_text)

    return "\n\n".join(parts)
