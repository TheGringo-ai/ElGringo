"""
Test Generator Service
======================

AI-powered unit test generation, coverage analysis, and test quality improvement
using El Gringo's multi-agent collaboration.

Endpoints:
    GET  /tests/health   - Health check
    POST /tests/generate - Generate unit tests for source code
    POST /tests/analyze  - Analyze test coverage and suggest missing tests
    POST /tests/improve  - Improve existing tests for better coverage/quality

Reuses: AIDevTeam orchestrator from elgringo.orchestrator
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Test Generator Service",
    description="AI-powered unit test generation and improvement powered by El Gringo",
    version="0.1.0",
    docs_url="/tests/docs",
)

_cors_origins = os.getenv(
    "TEST_GEN_CORS_ORIGINS",
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

# ── Auth ─────────────────────────────────────────────────────────────

TEST_GEN_API_KEYS: set = set()
_raw = os.getenv("TEST_GEN_API_KEYS", "")
if _raw:
    TEST_GEN_API_KEYS = {k.strip() for k in _raw.split(",") if k.strip()}


async def verify_api_key(request: Request):
    """Verify Bearer token against TEST_GEN_API_KEYS. Skipped when no keys are configured."""
    if not TEST_GEN_API_KEYS:
        return
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    if auth[7:] not in TEST_GEN_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Shared Team Instance ─────────────────────────────────────────────

_team = None


def get_team():
    """Lazy-load the AIDevTeam to avoid import overhead at module level."""
    global _team
    if _team is None:
        from elgringo.orchestrator import AIDevTeam

        _team = AIDevTeam(project_name="test-generator", enable_memory=True)
    return _team


# ── Supported Frameworks ─────────────────────────────────────────────

SUPPORTED_FRAMEWORKS = {
    "python": ["pytest", "unittest"],
    "javascript": ["jest", "vitest"],
    "typescript": ["jest", "vitest"],
    "go": ["go-test"],
    "rust": ["cargo-test"],
    "java": ["junit"],
}

DEFAULT_FRAMEWORK = {
    "python": "pytest",
    "javascript": "jest",
    "typescript": "vitest",
    "go": "go-test",
    "rust": "cargo-test",
    "java": "junit",
}


def _resolve_framework(language: str, framework: Optional[str]) -> str:
    """Resolve the test framework, falling back to the language default."""
    lang = language.lower()
    if framework:
        return framework
    return DEFAULT_FRAMEWORK.get(lang, "pytest")


# ── Request / Response Models ────────────────────────────────────────


class GenerateRequest(BaseModel):
    code: str = Field(..., description="Source code to generate tests for")
    language: str = Field("python", description="Programming language of the source code")
    framework: Optional[str] = Field(
        None,
        description="Test framework to use (e.g. pytest, jest, vitest, go-test). "
        "Auto-detected from language if omitted.",
    )
    filename: Optional[str] = Field(None, description="Filename for additional context")
    focus: Optional[str] = Field(
        None,
        description="Specific area to focus tests on (e.g. 'edge cases', 'error handling')",
    )


class AnalyzeRequest(BaseModel):
    code: str = Field(..., description="Source code to analyze")
    tests: Optional[str] = Field(None, description="Existing test code, if any")
    language: str = Field("python", description="Programming language")
    framework: Optional[str] = Field(None, description="Test framework in use")
    filename: Optional[str] = Field(None, description="Filename for context")


class ImproveRequest(BaseModel):
    code: str = Field(..., description="Source code under test")
    tests: str = Field(..., description="Existing test code to improve")
    language: str = Field("python", description="Programming language")
    framework: Optional[str] = Field(None, description="Test framework in use")
    filename: Optional[str] = Field(None, description="Filename for context")
    goals: Optional[str] = Field(
        None,
        description="Improvement goals (e.g. 'increase branch coverage', "
        "'add parameterized tests', 'improve readability')",
    )


class TestGeneratorResponse(BaseModel):
    request_id: str
    action: str
    result: str
    framework: str
    agents_used: List[str]
    total_time: float
    timestamp: str


# ── Endpoints ────────────────────────────────────────────────────────


@app.get("/tests/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "test-generator",
        "version": "0.1.0",
        "supported_frameworks": SUPPORTED_FRAMEWORKS,
    }


@app.post(
    "/tests/generate",
    response_model=TestGeneratorResponse,
    dependencies=[Depends(verify_api_key)],
)
async def generate_tests(req: GenerateRequest):
    """Generate unit tests for the provided source code using AI agents."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]
    framework = _resolve_framework(req.language, req.framework)

    focus_section = ""
    if req.focus:
        focus_section = f"\nFocus area: {req.focus}\n"

    filename_section = ""
    if req.filename:
        filename_section = f"Filename: {req.filename}\n"

    prompt = (
        f"Generate comprehensive unit tests for the following {req.language} code "
        f"using the **{framework}** test framework.\n\n"
        f"{filename_section}"
        f"{focus_section}"
        f"Requirements:\n"
        f"1. Cover all public functions/methods/classes\n"
        f"2. Include happy path, edge cases, and error cases\n"
        f"3. Use descriptive test names that explain the scenario\n"
        f"4. Add appropriate setup/teardown where needed\n"
        f"5. Mock external dependencies appropriately\n"
        f"6. Return ONLY the test code, ready to run\n\n"
        f"Source code:\n```{req.language}\n{req.code}\n```"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="parallel")
        return TestGeneratorResponse(
            request_id=request_id,
            action="generate",
            result=result.final_answer,
            framework=framework,
            agents_used=result.participating_agents,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.exception("Test generation failed for request %s", request_id)
        raise HTTPException(status_code=500, detail=f"Test generation failed: {e}")


@app.post(
    "/tests/analyze",
    response_model=TestGeneratorResponse,
    dependencies=[Depends(verify_api_key)],
)
async def analyze_coverage(req: AnalyzeRequest):
    """Analyze test coverage and suggest what tests are missing."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]
    framework = _resolve_framework(req.language, req.framework)

    existing_tests_section = ""
    if req.tests:
        existing_tests_section = (
            f"\nExisting tests:\n```{req.language}\n{req.tests}\n```\n"
        )

    filename_section = ""
    if req.filename:
        filename_section = f"Filename: {req.filename}\n"

    prompt = (
        f"Analyze the test coverage for the following {req.language} code "
        f"(framework: {framework}).\n\n"
        f"{filename_section}"
        f"Source code:\n```{req.language}\n{req.code}\n```\n"
        f"{existing_tests_section}\n"
        f"Provide:\n"
        f"1. **Coverage Summary**: Which functions/branches/paths are tested vs untested\n"
        f"2. **Missing Tests**: Specific test cases that should be added\n"
        f"3. **Risk Areas**: Untested code paths that pose the highest risk\n"
        f"4. **Recommended Priority**: Order of test cases to implement by impact\n"
        f"5. **Suggested Test Code**: Ready-to-use test stubs for the top missing cases\n"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="parallel")
        return TestGeneratorResponse(
            request_id=request_id,
            action="analyze",
            result=result.final_answer,
            framework=framework,
            agents_used=result.participating_agents,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.exception("Coverage analysis failed for request %s", request_id)
        raise HTTPException(status_code=500, detail=f"Coverage analysis failed: {e}")


@app.post(
    "/tests/improve",
    response_model=TestGeneratorResponse,
    dependencies=[Depends(verify_api_key)],
)
async def improve_tests(req: ImproveRequest):
    """Improve existing tests for better quality, coverage, and maintainability."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]
    framework = _resolve_framework(req.language, req.framework)

    goals_section = ""
    if req.goals:
        goals_section = f"\nImprovement goals: {req.goals}\n"

    filename_section = ""
    if req.filename:
        filename_section = f"Filename: {req.filename}\n"

    prompt = (
        f"Improve the following {req.language} test suite (framework: {framework}).\n\n"
        f"{filename_section}"
        f"{goals_section}"
        f"Source code under test:\n```{req.language}\n{req.code}\n```\n\n"
        f"Current tests:\n```{req.language}\n{req.tests}\n```\n\n"
        f"Improve the tests by:\n"
        f"1. **Coverage**: Add tests for uncovered branches and edge cases\n"
        f"2. **Quality**: Improve assertions, use more specific matchers\n"
        f"3. **Readability**: Better test names, clearer arrange-act-assert structure\n"
        f"4. **Robustness**: Add parameterized tests where appropriate\n"
        f"5. **Mocking**: Ensure external dependencies are properly isolated\n"
        f"6. **Performance**: Remove redundant setup, optimize slow tests\n\n"
        f"Return the COMPLETE improved test file, ready to replace the original.\n"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="consensus")
        return TestGeneratorResponse(
            request_id=request_id,
            action="improve",
            result=result.final_answer,
            framework=framework,
            agents_used=result.participating_agents,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.exception("Test improvement failed for request %s", request_id)
        raise HTTPException(status_code=500, detail=f"Test improvement failed: {e}")


# ── Entry point ──────────────────────────────────────────────────────


def main():
    import uvicorn

    port = int(os.getenv("TEST_GEN_PORT", "8082"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
