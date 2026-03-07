"""Scheduler and standup automation router."""


from fastapi import APIRouter, HTTPException, Query

from products.command_center.models import (
    ScheduledTaskCreate,
    ScheduledTaskOut,
    StandupOut,
)
from products.command_center.services import get_scheduler, get_standup_generator

router = APIRouter(tags=["automation"])

# ── Scheduler ────────────────────────────────────────────────────────

VALID_TASK_TYPES = ("standup", "social_post", "sprint_report", "newsletter", "code_review", "custom")


@router.get("/scheduler", response_model=list[ScheduledTaskOut])
async def list_scheduled_tasks():
    sched = get_scheduler()
    return [ScheduledTaskOut(**t) for t in sched.list_tasks()]


@router.post("/scheduler", response_model=ScheduledTaskOut, status_code=201)
async def add_scheduled_task(req: ScheduledTaskCreate):
    if req.task_type not in VALID_TASK_TYPES:
        raise HTTPException(400, f"Invalid task type: '{req.task_type}'. Must be one of: {', '.join(VALID_TASK_TYPES)}")
    sched = get_scheduler()
    task_id = sched.add_task(
        name=req.name,
        cron_expr=req.cron_expression,
        task_type=req.task_type,
        config=req.config,
    )
    tasks = sched.list_tasks()
    added = next((t for t in tasks if t["id"] == task_id), None)
    if not added:
        raise HTTPException(500, "Failed to create scheduled task")
    return ScheduledTaskOut(**added)


@router.delete("/scheduler/{task_id}")
async def remove_scheduled_task(task_id: str):
    sched = get_scheduler()
    ok = sched.remove_task(task_id)
    if not ok:
        raise HTTPException(404, f"Scheduled task not found: {task_id}")
    return {"success": True, "task_id": task_id}


@router.patch("/scheduler/{task_id}/toggle")
async def toggle_scheduled_task(task_id: str):
    sched = get_scheduler()
    ok = sched.toggle_task(task_id)
    if not ok:
        raise HTTPException(404, f"Scheduled task not found: {task_id}")
    tasks = sched.list_tasks()
    toggled = next((t for t in tasks if t["id"] == task_id), None)
    return {"success": True, "task_id": task_id, "enabled": toggled["enabled"] if toggled else None}


# ── Standups ─────────────────────────────────────────────────────────

@router.get("/standups/today", response_model=StandupOut)
async def get_today_standup():
    sg = get_standup_generator()
    history = sg.get_standup_history(days=1)
    if history:
        data = history[0]
    else:
        data = sg.generate_standup()
        sg.save_standup(data)
    return StandupOut(
        date=data["date"],
        formatted=sg.format_standup(data),
        raw=data,
    )


@router.get("/standups", response_model=list[StandupOut])
async def list_standups(days: int = Query(7, ge=1, le=30)):
    sg = get_standup_generator()
    history = sg.get_standup_history(days=days)
    return [
        StandupOut(date=d["date"], formatted=sg.format_standup(d), raw=d)
        for d in history
    ]


@router.post("/standups/generate", response_model=StandupOut, status_code=201)
async def generate_standup():
    sg = get_standup_generator()
    data = sg.generate_standup()
    sg.save_standup(data)
    return StandupOut(
        date=data["date"],
        formatted=sg.format_standup(data),
        raw=data,
    )
