"""
Maintenance Advisor Service
============================

AI-powered maintenance optimization and predictive analytics.
Analyzes work orders, equipment history, and failure patterns to
recommend preventive maintenance strategies.

Endpoints:
    POST /advisor/analyze-workorder  - Analyze a work order for optimization
    POST /advisor/predict-failure    - Predict equipment failure probability
    POST /advisor/optimize-schedule  - Optimize a maintenance schedule
    POST /advisor/root-cause         - Root cause analysis for equipment failure
    GET  /advisor/health             - Health check

Run: uvicorn products.maintenance_advisor.server:app --port 8082
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Maintenance Advisor",
    description="AI-powered maintenance optimization powered by FredAI",
    version="0.1.0",
    docs_url="/advisor/docs",
)

_cors_origins = os.getenv(
    "MAINTENANCE_ADVISOR_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ─────────────────────────────────────────────────────────────

ADVISOR_API_KEYS: set = set()
_raw = os.getenv("MAINTENANCE_ADVISOR_API_KEYS", "")
if _raw:
    ADVISOR_API_KEYS = {k.strip() for k in _raw.split(",") if k.strip()}


async def verify_api_key(request: Request):
    if not ADVISOR_API_KEYS:
        return
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    if auth[7:] not in ADVISOR_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Shared Team Instance ─────────────────────────────────────────────

_team = None


def get_team():
    global _team
    if _team is None:
        from ai_dev_team.orchestrator import AIDevTeam

        _team = AIDevTeam(project_name="maintenance-advisor", enable_memory=True)
    return _team


# ── Request / Response Models ────────────────────────────────────────


class WorkOrderRequest(BaseModel):
    description: str = Field(..., description="Work order description")
    equipment_type: str = Field("", description="Equipment type (e.g., HVAC, pump, conveyor)")
    priority: str = Field("medium", description="Priority: low, medium, high, critical")
    history: Optional[List[str]] = Field(None, description="Past work orders for this equipment")


class FailurePredictionRequest(BaseModel):
    equipment_type: str = Field(..., description="Equipment type")
    age_years: float = Field(..., description="Equipment age in years")
    last_maintenance: str = Field("", description="Date of last maintenance (ISO format)")
    operating_hours: float = Field(0, description="Total operating hours")
    symptoms: Optional[List[str]] = Field(None, description="Current symptoms or warnings")
    environment: str = Field("", description="Operating environment (indoor, outdoor, harsh, clean)")


class ScheduleRequest(BaseModel):
    equipment_list: List[Dict[str, Any]] = Field(
        ..., description="List of equipment with type, age, priority, last_maintenance"
    )
    budget_constraint: Optional[float] = Field(None, description="Monthly budget limit")
    max_downtime_hours: Optional[float] = Field(None, description="Max acceptable downtime per month")


class RootCauseRequest(BaseModel):
    failure_description: str = Field(..., description="Description of the failure")
    equipment_type: str = Field("", description="Equipment type")
    timeline: Optional[List[str]] = Field(None, description="Timeline of events leading to failure")
    environmental_factors: Optional[List[str]] = Field(None, description="Environmental conditions")


class AdvisorResponse(BaseModel):
    request_id: str
    analysis_type: str
    recommendation: str
    agents_used: List[str]
    confidence: float
    total_time: float
    timestamp: str


# ── Endpoints ────────────────────────────────────────────────────────


@app.get("/advisor/health")
async def health():
    return {"status": "healthy", "service": "maintenance-advisor", "version": "0.1.0"}


@app.post(
    "/advisor/analyze-workorder",
    response_model=AdvisorResponse,
    dependencies=[Depends(verify_api_key)],
)
async def analyze_workorder(req: WorkOrderRequest):
    """Analyze a work order and recommend optimization strategies."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]

    history_section = ""
    if req.history:
        history_section = "\n\nPast work orders for this equipment:\n" + "\n".join(
            f"- {h}" for h in req.history
        )

    prompt = (
        f"You are a CMMS maintenance optimization expert. Analyze this work order "
        f"and provide recommendations for:\n"
        f"1. Optimal repair approach\n"
        f"2. Parts likely needed\n"
        f"3. Whether this should trigger a preventive maintenance review\n"
        f"4. Estimated time and skill level required\n\n"
        f"Equipment type: {req.equipment_type}\n"
        f"Priority: {req.priority}\n"
        f"Description: {req.description}"
        f"{history_section}"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="parallel")
        return AdvisorResponse(
            request_id=request_id,
            analysis_type="workorder-analysis",
            recommendation=result.final_answer,
            agents_used=result.participating_agents,
            confidence=result.confidence_score,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/advisor/predict-failure",
    response_model=AdvisorResponse,
    dependencies=[Depends(verify_api_key)],
)
async def predict_failure(req: FailurePredictionRequest):
    """Predict equipment failure probability and recommend preventive actions."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]

    symptoms_section = ""
    if req.symptoms:
        symptoms_section = "\nCurrent symptoms:\n" + "\n".join(f"- {s}" for s in req.symptoms)

    prompt = (
        f"You are a predictive maintenance specialist. Based on the following "
        f"equipment data, predict failure probability and recommend actions:\n\n"
        f"Equipment: {req.equipment_type}\n"
        f"Age: {req.age_years} years\n"
        f"Operating hours: {req.operating_hours}\n"
        f"Last maintenance: {req.last_maintenance or 'unknown'}\n"
        f"Environment: {req.environment or 'standard'}"
        f"{symptoms_section}\n\n"
        f"Provide:\n"
        f"1. Failure probability (low/medium/high/critical) with reasoning\n"
        f"2. Most likely failure modes\n"
        f"3. Recommended immediate actions\n"
        f"4. Preventive maintenance schedule recommendation"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="consensus")
        return AdvisorResponse(
            request_id=request_id,
            analysis_type="failure-prediction",
            recommendation=result.final_answer,
            agents_used=result.participating_agents,
            confidence=result.confidence_score,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/advisor/optimize-schedule",
    response_model=AdvisorResponse,
    dependencies=[Depends(verify_api_key)],
)
async def optimize_schedule(req: ScheduleRequest):
    """Optimize maintenance schedule across equipment fleet."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]

    equipment_desc = "\n".join(
        f"- {eq.get('type', 'unknown')}: age={eq.get('age', '?')}y, "
        f"priority={eq.get('priority', 'medium')}, "
        f"last_maint={eq.get('last_maintenance', 'unknown')}"
        for eq in req.equipment_list
    )

    constraints = ""
    if req.budget_constraint:
        constraints += f"\nBudget constraint: ${req.budget_constraint}/month"
    if req.max_downtime_hours:
        constraints += f"\nMax downtime: {req.max_downtime_hours} hours/month"

    prompt = (
        f"You are a maintenance scheduling optimizer. Create an optimized "
        f"maintenance schedule for this equipment fleet:\n\n"
        f"{equipment_desc}\n"
        f"{constraints}\n\n"
        f"Provide:\n"
        f"1. Prioritized maintenance schedule\n"
        f"2. Grouping opportunities (combine tasks to reduce downtime)\n"
        f"3. Critical items that need immediate attention\n"
        f"4. Cost-saving recommendations\n"
        f"5. Risk assessment for deferred items"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="parallel")
        return AdvisorResponse(
            request_id=request_id,
            analysis_type="schedule-optimization",
            recommendation=result.final_answer,
            agents_used=result.participating_agents,
            confidence=result.confidence_score,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/advisor/root-cause",
    response_model=AdvisorResponse,
    dependencies=[Depends(verify_api_key)],
)
async def root_cause_analysis(req: RootCauseRequest):
    """Perform root cause analysis on equipment failure."""
    team = get_team()
    request_id = str(uuid.uuid4())[:8]

    timeline_section = ""
    if req.timeline:
        timeline_section = "\n\nTimeline of events:\n" + "\n".join(
            f"- {t}" for t in req.timeline
        )

    env_section = ""
    if req.environmental_factors:
        env_section = "\n\nEnvironmental factors:\n" + "\n".join(
            f"- {f}" for f in req.environmental_factors
        )

    prompt = (
        f"You are a root cause analysis specialist. Analyze this equipment failure:\n\n"
        f"Equipment: {req.equipment_type or 'not specified'}\n"
        f"Failure: {req.failure_description}"
        f"{timeline_section}"
        f"{env_section}\n\n"
        f"Provide:\n"
        f"1. Most likely root cause(s) ranked by probability\n"
        f"2. Contributing factors\n"
        f"3. Corrective actions to prevent recurrence\n"
        f"4. Systemic changes recommended\n"
        f"5. Lessons learned for the maintenance team"
    )

    try:
        result = await team.collaborate(prompt=prompt, mode="consensus")
        return AdvisorResponse(
            request_id=request_id,
            analysis_type="root-cause",
            recommendation=result.final_answer,
            agents_used=result.participating_agents,
            confidence=result.confidence_score,
            total_time=result.total_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry point ──────────────────────────────────────────────────────


def main():
    import uvicorn

    port = int(os.getenv("MAINTENANCE_ADVISOR_PORT", "8082"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
