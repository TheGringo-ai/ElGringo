"""
Code Embeddings
===============
Semantic code search using transformer embeddings.

This enables:
- Finding similar code by meaning, not just keywords
- Understanding code intent
- Matching problems to solutions

Uses lightweight models that run locally:
- all-MiniLM-L6-v2 (default, 80MB, fast)
- codeberta-base (code-specific, 500MB, more accurate)

Usage:
    embeddings = CodeEmbeddings()

    # Index code snippets
    embeddings.add("def hello(): print('hi')", metadata={"lang": "python"})
    embeddings.add("function hello() { console.log('hi') }", metadata={"lang": "js"})

    # Search semantically
    results = embeddings.search("greeting function", top_k=5)
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Storage path
EMBEDDINGS_DIR = Path.home() / ".ai-dev-team" / "embeddings"
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CodeChunk:
    """A chunk of code with its embedding"""
    id: str
    content: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CodeEmbeddings:
    """
    Semantic code search using embeddings.

    Features:
    - Local embedding models (no API calls)
    - Persistent storage
    - Fast similarity search
    - Code-aware chunking
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        storage_path: Optional[Path] = None,
        use_gpu: bool = True,
    ):
        """
        Initialize code embeddings.

        Args:
            model_name: Sentence transformer model name
                - "all-MiniLM-L6-v2" (fast, general)
                - "microsoft/codebert-base" (code-specific)
                - "BAAI/bge-small-en-v1.5" (high quality)
            storage_path: Where to persist embeddings
            use_gpu: Use GPU/MPS if available
        """
        self.model_name = model_name
        self.storage_path = storage_path or EMBEDDINGS_DIR / "code_index"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._model = None
        self._chunks: Dict[str, CodeChunk] = {}
        self._embeddings_matrix: Optional[np.ndarray] = None
        self._id_to_idx: Dict[str, int] = {}

        self._load_index()

    def _get_model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                # Check for MPS (Apple Silicon) or CUDA
                device = "cpu"
                try:
                    import torch
                    if torch.backends.mps.is_available():
                        device = "mps"
                    elif torch.cuda.is_available():
                        device = "cuda"
                except:
                    pass

                self._model = SentenceTransformer(self.model_name, device=device)
                logger.info(f"Loaded embedding model {self.model_name} on {device}")
            except ImportError:
                logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")
                return None
        return self._model

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def embed(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if model unavailable
        """
        model = self._get_model()
        if model is None:
            return None

        # Preprocess code
        processed = self._preprocess_code(text)
        embedding = model.encode(processed, convert_to_numpy=True)
        return embedding

    def _preprocess_code(self, code: str) -> str:
        """Preprocess code for embedding"""
        # Remove excessive whitespace but preserve structure
        lines = code.split('\n')
        lines = [line.rstrip() for line in lines]

        # Limit length (models have token limits)
        text = '\n'.join(lines)
        if len(text) > 2000:
            text = text[:2000]

        return text

    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_id: Optional[str] = None,
    ) -> str:
        """
        Add code to the index.

        Args:
            content: Code content
            metadata: Additional metadata (language, file, etc.)
            chunk_id: Custom ID (auto-generated if not provided)

        Returns:
            Chunk ID
        """
        chunk_id = chunk_id or self._generate_id(content)

        # Skip if already indexed
        if chunk_id in self._chunks:
            return chunk_id

        embedding = self.embed(content)

        chunk = CodeChunk(
            id=chunk_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
        )
        self._chunks[chunk_id] = chunk

        # Rebuild matrix
        self._rebuild_matrix()

        return chunk_id

    def add_batch(
        self,
        items: List[Tuple[str, Dict[str, Any]]],
    ) -> List[str]:
        """
        Add multiple code chunks efficiently.

        Args:
            items: List of (content, metadata) tuples

        Returns:
            List of chunk IDs
        """
        model = self._get_model()
        if model is None:
            return []

        # Filter out already indexed
        new_items = []
        ids = []
        for content, metadata in items:
            chunk_id = self._generate_id(content)
            if chunk_id not in self._chunks:
                new_items.append((chunk_id, content, metadata))
            ids.append(chunk_id)

        if not new_items:
            return ids

        # Batch encode
        contents = [self._preprocess_code(content) for _, content, _ in new_items]
        embeddings = model.encode(contents, convert_to_numpy=True, show_progress_bar=True)

        # Store
        for (chunk_id, content, metadata), embedding in zip(new_items, embeddings):
            self._chunks[chunk_id] = CodeChunk(
                id=chunk_id,
                content=content,
                embedding=embedding,
                metadata=metadata,
            )

        self._rebuild_matrix()
        logger.info(f"Added {len(new_items)} new chunks to index")

        return ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code.

        Args:
            query: Search query (natural language or code)
            top_k: Number of results
            min_score: Minimum similarity score (0-1)
            filter_metadata: Filter by metadata fields

        Returns:
            List of results with score, content, metadata
        """
        if not self._chunks or self._embeddings_matrix is None:
            return []

        query_embedding = self.embed(query)
        if query_embedding is None:
            return []

        # Cosine similarity
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        matrix_norm = self._embeddings_matrix / np.linalg.norm(
            self._embeddings_matrix, axis=1, keepdims=True
        )
        similarities = np.dot(matrix_norm, query_norm)

        # Get top results
        top_indices = np.argsort(similarities)[::-1][:top_k * 2]  # Get extra for filtering

        results = []
        idx_to_id = {v: k for k, v in self._id_to_idx.items()}

        for idx in top_indices:
            if len(results) >= top_k:
                break

            score = float(similarities[idx])
            if score < min_score:
                continue

            chunk_id = idx_to_id[idx]
            chunk = self._chunks[chunk_id]

            # Apply metadata filter
            if filter_metadata:
                match = all(
                    chunk.metadata.get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue

            results.append({
                "id": chunk_id,
                "score": score,
                "content": chunk.content,
                "metadata": chunk.metadata,
            })

        return results

    def find_similar(
        self,
        code: str,
        top_k: int = 5,
        exclude_self: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Find code similar to given code.

        Args:
            code: Code to find similar matches for
            top_k: Number of results
            exclude_self: Exclude exact match

        Returns:
            Similar code chunks
        """
        results = self.search(code, top_k=top_k + 1)

        if exclude_self:
            code_id = self._generate_id(code)
            results = [r for r in results if r["id"] != code_id]

        return results[:top_k]

    def _rebuild_matrix(self):
        """Rebuild the embeddings matrix for fast search"""
        chunks_with_embeddings = [
            (cid, chunk) for cid, chunk in self._chunks.items()
            if chunk.embedding is not None
        ]

        if not chunks_with_embeddings:
            self._embeddings_matrix = None
            self._id_to_idx = {}
            return

        self._id_to_idx = {cid: i for i, (cid, _) in enumerate(chunks_with_embeddings)}
        self._embeddings_matrix = np.vstack([
            chunk.embedding for _, chunk in chunks_with_embeddings
        ])

    def save(self):
        """Save index to disk"""
        # Save chunks (without embeddings in JSON)
        chunks_data = []
        for cid, chunk in self._chunks.items():
            chunks_data.append({
                "id": chunk.id,
                "content": chunk.content,
                "metadata": chunk.metadata,
            })

        with open(self.storage_path / "chunks.json", "w") as f:
            json.dump(chunks_data, f)

        # Save embeddings as numpy
        if self._embeddings_matrix is not None:
            np.save(self.storage_path / "embeddings.npy", self._embeddings_matrix)
            with open(self.storage_path / "id_to_idx.json", "w") as f:
                json.dump(self._id_to_idx, f)

        logger.info(f"Saved {len(self._chunks)} chunks to {self.storage_path}")

    def _load_index(self):
        """Load index from disk"""
        chunks_file = self.storage_path / "chunks.json"
        embeddings_file = self.storage_path / "embeddings.npy"
        idx_file = self.storage_path / "id_to_idx.json"

        if not chunks_file.exists():
            return

        try:
            with open(chunks_file) as f:
                chunks_data = json.load(f)

            # Load embeddings if available
            embeddings = None
            id_to_idx = {}
            if embeddings_file.exists() and idx_file.exists():
                embeddings = np.load(embeddings_file)
                with open(idx_file) as f:
                    id_to_idx = json.load(f)

            # Reconstruct chunks
            for data in chunks_data:
                chunk_id = data["id"]
                embedding = None
                if chunk_id in id_to_idx and embeddings is not None:
                    idx = id_to_idx[chunk_id]
                    embedding = embeddings[idx]

                self._chunks[chunk_id] = CodeChunk(
                    id=chunk_id,
                    content=data["content"],
                    embedding=embedding,
                    metadata=data.get("metadata", {}),
                )

            self._id_to_idx = {k: int(v) for k, v in id_to_idx.items()}
            self._embeddings_matrix = embeddings

            logger.info(f"Loaded {len(self._chunks)} chunks from {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to load index: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        languages = {}
        for chunk in self._chunks.values():
            lang = chunk.metadata.get("language", "unknown")
            languages[lang] = languages.get(lang, 0) + 1

        return {
            "total_chunks": len(self._chunks),
            "indexed_chunks": len(self._id_to_idx),
            "languages": languages,
            "model": self.model_name,
            "storage_path": str(self.storage_path),
        }


# Global instance
_embeddings = None

def get_code_embeddings() -> CodeEmbeddings:
    """Get global code embeddings instance"""
    global _embeddings
    if _embeddings is None:
        _embeddings = CodeEmbeddings()
    return _embeddings


# ============================================================================
# CODE CHUNKING UTILITIES
# ============================================================================

def chunk_code_file(
    content: str,
    language: str,
    file_path: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Chunk a code file for indexing.

    Args:
        content: File content
        language: Programming language
        file_path: File path for metadata
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks

    Returns:
        List of (chunk_content, metadata) tuples
    """
    chunks = []
    lines = content.split('\n')

    current_chunk = []
    current_size = 0
    chunk_start_line = 0

    for i, line in enumerate(lines):
        current_chunk.append(line)
        current_size += len(line) + 1

        # Check if we should end this chunk
        if current_size >= chunk_size:
            # Try to end at a logical boundary
            chunk_content = '\n'.join(current_chunk)

            metadata = {
                "language": language,
                "file": file_path,
                "start_line": chunk_start_line,
                "end_line": i,
            }
            chunks.append((chunk_content, metadata))

            # Start new chunk with overlap
            overlap_lines = max(1, overlap // 50)
            current_chunk = current_chunk[-overlap_lines:]
            current_size = sum(len(l) + 1 for l in current_chunk)
            chunk_start_line = i - overlap_lines + 1

    # Don't forget the last chunk
    if current_chunk:
        chunk_content = '\n'.join(current_chunk)
        metadata = {
            "language": language,
            "file": file_path,
            "start_line": chunk_start_line,
            "end_line": len(lines) - 1,
        }
        chunks.append((chunk_content, metadata))

    return chunks


def chunk_by_functions(
    content: str,
    language: str,
    file_path: str,
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Chunk code by functions/methods.

    This is more semantically meaningful than fixed-size chunks.
    """
    import re

    chunks = []

    # Language-specific patterns
    patterns = {
        "python": r'^(async\s+)?def\s+(\w+)',
        "javascript": r'^(async\s+)?function\s+(\w+)|^(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\(',
        "typescript": r'^(async\s+)?function\s+(\w+)|^(const|let|var)\s+(\w+)\s*=\s*(async\s+)?\(',
    }

    pattern = patterns.get(language)
    if not pattern:
        # Fall back to line-based chunking
        return chunk_code_file(content, language, file_path)

    lines = content.split('\n')
    current_func = []
    current_func_name = None
    func_start_line = 0

    for i, line in enumerate(lines):
        match = re.match(pattern, line.strip())

        if match:
            # Save previous function
            if current_func and current_func_name:
                chunk_content = '\n'.join(current_func)
                metadata = {
                    "language": language,
                    "file": file_path,
                    "function": current_func_name,
                    "start_line": func_start_line,
                    "end_line": i - 1,
                }
                chunks.append((chunk_content, metadata))

            # Start new function
            current_func = [line]
            current_func_name = match.group(2) or match.group(4)
            func_start_line = i
        else:
            current_func.append(line)

    # Don't forget the last function
    if current_func and current_func_name:
        chunk_content = '\n'.join(current_func)
        metadata = {
            "language": language,
            "file": file_path,
            "function": current_func_name,
            "start_line": func_start_line,
            "end_line": len(lines) - 1,
        }
        chunks.append((chunk_content, metadata))

    return chunks if chunks else chunk_code_file(content, language, file_path)
