"""
Shared AI Provider Configuration
================================

Centralized configuration for AI providers that can be shared
across AITeamPlatform and FreddyMac IDE.

This module provides:
- Unified provider definitions
- API key management
- Provider selection logic
- Configuration export/import
"""

import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProviderType(Enum):
    """AI Provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"
    GROQ = "groq"
    OLLAMA = "ollama"


@dataclass
class AIProviderConfig:
    """Configuration for a single AI provider"""
    id: str
    name: str
    type: ProviderType
    model: str
    endpoint: str
    description: str
    specialties: List[str] = field(default_factory=list)
    requires_api_key: bool = True
    is_local: bool = False
    max_tokens: int = 2000
    temperature: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            **asdict(self),
            "type": self.type.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIProviderConfig":
        """Create from dictionary"""
        data = data.copy()
        data["type"] = ProviderType(data["type"])
        return cls(**data)


# ============================================
# Default Provider Configurations
# ============================================

DEFAULT_PROVIDERS: List[AIProviderConfig] = [
    # OpenAI
    AIProviderConfig(
        id="gpt-4",
        name="GPT-4",
        type=ProviderType.OPENAI,
        model="gpt-4",
        endpoint="https://api.openai.com/v1/chat/completions",
        description="Advanced reasoning and complex problem solving",
        specialties=["complex-reasoning", "architecture", "planning", "coding"],
    ),
    AIProviderConfig(
        id="gpt-4o",
        name="GPT-4o",
        type=ProviderType.OPENAI,
        model="gpt-4o",
        endpoint="https://api.openai.com/v1/chat/completions",
        description="Latest GPT-4 with vision capabilities",
        specialties=["multimodal", "vision", "coding", "analysis"],
    ),
    AIProviderConfig(
        id="gpt-3.5",
        name="GPT-3.5 Turbo",
        type=ProviderType.OPENAI,
        model="gpt-3.5-turbo",
        endpoint="https://api.openai.com/v1/chat/completions",
        description="Fast and efficient for most tasks",
        specialties=["general-coding", "quick-tasks", "explanations"],
    ),

    # Anthropic
    AIProviderConfig(
        id="claude-3.5",
        name="Claude 3.5 Sonnet",
        type=ProviderType.ANTHROPIC,
        model="claude-3-5-sonnet-20241022",
        endpoint="https://api.anthropic.com/v1/messages",
        description="Excellent at code analysis and reasoning",
        specialties=["code-analysis", "security", "best-practices", "architecture"],
    ),
    AIProviderConfig(
        id="claude-3-opus",
        name="Claude 3 Opus",
        type=ProviderType.ANTHROPIC,
        model="claude-3-opus-20240229",
        endpoint="https://api.anthropic.com/v1/messages",
        description="Most capable Claude model",
        specialties=["complex-reasoning", "research", "detailed-analysis"],
    ),

    # Google
    AIProviderConfig(
        id="gemini-pro",
        name="Gemini Pro",
        type=ProviderType.GOOGLE,
        model="gemini-pro",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
        description="Strong at multimodal tasks and analysis",
        specialties=["analysis", "documentation", "research", "creative"],
    ),
    AIProviderConfig(
        id="gemini-flash",
        name="Gemini Flash",
        type=ProviderType.GOOGLE,
        model="gemini-2.0-flash",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        description="Fast Gemini model for quick tasks",
        specialties=["quick-tasks", "coding", "explanations"],
    ),

    # X.AI (Grok)
    AIProviderConfig(
        id="grok-3",
        name="Grok 3",
        type=ProviderType.XAI,
        model="grok-3-beta",
        endpoint="https://api.x.ai/v1/chat/completions",
        description="Latest Grok 3 model - powerful reasoning",
        specialties=["reasoning", "coding", "analysis", "creative-coding"],
    ),

    # Groq (Fast inference)
    AIProviderConfig(
        id="groq-llama",
        name="Groq Llama",
        type=ProviderType.GROQ,
        model="llama-3.3-70b-versatile",
        endpoint="https://api.groq.com/openai/v1/chat/completions",
        description="Ultra-fast Llama inference",
        specialties=["fast-coding", "quick-tasks", "explanations"],
    ),
    AIProviderConfig(
        id="groq-mixtral",
        name="Groq Mixtral",
        type=ProviderType.GROQ,
        model="mixtral-8x7b-32768",
        endpoint="https://api.groq.com/openai/v1/chat/completions",
        description="Fast Mixtral inference",
        specialties=["coding", "analysis", "reasoning"],
    ),

    # Ollama (Local)
    AIProviderConfig(
        id="ollama-qwen",
        name="Qwen Coder (Local)",
        type=ProviderType.OLLAMA,
        model="qwen2.5-coder:7b",
        endpoint="http://localhost:11434/api/generate",
        description="Local coding specialist",
        specialties=["coding", "debugging", "code-review"],
        requires_api_key=False,
        is_local=True,
    ),
    AIProviderConfig(
        id="ollama-llama",
        name="Llama 3.2 (Local)",
        type=ProviderType.OLLAMA,
        model="llama3.2:3b",
        endpoint="http://localhost:11434/api/generate",
        description="Quick local responses",
        specialties=["quick-help", "simple-questions"],
        requires_api_key=False,
        is_local=True,
    ),
]


@dataclass
class SharedConfig:
    """Shared configuration manager"""
    providers: List[AIProviderConfig] = field(default_factory=lambda: DEFAULT_PROVIDERS.copy())
    api_keys: Dict[str, str] = field(default_factory=dict)
    default_provider: str = "gpt-4"

    _config_path: Path = field(default=Path.home() / ".ai_team" / "shared_config.json", repr=False)

    def __post_init__(self):
        """Load environment variables for API keys"""
        env_keys = {
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
            ProviderType.GOOGLE: "GEMINI_API_KEY",
            ProviderType.XAI: "XAI_API_KEY",
            ProviderType.GROQ: "GROQ_API_KEY",
        }

        for provider_type, env_var in env_keys.items():
            key = os.getenv(env_var)
            if key:
                self.api_keys[provider_type.value] = key

    def get_provider(self, provider_id: str) -> Optional[AIProviderConfig]:
        """Get provider by ID"""
        for provider in self.providers:
            if provider.id == provider_id:
                return provider
        return None

    def get_providers_by_type(self, provider_type: ProviderType) -> List[AIProviderConfig]:
        """Get all providers of a specific type"""
        return [p for p in self.providers if p.type == provider_type]

    def get_available_providers(self) -> List[AIProviderConfig]:
        """Get providers that have API keys configured or are local"""
        available = []
        for provider in self.providers:
            if provider.is_local:
                available.append(provider)
            elif provider.type.value in self.api_keys:
                available.append(provider)
        return available

    def get_providers_for_specialty(self, specialty: str) -> List[AIProviderConfig]:
        """Get providers that match a specialty"""
        matching = []
        for provider in self.get_available_providers():
            if specialty in provider.specialties:
                matching.append(provider)
        return matching

    def set_api_key(self, provider_type: ProviderType, key: str):
        """Set API key for a provider type"""
        self.api_keys[provider_type.value] = key

        # Also set environment variable
        env_vars = {
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
            ProviderType.GOOGLE: "GEMINI_API_KEY",
            ProviderType.XAI: "XAI_API_KEY",
            ProviderType.GROQ: "GROQ_API_KEY",
        }
        if provider_type in env_vars:
            os.environ[env_vars[provider_type]] = key

    def select_best_provider(
        self,
        task: str,
        required_specialties: Optional[List[str]] = None
    ) -> Optional[AIProviderConfig]:
        """Select the best provider for a task"""
        available = self.get_available_providers()
        if not available:
            return None

        # If specialties required, filter
        if required_specialties:
            matching = []
            for provider in available:
                if any(spec in provider.specialties for spec in required_specialties):
                    matching.append(provider)
            if matching:
                available = matching

        # Priority based on task keywords
        task_lower = task.lower()

        if "complex" in task_lower or "architecture" in task_lower:
            for pid in ["gpt-4", "grok", "gemini-pro"]:
                provider = self.get_provider(pid)
                if provider in available:
                    return provider

        if "fast" in task_lower or "quick" in task_lower:
            for pid in ["groq-llama", "gpt-3.5", "ollama-llama"]:
                provider = self.get_provider(pid)
                if provider in available:
                    return provider

        if "creative" in task_lower:
            for pid in ["grok", "gemini-pro"]:
                provider = self.get_provider(pid)
                if provider in available:
                    return provider

        if "code" in task_lower or "coding" in task_lower:
            for pid in ["gpt-4", "grok", "ollama-qwen"]:
                provider = self.get_provider(pid)
                if provider in available:
                    return provider

        # Return default or first available
        default = self.get_provider(self.default_provider)
        if default in available:
            return default

        return available[0] if available else None

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration to dictionary"""
        return {
            "providers": [p.to_dict() for p in self.providers],
            "api_keys": {k: "***" for k in self.api_keys},  # Mask keys
            "default_provider": self.default_provider,
        }

    def to_typescript(self) -> str:
        """Export configuration as TypeScript code for FreddyMac IDE"""
        providers_ts = []
        for p in self.providers:
            provider_entry = "  {\n"
            provider_entry += f"    id: '{p.id}',\n"
            provider_entry += f"    name: '{p.name}',\n"
            provider_entry += f"    type: '{p.type.value}',\n"
            provider_entry += f"    model: '{p.model}',\n"
            provider_entry += f"    endpoint: '{p.endpoint}',\n"
            provider_entry += f"    description: '{p.description}',\n"
            provider_entry += f"    specialties: {json.dumps(p.specialties)},\n"
            provider_entry += f"    requiresApiKey: {str(p.requires_api_key).lower()},\n"
            provider_entry += f"    isLocal: {str(p.is_local).lower()},\n"
            provider_entry += "  }"
            providers_ts.append(provider_entry)

        newline = "\n"
        providers_joined = f",{newline}".join(providers_ts)

        return f"""// Auto-generated from AITeamPlatform shared_config.py
// Do not edit manually - regenerate with: python -c "from elgringo.core.shared_config import shared_config; print(shared_config.to_typescript())"

export interface AIProviderConfig {{
  id: string;
  name: string;
  type: 'openai' | 'anthropic' | 'google' | 'xai' | 'groq' | 'ollama';
  model: string;
  endpoint: string;
  description: string;
  specialties: string[];
  requiresApiKey: boolean;
  isLocal: boolean;
}}

export const AI_PROVIDERS: AIProviderConfig[] = [
{providers_joined}
];

export const DEFAULT_PROVIDER = '{self.default_provider}';
"""

    def save(self):
        """Save configuration to file"""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls) -> "SharedConfig":
        """Load configuration from file"""
        config = cls()
        if config._config_path.exists():
            try:
                with open(config._config_path) as f:
                    json.load(f)
                # Don't load masked API keys
            except Exception:
                pass
        return config


# Singleton instance
shared_config = SharedConfig()


def get_shared_config() -> SharedConfig:
    """Get the shared configuration instance"""
    return shared_config


# ============================================
# Project Management
# ============================================

@dataclass
class ProjectConfig:
    """Configuration for a managed project"""
    name: str
    path: str
    description: str
    domain: str
    tech_stack: List[str] = field(default_factory=list)
    priority: str = "medium"
    status: str = "active"
    ai_roles: List[str] = field(default_factory=list)

    def get_full_path(self, platform_dir: Optional[Path] = None) -> Path:
        """Get the full filesystem path to the project"""
        if platform_dir is None:
            platform_dir = Path(__file__).parent.parent
        return (platform_dir / self.path).resolve()


class ProjectManager:
    """Manages projects available to the AI team"""

    def __init__(self):
        self._platform_dir = Path(__file__).parent.parent
        self._config_path = self._platform_dir / "config" / "projects.yaml"
        self._projects: Dict[str, ProjectConfig] = {}
        self._load_projects()

    def _load_projects(self):
        """Load projects from config/projects.yaml"""
        if not self._config_path.exists():
            return

        try:
            import yaml
        except ImportError:
            # Fallback to basic parsing if PyYAML not available
            return

        try:
            with open(self._config_path) as f:
                data = yaml.safe_load(f)

            if data and "projects" in data:
                for project_id, project_data in data["projects"].items():
                    self._projects[project_id] = ProjectConfig(
                        name=project_data.get("name", project_id),
                        path=project_data.get("path", f"projects/{project_id}"),
                        description=project_data.get("description", ""),
                        domain=project_data.get("domain", "general"),
                        tech_stack=project_data.get("tech_stack", []),
                        priority=project_data.get("priority", "medium"),
                        status=project_data.get("status", "active"),
                        ai_roles=project_data.get("ai_roles", []),
                    )
        except Exception:
            pass

    def list_projects(self) -> List[ProjectConfig]:
        """Get all managed projects"""
        return list(self._projects.values())

    def get_project(self, project_id: str) -> Optional[ProjectConfig]:
        """Get a specific project by ID"""
        return self._projects.get(project_id)

    def get_active_projects(self) -> List[ProjectConfig]:
        """Get all active projects"""
        return [p for p in self._projects.values() if p.status == "active"]

    def get_projects_by_domain(self, domain: str) -> List[ProjectConfig]:
        """Get projects by domain"""
        return [p for p in self._projects.values() if p.domain == domain]

    def get_project_path(self, project_id: str) -> Optional[Path]:
        """Get the full path to a project"""
        project = self.get_project(project_id)
        if project:
            return project.get_full_path(self._platform_dir)
        return None


# Singleton instance
project_manager = ProjectManager()


def get_project_manager() -> ProjectManager:
    """Get the project manager instance"""
    return project_manager
