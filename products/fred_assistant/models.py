"""Pydantic models for Fred Assistant API."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Boards ────────────────────────────────────────────────────────

class BoardOut(BaseModel):
    id: str
    name: str
    icon: str = "📋"
    color: str = "blue"
    position: int = 0
    columns: list[str] = ["todo", "in_progress", "done"]
    task_count: int = 0


class BoardCreate(BaseModel):
    name: str
    icon: str = "📋"
    color: str = "blue"
    columns: list[str] = ["todo", "in_progress", "done"]


# ── Tasks ─────────────────────────────────────────────────────────

class TaskOut(BaseModel):
    id: str
    board_id: str
    title: str
    description: str = ""
    status: str = "todo"
    priority: int = 3
    category: str = "general"
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    recurring: Optional[str] = None
    tags: list[str] = []
    notes: str = ""
    position: int = 0
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None


class TaskCreate(BaseModel):
    board_id: str = "work"
    title: str
    description: str = ""
    status: str = "todo"
    priority: int = 3
    category: str = "general"
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    recurring: Optional[str] = None
    tags: list[str] = []
    notes: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    category: Optional[str] = None
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    board_id: Optional[str] = None
    position: Optional[int] = None


class TaskMoveRequest(BaseModel):
    status: str


# ── Memory ────────────────────────────────────────────────────────

class MemoryOut(BaseModel):
    id: str
    category: str
    key: str
    value: str
    context: str = ""
    importance: int = 5
    created_at: str = ""
    updated_at: str = ""


class MemoryCreate(BaseModel):
    category: str
    key: str
    value: str
    context: str = ""
    importance: int = 5


# ── Chat ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    persona: str = "fred"


class ChatMessage(BaseModel):
    role: str
    content: str
    persona: str = "fred"
    created_at: str = ""


# ── Briefing ──────────────────────────────────────────────────────

class BriefingOut(BaseModel):
    id: str
    date: str
    content: str
    tasks_snapshot: dict = {}
    created_at: str = ""


# ── Quick Capture ─────────────────────────────────────────────────

class QuickCaptureRequest(BaseModel):
    text: str
    board_id: str = "work"


# ── Stats ─────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_tasks: int = 0
    completed_today: int = 0
    overdue: int = 0
    in_progress: int = 0
    due_today: int = 0
    boards: int = 0
    memories: int = 0
    streak_days: int = 0


# ── Projects ─────────────────────────────────────────────────────

class ProjectOut(BaseModel):
    name: str
    path: str
    git_branch: Optional[str] = None
    git_status: str = "clean"
    uncommitted_changes: int = 0
    last_commit_msg: Optional[str] = None
    last_commit_date: Optional[str] = None
    tech_stack: list[str] = []
    remote_url: Optional[str] = None
    repo_html_url: str = ""
    deploy_url: str = ""
    is_git: bool = False


# ── Calendar ─────────────────────────────────────────────────────

class CalendarEventOut(BaseModel):
    id: str
    title: str
    description: str = ""
    event_type: str = "event"
    start_date: str
    start_time: Optional[str] = None
    end_date: Optional[str] = None
    end_time: Optional[str] = None
    all_day: bool = False
    recurring: Optional[str] = None
    color: str = "blue"
    location: str = ""
    linked_task_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class CalendarEventCreate(BaseModel):
    title: str
    description: str = ""
    event_type: str = "event"
    start_date: str
    start_time: Optional[str] = None
    end_date: Optional[str] = None
    end_time: Optional[str] = None
    all_day: bool = False
    recurring: Optional[str] = None
    color: str = "blue"
    location: str = ""
    linked_task_id: Optional[str] = None


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    start_date: Optional[str] = None
    start_time: Optional[str] = None
    end_date: Optional[str] = None
    end_time: Optional[str] = None
    all_day: Optional[bool] = None
    recurring: Optional[str] = None
    color: Optional[str] = None
    location: Optional[str] = None


# ── Content & Social ─────────────────────────────────────────────

class ContentItemOut(BaseModel):
    id: str
    title: str
    body: str = ""
    content_type: str = "post"
    platform: str = "linkedin"
    status: str = "draft"
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    published_at: Optional[str] = None
    tags: list[str] = []
    ai_generated: bool = False
    created_at: str = ""
    updated_at: str = ""


class ContentItemCreate(BaseModel):
    title: str
    body: str = ""
    content_type: str = "post"
    platform: str = "linkedin"
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    tags: list[str] = []


class ContentGenerateRequest(BaseModel):
    content_type: str = "post"
    platform: str = "linkedin"
    topic: str
    tone: str = "professional"
    length: str = "medium"


class SocialAccountOut(BaseModel):
    id: str
    platform: str
    handle: str
    display_name: str = ""
    connected: bool = False
    created_at: str = ""


class SocialAccountUpdate(BaseModel):
    handle: Optional[str] = None
    display_name: Optional[str] = None
    connected: Optional[bool] = None


# ── Goals & Business Coach ───────────────────────────────────────

class GoalOut(BaseModel):
    id: str
    title: str
    description: str = ""
    category: str = "business"
    target_date: Optional[str] = None
    status: str = "active"
    progress: int = 0
    milestones: list[dict] = []
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


class GoalCreate(BaseModel):
    title: str
    description: str = ""
    category: str = "business"
    target_date: Optional[str] = None
    milestones: list[dict] = []


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_date: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    milestones: Optional[list[dict]] = None
    notes: Optional[str] = None


class WeeklyReviewOut(BaseModel):
    id: str
    week_start: str
    wins: list[str] = []
    challenges: list[str] = []
    lessons: list[str] = []
    next_week_priorities: list[str] = []
    ai_insights: str = ""
    created_at: str = ""


# ── Focus Mode ──────────────────────────────────────────────────

class FocusSessionOut(BaseModel):
    id: str
    task_id: Optional[str] = None
    task_title: str = ""
    started_at: str
    ended_at: Optional[str] = None
    planned_minutes: int = 25
    notes: str = ""
    completed: bool = False
    created_at: str = ""


class FocusStartRequest(BaseModel):
    task_id: Optional[str] = None
    planned_minutes: int = 25


class FocusStopRequest(BaseModel):
    session_id: Optional[str] = None
    completed: bool = True
    notes: str = ""


# ── CRM / Leads ────────────────────────────────────────────────

class LeadOut(BaseModel):
    id: str
    name: str
    company: str = ""
    email: str = ""
    phone: str = ""
    source: str = ""
    pipeline_stage: str = "cold"
    deal_value: float = 0
    notes: str = ""
    next_followup: Optional[str] = None
    tags: list[str] = []
    created_at: str = ""
    updated_at: str = ""


class LeadCreate(BaseModel):
    name: str
    company: str = ""
    email: str = ""
    phone: str = ""
    source: str = ""
    pipeline_stage: str = "cold"
    deal_value: float = 0
    notes: str = ""
    next_followup: Optional[str] = None
    tags: list[str] = []


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    pipeline_stage: Optional[str] = None
    deal_value: Optional[float] = None
    notes: Optional[str] = None
    next_followup: Optional[str] = None
    tags: Optional[list[str]] = None


class OutreachEntry(BaseModel):
    lead_id: str
    outreach_type: str = "email"
    content: str = ""
    result: str = ""


class FollowupRequest(BaseModel):
    date: str
    notes: str = ""


# ── CEO Lens Metrics ───────────────────────────────────────────

class MetricsSnapshotOut(BaseModel):
    id: str
    date: str
    mrr: float = 0
    leads_contacted: int = 0
    calls_booked: int = 0
    trials_started: int = 0
    deals_closed: int = 0
    sprint_completion_pct: float = 0
    content_published: int = 0
    revenue: float = 0
    custom_metrics: dict = {}
    created_at: str = ""


class MetricLogRequest(BaseModel):
    name: str
    value: float


# ── Playbooks ──────────────────────────────────────────────────

class PlaybookOut(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = "general"
    steps: list[dict] = []
    created_at: str = ""
    updated_at: str = ""


class PlaybookCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "general"
    steps: list[dict] = []


class PlaybookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    steps: Optional[list[dict]] = None


# ── Unified Inbox ──────────────────────────────────────────────

class InboxItem(BaseModel):
    type: str
    title: str
    description: str = ""
    priority: int = 3
    entity_id: str = ""
    action_hint: str = ""


# ── Repo Intelligence ─────────────────────────────────────────

class RepoAnalysisOut(BaseModel):
    id: str
    project_name: str
    project_path: str
    depth: str = "quick"
    health_score: int = 0
    tech_stack: list[str] = []
    findings: dict = {}
    tasks_generated: list[dict] = []
    summary: str = ""
    created_at: str = ""


class RepoAnalyzeRequest(BaseModel):
    depth: str = "quick"


class RepoTasksRequest(BaseModel):
    create_tasks: bool = False


# ── Platform Integration ─────────────────────────────────────────

class PRReviewCallback(BaseModel):
    repo: str
    pr_number: int
    verdict: str
    summary: str = ""
    confidence: float = 0
    agents_used: list[str] = []
    review_time: float = 0


class PlatformAuditRequest(BaseModel):
    audit_type: str = "full"


class PlatformDocsRequest(BaseModel):
    doc_type: str = "readme"


class ServiceResultOut(BaseModel):
    id: str
    service: str
    action: str
    project_name: str = ""
    input_summary: str = ""
    result: str = ""
    agents_used: list[str] = []
    total_time: float = 0
    created_at: str = ""


# ── Audit Insights ──────────────────────────────────────────────────

class ParseFindingsRequest(BaseModel):
    raw_findings: str
    project_name: str
    language: str = "python"


class ApplyFixRequest(BaseModel):
    project_name: str
    file_path: str
    finding_id: str
    code_snippet: str = ""
    suggested_fix: str
    description: str = ""


class AuditChatRequest(BaseModel):
    message: str
    project_name: str
    audit_findings: list[dict] = []
    finding_id: Optional[str] = None


class ReviewChatRequest(BaseModel):
    message: str
    project_name: str
    review_data: dict = {}


# ── App Factory ──────────────────────────────────────────────────

class AppOut(BaseModel):
    id: str
    name: str
    display_name: str
    description: str = ""
    app_type: str = "fullstack"
    tech_stack: dict = {}
    spec: dict = {}
    status: str = "draft"
    repo_url: str = ""
    deploy_url: str = ""
    port: int = 0
    project_dir: str = ""
    error_message: str = ""
    created_at: str = ""
    updated_at: str = ""


class AppCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: str = ""
    app_type: str = "fullstack"
    tech_stack: dict = {}
    template: Optional[str] = None


class AppUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    app_type: Optional[str] = None
    tech_stack: Optional[dict] = None
    repo_url: Optional[str] = None


class AppGenerateRequest(BaseModel):
    enrich: bool = True
    template: Optional[str] = None


class AppBuildOut(BaseModel):
    id: str
    app_id: str
    version: int = 1
    step: str
    status: str = "pending"
    log: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class AppCustomerCreate(BaseModel):
    app_id: str
    name: str
    email: str = ""
    plan: str = "free"


class AppCustomerOut(BaseModel):
    id: str
    app_id: str
    name: str
    email: str = ""
    plan: str = "free"
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""
    mrr: float = 0
    status: str = "trial"
    created_at: str = ""
    updated_at: str = ""


class ProjectChatRequest(BaseModel):
    message: str
    context: dict = {}


class ProjectTasksRequest(BaseModel):
    instructions: str = ""
    board_id: str = "work"


class FileWriteRequest(BaseModel):
    content: str


class FileCreateRequest(BaseModel):
    path: str
    content: str = ""


class FileRenameRequest(BaseModel):
    old_path: str
    new_path: str
