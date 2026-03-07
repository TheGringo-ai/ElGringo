"""Sprint and task management router."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from products.command_center.models import (
    SprintCreate,
    SprintCurrentOut,
    SprintOut,
    StatsOut,
    TaskCreate,
    TaskOut,
    TaskSprintAssign,
    TaskStatusUpdate,
    VelocityPoint,
)
from products.command_center.services import get_sprint_manager

router = APIRouter(tags=["sprints"])

VALID_STATUSES = ("backlog", "sprint", "in_progress", "review", "done")


def _task_to_out(t) -> TaskOut:
    return TaskOut(
        id=t.id, title=t.title, description=t.description,
        status=t.status, priority=t.priority if isinstance(t.priority, int) else 3,
        estimate_hours=t.estimate_hours, sprint_id=t.sprint_id,
        project=t.project, assignee=t.assignee,
        created_at=t.created_at, updated_at=t.updated_at,
    )


def _sprint_to_out(s) -> SprintOut:
    return SprintOut(
        id=s.id, name=s.name, start_date=s.start_date,
        end_date=s.end_date, goals=s.goals, status=s.status,
    )


# ── Stats ────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsOut)
async def get_stats():
    sm = get_sprint_manager()
    raw = sm.get_summary_stats()
    active = raw.get("active_sprint")
    return StatsOut(
        tasks_total=raw["tasks_total"],
        tasks_done=raw["tasks_done"],
        tasks_in_progress=raw["tasks_in_progress"],
        tasks_in_review=raw["tasks_in_review"],
        tasks_backlog=raw["tasks_backlog"],
        active_sprint=SprintOut(**active) if active else None,
        velocity=raw["velocity"],
    )


@router.get("/velocity", response_model=list[VelocityPoint])
async def get_velocity(weeks: int = Query(4, ge=1, le=12)):
    sm = get_sprint_manager()
    return [VelocityPoint(**v) for v in sm.get_velocity_trend(weeks=weeks)]


# ── Sprints ──────────────────────────────────────────────────────────

@router.get("/sprints", response_model=list[SprintOut])
async def list_sprints():
    sm = get_sprint_manager()
    return [_sprint_to_out(s) for s in sm.sprints]


@router.get("/sprints/current", response_model=SprintCurrentOut)
async def get_current_sprint():
    sm = get_sprint_manager()
    sprint = sm.get_current_sprint()
    if not sprint:
        raise HTTPException(404, "No active sprint")
    tasks = sm.get_tasks_for_sprint(sprint.id)
    completion = sm.calculate_sprint_completion(sprint.id)
    try:
        end = datetime.fromisoformat(sprint.end_date)
        days_left = max(0, (end - datetime.now()).days)
    except ValueError:
        days_left = 0
    return SprintCurrentOut(
        sprint=_sprint_to_out(sprint),
        tasks=[_task_to_out(t) for t in tasks],
        completion_percentage=completion,
        days_remaining=days_left,
    )


@router.post("/sprints", response_model=SprintOut, status_code=201)
async def create_sprint(req: SprintCreate):
    sm = get_sprint_manager()
    s = sm.create_sprint(
        name=req.name, goals=req.goals,
        start_date=req.start_date, end_date=req.end_date,
    )
    return _sprint_to_out(s)


@router.get("/sprints/{sprint_id}/tasks", response_model=list[TaskOut])
async def get_sprint_tasks(sprint_id: str):
    sm = get_sprint_manager()
    tasks = sm.get_tasks_for_sprint(sprint_id)
    return [_task_to_out(t) for t in tasks]


# ── Tasks ────────────────────────────────────────────────────────────

@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    status: Optional[str] = Query(None),
    sprint_id: Optional[str] = Query(None),
):
    sm = get_sprint_manager()
    tasks = sm.tasks
    if status:
        tasks = [t for t in tasks if t.status == status]
    if sprint_id:
        tasks = [t for t in tasks if t.sprint_id == sprint_id]
    return [_task_to_out(t) for t in tasks]


@router.post("/tasks", response_model=TaskOut, status_code=201)
async def create_task(req: TaskCreate):
    sm = get_sprint_manager()
    t = sm.create_task(
        title=req.title, description=req.description,
        priority=req.priority, estimate_hours=req.estimate_hours,
        project=req.project, assignee=req.assignee,
    )
    return _task_to_out(t)


@router.patch("/tasks/{task_id}/status")
async def update_task_status(task_id: str, req: TaskStatusUpdate):
    if req.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status: '{req.status}'. Must be one of: {', '.join(VALID_STATUSES)}")
    sm = get_sprint_manager()
    ok = sm.update_task_status(task_id, req.status)
    if not ok:
        raise HTTPException(404, f"Task not found: {task_id}")
    return {"success": True, "task_id": task_id, "new_status": req.status}


@router.post("/tasks/{task_id}/assign-sprint")
async def assign_task_to_sprint(task_id: str, req: TaskSprintAssign):
    sm = get_sprint_manager()
    ok = sm.add_to_sprint(req.sprint_id, task_id)
    if not ok:
        raise HTTPException(404, "Task or sprint not found")
    return {"success": True, "task_id": task_id, "sprint_id": req.sprint_id}
