"""
Documentation Generator Service
================================

AI-powered documentation generation using FredAI's specialist agents.

Endpoints:
    POST /docs/readme        - Generate comprehensive README.md from code/structure
    POST /docs/api           - Generate API documentation from route definitions
    POST /docs/architecture  - Generate architecture docs with Mermaid diagrams
    GET  /docs/health        - Health check

Reuses: AIDevTeam from ai_dev_team.orchestrator
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# -- App -------------------------------------------------------------------

app = FastAPI(
    title="Documentation Generator Service",
    description="AI-powered documentation generation powered by FredAI",
    version="0.1.0",
    docs_url="/docs/openapi",
)

_cors_origins = os.getenv(
    "DOC_GEN_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Usage Analytics ──────────────────────────────────────────────────
from middleware.analytics import UsageAnalyticsMiddleware, get_analytics_store
from middleware.analytics_api import analytics_router

app.add_middleware(UsageAnalyticsMiddleware, store=get_analytics_store())
app.include_router(analytics_router)

# -- Auth ------------------------------------------------------------------

DOC_GEN_API_KEYS: set = set()
_raw = os.getenv("DOC_GEN_API_KEYS", "")
if _raw:
    DOC_GEN_API_KEYS = {k.strip() for k in _raw.split(",") if k.strip()}


async def verify_api_key(request: Request):
    """Verify Bearer token against DOC_GEN_API_KEYS env var.
    If no keys are configured, all requests are allowed (dev mode).
    """
    if not DOC_GEN_API_KEYS:
        return
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    if auth[7:] not in DOC_GEN_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")


# -- Shared Team Instance --------------------------------------------------

_team = None


def get_team():
    """Lazy-load the AIDevTeam to avoid import overhead at startup."""
    global _team
    if _team is None:
        from ai_dev_team.orchestrator import AIDevTeam

        _team = AIDevTeam(project_name="doc-generator", enable_memory=True)
    return _team


# -- Request / Response Models ---------------------------------------------


class FileEntry(BaseModel):
    """A single source file with its path and content."""

    path: str = Field(..., description="Relative file path (e.g. 'src/main.py')")
    content: str = Field(..., description="Full file content")
    language: Optional[str] = Field(
        None, description="Programming language (auto-detected from extension if omitted)"
    )


class ReadmeRequest(BaseModel):
    """Input for README generation."""

    project_name: str = Field(..., description="Name of the project")
    description: Optional[str] = Field(
        None, description="Short project description (AI will generate one if omitted)"
    )
    files: List[FileEntry] = Field(
        ..., min_length=1, description="Source files to analyze"
    )
    directory_tree: Optional[str] = Field(
        None, description="Directory tree output (e.g. from `tree` command)"
    )
    include_badges: bool = Field(
        True, description="Include status/tech badges in the README"
    )
    include_contributing: bool = Field(
        True, description="Include a Contributing section"
    )
    include_license: bool = Field(
        True, description="Include a License section placeholder"
    )


class ApiDocRequest(BaseModel):
    """Input for API documentation generation."""

    project_name: str = Field(..., description="Name of the API project")
    framework: str = Field(
        "auto",
        description="Web framework: 'fastapi', 'flask', 'express', or 'auto' for detection",
    )
    files: List[FileEntry] = Field(
        ..., min_length=1, description="API source files containing route definitions"
    )
    base_url: Optional[str] = Field(
        None, description="Base URL for the API (e.g. 'https://api.example.com/v1')"
    )
    include_examples: bool = Field(
        True, description="Include cURL/httpx request examples"
    )
    include_schemas: bool = Field(
        True, description="Include request/response schema tables"
    )
    output_format: str = Field(
        "markdown",
        description="Output format: 'markdown' or 'openapi-yaml'",
    )


class ArchitectureRequest(BaseModel):
    """Input for architecture documentation generation."""

    project_name: str = Field(..., description="Name of the project")
    files: List[FileEntry] = Field(
        ..., min_length=1, description="Source files to analyze for architecture"
    )
    directory_tree: Optional[str] = Field(
        None, description="Directory tree output"
    )
    tech_stack: Optional[Dict[str, str]] = Field(
        None,
        description="Known tech stack, e.g. {'backend': 'FastAPI', 'db': 'Firestore'}",
    )
    include_c4_diagrams: bool = Field(
        True, description="Include C4-model-style Mermaid diagrams"
    )
    include_data_flow: bool = Field(
        True, description="Include data-flow diagrams"
    )
    include_deployment: bool = Field(
        True, description="Include deployment architecture diagram"
    )


class DocResponse(BaseModel):
    """Standard response for all documentation endpoints."""

    doc_id: str
    doc_type: str
    content: str
    agents_used: List[str]
    total_time: float
    timestamp: str


# -- Helpers ---------------------------------------------------------------


def _format_files_for_prompt(files: List[FileEntry], max_chars: int = 120_000) -> str:
    """Format file entries into a prompt-friendly string, respecting a character budget."""
    parts: List[str] = []
    total = 0
    for f in files:
        lang = f.language or _guess_language(f.path)
        block = f"### {f.path}\n```{lang}\n{f.content}\n```\n"
        if total + len(block) > max_chars:
            parts.append(
                f"### {f.path}\n(truncated - {len(f.content)} chars, "
                f"exceeds context budget)\n"
            )
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts)


def _guess_language(path: str) -> str:
    """Best-effort language detection from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".sh": "bash",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".toml": "toml",
        ".sql": "sql",
        ".html": "html",
        ".css": "css",
        ".md": "markdown",
        ".dockerfile": "dockerfile",
    }
    for ext, lang in ext_map.items():
        if path.lower().endswith(ext):
            return lang
    if path.lower().endswith("dockerfile") or path.lower().startswith("dockerfile"):
        return "dockerfile"
    return "text"


# -- Endpoints -------------------------------------------------------------


@app.get("/docs/health")
async def health():
    """Health check endpoint (no auth required)."""
    return {"status": "healthy", "service": "doc-generator", "version": "0.1.0"}


@app.post(
    "/docs/readme",
    response_model=DocResponse,
    dependencies=[Depends(verify_api_key)],
)
async def generate_readme(req: ReadmeRequest):
    """Generate a comprehensive README.md from the provided source files.

    The AI team analyzes the code structure, identifies key components,
    and produces a well-organized README with installation instructions,
    usage examples, and configuration details.
    """
    team = get_team()
    doc_id = str(uuid.uuid4())[:8]

    files_text = _format_files_for_prompt(req.files)
    tree_section = (
        f"\n## Directory Structure\n```\n{req.directory_tree}\n```\n"
        if req.directory_tree
        else ""
    )
    description_hint = (
        f"Project description provided by the user: {req.description}\n"
        if req.description
        else "Infer the project description from the code.\n"
    )

    sections = ["Installation", "Usage", "Configuration", "Project Structure"]
    if req.include_badges:
        sections.insert(0, "Badges (shields.io style)")
    if req.include_contributing:
        sections.append("Contributing")
    if req.include_license:
        sections.append("License")

    prompt = (
        f"Generate a comprehensive, production-quality README.md for the project "
        f"'{req.project_name}'.\n\n"
        f"{description_hint}\n"
        f"Required sections: {', '.join(sections)}.\n\n"
        f"Guidelines:\n"
        f"- Write clear, professional Markdown\n"
        f"- Include actual code examples derived from the source files\n"
        f"- Detect the tech stack and list dependencies accurately\n"
        f"- Make installation steps concrete and copy-pasteable\n"
        f"- If environment variables are used, list them in a table\n"
        f"- Output ONLY the README.md content (raw Markdown), no wrapper\n"
        f"{tree_section}\n"
        f"## Source Files\n{files_text}"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="consensus")
        return DocResponse(
            doc_id=doc_id,
            doc_type="readme",
            content=result.final_answer,
            agents_used=result.participating_agents,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.exception("README generation failed for project '%s'", req.project_name)
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/docs/api",
    response_model=DocResponse,
    dependencies=[Depends(verify_api_key)],
)
async def generate_api_docs(req: ApiDocRequest):
    """Generate API documentation from route definitions.

    Supports FastAPI, Flask, and Express frameworks. The AI team
    extracts endpoints, parameters, request/response schemas, and
    produces organized API reference documentation.
    """
    team = get_team()
    doc_id = str(uuid.uuid4())[:8]

    files_text = _format_files_for_prompt(req.files)
    base_url_hint = (
        f"Base URL: {req.base_url}\n" if req.base_url else ""
    )
    framework_hint = (
        f"The framework is {req.framework}.\n"
        if req.framework != "auto"
        else "Auto-detect the web framework from the code.\n"
    )

    prompt = (
        f"Generate comprehensive API documentation for '{req.project_name}'.\n\n"
        f"{framework_hint}"
        f"{base_url_hint}\n"
        f"Output format: {req.output_format}\n\n"
        f"For each endpoint, document:\n"
        f"- HTTP method and path\n"
        f"- Description of what it does\n"
        f"- Path/query parameters with types and descriptions\n"
        f"- Request body schema (if any)\n"
        f"- Response schema with example\n"
        f"- Authentication requirements\n"
        f"- Possible error responses\n"
    )

    if req.include_examples:
        prompt += "- Include cURL and Python httpx request examples for each endpoint\n"
    if req.include_schemas:
        prompt += "- Include request/response schema tables in Markdown\n"

    prompt += (
        f"\nOrganize endpoints by resource/router group.\n"
        f"Output ONLY the documentation content, no wrapper.\n\n"
        f"## API Source Files\n{files_text}"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="consensus")
        return DocResponse(
            doc_id=doc_id,
            doc_type="api",
            content=result.final_answer,
            agents_used=result.participating_agents,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.exception("API doc generation failed for project '%s'", req.project_name)
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/docs/architecture",
    response_model=DocResponse,
    dependencies=[Depends(verify_api_key)],
)
async def generate_architecture_docs(req: ArchitectureRequest):
    """Generate architecture documentation with Mermaid diagrams.

    The AI team analyzes the codebase to identify components, layers,
    data flows, and deployment topology. Output includes C4-model diagrams,
    data-flow diagrams, and deployment architecture rendered as Mermaid.
    """
    team = get_team()
    doc_id = str(uuid.uuid4())[:8]

    files_text = _format_files_for_prompt(req.files)
    tree_section = (
        f"\n## Directory Structure\n```\n{req.directory_tree}\n```\n"
        if req.directory_tree
        else ""
    )
    tech_stack_section = ""
    if req.tech_stack:
        items = "\n".join(f"- **{k}**: {v}" for k, v in req.tech_stack.items())
        tech_stack_section = f"\n## Known Tech Stack\n{items}\n"

    diagram_instructions = []
    if req.include_c4_diagrams:
        diagram_instructions.append(
            "- C4 Context and Container diagrams as Mermaid flowcharts "
            "(use `graph TD` or `graph LR`)"
        )
    if req.include_data_flow:
        diagram_instructions.append(
            "- Data flow diagram showing how data moves through the system "
            "(use `sequenceDiagram` or `flowchart`)"
        )
    if req.include_deployment:
        diagram_instructions.append(
            "- Deployment architecture diagram showing infrastructure components "
            "(use `graph TD` with subgraphs for environments)"
        )

    diagrams_text = "\n".join(diagram_instructions) if diagram_instructions else ""

    prompt = (
        f"Generate comprehensive architecture documentation for '{req.project_name}'.\n\n"
        f"Include the following sections:\n"
        f"1. **System Overview** - High-level description of the system\n"
        f"2. **Component Architecture** - Major components and their responsibilities\n"
        f"3. **Technology Stack** - Languages, frameworks, databases, infrastructure\n"
        f"4. **Module Structure** - How the codebase is organized\n"
        f"5. **Key Design Decisions** - Architectural patterns and rationale\n"
        f"6. **Diagrams** (as Mermaid code blocks):\n"
        f"{diagrams_text}\n"
        f"7. **API Boundaries** - How components communicate\n"
        f"8. **Data Model** - Key entities and relationships\n"
        f"9. **Security Architecture** - Auth, authorization, data protection\n"
        f"10. **Scalability Considerations** - How the system scales\n\n"
        f"Guidelines:\n"
        f"- All diagrams MUST use Mermaid syntax inside ```mermaid code blocks\n"
        f"- Derive everything from the actual code, do not fabricate components\n"
        f"- Be specific about file paths and module names\n"
        f"- Output ONLY the architecture document content (raw Markdown), no wrapper\n"
        f"{tree_section}"
        f"{tech_stack_section}\n"
        f"## Source Files\n{files_text}"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="consensus")
        return DocResponse(
            doc_id=doc_id,
            doc_type="architecture",
            content=result.final_answer,
            agents_used=result.participating_agents,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.exception(
            "Architecture doc generation failed for project '%s'", req.project_name
        )
        raise HTTPException(status_code=500, detail=str(e))


# -- Entry point -----------------------------------------------------------


def main():
    import uvicorn

    port = int(os.getenv("DOC_GEN_PORT", "8083"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
