"""
Application Bootstrapper - Rapid Project Scaffolding
=====================================================

Generates application scaffolds quickly with optional AI enhancement.
Templates are minimal and production-ready.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AppSpec:
    """Specification for a new application"""
    name: str
    app_type: str  # fastapi, flask, cli, library
    description: str = ""
    features: List[str] = field(default_factory=list)  # auth, database, tests, docker
    database: Optional[str] = None  # sqlite, postgres, firestore
    python_version: str = "3.11"
    ai_integration: bool = True  # Include AI team hooks


@dataclass
class BootstrapResult:
    """Result of bootstrap operation"""
    success: bool
    created_files: List[str]
    output_dir: Path
    next_steps: List[str]
    errors: List[str] = field(default_factory=list)
    ai_enhanced: bool = False


class AppBootstrapper:
    """
    Generate application scaffolds quickly.

    Supports:
    - FastAPI REST APIs
    - CLI tools (typer)
    - Python libraries
    - Flask apps

    Each template is minimal, typed, and production-ready.
    """

    TEMPLATES = {
        "fastapi": {
            "base": [
                ("app/__init__.py", ""),
                ("app/main.py", "_fastapi_main"),
                ("app/config.py", "_fastapi_config"),
                ("app/routers/__init__.py", ""),
                ("app/models/__init__.py", ""),
                ("app/services/__init__.py", ""),
                ("tests/__init__.py", ""),
                ("tests/conftest.py", "_pytest_conftest"),
                ("tests/test_main.py", "_fastapi_test"),
                ("requirements.txt", "_fastapi_requirements"),
                (".env.template", "_env_template"),
                ("README.md", "_readme"),
            ],
            "features": {
                "docker": [
                    ("Dockerfile", "_dockerfile"),
                    ("docker-compose.yml", "_docker_compose"),
                    (".dockerignore", "_dockerignore"),
                ],
                "database": [
                    ("app/core/__init__.py", ""),
                    ("app/core/database.py", "_database"),
                ],
                "auth": [
                    ("app/routers/auth.py", "_auth_router"),
                    ("app/services/auth_service.py", "_auth_service"),
                ],
                "tests": [
                    ("tests/test_api.py", "_api_tests"),
                ],
                "ai": [
                    ("app/services/ai_team.py", "_ai_integration"),
                ],
            },
        },
        "cli": {
            "base": [
                ("src/__init__.py", ""),
                ("src/cli.py", "_cli_main"),
                ("src/commands/__init__.py", ""),
                ("src/commands/main.py", "_cli_commands"),
                ("tests/__init__.py", ""),
                ("tests/test_cli.py", "_cli_test"),
                ("pyproject.toml", "_pyproject"),
                ("README.md", "_readme"),
            ],
            "features": {
                "ai": [
                    ("src/ai_helper.py", "_cli_ai_helper"),
                ],
            },
        },
        "library": {
            "base": [
                ("src/__init__.py", "_lib_init"),
                ("src/core.py", "_lib_core"),
                ("tests/__init__.py", ""),
                ("tests/test_core.py", "_lib_test"),
                ("pyproject.toml", "_pyproject"),
                ("README.md", "_readme"),
            ],
            "features": {},
        },
    }

    def __init__(self):
        self._ai_team = None

    async def generate(
        self,
        spec: AppSpec,
        output_dir: Path,
        enhance_with_ai: bool = False,
    ) -> BootstrapResult:
        """
        Generate application scaffold.

        Args:
            spec: Application specification
            output_dir: Where to create the project
            enhance_with_ai: Use AI to improve generated code

        Returns:
            BootstrapResult with created files and next steps
        """
        if spec.app_type not in self.TEMPLATES:
            return BootstrapResult(
                success=False,
                created_files=[],
                output_dir=output_dir,
                next_steps=[],
                errors=[f"Unknown app type: {spec.app_type}. Available: {list(self.TEMPLATES.keys())}"],
            )

        template = self.TEMPLATES[spec.app_type]
        created_files = []
        errors = []

        try:
            # Create output directory
            output_dir = output_dir / spec.name
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate base files
            for file_path, template_name in template["base"]:
                try:
                    content = self._render(template_name, spec) if template_name else ""
                    full_path = output_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                    created_files.append(file_path)
                except Exception as e:
                    errors.append(f"Failed to create {file_path}: {e}")

            # Generate feature files
            for feature in spec.features:
                if feature in template.get("features", {}):
                    for file_path, template_name in template["features"][feature]:
                        try:
                            content = self._render(template_name, spec) if template_name else ""
                            full_path = output_dir / file_path
                            full_path.parent.mkdir(parents=True, exist_ok=True)
                            full_path.write_text(content)
                            created_files.append(file_path)
                        except Exception as e:
                            errors.append(f"Failed to create {file_path}: {e}")

            # AI enhancement pass
            ai_enhanced = False
            if enhance_with_ai and spec.ai_integration:
                try:
                    await self._enhance_with_ai(output_dir, spec)
                    ai_enhanced = True
                except Exception as e:
                    errors.append(f"AI enhancement failed: {e}")

            return BootstrapResult(
                success=len(errors) == 0,
                created_files=created_files,
                output_dir=output_dir,
                next_steps=self._get_next_steps(spec),
                errors=errors,
                ai_enhanced=ai_enhanced,
            )

        except Exception as e:
            return BootstrapResult(
                success=False,
                created_files=created_files,
                output_dir=output_dir,
                next_steps=[],
                errors=[str(e)],
            )

    def _render(self, template_name: str, spec: AppSpec) -> str:
        """Render a template"""
        templates = {
            "_fastapi_main": self._fastapi_main,
            "_fastapi_config": self._fastapi_config,
            "_fastapi_requirements": self._fastapi_requirements,
            "_fastapi_test": self._fastapi_test,
            "_pytest_conftest": self._pytest_conftest,
            "_env_template": self._env_template,
            "_readme": self._readme,
            "_dockerfile": self._dockerfile,
            "_docker_compose": self._docker_compose,
            "_dockerignore": self._dockerignore,
            "_database": self._database,
            "_auth_router": self._auth_router,
            "_auth_service": self._auth_service,
            "_api_tests": self._api_tests,
            "_ai_integration": self._ai_integration,
            "_cli_main": self._cli_main,
            "_cli_commands": self._cli_commands,
            "_cli_test": self._cli_test,
            "_cli_ai_helper": self._cli_ai_helper,
            "_pyproject": self._pyproject,
            "_lib_init": self._lib_init,
            "_lib_core": self._lib_core,
            "_lib_test": self._lib_test,
        }

        if template_name in templates:
            return templates[template_name](spec)
        return ""

    async def _enhance_with_ai(self, output_dir: Path, spec: AppSpec):
        """Use AI team to enhance generated code"""
        if self._ai_team is None:
            from ..orchestrator import AIDevTeam
            self._ai_team = AIDevTeam(project_name=spec.name, auto_setup=True)

        # Enhance Python files with better docstrings
        for py_file in output_dir.rglob("*.py"):
            content = py_file.read_text()
            if len(content) < 50:  # Skip tiny files
                continue

            # Only enhance substantial files
            response = await self._ai_team.ask(
                f"""Add concise docstrings to this Python code. Keep existing code unchanged.
Only add docstrings where missing. Be brief.

```python
{content}
```

Return only the improved code, no explanation.""",
                agent='local-qwen-coder-7b'
            )

            if response.success and "```python" in response.content:
                # Extract code block
                code = response.content.split("```python")[1].split("```")[0].strip()
                if code and len(code) > len(content) * 0.5:  # Sanity check
                    py_file.write_text(code)

    def _get_next_steps(self, spec: AppSpec) -> List[str]:
        """Get next steps for the developer"""
        steps = [
            f"cd {spec.name}",
            "python -m venv venv",
            "source venv/bin/activate",
            "pip install -r requirements.txt" if spec.app_type == "fastapi" else "pip install -e .",
        ]

        if spec.app_type == "fastapi":
            steps.append("uvicorn app.main:app --reload")
        elif spec.app_type == "cli":
            steps.append("python -m src.cli --help")

        if "tests" in spec.features:
            steps.append("pytest")

        return steps

    # =========================================================================
    # TEMPLATES
    # =========================================================================

    def _fastapi_main(self, spec: AppSpec) -> str:
        return f'''"""
{spec.name} - FastAPI Application
{"=" * (len(spec.name) + 22)}
{spec.description or "Generated by AI Team Platform"}
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="{spec.name}",
    description="{spec.description or 'API generated by AI Team Platform'}",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {{"status": "healthy", "service": "{spec.name}"}}


@app.get("/")
async def root():
    """Root endpoint"""
    return {{"message": "Welcome to {spec.name}", "docs": "/docs"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

    def _fastapi_config(self, spec: AppSpec) -> str:
        return f'''"""Configuration management"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    app_name: str = "{spec.name}"
    debug: bool = False

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Database (if enabled)
    database_url: str = "sqlite:///./app.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
'''

    def _fastapi_requirements(self, spec: AppSpec) -> str:
        reqs = [
            "fastapi>=0.109.0",
            "uvicorn[standard]>=0.27.0",
            "pydantic>=2.5.0",
            "pydantic-settings>=2.1.0",
            "python-dotenv>=1.0.0",
        ]
        if "database" in spec.features:
            reqs.extend(["sqlalchemy>=2.0.0", "aiosqlite>=0.19.0"])
        if "auth" in spec.features:
            reqs.extend(["python-jose[cryptography]>=3.3.0", "passlib[bcrypt]>=1.7.4"])
        if "tests" in spec.features:
            reqs.extend(["pytest>=7.4.0", "pytest-asyncio>=0.23.0", "httpx>=0.26.0"])
        return "\n".join(reqs)

    def _fastapi_test(self, spec: AppSpec) -> str:
        return f'''"""Tests for {spec.name}"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
'''

    def _pytest_conftest(self, spec: AppSpec) -> str:
        return '''"""Pytest configuration and fixtures"""

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
'''

    def _env_template(self, spec: AppSpec) -> str:
        return f'''# {spec.name} Environment Configuration
DEBUG=true
DATABASE_URL=sqlite:///./app.db
'''

    def _readme(self, spec: AppSpec) -> str:
        return f'''# {spec.name}

{spec.description or "Generated by AI Team Platform"}

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Features

{chr(10).join(f"- {f.title()}" for f in spec.features) if spec.features else "- Basic API structure"}

---
Generated by AI Team Platform
'''

    def _dockerfile(self, spec: AppSpec) -> str:
        return f'''FROM python:{spec.python_version}-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

    def _docker_compose(self, spec: AppSpec) -> str:
        return f'''version: "3.8"

services:
  {spec.name}:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
    volumes:
      - .:/app
'''

    def _dockerignore(self, spec: AppSpec) -> str:
        return '''__pycache__
*.pyc
.env
.git
.venv
venv
*.egg-info
'''

    def _database(self, spec: AppSpec) -> str:
        return '''"""Database configuration"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ..config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
'''

    def _auth_router(self, spec: AppSpec) -> str:
        return '''"""Authentication routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login and get access token"""
    # TODO(template): Implement authentication — placeholder for generated project code
    raise HTTPException(status_code=501, detail="Not implemented")
'''

    def _auth_service(self, spec: AppSpec) -> str:
        return '''"""Authentication service"""

from datetime import datetime, timedelta
from typing import Optional


class AuthService:
    """Handles authentication logic"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def create_token(self, user_id: str, expires_delta: timedelta = None) -> str:
        """Create JWT token"""
        # TODO(template): Implement JWT creation — placeholder for generated project code
        raise NotImplementedError

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode JWT token"""
        # TODO(template): Implement JWT verification — placeholder for generated project code
        raise NotImplementedError
'''

    def _api_tests(self, spec: AppSpec) -> str:
        return '''"""API integration tests"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAPI:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
'''

    def _ai_integration(self, spec: AppSpec) -> str:
        return f'''"""AI Team integration for {spec.name}"""

from typing import Optional


class AITeamHelper:
    """Helper for AI Team integration"""

    def __init__(self):
        self._team = None

    async def get_team(self):
        """Lazy load AI team"""
        if self._team is None:
            try:
                from ai_dev_team import AIDevTeam
                self._team = AIDevTeam(project_name="{spec.name}")
            except ImportError:
                raise RuntimeError("ai_dev_team not installed")
        return self._team

    async def ask(self, prompt: str) -> str:
        """Ask the AI team a question"""
        team = await self.get_team()
        response = await team.ask(prompt)
        return response.content if response.success else f"Error: {{response.error}}"


# Global helper instance
ai_helper = AITeamHelper()
'''

    def _cli_main(self, spec: AppSpec) -> str:
        return f'''"""
{spec.name} - CLI Application
{"=" * (len(spec.name) + 19)}
"""

import typer

app = typer.Typer(
    name="{spec.name}",
    help="{spec.description or 'CLI generated by AI Team Platform'}",
    add_completion=False,
)


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    """Main entry point"""
    if version:
        typer.echo("{spec.name} v0.1.0")
        raise typer.Exit()


# Import subcommands
from .commands import main as main_commands
app.add_typer(main_commands.app, name="run")


if __name__ == "__main__":
    app()
'''

    def _cli_commands(self, spec: AppSpec) -> str:
        return f'''"""Main commands for {spec.name}"""

import typer

app = typer.Typer(help="Main commands")


@app.command()
def hello(name: str = typer.Argument("World", help="Name to greet")):
    """Say hello"""
    typer.echo(f"Hello, {{name}}!")


@app.command()
def info():
    """Show information"""
    typer.echo("{spec.name} - {spec.description or 'CLI Application'}")
'''

    def _cli_test(self, spec: AppSpec) -> str:
        return f'''"""CLI tests"""

from typer.testing import CliRunner
from src.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "{spec.name}" in result.stdout


def test_hello():
    result = runner.invoke(app, ["run", "hello", "Test"])
    assert result.exit_code == 0
    assert "Hello, Test" in result.stdout
'''

    def _cli_ai_helper(self, spec: AppSpec) -> str:
        return '''"""AI helper for CLI"""

import asyncio
from typing import Optional


async def ask_ai(prompt: str) -> str:
    """Ask the AI team"""
    try:
        from ai_dev_team import AIDevTeam
        team = AIDevTeam(project_name="cli")
        response = await team.ask(prompt)
        return response.content
    except Exception as e:
        return f"AI unavailable: {e}"


def ask_ai_sync(prompt: str) -> str:
    """Synchronous wrapper for CLI usage"""
    return asyncio.run(ask_ai(prompt))
'''

    def _pyproject(self, spec: AppSpec) -> str:
        return f'''[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "{spec.name}"
version = "0.1.0"
description = "{spec.description or 'Generated by AI Team Platform'}"
requires-python = ">={spec.python_version}"
dependencies = [
    "typer>=0.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
]

[project.scripts]
{spec.name} = "src.cli:app"
'''

    def _lib_init(self, spec: AppSpec) -> str:
        return f'''"""
{spec.name}
{"=" * len(spec.name)}

{spec.description or "Python library"}
"""

__version__ = "0.1.0"

from .core import *
'''

    def _lib_core(self, spec: AppSpec) -> str:
        return f'''"""Core functionality for {spec.name}"""

__all__ = ["hello"]


def hello(name: str = "World") -> str:
    """Return a greeting."""
    return f"Hello, {{name}}!"
'''

    def _lib_test(self, spec: AppSpec) -> str:
        return f'''"""Tests for {spec.name}"""

from src import hello


def test_hello():
    assert hello() == "Hello, World!"
    assert hello("Test") == "Hello, Test!"
'''


# Convenience function
async def bootstrap_app(
    spec_or_name,
    output_dir = None,
    app_type: str = "fastapi",
    features: List[str] = None,
    enhance: bool = False,
) -> BootstrapResult:
    """
    Quick bootstrap function.

    Args:
        spec_or_name: Either an AppSpec object or string name for the app
        output_dir: Where to create the project (default: current directory)
        app_type: App type if name is string (fastapi, cli, library)
        features: Features if name is string (auth, database, tests, docker)
        enhance: Whether to use AI to improve generated code

    Examples:
        # Using AppSpec
        result = await bootstrap_app(AppSpec(name='myapp', app_type='fastapi'))

        # Using name string
        result = await bootstrap_app('myapp', features=['auth', 'tests'])
    """
    if isinstance(spec_or_name, AppSpec):
        spec = spec_or_name
    else:
        spec = AppSpec(
            name=spec_or_name,
            app_type=app_type,
            features=features or ["tests"],
        )

    output = Path(output_dir) if output_dir else Path.cwd()
    bootstrapper = AppBootstrapper()
    return await bootstrapper.generate(spec, output, enhance_with_ai=enhance)
