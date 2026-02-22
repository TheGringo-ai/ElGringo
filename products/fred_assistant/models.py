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
