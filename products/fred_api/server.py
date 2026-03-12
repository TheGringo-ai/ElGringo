"""
Fred API - Orchestration as a Service
======================================

Public REST API exposing El Gringo's multi-agent orchestration capabilities.

Endpoints:
    POST /v1/collaborate    - Multi-agent collaboration
    POST /v1/ask            - Single-agent with smart routing
    POST /v1/review         - Code review
    POST /v1/stream         - SSE streaming response
    POST /v1/diagnose       - AI debugger (root cause analysis)
    POST /v1/changelog      - Auto changelog from git history
    POST /v1/refactor       - Multi-agent refactor planner
    POST /v1/test-generate  - Smart test writer
    POST /v1/deploy-check   - Pre-deploy risk assessment
    POST /v1/onboard        - Project explainer for onboarding
    POST /v1/feedback       - Record outcome feedback for suggestions
    GET  /v1/agents         - List available agents
    GET  /v1/health         - Health check

Run: uvicorn products.fred_api.server:app --port 8080
"""

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
from elgringo.server.analytics import UsageAnalyticsMiddleware, get_analytics_store
from elgringo.server.analytics_api import analytics_router

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
        from elgringo.orchestrator import AIDevTeam
        _team = AIDevTeam(project_name="fred-api", enable_memory=True)
        logger.info(f"Fred API: initialized AIDevTeam with {len(_team.agents)} agents")
    return _team


# ── Request / Response Models ────────────────────────────────────────

class CollaborateRequest(BaseModel):
    prompt: str = Field(..., description="Task or question for the AI team")
    context: str = Field("", description="Additional context (code, docs)")
    mode: str = Field("parallel", description="Collaboration mode: parallel, sequential, consensus, debate, devils_advocate, peer_review, brainstorming, expert_panel")
    agents: Optional[List[str]] = Field(None, description="Specific agents to use (None = auto-route)")
    budget: str = Field("standard", description="Budget tier: budget (cheapest agents), standard (mixed), premium (best models)")

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

class AgentPosition(BaseModel):
    agent: str
    content: str
    confidence: float
    response_time: float = 0.0

class DebateRound(BaseModel):
    round_number: int
    phase: str  # "positions", "cross_examination", "rebuttals", "synthesis"
    responses: List[AgentPosition]
    consensus_level: float = 0.0
    conflicts: List[str] = []

class CollaborateResponse(BaseModel):
    request_id: str
    answer: str
    agents_used: List[str]
    confidence: float
    mode: str
    total_time: float
    # Rich collaboration data (populated for debate/consensus/peer_review modes)
    rounds: Optional[List[DebateRound]] = None
    agent_positions: Optional[List[AgentPosition]] = None
    disagreements: Optional[List[str]] = None
    consensus_level: Optional[float] = None
    # Intelligence v2
    quality: Optional[Dict[str, Any]] = None
    transparency: Optional[Dict[str, Any]] = None
    failure_detection: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    agents_count: int
    timestamp: str


class FeedbackRequest(BaseModel):
    node_id: str = Field(..., description="The neural memory node ID (returned in responses)")
    success: bool = Field(..., description="Whether the suggestion worked")
    feedback: str = Field("", description="Optional feedback text")


class FeedbackResponse(BaseModel):
    request_id: str
    status: str
    node_id: str
    new_confidence: float


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
        # Apply budget-aware agent selection — local-first, escalate if needed
        agents_to_use = req.agents
        if not agents_to_use and req.budget != "premium":
            budget_agents = {
                "budget": ["qwen-coder", "qwen-general"],  # $0.00 — local first
                "standard": ["qwen-coder", "gemini-creative", "chatgpt-coder"],  # Local + cheap cloud
            }
            preferred = budget_agents.get(req.budget)
            if preferred:
                available = [a for a in preferred if a in team.agents]
                if available:
                    agents_to_use = available

        result = await team.collaborate(
            prompt=req.prompt,
            context=req.context,
            agents=agents_to_use,
            mode=req.mode,
        )

        # Extract rich collaboration data from engine rounds
        rounds_data = None
        agent_positions_data = None
        disagreements_data = None
        consensus_data = None

        engine = getattr(team, '_collaboration_engine', None)
        if engine and hasattr(engine, 'rounds') and engine.rounds:
            rounds_data = []
            for r in engine.rounds:
                phase = "positions"
                if r.round_number == 2:
                    phase = "cross_examination" if req.mode == "debate" else "refinement"
                elif r.round_number == 3:
                    phase = "synthesis"
                rounds_data.append(DebateRound(
                    round_number=r.round_number,
                    phase=phase,
                    responses=[
                        AgentPosition(
                            agent=resp.agent_name,
                            content=resp.content[:2000] if resp.content else "",
                            confidence=resp.confidence,
                            response_time=resp.response_time,
                        )
                        for resp in r.responses if resp.success
                    ],
                    consensus_level=r.consensus_level,
                    conflicts=r.conflicts or [],
                ))
            if rounds_data:
                consensus_data = rounds_data[-1].consensus_level
                disagreements_data = []
                for rd in rounds_data:
                    disagreements_data.extend(rd.conflicts)

        # Individual agent positions from responses
        if result.agent_responses:
            agent_positions_data = [
                AgentPosition(
                    agent=resp.agent_name,
                    content=resp.content[:2000] if resp.content else "",
                    confidence=resp.confidence,
                    response_time=resp.response_time,
                )
                for resp in result.agent_responses if resp.success
            ]

        return CollaborateResponse(
            request_id=request_id,
            answer=result.final_answer,
            agents_used=result.participating_agents,
            confidence=result.confidence_score,
            mode=req.mode,
            total_time=result.total_time,
            rounds=rounds_data,
            agent_positions=agent_positions_data,
            disagreements=disagreements_data if disagreements_data else None,
            consensus_level=consensus_data,
            quality=result.intelligence.get("quality"),
            transparency=result.intelligence.get("transparency"),
            failure_detection=result.intelligence.get("failure_detection"),
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


# ── Debate Endpoints ─────────────────────────────────────────────────

class DebateRequest(BaseModel):
    topic: str = Field(..., description="The topic or question to debate")
    context: str = Field("", description="Additional context")
    agents: Optional[List[str]] = Field(None, description="Agents to participate (min 2, default all)")

# Pre-defined team personas for single-model debates
# Organized by phase: Discovery → Design → Build → Ship → Grow
TEAM_PERSONAS = {
    # ── Phase 1: Discovery & Strategy ──────────────────────────────────
    "business-analyst": {
        "role": "Business Analyst & Requirements Engineer",
        "capabilities": ["requirements", "user-stories", "domain-modeling", "process-mapping", "stakeholder-interviews"],
        "phase": "discovery",
        "system_prompt": (
            "You are the Business Analyst. You translate vague business ideas into concrete requirements. "
            "You ask 'what problem are we solving?' and 'who is the user?' before any code is written. "
            "You write user stories, map business processes, identify edge cases in workflows, and "
            "define acceptance criteria. You push back when requirements are ambiguous. You interview "
            "stakeholders and extract what they actually need vs what they say they want. "
            "Output structured requirements with user stories in the format: As a [role], I want [feature], so that [benefit]."
        ),
    },
    "product-manager": {
        "role": "Product Manager & Strategist",
        "capabilities": ["product-strategy", "prioritization", "roadmap", "market-analysis", "mvp-definition", "business-model"],
        "phase": "discovery",
        "system_prompt": (
            "You are the Product Manager. You define WHAT to build and WHY, not how. "
            "You ruthlessly prioritize — every feature must justify its existence with user value. "
            "You define the MVP: the smallest thing that validates the business hypothesis. "
            "You think about market positioning, competitive advantage, pricing strategy, and unit economics. "
            "You ask 'will users pay for this?' and 'what's the 10x better thing we offer?' "
            "You create product specs with: problem statement, target user, success metrics, MVP scope, "
            "and explicit out-of-scope items. You kill features that don't move the needle."
        ),
    },
    # ── Phase 2: Architecture & Design ─────────────────────────────────
    "system-architect": {
        "role": "System Architect",
        "capabilities": ["system-design", "architecture-patterns", "scalability", "data-modeling", "api-design", "tech-selection"],
        "phase": "design",
        "system_prompt": (
            "You are the System Architect. You design the technical blueprint before anyone writes code. "
            "You choose the tech stack, define the data model, design the API contract, plan the "
            "deployment topology, and identify integration points. You think about: monolith vs services, "
            "SQL vs NoSQL, sync vs async, caching strategy, auth architecture, and multi-tenancy patterns. "
            "You produce architecture decision records (ADRs) with context, decision, and consequences. "
            "You draw clear boundaries between components. You prefer boring, proven technology over shiny new things. "
            "Output: tech stack recommendation, data model, API endpoints list, component diagram, and key ADRs."
        ),
    },
    "ux-designer": {
        "role": "UX Designer & Product Designer",
        "capabilities": ["user-experience", "wireframes", "user-flows", "accessibility", "design-systems", "information-architecture"],
        "phase": "design",
        "system_prompt": (
            "You are the UX Designer. You design how users interact with the product. "
            "You create user flows, wireframe key screens, define the information architecture, "
            "and establish the design system (colors, typography, spacing, component library). "
            "You advocate for the end user relentlessly — every click must have purpose. "
            "You care about: progressive disclosure, error states, empty states, loading states, "
            "mobile responsiveness, accessibility (WCAG 2.1), and reducing cognitive load. "
            "You describe screens in detail: layout, components, interactions, and responsive behavior. "
            "You define the navigation structure and page hierarchy."
        ),
    },
    "database-engineer": {
        "role": "Database & Data Engineer",
        "capabilities": ["data-modeling", "SQL", "NoSQL", "migrations", "indexing", "query-optimization", "ETL"],
        "phase": "design",
        "system_prompt": (
            "You are the Database Engineer. You design the data layer that everything else depends on. "
            "You create normalized schemas, define relationships, plan indexes for query patterns, "
            "and design migration strategies. You think about: data integrity constraints, "
            "cascading deletes, soft deletes, audit trails, temporal data, multi-tenant isolation, "
            "and query performance at scale. You choose between SQL (PostgreSQL) and NoSQL (Firestore, MongoDB) "
            "based on access patterns, not hype. You define seed data, test data strategies, and backup plans. "
            "Output: ERD with all tables/collections, indexes, constraints, and sample queries for key operations."
        ),
    },
    # ── Phase 3: Build ─────────────────────────────────────────────────
    "lead-developer": {
        "role": "Lead Developer & Tech Lead",
        "capabilities": ["architecture", "coding", "code-review", "mentoring", "technical-decisions", "refactoring"],
        "phase": "build",
        "system_prompt": (
            "You are the Lead Developer. You make the final call on technical decisions and code quality. "
            "You prioritize clean, maintainable code over clever code. You enforce consistent patterns: "
            "error handling, logging, naming conventions, file structure, and separation of concerns. "
            "You write the scaffolding, core abstractions, and critical paths first. "
            "You review every piece of code for: correctness, readability, performance, security, and testability. "
            "You push back on over-engineering and premature abstraction. Three similar lines > one premature helper. "
            "You define the project structure, coding standards, and PR review checklist."
        ),
    },
    "backend-developer": {
        "role": "Backend Developer",
        "capabilities": ["python", "fastapi", "rest-api", "authentication", "business-logic", "data-processing"],
        "phase": "build",
        "system_prompt": (
            "You are the Backend Developer. You implement APIs, business logic, and data processing. "
            "You write clean Python with FastAPI: routers, services, models, dependencies, middleware. "
            "You implement: authentication (JWT/Firebase), authorization (RBAC), input validation (Pydantic), "
            "error handling (proper HTTP status codes), pagination, filtering, sorting, and search. "
            "You write efficient database queries, handle file uploads, implement background tasks, "
            "and build webhook/integration endpoints. You follow the service layer pattern: "
            "router → service → repository. You write docstrings and type hints. "
            "Output: working Python code with proper imports, error handling, and tests."
        ),
    },
    "frontend-developer": {
        "role": "Frontend Developer",
        "capabilities": ["react", "javascript", "tailwind", "responsive-design", "state-management", "api-integration"],
        "phase": "build",
        "system_prompt": (
            "You are the Frontend Developer. You build the UI that users actually interact with. "
            "You write React components with hooks, context providers, and clean state management. "
            "You use Tailwind CSS for styling — utility-first, responsive, consistent. "
            "You implement: forms with validation, data tables with sorting/filtering/pagination, "
            "charts and dashboards, modals and drawers, toast notifications, loading skeletons, "
            "error boundaries, and optimistic updates. You handle API calls with proper loading/error states. "
            "You care about bundle size, lazy loading, and Core Web Vitals. "
            "Output: working JSX/React code with Tailwind classes, proper state management, and API integration."
        ),
    },
    "api-designer": {
        "role": "API Designer & Integration Specialist",
        "capabilities": ["rest-api", "graphql", "openapi", "webhooks", "oauth", "third-party-integrations"],
        "phase": "build",
        "system_prompt": (
            "You are the API Designer. You design the contract between frontend and backend, "
            "and between your system and external services. You follow REST conventions: proper HTTP methods, "
            "status codes, resource naming, versioning (/v1/), pagination (cursor-based), and HATEOAS where useful. "
            "You write OpenAPI/Swagger specs. You design webhook payloads, OAuth flows, and API key auth. "
            "You think about: rate limiting, idempotency, backward compatibility, error response formats, "
            "and API versioning strategy. You define request/response schemas with examples. "
            "Output: OpenAPI spec, endpoint list with methods/paths/params/responses, auth flow diagram."
        ),
    },
    # ── Phase 4: Quality & Security ────────────────────────────────────
    "qa-engineer": {
        "role": "QA Engineer & Test Architect",
        "capabilities": ["testing", "test-automation", "edge-cases", "regression", "performance-testing", "e2e-testing"],
        "phase": "quality",
        "system_prompt": (
            "You are the QA Engineer. You find the bugs nobody else sees and build the test infrastructure "
            "that prevents regressions. You write: unit tests (pytest), integration tests (API), "
            "end-to-end tests (Playwright/Cypress), and performance tests (load testing). "
            "You think about: boundary values, null/empty inputs, concurrent operations, race conditions, "
            "data corruption scenarios, permission bypass, and what happens when external services are down. "
            "You define the test pyramid: many unit tests, fewer integration tests, minimal E2E tests. "
            "You create test data factories and fixtures. You refuse to ship without adequate coverage. "
            "Output: test cases with setup, action, expected result, and edge case variations."
        ),
    },
    "security-engineer": {
        "role": "Security Engineer",
        "capabilities": ["security", "threat-modeling", "owasp", "authentication", "encryption", "compliance"],
        "phase": "quality",
        "system_prompt": (
            "You are the Security Engineer. You see threats everywhere and that's your job. "
            "You perform threat modeling on every feature: what can go wrong, who can exploit it, "
            "what's the blast radius? You check for OWASP Top 10: injection, broken auth, XSS, CSRF, "
            "insecure deserialization, misconfigurations, and sensitive data exposure. "
            "You enforce: input validation at every boundary, parameterized queries, HTTPS everywhere, "
            "secrets management (never in code), least privilege, rate limiting, and audit logging. "
            "You design the auth architecture: session management, token rotation, MFA, and role-based access. "
            "You think about: supply chain attacks, dependency vulnerabilities, and insider threats. "
            "Output: threat model, security requirements, and specific code-level recommendations."
        ),
    },
    # ── Phase 5: Ship & Operate ────────────────────────────────────────
    "devops-engineer": {
        "role": "DevOps & Platform Engineer",
        "capabilities": ["deployment", "docker", "CI-CD", "monitoring", "cloud-infrastructure", "reliability", "IaC"],
        "phase": "ship",
        "system_prompt": (
            "You are the DevOps Engineer. You build the platform that gets code from laptop to production safely. "
            "You design: Dockerfiles, docker-compose for local dev, CI/CD pipelines (GitHub Actions), "
            "deployment scripts, health checks, and rollback procedures. "
            "You set up: monitoring (uptime, error rates, latency), alerting (PagerDuty/Slack), "
            "centralized logging, and infrastructure-as-code (Terraform/gcloud). "
            "You automate everything — if a human has to SSH into a box, that's a failure. "
            "You care about: zero-downtime deploys, database migration safety, secret rotation, "
            "backup verification, and disaster recovery. You prefer boring, proven tech that works at 3am. "
            "Output: Dockerfile, CI/CD config, deploy script, monitoring setup, and runbook."
        ),
    },
    # ── Phase 6: Growth & Intelligence ─────────────────────────────────
    "data-analyst": {
        "role": "Data Analyst & BI Engineer",
        "capabilities": ["analytics", "dashboards", "KPIs", "reporting", "data-visualization", "SQL", "metrics-design"],
        "phase": "grow",
        "system_prompt": (
            "You are the Data Analyst. You turn raw data into business intelligence. "
            "You define the KPIs that matter: what to measure, how to calculate it, what's the target, "
            "and what action to take when it's off. You design dashboards that tell a story — "
            "not just numbers but trends, comparisons, and anomaly highlights. "
            "You write SQL queries for complex aggregations, cohort analysis, funnel metrics, and retention curves. "
            "You think about: data quality, missing data handling, statistical significance, "
            "misleading visualizations, and actionable vs vanity metrics. "
            "You design the analytics event schema: what events to track, what properties to capture. "
            "Output: KPI definitions, dashboard wireframes, SQL queries, and event tracking plan."
        ),
    },
    "growth-engineer": {
        "role": "Growth Engineer & Revenue Strategist",
        "capabilities": ["monetization", "pricing", "onboarding", "retention", "conversion", "email-automation", "SaaS-metrics"],
        "phase": "grow",
        "system_prompt": (
            "You are the Growth Engineer. You think about how the product makes money and grows. "
            "You design: pricing tiers and packaging, trial flows, onboarding sequences, "
            "upgrade prompts, churn prevention, referral programs, and usage-based billing. "
            "You optimize the funnel: awareness → signup → activation → retention → revenue → referral. "
            "You define activation metrics (what makes a user 'stick'), design email drip campaigns, "
            "and identify upsell opportunities from usage patterns. "
            "You think about: freemium vs trial, per-seat vs usage pricing, annual discounts, "
            "enterprise features, and self-serve vs sales-assisted motions. "
            "You know SaaS metrics: MRR, ARR, churn rate, LTV, CAC, NPS. "
            "Output: pricing page design, onboarding flow, email sequences, and growth experiment ideas."
        ),
    },
    "technical-writer": {
        "role": "Technical Writer & Documentation Lead",
        "capabilities": ["documentation", "API-docs", "user-guides", "tutorials", "changelogs", "knowledge-base"],
        "phase": "grow",
        "system_prompt": (
            "You are the Technical Writer. You make complex things simple and ensure nobody is confused. "
            "You write: API documentation (with curl examples), user guides with screenshots, "
            "developer setup guides (clone → running in 5 minutes), architecture docs, "
            "troubleshooting guides, FAQ pages, and release notes. "
            "You follow the principle: if someone has to ask how it works, the docs failed. "
            "You structure docs with: quick start, concepts, how-to guides, and reference. "
            "You write for two audiences: end users (non-technical) and developers (technical). "
            "You include: code examples that actually work, common error messages with solutions, "
            "and decision trees for 'which feature should I use?' "
            "Output: structured markdown documentation with headings, code blocks, and practical examples."
        ),
    },
}

# Pre-built team configurations for common tasks
TEAM_PRESETS = {
    "discover": ["business-analyst", "product-manager", "ux-designer"],
    "design": ["system-architect", "database-engineer", "api-designer"],
    "build-backend": ["lead-developer", "backend-developer", "database-engineer"],
    "build-frontend": ["frontend-developer", "ux-designer", "lead-developer"],
    "build-fullstack": ["backend-developer", "frontend-developer", "lead-developer"],
    "review": ["lead-developer", "security-engineer", "qa-engineer"],
    "ship": ["devops-engineer", "security-engineer", "qa-engineer"],
    "grow": ["growth-engineer", "data-analyst", "product-manager"],
    "full-review": ["lead-developer", "security-engineer", "qa-engineer", "devops-engineer"],
    "new-app": ["business-analyst", "product-manager", "system-architect", "ux-designer"],
}

class TeamDebateRequest(BaseModel):
    topic: str = Field(..., description="The topic or question to debate")
    context: str = Field("", description="Additional context")
    team: List[str] = Field(
        default=["lead-developer", "security-engineer", "product-manager"],
        description="Team roles OR a preset name (discover, design, build-backend, build-frontend, build-fullstack, review, ship, grow, full-review, new-app)"
    )
    model: str = Field(
        default="gemini",
        description="Base model for all personas: gemini (cheapest), chatgpt, grok"
    )
    mode: str = Field(
        default="debate",
        description="Collaboration mode: debate (4-phase with opposing views), brainstorming (creative ideation), expert_panel (each expert contributes from their specialty), peer_review (review each other's work)"
    )

@app.post("/v1/debate", response_model=CollaborateResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def debate(req: DebateRequest):
    """Structured multi-agent debate with forced opposing viewpoints.

    Returns full debate transcript with each agent's positions, cross-examinations,
    rebuttals, and final verdicts. Agents are assigned FOR/AGAINST/PRAGMATIST/INNOVATOR roles.
    """
    team = get_team()
    request_id = str(uuid.uuid4())[:8]

    try:
        result = await team.collaborate(
            prompt=req.topic,
            context=req.context,
            agents=req.agents,
            mode="debate",
        )

        # Build rich debate data
        rounds_data = None
        agent_positions_data = None
        disagreements_data = None
        consensus_data = None

        engine = getattr(team, '_collaboration_engine', None)
        if engine and hasattr(engine, 'rounds') and engine.rounds:
            phase_names = ["positions", "cross_examination", "rebuttals", "verdict"]
            rounds_data = []
            for r in engine.rounds:
                phase = phase_names[r.round_number - 1] if r.round_number <= len(phase_names) else "extra"
                rounds_data.append(DebateRound(
                    round_number=r.round_number,
                    phase=phase,
                    responses=[
                        AgentPosition(
                            agent=resp.agent_name,
                            content=resp.content[:2000] if resp.content else "",
                            confidence=resp.confidence,
                            response_time=resp.response_time,
                        )
                        for resp in r.responses if resp.success
                    ],
                    consensus_level=r.consensus_level,
                    conflicts=r.conflicts or [],
                ))
            if rounds_data:
                consensus_data = rounds_data[-1].consensus_level
                disagreements_data = []
                for rd in rounds_data:
                    disagreements_data.extend(rd.conflicts)

        if result.agent_responses:
            agent_positions_data = [
                AgentPosition(
                    agent=resp.agent_name,
                    content=resp.content[:2000] if resp.content else "",
                    confidence=resp.confidence,
                    response_time=resp.response_time,
                )
                for resp in result.agent_responses if resp.success
            ]

        return CollaborateResponse(
            request_id=request_id,
            answer=result.final_answer,
            agents_used=result.participating_agents,
            confidence=result.confidence_score,
            mode="debate",
            total_time=result.total_time,
            rounds=rounds_data,
            agent_positions=agent_positions_data,
            disagreements=disagreements_data if disagreements_data else None,
            consensus_level=consensus_data,
        )
    except Exception as e:
        logger.error(f"Debate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/team-debate", response_model=CollaborateResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def team_debate(req: TeamDebateRequest):
    """Single-model virtual dev team — one cheap model plays multiple expert roles.

    Creates a virtual dev team where each persona is the SAME underlying model
    with different system prompts. Full debate for ~$0.005 instead of ~$0.25.

    Team presets: discover, design, build-backend, build-frontend, build-fullstack,
    review, ship, grow, full-review, new-app

    Or pick individual roles: business-analyst, product-manager, system-architect,
    ux-designer, database-engineer, lead-developer, backend-developer,
    frontend-developer, api-designer, qa-engineer, security-engineer,
    devops-engineer, data-analyst, growth-engineer, technical-writer
    """
    request_id = str(uuid.uuid4())[:8]

    # Auto-select team based on topic keywords
    AUTO_ROUTING = [
        (["build", "implement", "code", "write", "create app", "develop", "function", "class", "api endpoint"],
         ["lead-developer", "backend-developer"]),
        (["frontend", "ui", "react", "component", "page", "dashboard", "layout", "css", "tailwind"],
         ["frontend-developer", "ux-designer"]),
        (["database", "schema", "model", "table", "migration", "sql", "firestore", "query"],
         ["database-engineer", "backend-developer"]),
        (["security", "auth", "vulnerability", "owasp", "encrypt", "permission", "hack", "threat"],
         ["security-engineer", "lead-developer"]),
        (["deploy", "docker", "ci/cd", "infrastructure", "server", "vm", "cloud", "monitor", "nginx"],
         ["devops-engineer", "system-architect"]),
        (["test", "bug", "quality", "coverage", "edge case", "regression"],
         ["qa-engineer", "lead-developer"]),
        (["design", "architect", "stack", "pattern", "scale", "structure", "monolith", "microservice"],
         ["system-architect", "lead-developer", "product-manager"]),
        (["idea", "app", "startup", "business", "saas", "product", "feature", "mvp", "market"],
         ["product-manager", "business-analyst", "ux-designer"]),
        (["pricing", "revenue", "growth", "onboarding", "churn", "convert", "monetiz"],
         ["growth-engineer", "product-manager"]),
        (["analytics", "kpi", "metric", "dashboard", "report", "data", "insight"],
         ["data-analyst", "backend-developer"]),
        (["docs", "documentation", "readme", "guide", "tutorial", "api doc"],
         ["technical-writer", "api-designer"]),
        (["review", "refactor", "optimize", "clean", "improve", "performance"],
         ["lead-developer", "qa-engineer", "system-architect"]),
    ]

    # Resolve preset or auto-select
    team_roles = req.team
    if len(team_roles) == 1 and team_roles[0] == "auto":
        # Auto-select based on topic keywords
        topic_lower = req.topic.lower()
        matched_roles = set()
        for keywords, roles in AUTO_ROUTING:
            if any(kw in topic_lower for kw in keywords):
                matched_roles.update(roles)
        # Default to architect + lead-dev + PM if nothing matched
        if len(matched_roles) < 2:
            matched_roles = {"system-architect", "lead-developer", "product-manager"}
        # Cap at 4 roles to keep costs down
        team_roles = list(matched_roles)[:4]
    elif len(team_roles) == 1 and team_roles[0] in TEAM_PRESETS:
        team_roles = TEAM_PRESETS[team_roles[0]]
    elif len(team_roles) == 1 and team_roles[0] not in TEAM_PERSONAS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role or preset: {team_roles[0]}. Use 'auto', a preset ({list(TEAM_PRESETS.keys())}), or roles ({list(TEAM_PERSONAS.keys())})"
        )

    # Validate team roles
    invalid_roles = [r for r in team_roles if r not in TEAM_PERSONAS]
    if invalid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown roles: {invalid_roles}. Available: {list(TEAM_PERSONAS.keys())}. Presets: {list(TEAM_PRESETS.keys())}"
        )
    if len(team_roles) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 team members")

    # Create persona agents from the chosen base model
    from elgringo.agents.base import AgentConfig, ModelType

    agents = []
    for role_name in team_roles:
        persona = TEAM_PERSONAS[role_name]
        config = AgentConfig(
            name=role_name,
            model_type=ModelType.GEMINI,  # default
            role=persona["role"],
            capabilities=persona["capabilities"],
            system_prompt=persona["system_prompt"],
        )

        if req.model == "gemini":
            from elgringo.agents.gemini import GeminiAgent
            config.model_type = ModelType.GEMINI
            config.model_name = "gemini-2.5-flash"
            agent = GeminiAgent(config=config)
        elif req.model == "chatgpt":
            from elgringo.agents.chatgpt import ChatGPTAgent
            config.model_type = ModelType.CHATGPT
            config.model_name = "gpt-4o-mini"
            agent = ChatGPTAgent(config=config)
        elif req.model == "grok":
            from elgringo.agents.grok import GrokAgent
            config.model_type = ModelType.GROK
            config.model_name = "grok-3-fast"
            agent = GrokAgent(config=config)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}. Use: gemini, chatgpt, grok")

        agents.append(agent)

    # Run using the collaboration engine directly
    try:
        from elgringo.collaboration.engine import CollaborationEngine, CollaborationMode, CollaborationContext

        # Map mode string to enum
        mode_map = {
            "debate": CollaborationMode.DEBATE,
            "brainstorming": CollaborationMode.BRAINSTORMING,
            "expert_panel": CollaborationMode.EXPERT_PANEL,
            "peer_review": CollaborationMode.PEER_REVIEW,
            "consensus": CollaborationMode.CONSENSUS,
            "parallel": CollaborationMode.PARALLEL,
        }
        collab_mode = mode_map.get(req.mode, CollaborationMode.DEBATE)

        engine = CollaborationEngine()
        collab_ctx = CollaborationContext(
            mode=collab_mode,
            max_rounds=4,
            consensus_threshold=0.75,
        )

        start_time = time.time()
        all_responses = await engine.execute(agents, req.topic, req.context, collab_ctx)
        total_time = time.time() - start_time

        # Synthesize final answer from all responses
        successful = [r for r in all_responses if r.success]
        if not successful:
            raise HTTPException(status_code=500, detail="No successful responses from team")

        # Use the last round's responses for synthesis (verdicts)
        verdict_responses = engine.rounds[-1].responses if engine.rounds else successful
        verdict_text = "\n\n".join(
            f"**{r.agent_name}** ({TEAM_PERSONAS.get(r.agent_name, {}).get('role', 'Expert')}):\n{r.content}"
            for r in verdict_responses if r.success
        )

        # Have one agent synthesize the final answer
        synthesis_prompt = (
            f"Synthesize these expert verdicts on: {req.topic}\n\n{verdict_text}\n\n"
            "Combine into a clear, actionable recommendation. Credit specific experts where relevant."
        )
        synthesis_response = await agents[0].generate_response(synthesis_prompt, req.context)
        final_answer = synthesis_response.content if synthesis_response.success else verdict_text

        # Build rounds data
        phase_names = ["positions", "cross_examination", "rebuttals", "verdict"]
        rounds_data = []
        for r in engine.rounds:
            phase = phase_names[r.round_number - 1] if r.round_number <= len(phase_names) else "extra"
            rounds_data.append(DebateRound(
                round_number=r.round_number,
                phase=phase,
                responses=[
                    AgentPosition(
                        agent=resp.agent_name,
                        content=resp.content[:2000] if resp.content else "",
                        confidence=resp.confidence,
                        response_time=resp.response_time,
                    )
                    for resp in r.responses if resp.success
                ],
                consensus_level=r.consensus_level,
                conflicts=r.conflicts or [],
            ))

        disagreements_data = []
        for rd in rounds_data:
            disagreements_data.extend(rd.conflicts)

        return CollaborateResponse(
            request_id=request_id,
            answer=final_answer,
            agents_used=team_roles,
            confidence=sum(r.confidence for r in successful) / len(successful),
            mode=f"team-{req.mode} ({req.model})",
            total_time=total_time,
            rounds=rounds_data,
            agent_positions=[
                AgentPosition(
                    agent=r.agent_name,
                    content=r.content[:2000] if r.content else "",
                    confidence=r.confidence,
                    response_time=r.response_time,
                )
                for r in successful
            ],
            disagreements=disagreements_data if disagreements_data else None,
            consensus_level=rounds_data[-1].consensus_level if rounds_data else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Team debate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/team-roles")
async def list_team_roles():
    """List available team roles and presets for team-debate."""
    return {
        "roles": {
            name: {
                "role": p["role"],
                "phase": p.get("phase", "general"),
                "capabilities": p["capabilities"],
            }
            for name, p in TEAM_PERSONAS.items()
        },
        "presets": {
            name: {"roles": roles, "description": f"Pre-built team for {name.replace('-', ' ')} tasks"}
            for name, roles in TEAM_PRESETS.items()
        },
        "phases": ["discovery", "design", "build", "quality", "ship", "grow"],
    }


# ── Feedback Endpoint ────────────────────────────────────────────────

@app.post("/v1/feedback", response_model=FeedbackResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def record_feedback(req: FeedbackRequest):
    """Record outcome feedback for a previous suggestion to improve future results."""
    request_id = str(uuid.uuid4())[:8]
    try:
        team = get_team()
        # Use neural memory if available
        neural = getattr(team, '_neural_memory', None)
        if neural:
            neural.record_outcome(req.node_id, req.success, req.feedback)
            node = neural._nodes.get(req.node_id)
            new_confidence = node.confidence if node else 0.0
        else:
            new_confidence = 0.0

        return FeedbackResponse(
            request_id=request_id,
            status="recorded",
            node_id=req.node_id,
            new_confidence=new_confidence,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Memory Endpoints ─────────────────────────────────────────────────

class MemorySearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    search_type: str = Field("all", description="solutions, mistakes, or all")
    limit: int = Field(5, description="Max results")

class MemoryStoreRequest(BaseModel):
    type: str = Field(..., description="solution or mistake")
    # Solution fields
    problem: str = Field("", description="Problem pattern (for solutions)")
    solution_steps: List[str] = Field(default_factory=list, description="Solution steps")
    tags: List[str] = Field(default_factory=list, description="Tags")
    # Mistake fields
    description: str = Field("", description="Mistake description")
    mistake_type: str = Field("code_error", description="Mistake type")
    severity: str = Field("medium", description="Severity level")
    prevention: str = Field("", description="Prevention strategy")

class TeachRequest(BaseModel):
    topic: str = Field(..., description="Topic to teach")
    content: str = Field(..., description="Knowledge content")
    domain: str = Field("general", description="Domain area")


@app.post("/v1/memory/search", dependencies=[Depends(verify_api_key)])
async def memory_search(req: MemorySearchRequest):
    """Search memory for past solutions and mistakes."""
    team = get_team()
    memory = team._memory if hasattr(team, '_memory') and team._memory else None
    if not memory:
        from elgringo.memory import MemorySystem
        memory = MemorySystem()

    results = {"solutions": [], "mistakes": []}

    if req.search_type in ("solutions", "all"):
        solutions = await memory.find_solution_patterns(req.query, limit=req.limit)
        results["solutions"] = [
            {"problem": s.problem_pattern, "steps": s.solution_steps,
             "success_rate": s.success_rate, "tags": s.tags}
            for s in solutions
        ]

    if req.search_type in ("mistakes", "all"):
        mistakes = await memory.find_similar_mistakes({"query": req.query}, limit=req.limit)
        results["mistakes"] = [
            {"description": m.description, "type": m.mistake_type,
             "severity": m.severity, "prevention": m.prevention_strategy}
            for m in mistakes
        ]

    return results


@app.post("/v1/memory/store", dependencies=[Depends(verify_api_key)])
async def memory_store(req: MemoryStoreRequest):
    """Store a solution or mistake in memory."""
    team = get_team()
    memory = team._memory if hasattr(team, '_memory') and team._memory else None
    if not memory:
        from elgringo.memory import MemorySystem
        memory = MemorySystem()

    if req.type == "solution":
        solution_id = await memory.capture_solution(
            problem_pattern=req.problem,
            solution_steps=req.solution_steps,
            success_rate=1.0,
            tags=req.tags,
        )
        return {"stored": "solution", "id": solution_id, "problem": req.problem}
    elif req.type == "mistake":
        from elgringo.memory.system import MistakeType
        type_map = {t.value: t for t in MistakeType}
        mt = type_map.get(req.mistake_type, MistakeType.CODE_ERROR)
        mistake_id = await memory.capture_mistake(
            mistake_type=mt,
            description=req.description,
            context={"source": "api"},
            severity=req.severity,
            prevention_strategy=req.prevention,
        )
        return {"stored": "mistake", "id": mistake_id, "description": req.description}
    else:
        raise HTTPException(status_code=400, detail="type must be 'solution' or 'mistake'")


@app.get("/v1/memory/stats", dependencies=[Depends(verify_api_key)])
async def memory_stats():
    """Get memory system statistics."""
    team = get_team()
    memory = team._memory if hasattr(team, '_memory') and team._memory else None
    if not memory:
        from elgringo.memory import MemorySystem
        memory = MemorySystem()
    return memory.get_statistics()


# ── Cost Endpoints ──────────────────────────────────────────────────

@app.get("/v1/costs", dependencies=[Depends(verify_api_key)])
async def costs():
    """Get cost tracking report."""
    from elgringo.routing.cost_tracker import get_cost_tracker
    ct = get_cost_tracker()
    return {
        "statistics": ct.get_statistics(),
        "daily": ct.get_daily_report(),
        "budget": ct.get_budget_status(),
        "per_model": ct.get_model_costs(),
    }


# ── Teach Endpoint ──────────────────────────────────────────────────

@app.post("/v1/teach", dependencies=[Depends(verify_api_key)])
async def teach(req: TeachRequest):
    """Teach the AI team new knowledge."""
    from elgringo.knowledge import TeachingSystem
    teacher = TeachingSystem()
    result = await teacher.teach(topic=req.topic, content=req.content, domain=req.domain)
    return {"taught": True, "topic": req.topic, "domain": req.domain, "result": result}


# ── Verify Code Endpoint ───────────────────────────────────────────

class VerifyCodeRequest(BaseModel):
    code: str = Field(..., description="Code to validate")
    language: str = Field("", description="Language (auto-detect if empty)")

@app.post("/v1/verify", dependencies=[Depends(verify_api_key)])
async def verify_code(req: VerifyCodeRequest):
    """Validate code for syntax errors, security issues, and lint warnings."""
    from elgringo.validation.code_validator import CodeValidator
    validator = CodeValidator()
    result = validator.validate(req.code, language=req.language or None)
    return {
        "valid": result.valid,
        "language": result.language,
        "errors": [str(e) for e in result.errors],
        "warnings": [str(w) for w in result.warnings],
        "suggestions": result.suggestions,
    }


# ── Diagnose Endpoint ────────────────────────────────────────────────

class DiagnoseRequest(BaseModel):
    error_message: str = Field(..., description="The error message to diagnose")
    stacktrace: str = Field("", description="Full stack trace if available")
    project_path: str = Field("", description="Project path to read files for context")
    files_context: List[str] = Field(default_factory=list, description="Specific files to read for context")
    language: str = Field("", description="Programming language (auto-detect if empty)")

class DiagnoseResponse(BaseModel):
    request_id: str
    node_id: str = ""
    root_cause: str
    explanation: str
    suggested_fix: str
    confidence: float
    agents_used: List[str]
    related_files: List[str]
    total_time: float


@app.post("/v1/diagnose", response_model=DiagnoseResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def diagnose(req: DiagnoseRequest):
    """AI debugger: multi-agent root cause analysis for errors and bugs."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    try:
        # Build context from error info + file contents
        context_parts = [f"ERROR MESSAGE:\n{req.error_message}"]
        if req.stacktrace:
            context_parts.append(f"STACKTRACE:\n{req.stacktrace}")
        if req.language:
            context_parts.append(f"LANGUAGE: {req.language}")

        related_files = []
        if req.project_path and req.files_context:
            from products.fred_api.coding_endpoints import ProjectTools
            try:
                tools = ProjectTools(req.project_path)
                for filepath in req.files_context[:10]:
                    abs_path = str(tools.root / filepath) if not os.path.isabs(filepath) else filepath
                    content = tools.read_file(abs_path)
                    if not content.startswith("[ERROR]"):
                        context_parts.append(f"--- FILE: {filepath} ---\n{content[:6000]}")
                        related_files.append(filepath)
            except Exception as e:
                logger.warning(f"Diagnose: could not read project files: {e}")

        context = "\n\n".join(context_parts)

        prompt = """Diagnose the root cause of this error. Provide:
1. ROOT CAUSE: A single clear sentence identifying the root cause
2. EXPLANATION: A detailed explanation of why this happens
3. SUGGESTED FIX: Concrete code changes or steps to fix it
4. RELATED FILES: Which files are most likely involved

Be specific and actionable. Reference exact lines/functions when possible."""

        result = await team.collaborate(
            prompt=prompt,
            context=context,
            mode="peer_review",
        )

        # Parse structured sections from the response
        answer = result.final_answer
        root_cause = ""
        explanation = ""
        suggested_fix = ""

        for section in ["ROOT CAUSE:", "EXPLANATION:", "SUGGESTED FIX:", "RELATED FILES:"]:
            pass  # We'll do simple extraction below

        # Simple section extraction
        lines = answer.split("\n")
        current_section = ""
        sections: Dict[str, List[str]] = {
            "root_cause": [], "explanation": [], "suggested_fix": [], "related_files": []
        }
        section_map = {
            "root cause": "root_cause", "explanation": "explanation",
            "suggested fix": "suggested_fix", "related files": "related_files",
        }

        for line in lines:
            line_lower = line.lower().strip()
            matched = False
            for key, section_name in section_map.items():
                if key in line_lower and (":" in line or "#" in line):
                    current_section = section_name
                    # Grab text after the colon on same line
                    after = line.split(":", 1)[-1].strip() if ":" in line else ""
                    if after:
                        sections[current_section].append(after)
                    matched = True
                    break
            if not matched and current_section:
                sections[current_section].append(line)

        root_cause = "\n".join(sections["root_cause"]).strip() or answer[:200]
        explanation = "\n".join(sections["explanation"]).strip() or answer
        suggested_fix = "\n".join(sections["suggested_fix"]).strip() or ""

        node_id = ""
        neural = getattr(team, '_neural_memory', None)
        if neural:
            try:
                node_id = neural.store(
                    content=f"diagnose: {root_cause[:200]}",
                    node_type="solution",
                    tags=["diagnose"],
                    confidence=result.confidence_score,
                )
            except Exception:
                pass

        return DiagnoseResponse(
            request_id=request_id,
            node_id=node_id,
            root_cause=root_cause,
            explanation=explanation,
            suggested_fix=suggested_fix,
            confidence=result.confidence_score,
            agents_used=result.participating_agents,
            related_files=related_files,
            total_time=time.time() - start,
        )
    except Exception as e:
        logger.error(f"Diagnose error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Changelog Endpoint ──────────────────────────────────────────────

class ChangelogRequest(BaseModel):
    project_path: str = Field(..., description="Absolute path to the project")
    git_range: str = Field("HEAD~10..HEAD", description="Git range (e.g. HEAD~10..HEAD, v1.0..HEAD)")
    audience: str = Field("developer", description="Target audience: developer, stakeholder, user")
    format: str = Field("markdown", description="Output format: markdown, json")

class ChangelogResponse(BaseModel):
    request_id: str
    node_id: str = ""
    changelog: str
    commits_analyzed: int
    categories: Dict[str, List[str]]
    total_time: float


@app.post("/v1/changelog", response_model=ChangelogResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def changelog(req: ChangelogRequest):
    """Generate changelog from git history using multi-agent analysis."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    try:
        from products.fred_api.coding_endpoints import ProjectTools
        tools = ProjectTools(req.project_path)

        # Get git log
        git_log = tools.run_command(
            f"git log {req.git_range} --format='%h|%an|%s' --no-merges"
        )
        if git_log["exit_code"] != 0:
            raise HTTPException(status_code=400, detail=f"Git log failed: {git_log['stderr']}")

        log_output = git_log["stdout"].strip()
        if not log_output:
            raise HTTPException(status_code=400, detail="No commits found in the given range")

        commits = [line for line in log_output.split("\n") if line.strip()]

        # Get diff stat for context
        diff_stat = tools.run_command(f"git diff {req.git_range} --stat")
        stat_output = diff_stat["stdout"][:3000] if diff_stat["exit_code"] == 0 else ""

        context = f"GIT LOG ({len(commits)} commits):\n{log_output}\n\nDIFF STAT:\n{stat_output}"

        audience_instructions = {
            "developer": "Include technical details, file paths, and breaking changes. Use conventional commit style.",
            "stakeholder": "Focus on business impact, features, and improvements. Avoid technical jargon.",
            "user": "Focus on user-facing changes, new features, and bug fixes. Keep it simple and friendly.",
        }

        prompt = f"""Generate a {req.format} changelog for the following git commits.
Target audience: {req.audience}
{audience_instructions.get(req.audience, audience_instructions['developer'])}

Organize into categories:
- Features (new capabilities)
- Fixes (bug fixes)
- Improvements (enhancements to existing features)
- Breaking Changes (if any)
- Other (maintenance, docs, etc.)

Be concise. One line per change."""

        result = await team.collaborate(
            prompt=prompt,
            context=context,
            mode="parallel",
        )

        # Extract categories from the response
        categories: Dict[str, List[str]] = {
            "features": [], "fixes": [], "improvements": [], "breaking": [], "other": []
        }
        current_cat = "other"
        for line in result.final_answer.split("\n"):
            line_lower = line.lower().strip()
            if "feature" in line_lower and ("#" in line or ":" in line_lower[:15]):
                current_cat = "features"
            elif "fix" in line_lower and ("#" in line or ":" in line_lower[:10]):
                current_cat = "fixes"
            elif "improvement" in line_lower and ("#" in line or ":" in line_lower[:15]):
                current_cat = "improvements"
            elif "breaking" in line_lower and ("#" in line or ":" in line_lower[:15]):
                current_cat = "breaking"
            elif line.strip().startswith("-") or line.strip().startswith("*"):
                categories[current_cat].append(line.strip().lstrip("-*").strip())

        node_id = ""
        neural = getattr(team, '_neural_memory', None)
        if neural:
            try:
                node_id = neural.store(
                    content=f"changelog: {len(commits)} commits analyzed",
                    node_type="solution",
                    tags=["changelog"],
                    confidence=result.confidence_score,
                )
            except Exception:
                pass

        return ChangelogResponse(
            request_id=request_id,
            node_id=node_id,
            changelog=result.final_answer,
            commits_analyzed=len(commits),
            categories=categories,
            total_time=time.time() - start,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Changelog error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Refactor Endpoint ───────────────────────────────────────────────

class RefactorRequest(BaseModel):
    project_path: str = Field(..., description="Absolute path to the project")
    target_files: List[str] = Field(default_factory=list, description="Specific files to analyze (empty = auto-detect)")
    focus: str = Field("all", description="Focus: complexity, duplication, performance, security, all")
    glob_pattern: str = Field("**/*.py", description="File pattern to analyze")

class RefactorResponse(BaseModel):
    request_id: str
    node_id: str = ""
    summary: str
    recommendations: List[Dict]
    tech_debt_score: float
    agents_used: List[str]
    total_time: float


@app.post("/v1/refactor", response_model=RefactorResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def refactor(req: RefactorRequest):
    """Multi-agent refactor analysis: finds complexity, duplication, and tech debt."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    try:
        from products.fred_api.coding_endpoints import ProjectTools
        from fnmatch import fnmatch
        tools = ProjectTools(req.project_path)

        # Get files to analyze
        all_files = tools.list_files()
        if req.target_files:
            files_to_read = req.target_files[:15]
        else:
            files_to_read = [f for f in all_files if fnmatch(f, req.glob_pattern)][:15]

        if not files_to_read:
            raise HTTPException(status_code=400, detail="No files matched the pattern")

        # Read file contents
        context_parts = [f"PROJECT: {req.project_path} ({len(all_files)} total files)"]
        for filepath in files_to_read:
            content = tools.read_file(str(tools.root / filepath))
            if not content.startswith("[ERROR]"):
                context_parts.append(f"--- {filepath} ({len(content.splitlines())} lines) ---\n{content[:5000]}")

        context = "\n\n".join(context_parts)

        focus_instructions = {
            "complexity": "Focus on cyclomatic complexity, deeply nested logic, long functions, and god classes.",
            "duplication": "Focus on duplicated code, copy-paste patterns, and opportunities for shared abstractions.",
            "performance": "Focus on N+1 queries, unnecessary allocations, blocking I/O, and algorithmic inefficiency.",
            "security": "Focus on injection vulnerabilities, auth gaps, data exposure, and insecure defaults.",
            "all": "Analyze complexity, duplication, performance, and security comprehensively.",
        }

        prompt = f"""Analyze this codebase for refactoring opportunities.
Focus: {req.focus}
{focus_instructions.get(req.focus, focus_instructions['all'])}

For each finding, provide:
- FILE: which file
- ISSUE: what the problem is
- SUGGESTION: how to fix it
- PRIORITY: high/medium/low
- EFFORT: small/medium/large

Also provide:
- TECH DEBT SCORE: 0-100 (0=pristine, 100=critical debt)
- SUMMARY: one paragraph overview"""

        result = await team.collaborate(
            prompt=prompt,
            context=context,
            mode="expert_panel",
        )

        # Parse recommendations from the response
        recommendations = []
        answer = result.final_answer
        current_rec: Dict = {}

        for line in answer.split("\n"):
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            if line_lower.startswith("file:") or line_lower.startswith("- file:"):
                if current_rec.get("file"):
                    recommendations.append(current_rec)
                current_rec = {"file": line_stripped.split(":", 1)[-1].strip()}
            elif line_lower.startswith("issue:") or line_lower.startswith("- issue:"):
                current_rec["issue"] = line_stripped.split(":", 1)[-1].strip()
            elif line_lower.startswith("suggestion:") or line_lower.startswith("- suggestion:"):
                current_rec["suggestion"] = line_stripped.split(":", 1)[-1].strip()
            elif line_lower.startswith("priority:") or line_lower.startswith("- priority:"):
                current_rec["priority"] = line_stripped.split(":", 1)[-1].strip().lower()
            elif line_lower.startswith("effort:") or line_lower.startswith("- effort:"):
                current_rec["effort"] = line_stripped.split(":", 1)[-1].strip().lower()

        if current_rec.get("file"):
            recommendations.append(current_rec)

        # Extract tech debt score
        tech_debt_score = 50.0  # default
        import re
        score_match = re.search(r'tech\s*debt\s*score[:\s]*(\d+)', answer, re.IGNORECASE)
        if score_match:
            tech_debt_score = min(100.0, max(0.0, float(score_match.group(1))))

        # Extract summary
        summary = ""
        summary_match = re.search(r'summary[:\s]*(.*?)(?:\n\n|\nfile:|\n-\s*file:|\Z)', answer, re.IGNORECASE | re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()[:500]
        if not summary:
            summary = answer[:300]

        node_id = ""
        neural = getattr(team, '_neural_memory', None)
        if neural:
            try:
                node_id = neural.store(
                    content=f"refactor: {summary[:200]}",
                    node_type="solution",
                    tags=["refactor"],
                    confidence=result.confidence_score,
                )
            except Exception:
                pass

        return RefactorResponse(
            request_id=request_id,
            node_id=node_id,
            summary=summary,
            recommendations=recommendations,
            tech_debt_score=tech_debt_score,
            agents_used=result.participating_agents,
            total_time=time.time() - start,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refactor error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Test Generate Endpoint ──────────────────────────────────────────

class TestGenRequest(BaseModel):
    project_path: str = Field(..., description="Absolute path to the project")
    target_file: str = Field(..., description="File to generate tests for")
    test_framework: str = Field("", description="Test framework (auto-detect: pytest, jest, go test)")
    coverage_focus: str = Field("edge_cases", description="Focus: happy_path, edge_cases, comprehensive")

class TestGenResponse(BaseModel):
    request_id: str
    node_id: str = ""
    test_code: str
    test_file_path: str
    tests_count: int
    coverage_areas: List[str]
    agents_used: List[str]
    total_time: float


@app.post("/v1/test-generate", response_model=TestGenResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def test_generate(req: TestGenRequest):
    """AI test writer: generates comprehensive tests for any source file."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    try:
        from products.fred_api.coding_endpoints import ProjectTools
        from pathlib import Path as PurePath
        tools = ProjectTools(req.project_path)

        # Read the target file
        abs_path = str(tools.root / req.target_file) if not os.path.isabs(req.target_file) else req.target_file
        source_content = tools.read_file(abs_path)
        if source_content.startswith("[ERROR]"):
            raise HTTPException(status_code=400, detail=f"Cannot read file: {source_content}")

        # Auto-detect test framework from file extension and project
        ext = PurePath(req.target_file).suffix
        framework = req.test_framework
        if not framework:
            if ext == ".py":
                framework = "pytest"
            elif ext in (".js", ".jsx", ".ts", ".tsx"):
                framework = "jest"
            elif ext == ".go":
                framework = "go test"
            elif ext == ".rs":
                framework = "cargo test"
            else:
                framework = "pytest"

        # Determine test file path
        target_name = PurePath(req.target_file).stem
        target_dir = str(PurePath(req.target_file).parent)
        if framework == "pytest":
            test_file = f"{target_dir}/test_{target_name}.py" if target_dir != "." else f"test_{target_name}.py"
        elif framework in ("jest",):
            test_file = f"{target_dir}/{target_name}.test{ext}" if target_dir != "." else f"{target_name}.test{ext}"
        elif framework == "go test":
            test_file = f"{target_dir}/{target_name}_test.go" if target_dir != "." else f"{target_name}_test.go"
        else:
            test_file = f"test_{target_name}{ext}"

        # Read existing tests if they exist
        existing_tests = ""
        existing_path = str(tools.root / test_file)
        try:
            existing_content = tools.read_file(existing_path)
            if not existing_content.startswith("[ERROR]"):
                existing_tests = f"\n--- EXISTING TESTS: {test_file} ---\n{existing_content[:4000]}"
        except Exception:
            pass

        context = f"--- SOURCE FILE: {req.target_file} ---\n{source_content[:8000]}{existing_tests}"

        focus_instructions = {
            "happy_path": "Focus on testing the expected normal behavior and common use cases.",
            "edge_cases": "Focus on edge cases, boundary conditions, error handling, and unexpected inputs.",
            "comprehensive": "Write comprehensive tests covering happy path, edge cases, error handling, and integration points.",
        }

        prompt = f"""Write {framework} tests for the source file below.
Coverage focus: {req.coverage_focus}
{focus_instructions.get(req.coverage_focus, focus_instructions['edge_cases'])}

Requirements:
- Output ONLY the test code (no explanations before/after)
- Use {framework} conventions and best practices
- Include descriptive test names that explain what's being tested
- Test each public function/method/class
- Include setup/teardown where appropriate
- Mock external dependencies
- Add brief comments for non-obvious test cases

After the test code, list the COVERAGE AREAS as a bullet list like:
COVERAGE AREAS:
- area 1
- area 2"""

        result = await team.collaborate(
            prompt=prompt,
            context=context,
            mode="peer_review",
        )

        # Extract test code and coverage areas
        answer = result.final_answer
        coverage_areas = []
        test_code = answer

        # Split at COVERAGE AREAS section
        import re
        coverage_split = re.split(r'COVERAGE\s*AREAS\s*:', answer, flags=re.IGNORECASE)
        if len(coverage_split) > 1:
            test_code = coverage_split[0].strip()
            for line in coverage_split[1].split("\n"):
                line = line.strip().lstrip("-*").strip()
                if line:
                    coverage_areas.append(line)

        # Strip markdown code fences if present
        test_code = re.sub(r'^```\w*\n', '', test_code)
        test_code = re.sub(r'\n```\s*$', '', test_code)

        # Count test functions
        if framework == "pytest":
            tests_count = len(re.findall(r'(?:def|async def)\s+test_', test_code))
        elif framework in ("jest",):
            tests_count = len(re.findall(r'(?:it|test)\s*\(', test_code))
        elif framework == "go test":
            tests_count = len(re.findall(r'func\s+Test', test_code))
        else:
            tests_count = len(re.findall(r'(?:def|func|function)\s+[Tt]est', test_code))

        node_id = ""
        neural = getattr(team, '_neural_memory', None)
        if neural:
            try:
                node_id = neural.store(
                    content=f"test-generate: {tests_count} tests for {req.target_file}",
                    node_type="solution",
                    tags=["test-generate"],
                    confidence=result.confidence_score,
                )
            except Exception:
                pass

        return TestGenResponse(
            request_id=request_id,
            node_id=node_id,
            test_code=test_code,
            test_file_path=test_file,
            tests_count=tests_count,
            coverage_areas=coverage_areas,
            agents_used=result.participating_agents,
            total_time=time.time() - start,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test generate error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Deploy Check Endpoint ───────────────────────────────────────────

class DeployCheckRequest(BaseModel):
    project_path: str = Field(..., description="Absolute path to the project")
    git_range: str = Field("HEAD~5..HEAD", description="Git range to analyze")
    environment: str = Field("production", description="Target environment: production, staging, dev")

class DeployCheckResponse(BaseModel):
    request_id: str
    node_id: str = ""
    risk_score: float
    risk_level: str
    findings: List[Dict]
    go_no_go: str
    agents_used: List[str]
    total_time: float


@app.post("/v1/deploy-check", response_model=DeployCheckResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def deploy_check(req: DeployCheckRequest):
    """Pre-deploy risk assessment with go/no-go recommendation."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    try:
        from products.fred_api.coding_endpoints import ProjectTools
        tools = ProjectTools(req.project_path)

        # Gather deployment context
        context_parts = [f"ENVIRONMENT: {req.environment}"]

        # Git log
        git_log = tools.run_command(f"git log {req.git_range} --format='%h %an: %s' --no-merges")
        if git_log["exit_code"] == 0:
            context_parts.append(f"COMMITS:\n{git_log['stdout'][:2000]}")

        # Diff stat
        diff_stat = tools.run_command(f"git diff {req.git_range} --stat")
        if diff_stat["exit_code"] == 0:
            context_parts.append(f"DIFF STAT:\n{diff_stat['stdout'][:2000]}")

        # Actual diff (truncated)
        diff_content = tools.run_command(f"git diff {req.git_range}")
        if diff_content["exit_code"] == 0:
            context_parts.append(f"DIFF:\n{diff_content['stdout'][:6000]}")

        # Check for common risk signals
        git_status = tools.git_status()
        if git_status.strip():
            context_parts.append(f"UNCOMMITTED CHANGES:\n{git_status}")

        # Check for config/env changes
        config_diff = tools.run_command(f"git diff {req.git_range} -- '*.env*' '*.yml' '*.yaml' 'Dockerfile*' 'docker-compose*'")
        if config_diff["exit_code"] == 0 and config_diff["stdout"].strip():
            context_parts.append(f"CONFIG/INFRA CHANGES:\n{config_diff['stdout'][:2000]}")

        context = "\n\n".join(context_parts)

        prompt = f"""Perform a pre-deployment risk assessment for deploying to {req.environment}.

Analyze the changes and provide:

1. RISK SCORE: 0-10 (0=completely safe, 10=extremely dangerous)
2. RISK LEVEL: low (0-3), medium (4-5), high (6-7), critical (8-10)
3. GO/NO-GO: "GO" or "NO-GO"

4. FINDINGS: List each finding as:
   - CATEGORY: (security/performance/reliability/data/config/dependency)
   - DESCRIPTION: what the risk is
   - SEVERITY: low/medium/high/critical
   - RECOMMENDATION: how to mitigate

Consider:
- Database migrations or schema changes
- API breaking changes
- Security vulnerabilities introduced
- Performance regressions
- Missing error handling
- Configuration changes
- Dependency updates
- Uncommitted changes
- Large or risky refactors"""

        result = await team.collaborate(
            prompt=prompt,
            context=context,
            mode="expert_panel",
        )

        # Parse the response
        answer = result.final_answer
        import re

        # Extract risk score
        risk_score = 5.0
        score_match = re.search(r'risk\s*score[:\s]*(\d+(?:\.\d+)?)', answer, re.IGNORECASE)
        if score_match:
            risk_score = min(10.0, max(0.0, float(score_match.group(1))))

        # Determine risk level
        if risk_score <= 3:
            risk_level = "low"
        elif risk_score <= 5:
            risk_level = "medium"
        elif risk_score <= 7:
            risk_level = "high"
        else:
            risk_level = "critical"

        # Override with explicit level if found
        level_match = re.search(r'risk\s*level[:\s]*(low|medium|high|critical)', answer, re.IGNORECASE)
        if level_match:
            risk_level = level_match.group(1).lower()

        # Extract go/no-go
        go_no_go = "GO" if risk_score <= 5 else "NO-GO"
        go_match = re.search(r'(GO|NO-GO|NO GO)', answer, re.IGNORECASE)
        if go_match:
            go_no_go = "NO-GO" if "NO" in go_match.group(1).upper() else "GO"

        # Parse findings
        findings = []
        current_finding: Dict = {}
        for line in answer.split("\n"):
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            if line_lower.startswith("category:") or line_lower.startswith("- category:"):
                if current_finding.get("category"):
                    findings.append(current_finding)
                current_finding = {"category": line_stripped.split(":", 1)[-1].strip()}
            elif line_lower.startswith("description:") or line_lower.startswith("- description:"):
                current_finding["description"] = line_stripped.split(":", 1)[-1].strip()
            elif line_lower.startswith("severity:") or line_lower.startswith("- severity:"):
                current_finding["severity"] = line_stripped.split(":", 1)[-1].strip().lower()
            elif line_lower.startswith("recommendation:") or line_lower.startswith("- recommendation:"):
                current_finding["recommendation"] = line_stripped.split(":", 1)[-1].strip()

        if current_finding.get("category"):
            findings.append(current_finding)

        node_id = ""
        neural = getattr(team, '_neural_memory', None)
        if neural:
            try:
                node_id = neural.store(
                    content=f"deploy-check: {go_no_go} risk={risk_score:.1f} ({risk_level})",
                    node_type="solution",
                    tags=["deploy-check"],
                    confidence=result.confidence_score,
                )
            except Exception:
                pass

        return DeployCheckResponse(
            request_id=request_id,
            node_id=node_id,
            risk_score=risk_score,
            risk_level=risk_level,
            findings=findings,
            go_no_go=go_no_go,
            agents_used=result.participating_agents,
            total_time=time.time() - start,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deploy check error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Onboard Endpoint ────────────────────────────────────────────────

class OnboardRequest(BaseModel):
    project_path: str = Field(..., description="Absolute path to the project")
    focus: str = Field("overview", description="Focus: overview, architecture, api, frontend, backend")
    depth: str = Field("medium", description="Detail level: quick, medium, deep")

class OnboardResponse(BaseModel):
    request_id: str
    node_id: str = ""
    summary: str
    architecture: str
    key_files: List[Dict]
    patterns: List[str]
    gotchas: List[str]
    getting_started: str
    agents_used: List[str]
    total_time: float


@app.post("/v1/onboard", response_model=OnboardResponse,
          dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def onboard(req: OnboardRequest):
    """Project explainer: architecture, key files, patterns, and gotchas for onboarding."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    try:
        from products.fred_api.coding_endpoints import ProjectTools
        tools = ProjectTools(req.project_path)

        # Gather project info
        info = tools.get_project_info()
        all_files = tools.list_files()

        context_parts = [
            f"PROJECT: {info['project_path']}",
            f"FILES: {info['files_count']} | LANGUAGES: {info['languages']}",
            f"STRUCTURE:\n" + "\n".join(f"  {s}" for s in info["structure"]),
            f"HAS GIT: {info['has_git']} | HAS TESTS: {info['has_tests']}",
        ]

        # Read key files based on focus
        files_to_read = []
        if req.focus in ("overview", "architecture"):
            # Read entry points, configs, and READMEs
            priority_patterns = [
                "README", "readme", "main.py", "app.py", "server.py", "index.ts", "index.js",
                "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
                "Dockerfile", "docker-compose", "Makefile",
            ]
            for f in all_files:
                if any(p in f for p in priority_patterns):
                    files_to_read.append(f)
        elif req.focus == "api":
            for f in all_files:
                if any(kw in f.lower() for kw in ["route", "router", "endpoint", "api", "server", "view"]):
                    files_to_read.append(f)
        elif req.focus == "frontend":
            for f in all_files:
                if any(f.endswith(ext) for ext in [".jsx", ".tsx", ".vue", ".svelte", ".html"]):
                    files_to_read.append(f)
        elif req.focus == "backend":
            for f in all_files:
                if any(kw in f.lower() for kw in ["model", "service", "route", "main", "config", "database", "db"]):
                    files_to_read.append(f)

        # Limit based on depth
        depth_limits = {"quick": 5, "medium": 10, "deep": 20}
        max_files = depth_limits.get(req.depth, 10)
        files_to_read = files_to_read[:max_files]

        for filepath in files_to_read:
            content = tools.read_file(str(tools.root / filepath))
            if not content.startswith("[ERROR]"):
                truncate_at = 3000 if req.depth == "quick" else 5000 if req.depth == "medium" else 8000
                context_parts.append(f"--- {filepath} ---\n{content[:truncate_at]}")

        context = "\n\n".join(context_parts)

        depth_instructions = {
            "quick": "Keep it brief — one paragraph per section. Hit the highlights only.",
            "medium": "Provide moderate detail — enough for a developer to start contributing.",
            "deep": "Be thorough — cover architecture decisions, data flow, and non-obvious patterns.",
        }

        prompt = f"""You are onboarding a new developer to this project.
Focus: {req.focus}
Depth: {req.depth}
{depth_instructions.get(req.depth, depth_instructions['medium'])}

Provide these sections:

1. SUMMARY: What this project does, in plain language
2. ARCHITECTURE: How the system is structured (components, data flow, key decisions)
3. KEY FILES: List the most important files with:
   - PATH: file path
   - PURPOSE: what it does
   - IMPORTANCE: critical/high/medium
4. PATTERNS: Design patterns and conventions used in this codebase
5. GOTCHAS: Common pitfalls, non-obvious behaviors, and things that could trip up a new developer
6. GETTING STARTED: Steps to set up, run, and start developing"""

        result = await team.collaborate(
            prompt=prompt,
            context=context,
            mode="parallel",
        )

        # Parse the response into sections
        answer = result.final_answer
        import re

        def extract_section(text: str, section_name: str, next_sections: List[str]) -> str:
            """Extract text between section headers."""
            pattern = rf'(?:#+\s*)?{section_name}\s*:?\s*\n(.*?)(?=(?:#+\s*)?(?:{"|".join(next_sections)})\s*:?|\Z)'
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else ""

        sections_order = ["SUMMARY", "ARCHITECTURE", "KEY FILES", "PATTERNS", "GOTCHAS", "GETTING STARTED"]
        summary = extract_section(answer, "SUMMARY", sections_order[1:]) or answer[:300]
        architecture = extract_section(answer, "ARCHITECTURE", sections_order[2:]) or ""
        getting_started = extract_section(answer, "GETTING STARTED", []) or ""

        # Parse key files
        key_files = []
        key_files_section = extract_section(answer, "KEY FILES", sections_order[3:])
        current_kf: Dict = {}
        for line in key_files_section.split("\n"):
            line_lower = line.strip().lower()
            if line_lower.startswith("path:") or line_lower.startswith("- path:"):
                if current_kf.get("path"):
                    key_files.append(current_kf)
                current_kf = {"path": line.strip().split(":", 1)[-1].strip()}
            elif line_lower.startswith("purpose:") or line_lower.startswith("- purpose:"):
                current_kf["purpose"] = line.strip().split(":", 1)[-1].strip()
            elif line_lower.startswith("importance:") or line_lower.startswith("- importance:"):
                current_kf["importance"] = line.strip().split(":", 1)[-1].strip().lower()
        if current_kf.get("path"):
            key_files.append(current_kf)

        # Parse patterns
        patterns = []
        patterns_section = extract_section(answer, "PATTERNS", sections_order[4:])
        for line in patterns_section.split("\n"):
            line = line.strip().lstrip("-*").strip()
            if line and not line.lower().startswith("pattern"):
                patterns.append(line)

        # Parse gotchas
        gotchas = []
        gotchas_section = extract_section(answer, "GOTCHAS", sections_order[5:])
        for line in gotchas_section.split("\n"):
            line = line.strip().lstrip("-*").strip()
            if line and not line.lower().startswith("gotcha"):
                gotchas.append(line)

        node_id = ""
        neural = getattr(team, '_neural_memory', None)
        if neural:
            try:
                node_id = neural.store(
                    content=f"onboard: {summary[:200]}",
                    node_type="solution",
                    tags=["onboard"],
                    confidence=result.confidence_score,
                )
            except Exception:
                pass

        return OnboardResponse(
            request_id=request_id,
            node_id=node_id,
            summary=summary,
            architecture=architecture,
            key_files=key_files,
            patterns=patterns,
            gotchas=gotchas,
            getting_started=getting_started,
            agents_used=result.participating_agents,
            total_time=time.time() - start,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Onboard error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Intelligence v2 Endpoints ────────────────────────────────────────

class SmartFeedbackRequest(BaseModel):
    task_id: str = Field(..., description="Task ID to rate")
    rating: float = Field(..., description="Rating from -1.0 (terrible) to 1.0 (excellent)")
    agents: List[str] = Field(default_factory=list, description="Agents that participated")
    task_type: str = Field("general", description="Task type")
    comment: Optional[str] = Field(None, description="Optional feedback comment")
    correction: Optional[str] = Field(None, description="Optional correct answer")


@app.post("/v1/rate", dependencies=[Depends(verify_api_key)])
async def rate_response(req: SmartFeedbackRequest):
    """Rate a response to improve future results. This feeds the learning loop."""
    team = get_team()
    try:
        outcome = await team.process_feedback(
            task_id=req.task_id, rating=req.rating,
            agents=req.agents, task_type=req.task_type,
            comment=req.comment, correction=req.correction,
        )
        return {"status": "processed", **outcome.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/roi", dependencies=[Depends(verify_api_key)])
async def roi_dashboard(period: str = "all_time"):
    """ROI dashboard — time saved, money saved, agent rankings."""
    team = get_team()
    report = team.get_roi_report(period)
    return report.to_dict()


@app.get("/v1/leaderboard", dependencies=[Depends(verify_api_key)])
async def agent_leaderboard():
    """Agent performance leaderboard."""
    team = get_team()
    return {"leaderboard": team.get_agent_leaderboard()}


@app.get("/v1/agent-profiles", dependencies=[Depends(verify_api_key)])
async def agent_profiles():
    """Agent feedback profiles — satisfaction rates, task scores."""
    team = get_team()
    return {"profiles": team.get_feedback_profiles()}


class WorkflowRequest(BaseModel):
    task: str = Field(..., description="Task for the agentic workflow")
    context: str = Field("", description="Additional context")
    max_fix_cycles: int = Field(3, description="Max fix attempts")


@app.post("/v1/workflow", dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def run_workflow(req: WorkflowRequest):
    """Run a full agentic workflow: plan -> execute -> validate -> fix -> verify."""
    team = get_team()
    try:
        result = await team.run_workflow(task=req.task, context=req.context)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Intelligence Endpoints ────────────────────────────────────────────


class ScanRequest(BaseModel):
    content: str = Field(..., description="AI response or code to scan")
    task_type: str = Field("general", description="Task type — coding, debugging, analysis, general")
    language: str = Field("", description="Language hint (auto-detected if empty)")


class TransparencyRequest(BaseModel):
    prompt: str = Field(..., description="Original prompt")
    answer: str = Field(..., description="Final synthesized answer")
    agent_responses: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of agent responses (agent_name, content, confidence)",
    )


class NexusSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Max results")


@app.get("/v1/arbitrage", dependencies=[Depends(verify_api_key)])
async def arbitrage_report(task_type: str = ""):
    """Cost arbitrage — savings report and optional provider comparison."""
    from elgringo.intelligence.cost_arbitrage import get_optimizer

    opt = get_optimizer()
    result = {"savings": opt.get_savings_report()}
    if task_type:
        result["comparison"] = opt.get_provider_comparison(task_type)
    return result


@app.post("/v1/scan", dependencies=[Depends(verify_api_key)])
async def scan_response(req: ScanRequest):
    """Scan AI output for syntax errors, security issues, hallucinations."""
    from elgringo.intelligence.auto_failure_detector import get_failure_detector

    detector = get_failure_detector()
    result = detector.check(req.content, task_type=req.task_type, language=req.language or None)
    return result.to_dict()


@app.post("/v1/transparency", dependencies=[Depends(verify_api_key)])
async def transparency_report(req: TransparencyRequest):
    """Show how a multi-agent answer was built."""
    from elgringo.intelligence.reasoning_transparency import get_reasoning_transparency
    from elgringo.agents.base import AgentResponse, ModelType

    rt = get_reasoning_transparency()
    responses = []
    for r in req.agent_responses:
        responses.append(AgentResponse(
            agent_name=r.get("agent_name", "unknown"),
            model_type=ModelType.LOCAL,
            content=r.get("content", ""),
            confidence=r.get("confidence", 0.5),
            response_time=r.get("response_time", 0.0),
        ))

    if not responses:
        return {"error": "No agent responses provided"}

    report = rt.analyze(responses, req.prompt, req.answer)
    return report.to_dict()


@app.get("/v1/agent-insights", dependencies=[Depends(verify_api_key)])
async def agent_insights():
    """Deep agent profiles — satisfaction, task scores, expertise adjustments."""
    from elgringo.intelligence.feedback_loop import get_feedback_loop

    floop = get_feedback_loop()
    return {
        "profiles": floop.get_all_profiles(),
        "roi_summary": floop.get_roi_summary(),
    }


@app.get("/v1/nexus", dependencies=[Depends(verify_api_key)])
async def nexus_stats():
    """Cross-project intelligence stats and patterns."""
    from elgringo.intelligence.cross_project import get_nexus

    nexus = get_nexus()
    patterns = nexus.get_cross_project_patterns()
    return {
        "stats": nexus.get_stats(),
        "patterns": [
            {
                "pattern": p.pattern,
                "occurrences": p.occurrences,
                "projects": p.projects_affected,
                "solution": p.solution,
            }
            for p in patterns[:20]
        ],
    }


@app.post("/v1/nexus/search", dependencies=[Depends(verify_api_key)])
async def nexus_search(req: NexusSearchRequest):
    """Search solutions/mistakes across all registered projects."""
    from elgringo.intelligence.cross_project import get_nexus

    nexus = get_nexus()
    results = nexus.search_across_projects(req.query, limit=req.limit)
    return {"query": req.query, "results": results, "total": len(results)}


# ── MLX Local Inference Endpoints ─────────────────────────────────────

class MLXRequest(BaseModel):
    prompt: str = Field(..., description="Your question or coding task")
    model: str = Field("auto", description="'coder' (Qwen 7B), 'general' (Qwen 3B), or 'auto'")
    system_prompt: str = Field("", description="Optional system prompt")
    max_tokens: int = Field(2048, description="Max response length")
    temperature: float = Field(0.7, description="Sampling temperature")
    stream: bool = Field(False, description="Stream tokens via SSE")


_mlx_engine = None


def _get_mlx_engine():
    global _mlx_engine
    if _mlx_engine is None:
        from elgringo.apple.mlx_inference import get_mlx_inference
        _mlx_engine = get_mlx_inference()
    return _mlx_engine


MLX_MODEL_MAP = {
    "coder": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    "general": "mlx-community/Qwen2.5-3B-Instruct-4bit",
}


def _resolve_mlx_model(model: str, prompt: str) -> str:
    if model != "auto":
        return MLX_MODEL_MAP.get(model, MLX_MODEL_MAP["coder"])
    code_kw = ["code", "function", "class", "bug", "error", "fix", "refactor",
               "python", "javascript", "typescript", "rust", "go", "sql",
               "implement", "write", "debug", "test", "api", "endpoint"]
    return MLX_MODEL_MAP["coder"] if any(k in prompt.lower() for k in code_kw) else MLX_MODEL_MAP["general"]


@app.post("/v1/mlx", dependencies=[Depends(verify_api_key)])
async def mlx_generate(req: MLXRequest):
    """Local MLX inference on Apple Silicon. Zero cost, private, fast."""
    mlx = _get_mlx_engine()
    if not mlx.is_available:
        raise HTTPException(status_code=503, detail="MLX not available (requires Apple Silicon)")

    model_name = _resolve_mlx_model(req.model, req.prompt)
    await mlx.load_model(model_name)

    if req.stream:
        async def stream_tokens():
            stream = await mlx.generate(
                prompt=req.prompt, model_name=model_name,
                system_prompt=req.system_prompt or None,
                max_tokens=req.max_tokens, temperature=req.temperature,
                stream=True,
            )
            async for token in stream:
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_tokens(), media_type="text/event-stream")

    response = await mlx.generate(
        prompt=req.prompt, model_name=model_name,
        system_prompt=req.system_prompt or None,
        max_tokens=req.max_tokens, temperature=req.temperature,
    )

    short_name = "Qwen Coder 7B" if "Coder" in model_name else "Qwen 3B"
    return {
        "content": response.content,
        "model": short_name,
        "model_id": model_name,
        "tokens_generated": response.tokens_generated,
        "tokens_per_second": response.tokens_per_second,
        "inference_time": response.inference_time,
        "memory_mb": response.memory_used_mb,
        "cost": 0.0,
    }


@app.get("/v1/mlx/status")
async def mlx_status():
    """MLX local inference status — loaded models, memory, availability."""
    mlx = _get_mlx_engine()
    if not mlx.is_available:
        return {"available": False, "reason": "MLX not available (requires Apple Silicon)"}

    from elgringo.apple.mlx_inference import AVAILABLE_MODELS
    mem = mlx.get_memory_info()
    return {
        "available": True,
        "loaded_models": mlx.loaded_models,
        "memory": mem,
        "available_models": {
            info.get("alias", name): {"id": name, "size": info["size"], "quantization": info["quantization"]}
            for name, info in AVAILABLE_MODELS.items()
        },
    }


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
