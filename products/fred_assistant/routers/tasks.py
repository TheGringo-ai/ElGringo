from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from products.fred_assistant.models import TaskOut, TaskCreate, TaskUpdate, TaskMoveRequest, DashboardStats
from products.fred_assistant.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    return task_service.get_dashboard_stats()


@router.get("/today", response_model=list[TaskOut])
async def get_today():
    return task_service.get_today_tasks()


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    board_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    due_date: Optional[str] = Query(None),
):
    return task_service.list_tasks(board_id=board_id, status=status, due_date=due_date)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: str):
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(data: TaskCreate):
    return task_service.create_task(data.model_dump())


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(task_id: str, data: TaskUpdate):
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return task
    return task_service.update_task(task_id, updates)


@router.patch("/{task_id}/move", response_model=TaskOut)
async def move_task(task_id: str, data: TaskMoveRequest):
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task_service.update_task(task_id, {"status": data.status})


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str):
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    task_service.delete_task(task_id)
