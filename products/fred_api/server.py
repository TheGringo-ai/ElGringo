"""
Fred API - Orchestration as a Service
======================================

Public REST API exposing El Gringo's multi-agent orchestration capabilities.

Endpoints:
    POST /v1/collaborate  - Multi-agent collaboration
    POST /v1/ask          - Single-agent with smart routing
    POST /v1/review       - Code review
    POST /v1/stream       - SSE streaming response
    GET  /v1/agents       - List available agents
    GET  /v1/health       - Health check

Run: uvicorn products.fred_api.server:app --port 8080
"""

import json
import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

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
        # Apply budget-aware agent selection
        agents_to_use = req.agents
        if not agents_to_use and req.budget != "premium":
            # Budget tiers: prefer cheaper models
            budget_agents = {
                "budget": ["gemini-creative"],  # $0.0008/request
                "standard": ["gemini-creative", "chatgpt-coder"],  # Mix cheap + mid
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
TEAM_PERSONAS = {
    "lead-developer": {
        "role": "Lead Developer & Architect",
        "capabilities": ["architecture", "coding", "system-design", "best-practices", "debugging"],
        "system_prompt": (
            "You are the Lead Developer. You prioritize clean architecture, maintainability, "
            "and proven patterns. You push back on over-engineering and prefer simplicity. "
            "You care about developer experience, testing, and long-term code health."
        ),
    },
    "security-engineer": {
        "role": "Security Engineer",
        "capabilities": ["security", "threat-modeling", "compliance", "penetration-testing", "risk-assessment"],
        "system_prompt": (
            "You are the Security Engineer. You see threats everywhere and that's your job. "
            "You challenge every design decision from a security perspective. You know OWASP, "
            "zero-trust, least privilege, and defense in depth. You are paranoid by profession."
        ),
    },
    "product-manager": {
        "role": "Product Manager",
        "capabilities": ["user-research", "prioritization", "roadmap", "business-value", "customer-empathy"],
        "system_prompt": (
            "You are the Product Manager. You care about users, business value, and shipping fast. "
            "You push back on technical perfection that delays delivery. You ask 'does the user care?' "
            "and 'what's the ROI?' You balance technical debt against speed-to-market."
        ),
    },
    "devops-engineer": {
        "role": "DevOps & Infrastructure Engineer",
        "capabilities": ["deployment", "monitoring", "scaling", "CI-CD", "cloud-infrastructure", "reliability"],
        "system_prompt": (
            "You are the DevOps Engineer. You care about reliability, observability, and operational "
            "simplicity. You hate snowflake deployments and manual processes. You champion automation, "
            "infrastructure-as-code, and boring technology that works at 3am."
        ),
    },
    "ux-designer": {
        "role": "UX Designer & Frontend Advocate",
        "capabilities": ["user-experience", "accessibility", "performance", "design-systems", "usability"],
        "system_prompt": (
            "You are the UX Designer. You advocate for the end user relentlessly. You care about "
            "page load times, accessibility, intuitive workflows, and delightful interactions. "
            "You challenge engineers when they optimize for developer convenience over user experience."
        ),
    },
    "qa-engineer": {
        "role": "QA Engineer & Quality Advocate",
        "capabilities": ["testing", "edge-cases", "regression", "automation", "quality-metrics"],
        "system_prompt": (
            "You are the QA Engineer. You find the bugs nobody else sees. You think about edge cases, "
            "race conditions, data corruption, and what happens when users do the unexpected. "
            "You push for comprehensive testing and refuse to ship without confidence."
        ),
    },
}

class TeamDebateRequest(BaseModel):
    topic: str = Field(..., description="The topic or question to debate")
    context: str = Field("", description="Additional context")
    team: List[str] = Field(
        default=["lead-developer", "security-engineer", "product-manager"],
        description=f"Team roles to participate. Available: {', '.join(TEAM_PERSONAS.keys())}"
    )
    model: str = Field(
        default="gemini",
        description="Base model for all personas: gemini (cheapest), chatgpt, grok"
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
    """Single-model team debate — one cheap model plays multiple expert roles.

    Creates a virtual dev team where each persona (lead-developer, security-engineer,
    product-manager, etc.) is the SAME underlying model with different system prompts.
    Runs a full 4-phase debate for ~$0.005 instead of ~$0.25.

    Available roles: lead-developer, security-engineer, product-manager,
    devops-engineer, ux-designer, qa-engineer
    """
    request_id = str(uuid.uuid4())[:8]

    # Validate team roles
    invalid_roles = [r for r in req.team if r not in TEAM_PERSONAS]
    if invalid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown roles: {invalid_roles}. Available: {list(TEAM_PERSONAS.keys())}"
        )
    if len(req.team) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 team members for a debate")

    # Create persona agents from the chosen base model
    from elgringo.agents.base import AgentConfig, ModelType

    agents = []
    for role_name in req.team:
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

    # Run the debate using the collaboration engine directly
    try:
        from elgringo.collaboration.engine import CollaborationEngine, CollaborationMode, CollaborationContext

        engine = CollaborationEngine()
        collab_ctx = CollaborationContext(
            mode=CollaborationMode.DEBATE,
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
            agents_used=[r for r in req.team],
            confidence=sum(r.confidence for r in successful) / len(successful),
            mode=f"team-debate ({req.model})",
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
    """List available team roles for team-debate."""
    return {
        name: {"role": p["role"], "capabilities": p["capabilities"]}
        for name, p in TEAM_PERSONAS.items()
    }


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
