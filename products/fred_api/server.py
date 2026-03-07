"""
Fred API - Orchestration as a Service
======================================

Public REST API exposing FredAI's multi-agent orchestration capabilities.

Endpoints:
    POST /v1/collaborate  - Multi-agent collaboration
    POST /v1/ask          - Single-agent with smart routing
    POST /v1/review       - Code review
    POST /v1/stream       - SSE streaming response
    GET  /v1/agents       - List available agents
    GET  /v1/health       - Health check

Run: uvicorn products.fred_api.server:app --port 8080
"""

import asyncio
import json
import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Fred API",
    description="Multi-agent AI orchestration as a service",
    version="0.1.0",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
)

_cors_origins = os.getenv(
    "FRED_API_CORS_ORIGINS",
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

FRED_API_KEYS: set = set()
_raw = os.getenv("FRED_API_KEYS", "")
if _raw:
    FRED_API_KEYS = {k.strip() for k in _raw.split(",") if k.strip()}


async def verify_api_key(request: Request):
    """Verify API key from Authorization header. Skip if no keys configured."""
    if not FRED_API_KEYS:
        return  # No keys = open (dev mode)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    key = auth[7:]
    if key not in FRED_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Rate Limiting (in-memory token bucket) ───────────────────────────

_rate_buckets: Dict[str, Dict] = defaultdict(lambda: {"tokens": 60, "last": time.time()})
RATE_LIMIT = int(os.getenv("FRED_API_RATE_LIMIT", "60"))  # requests per minute
RATE_WINDOW = 60.0


async def rate_limit(request: Request):
    """Simple in-memory rate limiter by IP."""
    client_ip = request.client.host if request.client else "unknown"
    bucket = _rate_buckets[client_ip]

    now = time.time()
    elapsed = now - bucket["last"]
    bucket["tokens"] = min(RATE_LIMIT, bucket["tokens"] + elapsed * (RATE_LIMIT / RATE_WINDOW))
    bucket["last"] = now

    if bucket["tokens"] < 1:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    bucket["tokens"] -= 1


# ── Shared AIDevTeam singleton ───────────────────────────────────────

_team = None


def get_team():
    global _team
    if _team is None:
        from ai_dev_team.orchestrator import AIDevTeam
        _team = AIDevTeam(project_name="fred-api", enable_memory=True)
        logger.info(f"Fred API: initialized AIDevTeam with {len(_team.agents)} agents")
    return _team


# ── Request / Response Models ────────────────────────────────────────

class CollaborateRequest(BaseModel):
    prompt: str = Field(..., description="Task or question for the AI team")
    context: str = Field("", description="Additional context (code, docs)")
    mode: str = Field("parallel", description="Collaboration mode: parallel, sequential, consensus, single, fast")
    agents: Optional[List[str]] = Field(None, description="Specific agents to use (None = auto-route)")

class AskRequest(BaseModel):
    prompt: str = Field(..., description="Question for the best-matched agent")
    context: str = Field("", description="Additional context")

class ReviewRequest(BaseModel):
    code: str = Field(..., description="Code to review")
    language: str = Field("python", description="Programming language")
    focus: str = Field("quality", description="Review focus: quality, security, performance")

class StreamRequest(BaseModel):
    prompt: str = Field(..., description="Prompt to stream")
    agent: Optional[str] = Field(None, description="Specific agent (None = auto-route)")

class AgentInfo(BaseModel):
    name: str
    role: str
    model_type: str
    capabilities: List[str]

class CollaborateResponse(BaseModel):
    request_id: str
    answer: str
    agents_used: List[str]
    confidence: float
    mode: str
    total_time: float

class HealthResponse(BaseModel):
    status: str
    version: str
    agents_count: int
    timestamp: str


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/v1/health", response_model=HealthResponse)
async def health():
    """Health check - no auth required."""
    team = get_team()
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        agents_count=len(team.agents),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/v1/agents", response_model=List[AgentInfo], dependencies=[Depends(verify_api_key)])
async def list_agents():
    """List available AI agents."""
    team = get_team()
    agents = []
    for name, agent in team.agents.items():
        agents.append(AgentInfo(
            name=name,
            role=getattr(agent, "role", "agent"),
            model_type=agent.config.model_type.value,
            capabilities=agent.config.capabilities,
        ))
    return agents


@app.post("/v1/collaborate", response_model=CollaborateResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def collaborate(req: CollaborateRequest):
    """Multi-agent collaboration."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]

    try:
        result = await team.collaborate(
            prompt=req.prompt,
            context=req.context,
            agents=req.agents,
            mode=req.mode,
        )

        return CollaborateResponse(
            request_id=request_id,
            answer=result.final_answer,
            agents_used=result.participating_agents,
            confidence=result.confidence_score,
            mode=req.mode,
            total_time=result.total_time,
        )
    except Exception as e:
        logger.error(f"Collaboration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/ask", response_model=CollaborateResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def ask(req: AskRequest):
    """Single-agent with smart routing."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]

    try:
        result = await team.collaborate(
            prompt=req.prompt,
            context=req.context,
            mode="single",
        )

        return CollaborateResponse(
            request_id=request_id,
            answer=result.final_answer,
            agents_used=result.participating_agents,
            confidence=result.confidence_score,
            mode="single",
            total_time=result.total_time,
        )
    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/review", response_model=CollaborateResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def review(req: ReviewRequest):
    """Code review using the AI team."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]

    prompt = f"Review this {req.language} code for {req.focus}:\n\n```{req.language}\n{req.code}\n```"

    try:
        result = await team.collaborate(
            prompt=prompt,
            mode="parallel",
        )

        return CollaborateResponse(
            request_id=request_id,
            answer=result.final_answer,
            agents_used=result.participating_agents,
            confidence=result.confidence_score,
            mode="parallel",
            total_time=result.total_time,
        )
    except Exception as e:
        logger.error(f"Review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/stream", dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def stream(req: StreamRequest):
    """SSE streaming response from a single agent."""
    team = get_team()

    # Select agent
    if req.agent and req.agent in team.agents:
        agent = team.agents[req.agent]
    else:
        # Use router to pick best agent
        classification = team._task_router.classify(req.prompt)
        recommended = classification.recommended_agents
        agent = None
        for rec_name in recommended:
            if rec_name in team.agents:
                agent = team.agents[rec_name]
                break
        if agent is None:
            agent = next(iter(team.agents.values()), None)

    if agent is None:
        raise HTTPException(status_code=503, detail="No agents available")

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'start', 'agent': agent.name})}\n\n"

            async for token in agent.generate_stream(req.prompt):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Coding Agent Endpoints ───────────────────────────────────────────

from products.fred_api.coding_endpoints import router as coding_router
app.include_router(coding_router, dependencies=[Depends(verify_api_key), Depends(rate_limit)])


# ── Entry point ──────────────────────────────────────────────────────

def main():
    """Launch the Fred API server."""
    import uvicorn

    port = int(os.getenv("FRED_API_PORT", "8080"))
    logger.info(f"Starting Fred API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
