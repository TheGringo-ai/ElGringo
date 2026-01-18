"""
Configuration utilities for AI Dev Team
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AgentSettings:
    """Settings for an individual agent"""
    enabled: bool = True
    max_tokens: int = 4000
    temperature: float = 0.7
    model_name: Optional[str] = None


@dataclass
class Config:
    """Configuration for AI Dev Team"""
    # Project settings
    project_name: str = "default"

    # Memory settings
    enable_memory: bool = True
    enable_learning: bool = True
    memory_storage_dir: str = "~/.ai-dev-team/memory"
    use_firestore: bool = False

    # Agent settings
    claude_settings: AgentSettings = field(default_factory=AgentSettings)
    chatgpt_settings: AgentSettings = field(default_factory=AgentSettings)
    gemini_settings: AgentSettings = field(default_factory=AgentSettings)
    grok_settings: AgentSettings = field(default_factory=AgentSettings)

    # Collaboration settings
    default_mode: str = "parallel"
    max_consensus_rounds: int = 3
    consensus_threshold: float = 0.8

    # Performance settings
    enable_caching: bool = True
    cache_ttl_hours: int = 24
    request_timeout: int = 120

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "project_name": self.project_name,
            "enable_memory": self.enable_memory,
            "enable_learning": self.enable_learning,
            "memory_storage_dir": self.memory_storage_dir,
            "use_firestore": self.use_firestore,
            "default_mode": self.default_mode,
            "max_consensus_rounds": self.max_consensus_rounds,
            "consensus_threshold": self.consensus_threshold,
            "enable_caching": self.enable_caching,
            "cache_ttl_hours": self.cache_ttl_hours,
            "request_timeout": self.request_timeout,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary"""
        return cls(
            project_name=data.get("project_name", "default"),
            enable_memory=data.get("enable_memory", True),
            enable_learning=data.get("enable_learning", True),
            memory_storage_dir=data.get("memory_storage_dir", "~/.ai-dev-team/memory"),
            use_firestore=data.get("use_firestore", False),
            default_mode=data.get("default_mode", "parallel"),
            max_consensus_rounds=data.get("max_consensus_rounds", 3),
            consensus_threshold=data.get("consensus_threshold", 0.8),
            enable_caching=data.get("enable_caching", True),
            cache_ttl_hours=data.get("cache_ttl_hours", 24),
            request_timeout=data.get("request_timeout", 120),
        )

    def save(self, path: str):
        """Save config to file"""
        config_path = Path(os.path.expanduser(path))
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


def load_config(path: Optional[str] = None) -> Config:
    """
    Load configuration from file or environment.

    Order of precedence:
    1. Specified path
    2. ./ai-dev-team.json
    3. ~/.ai-dev-team/config.json
    4. Default config
    """
    # Try specified path
    if path and os.path.exists(path):
        with open(path) as f:
            return Config.from_dict(json.load(f))

    # Try local config
    local_config = Path("./ai-dev-team.json")
    if local_config.exists():
        with open(local_config) as f:
            return Config.from_dict(json.load(f))

    # Try user config
    user_config = Path(os.path.expanduser("~/.ai-dev-team/config.json"))
    if user_config.exists():
        with open(user_config) as f:
            return Config.from_dict(json.load(f))

    # Return default config
    return Config()


def get_api_keys() -> Dict[str, Optional[str]]:
    """Get all configured API keys"""
    return {
        "anthropic": os.getenv("ANTHROPIC_API_KEY"),
        "openai": os.getenv("OPENAI_API_KEY"),
        "gemini": os.getenv("GEMINI_API_KEY"),
        "xai": os.getenv("XAI_API_KEY"),
    }


def check_api_keys() -> Dict[str, bool]:
    """Check which API keys are configured"""
    keys = get_api_keys()
    return {name: bool(key) for name, key in keys.items()}
