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
