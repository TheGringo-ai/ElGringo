"""
AI Agents Module - Individual AI Model Integrations
====================================================

Provides abstract base class and concrete implementations for:
- Claude (Anthropic)
- ChatGPT (OpenAI)
- Gemini (Google)
- Grok (xAI)
- Ollama (Local LLMs)
- Llama Cloud (Groq, Together AI, Fireworks)
"""

from .base import AIAgent, AgentConfig, AgentResponse, ModelType
from .claude import ClaudeAgent
from .chatgpt import ChatGPTAgent
from .gemini import GeminiAgent
from .grok import GrokAgent
from .ollama import OllamaAgent
from .mlx_agent import MLXAgent, create_mlx_coder, create_mlx_general
from .llama_cloud import (
    LlamaCloudAgent,
    create_llama_70b,
    create_llama_405b,
    create_llama_fast,
    create_llama_vision,
    create_qwen_coder,
    create_deepseek_coder,
    get_available_providers,
    get_best_available_agent,
    LLAMA_PROVIDERS,
)
from .specialists import (
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

__all__ = [
    "AIAgent",
    "AgentConfig",
    "AgentResponse",
    "ModelType",
    "ClaudeAgent",
    "ChatGPTAgent",
    "GeminiAgent",
    "GrokAgent",
    "OllamaAgent",
    # MLX agents
    "MLXAgent",
    "create_mlx_coder",
    "create_mlx_general",
    # Llama Cloud agents
    "LlamaCloudAgent",
    "create_llama_70b",
    "create_llama_405b",
    "create_llama_fast",
    "create_llama_vision",
    "create_qwen_coder",
    "create_deepseek_coder",
    "get_available_providers",
    "get_best_available_agent",
    "LLAMA_PROVIDERS",
    # Specialized agents
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
]
