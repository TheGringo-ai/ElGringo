"""
Template Registry
=================
Central registry for all code templates. The AI team uses this to find,
search, and combine templates for building applications.

Usage:
    from templates.registry import TemplateRegistry

    registry = TemplateRegistry()
    templates = registry.search("auth fastapi")
    code = registry.get_template("backend/auth/jwt_auth")
    combined = registry.combine(["backend/fastapi/crud_api", "backend/auth/jwt_auth"])
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

TEMPLATES_DIR = Path(__file__).parent

@dataclass
class Template:
    """Represents a code template"""
    id: str
    name: str
    category: str
    subcategory: str
    description: str
    file_path: Path
    language: str
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)

    @property
    def content(self) -> str:
        """Load template content"""
        return self.file_path.read_text()

    def render(self, **kwargs) -> str:
        """Render template with variable substitution"""
        content = self.content
        for key, value in kwargs.items():
            content = content.replace(f"{{{{ {key} }}}}", value)
            content = content.replace(f"{{{key}}}", value)
        return content


class TemplateRegistry:
    """Registry of all available templates"""

    def __init__(self, templates_dir: Path = TEMPLATES_DIR):
        self.templates_dir = templates_dir
        self.templates: Dict[str, Template] = {}
        self._load_templates()

    def _load_templates(self):
        """Scan templates directory and register all templates"""

        # Backend templates
        self._register_template(
            id="backend/fastapi/crud_api",
            name="FastAPI CRUD API",
            category="backend",
            subcategory="fastapi",
            description="Complete REST API with Pydantic models, validation, and error handling",
            file_path=self.templates_dir / "backend/fastapi/crud_api.py",
            language="python",
            tags=["api", "rest", "crud", "fastapi", "pydantic"],
            dependencies=["fastapi", "pydantic", "uvicorn"],
        )

        self._register_template(
            id="backend/auth/jwt_auth",
            name="JWT Authentication",
            category="backend",
            subcategory="auth",
            description="Complete JWT auth system with login, registration, and protected routes",
            file_path=self.templates_dir / "backend/auth/jwt_auth.py",
            language="python",
            tags=["auth", "jwt", "security", "login", "register"],
            dependencies=["fastapi", "python-jose", "passlib", "bcrypt"],
        )

        self._register_template(
            id="backend/database/sqlalchemy_models",
            name="SQLAlchemy Models",
            category="backend",
            subcategory="database",
            description="Production-ready database models with relationships, mixins, and utilities",
            file_path=self.templates_dir / "backend/database/sqlalchemy_models.py",
            language="python",
            tags=["database", "orm", "sqlalchemy", "postgresql", "models"],
            dependencies=["sqlalchemy", "asyncpg", "alembic"],
        )

        # Frontend templates
        self._register_template(
            id="frontend/react/DataTable",
            name="Data Table Component",
            category="frontend",
            subcategory="react",
            description="Fully-featured data table with sorting, filtering, pagination, and selection",
            file_path=self.templates_dir / "frontend/react/DataTable.tsx",
            language="typescript",
            tags=["react", "table", "data", "sorting", "filtering", "pagination"],
            dependencies=["@tanstack/react-table", "lucide-react"],
        )

        self._register_template(
            id="frontend/react/Form",
            name="Form Components",
            category="frontend",
            subcategory="react",
            description="Reusable form components with validation using react-hook-form and zod",
            file_path=self.templates_dir / "frontend/react/Form.tsx",
            language="typescript",
            tags=["react", "form", "validation", "input", "zod"],
            dependencies=["react-hook-form", "@hookform/resolvers", "zod", "lucide-react"],
        )

        self._register_template(
            id="frontend/react/DashboardLayout",
            name="Dashboard Layout",
            category="frontend",
            subcategory="react",
            description="Complete dashboard shell with sidebar, header, and content area",
            file_path=self.templates_dir / "frontend/react/DashboardLayout.tsx",
            language="typescript",
            tags=["react", "dashboard", "layout", "sidebar", "navigation"],
            dependencies=["lucide-react"],
        )

        # Infrastructure templates
        self._register_template(
            id="infrastructure/docker/python",
            name="Python Dockerfile",
            category="infrastructure",
            subcategory="docker",
            description="Multi-stage Dockerfile for production Python applications",
            file_path=self.templates_dir / "infrastructure/docker/Dockerfile.python",
            language="dockerfile",
            tags=["docker", "python", "production", "container"],
            dependencies=[],
        )

        self._register_template(
            id="infrastructure/docker/compose",
            name="Docker Compose",
            category="infrastructure",
            subcategory="docker",
            description="Full-stack development environment with backend, frontend, database, and cache",
            file_path=self.templates_dir / "infrastructure/docker/docker-compose.yml",
            language="yaml",
            tags=["docker", "compose", "postgres", "redis", "nginx", "fullstack"],
            dependencies=[],
        )

        self._register_template(
            id="infrastructure/cicd/github-actions",
            name="GitHub Actions CI/CD",
            category="infrastructure",
            subcategory="cicd",
            description="Complete CI/CD pipeline with tests, security scanning, and deployment",
            file_path=self.templates_dir / "infrastructure/cicd/github-actions.yml",
            language="yaml",
            tags=["cicd", "github", "actions", "testing", "deployment", "docker"],
            dependencies=[],
        )

    def _register_template(self, **kwargs):
        """Register a template"""
        template = Template(**kwargs)
        if template.file_path.exists():
            self.templates[template.id] = template

    def get(self, template_id: str) -> Optional[Template]:
        """Get a template by ID"""
        return self.templates.get(template_id)

    def get_content(self, template_id: str) -> Optional[str]:
        """Get template content by ID"""
        template = self.get(template_id)
        return template.content if template else None

    def list_all(self) -> List[Template]:
        """List all templates"""
        return list(self.templates.values())

    def list_by_category(self, category: str) -> List[Template]:
        """List templates by category"""
        return [t for t in self.templates.values() if t.category == category]

    def list_by_language(self, language: str) -> List[Template]:
        """List templates by language"""
        return [t for t in self.templates.values() if t.language == language]

    def search(self, query: str) -> List[Template]:
        """Search templates by query"""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for template in self.templates.values():
            # Score based on matches in different fields
            score = 0
            searchable = f"{template.name} {template.description} {' '.join(template.tags)}".lower()

            for word in query_words:
                if word in searchable:
                    score += 1
                if word in template.tags:
                    score += 2  # Boost for exact tag match

            if score > 0:
                results.append((template, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in results]

    def combine(self, template_ids: List[str], separator: str = "\n\n# " + "=" * 70 + "\n\n") -> str:
        """Combine multiple templates into one file"""
        parts = []
        all_deps = set()

        for tid in template_ids:
            template = self.get(tid)
            if template:
                parts.append(f"# Template: {template.name}\n# Source: {template.id}\n\n{template.content}")
                all_deps.update(template.dependencies)

        # Add dependencies header
        deps_header = f"# Combined Dependencies:\n# pip install {' '.join(sorted(all_deps))}\n"

        return deps_header + separator + separator.join(parts)

    def get_dependencies(self, template_ids: List[str]) -> Dict[str, List[str]]:
        """Get all dependencies for a set of templates"""
        python_deps = set()
        npm_deps = set()

        for tid in template_ids:
            template = self.get(tid)
            if template:
                if template.language == "python":
                    python_deps.update(template.dependencies)
                elif template.language in ["typescript", "javascript"]:
                    npm_deps.update(template.dependencies)

        return {
            "pip": sorted(python_deps),
            "npm": sorted(npm_deps),
        }

    def suggest_for_task(self, task_description: str) -> List[Template]:
        """Suggest templates based on a task description"""
        # Keywords mapping to templates
        suggestions = []
        task_lower = task_description.lower()

        # Backend suggestions
        if any(word in task_lower for word in ["api", "rest", "endpoint", "backend", "server"]):
            if self.get("backend/fastapi/crud_api"):
                suggestions.append(self.get("backend/fastapi/crud_api"))

        if any(word in task_lower for word in ["auth", "login", "register", "user", "jwt", "token"]):
            if self.get("backend/auth/jwt_auth"):
                suggestions.append(self.get("backend/auth/jwt_auth"))

        if any(word in task_lower for word in ["database", "model", "sql", "postgres", "orm"]):
            if self.get("backend/database/sqlalchemy_models"):
                suggestions.append(self.get("backend/database/sqlalchemy_models"))

        # Frontend suggestions
        if any(word in task_lower for word in ["table", "list", "data", "grid"]):
            if self.get("frontend/react/DataTable"):
                suggestions.append(self.get("frontend/react/DataTable"))

        if any(word in task_lower for word in ["form", "input", "validation", "submit"]):
            if self.get("frontend/react/Form"):
                suggestions.append(self.get("frontend/react/Form"))

        if any(word in task_lower for word in ["dashboard", "admin", "layout", "sidebar"]):
            if self.get("frontend/react/DashboardLayout"):
                suggestions.append(self.get("frontend/react/DashboardLayout"))

        return suggestions

    def to_dict(self) -> Dict[str, Any]:
        """Export registry as dictionary"""
        return {
            tid: {
                "name": t.name,
                "category": t.category,
                "subcategory": t.subcategory,
                "description": t.description,
                "language": t.language,
                "tags": t.tags,
                "dependencies": t.dependencies,
            }
            for tid, t in self.templates.items()
        }

    def print_catalog(self):
        """Print a formatted catalog of all templates"""
        print("\n" + "=" * 70)
        print("TEMPLATE CATALOG")
        print("=" * 70)

        categories = {}
        for t in self.templates.values():
            if t.category not in categories:
                categories[t.category] = []
            categories[t.category].append(t)

        for category, templates in sorted(categories.items()):
            print(f"\n## {category.upper()}")
            print("-" * 40)
            for t in templates:
                print(f"  {t.id}")
                print(f"    {t.name}: {t.description[:60]}...")
                print(f"    Tags: {', '.join(t.tags)}")
                print()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_registry = None

def get_registry() -> TemplateRegistry:
    """Get the global template registry"""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
    return _registry

def search_templates(query: str) -> List[Template]:
    """Search templates"""
    return get_registry().search(query)

def get_template(template_id: str) -> Optional[str]:
    """Get template content"""
    return get_registry().get_content(template_id)

def suggest_templates(task: str) -> List[Template]:
    """Suggest templates for a task"""
    return get_registry().suggest_for_task(task)


if __name__ == "__main__":
    registry = TemplateRegistry()
    registry.print_catalog()

    print("\n" + "=" * 70)
    print("SEARCH TEST: 'auth api'")
    print("=" * 70)
    for t in registry.search("auth api"):
        print(f"  - {t.id}: {t.name}")

    print("\n" + "=" * 70)
    print("SUGGESTION TEST: 'Build a user management dashboard'")
    print("=" * 70)
    for t in registry.suggest_for_task("Build a user management dashboard"):
        print(f"  - {t.id}: {t.name}")
