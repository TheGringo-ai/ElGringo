"""Pydantic request/response models for Command Center API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Error ────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# ── Sprint & Task ────────────────────────────────────────────────────

class TaskOut(BaseModel):
    id: str
    title: str
    description: str
    status: str
    priority: int
    estimate_hours: float
    sprint_id: Optional[str]
    project: str
    assignee: str
    created_at: str
    updated_at: str


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    priority: int = Field(3, ge=1, le=5)
    estimate_hours: float = Field(1.0, ge=0)
    project: str = ""
    assignee: str = ""


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., description="One of: backlog, sprint, in_progress, review, done")


class TaskSprintAssign(BaseModel):
    sprint_id: str


class SprintOut(BaseModel):
    id: str
    name: str
    start_date: str
    end_date: str
    goals: List[str]
    status: str


class SprintCreate(BaseModel):
    name: str = Field(..., min_length=1)
    goals: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class SprintCurrentOut(BaseModel):
    sprint: Optional[SprintOut]
    tasks: List[TaskOut]
    completion_percentage: float
    days_remaining: int


class StatsOut(BaseModel):
    tasks_total: int
    tasks_done: int
    tasks_in_progress: int
    tasks_in_review: int
    tasks_backlog: int
    active_sprint: Optional[SprintOut]
    velocity: float


class VelocityPoint(BaseModel):
    sprint: str
    velocity: float
    completion: float


# ── Content ──────────────────────────────────────────────────────────

class ContentItemOut(BaseModel):
    id: str
    type: str
    status: str
    created_at: str
    data: Dict[str, Any]


class ContentGenerateRequest(BaseModel):
    type: str = Field(..., description="linkedin_post, blog_post, newsletter, release_notes")
    params: Dict[str, Any] = Field(default_factory=dict)


class ContentJobOut(BaseModel):
    job_id: str
    status: str  # running, completed, failed
    type: str
    item_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ContentStatusUpdate(BaseModel):
    status: str = Field(..., description="approved or rejected")


# ── Scheduler ────────────────────────────────────────────────────────

class ScheduledTaskOut(BaseModel):
    id: str
    name: str
    cron: str
    type: str
    enabled: bool
    next_run: Optional[str]
    last_run: Optional[str]


class ScheduledTaskCreate(BaseModel):
    name: str = Field(..., min_length=1)
    cron_expression: str = Field(..., min_length=5)
    task_type: str
    config: Dict[str, Any] = Field(default_factory=dict)


# ── Standup ──────────────────────────────────────────────────────────

class StandupOut(BaseModel):
    date: str
    formatted: str
    raw: Dict[str, Any]


# ── Chat ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    persona: str = "dev_lead"
    context: str = ""


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    agent_name: Optional[str] = None
    confidence: Optional[float] = None
    response_time: Optional[float] = None


# ── Persona ──────────────────────────────────────────────────────────

class PersonaOut(BaseModel):
    name: str
    role: str
    capabilities: List[str]
    output_format: str
    temperature: float


# ── Health ───────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status: str
    version: str
    services: Dict[str, bool]
