"""Knowledge base for AI team domain expertise"""
from .domains import DOMAIN_EXPERTISE, get_domain_context, get_all_domains
from .teaching import TeachingSystem, Lesson, ProjectPattern
from .auto_learner import AutoLearner, ExtractedPrompt, InteractionInsight, ConversationContext
from .data_manager import DataManager, DataLimits, get_data_manager
from .coding_hub import (
    CodingKnowledgeHub,
    CodeSnippet,
    ErrorFix,
    FrameworkPattern,
    APIKnowledge,
    get_coding_hub,
)
from .rag_system import (
    UniversalRAG,
    Document,
    SearchResult,
    RAGContext,
    get_rag,
)
from .documentation_loader import (
    DocumentationLoader,
    DocumentChunk,
    get_documentation_loader,
)
from .firebase_docs import (
    FirebaseDocumentation,
    DocChunk,
    get_firebase_docs,
)

__all__ = [
    "DOMAIN_EXPERTISE", "get_domain_context", "get_all_domains",
    "TeachingSystem", "Lesson", "ProjectPattern",
    "AutoLearner", "ExtractedPrompt", "InteractionInsight", "ConversationContext",
    "DataManager", "DataLimits", "get_data_manager",
    # Coding Knowledge Hub
    "CodingKnowledgeHub", "CodeSnippet", "ErrorFix", "FrameworkPattern",
    "APIKnowledge", "get_coding_hub",
    # RAG System
    "UniversalRAG", "Document", "SearchResult", "RAGContext", "get_rag",
    # Documentation Loader
    "DocumentationLoader", "DocumentChunk", "get_documentation_loader",
    # Firebase Documentation
    "FirebaseDocumentation", "DocChunk", "get_firebase_docs",
]
