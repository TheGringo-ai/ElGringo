"""
Project Context System — stores project profiles, loads key files,
and generates project-aware system prompts for agents.

Used by the orchestrator to auto-inject project conventions into
collaborate calls and specialize agent behavior per project.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Persistent storage path
PROFILES_DIR = Path.home() / ".ai-dev-team" / "projects"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


class ProjectProfile:
    """A project's tech stack, conventions, and key file excerpts."""

    def __init__(
        self,
        name: str,
        tech_stack: str = "",
        backend_framework: str = "",
        frontend_framework: str = "",
        database: str = "",
        auth: str = "",
        key_patterns: List[str] = None,
        key_files: Dict[str, str] = None,
        agent_hint: str = "",
    ):
        self.name = name
        self.tech_stack = tech_stack
        self.backend_framework = backend_framework
        self.frontend_framework = frontend_framework
        self.database = database
        self.auth = auth
        self.key_patterns = key_patterns or []
        self.key_files = key_files or {}  # filename -> excerpt (first N lines)
        self.agent_hint = agent_hint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tech_stack": self.tech_stack,
            "backend_framework": self.backend_framework,
            "frontend_framework": self.frontend_framework,
            "database": self.database,
            "auth": self.auth,
            "key_patterns": self.key_patterns,
            "key_files": self.key_files,
            "agent_hint": self.agent_hint,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})

    def generate_system_prompt(self) -> str:
        """Generate a system prompt that makes agents project-aware."""
        lines = [f"You are working on '{self.name}'."]

        if self.tech_stack:
            lines.append(f"Tech stack: {self.tech_stack}")
        if self.backend_framework:
            lines.append(f"Backend: {self.backend_framework}")
        if self.frontend_framework:
            lines.append(f"Frontend: {self.frontend_framework}")
        if self.database:
            lines.append(f"Database: {self.database}")
        if self.auth:
            lines.append(f"Auth: {self.auth}")

        if self.key_patterns:
            lines.append("\nMANDATORY CONVENTIONS — follow these exactly:")
            for i, pattern in enumerate(self.key_patterns, 1):
                lines.append(f"  {i}. {pattern}")

        if self.agent_hint:
            lines.append(f"\n{self.agent_hint}")

        return "\n".join(lines)

    def generate_context_block(self) -> str:
        """Generate a context block with key file excerpts for prompt injection."""
        if not self.key_files:
            return ""

        lines = [f"PROJECT FILES ({self.name}):"]
        for filename, content in self.key_files.items():
            lines.append(f"\n--- {filename} ---")
            lines.append(content)

        context = "\n".join(lines)
        # Cap at 4000 chars to avoid prompt bloat
        if len(context) > 4000:
            context = context[:4000] + "\n... (truncated)"
        return context


class ProjectContextManager:
    """Manages project profiles with file-based persistence."""

    def __init__(self):
        self._profiles: Dict[str, ProjectProfile] = {}
        self._load_all()

    def _profile_path(self, name: str) -> Path:
        safe_name = name.replace("/", "_").replace("\\", "_")
        return PROFILES_DIR / f"{safe_name}.json"

    def _load_all(self):
        """Load all saved profiles from disk."""
        for path in PROFILES_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                profile = ProjectProfile.from_dict(data)
                self._profiles[profile.name] = profile
            except Exception as e:
                logger.warning(f"Failed to load profile {path}: {e}")

    def save_profile(self, profile: ProjectProfile):
        """Save a project profile to disk."""
        self._profiles[profile.name] = profile
        path = self._profile_path(profile.name)
        path.write_text(json.dumps(profile.to_dict(), indent=2))
        logger.info(f"Saved project profile: {profile.name}")

    def get_profile(self, name: str) -> Optional[ProjectProfile]:
        return self._profiles.get(name)

    def list_profiles(self) -> List[str]:
        return list(self._profiles.keys())

    def delete_profile(self, name: str) -> bool:
        if name in self._profiles:
            del self._profiles[name]
            path = self._profile_path(name)
            if path.exists():
                path.unlink()
            return True
        return False

    def load_project_files(
        self,
        profile_name: str,
        project_path: str,
        file_patterns: List[str] = None,
        max_lines_per_file: int = 50,
    ) -> ProjectProfile:
        """
        Load key files from a project directory into the profile.

        Auto-detects important files if no patterns specified:
        - requirements.txt / package.json
        - Main entry point (main.py, app.py, App.jsx)
        - First router/route file found
        - Config/deps files
        """
        profile = self.get_profile(profile_name) or ProjectProfile(name=profile_name)
        project = Path(project_path)

        if not project.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")

        # Auto-detect key files if none specified
        if not file_patterns:
            file_patterns = []
            candidates = [
                "requirements.txt", "package.json", "pyproject.toml",
                "main.py", "app.py", "app/main.py", "backend/main.py",
                "src/App.jsx", "src/App.tsx", "frontend/src/App.jsx",
                "deps.py", "backend/deps.py", "app/dependencies.py",
                "Dockerfile", "docker-compose.yml",
            ]
            for c in candidates:
                if (project / c).exists():
                    file_patterns.append(c)

            # Also grab first router file if exists
            for router_dir in ["routers", "backend/routers", "app/routers", "routes"]:
                router_path = project / router_dir
                if router_path.is_dir():
                    routers = sorted(router_path.glob("*.py"))
                    # Skip __init__.py, grab first real router
                    for r in routers:
                        if r.name != "__init__.py":
                            file_patterns.append(f"{router_dir}/{r.name}")
                            break
                    break

        # Read files
        for pattern in file_patterns:
            filepath = project / pattern
            if filepath.exists() and filepath.is_file():
                try:
                    lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
                    excerpt = "\n".join(lines[:max_lines_per_file])
                    profile.key_files[pattern] = excerpt
                except Exception as e:
                    logger.warning(f"Failed to read {filepath}: {e}")

        # Auto-detect tech stack from files
        if not profile.tech_stack:
            profile.tech_stack = self._detect_tech_stack(profile.key_files)

        self.save_profile(profile)
        return profile

    def _detect_tech_stack(self, key_files: Dict[str, str]) -> str:
        """Infer tech stack from file contents."""
        parts = []
        for filename, content in key_files.items():
            lower = content.lower()
            if filename == "requirements.txt":
                if "fastapi" in lower:
                    parts.append("FastAPI")
                if "django" in lower:
                    parts.append("Django")
                if "flask" in lower:
                    parts.append("Flask")
                if "firebase" in lower:
                    parts.append("Firebase")
                if "pandas" in lower:
                    parts.append("Pandas")
            elif filename == "package.json":
                if "react" in lower:
                    parts.append("React")
                if "vue" in lower:
                    parts.append("Vue")
                if "next" in lower:
                    parts.append("Next.js")
                if "vite" in lower:
                    parts.append("Vite")
                if "tailwind" in lower:
                    parts.append("Tailwind CSS")
        return " + ".join(parts) if parts else ""
