"""
AI Intelligence Module
======================
ML-powered code intelligence for smarter coding assistance.

Components:
- CodeEmbeddings: Semantic code search using embeddings
- MLXCodeEmbeddings: Apple Silicon optimized embeddings
- CodeRAG: Retrieval-augmented generation for code context
- CodeAnalyzer: AST-based code understanding
- MLXCodeGenerator: Local code generation on Apple Silicon
- UniversalIngestor: Schema-agnostic data ingestion for any CSV
"""

from .code_embeddings import CodeEmbeddings, get_code_embeddings
from .code_rag import CodeRAG
from .code_analyzer import CodeAnalyzer
from .mlx_embeddings import (
    MLXCodeEmbeddings,
    MLXCodeGenerator,
    get_mlx_embeddings,
    check_mlx_status,
)
from .semantic_delta import (
    SemanticDeltaExtractor,
    SemanticDelta,
    SemanticChange,
    RiskLevel,
    get_semantic_delta,
)
from .universal_ingestor import (
    UniversalIngestor,
    SchemaAnalysis,
    ColumnMapping,
    GOLDEN_SCHEMA,
)
from .cmms_schemas import (
    COMPREHENSIVE_ALIASES,
    identify_vendor,
    get_vendor_fields,
    get_all_known_fields,
)

__all__ = [
    # Standard (cross-platform)
    "CodeEmbeddings",
    "get_code_embeddings",
    "CodeRAG",
    "CodeAnalyzer",
    # Apple Silicon optimized
    "MLXCodeEmbeddings",
    "MLXCodeGenerator",
    "get_mlx_embeddings",
    "check_mlx_status",
    # Semantic Delta (16GB RAM optimization)
    "SemanticDeltaExtractor",
    "SemanticDelta",
    "SemanticChange",
    "RiskLevel",
    "get_semantic_delta",
    # Universal Ingestor (Schema-agnostic data ingestion)
    "UniversalIngestor",
    "SchemaAnalysis",
    "ColumnMapping",
    "GOLDEN_SCHEMA",
    # CMMS Vendor Schemas (15+ vendors)
    "COMPREHENSIVE_ALIASES",
    "identify_vendor",
    "get_vendor_fields",
    "get_all_known_fields",
]
