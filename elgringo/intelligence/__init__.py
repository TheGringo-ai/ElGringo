"""
AI Intelligence Module
======================
ML-powered code intelligence for smarter coding assistance.

Components:
- MLXCodeEmbeddings: Apple Silicon optimized embeddings
- CodeAnalyzer: AST-based code understanding
- MLXCodeGenerator: Local code generation on Apple Silicon
- UniversalIngestor: Schema-agnostic data ingestion for any CSV
"""

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
    # Intelligence v2 — Quality, Transparency, Workflows, Feedback, ROI
    "QualityScorer",
    "get_quality_scorer",
    "ReasoningTransparency",
    "get_reasoning_transparency",
    "AgenticWorkflow",
    "AutoFailureDetector",
    "get_failure_detector",
    "FeedbackLearningLoop",
    "get_feedback_loop",
    "ROIDashboard",
    "get_roi_dashboard",
]

# Intelligence v2 modules
from .quality_scorer import QualityScorer, get_quality_scorer
from .reasoning_transparency import ReasoningTransparency, get_reasoning_transparency
from .agentic_workflow import AgenticWorkflow
from .auto_failure_detector import AutoFailureDetector, get_failure_detector
from .feedback_loop import FeedbackLearningLoop, get_feedback_loop
from .roi_dashboard import ROIDashboard, get_roi_dashboard
