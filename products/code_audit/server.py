"""
Code Audit Service
==================

Automated security and quality audits using El Gringo's specialist agents.

Endpoints:
    POST /audit/security  - Security vulnerability scan
    POST /audit/review    - Code quality review
    POST /audit/full      - Full audit (security + quality)
    GET  /audit/health    - Health check

Reuses: SecurityAuditor, CodeReviewer from ai_dev_team.agents.specialists
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Code Audit Service",
    description="Automated security and quality audits powered by El Gringo",
    version="0.1.0",
    docs_url="/audit/docs",
)

_cors_origins = os.getenv(
    "CODE_AUDIT_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173"
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

AUDIT_API_KEYS: set = set()
_raw = os.getenv("CODE_AUDIT_API_KEYS", "")
if _raw:
    AUDIT_API_KEYS = {k.strip() for k in _raw.split(",") if k.strip()}


async def verify_api_key(request: Request):
    if not AUDIT_API_KEYS:
        return
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    if auth[7:] not in AUDIT_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Shared Team Instance ─────────────────────────────────────────────

_team = None


def get_team():
    global _team
    if _team is None:
        from ai_dev_team.orchestrator import AIDevTeam
        _team = AIDevTeam(project_name="code-audit", enable_memory=True)
    return _team


# ── Request / Response Models ────────────────────────────────────────

class AuditRequest(BaseModel):
    code: str = Field(..., description="Code to audit")
    language: str = Field("python", description="Programming language")
    filename: Optional[str] = Field(None, description="Filename for context")

class AuditResponse(BaseModel):
    audit_id: str
    audit_type: str
    findings: str
    agents_used: List[str]
    total_time: float
    timestamp: str


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/audit/health")
async def health():
    return {"status": "healthy", "service": "code-audit", "version": "0.1.0"}


@app.post("/audit/security", response_model=AuditResponse,
          dependencies=[Depends(verify_api_key)])
async def security_audit(req: AuditRequest):
    """Run a security-focused audit on the provided code."""
    team = get_team()
    audit_id = str(uuid.uuid4())[:8]

    prompt = (
        f"Perform a thorough security audit of this {req.language} code. "
        f"Look for: OWASP Top 10, hardcoded secrets, injection vulnerabilities, "
        f"path traversal, insecure deserialization, and auth issues.\n\n"
        f"```{req.language}\n{req.code}\n```"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="parallel")
        return AuditResponse(
            audit_id=audit_id,
            audit_type="security",
            findings=result.final_answer,
            agents_used=result.participating_agents,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/review", response_model=AuditResponse,
          dependencies=[Depends(verify_api_key)])
async def code_review(req: AuditRequest):
    """Run a quality-focused code review."""
    team = get_team()
    audit_id = str(uuid.uuid4())[:8]

    prompt = (
        f"Review this {req.language} code for quality. "
        f"Check: code style, error handling, performance, maintainability, "
        f"test coverage gaps, and best practices.\n\n"
        f"```{req.language}\n{req.code}\n```"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="parallel")
        return AuditResponse(
            audit_id=audit_id,
            audit_type="review",
            findings=result.final_answer,
            agents_used=result.participating_agents,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/full", response_model=AuditResponse,
          dependencies=[Depends(verify_api_key)])
async def full_audit(req: AuditRequest):
    """Run a comprehensive audit (security + quality + performance)."""
    team = get_team()
    audit_id = str(uuid.uuid4())[:8]

    prompt = (
        f"Perform a comprehensive audit of this {req.language} code covering:\n"
        f"1. SECURITY: vulnerabilities, injection, auth issues, secrets\n"
        f"2. QUALITY: code style, error handling, maintainability\n"
        f"3. PERFORMANCE: bottlenecks, memory leaks, inefficiencies\n\n"
        f"Provide findings organized by category with severity levels.\n\n"
        f"```{req.language}\n{req.code}\n```"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="consensus")
        return AuditResponse(
            audit_id=audit_id,
            audit_type="full",
            findings=result.final_answer,
            agents_used=result.participating_agents,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry point ──────────────────────────────────────────────────────

def main():
    import uvicorn
    port = int(os.getenv("CODE_AUDIT_PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
