"""
MLX Code Embeddings
===================
Apple Silicon optimized code embeddings using MLX.

MLX advantages on Mac:
- Uses unified memory (can use all RAM)
- Optimized for M1/M2/M3/M4 chips
- 2-5x faster than PyTorch on Mac
- Lazy evaluation for efficiency

Usage:
    from ai_dev_team.intelligence.mlx_embeddings import MLXCodeEmbeddings

    embeddings = MLXCodeEmbeddings()
    embeddings.add("def hello(): print('hi')")
    results = embeddings.search("greeting function")
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Check for MLX availability
MLX_AVAILABLE = False
try:
    import mlx.core as mx
    import mlx.nn as nn
    MLX_AVAILABLE = True
    logger.info("MLX is available - using Apple Silicon optimization")
except ImportError:
    logger.info("MLX not available - install with: pip install mlx")

# Storage
EMBEDDINGS_DIR = Path.home() / ".ai-dev-team" / "mlx_embeddings"
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CodeChunk:
    """A chunk of code with embedding"""
    id: str
    content: str
    embedding: Optional[Any] = None  # mx.array or np.array
    metadata: Dict[str, Any] = field(default_factory=dict)


class MLXCodeEmbeddings:
    """
    Code embeddings using MLX for Apple Silicon.

    Features:
    - Fast inference on M1/M2/M3/M4
    - Uses unified memory efficiently
    - Supports multiple embedding models
    - Persistent storage
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        use_mlx: bool = True,
    ):
        """
        Initialize MLX embeddings.

        Args:
            model_name: Model to use for embeddings
            use_mlx: Use MLX if available (falls back to numpy)
        """
        self.model_name = model_name
        self.use_mlx = use_mlx and MLX_AVAILABLE
        self._model = None
        self._tokenizer = None

        self._chunks: Dict[str, CodeChunk] = {}
        self._embeddings_matrix = None
        self._id_to_idx: Dict[str, int] = {}

        self._load_index()

    def _load_model(self):
        """Load embedding model"""
        if self._model is not None:
            return

        if self.use_mlx:
            self._load_mlx_model()
        else:
            self._load_sentence_transformer()

    def _load_mlx_model(self):
        """Load model using MLX"""
        try:
            # Try mlx-embeddings package first
            from mlx_embeddings import load_model

            self._model, self._tokenizer = load_model(self.model_name)
            logger.info(f"Loaded MLX embedding model: {self.model_name}")
        except ImportError:
            logger.info("mlx-embeddings not found, using sentence-transformers with MLX conversion")
            self._load_sentence_transformer_with_mlx()

    def _load_sentence_transformer_with_mlx(self):
        """Load sentence-transformers and convert to MLX"""
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np

            # Load the model
            self._model = SentenceTransformer(self.model_name)

            # Mark that we'll convert to MLX after encoding
            self._convert_to_mlx = True
            logger.info(f"Loaded sentence-transformer with MLX conversion: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")
            self._model = None

    def _load_sentence_transformer(self):
        """Load using pure sentence-transformers"""
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded sentence-transformer: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available")
            self._model = None

    def _generate_id(self, content: str) -> str:
        """Generate unique ID"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def embed(self, text: str) -> Optional[Any]:
        """
        Generate embedding for text.

        Returns MLX array if available, else numpy array.
        """
        self._load_model()
        if self._model is None:
            return None

        # Preprocess
        text = self._preprocess(text)

        if hasattr(self._model, 'encode'):
            # sentence-transformers style
            embedding = self._model.encode(text, convert_to_numpy=True)
            if self.use_mlx and MLX_AVAILABLE:
                embedding = mx.array(embedding)
            return embedding
        else:
            # MLX native model
            tokens = self._tokenizer(text)
            embedding = self._model(tokens)
            return embedding

    def embed_batch(self, texts: List[str]) -> Optional[Any]:
        """Batch embed multiple texts efficiently"""
        self._load_model()
        if self._model is None:
            return None

        texts = [self._preprocess(t) for t in texts]

        if hasattr(self._model, 'encode'):
            embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            if self.use_mlx and MLX_AVAILABLE:
                embeddings = mx.array(embeddings)
            return embeddings
        else:
            # Batch with MLX
            results = []
            for text in texts:
                tokens = self._tokenizer(text)
                results.append(self._model(tokens))
            return mx.stack(results)

    def _preprocess(self, text: str) -> str:
        """Preprocess text for embedding"""
        # Limit length
        if len(text) > 2000:
            text = text[:2000]
        return text.strip()

    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_id: Optional[str] = None,
    ) -> str:
        """Add code to index"""
        chunk_id = chunk_id or self._generate_id(content)

        if chunk_id in self._chunks:
            return chunk_id

        embedding = self.embed(content)

        self._chunks[chunk_id] = CodeChunk(
            id=chunk_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
        )

        self._rebuild_matrix()
        return chunk_id

    def add_batch(self, items: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
        """Add multiple items efficiently"""
        # Filter already indexed
        new_items = []
        ids = []
        for content, metadata in items:
            chunk_id = self._generate_id(content)
            ids.append(chunk_id)
            if chunk_id not in self._chunks:
                new_items.append((chunk_id, content, metadata))

        if not new_items:
            return ids

        # Batch embed
        contents = [content for _, content, _ in new_items]
        embeddings = self.embed_batch(contents)

        if embeddings is None:
            return ids

        # Store
        for i, (chunk_id, content, metadata) in enumerate(new_items):
            if MLX_AVAILABLE and self.use_mlx:
                emb = embeddings[i]
            else:
                emb = embeddings[i]

            self._chunks[chunk_id] = CodeChunk(
                id=chunk_id,
                content=content,
                embedding=emb,
                metadata=metadata,
            )

        self._rebuild_matrix()
        logger.info(f"Added {len(new_items)} chunks with MLX embeddings")
        return ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Search for similar code using cosine similarity"""
        if not self._chunks or self._embeddings_matrix is None:
            return []

        query_embedding = self.embed(query)
        if query_embedding is None:
            return []

        # Cosine similarity
        if MLX_AVAILABLE and self.use_mlx:
            # MLX optimized similarity
            query_norm = query_embedding / mx.linalg.norm(query_embedding)
            matrix_norm = self._embeddings_matrix / mx.linalg.norm(
                self._embeddings_matrix, axis=1, keepdims=True
            )
            similarities = mx.matmul(matrix_norm, query_norm)
            similarities = similarities.tolist()  # Convert to Python list
        else:
            import numpy as np
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            matrix_norm = self._embeddings_matrix / np.linalg.norm(
                self._embeddings_matrix, axis=1, keepdims=True
            )
            similarities = np.dot(matrix_norm, query_norm)

        # Get top results
        idx_score = list(enumerate(similarities))
        idx_score.sort(key=lambda x: x[1], reverse=True)

        results = []
        idx_to_id = {v: k for k, v in self._id_to_idx.items()}

        for idx, score in idx_score[:top_k]:
            if score < min_score:
                continue

            chunk_id = idx_to_id[idx]
            chunk = self._chunks[chunk_id]

            results.append({
                "id": chunk_id,
                "score": float(score),
                "content": chunk.content,
                "metadata": chunk.metadata,
            })

        return results

    def _rebuild_matrix(self):
        """Rebuild embeddings matrix"""
        chunks_with_emb = [
            (cid, chunk) for cid, chunk in self._chunks.items()
            if chunk.embedding is not None
        ]

        if not chunks_with_emb:
            self._embeddings_matrix = None
            self._id_to_idx = {}
            return

        self._id_to_idx = {cid: i for i, (cid, _) in enumerate(chunks_with_emb)}

        if MLX_AVAILABLE and self.use_mlx:
            self._embeddings_matrix = mx.stack([
                chunk.embedding for _, chunk in chunks_with_emb
            ])
        else:
            import numpy as np
            self._embeddings_matrix = np.vstack([
                chunk.embedding for _, chunk in chunks_with_emb
            ])

    def save(self, path: Optional[Path] = None):
        """Save index to disk"""
        path = path or EMBEDDINGS_DIR / "mlx_index"
        path.mkdir(parents=True, exist_ok=True)

        # Save chunks metadata
        chunks_data = []
        for cid, chunk in self._chunks.items():
            chunks_data.append({
                "id": chunk.id,
                "content": chunk.content,
                "metadata": chunk.metadata,
            })

        with open(path / "chunks.json", "w") as f:
            json.dump(chunks_data, f)

        # Save embeddings
        if self._embeddings_matrix is not None:
            import numpy as np
            if MLX_AVAILABLE and self.use_mlx:
                matrix_np = np.array(self._embeddings_matrix.tolist())
            else:
                matrix_np = self._embeddings_matrix
            np.save(path / "embeddings.npy", matrix_np)

            with open(path / "id_to_idx.json", "w") as f:
                json.dump(self._id_to_idx, f)

        logger.info(f"Saved {len(self._chunks)} chunks to {path}")

    def _load_index(self):
        """Load index from disk"""
        path = EMBEDDINGS_DIR / "mlx_index"
        chunks_file = path / "chunks.json"

        if not chunks_file.exists():
            return

        try:
            import numpy as np

            with open(chunks_file) as f:
                chunks_data = json.load(f)

            embeddings = None
            id_to_idx = {}
            embeddings_file = path / "embeddings.npy"
            idx_file = path / "id_to_idx.json"

            if embeddings_file.exists() and idx_file.exists():
                embeddings = np.load(embeddings_file)
                with open(idx_file) as f:
                    id_to_idx = json.load(f)

                if MLX_AVAILABLE and self.use_mlx:
                    embeddings = mx.array(embeddings)

            # Reconstruct
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

            logger.info(f"Loaded {len(self._chunks)} chunks from MLX index")
        except Exception as e:
            logger.error(f"Failed to load MLX index: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return {
            "total_chunks": len(self._chunks),
            "using_mlx": self.use_mlx and MLX_AVAILABLE,
            "model": self.model_name,
            "indexed": len(self._id_to_idx),
        }


# ============================================================================
# MLX LOCAL CODE GENERATOR
# ============================================================================

class MLXCodeGenerator:
    """
    Local code generation using MLX models.

    Uses your fine-tuned Qwen Coder or Llama Coder models.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_type: str = "qwen",  # "qwen" or "llama"
    ):
        """
        Initialize MLX code generator.

        Args:
            model_path: Path to MLX model directory
            model_type: Type of model ("qwen" or "llama")
        """
        self.model_type = model_type
        self.model_path = model_path or self._find_model()
        self._model = None
        self._tokenizer = None

    def _find_model(self) -> Optional[str]:
        """Find available MLX model"""
        mlx_dir = Path(__file__).parent.parent.parent / "mlx-training" / "models"

        if self.model_type == "qwen":
            candidates = ["qwen-coder-fused", "qwen-coder-lora"]
        else:
            candidates = ["llama-coder-fused", "llama-coder-lora"]

        for name in candidates:
            path = mlx_dir / name
            if path.exists():
                return str(path)

        return None

    def _load_model(self):
        """Load MLX model"""
        if self._model is not None:
            return

        if not MLX_AVAILABLE:
            logger.warning("MLX not available")
            return

        if not self.model_path:
            logger.warning("No MLX model found")
            return

        try:
            from mlx_lm import load, generate

            self._model, self._tokenizer = load(self.model_path)
            self._generate_fn = generate
            logger.info(f"Loaded MLX model from {self.model_path}")
        except ImportError:
            logger.warning("mlx-lm not installed. Install with: pip install mlx-lm")
        except Exception as e:
            logger.error(f"Failed to load MLX model: {e}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """
        Generate code using MLX model.

        Args:
            prompt: Code prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated code or None
        """
        self._load_model()
        if self._model is None:
            return None

        try:
            response = self._generate_fn(
                self._model,
                self._tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
            )
            return response
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return None

    def complete(
        self,
        code_prefix: str,
        max_tokens: int = 200,
    ) -> Optional[str]:
        """
        Complete code given a prefix.

        Args:
            code_prefix: Code to complete
            max_tokens: Maximum tokens

        Returns:
            Completed code
        """
        return self.generate(code_prefix, max_tokens=max_tokens, temperature=0.3)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_mlx_embeddings = None

def get_mlx_embeddings() -> MLXCodeEmbeddings:
    """Get global MLX embeddings instance"""
    global _mlx_embeddings
    if _mlx_embeddings is None:
        _mlx_embeddings = MLXCodeEmbeddings()
    return _mlx_embeddings


def check_mlx_status() -> Dict[str, Any]:
    """Check MLX availability and status"""
    status = {
        "mlx_available": MLX_AVAILABLE,
        "apple_silicon": False,
        "models_found": [],
    }

    # Check for Apple Silicon
    try:
        import platform
        if platform.machine() == "arm64" and platform.system() == "Darwin":
            status["apple_silicon"] = True
    except Exception:
        logger.debug("Failed to detect Apple Silicon status")

    # Check for models
    mlx_dir = Path(__file__).parent.parent.parent / "mlx-training" / "models"
    if mlx_dir.exists():
        for item in mlx_dir.iterdir():
            if item.is_dir() and ("coder" in item.name or "fused" in item.name):
                status["models_found"].append(item.name)

    return status


if __name__ == "__main__":
    print("=== MLX STATUS ===")
    status = check_mlx_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
