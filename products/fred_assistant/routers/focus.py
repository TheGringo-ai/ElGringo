"""Focus Mode router — start/stop focus sessions, stats, history."""

from fastapi import APIRouter, Query

from products.fred_assistant.services import focus_service

router = APIRouter(prefix="/focus", tags=["focus"])


@router.post("/start")
def start_focus(data: dict):
    return focus_service.start_focus(
        task_id=data.get("task_id"),
        planned_minutes=data.get("planned_minutes", 25),
    )


@router.post("/stop")
def stop_focus(data: dict):
    result = focus_service.end_focus(
        session_id=data.get("session_id"),
        completed=data.get("completed", True),
        notes=data.get("notes", ""),
    )
    if not result:
        return {"error": "No active focus session found"}
    return result


@router.get("/active")
def get_active():
    session = focus_service.get_active_session()
    return session or {"active": False}


@router.get("/stats")
def get_stats(days: int = Query(7, ge=1, le=90)):
    return focus_service.get_focus_stats(days)


@router.get("/sessions")
def list_sessions(days: int = Query(7, ge=1, le=90)):
    return focus_service.list_sessions(days)
