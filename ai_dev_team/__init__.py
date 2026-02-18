"""
AI Development Team - Multi-Model AI Orchestration Platform
============================================================

A standalone, reusable AI development team that orchestrates multiple AI models
(Claude, ChatGPT, Gemini, Grok) for collaborative software development.

Usage:
    from ai_dev_team import AIDevTeam

    team = AIDevTeam()
    result = await team.collaborate("Build a REST API for user authentication")
    print(result.final_answer)
"""

__version__ = "1.0.0"
__author__ = "Fred AI Team"

from .orchestrator import AIDevTeam, CollaborationResult
from .agents import (
    AIAgent,
    ClaudeAgent,
    ChatGPTAgent,
    GeminiAgent,
    GrokAgent,
    AgentConfig,
    ModelType,
    # Specialized agents
    SecurityAuditor,
    CodeReviewer,
    SolutionArchitect,
    FrontendDeveloper,
    SecurityFinding,
    CodeReviewComment,
    ArchitectureDecision,
    FrontendAnalysis,
    ComponentSuggestion,
    Severity,
    create_security_auditor,
    create_code_reviewer,
    create_solution_architect,
    create_frontend_developer,
)
from .memory import MemorySystem, MistakePrevention, LearningEngine
from .collaboration import CollaborationEngine, CollaborationMode, WeightedConsensus
from .routing import (
    TaskRouter,
    TaskType,
    TaskClassification,
    CostOptimizer,
    ModelTier,
    RoutingDecision,
    AgentScore,
    DecisionLogger,
    get_decision_logger,
)
from .integrations import ChatterFixConnector, check_against_learnings, find_solution, GitHubIntegration
from .parallel_coding import ParallelCodingEngine, CodeTask, CodeFix, ParallelCodingResult
from .shared_config import SharedConfig, AIProviderConfig, ProviderType, shared_config, get_shared_config
from .fredfix import FredFix, FixResult, create_fredfix
from .app_generator import AppGenerator, create_app_generator, generate_app
from .tools import (
    create_all_tools,
    GitTools, DockerTools, DatabaseTools, PackageTools, DeployTools,
    # Infrastructure tools
    KubernetesTools, TerraformTools, GCPTools,
    create_kubernetes_tools, create_terraform_tools, create_gcp_tools,
    # Frontend tools
    FrontendTools, create_frontend_tools,
)
from .security import (
    SecurityValidator,
    ValidationResult,
    ThreatLevel,
    validate_tool_call,
    get_security_validator,
)
from .ollama_knowledge import (
    OllamaKnowledgeBase,
    get_ollama_knowledge_base,
    get_enhanced_prompt,
    ExpertiseDomain,
)
from .workflows import (
    PreCommitWorkflow,
    CICDWorkflow,
    CodeReviewPipeline,
    WorkflowResult,
    GateResult,
    WorkflowStatus,
    GateType,
    create_pre_commit_workflow,
    create_cicd_workflow,
    create_code_review_pipeline,
    run_pre_commit,
)

# v2 Modules - Preferences, Bootstrap
from .preferences import DevConstraints, PreferenceStore, get_preference_store
from .bootstrap import AppSpec, AppBootstrapper, BootstrapResult, bootstrap_app

# Advanced Agent Framework
from .framework import (
    # Tools
    Tool,
    ToolRegistry,
    ToolResult,
    ToolParameter,
    create_tool,
    get_tool_registry,
    # ReAct
    ReActAgent,
    ReActStep,
    ReActTrace,
    ThoughtType,
    # Planner
    TaskPlanner,
    ExecutionPlan,
    PlanStep,
    PlanStatus,
    # Chain of Thought
    ChainOfThought,
    ReasoningChain,
    ReasoningStep,
    ReasoningType,
    reason_through,
    # Context
    ContextManager,
    ContextWindow,
    ConversationTracker,
    Message,
    MessagePriority,
    MessageRole,
)

__all__ = [
    # Core
    "AIDevTeam",
    "CollaborationResult",
    # Agents
    "AIAgent",
    "ClaudeAgent",
    "ChatGPTAgent",
    "GeminiAgent",
    "GrokAgent",
    "AgentConfig",
    "ModelType",
    # Memory
    "MemorySystem",
    "MistakePrevention",
    "LearningEngine",
    # Collaboration
    "CollaborationEngine",
    "CollaborationMode",
    "WeightedConsensus",
    # Routing & Cost Optimization
    "TaskRouter",
    "TaskType",
    "TaskClassification",
    "CostOptimizer",
    "ModelTier",
    "RoutingDecision",
    "AgentScore",
    "DecisionLogger",
    "get_decision_logger",
    # Integrations
    "ChatterFixConnector",
    "check_against_learnings",
    "find_solution",
    "GitHubIntegration",
    # Parallel Coding
    "ParallelCodingEngine",
    "CodeTask",
    "CodeFix",
    "ParallelCodingResult",
    # Shared Config
    "SharedConfig",
    "AIProviderConfig",
    "ProviderType",
    "shared_config",
    "get_shared_config",
    # FredFix - Autonomous Fixer
    "FredFix",
    "FixResult",
    "create_fredfix",
    # App Generator
    "AppGenerator",
    "create_app_generator",
    "generate_app",
    # Tools
    "create_all_tools",
    "GitTools",
    "DockerTools",
    "DatabaseTools",
    "PackageTools",
    "DeployTools",
    # Infrastructure Tools
    "KubernetesTools",
    "TerraformTools",
    "GCPTools",
    "create_kubernetes_tools",
    "create_terraform_tools",
    "create_gcp_tools",
    # Frontend Tools
    "FrontendTools",
    "create_frontend_tools",
    # Specialized Agents
    "SecurityAuditor",
    "CodeReviewer",
    "SolutionArchitect",
    "FrontendDeveloper",
    "SecurityFinding",
    "CodeReviewComment",
    "ArchitectureDecision",
    "FrontendAnalysis",
    "ComponentSuggestion",
    "Severity",
    "create_security_auditor",
    "create_code_reviewer",
    "create_solution_architect",
    "create_frontend_developer",
    # Security
    "SecurityValidator",
    "ValidationResult",
    "ThreatLevel",
    "validate_tool_call",
    "get_security_validator",
    # Ollama Knowledge
    "OllamaKnowledgeBase",
    "get_ollama_knowledge_base",
    "get_enhanced_prompt",
    "ExpertiseDomain",
    # Workflows
    "PreCommitWorkflow",
    "CICDWorkflow",
    "CodeReviewPipeline",
    "WorkflowResult",
    "GateResult",
    "WorkflowStatus",
    "GateType",
    "create_pre_commit_workflow",
    "create_cicd_workflow",
    "create_code_review_pipeline",
    "run_pre_commit",
    # v2 - Preferences
    "DevConstraints",
    "PreferenceStore",
    "get_preference_store",
    # v2 - Bootstrap
    "AppSpec",
    "AppBootstrapper",
    "BootstrapResult",
    "bootstrap_app",
    # Advanced Agent Framework - Tools
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "ToolParameter",
    "create_tool",
    "get_tool_registry",
    # Advanced Agent Framework - ReAct
    "ReActAgent",
    "ReActStep",
    "ReActTrace",
    "ThoughtType",
    # Advanced Agent Framework - Planner
    "TaskPlanner",
    "ExecutionPlan",
    "PlanStep",
    "PlanStatus",
    # Advanced Agent Framework - Chain of Thought
    "ChainOfThought",
    "ReasoningChain",
    "ReasoningStep",
    "ReasoningType",
    "reason_through",
    # Advanced Agent Framework - Context
    "ContextManager",
    "ContextWindow",
    "ConversationTracker",
    "Message",
    "MessagePriority",
    "MessageRole",
]
